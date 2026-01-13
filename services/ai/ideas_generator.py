"""Enhanced LangChain integration for AI post generation with web search and image generation"""
from typing import Dict, Optional, List
import os
import aiohttp
import json
from dotenv import load_dotenv

load_dotenv()

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate

# Import agent executor
create_agent = None
AgentExecutor = None
AgentType = None
USE_CREATE_AGENT = False

try:
    from langchain.agents import create_agent
    from langchain.agents import AgentType
    USE_CREATE_AGENT = True
    try:
        from langchain.agents import AgentExecutor
    except ImportError:
        try:
            from langchain.agents.agent import AgentExecutor
        except ImportError:
            try:
                from langchain.agents.agent_executor import AgentExecutor
            except ImportError:
                AgentExecutor = None
except ImportError:
    try:
        from langchain.agents import initialize_agent, AgentType
        USE_CREATE_AGENT = False
        try:
            from langchain.agents import AgentExecutor
        except ImportError:
            try:
                from langchain.agents.agent import AgentExecutor
            except ImportError:
                AgentExecutor = None
    except ImportError:
        pass


class AIPostChain:
    """Enhanced LangChain-based AI post generation with web search and image generation"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.gemini_api_key,
            temperature=0.8,  # Higher temperature for more creative, personal content
        )
        self.tools = self._create_tools()
        self.agent = self._create_agent()
    
    def _create_tools(self):
        """Create LangChain tools for web search and content generation"""
        self_ref = self
        
        def web_search_sync(query: str) -> str:
            """Sync wrapper for web search"""
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(self_ref._web_search_async(query))
        
        return [
            Tool(
                name="web_search",
                description="Search the web for real-time, current information about tech trends, programming topics, tools, and latest developments. Always use this to find factual, up-to-date information with sources and links.",
                func=web_search_sync
            )
        ]
    
    async def _web_search_async(self, query: str) -> str:
        """Async web search using Gemini's googleSearch tool with enhanced results"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": f"Search web for LATEST INFORMATION about: {query}\n\nProvide:\n1. Most recent news/updates\n2. Official sources and links\n3. Key statistics or data\n4. Real-world examples\n5. Source URLs"}]
                    }],
                    "tools": [{"googleSearch": {}}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1500,
                    }
                }
                
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "candidates" in data and len(data["candidates"]) > 0:
                            candidate = data["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                text_parts = []
                                for part in candidate["content"]["parts"]:
                                    if "text" in part:
                                        text_parts.append(part["text"])
                                return "\n".join(text_parts)
            return ""
        except Exception:
            return ""
    
    def _create_agent(self):
        """Create LangChain agent with tools"""
        try:
            if USE_CREATE_AGENT and create_agent:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self._get_system_prompt()),
                    ("human", "{input}"),
                ])
                
                agent = create_agent(self.llm, self.tools, prompt)
                if hasattr(agent, 'ainvoke'):
                    return agent
                if AgentExecutor:
                    return AgentExecutor(agent=agent, tools=self.tools, verbose=False, max_iterations=3)
                return agent
            else:
                from langchain.agents import initialize_agent, AgentType
                return initialize_agent(
                    self.tools,
                    self.llm,
                    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    verbose=False,
                    max_iterations=3
                )
        except Exception:
            try:
                from langchain.agents import initialize_agent, AgentType
                return initialize_agent(
                    self.tools,
                    self.llm,
                    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    verbose=False,
                    max_iterations=3
                )
            except Exception:
                return None
    
    def _get_system_prompt(self) -> str:
        """Enhanced system prompt for personal, authentic tech content"""
        return """You are an authentic tech creator who shares PERSONAL EXPERIENCES and GENUINE INSIGHTS - NOT generic ChatGPT content.

🎯 YOUR UNIQUE VOICE:
- Share YOUR perspective, not regurgitated common knowledge
- Write like you're talking to peers, not lecturing
- Include personal lessons learned and failures, not just wins
- Be specific with technical details and real examples
- Show genuine passion for tech topics

🚨 CRITICAL RULES:
- NO meta-commentary ("Here's a post...", "Here's a draft...")
- NO generic advice or buzzwords
- START DIRECTLY with authentic content
- NO ChatGPT-like corporate tone
- Write naturally, like a real human

📚 CONTENT REQUIREMENTS:
- ALWAYS use web_search to find REAL, LATEST information
- Include personal experience with the topic
- Share specific technical details and real tools/projects
- Link to sources and references
- Focus on actionable insights
- Use conversational, authentic language

✨ WHAT MAKES IT AUTHENTIC:
- Share what YOU actually learned
- Include specific numbers, frameworks, or tools YOU use
- Mention real projects or experiences (anonymized if needed)
- Be honest about challenges and failures
- Show real technical depth, not surface-level understanding"""
    
    async def generate_post(self, topic: str, language: str = "en", personal_context: Optional[str] = None) -> Dict:
        """
        Generate LinkedIn post with personal touch and web search
        
        Args:
            topic: The post topic
            language: Language code (en, fr, es, etc.)
            personal_context: Optional personal experience or context to include
        """
        try:
            language_map = {
                'en': 'English', 'fr': 'French', 'es': 'Spanish', 'it': 'Italian',
                'de': 'German', 'pt': 'Portuguese', 'nl': 'Dutch', 'hi': 'Hindi'
            }
            language_name = language_map.get(language, 'English')
            
            if self.agent:
                return await self._generate_with_langchain(topic, language_name, personal_context)
            else:
                return await self._generate_direct_fallback(topic, language_name, personal_context)
        except Exception as e:
            import traceback
            return {
                "success": False,
                "content": "",
                "error": f"{str(e)}\n{traceback.format_exc()}"
            }
    
    async def _generate_direct_fallback(self, topic: str, language_name: str, personal_context: Optional[str] = None) -> Dict:
        """Fallback generation with enhanced personal content prompt"""
        personal_instruction = f"\n\nPERSONAL CONTEXT: {personal_context}" if personal_context else ""
        
        prompt = f"""You are an authentic tech creator sharing PERSONAL EXPERIENCES and GENUINE INSIGHTS.
TOPIC: "{topic}"{personal_instruction}

🚨 CRITICAL: Generate authentic, personal content - NOT generic ChatGPT-like posts
- Share YOUR perspective and personal experience
- Include specific technical details and real examples
- Avoid buzzwords and generic advice
- Write naturally like talking to peers
- START DIRECTLY with content (no introductions)

INSTRUCTIONS:
1. SEARCH FIRST: Use web_search to find latest information about "{topic}"
2. ADD PERSONAL TOUCH: Include your own experience, lessons learned, or specific technical insights
3. BE SPECIFIC: Use real tools, frameworks, projects, numbers, or technical details
4. AUTHENTIC TONE: Write conversationally, not like corporate content
5. INCLUDE SOURCES: Link all facts and information with markdown [Source](URL)

FORMAT:
- **bold** for key points
- `code` for technical terms and tools
- 200-300 words
- 3-5 relevant hashtags
- 1-2 strategic emojis
- Start with hook, end with question/CTA
- Write ENTIRELY in {language_name}

OUTPUT: Start directly with post content - no meta-commentary or explanations."""
        
        async with aiohttp.ClientSession() as session:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "tools": [{"googleSearch": {}}],
                "generationConfig": {
                    "temperature": 0.85,
                    "maxOutputTokens": 2048,
                }
            }
            
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=180)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {
                        "success": False,
                        "content": "",
                        "error": f"API error: {resp.status} - {error_text}"
                    }
                
                data = await resp.json()
                
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        text_parts = []
                        for part in candidate["content"]["parts"]:
                            if "text" in part:
                                text_parts.append(part["text"])
                        
                        content = "\n".join(text_parts)
                        content = self._remove_meta_commentary(content)
                        
                        return {
                            "success": True,
                            "content": content.strip(),
                            "error": None
                        }
                
                return {
                    "success": False,
                    "content": "",
                    "error": "No content generated"
                }
    
    async def _generate_with_langchain(self, topic: str, language_name: str, personal_context: Optional[str] = None) -> Dict:
        """Enhanced generation with personal context support"""
        try:
            import random
            
            # Varied hooks for authentic content
            hooks = [
                "Share a personal insight or lesson learned",
                "Start with a surprising technical discovery",
                "Begin with a real problem you faced",
                "Open with a contrarian take",
                "Start with specific technical depth",
                "Begin with a personal 'aha moment'"
            ]
            
            structures = [
                "Personal experience + Technical insight format",
                "Problem I faced, Solution I found, Lessons learned",
                "Real example from my work + Key takeaways",
                "Specific technical details + Practical application",
                "Challenge I overcame + Actionable advice",
                "Technical deep-dive + Personal perspective"
            ]
            
            ctas = [
                "Ask what others have experienced with this",
                "Invite others to share their approach",
                "Ask for feedback or counter-opinions",
                "Challenge readers with a question",
                "Ask what tools they recommend",
                "Invite specific recommendations or experiences"
            ]
            
            selected_hook = random.choice(hooks)
            selected_structure = random.choice(structures)
            selected_cta = random.choice(ctas)
            
            personal_section = f"\n\nYOUR PERSONAL CONTEXT/EXPERIENCE:\n{personal_context}" if personal_context else ""
            
            input_text = f"""Generate an AUTHENTIC, PERSONAL tech LinkedIn post:

TOPIC: "{topic}"{personal_section}

🎯 BE AUTHENTIC AND PERSONAL - NOT GENERIC:
Your voice: Real person sharing genuine insights, NOT ChatGPT corporate tone
- Include personal experience, lessons learned, or specific insights
- Share real technical details and specific tools/projects you use
- Be honest about challenges and learning journey
- Write conversationally like talking to tech peers

🚨 CRITICAL - START DIRECTLY WITH CONTENT:
- NO "Here's a post..." or meta-commentary
- First words are actual post content
- Write as if posting directly to LinkedIn

📝 CONTENT STRUCTURE ({selected_structure}):
1. {selected_hook}
2. Use web_search to find LATEST information about "{topic}"
3. Add YOUR personal perspective and experience
4. Include specific technical details, real tools, or examples
5. {selected_cta}

📋 FORMAT REQUIREMENTS:
- Use **bold** for key technical concepts
- Use `code` for tools, frameworks, languages, libraries
- Include [Source links](URL) for all facts
- 200-300 words
- Strategic placement of 1-2 emojis
- 3-5 relevant hashtags
- Conversational, authentic language
- ENTIRELY in {language_name}

✅ AUTHENTICITY CHECKLIST:
- Shares personal experience or perspective? ✓
- Includes specific technical details? ✓
- Uses real tools/projects/numbers? ✓
- Avoids generic corporate language? ✓
- Conversational tone like real person? ✓
- Includes web search results? ✓

Generate UNIQUE, AUTHENTIC content starting directly with the post."""
            
            result = await self.agent.ainvoke({"input": input_text})
            content = result.get("output", "")
            content = self._remove_meta_commentary(content)
            
            return {
                "success": True,
                "content": content.strip(),
                "error": None
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "content": "",
                "error": f"Generation failed: {str(e)}\n{traceback.format_exc()}"
            }
    
    async def generate_image_prompt(self, post_content: str) -> str:
        """
        NEW: Generate an optimized image prompt for the post content
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
                
                prompt = f"""Based on this tech LinkedIn post, create a PROFESSIONAL, CLEAN image prompt for generating a featured image.

