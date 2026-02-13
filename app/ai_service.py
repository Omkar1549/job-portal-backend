import httpx
import asyncio


apiKey = ""
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"

async def generate_job_description(job_title: str):
    
    prompt = (
        f"Act as a professional HR Manager. Write a detailed and professional job description "
        f"for the role: {job_title}. Include responsibilities and required skills. "
        f"Keep it professional and under 150 words."
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

   
    for delay in [1, 2, 4, 8]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(GEMINI_URL, json=payload, timeout=30.0)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    return result['candidates'][0]['content']['parts'][0]['text']
                elif response.status_code == 429:
                   
                    await asyncio.sleep(delay)
                else:
                    return f"AI Error: {response.status_code}"
        except Exception as e:
            await asyncio.sleep(delay)
            
    return "The AI ​​service is currently busy, please try again later."