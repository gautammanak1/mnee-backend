"""Image generation service using Gemini API directly"""
import os
import base64
import asyncio
import aiohttp
from io import BytesIO
from typing import Optional, Tuple, List, Dict
from uagents import Context
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-3-pro-image-preview"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

TMPFILES_API_URL = "https://tmpfiles.org/api/v1/upload"

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

class ImageGenerator:
    """Handles image generation using Gemini API directly"""
    
    def __init__(self, agent_context: Optional[Context] = None):
        self.gemini_api_key = GEMINI_API_KEY
        self.agent_context = agent_context
        # Keep for backward compatibility
        self.image_generation_agent = None
        self._pending_image_requests = {}
        self._last_image_url = None
    
    async def _generate_image_with_gemini(
        self,
        prompt: str,
        chat_history: Optional[List[Dict]] = None,
        user_images: Optional[List[Tuple[bytes, str]]] = None
    ) -> Tuple[bytes, str]:
        """
        Generate an image using Gemini 3 Pro Image API.
        
        Args:
            prompt: The image generation prompt
            chat_history: Previous conversation history (optional)
            user_images: Optional list of (image_bytes, mime_type) tuples
        
        Returns:
            Tuple of (image_data, content_type)
        """
        try:
            # Build request contents
            contents = []
            if chat_history:
                contents.extend(chat_history)
            
            # Build user message parts
            user_parts = []
            
            # Add user-uploaded images if provided
            if user_images and not chat_history:
                # First message with images: images first, then text
                for image_bytes, mime_type in user_images:
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    user_parts.append({
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_base64
                        }
                    })
                user_parts.append({"text": prompt})
            else:
                # Text first (for generation or subsequent messages)
                user_parts.append({"text": prompt})
                if user_images:
                    # Add images after text for subsequent messages
                    for image_bytes, mime_type in user_images:
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        user_parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_base64
                            }
                        })
            
            # Add current user message
            contents.append({
                "role": "user",
                "parts": user_parts
            })
            
            # Build payload
            payload = {
                "contents": contents
            }
            
            # Add generationConfig only for text-only generation
            if not chat_history and not user_images:
                payload["generationConfig"] = {
                    "imageConfig": {
                        "aspectRatio": "1:1",
                        "imageSize": "2K"
                    }
                }
            
            # Make API request
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.gemini_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Gemini API request failed with status {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    if 'candidates' not in data or not data['candidates']:
                        raise Exception("No candidates in Gemini API response")
                    
                    candidate = data['candidates'][0]
                    content = candidate.get('content', {})
                    
                    # Extract image data
                    image_data = None
                    content_type = 'image/png'
                    
                    for part in content.get('parts', []):
                        inline_data = part.get('inlineData') or part.get('inline_data')
                        if inline_data:
                            base64_data = inline_data.get('data')
                            if base64_data:
                                image_data = base64.b64decode(base64_data)
                                content_type = inline_data.get('mimeType') or inline_data.get('mime_type', 'image/png')
                                break
                    
                    if not image_data:
                        raise Exception("No image data in Gemini API response")
                    
                    return image_data, content_type
                    
        except Exception as e:
            raise Exception(f"Error generating image with Gemini: {e}")
    
    async def _upload_to_tmpfiles(self, image_data: bytes, content_type: str) -> Optional[str]:
        """
        Upload image to tmpfiles.org and return the download URL.
        Files are automatically deleted after 60 minutes.
        """
        # Determine file extension from content type
        ext_map = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/gif": "gif",
            "image/webp": "webp"
        }
        ext = ext_map.get(content_type, "png")
        
        # Retry logic for upload
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=60)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    form_data = aiohttp.FormData()
                    file_obj = BytesIO(image_data)
                    form_data.add_field('file', 
                                      file_obj, 
                                      filename=f"gemini_image.{ext}", 
                                      content_type=content_type)
                    
                    async with session.post(TMPFILES_API_URL, data=form_data) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            # Handle different response formats
                            if isinstance(result, dict):
                                if "status" in result and result.get("status") == "success":
                                    if "data" in result and isinstance(result["data"], dict):
                                        file_url = result["data"].get("url", "")
                                    else:
                                        file_url = result.get("url", "")
                                else:
                                    file_url = result.get("url", "")
                                
                                if file_url:
                                    # Convert to direct download link
                                    download_url = file_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                                    if download_url.startswith("http://"):
                                        download_url = download_url.replace("http://", "https://", 1)
                                    return download_url
                            
                            # If response is a string URL
                            if isinstance(result, str):
                                file_url = result
                                download_url = file_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                                if download_url.startswith("http://"):
                                    download_url = download_url.replace("http://", "https://", 1)
                                return download_url
                        else:
                            error_text = await response.text()
                            raise Exception(f"tmpfiles.org upload failed with status {response.status}: {error_text}")
                            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception(f"Failed to upload to tmpfiles.org after {max_retries} attempts: {str(e)}")
            except Exception as e:
                raise Exception(f"Failed to upload to tmpfiles.org: {str(e)}")
        
        raise Exception(f"Failed to upload to tmpfiles.org after {max_retries} attempts")
    
    async def generate(self, prompt: str, topic: Optional[str] = None, ctx: Optional[Context] = None) -> Optional[str]:
        """
        Generate an image using Gemini API directly and upload to tmpfiles.org.
        Returns the image URL.
        """
        agent_ctx = ctx or self.agent_context
        
        try:
            import random
            import datetime
            
            # Add variety to image generation
            styles = [
                "modern minimalist illustration",
                "professional photography style",
                "abstract geometric design",
                "isometric 3D illustration",
                "flat design with vibrant colors",
                "gradient background with icons",
                "hand-drawn sketch style",
                "corporate infographic style",
                "tech-focused futuristic design",
                "warm and inviting illustration"
            ]
            
            color_schemes = [
                "blue and white professional palette",
                "vibrant gradient with purple and orange",
                "warm earth tones with browns and greens",
                "cool tech colors: cyan and dark blue",
                "bold contrast: black, white, and one accent color",
                "pastel professional palette",
                "dark mode with neon accents",
                "sunset gradient: orange, pink, purple",
                "ocean theme: various shades of blue",
                "forest theme: greens and natural tones"
            ]
            
            compositions = [
                "centered focal point with negative space",
                "split-screen composition",
                "diagonal dynamic layout",
                "rule of thirds composition",
                "symmetrical balanced design",
                "asymmetric modern layout",
                "circular elements with radial design",
                "grid-based structured layout"
            ]
            
            selected_style = random.choice(styles)
            selected_colors = random.choice(color_schemes)
            selected_composition = random.choice(compositions)
            
            # Enhance prompt for better, varied image generation
            enhanced_prompt = prompt
            if topic:
                enhanced_prompt = f"""Create a UNIQUE, professional, high-quality image for a LinkedIn post about "{topic}".

Original prompt: {prompt}

🎨 CREATIVE DIRECTION (Make it UNIQUE):
- Style: {selected_style}
- Color scheme: {selected_colors}
- Composition: {selected_composition}
- Current date: {datetime.datetime.now().strftime('%B %Y')}

📐 TECHNICAL REQUIREMENTS:
- High resolution (2K), crisp and clear visuals
- Professional business aesthetic suitable for LinkedIn
- Modern, clean design with excellent composition
- Visually striking and eye-catching
- Suitable for social media sharing
- High contrast for better visibility on LinkedIn feed
- Engaging and professional appearance
- Avoid cluttered designs - keep it clean and focused
- Unique visual approach that stands out from generic stock images

🚫 AVOID:
- Generic stock photo look
- Overused visual clichés
- Cluttered or busy designs
- Low contrast or hard-to-read elements
- Unprofessional or casual styles

✨ MAKE IT UNIQUE:
- Use creative visual metaphors related to "{topic}"
- Incorporate unique design elements
- Create a memorable visual identity
- Ensure it's different from typical LinkedIn post images"""
            
            # Generate image using Gemini API with enhanced prompt
            image_data, content_type = await self._generate_image_with_gemini(enhanced_prompt)
            
            # Upload to tmpfiles.org
            image_url = await self._upload_to_tmpfiles(image_data, content_type)
            
            if image_url:
                return image_url
            else:
                return None
                
        except Exception as e:
            return None
        
    def handle_response(self, sender: str, msg) -> bool:
        """
        Legacy method for backward compatibility.
        No longer needed since we use Gemini API directly.
        """
        return False
