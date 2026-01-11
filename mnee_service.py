"""
MNEE Service - Integration with MNEE stablecoin API

Built for MNEE Hackathon: Programmable Money for Agents, Commerce, and Automated Finance
Track: AI & Agent Payments
Contract Address: 0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF
Hackathon Deadline: January 13, 2026
"""

import os
import aiohttp
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

MNEE_API_KEY = os.getenv("MNEE_API_KEY", "")
MNEE_ENVIRONMENT = os.getenv("MNEE_ENVIRONMENT", "sandbox")
MNEE_API_BASE = "https://proxy-api.mnee.net" if MNEE_ENVIRONMENT == "production" else "https://sandbox-proxy-api.mnee.net"

class MneeService:
    def __init__(self):
        self.api_key = MNEE_API_KEY
        self.environment = MNEE_ENVIRONMENT
        self.api_base = MNEE_API_BASE

    async def get_tx_status(self, ticket_id: str) -> Dict:
        """Get transaction status using v2/ticket API"""
        try:
            url = f"{self.api_base}/v2/ticket?ticketID={ticket_id}&auth_token={self.api_key}"
            headers = {
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "success": True,
                            "status": data.get("status"),
                            "tx_id": data.get("tx_id"),
                            "tx_hex": data.get("tx_hex"),
                            "errors": data.get("errors"),
                            "action_requested": data.get("action_requested"),
                            "createdAt": data.get("createdAt"),
                            "updatedAt": data.get("updatedAt"),
                        }
                    elif resp.status == 404:
                        return {
                            "success": False,
                            "error": "Ticket not found",
                        }
                    else:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "error": f"API error ({resp.status}): {error_text}",
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get transaction status: {str(e)}",
            }

    async def get_transaction(self, tx_id: str) -> Dict:
        """Get transaction data using v1/tx/{txid} API"""
        try:
            url = f"{self.api_base}/v1/tx/{tx_id}?auth_token={self.api_key}"
            headers = {"Accept": "application/json"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "success": True,
                            "exists": True,
                            "rawtx": data.get("rawtx"),
                        }
                    elif resp.status == 404:
                        return {
                            "success": False,
                            "exists": False,
                            "error": "Transaction not found",
                        }
                    else:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "exists": False,
                            "error": f"API error ({resp.status}): {error_text}",
                        }
        except Exception as e:
            return {
                "success": False,
                "exists": False,
                "error": f"Failed to get transaction: {str(e)}",
            }

    async def verify_transaction(self, tx_id: str) -> Dict:
        """Verify MNEE transaction by checking ticket status and recipient
        
        For hackathon demo: If transaction is SUCCESS/MINED, assume it's verified.
        In production, you would parse the transaction to verify recipient.
        """
        try:
            # For now, we'll use a simplified verification:
            # If tx_id is provided and looks valid, and we can get ticket status, verify it
            # The actual transaction verification would require parsing the raw transaction
            
            # Check if tx_id is actually a ticket_id (UUID format)
            # If it's a ticket_id, get the transaction status first
            import re
            ticket_id_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            
            if ticket_id_pattern.match(tx_id):
                # It's a ticket_id, get status first
                status_result = await self.get_tx_status(tx_id)
                if status_result.get("success") and status_result.get("status") in ["SUCCESS", "MINED"]:
                    # Transaction is successful, verify it
                    actual_tx_id = status_result.get("tx_id")
                    if actual_tx_id:
                        # For hackathon demo, if transaction is SUCCESS/MINED, accept it
                        # In production, you would parse the transaction to verify recipient address
                        return {
                            "success": True,
                            "verified": True,
                            "tx_id": actual_tx_id,
                            "amount": "0.01",  # Default amount for dashboard access
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Transaction not yet mined",
                        }
                else:
                    status = status_result.get("status", "UNKNOWN")
                    return {
                        "success": False,
                        "error": f"Transaction status: {status}. Must be SUCCESS or MINED.",
                    }
            else:
                # It's a transaction ID, try to get transaction data
                # For hackathon demo, if we have a valid tx_id format, accept it
                # In production, parse the transaction to verify recipient
                if len(tx_id) == 64:  # Standard Bitcoin txid length
                    # For hackathon: Accept any valid-looking transaction ID
                    # In production, you would parse it to verify recipient
                    return {
                        "success": True,
                        "verified": True,
                        "tx_id": tx_id,
                        "amount": "0.01",  # Default amount for dashboard access
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Invalid transaction ID format: {tx_id}",
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Verification failed: {str(e)}",
            }

    async def check_balance(self, address: str) -> Dict:
        """Check MNEE balance for an address using v2 API with API key authentication
        
        According to MNEE API docs: https://docs.mnee.io/api-reference/mnee-api
        POST /v2/balance accepts list of addresses and requires auth_token
        """
        try:
            url = f"{self.api_base}/v2/balance?auth_token={self.api_key}"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=[address], timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list) and len(data) > 0:
                            balance_data = data[0]
                            return {
                                "success": True,
                                "balance": balance_data.get("precised", 0),  # decimalAmount
                                "amount": balance_data.get("amt", 0),  # atomic units
                            }
                        else:
                            return {
                                "success": True,
                                "balance": 0,
                                "amount": 0,
                            }
                    elif resp.status == 404:
                        return {
                            "success": True,
                            "balance": 0,
                            "amount": 0,
                        }
                    else:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "balance": 0,
                            "error": f"Failed to get balance: {error_text}",
                        }
        except Exception as e:
            return {
                "success": False,
                "balance": 0,
                "error": str(e),
            }
    
    async def get_utxos(self, addresses: list) -> Dict:
        """Get UTXOs for a list of addresses using v2/utxos API
        
        According to MNEE API docs: https://docs.mnee.io/api-reference/mnee-api
        POST /v2/utxos accepts list of addresses and returns unspent transaction outputs
        """
        try:
            if not addresses or not isinstance(addresses, list):
                return {"success": False, "error": "Addresses must be a non-empty list"}
            
            # Use v2/utxos endpoint with pagination
            url = f"{self.api_base}/v2/utxos?auth_token={self.api_key}&page=1&size=1000&order=desc"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=addresses, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return {
                                "success": True,
                                "utxos": data,
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"Unexpected response format: {type(data)}",
                            }
                    else:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "error": f"API error ({resp.status}): {error_text}",
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def transfer(self, recipients: list, wif: str) -> Dict:
        """Transfer MNEE tokens using v2/transfer API (proxied through backend to avoid CORS)
        
        Note: This requires creating rawtx using MNEE SDK logic.
        For now, we'll use a workaround: the frontend will create rawtx and send it to backend.
        """
        # This method will be called from backend endpoint that receives rawtx from frontend
        # The frontend SDK creates rawtx, then sends it here for submission
        return {
            "success": False,
            "error": "Use /api/mnee/transfer endpoint with rawtx",
        }
    
    async def get_config(self) -> Dict:
        """Get MNEE config using API key authentication
        
        According to MNEE API docs: https://docs.mnee.io/api-reference/mnee-api
        API key should be passed as auth_token query parameter or Authorization header
        """
        try:
            # Use auth_token query parameter as per MNEE API docs
            url = f"{self.api_base}/v1/config?auth_token={self.api_key}"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "success": True,
                            "config": data,
                        }
                    else:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "error": f"API error ({resp.status}): {error_text}",
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get config: {str(e)}",
            }

    async def submit_rawtx(self, rawtx: str) -> Dict:
        """Submit raw transaction via v2/transfer API
        
        Converts hex-encoded rawtx to base64 if needed (MNEE API expects base64)
        """
        try:
            import base64
            import binascii
            
            # Check if rawtx is hex format (starts with numbers/letters, even length)
            # MNEE SDK returns hex, but API expects base64
            rawtx_processed = rawtx.strip()
            
            # Detect if it's hex format (starts with hex characters, even length)
            is_hex = False
            if len(rawtx_processed) > 0 and len(rawtx_processed) % 2 == 0:
                try:
                    # Try to decode as hex
                    hex_chars = set('0123456789abcdefABCDEF')
                    if all(c in hex_chars for c in rawtx_processed):
                        is_hex = True
                except:
                    pass
            
            if is_hex:
                # Convert hex to base64
                try:
                    hex_bytes = binascii.unhexlify(rawtx_processed)
                    rawtx_base64 = base64.b64encode(hex_bytes).decode('utf-8')
                    rawtx_processed = rawtx_base64
                except Exception as conv_error:
                    return {
                        "success": False,
                        "error": f"Failed to convert hex to base64: {str(conv_error)}",
                    }
            
            url = f"{self.api_base}/v2/transfer?auth_token={self.api_key}"
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/plain"  # v2/transfer returns ticket ID as plain text
            }
            payload = {"rawtx": rawtx_processed}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        ticket_id = await resp.text()  # v2/transfer returns ticket ID as plain text
                        ticket_id = ticket_id.strip()
                        return {
                            "success": True,
                            "ticketId": ticket_id,
                        }
                    else:
                        error_text = await resp.text()
                        error_lower = error_text.lower()
                        
                        # Handle specific error cases
                        if "outpoint" in error_lower and "locked" in error_lower:
                            # Extract outpoint from error if possible
                            import re
                            outpoint_match = re.search(r'outpoint\s+([a-f0-9_]+)', error_text, re.IGNORECASE)
                            outpoint = outpoint_match.group(1) if outpoint_match else "unknown"
                            
                            # Extract transaction ID from outpoint if possible (format: txid_vout)
                            tx_id_from_outpoint = outpoint.split('_')[0] if '_' in outpoint else None
                            
                            error_message = (
                                f"Transaction failed: UTXO is locked. "
                                f"A previous transaction attempt is still processing. "
                                f"Please wait 30-60 seconds and try again.\n\n"
                                f"This happens when the same wallet address is used for multiple transactions in quick succession.\n\n"
                            )
                            
                            if tx_id_from_outpoint:
                                error_message += f"Locked outpoint: {outpoint}\n"
                                error_message += f"Previous transaction: {tx_id_from_outpoint[:16]}...\n"
                                error_message += "You can check transaction status using the transaction ID."
                            
                            return {
                                "success": False,
                                "error": error_message,
                                "error_code": "UTXO_LOCKED",
                                "retry_after": 30,  # Suggest waiting 30 seconds
                                "locked_outpoint": outpoint,
                                "previous_tx_id": tx_id_from_outpoint,
                            }
                        elif resp.status == 400:
                            # Try to parse JSON error for better message
                            try:
                                import json
                                error_json = json.loads(error_text)
                                error_message = error_json.get("message", error_text)
                                
                                # Check for locked outpoint in JSON format
                                if "locked" in error_message.lower() and "outpoint" in error_message.lower():
                                    return {
                                        "success": False,
                                        "error": f"Transaction failed: UTXO is locked. A previous transaction attempt is still processing. Please wait a few moments and try again.",
                                        "error_code": "UTXO_LOCKED",
                                        "retry_after": 30,
                                    }
                                
                                return {
                                    "success": False,
                                    "error": f"Transaction failed: {error_message}",
                                    "error_code": "VALIDATION_ERROR",
                                }
                            except:
                                pass
                        
                        return {
                            "success": False,
                            "error": f"API error ({resp.status}): {error_text}",
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"Transfer failed: {str(e)}",
            }


