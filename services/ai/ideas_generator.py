"""Post ideas generation service"""
import os
import json
import re
import aiohttp
from typing import Dict, Optional
from uagents import Context
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

class IdeasGenerator:
    """Handles LinkedIn post ideas generation"""
    
    def __init__(self, agent_context: Optional[Context] = None):
        self.gemini_api_key = GEMINI_API_KEY
        self.agent_context = agent_context
    
    async def generate(self, industry: Optional[str] = None, topic: Optional[str] = None, prompt: Optional[str] = None, count: int = 5, language: str = "en") -> Dict:
        """Generate LinkedIn post ideas optimized for content creators, tech professionals, and LinkedIn"""
        try:
            language_map = {
                'en': 'English', 'fr': 'French', 'es': 'Spanish', 'it': 'Italian',
                'de': 'German', 'pt': 'Portuguese', 'hi': 'Hindi', 'ja': 'Japanese',
                'ko': 'Korean', 'zh': 'Chinese'
            }
            language_name = language_map.get(language, 'English')
            
            context_parts = []
            if prompt:
                context_parts.append(f"User's specific request/prompt: {prompt}")
            if industry:
                context_parts.append(f"Industry: {industry}")
            if topic:
                context_parts.append(f"Topic focus: {topic}")
            
            context = "\n".join(context_parts) if context_parts else ""
            
            ai_prompt = f"""You are an expert LinkedIn content strategist specializing in creating viral, engaging TECHNICAL posts for content creators, tech professionals, and business leaders.

Generate {count} high-quality TECHNICAL LinkedIn post ideas optimized for content creators, tech professionals, and LinkedIn engagement.

Each idea should be:
- A complete, ready-to-post LinkedIn post (200-300 words)
- Optimized for LinkedIn's algorithm (engagement-driven, professional yet conversational)
- Perfect for content creators, tech professionals, and business professionals
- TECHNICAL and actionable with specific examples, frameworks, tools, technologies, or insights
- Use storytelling, data, technical depth, or unique perspectives
- Include relevant hashtags (3-5 per idea)
- Written completely in {language_name}
- DO NOT mention dates, years, or time-specific references

Focus areas (TECHNICAL EMPHASIS):
- Tech trends, AI, software development, startup culture, technical tools
- Content creation strategies with technical depth, personal branding, thought leadership
- Business growth with technical insights, productivity tools, career development
- Industry insights, technical case studies, real-world technical examples
- Programming languages, frameworks, architectures, technical methodologies
- Technical problem-solving, best practices, technical tutorials

{context}

Return ONLY a JSON array of strings. Each string should be a complete LinkedIn post idea ready to use.
Format: {{"ideas": ["Complete post idea 1 with hashtags", "Complete post idea 2 with hashtags", ...]}}
Do NOT return JSON objects with title/content fields. Return simple strings that are complete posts.
Each idea should START DIRECTLY with the post content - no meta-commentary or introductions."""

            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": ai_prompt}]}]}
            
            async with aiohttp.ClientSession() as session:
                gemini_url = GEMINI_API_URL.format(GEMINI_API_KEY=self.gemini_api_key)
                async with session.post(
                    gemini_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
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
                                
                                ideas_list = parsed.get("ideas", [])
                                if isinstance(ideas_list, list) and len(ideas_list) > 0:
                                    formatted_ideas = []
                                    for idea in ideas_list[:count]:
                                        if isinstance(idea, dict):
                                            title = idea.get('title', '')
                                            content = idea.get('content', '')
                                            image_suggestion = idea.get('image_suggestion', '')
                                            if title and content:
                                                idea_str = f"{title}\n\n{content}"
                                            elif content:
                                                idea_str = content
                                            else:
                                                idea_str = json.dumps(idea, indent=2)
                                        elif isinstance(idea, str):
                                            idea_str = idea.strip()
                                        else:
                                            idea_str = str(idea).strip()
                                        
                                        if idea_str and len(idea_str) > 20:
                                            formatted_ideas.append(idea_str)
                                    
                                    if formatted_ideas:
                                        return {"ideas": formatted_ideas}
                                
                                lines = [line.strip() for line in response_text.split('\n') 
                                        if line.strip() and not line.strip().startswith('{') 
                                        and not line.strip().startswith('[') 
                                        and not line.strip().startswith('"') 
                                        and not line.strip().startswith('}') 
                                        and not line.strip().startswith(']')]
                                ideas = [str(line) for line in lines if len(line) > 30][:count]
                                return {"ideas": ideas if ideas else ["Generate a post about industry trends", "Share a professional tip", "Discuss best practices"]}
                            except Exception as parse_error:
                                lines = [line.strip() for line in response_text.split('\n') 
                                        if line.strip() and not line.strip().startswith('{') 
                                        and not line.strip().startswith('[') 
                                        and not line.strip().startswith('"') 
                                        and not line.strip().startswith('}') 
                                        and not line.strip().startswith(']')
                                        and ':' not in line or line.count(':') == 1]
                                ideas = [str(line) for line in lines if len(line) > 30 and not line.startswith('"')][:count]
                                return {"ideas": ideas if ideas else ["Generate a post about industry trends", "Share a professional tip", "Discuss best practices"]}
                        else:
                            return {"error": "Failed to generate ideas"}
                    else:
                        error_text = await resp.text()
                        return {"error": f"API error: {error_text}"}
        except Exception as e:
            return {"error": f"Failed to generate post ideas: {str(e)}"}

