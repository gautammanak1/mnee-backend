"""Slack bot commands handler"""
import os
import aiohttp
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class SlackBot:
    """Handles Slack bot commands and interactions"""
    
    def __init__(self, slack_service, ai_service, linkedin_service, payment_service, scheduler_service, supabase_admin):
        self.slack_service = slack_service
        self.ai_service = ai_service
        self.linkedin_service = linkedin_service
        self.payment_service = payment_service
        self.scheduler_service = scheduler_service
        self.supabase_admin = supabase_admin
    
    async def handle_command(self, command: str, text: str, user_id: str, channel: str, team_id: str) -> Dict:
        """Handle Slack slash commands"""
        try:
            if command == "/create-post":
                return await self._handle_create_post(text, user_id, channel, team_id)
            elif command == "/ai-generate":
                return await self._handle_ai_generate(text, user_id, channel, team_id)
            elif command == "/url-to-post":
                return await self._handle_url_to_post(text, user_id, channel, team_id)
            elif command == "/idea-generate":
                return await self._handle_idea_generate(text, user_id, channel, team_id)
            else:
                return {"error": f"Unknown command: {command}"}
        except Exception as e:
            return {"error": f"Command failed: {str(e)}"}
    
    async def _handle_create_post(self, text: str, user_id: str, channel: str, team_id: str) -> Dict:
        """Handle /create-post command"""
        if not text or not text.strip():
            return {
                "response_type": "ephemeral",
                "text": "Usage: /create-post <post content>\nExample: /create-post Hello LinkedIn!"
            }
        
        # Check payment
        payment_status = await self.payment_service.check_user_payment_status(user_id, "linkedin_post")
        if not payment_status.get("has_paid"):
            payment_msg = (
                "⚠️ Payment required!\n"
                "Please make a payment of 0.01 MNEE to create LinkedIn posts.\n"
                "Visit your dashboard to complete payment."
            )
            return {"text": payment_msg, "response_type": "ephemeral"}
        
        # Post to LinkedIn
        result = await self.linkedin_service.post_text(user_id, text)
        
        if result.get("error"):
            return {
                "text": f"❌ Failed to create post: {result.get('error')}",
                "response_type": "ephemeral"
            }
        
        post_url = result.get("post_url", "")
        return {
            "text": f"✅ Post created successfully!\n{post_url if post_url else 'Check LinkedIn for your post.'}",
            "response_type": "in_channel"
        }
    
    async def _handle_ai_generate(self, text: str, user_id: str, channel: str, team_id: str) -> Dict:
        """Handle /ai-generate command"""
        if not text or not text.strip():
            return {
                "response_type": "ephemeral",
                "text": "Usage: /ai-generate <topic>\nExample: /ai-generate AI agents in 2024"
            }
        
        topic = text.strip()
        
        # Check payment
        payment_status = await self.payment_service.check_user_payment_status(user_id, "ai_generate_post")
        if not payment_status.get("has_paid"):
            payment_msg = (
                "⚠️ Payment required!\n"
                "Please make a payment of 0.01 MNEE to use AI generation.\n"
                "Visit your dashboard to complete payment."
            )
            return {"text": payment_msg, "response_type": "ephemeral"}
        
        # Generate post
        result = await self.ai_service.generate_linkedin_post(topic, False, "en")
        
        if result.get("has_error") or result.get("error"):
            error_msg = result.get("error", "Failed to generate post")
            return {
                "text": f"❌ Generation failed: {error_msg}",
                "response_type": "ephemeral"
            }
        
        post_text = result.get("text", "")
        hashtags = result.get("hashtags", [])
        
        if hashtags:
            post_text += "\n\n" + " ".join(hashtags)
        
        return {
            "text": f"🤖 AI Generated Post:\n\n{post_text}",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*AI Generated Post:*\n\n{post_text}"
                    }
                }
            ]
        }
    
    async def _handle_url_to_post(self, text: str, user_id: str, channel: str, team_id: str) -> Dict:
        """Handle /url-to-post command"""
        if not text or not text.strip():
            return {
                "response_type": "ephemeral",
                "text": "Usage: /url-to-post <URL>\nExample: /url-to-post https://example.com/article"
            }
        
        url = text.strip()
        
        # Check payment
        payment_status = await self.payment_service.check_user_payment_status(user_id, "url_to_post")
        if not payment_status.get("has_paid"):
            payment_msg = (
                "⚠️ Payment required!\n"
                "Please make a payment of 0.01 MNEE to convert URLs to posts.\n"
                "Visit your dashboard to complete payment."
            )
            return {"text": payment_msg, "response_type": "ephemeral"}
        
        # Convert URL to post
        result = await self.ai_service.extract_and_convert_url_to_post(url, False, "en")
        
        if result.get("error"):
            return {
                "text": f"❌ Failed to convert URL: {result.get('error')}",
                "response_type": "ephemeral"
            }
        
        post_text = result.get("text", "")
        hashtags = result.get("hashtags", [])
        
        if hashtags:
            post_text += "\n\n" + " ".join(hashtags)
        
        return {
            "text": f"🔗 Post from URL:\n\n{post_text}",
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Post from URL:*\n\n{post_text}"
                    }
                }
            ]
        }
    
    async def _handle_idea_generate(self, text: str, user_id: str, channel: str, team_id: str) -> Dict:
        """Handle /idea-generate command"""
        # Idea generation is free, no payment check needed
        
        # Generate ideas
        result = await self.ai_service.generate_post_ideas(
            topic=text if text.strip() else "LinkedIn content",
            count=5
        )
        
        if result.get("has_error") or result.get("error"):
            error_msg = result.get("error", "Failed to generate ideas")
            return {
                "text": f"❌ Generation failed: {error_msg}",
                "response_type": "ephemeral"
            }
        
        ideas = result.get("ideas", []) if isinstance(result.get("ideas"), list) else []
        
        if not ideas:
            return {
                "text": "No ideas generated. Please try again.",
                "response_type": "ephemeral"
            }
        
        ideas_text = "\n".join([f"{i+1}. {idea}" for i, idea in enumerate(ideas[:5])])
        
        return {
            "text": f"💡 Content Ideas:\n\n{ideas_text}",
            "response_type": "ephemeral"
        }
    
    async def send_scheduled_post_notification(self, user_id: str, schedule_id: str, review_link: str, team_id: Optional[str] = None) -> Dict:
        """Send notification about scheduled post requiring review"""
        message = (
            f"📅 *New Scheduled Post Ready for Review*\n\n"
            f"Schedule ID: `{schedule_id}`\n"
            f"Review Link: {review_link}\n\n"
            f"Click the link above to review and approve the post."
        )
        
        return await self.slack_service.send_notification(user_id, message, team_id)
    
    async def send_payment_notification(self, user_id: str, amount: str, service: str, tx_hash: str, team_id: Optional[str] = None) -> Dict:
        """Send payment notification"""
        message = (
            f"💳 *Payment Successful*\n\n"
            f"Amount: {amount} MNEE\n"
            f"Service: {service}\n"
            f"Transaction: `{tx_hash}`\n\n"
            f"You can now use the service!"
        )
        
        return await self.slack_service.send_notification(user_id, message, team_id)

