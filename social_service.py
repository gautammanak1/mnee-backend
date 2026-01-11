import os
import aiohttp
from typing import Dict, Optional
from datetime import datetime, timedelta

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")

TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID", "")
TWITTER_REDIRECT_URI = os.getenv("TWITTER_REDIRECT_URI", "")

class SocialService:
    def __init__(self, supabase_client=None):
        self.supabase_client = supabase_client

    async def send_whatsapp_message(self, to: str, text: str) -> Dict:
        """Send WhatsApp message"""
        if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            return {"error": "WhatsApp credentials not configured"}
        
        try:
            url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": text},
                }
                
                async with session.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        return {"message": f"Message sent to {to}"}
                    else:
                        error_text = await resp.text()
                        return {"error": f"Failed to send WhatsApp message: {error_text}"}
        except Exception as e:
            return {"error": f"Failed to send WhatsApp message: {str(e)}"}

    def get_twitter_auth_url(self) -> Dict:
        """Get Twitter OAuth URL"""
        if not TWITTER_CLIENT_ID or not TWITTER_REDIRECT_URI:
            return {"error": "Twitter credentials not configured"}
        
        scope = "tweet.read tweet.write users.read offline.access"
        state = f"sociantra-twitter-{int(__import__('time').time())}"
        
        auth_url = (
            f"https://twitter.com/i/oauth2/authorize?"
            f"response_type=code&"
            f"client_id={TWITTER_CLIENT_ID}&"
            f"redirect_uri={TWITTER_REDIRECT_URI}&"
            f"scope={scope}&"
            f"state={state}&"
            f"code_challenge=challenge&"
            f"code_challenge_method=plain"
        )
        
        return {"auth_url": auth_url}

    async def handle_twitter_callback(self, code: str, user_id: str = None) -> Dict:
        """Handle Twitter OAuth callback"""
        if not TWITTER_CLIENT_ID or not TWITTER_REDIRECT_URI:
            return {"error": "Twitter credentials not configured"}
        
        try:
            async with aiohttp.ClientSession() as session:
                token_data = {
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": TWITTER_REDIRECT_URI,
                    "client_id": TWITTER_CLIENT_ID,
                    "code_verifier": "challenge",
                }
                
                async with session.post(
                    "https://api.twitter.com/2/oauth2/token",
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {"error": f"Twitter auth failed: {error_text}"}
                    
                    token_response = await resp.json()
                    access_token = token_response.get("access_token")
                    refresh_token = token_response.get("refresh_token")
                    expires_in = token_response.get("expires_in", 7200)
                    expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
                    
                    # Save to Supabase if user_id provided
                    if user_id and self.supabase_client:
                        try:
                            account_data = {
                                "user_id": user_id,
                                "platform": "twitter",
                                "access_token": access_token,
                                "refresh_token": refresh_token,
                                "expires_at": expires_at,
                            }
                            
                            # Check if account exists
                            existing = self.supabase_client.table("social_accounts").select("*").eq("user_id", user_id).eq("platform", "twitter").execute()
                            
                            if existing.data:
                                # Update existing
                                self.supabase_client.table("social_accounts").update(account_data).eq("user_id", user_id).eq("platform", "twitter").execute()
                            else:
                                # Insert new
                                self.supabase_client.table("social_accounts").insert(account_data).execute()
                        except Exception:
                            pass
                    
                    return {
                        "message": "Twitter connected successfully",
                        "expires_at": expires_at,
                    }
        except Exception as e:
            return {"error": f"Twitter auth failed: {str(e)}"}
