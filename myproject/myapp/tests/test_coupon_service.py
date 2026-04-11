import pytest
from decimal import Decimal
from django.utils import timezone
from myapp.models import Coupon, Customer
from myapp.services.coupon_service import apply_coupon, get_applied_coupon, clear_coupon
import datetime

@pytest.fixture
def active_coupon():
    now = timezone.now()
    return Coupon.objects.create(
        code="SAVE50",
        discount_type="fixed",
        value=Decimal("50.00"),
        valid_from=now - datetime.timedelta(days=1),
        valid_to=now + datetime.timedelta(days=1),
        active=True,
        min_purchase_amount=Decimal("100.00")
    )

@pytest.mark.django_db
class TestCouponService:
    def test_apply_coupon_success(self, active_coupon):
        session = {}
        result = apply_coupon("SAVE50", Decimal("200.00"), session)
        
        assert result["success"] is True
        assert result["discount"] == Decimal("50.00")
        assert result["new_total"] == Decimal("150.00")
        assert session["coupon_id"] == active_coupon.pk

    def test_apply_coupon_invalid_code(self):
        session = {}
        result = apply_coupon("INVALID", Decimal("200.00"), session)
        
        assert result["success"] is False
        assert "Invalid" in result["message"]
        assert "coupon_id" not in session

    def test_apply_coupon_not_valid(self, active_coupon):
        # min purchase not met
        session = {"coupon_id": active_coupon.pk}
        result = apply_coupon("SAVE50", Decimal("50.00"), session)
        
        assert result["success"] is False
        assert "Spend at least" in result["message"]
        assert "coupon_id" not in session

    def test_get_applied_coupon_exists(self, active_coupon):
        session = {"coupon_id": active_coupon.pk}
        coupon = get_applied_coupon(session)
        assert coupon == active_coupon

    def test_get_applied_coupon_inactive(self, active_coupon):
        active_coupon.active = False
        active_coupon.save()
        session = {"coupon_id": active_coupon.pk}
        
        coupon = get_applied_coupon(session)
        assert coupon is None
        assert "coupon_id" not in session

    def test_get_applied_coupon_not_found(self):
        session = {"coupon_id": 99999}
        coupon = get_applied_coupon(session)
        assert coupon is None
        assert "coupon_id" not in session

    def test_clear_coupon(self):
        session = {"coupon_id": 1}
        clear_coupon(session)
        assert "coupon_id" not in session
        
        # Should not crash if already clear
        clear_coupon(session)
