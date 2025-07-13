"""
Credits Service for In-Memory Storage
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal

from ..storage.storage_adapter import get_storage
from ..config.settings import settings


class CreditsService:
    """Manages the credits system with in-memory storage"""
    
    # Credit earning rates
    CREDITS_PER_PR_MERGE = 100
    CREDITS_PER_HELPFUL_ANSWER = 50
    CREDITS_PER_TEMPLATE_USE = 10
    CREDITS_PER_BUG_FIX = 75
    CREDITS_PER_REFERRED_USER = 200
    
    # Monthly free credits (in cents)
    MONTHLY_FREE_CREDITS = 500  # $5
    
    def __init__(self, db_session=None):
        # db_session is ignored for memory storage
        self.storage = get_storage()
        
    async def get_user_credits(self, user_id: str) -> Dict[str, Any]:
        """Get user's current credit balance and stats"""
        if hasattr(self.storage, 'get_user_credits'):
            return await self.storage.get_user_credits(user_id)
        else:
            # Return default credits if storage doesn't support it
            return {
                "user_id": user_id,
                "balance": self.MONTHLY_FREE_CREDITS,
                "total_earned": 0.0,
                "total_spent": 0.0,
                "updated_at": datetime.now(timezone.utc),
            }
    
    async def charge_credits(
        self, 
        user_id: str, 
        amount: float, 
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Charge credits from user account
        Returns True if successful, False if insufficient credits
        """
        credits = await self.get_user_credits(user_id)
        
        if credits["balance"] < amount:
            return False
        
        # Update credits
        if hasattr(self.storage, 'update_credits'):
            await self.storage.update_credits(
                user_id, 
                -amount, 
                "charge", 
                description
            )
        
        return True
    
    async def add_credits(
        self,
        user_id: str,
        amount: float,
        earning_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add credits to user account (from earnings or purchases)"""
        if hasattr(self.storage, 'update_credits'):
            credits = await self.storage.update_credits(
                user_id,
                amount,
                earning_type,
                description
            )
            return credits
        else:
            return await self.get_user_credits(user_id)
    
    async def get_credit_history(
        self, 
        user_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's credit transaction history"""
        if hasattr(self.storage, 'get_credit_transactions'):
            return await self.storage.get_credit_transactions(user_id, limit)
        else:
            return []
    
    async def calculate_usage_cost(
        self,
        cpu_seconds: float,
        memory_mb_seconds: float,
        storage_gb_hours: float,
        network_gb: float,
        gpu_hours: float = 0
    ) -> float:
        """
        Calculate cost based on actual usage
        Returns cost in cents
        """
        # Pricing per resource (in cents)
        CPU_COST_PER_SECOND = 0.001  # $0.00001 per CPU second
        MEMORY_COST_PER_MB_SECOND = 0.0001  # $0.000001 per MB-second
        STORAGE_COST_PER_GB_HOUR = 0.01  # $0.0001 per GB-hour
        NETWORK_COST_PER_GB = 1.0  # $0.01 per GB
        GPU_COST_PER_HOUR = 100.0  # $1.00 per GPU hour
        
        total_cost = (
            cpu_seconds * CPU_COST_PER_SECOND +
            memory_mb_seconds * MEMORY_COST_PER_MB_SECOND +
            storage_gb_hours * STORAGE_COST_PER_GB_HOUR +
            network_gb * NETWORK_COST_PER_GB +
            gpu_hours * GPU_COST_PER_HOUR
        )
        
        return round(total_cost, 2)
    
    async def award_credits_for_contribution(
        self,
        user_id: str,
        contribution_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Award credits for user contributions"""
        award_amounts = {
            "pr_merge": self.CREDITS_PER_PR_MERGE,
            "helpful_answer": self.CREDITS_PER_HELPFUL_ANSWER,
            "template_use": self.CREDITS_PER_TEMPLATE_USE,
            "bug_fix": self.CREDITS_PER_BUG_FIX,
            "referral": self.CREDITS_PER_REFERRED_USER,
        }
        
        amount = award_amounts.get(contribution_type, 0)
        if amount > 0:
            return await self.add_credits(
                user_id,
                amount,
                f"earned_{contribution_type}",
                f"Earned credits for {contribution_type.replace('_', ' ')}",
                metadata
            )
        
        return await self.get_user_credits(user_id)
    
    async def check_credit_limit(self, user_id: str, required_amount: float) -> bool:
        """Check if user has enough credits for an operation"""
        credits = await self.get_user_credits(user_id)
        return credits["balance"] >= required_amount
    
    async def get_pricing_info(self) -> Dict[str, Any]:
        """Get current pricing information"""
        return {
            "compute": {
                "cpu_per_second": 0.001,
                "memory_per_mb_second": 0.0001,
                "storage_per_gb_hour": 0.01,
                "network_per_gb": 1.0,
                "gpu_per_hour": 100.0,
            },
            "earnings": {
                "pr_merge": self.CREDITS_PER_PR_MERGE,
                "helpful_answer": self.CREDITS_PER_HELPFUL_ANSWER,
                "template_use": self.CREDITS_PER_TEMPLATE_USE,
                "bug_fix": self.CREDITS_PER_BUG_FIX,
                "referral": self.CREDITS_PER_REFERRED_USER,
            },
            "free_tier": {
                "monthly_credits": self.MONTHLY_FREE_CREDITS,
                "description": "$5 in free credits every month",
            },
            "currency": "USD cents",
        }