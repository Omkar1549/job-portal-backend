import httpx
import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# API Configuration
API_KEY = ""  # Set via environment variable in production
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff

# Simple in-memory cache (for production, use Redis)
_cache = {}
CACHE_TTL = timedelta(hours=24)

class AIServiceError(Exception):
    """Custom exception for AI Service errors"""
    pass

def _get_cache_key(service: str, input_text: str) -> str:
    """Generate cache key from service and input"""
    import hashlib
    key_input = f"{service}:{input_text}"
    return hashlib.md5(key_input.encode()).hexdigest()

def _get_cached_response(cache_key: str) -> Optional[str]:
    """Retrieve cached response if valid"""
    if cache_key in _cache:
        cached_data = _cache[cache_key]
        if datetime.now() < cached_data['expiry']:
            logger.info(f"Cache hit for key: {cache_key}")
            return cached_data['response']
        else:
            del _cache[cache_key]  # Expired
    return None

def _cache_response(cache_key: str, response: str):
    """Cache the response"""
    _cache[cache_key] = {
        'response': response,
        'expiry': datetime.now() + CACHE_TTL,
        'cached_at': datetime.now().isoformat()
    }
    logger.info(f"Response cached with key: {cache_key}")

async def _make_gemini_request(prompt: str, max_retries: int = MAX_RETRIES) -> str:
    """
    Make a request to Gemini API with retry logic
    
    Args:
        prompt: The text prompt to send
        max_retries: Number of retry attempts
        
    Returns:
        Generated text from Gemini
        
    Raises:
        AIServiceError: If all retries fail
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Gemini API request attempt {attempt + 1}/{max_retries}")
                
                response = await client.post(
                    GEMINI_URL, 
                    json=payload, 
                    timeout=REQUEST_TIMEOUT,
                    headers={"Content-Type": "application/json"}
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 10
                    logger.warning(f"Rate limited. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                # Handle success
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Validate response structure
                        if 'candidates' not in data or len(data['candidates']) == 0:
                            raise AIServiceError("Empty response from Gemini API")
                        
                        candidate = data['candidates'][0]
                        if 'content' not in candidate or 'parts' not in candidate['content']:
                            raise AIServiceError("Invalid response structure from Gemini API")
                        
                        text = candidate['content']['parts'][0].get('text', '')
                        if not text:
                            raise AIServiceError("Empty text in Gemini response")
                        
                        logger.info("Gemini API request successful")
                        return text
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        raise AIServiceError("Invalid JSON response from Gemini API")
                
                # Handle other HTTP errors
                elif response.status_code == 400:
                    logger.error(f"Bad request: {response.text}")
                    raise AIServiceError("Invalid request to Gemini API")
                
                elif response.status_code == 401:
                    logger.error("API key invalid or expired")
                    raise AIServiceError("Authentication failed with Gemini API")
                
                elif response.status_code == 500:
                    logger.warning(f"Server error {response.status_code}. Retrying...")
                    delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 10
                    await asyncio.sleep(delay)
                    continue
                
                else:
                    logger.error(f"HTTP {response.status_code}: {response.text}")
                    raise AIServiceError(f"Gemini API error: HTTP {response.status_code}")
                    
        except httpx.TimeoutException:
            logger.warning(f"Timeout on attempt {attempt + 1}. Retrying...")
            if attempt < max_retries - 1:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 10
                await asyncio.sleep(delay)
                continue
            else:
                raise AIServiceError("Request timeout - Gemini API not responding")
                
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            if attempt < max_retries - 1:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 10
                await asyncio.sleep(delay)
                continue
            else:
                raise AIServiceError(f"Network error: {str(e)}")
    
    raise AIServiceError("Max retries exceeded - AI service temporarily unavailable")


async def generate_job_description(job_title: str) -> str:
    """
    Generates a professional job description from a job title (Day 8 Feature)
    
    Args:
        job_title: The job position title
        
    Returns:
        AI-generated job description
        
    Raises:
        AIServiceError: If generation fails
    """
    try:
        # Validate input
        if not job_title or len(job_title.strip()) == 0:
            raise AIServiceError("Job title cannot be empty")
        
        if len(job_title) > 100:
            raise AIServiceError("Job title too long (max 100 characters)")
        
        # Check cache
        cache_key = _get_cache_key("job_description", job_title)
        cached = _get_cached_response(cache_key)
        if cached:
            return cached
        
        # Generate description
        prompt = (
            f"Write a professional, detailed job description for a '{job_title}' role. "
            f"Include:\n"
            f"1. Role Overview (2-3 sentences)\n"
            f"2. Key Responsibilities (5-7 bullet points)\n"
            f"3. Required Skills and Qualifications\n"
            f"4. Nice-to-have skills\n"
            f"5. Benefits and Growth Opportunities\n\n"
            f"Keep the tone professional and engaging. Make it suitable for posting on a job portal."
        )
        
        description = await _make_gemini_request(prompt)
        
        # Cache the result
        _cache_response(cache_key, description)
        
        return description
        
    except AIServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_job_description: {str(e)}")
        raise AIServiceError(f"Job description generation failed: {str(e)}")


async def match_resume_with_ai(job_description: str, resume_text: str) -> Dict[str, Any]:
    """
    Day 9: AI-powered resume matching against job description
    
    Compares a candidate's resume with a job description and provides:
    - Match score
    - Matched skills
    - Skill gaps
    - Hiring recommendation
    
    Args:
        job_description: Full job description text
        resume_text: Candidate's resume text
        
    Returns:
        Dictionary with matching analysis
        
    Raises:
        AIServiceError: If matching fails
    """
    try:
        # Validate inputs
        if not job_description or len(job_description.strip()) == 0:
            raise AIServiceError("Job description cannot be empty")
        
        if not resume_text or len(resume_text.strip()) == 0:
            raise AIServiceError("Resume text cannot be empty")
        
        if len(job_description) > 5000:
            raise AIServiceError("Job description too long (max 5000 characters)")
        
        if len(resume_text) > 5000:
            raise AIServiceError("Resume text too long (max 5000 characters)")
        
        # Create cache key (consider only resume for caching to avoid huge keys)
        cache_key = _get_cache_key("resume_match", resume_text[:500] + job_description[:500])
        cached = _get_cached_response(cache_key)
        if cached:
            return json.loads(cached)
        
        # Create the prompt
        prompt = (
            f"You are an expert ATS (Applicant Tracking System) recruiter. "
            f"Analyze the following resume against the job description and provide structured feedback.\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"CANDIDATE RESUME:\n{resume_text}\n\n"
            f"Provide the analysis in the following JSON format (output ONLY valid JSON, no markdown):\n"
            f"{{\n"
            f'  "match_score": <number 0-100>,\n'
            f'  "match_percentage": "<number>%",\n'
            f'  "top_matched_skills": ["skill1", "skill2", "skill3"],\n'
            f'  "skill_gaps": ["missing_skill1", "missing_skill2", "missing_skill3"],\n'
            f'  "experience_match": "<brief assessment>",\n'
            f'  "recommendation": "<HIRE|INTERVIEW|REJECT>",\n'
            f'  "recommendation_reason": "<detailed reason>",\n'
            f'  "strengths": ["strength1", "strength2"],\n'
            f'  "weaknesses": ["weakness1", "weakness2"],\n'
            f'  "overall_summary": "<2-3 sentence summary>"\n'
            f"}}"
        )
        
        response_text = await _make_gemini_request(prompt)
        
        # Parse and validate JSON response
        try:
            # Try to extract JSON from response (in case of extra text)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON found in response, returning raw text")
                analysis = {"raw_analysis": response_text}
            else:
                json_str = response_text[start_idx:end_idx]
                analysis = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from AI response, returning as text")
            analysis = {"raw_analysis": response_text}
        
        # Cache the result
        _cache_response(cache_key, json.dumps(analysis))
        
        return analysis
        
    except AIServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in match_resume_with_ai: {str(e)}")
        raise AIServiceError(f"Resume matching failed: {str(e)}")


async def improve_resume(resume_text: str, job_title: str = "") -> str:
    """
    BONUS: AI-powered resume improvement suggestions
    
    Args:
        resume_text: Current resume text
        job_title: Target job title (optional)
        
    Returns:
        Improvement suggestions
    """
    try:
        if not resume_text or len(resume_text.strip()) == 0:
            raise AIServiceError("Resume text cannot be empty")
        
        job_context = f"for a {job_title} position" if job_title else ""
        
        prompt = (
            f"Review the following resume {job_context} and provide specific, actionable improvement suggestions:\n\n"
            f"{resume_text}\n\n"
            f"Provide suggestions in these categories:\n"
            f"1. Content and Skills\n"
            f"2. Formatting and Presentation\n"
            f"3. Achievement Descriptions\n"
            f"4. Keywords for ATS\n"
            f"5. Grammar and Clarity"
        )
        
        suggestions = await _make_gemini_request(prompt)
        return suggestions
        
    except AIServiceError:
        raise
    except Exception as e:
        logger.error(f"Error in improve_resume: {str(e)}")
        raise AIServiceError(f"Resume improvement failed: {str(e)}")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics (for monitoring)"""
    return {
        "cached_items": len(_cache),
        "cache_keys": list(_cache.keys()),
        "ttl_hours": CACHE_TTL.total_seconds() / 3600
    }


def clear_cache():
    """Clear all cached responses"""
    global _cache
    _cache = {}
    logger.info("Cache cleared")