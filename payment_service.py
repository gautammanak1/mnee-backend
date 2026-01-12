from typing import Dict, Optional
from datetime import datetime, timezone
from supabase import Client
from mnee_service import MneeService
from utils.constants import MNEE_CONTRACT_ADDRESS

# MNEE Hackathon: Programmable Money for Agents, Commerce, and Automated Finance
# This service implements AI & Agent Payments track
# Contract Address: 0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF

class PaymentService:
    def __init__(self, supabase_client: Optional[Client] = None, supabase_admin: Optional[Client] = None):
        self.supabase_client = supabase_client
        self.supabase_admin = supabase_admin or supabase_client
        self.mnee_service = MneeService()
        self.contract_address = MNEE_CONTRACT_ADDRESS  # Contract: 0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF

    async def check_user_payment_status(self, user_id: str, service: str = None) -> Dict:
        """Check if user has made payment for dashboard access or specific service
        
        For hackathon: If service is None, checks for dashboard_access.
        If service is specified, checks for that specific service payment.
        """
        if not self.supabase_admin:
            return {"has_paid": False, "error": "Database not configured"}
        
        try:
            query = self.supabase_admin.table("payments").select("*").eq("user_id", user_id).eq("status", "verified")
            
            # For hackathon demo: If service specified, check for that service OR dashboard_access
            # This allows dashboard payment to grant access to all services
            if service and service != "dashboard_access":
                # Check for either the specific service OR dashboard_access
                result = query.in_("service", [service, "dashboard_access"]).order("created_at", desc=True).limit(1).execute()
            else:
                # Check for dashboard_access or the specified service
                service_to_check = service or "dashboard_access"
                result = query.eq("service", service_to_check).order("created_at", desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                payment = result.data[0]
                return {
                    "has_paid": True,
                    "payment_date": payment.get("created_at"),
                    "tx_hash": payment.get("tx_hash"),
                    "amount": payment.get("amount"),
                    "service": payment.get("service"),
                }
            
            return {"has_paid": False}
        except Exception as e:
            return {"has_paid": False, "error": str(e)}

    async def record_payment(self, user_id: str, tx_hash: str, amount: str, service: str = "dashboard_access") -> Dict:
        """Record a verified payment in database"""
        if not self.supabase_admin:
            return {"success": False, "error": "Database not configured"}
        
        try:
            payment_data = {
                "user_id": user_id,
                "tx_hash": tx_hash,
                "service": service,
                "amount": amount,
                "status": "verified",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            result = self.supabase_admin.table("payments").insert(payment_data).execute()
            
            if result.data and len(result.data) > 0:
                payment_record = result.data[0]
                return {
                    "success": True,
                    "payment_id": payment_record.get("id"),
                    "payment": payment_record  # Return full payment record
                }
            
            # If insert returns no data, check if it's a duplicate (same tx_hash AND service)
            try:
                existing = self.supabase_admin.table("payments").select("*").eq("tx_hash", tx_hash).eq("service", service).execute()
                if existing.data and len(existing.data) > 0:
                    payment_record = existing.data[0]
                    return {
                        "success": True, 
                        "payment_id": payment_record.get("id"),
                        "payment": payment_record,  # Return full payment record
                        "already_exists": True
                    }
            except:
                pass
            
            return {"success": False, "error": "Failed to record payment - no data returned"}
        except Exception as e:
            error_msg = str(e)
            error_lower = error_msg.lower()
            
            # Try to extract error details from exception
            error_code = ""
            error_message = error_msg
            
            # Check if error has dict-like structure in args
            if hasattr(e, 'args') and len(e.args) > 0:
                if isinstance(e.args[0], dict):
                    error_dict = e.args[0]
                    error_code = str(error_dict.get("code", ""))
                    error_message = error_dict.get("message", error_msg)
                elif isinstance(e.args[0], str) and ("code" in e.args[0] or "23503" in e.args[0] or "23505" in e.args[0]):
                    error_message = e.args[0]
                    # Try to extract code
                    if "23503" in error_message:
                        error_code = "23503"
                    elif "23505" in error_message:
                        error_code = "23505"
            
            # Handle foreign key constraint error (user doesn't exist) - PostgreSQL error code 23503
            if (error_code == "23503" or 
                "23503" in error_msg or
                "foreign key constraint" in error_lower or 
                "foreign key constraint" in error_message.lower() or
                "not present in table" in error_message.lower() or
                "violates foreign key constraint" in error_lower):
                return {
                    "success": False,
                    "error": f"User not found: {user_id}. Please register/login first."
                }
            
            # Handle duplicate key error - PostgreSQL error code 23505
            # Check for duplicate by tx_hash AND service combination
            if (error_code == "23505" or
                "23505" in error_msg or
                "duplicate" in error_lower or 
                "unique" in error_lower or
                "unique constraint" in error_lower):
                try:
                    # Check if same tx_hash + service combination already exists
                    existing = self.supabase_admin.table("payments").select("*").eq("tx_hash", tx_hash).eq("service", service).execute()
                    if existing.data and len(existing.data) > 0:
                        return {
                            "success": True,
                            "payment_id": existing.data[0].get("id"),
                            "already_exists": True
                        }
                    # If same tx_hash but different service, allow it (same payment used for different service)
                    # This allows recording the same payment for multiple services
                    existing_same_hash = self.supabase_admin.table("payments").select("*").eq("tx_hash", tx_hash).execute()
                    if existing_same_hash.data and len(existing_same_hash.data) > 0:
                        # Same tx_hash but different service - create new entry
                        # This should not happen with current schema, but handle it gracefully
                        return {
                            "success": True,
                            "payment_id": existing_same_hash.data[0].get("id"),
                            "already_exists": True,
                            "note": "Same transaction used for different service"
                        }
                except:
                    pass
            
            return {"success": False, "error": f"Database error: {error_msg}"}
    
    async def refund_payment(self, user_id: str, tx_hash: str, service: str, reason: str = "Service failed") -> Dict:
        """Mark a payment for refund when service fails
        
        Note: Actual refund processing should be handled separately via MNEE API.
        This method records the refund request and updates payment status.
        """
        if not self.supabase_admin:
            return {"success": False, "error": "Database not configured"}
        
        try:
            # Find the payment record
            payment_result = self.supabase_admin.table("payments").select("*").eq("user_id", user_id).eq("tx_hash", tx_hash).eq("service", service).order("created_at", desc=True).limit(1).execute()
            
            if not payment_result.data or len(payment_result.data) == 0:
                return {"success": False, "error": "Payment record not found"}
            
            payment = payment_result.data[0]
            
            # Update payment status to "refund_pending"
            update_result = self.supabase_admin.table("payments").update({
                "status": "refund_pending",
                "refund_reason": reason,
                "refund_requested_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", payment.get("id")).execute()
            
            if update_result.data and len(update_result.data) > 0:
                return {
                    "success": True,
                    "message": "Payment marked for refund. Refund will be processed within 2-3 business days.",
                    "payment_id": payment.get("id"),
                    "refund_status": "pending"
                }
            
            return {"success": False, "error": "Failed to update payment status"}
        except Exception as e:
            return {"success": False, "error": f"Failed to process refund request: {str(e)}"}

    async def verify_and_record_payment(self, user_id: str, tx_id: str, amount: str, service: str = "dashboard_access") -> Dict:
        """Verify MNEE payment transaction using MNEE SDK API
        
        Records each payment transaction even if user already has other payments.
        Only prevents duplicate recording of the same tx_hash for the same service.
        """
        try:
            # Verify the transaction first
            verify_result = await self.mnee_service.verify_transaction(tx_id)
            
            if verify_result.get("success") and verify_result.get("verified"):
                # Get the actual tx_id from verification result (might be different if tx_id was ticket_id)
                actual_tx_id = verify_result.get("tx_id", tx_id)
                
                # Check if this specific transaction (tx_hash + service) is already recorded
                if self.supabase_admin:
                    try:
                        existing = self.supabase_admin.table("payments").select("*").eq("tx_hash", actual_tx_id).eq("service", service).eq("user_id", user_id).execute()
                        if existing.data and len(existing.data) > 0:
                            return {
                                "success": True,
                                "verified": True,
                                "message": f"Transaction already recorded for service: {service}",
                                "tx_id": actual_tx_id,
                                "already_recorded": True,
                            }
                    except Exception as check_error:
                        # Continue to record if check fails
                        pass
                
                # Record the payment - this creates a new entry for this service
                record_result = await self.record_payment(user_id, actual_tx_id, amount, service)
                if record_result.get("success"):
                    return {
                        "success": True,
                        "verified": True,
                        "message": "Payment verified and recorded",
                        "tx_id": actual_tx_id,
                        "contract_address": self.contract_address,
                        "service": service,
                    }
                else:
                    error_detail = record_result.get("error", "Unknown error")
                    # Check if it's already recorded (duplicate)
                    if record_result.get("already_exists"):
                        return {
                            "success": True,
                            "verified": True,
                            "message": f"Payment already recorded for service: {service}",
                            "tx_id": actual_tx_id,
                            "already_recorded": True,
                        }
                    return {
                        "success": False,
                        "error": f"Payment verified but failed to record: {error_detail}",
                        "tx_id": actual_tx_id,
                    }
            else:
                return {
                    "success": False,
                    "error": verify_result.get("error", "Transaction verification failed"),
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Verification failed: {str(e)}",
            }
    
    async def get_payment_history(self, user_id: str, limit: int = 50, offset: int = 0) -> Dict:
        """Get user's payment history with pagination and explorer links
        
        Returns all verified payments for the user, ordered by most recent first.
        Includes WOC explorer links with MNEE plugin for each transaction.
        Only generates explorer links for valid transaction IDs (not ticket IDs).
        """
        if not self.supabase_admin:
            return {"success": False, "error": "Database not configured"}
        
        try:
            import re
            # Check if tx_hash is a ticket ID (UUID format) or actual tx_id (64 hex chars)
            def is_ticket_id(tx_hash: str) -> bool:
                if not tx_hash:
                    return False
                ticket_id_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
                return bool(ticket_id_pattern.match(tx_hash))
            
            def is_valid_tx_id(tx_hash: str) -> bool:
                if not tx_hash:
                    return False
                # Valid Bitcoin transaction ID is 64 hex characters
                tx_id_pattern = re.compile(r'^[0-9a-f]{64}$', re.IGNORECASE)
                return bool(tx_id_pattern.match(tx_hash))
            
            # Get total count
            count_result = self.supabase_admin.table("payments").select("*", count="exact").eq("user_id", user_id).eq("status", "verified").execute()
            total_count = count_result.count if hasattr(count_result, 'count') else 0
            
            # Get paginated payments
            result = (
                self.supabase_admin.table("payments")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "verified")
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            
            payments = result.data or []
            
            # Add explorer links to each payment - only for valid tx_ids
            is_sandbox = self.mnee_service.environment == "sandbox"
            enriched_payments = []
            
            for payment in payments:
                tx_hash = payment.get("tx_hash")
                explorer_url = None
                actual_tx_id = tx_hash
                
                if tx_hash:
                    # Check if it's a ticket ID - if so, try to get actual tx_id
                    if is_ticket_id(tx_hash):
                        try:
                            tx_status = await self.mnee_service.get_tx_status(tx_hash)
                            if tx_status.get("success") and tx_status.get("tx_id"):
                                actual_tx_id = tx_status.get("tx_id")
                                # Only generate URL if transaction is SUCCESS or MINED
                                if tx_status.get("status") in ["SUCCESS", "MINED"]:
                                    if is_valid_tx_id(actual_tx_id):
                                        if is_sandbox:
                                            explorer_url = f"https://whatsonchain.com/tx/{actual_tx_id}"
                                        else:
                                            explorer_url = f"https://whatsonchain.com/tx/{actual_tx_id}"
                                        payment["explorer_url"] = explorer_url
                                        payment["actual_tx_id"] = actual_tx_id
                                    else:
                                        payment["explorer_url"] = None
                                        payment["is_processing"] = True
                                else:
                                    payment["explorer_url"] = None
                                    payment["is_processing"] = True
                        except:
                            pass  # If we can't get status, use original tx_hash
                    elif is_valid_tx_id(tx_hash):
                        tx_verify = await self.mnee_service.get_transaction(tx_hash)
                        if tx_verify.get("exists"):
                            if is_sandbox:
                                explorer_url = f"https://whatsonchain.com/tx/{tx_hash}"
                            else:
                                explorer_url = f"https://whatsonchain.com/tx/{tx_hash}"
                            payment["explorer_url"] = explorer_url
                            payment["actual_tx_id"] = tx_hash
                        else:
                            payment["explorer_url"] = None
                            payment["is_processing"] = True
                            payment["actual_tx_id"] = tx_hash
                    else:
                        payment["explorer_url"] = None
                        payment["is_processing"] = True
                
                enriched_payments.append(payment)
            
            # Calculate total spent
            total_spent = sum(float(payment.get("amount", 0)) for payment in payments)
            
            return {
                "success": True,
                "payments": enriched_payments,
                "total_count": total_count,
                "total_spent": str(total_spent),
                "environment": self.mnee_service.environment,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_payment_analytics(self, user_id: str) -> Dict:
        """Get payment analytics for user
        
        Returns:
        - Total spent across all services
        - Total transaction count
        - Service breakdown (amount per service)
        - Recent payments (last 10)
        """
        if not self.supabase_admin:
            return {"success": False, "error": "Database not configured"}
        
        try:
            # Get all verified payments
            result = (
                self.supabase_admin.table("payments")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "verified")
                .order("created_at", desc=True)
                .execute()
            )
            
            payments = result.data or []
            
            # Calculate analytics
            total_spent = 0.0
            service_breakdown = {}
            
            for payment in payments:
                amount = float(payment.get("amount", 0))
                total_spent += amount
                
                service = payment.get("service", "unknown")
                if service not in service_breakdown:
                    service_breakdown[service] = {"count": 0, "total_amount": 0.0}
                service_breakdown[service]["count"] += 1
                service_breakdown[service]["total_amount"] += amount
            
            # Convert amounts to strings for JSON serialization
            for service in service_breakdown:
                service_breakdown[service]["total_amount"] = str(service_breakdown[service]["total_amount"])
            
            # Get recent payments (last 10)
            recent_payments = payments[:10] if len(payments) > 10 else payments
            
            return {
                "success": True,
                "total_spent": str(total_spent),
                "total_transactions": len(payments),
                "service_breakdown": service_breakdown,
                "recent_payments": recent_payments,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_payment_receipt(self, user_id: str, tx_hash: str) -> Dict:
        """Get detailed payment receipt with transaction information and explorer links"""
        if not self.supabase_admin:
            return {"success": False, "error": "Database not configured"}
        
        try:
            # Get payment from database
            result = (
                self.supabase_admin.table("payments")
                .select("*")
                .eq("user_id", user_id)
                .eq("tx_hash", tx_hash)
                .execute()
            )
            
            if not result.data or len(result.data) == 0:
                return {"success": False, "error": "Payment not found"}
            
            payment = result.data[0]
            
            # Check if tx_hash is a ticket ID (UUID) or actual tx_id (64 hex chars)
            import re
            ticket_id_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            tx_id_pattern = re.compile(r'^[0-9a-f]{64}$', re.IGNORECASE)
            
            is_ticket = bool(ticket_id_pattern.match(tx_hash)) if tx_hash else False
            is_valid_tx_id_format = bool(tx_id_pattern.match(tx_hash)) if tx_hash else False
            
            # Determine if sandbox or production based on environment
            is_sandbox = self.mnee_service.environment == "sandbox"
            
            # Get actual transaction ID and status
            actual_tx_id = None
            explorer_url = None
            tx_status = None
            is_processing = False
            
            if is_ticket:
                # It's a ticket ID - get status to find actual tx_id
                tx_status = await self.mnee_service.get_tx_status(tx_hash)
                if tx_status.get("success") and tx_status.get("tx_id"):
                    actual_tx_id = tx_status.get("tx_id")
                    # Only generate URL if transaction is SUCCESS or MINED
                    if tx_status.get("status") in ["SUCCESS", "MINED"]:
                        if actual_tx_id and tx_id_pattern.match(actual_tx_id):
                            if is_sandbox:
                                explorer_url = f"https://test.whatsonchain.com/tx/{actual_tx_id}?tab=m8eqcrbs"
                            else:
                                explorer_url = f"https://whatsonchain.com/tx/{actual_tx_id}?tab=m8eqcrbs"
                    elif tx_status.get("status") == "BROADCASTING":
                        is_processing = True
                elif tx_status.get("success") and tx_status.get("status") == "BROADCASTING":
                    is_processing = True
            elif is_valid_tx_id_format:
                tx_verify = await self.mnee_service.get_transaction(tx_hash)
                if tx_verify.get("exists"):
                    actual_tx_id = tx_hash
                    if is_sandbox:
                        explorer_url = f"https://test.whatsonchain.com/tx/{actual_tx_id}"
                    else:
                        explorer_url = f"https://whatsonchain.com/tx/{actual_tx_id}"
                else:
                    is_processing = True
                    actual_tx_id = tx_hash
            
            receipt = {
                "payment_id": payment.get("id"),
                "tx_hash": payment.get("tx_hash"),
                "service": payment.get("service"),
                "amount": payment.get("amount"),
                "status": payment.get("status"),
                "from_address": payment.get("from_address"),
                "created_at": payment.get("created_at"),
                "updated_at": payment.get("updated_at"),
                "contract_address": self.contract_address,
                "transaction_status": tx_status.get("status") if tx_status and tx_status.get("success") else None,
                "transaction_id": actual_tx_id,
                "transaction_hex": tx_status.get("tx_hex") if tx_status and tx_status.get("success") else None,
                "errors": tx_status.get("errors") if tx_status and tx_status.get("success") else None,
                "created_at_ticket": tx_status.get("createdAt") if tx_status and tx_status.get("success") else None,
                "updated_at_ticket": tx_status.get("updatedAt") if tx_status and tx_status.get("success") else None,
                "explorer_url": explorer_url,  # WOC explorer with MNEE plugin (only if valid tx_id exists and mined)
                "is_processing": is_processing,  # True if transaction is still being processed
                "environment": self.mnee_service.environment,
            }
            
            return {
                "success": True,
                "receipt": receipt,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

