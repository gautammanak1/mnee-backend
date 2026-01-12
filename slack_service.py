"""Slack integration service for OAuth and bot functionality"""
# NOTE: Slack functionality is currently disabled/coming soon
# This file is kept for future implementation
import os
import aiohttp
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# Slack environment variables (commented out - not in use)
# SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID", "")
# SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET", "")
# SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI", "")
# SLACK_SCOPES = os.getenv("SLACK_SCOPES", "")
# SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
# SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
# SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")
# SLACK_VERIFICATION_TOKEN = os.getenv("SLACK_VERIFICATION_TOKEN", "")
# SLACK_TEAM_ID = os.getenv("SLACK_TEAM_ID", "")


class SlackService:
    """Handles Slack OAuth and bot interactions"""
    
    def __init__(self, supabase_client=None, supabase_admin=None):
        self.supabase_client = supabase_client
        self.supabase_admin = supabase_admin or supabase_client
        # Slack functionality disabled - returning empty/default values
        self.client_id = os.getenv("SLACK_CLIENT_ID", "")
        self.client_secret = os.getenv("SLACK_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("SLACK_REDIRECT_URI", "")
        self.scopes = os.getenv("SLACK_SCOPES", "")
        self.bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        self.signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
        self.app_token = os.getenv("SLACK_APP_TOKEN", "")
        self.verification_token = os.getenv("SLACK_VERIFICATION_TOKEN", "")
        self.team_id = os.getenv("SLACK_TEAM_ID", "")
    
    def generate_auth_url(self, user_id: str, team_id: Optional[str] = None) -> Dict:
        """Generate Slack OAuth URL
        
        Note: redirect_uri must match exactly what's configured in Slack App Management.
        For local development, use ngrok or similar HTTPS tunnel.
        
        Args:
            user_id: User ID for state parameter
            team_id: Optional Slack workspace team ID to ensure installation on correct workspace
                     If not provided, uses SLACK_TEAM_ID from environment
        """
        if not self.redirect_uri:
            return {"error": "SLACK_REDIRECT_URI not configured. Please set it in environment variables."}
        
        state = f"slack-{user_id}-{int(datetime.now().timestamp())}"
        
        # URL encode the redirect_uri
        from urllib.parse import quote_plus
        encoded_redirect_uri = quote_plus(self.redirect_uri)
        
        # Use provided team_id or fall back to environment variable
        final_team_id = team_id or self.team_id
        
        # Build OAuth URL with proper encoding
        auth_url = (
            f"https://slack.com/oauth/v2/authorize?"
            f"client_id={self.client_id}&"
            f"scope={self.scopes}&"
            f"redirect_uri={encoded_redirect_uri}&"
            f"state={state}"
        )
        
        # Add team parameter if available (forces correct workspace for non-distributed apps)
        # URL encode the team ID as well
        if final_team_id:
            encoded_team_id = quote_plus(final_team_id)
            auth_url += f"&team={encoded_team_id}"
        
        return {"auth_url": auth_url}
    
    async def handle_callback(self, code: str, state: str) -> Dict:
        """Exchange authorization code for access token"""
        try:
            # Extract user_id from state
            # State format: slack-{uuid}-{timestamp}
            state_parts = state.split('-')
            if len(state_parts) < 3:
                return {"error": "Invalid state parameter format"}
            
            uuid_parts = state_parts[1:-1]  # Skip "slack" and timestamp
            user_id = '-'.join(uuid_parts)  # Rejoin UUID parts
            
            if not user_id or len(user_id) < 30:
                return {"error": "Invalid state parameter - user_id not found"}
            
            # Exchange code for token
            # IMPORTANT: redirect_uri must match exactly what was sent in authorize step
            async with aiohttp.ClientSession() as session:
                token_data = {
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,  # Must match authorize step
                }
                
                async with session.post(
                    "https://slack.com/api/oauth.v2.access",
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {"error": f"Token exchange failed: {error_text}"}
                    
                    token_response = await resp.json()
                    
                    if not token_response.get("ok"):
                        return {"error": token_response.get("error", "Token exchange failed")}
                    
                    access_token = token_response.get("access_token")
                    bot_token = token_response.get("access_token")  # Bot token
                    team_id = token_response.get("team", {}).get("id", "")
                    team_name = token_response.get("team", {}).get("name", "")
                    authed_user = token_response.get("authed_user", {})
                    bot_user_id = token_response.get("bot_user_id", "")
                    
                    # Save to Supabase
                    if self.supabase_admin:
                        try:
                            connection_data = {
                                "user_id": user_id,
                                "team_id": team_id,
                                "team_name": team_name,
                                "bot_token": bot_token,
                                "access_token": access_token,
                                "bot_user_id": bot_user_id,
                                "slack_user_id": authed_user.get("id", ""),
                                "connected_at": datetime.now(timezone.utc).isoformat(),
                            }
                            
                            # Upsert Slack connection
                            existing = self.supabase_admin.table("slack_connections").select("*").eq("user_id", user_id).eq("team_id", team_id).execute()
                            
                            if existing.data and len(existing.data) > 0:
                                result = self.supabase_admin.table("slack_connections").update(connection_data).eq("id", existing.data[0]["id"]).execute()
                            else:
                                result = self.supabase_admin.table("slack_connections").insert(connection_data).execute()
                            
                            if result.data:
                                return {
                                    "success": True,
                                    "team_id": team_id,
                                    "team_name": team_name,
                                    "bot_user_id": bot_user_id,
                                }
                        except Exception as db_error:
                            return {"error": f"Database error: {str(db_error)}"}
                    
                    return {"error": "Database not configured"}
        except Exception as e:
            return {"error": f"Failed to handle callback: {str(e)}"}
    
    async def get_bot_token(self, user_id: str, team_id: Optional[str] = None) -> Optional[str]:
        """Get bot token for user's Slack workspace"""
        if not self.supabase_admin:
            return None
        
        try:
            query = self.supabase_admin.table("slack_connections").select("bot_token").eq("user_id", user_id)
            if team_id:
                query = query.eq("team_id", team_id)
            
            result = query.order("connected_at", desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("bot_token")
            return None
        except Exception:
            return None
    
    async def send_message(self, user_id: str, channel: str, text: str, team_id: Optional[str] = None) -> Dict:
        """Send message to Slack channel"""
        bot_token = await self.get_bot_token(user_id, team_id)
        if not bot_token:
            return {"error": "Slack not connected. Please connect your Slack workspace first."}
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "channel": channel,
                    "text": text,
                }
                
                async with session.post(
                    "https://slack.com/api/chat.postMessage",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {bot_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("ok"):
                            return {"success": True, "ts": result.get("ts")}
                        return {"error": result.get("error", "Failed to send message")}
                    return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def send_notification(self, user_id: str, text: str, team_id: Optional[str] = None) -> Dict:
        """Send notification to user's Slack DM"""
        bot_token = await self.get_bot_token(user_id, team_id)
        if not bot_token:
            return {"error": "Slack not connected"}
        
        try:
            # Get user's Slack user ID
            if not self.supabase_admin:
                return {"error": "Database not configured"}
            
            result = self.supabase_admin.table("slack_connections").select("slack_user_id").eq("user_id", user_id)
            if team_id:
                result = result.eq("team_id", team_id)
            
            conn_result = result.order("connected_at", desc=True).limit(1).execute()
            
            if not conn_result.data or not conn_result.data[0].get("slack_user_id"):
                return {"error": "Slack user ID not found"}
            
            slack_user_id = conn_result.data[0]["slack_user_id"]
            
            # Open DM channel
            async with aiohttp.ClientSession() as session:
                # Open IM channel
                open_payload = {"users": slack_user_id}
                async with session.post(
                    "https://slack.com/api/conversations.open",
                    json=open_payload,
                    headers={
                        "Authorization": f"Bearer {bot_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as open_resp:
                    if open_resp.status == 200:
                        open_result = await open_resp.json()
                        if open_result.get("ok"):
                            channel_id = open_result.get("channel", {}).get("id")
                            if channel_id:
                                return await self.send_message(user_id, channel_id, text, team_id)
                    return {"error": "Failed to open DM channel"}
        except Exception as e:
            return {"error": str(e)}

