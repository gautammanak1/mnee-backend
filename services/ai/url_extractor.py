"""URL to post extraction service"""
import os
import json
import re
import aiohttp
from typing import Dict, Optional
from uagents import Context
from html import unescape
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
MAX_TEXT_LENGTH = int(os.getenv("URL_EXTRACTOR_MAX_LENGTH", "5000"))

class URLExtractor:
    """Handles URL content extraction and conversion to LinkedIn posts"""
    
    def __init__(self, agent_context: Optional[Context] = None):
        self.gemini_api_key = GEMINI_API_KEY
        self.agent_context = agent_context
    
    async def extract_and_convert(self, url: str, include_image: bool = False, language: str = "en") -> Dict:
        """Extract content from URL and convert to LinkedIn post"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        return {"error": f"Failed to fetch URL: HTTP {resp.status}"}
                    
                    html_content = await resp.text()
                    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                    
                    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
                    title = unescape(title_match.group(1).strip()) if title_match else None
                    
                    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.IGNORECASE | re.DOTALL)
                    body_content = body_match.group(1) if body_match else html_content
                    
                    text_content = re.sub(r'<[^>]+>', ' ', body_content)
                    text_content = unescape(text_content)
                    text_content = re.sub(r'\s+', ' ', text_content).strip()
                    
                    if len(text_content) > MAX_TEXT_LENGTH:
                        text_content = text_content[:MAX_TEXT_LENGTH] + "..."
            
            language_map = {
                'en': 'English', 'fr': 'French', 'es': 'Spanish', 'it': 'Italian',
                'de': 'German', 'pt': 'Portuguese', 'hi': 'Hindi', 'ja': 'Japanese',
                'ko': 'Korean', 'zh': 'Chinese'
            }
            language_name = language_map.get(language, 'English')
            
            prompt = f"""Based on the following content extracted from a URL, create an engaging LinkedIn post.

Source URL: {url}
Source Title: {title or "N/A"}

Content:
{text_content[:3000]}

Create a professional LinkedIn post that:
1. Summarizes the key points from this content
2. Adds value with insights or commentary
3. Is engaging and suitable for LinkedIn audience
4. Includes relevant hashtags (3-5)
5. Is written COMPLETELY in {language_name}

Return JSON format:
{{
  "text": "the post content here written COMPLETELY in {language_name}",
  "hashtags": ["#hashtag1", "#hashtag2", ...]
}}"""

            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            
            async with aiohttp.ClientSession() as session:
                gemini_url = GEMINI_API_URL.format(GEMINI_API_KEY=self.gemini_api_key)
                async with session.post(
                    gemini_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status == 200:
                        resp_json = await resp.json()
                        if "candidates" in resp_json and len(resp_json["candidates"]) > 0:
                            response_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                            
                            try:
                                json_match = re.search(r'\{[\s\S]*\}', response_text)
                                if json_match:
                                    parsed = json.loads(json_match.group(0))
                                else:
                                    parsed = json.loads(response_text)
                            except:
                                hashtags = re.findall(r'#\w+', response_text) or []
                                text = re.sub(r'\{[\s\S]*\}', '', response_text).strip()
                                parsed = {
                                    "text": text or response_text,
                                    "hashtags": hashtags[:5],
                                }
                            
                            result = {
                                "text": parsed.get("text", response_text),
                                "hashtags": parsed.get("hashtags", []),
                                "source_url": url,
                                "source_title": title,
                            }
                            
                            return result
                        else:
                            return {"error": "Failed to generate post from URL content"}
                    else:
                        error_text = await resp.text()
                        return {"error": f"API error: {error_text}"}
        except Exception as e:
            return {"error": f"Failed to convert URL to post: {str(e)}"}