POST CONTENT:
{post_content}

REQUIREMENTS:
- Describe a professional, minimalist tech-themed image
- Include relevant visual elements (code, tech symbols, charts if applicable)
- Use a modern, professional color scheme (blues, teals, grays, with accent color)
- Style: Clean, modern, professional
- NO people, NO stock photo vibes, NO cartoons
- Should look like professional tech blog/LinkedIn featured image
- Include specific technical visual elements related to the post topic

RESPOND WITH ONLY THE IMAGE PROMPT (no explanations)"""
                
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 256,
                    }
                }
                
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "candidates" in data and len(data["candidates"]) > 0:
                            candidate = data["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                for part in candidate["content"]["parts"]:
                                    if "text" in part:
                                        return part["text"].strip()
            return ""
        except Exception:
            return ""
    
    def _remove_meta_commentary(self, text: str) -> str:
        """Remove meta-commentary from generated content"""
        import re
        
        patterns = [
            r'^Here\'s a LinkedIn post.*?:?\s*',
            r'^Here\'s a draft.*?:?\s*',
            r'^Here is a LinkedIn post.*?:?\s*',
            r'^Here is a draft.*?:?\s*',
            r'^This is a LinkedIn post.*?:?\s*',
            r'^This LinkedIn post.*?:?\s*',
            r'^LinkedIn post draft.*?:?\s*',
            r'^designed to be engaging.*?:?\s*',
            r'^optimized for clarity.*?:?\s*',
            r'^incorporating real-world examples.*?:?\s*',
            r'^Below is.*?:?\s*',
            r'^Following is.*?:?\s*',
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_lower = line.lower().strip()
            if any(phrase in line_lower for phrase in [
                "here's a linkedin", "here is a linkedin", "this is a linkedin",
                "linkedin post draft", "designed to be", "optimized for",
                "incorporating real-world", "below is", "following is"
            ]):
                continue
            
            if line.strip() and not line.strip().startswith(('Here', 'This', 'Below', 'Following')):
                cleaned_lines.append(line)
            elif line.strip():
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
