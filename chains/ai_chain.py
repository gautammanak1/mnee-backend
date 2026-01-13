"""LangChain integration for AI post generation with tool calling - Handles content, images, ideas, and URL extraction"""
from typing import Dict, Optional, List, Tuple
import os
import aiohttp
import json
import re
import base64
import random
from io import BytesIO
from html import unescape
from dotenv import load_dotenv

load_dotenv()

# LangChain imports - REQUIRED
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Import agent executor - use compatible approach for langchain 1.2.0
create_agent = None
AgentExecutor = None
AgentType = None
USE_CREATE_AGENT = False

try:
    from langchain.agents import create_agent
    from langchain.agents import AgentType
    USE_CREATE_AGENT = True
    # Try to import AgentExecutor from various locations
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
    """LangChain-based AI post generation with web search - Handles content, images, ideas, and URL extraction"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        # Initialize LangChain - REQUIRED
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.gemini_api_key,
            temperature=0.8,  # Higher for more creative, personal content
        )
        self.tools = self._create_tools()
        self.agent = self._create_agent()
        
        # Image generation settings
        self.image_model = "gemini-3-pro-image-preview"
        self.image_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.image_model}:generateContent"
        self.tmpfiles_api_url = "https://tmpfiles.org/api/v1/upload"
        
        # Agent can be None if LangChain setup fails - will use fallback in generate_post
    
    def _create_tools(self):
        """Create LangChain tools for web search"""
        # Store reference to self for async call
        self_ref = self
        
        def web_search_sync(query: str) -> str:
            """Sync wrapper for web search - LangChain tools need sync functions"""
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
                description="Search the web for real-time, current information about topics, companies, products, or trends. Always use this to get factual, up-to-date information with sources.",
                func=web_search_sync
            )
        ]
    
    async def _web_search_async(self, query: str) -> str:
        """Async web search using Gemini's googleSearch tool"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": f"Search web for: {query}. Return factual, current information with sources."}]
                    }],
                    "tools": [{"googleSearch": {}}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1024,
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
                # Use create_agent for langchain 1.2.0+
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are an expert LinkedIn content creator who writes PERSONAL, EXPERIENCE-DRIVEN posts. Generate LinkedIn posts directly - NO INTRODUCTORY TEXT, NO META-COMMENTARY.

CRITICAL RULES:
- DO NOT write "Here's a LinkedIn post..." or "Here's a draft..." or any similar meta-commentary
- DO NOT explain what you're creating or describe the post
- START IMMEDIATELY with the actual post content (hook, first sentence, etc.)
- Write as if you're posting directly on LinkedIn
- DO NOT mention dates, years, or time-specific references

CONTENT STYLE (PERSONAL & EXPERIENCE-DRIVEN):
- Write from FIRST-PERSON perspective ("I spent...", "I learned...", "I built...")
- Share PERSONAL EXPERIENCES and REAL LESSONS LEARNED
- Make it ACTIONABLE and EXPERIENCE-DRIVEN, not theoretical
- Use SHORT PARAGRAPHS or bullet points for easy skimming
- Professional, confident, and insightful tone
- End with a thoughtful question to encourage engagement
- Use emojis ONLY where they improve clarity (no overuse)

CONTENT GUIDELINES:
- Always use web_search tool to get current, factual, and technical information
- Include sources and links in markdown format: [Source Name](URL)
- Write in a professional yet conversational tone
- Focus on actionable insights from real experience
- Use code formatting (`backticks`) for technical terms, tools, or technologies
- Start directly with the post content, no introductions
- Share specific examples, numbers, tools, or frameworks you've used"""),
                    ("human", "{input}"),
                ])
                
                agent = create_agent(self.llm, self.tools, prompt)
                # For langchain 1.2.0, create_agent returns an agent executor directly
                if hasattr(agent, 'ainvoke'):
                    return agent
                # Otherwise wrap it
                if AgentExecutor:
                    return AgentExecutor(agent=agent, tools=self.tools, verbose=False, max_iterations=3)
                return agent
            else:
                # Fallback: use initialize_agent
                from langchain.agents import initialize_agent, AgentType
                return initialize_agent(
                    self.tools,
                    self.llm,
                    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    verbose=False,
                    max_iterations=3
                )
        except Exception as e:
            # Final fallback: use simple agent without tools
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
                # Last resort: return None and handle in generate_post
                return None
    
    async def generate_post(self, topic: str, language: str = "en") -> Dict:
        """Generate LinkedIn post using LangChain agent with web search"""
        try:
            language_map = {
                'en': 'English', 'fr': 'French', 'es': 'Spanish', 'it': 'Italian',
                'de': 'German', 'pt': 'Portuguese', 'nl': 'Dutch',
            }
            language_name = language_map.get(language, 'English')
            
            # Use LangChain agent if available
            if self.agent:
                return await self._generate_with_langchain(topic, language_name)
            else:
                # Fallback to direct API if agent not available
                return await self._generate_direct_fallback(topic, language_name)
        except Exception as e:
            import traceback
            return {
                "success": False,
                "content": "",
                "error": f"{str(e)}\n{traceback.format_exc()}"
            }
    
    async def _generate_direct_fallback(self, topic: str, language_name: str) -> Dict:
        """Fallback: Direct API generation when LangChain agent unavailable"""
        prompt = f"""You are an expert LinkedIn content creator who writes PERSONAL, EXPERIENCE-DRIVEN posts. Generate a LinkedIn post directly - NO INTRODUCTORY TEXT, NO META-COMMENTARY.

🚨 CRITICAL: START DIRECTLY WITH THE POST CONTENT 🚨
- DO NOT write "Here's a LinkedIn post..." or "Here's a draft..." or any similar meta-commentary
- DO NOT explain what you're creating or describe the post
- START IMMEDIATELY with the actual post content (hook, first sentence, etc.)
- Write as if you're posting directly on LinkedIn
- DO NOT mention dates, years, or time-specific references

TOPIC: "{topic}"
LANGUAGE: {language_name}

CONTENT STYLE (PERSONAL & EXPERIENCE-DRIVEN):
- Write from FIRST-PERSON perspective ("I spent...", "I learned...", "I built...")
- Share PERSONAL EXPERIENCES and REAL LESSONS LEARNED about "{topic}"
- Make it ACTIONABLE and EXPERIENCE-DRIVEN, not theoretical
- Use SHORT PARAGRAPHS or bullet points for easy skimming
- Professional, confident, and insightful tone
- End with a thoughtful question to encourage engagement
- Use emojis ONLY where they improve clarity (no overuse or decoration)

CONTENT REQUIREMENTS:
- Use googleSearch tool to find REAL, CURRENT information about "{topic}"
- Share 3-5 practical key learnings from your experience
- Include specific examples, tools, frameworks, or numbers you've used
- Use markdown formatting: **bold**, *italics*, [links](URL), `code` for technical terms
- Include 3-5 relevant hashtags
- Write 200-300 words
- Start with a personal hook (e.g., "I spent...", "I learned...")
- End with a thoughtful question
- Include real sources in markdown: [Source](URL)
- Focus on actionable insights from real experience"""
        
        async with aiohttp.ClientSession() as session:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "tools": [{"googleSearch": {}}],
                "generationConfig": {
                    "temperature": 0.8,
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
                        # Remove any meta-commentary
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
    
    async def _generate_with_langchain(self, topic: str, language_name: str) -> Dict:
        """Generate post using LangChain agent"""
        try:
            import random
            
            # Add variety to prompts
            hooks = [
                "Start with a surprising statistic or fact",
                "Begin with a thought-provoking question",
                "Open with a bold statement or prediction",
                "Start with a personal story or anecdote",
                "Begin with a controversial opinion",
                "Open with a comparison or analogy"
            ]
            
            structures = [
                "Problem-Solution format",
                "Storytelling with beginning, middle, and end",
                "List format with actionable insights",
                "Case study format",
                "Before-After comparison",
                "Step-by-step guide format"
            ]
            
            ctas = [
                "End with a question that encourages discussion",
                "End with a call-to-action to share experiences",
                "End with a challenge for readers",
                "End with a request for opinions",
                "End with a thought-provoking statement",
                "End with an invitation to connect"
            ]
            
            selected_hook = random.choice(hooks)
            selected_structure = random.choice(structures)
            selected_cta = random.choice(ctas)
            
            input_text = f"""You are an expert LinkedIn content creator who writes PERSONAL, EXPERIENCE-DRIVEN posts. Generate a LinkedIn post directly - NO INTRODUCTORY TEXT, NO META-COMMENTARY.

TOPIC: "{topic}"
LANGUAGE: {language_name}

🚨 CRITICAL: START DIRECTLY WITH THE POST CONTENT 🚨
- DO NOT write "Here's a LinkedIn post..." or "Here's a draft..." or any similar meta-commentary
- DO NOT explain what you're creating or describe the post
- START IMMEDIATELY with the actual post content (hook, first sentence, etc.)
- Write as if you're posting directly on LinkedIn
- DO NOT mention dates, years, or time-specific references

🎯 CONTENT STYLE (PERSONAL & EXPERIENCE-DRIVEN):
- Write from FIRST-PERSON perspective ("I spent...", "I learned...", "I built...")
- Share PERSONAL EXPERIENCES and REAL LESSONS LEARNED about "{topic}"
- Make it ACTIONABLE and EXPERIENCE-DRIVEN, not theoretical
- Use SHORT PARAGRAPHS or bullet points for easy skimming
- Professional, confident, and insightful tone
- End with a thoughtful question to encourage engagement
- Use emojis ONLY where they improve clarity (no overuse or decoration)

📝 CONTENT GENERATION INSTRUCTIONS:

1. **ALWAYS USE WEB SEARCH FIRST**: Use web_search tool to find REAL, CURRENT information about "{topic}"
   - Search for latest trends, tools, frameworks, or best practices
   - Find actual examples, case studies, or real-world applications
   - Get specific data, statistics, or technical details
   - Use this information to inform your personal experience narrative

2. **SHARE 3-5 PRACTICAL KEY LEARNINGS**:
   - Each learning should be from YOUR experience
   - Start each with a personal statement (e.g., "I learned...", "We discovered...", "The biggest surprise was...")
   - Include specific examples, tools, numbers, or frameworks
   - Make each learning actionable and practical
   - Use {selected_structure} to organize your content

3. **PERSONAL EXPERIENCE FOCUS**:
   - Write as if you've actually worked with "{topic}"
   - Share what surprised you (positive or negative)
   - Include specific challenges you faced and how you solved them
   - Mention real tools, frameworks, or technologies you used
   - Be honest about failures and what you learned from them

4. **FORMATTING REQUIREMENTS**:
   - Use **bold** for key points and important concepts
   - Use *italics* for emphasis or quotes
   - Use bullet points (- or *) for lists and learnings
   - Use SHORT PARAGRAPHS (2-3 sentences max) for easy skimming
   - Include [source links](URL) in markdown format for facts/claims
   - Use code formatting (`backticks`) for technical terms, tools, or technologies

5. **ENGAGEMENT ELEMENTS**:
   - Start with a personal hook (e.g., "I spent...", "I learned...", "Here's what nobody tells you...")
   - Include 2-3 emojis ONLY where they improve clarity (no decoration)
   - Add 3-5 relevant hashtags at the end
   - Write 200-300 words (optimal LinkedIn length)
   - End with a thoughtful question (e.g., "What's been your biggest surprise...?", "What tools do you recommend...?")

6. **LANGUAGE REQUIREMENT**:
   - Write ENTIRELY in {language_name} - no English, no code-switching
   - Use natural {language_name} expressions and idioms
   - Hashtags should be in {language_name} or universal format

7. **VERIFICATION**:
   - ✓ Written in FIRST-PERSON perspective
   - ✓ Shares personal experiences and real lessons learned
   - ✓ Includes 3-5 practical, actionable learnings
   - ✓ Uses short paragraphs or bullet points
   - ✓ Professional, confident, and insightful tone
   - ✓ Ends with thoughtful question
   - ✓ Emojis used only for clarity, not decoration
   - ✓ Written entirely in {language_name}
   - ✓ No dates, years, or time-specific references

🚨 OUTPUT FORMAT - CRITICAL 🚨
- START DIRECTLY with the post content (first sentence/hook)
- DO NOT write "Here's a LinkedIn post..." or "Here's a draft..." or any meta-commentary
- DO NOT explain what you're creating or describe the post
- Write as if you're posting directly on LinkedIn
- The first word should be the actual post content, not an introduction

Generate a PERSONAL, EXPERIENCE-DRIVEN LinkedIn post about "{topic}" in {language_name}. Share 3-5 practical key learnings from your experience. Start directly with the post content - no introductions or meta-commentary."""
            
            result = await self.agent.ainvoke({"input": input_text})
            content = result.get("output", "")
            
            # Remove any meta-commentary that might have slipped through
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
                "error": f"LangChain generation failed: {str(e)}\n{traceback.format_exc()}"
            }
    
    def _remove_meta_commentary(self, text: str) -> str:
        """Remove meta-commentary like 'Here's a LinkedIn post...' from generated content"""
        import re
        
        # Patterns to remove
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
        
        # Remove lines that are just meta-commentary
        lines = text.split('\n')
        cleaned_lines = []
        skip_next = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            # Skip lines that are clearly meta-commentary
            if any(phrase in line_lower for phrase in [
                "here's a linkedin",
                "here is a linkedin",
                "this is a linkedin",
                "linkedin post draft",
                "designed to be",
                "optimized for",
                "incorporating real-world",
                "below is",
                "following is"
            ]):
                continue
            
            # If we find the actual content (starts with a hook-like pattern), keep everything from here
            if line.strip() and not line.strip().startswith(('Here', 'This', 'Below', 'Following')):
                cleaned_lines.append(line)
            elif line.strip():
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
