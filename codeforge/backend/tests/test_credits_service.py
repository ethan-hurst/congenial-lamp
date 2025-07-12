"""
Tests for Credits Service
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from src.services.credits_service import CreditsService, CreditTransaction, CreditTier


class TestCreditsService:
    """Test suite for CreditsService"""

    @pytest.fixture
    def credits_service(self):
        """Create credits service instance"""
        return CreditsService()

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()

    @pytest.mark.asyncio
    async def test_get_user_balance_existing_user(self, credits_service, mock_db):
        """Test getting balance for existing user"""
        # Mock database response
        mock_db.execute.return_value.scalar.return_value = 1500
        
        result = await credits_service.get_user_balance("user123", mock_db)
        
        assert result["balance"] == 1500
        assert result["tier"] == CreditTier.PREMIUM
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_get_user_balance_new_user(self, credits_service, mock_db):
        """Test getting balance for new user"""
        # Mock database response for new user
        mock_db.execute.return_value.scalar.return_value = None
        
        result = await credits_service.get_user_balance("newuser", mock_db)
        
        assert result["balance"] == credits_service.INITIAL_CREDITS
        assert result["tier"] == CreditTier.FREE

    @pytest.mark.asyncio
    async def test_consume_credits_sufficient_balance(self, credits_service, mock_db):
        """Test consuming credits with sufficient balance"""
        # Mock current balance
        mock_db.execute.return_value.scalar.return_value = 1000
        
        result = await credits_service.consume_credits(
            user_id="user123",
            amount=50,
            reason="AI completion",
            db=mock_db
        )
        
        assert result is True
        # Verify transaction was recorded
        mock_db.add.assert_called()

    @pytest.mark.asyncio
    async def test_consume_credits_insufficient_balance(self, credits_service, mock_db):
        """Test consuming credits with insufficient balance"""
        # Mock low balance
        mock_db.execute.return_value.scalar.return_value = 10
        
        result = await credits_service.consume_credits(
            user_id="user123",
            amount=50,
            reason="AI completion",
            db=mock_db
        )
        
        assert result is False
        # Verify no transaction was recorded
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_credits(self, credits_service, mock_db):
        """Test adding credits to user account"""
        # Mock current balance
        mock_db.execute.return_value.scalar.return_value = 500
        
        result = await credits_service.add_credits(
            user_id="user123",
            amount=1000,
            reason="Purchase",
            db=mock_db
        )
        
        assert result["success"] is True
        assert result["new_balance"] == 1500
        assert result["added"] == 1000

    @pytest.mark.asyncio
    async def test_earn_credits_pr_merge(self, credits_service, mock_db):
        """Test earning credits from PR merge"""
        mock_db.execute.return_value.scalar.return_value = 800
        
        result = await credits_service.earn_credits_pr_merge(
            user_id="user123",
            pr_url="https://github.com/user/repo/pull/1",
            db=mock_db
        )
        
        assert result["success"] is True
        assert result["earned"] == credits_service.CREDITS_PER_PR_MERGE
        assert result["reason"] == "PR merged"

    @pytest.mark.asyncio
    async def test_earn_credits_helpful_answer(self, credits_service, mock_db):
        """Test earning credits from helpful answer"""
        mock_db.execute.return_value.scalar.return_value = 700
        
        result = await credits_service.earn_credits_helpful_answer(
            user_id="user123",
            answer_url="https://stackoverflow.com/a/123456",
            db=mock_db
        )
        
        assert result["success"] is True
        assert result["earned"] == credits_service.CREDITS_PER_HELPFUL_ANSWER

    @pytest.mark.asyncio
    async def test_get_credit_history(self, credits_service, mock_db):
        """Test getting credit transaction history"""
        # Mock transaction history
        mock_transactions = [
            Mock(
                id="tx1",
                amount=-50,
                balance_after=950,
                reason="AI completion",
                created_at=datetime.now(timezone.utc)
            ),
            Mock(
                id="tx2", 
                amount=100,
                balance_after=1000,
                reason="PR merged",
                created_at=datetime.now(timezone.utc)
            )
        ]
        mock_db.execute.return_value.scalars.return_value.all.return_value = mock_transactions
        
        result = await credits_service.get_credit_history("user123", mock_db)
        
        assert len(result["transactions"]) == 2
        assert result["transactions"][0]["amount"] == -50
        assert result["transactions"][1]["amount"] == 100

    @pytest.mark.asyncio
    async def test_gift_credits(self, credits_service, mock_db):
        """Test gifting credits between users"""
        # Mock sender balance
        mock_db.execute.return_value.scalar.side_effect = [500, 200]  # sender, receiver
        
        result = await credits_service.gift_credits(
            sender_id="user1",
            receiver_id="user2", 
            amount=100,
            message="Thanks for the help!",
            db=mock_db
        )
        
        assert result["success"] is True
        assert result["gifted"] == 100

    @pytest.mark.asyncio
    async def test_gift_credits_insufficient_balance(self, credits_service, mock_db):
        """Test gifting credits with insufficient balance"""
        # Mock low sender balance
        mock_db.execute.return_value.scalar.return_value = 50
        
        result = await credits_service.gift_credits(
            sender_id="user1",
            receiver_id="user2",
            amount=100,
            message="Thanks!",
            db=mock_db
        )
        
        assert result["success"] is False
        assert "insufficient" in result["error"].lower()

    def test_determine_tier_free(self, credits_service):
        """Test tier determination for free tier"""
        tier = credits_service._determine_tier(credits_service.FREE_TIER_LIMIT - 100)
        assert tier == CreditTier.FREE

    def test_determine_tier_premium(self, credits_service):
        """Test tier determination for premium tier"""
        tier = credits_service._determine_tier(credits_service.FREE_TIER_LIMIT + 500)
        assert tier == CreditTier.PREMIUM

    def test_determine_tier_enterprise(self, credits_service):
        """Test tier determination for enterprise tier"""
        tier = credits_service._determine_tier(credits_service.PREMIUM_TIER_LIMIT + 1000)
        assert tier == CreditTier.ENTERPRISE

    @pytest.mark.asyncio
    async def test_calculate_usage_cost_basic(self, credits_service):
        """Test calculating usage cost for basic operations"""
        cost = await credits_service.calculate_usage_cost(
            operation="file_save",
            duration_seconds=1,
            metadata={"file_size": 1024}
        )
        
        assert cost == 1  # Base cost for file operations

    @pytest.mark.asyncio
    async def test_calculate_usage_cost_ai_completion(self, credits_service):
        """Test calculating usage cost for AI operations"""
        cost = await credits_service.calculate_usage_cost(
            operation="ai_completion",
            duration_seconds=2,
            metadata={"tokens": 500, "model": "claude"}
        )
        
        assert cost >= 2  # AI operations cost more

    @pytest.mark.asyncio
    async def test_calculate_usage_cost_container_runtime(self, credits_service):
        """Test calculating usage cost for container runtime"""
        cost = await credits_service.calculate_usage_cost(
            operation="container_runtime",
            duration_seconds=300,  # 5 minutes
            metadata={"cpu_cores": 2, "memory_gb": 4}
        )
        
        expected = int((300 / 60) * 2 * 4)  # minutes * cores * memory
        assert cost == expected

    @pytest.mark.asyncio
    async def test_purchase_credits_validation(self, credits_service, mock_db):
        """Test credit purchase with validation"""
        mock_db.execute.return_value.scalar.return_value = 500
        
        # Test minimum purchase
        result = await credits_service.purchase_credits(
            user_id="user123",
            amount=credits_service.MIN_PURCHASE - 1,
            payment_method="stripe",
            db=mock_db
        )
        
        assert result["success"] is False
        assert "minimum" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_usage_analytics(self, credits_service, mock_db):
        """Test getting usage analytics"""
        # Mock analytics data
        mock_stats = [
            Mock(date="2024-01-01", credits_spent=150, operation_count=75),
            Mock(date="2024-01-02", credits_spent=200, operation_count=100)
        ]
        mock_db.execute.return_value.all.return_value = mock_stats
        
        result = await credits_service.get_usage_analytics("user123", days=7, db=mock_db)
        
        assert len(result["daily_usage"]) == 2
        assert result["total_credits_spent"] == 350
        assert result["total_operations"] == 175