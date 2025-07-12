"""
CodeForge Credits Service - Revolutionary pricing system
Pay only for actual compute, earn credits by contributing
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
import asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.credits import ComputeCredits, CreditTransaction, CreditEarningType
from ..models.user import User
from ..config.settings import settings


class CreditsService:
    """Manages the revolutionary credits system"""
    
    # Credit earning rates
    CREDITS_PER_PR_MERGE = 100
    CREDITS_PER_HELPFUL_ANSWER = 50
    CREDITS_PER_TEMPLATE_USE = 10
    CREDITS_PER_BUG_FIX = 75
    CREDITS_PER_REFERRED_USER = 200
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
    async def get_user_credits(self, user_id: str) -> ComputeCredits:
        """Get user's current credit balance and stats"""
        result = await self.db.execute(
            select(ComputeCredits).where(ComputeCredits.user_id == user_id)
        )
        credits = result.scalar_one_or_none()
        
        if not credits:
            # Initialize new user with free credits
            credits = await self._initialize_user_credits(user_id)
            
        return credits
    
    async def _initialize_user_credits(self, user_id: str) -> ComputeCredits:
        """Initialize credits for new user"""
        credits = ComputeCredits(
            user_id=user_id,
            balance=settings.MONTHLY_FREE_CREDITS,
            lifetime_earned=settings.MONTHLY_FREE_CREDITS,
            lifetime_spent=0,
            monthly_allocation=settings.MONTHLY_FREE_CREDITS,
            rollover_credits=0,
            last_updated=datetime.utcnow()
        )
        self.db.add(credits)
        await self.db.commit()
        await self.db.refresh(credits)
        
        # Record initial credit grant
        await self._record_transaction(
            user_id=user_id,
            amount=settings.MONTHLY_FREE_CREDITS,
            transaction_type="grant",
            description="Welcome bonus credits"
        )
        
        return credits
    
    async def consume_credits(
        self, 
        user_id: str, 
        amount: int, 
        description: str,
        resource_type: str = "compute"
    ) -> bool:
        """Consume credits for resource usage"""
        credits = await self.get_user_credits(user_id)
        
        if credits.balance < amount:
            return False
            
        # Update balance
        credits.balance -= amount
        credits.lifetime_spent += amount
        credits.last_updated = datetime.utcnow()
        
        await self.db.commit()
        
        # Record transaction
        await self._record_transaction(
            user_id=user_id,
            amount=-amount,
            transaction_type="usage",
            description=description,
            metadata={"resource_type": resource_type}
        )
        
        return True
    
    async def earn_credits(
        self,
        user_id: str,
        earning_type: CreditEarningType,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Award credits for contributions"""
        amount = self._get_earning_amount(earning_type)
        
        credits = await self.get_user_credits(user_id)
        credits.balance += amount
        credits.lifetime_earned += amount
        credits.last_updated = datetime.utcnow()
        
        await self.db.commit()
        
        # Record earning
        await self._record_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type="earning",
            description=f"Earned credits: {earning_type.value}",
            metadata={
                "earning_type": earning_type.value,
                "reference_id": reference_id,
                **(metadata or {})
            }
        )
        
        return amount
    
    def _get_earning_amount(self, earning_type: CreditEarningType) -> int:
        """Get credit amount for earning type"""
        earning_map = {
            CreditEarningType.PR_MERGE: self.CREDITS_PER_PR_MERGE,
            CreditEarningType.HELPFUL_ANSWER: self.CREDITS_PER_HELPFUL_ANSWER,
            CreditEarningType.TEMPLATE_USE: self.CREDITS_PER_TEMPLATE_USE,
            CreditEarningType.BUG_FIX: self.CREDITS_PER_BUG_FIX,
            CreditEarningType.REFERRAL: self.CREDITS_PER_REFERRED_USER,
        }
        return earning_map.get(earning_type, 0)
    
    async def gift_credits(
        self,
        from_user_id: str,
        to_user_id: str,
        amount: int,
        message: Optional[str] = None
    ) -> bool:
        """Gift credits to another user"""
        # Check sender balance
        sender_credits = await self.get_user_credits(from_user_id)
        if sender_credits.balance < amount:
            return False
            
        # Transfer credits
        sender_credits.balance -= amount
        receiver_credits = await self.get_user_credits(to_user_id)
        receiver_credits.balance += amount
        
        await self.db.commit()
        
        # Record transactions
        await self._record_transaction(
            user_id=from_user_id,
            amount=-amount,
            transaction_type="gift_sent",
            description=f"Gift sent to user {to_user_id}",
            metadata={"recipient": to_user_id, "message": message}
        )
        
        await self._record_transaction(
            user_id=to_user_id,
            amount=amount,
            transaction_type="gift_received",
            description=f"Gift received from user {from_user_id}",
            metadata={"sender": from_user_id, "message": message}
        )
        
        return True
    
    async def process_monthly_rollover(self):
        """Process monthly credit allocation and rollover"""
        # Get all users
        result = await self.db.execute(select(ComputeCredits))
        all_credits = result.scalars().all()
        
        for credits in all_credits:
            # Add rollover credits (unused from previous month)
            if credits.balance > 0:
                credits.rollover_credits = min(
                    credits.balance,
                    settings.MAX_ROLLOVER_CREDITS
                )
                
            # Add monthly allocation
            credits.balance += credits.monthly_allocation
            credits.last_updated = datetime.utcnow()
            
        await self.db.commit()
    
    async def create_team_pool(
        self,
        team_id: str,
        initial_credits: int,
        admin_user_id: str
    ) -> Dict[str, Any]:
        """Create a team credit pool for organizations"""
        # Implementation for team pools
        # This enables organizations to manage credits centrally
        pass
    
    async def _record_transaction(
        self,
        user_id: str,
        amount: int,
        transaction_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record credit transaction for audit trail"""
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        self.db.add(transaction)
        await self.db.commit()
    
    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[CreditTransaction]:
        """Get user's transaction history"""
        result = await self.db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def estimate_credits_for_operation(
        self,
        cpu_cores: float,
        memory_gb: float,
        duration_seconds: int,
        gpu_type: Optional[str] = None
    ) -> int:
        """Estimate credits needed for an operation"""
        # Calculate based on resource usage
        cpu_credits = (cpu_cores * duration_seconds / 3600) * settings.CREDITS_PER_CPU_HOUR
        memory_credits = (memory_gb * duration_seconds / 3600) * settings.CREDITS_PER_GB_RAM_HOUR
        
        total_credits = int(cpu_credits + memory_credits)
        
        # Add GPU credits if applicable
        if gpu_type:
            gpu_multiplier = self._get_gpu_multiplier(gpu_type)
            total_credits = int(total_credits * gpu_multiplier)
            
        return total_credits
    
    def _get_gpu_multiplier(self, gpu_type: str) -> float:
        """Get credit multiplier for GPU types"""
        gpu_multipliers = {
            "tesla-t4": 5.0,
            "tesla-v100": 10.0,
            "a100": 15.0,
            "h100": 25.0
        }
        return gpu_multipliers.get(gpu_type.lower(), 5.0)