"""LangChain integration for AI post generation with tool calling"""
from typing import Dict, Optional
import os
import aiohttp
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
    """LangChain-based AI post generation with web search tool calling"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        # Initialize LangChain - REQUIRED
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.gemini_api_key,
            temperature=0.7,
        )
        self.tools = self._create_tools()
        self.agent = self._create_agent()
        
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
                    ("system", """You are an expert LinkedIn content creator specializing in technical and professional content. Generate LinkedIn posts directly - NO INTRODUCTORY TEXT, NO META-COMMENTARY.

CRITICAL RULES:
- DO NOT write "Here's a LinkedIn post..." or "Here's a draft..." or any similar meta-commentary
- DO NOT explain what you're creating or describe the post
- START IMMEDIATELY with the actual post content (hook, first sentence, etc.)
- Write as if you're posting directly on LinkedIn
- DO NOT mention dates, years, or time-specific references

CONTENT GUIDELINES:
- Always use web_search tool to get current, factual, and technical information
- Include sources and links in markdown format: [Source Name](URL)
- Write in a professional yet engaging tone with technical depth
- Focus on technical insights, professional value, and actionable content
- Use code formatting (`backticks`) for technical terms, tools, or technologies
- Start directly with the post content, no introductions
- Prioritize technical accuracy and professional expertise"""),
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
        prompt = f"""You are an expert LinkedIn content creator specializing in technical and professional content. Generate a LinkedIn post directly - NO INTRODUCTORY TEXT, NO META-COMMENTARY.

🚨 CRITICAL: START DIRECTLY WITH THE POST CONTENT 🚨
- DO NOT write "Here's a LinkedIn post..." or "Here's a draft..." or any similar meta-commentary
- DO NOT explain what you're creating or describe the post
- START IMMEDIATELY with the actual post content (hook, first sentence, etc.)
- Write as if you're posting directly on LinkedIn
- DO NOT mention dates, years, or time-specific references

TOPIC: "{topic}"
LANGUAGE: {language_name}

CONTENT REQUIREMENTS:
- Use googleSearch tool to find REAL, CURRENT, and TECHNICAL information
- Include actual companies, products, technologies, services, or technical facts
- Focus on technical depth and professional insights
- Use markdown formatting: **bold**, *italics*, [links](URL), `code` for technical terms
- Include 3-5 relevant hashtags
- Write 200-300 words
- Start with a hook
- End with a question or call-to-action
- Include real sources in markdown: [Source](URL)
- Prioritize actionable technical content and professional value"""
        
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
            
            input_text = f"""You are an expert LinkedIn content creator specializing in technical and professional content. Generate a LinkedIn post directly - NO INTRODUCTORY TEXT, NO META-COMMENTARY.

TOPIC: "{topic}"
LANGUAGE: {language_name}

🚨 CRITICAL: START DIRECTLY WITH THE POST CONTENT 🚨
- DO NOT write "Here's a LinkedIn post..." or "Here's a draft..." or any similar meta-commentary
- DO NOT explain what you're creating or describe the post
- START IMMEDIATELY with the actual post content (hook, first sentence, etc.)
- Write as if you're posting directly on LinkedIn

🎯 CONTENT GENERATION INSTRUCTIONS:

1. **ALWAYS USE WEB SEARCH FIRST**: Use web_search tool to find REAL, CURRENT, and SPECIFIC information about "{topic}"
   - Search for latest news, trends, companies, products, or technical facts
   - Find actual examples, case studies, or real-world applications
   - Get specific data, statistics, or technical details
   - Find unique angles or perspectives that haven't been covered before
   - Focus on technical depth and professional insights

2. **CONTENT STRUCTURE** (Use this format: {selected_structure}):
   - {selected_hook}
   - Provide unique insights based on web search results
   - Use {selected_structure} to organize your content
   - {selected_cta}

3. **MAKE IT UNIQUE AND TECHNICAL**:
   - Avoid generic advice or common knowledge
   - Use specific examples from web search results
   - Include real company names, products, technologies, or services found in search
   - Add unique perspectives or contrarian viewpoints
   - Include surprising facts, statistics, or technical details from search results
   - Focus on actionable technical insights and professional value

4. **FORMATTING REQUIREMENTS**:
   - Use **bold** for key points and important concepts
   - Use *italics* for emphasis or quotes
   - Use bullet points (- or *) for lists
   - Include [source links](URL) in markdown format for all facts/claims
   - Add line breaks between sections for readability
   - Use code formatting (`backticks`) for technical terms, tools, or technologies

5. **ENGAGEMENT ELEMENTS**:
   - Start with a powerful hook (use {selected_hook})
   - Include 2-3 relevant emojis strategically placed (prefer technical/professional emojis)
   - Add 3-5 relevant hashtags at the end
   - Write 200-300 words (optimal LinkedIn length)
   - End with engagement CTA (use {selected_cta})

6. **LANGUAGE REQUIREMENT**:
   - Write ENTIRELY in {language_name} - no English, no code-switching
   - Use natural {language_name} expressions and idioms
   - Hashtags should be in {language_name} or universal format

7. **TECHNICAL FOCUS**:
   - Prioritize technical depth over surface-level content
   - Include specific technologies, frameworks, tools, or methodologies
   - Provide actionable insights for technical professionals
   - Use professional terminology appropriate for the audience

8. **VERIFICATION**:
   - ✓ Used web_search tool to get real information
   - ✓ Content is unique and not generic
   - ✓ Includes specific examples from search results
   - ✓ All facts have source links
   - ✓ Written entirely in {language_name}
   - ✓ Has proper formatting with **bold** and *italics*
   - ✓ Includes emojis and hashtags
   - ✓ Technical depth and professional value

🚨 OUTPUT FORMAT - CRITICAL 🚨
- START DIRECTLY with the post content (first sentence/hook)
- DO NOT write "Here's a LinkedIn post..." or "Here's a draft..." or "designed to be engaging..." or any meta-commentary
- DO NOT explain what you're creating or describe the post
- Write as if you're posting directly on LinkedIn
- The first word should be the actual post content, not an introduction

Generate a UNIQUE, ENGAGING, TECHNICAL LinkedIn post about "{topic}" in {language_name}. Make it stand out with real information from web search. Start directly with the post content - no introductions or meta-commentary."""
            
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
