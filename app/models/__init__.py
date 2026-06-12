"""ORM models package. Importing here registers all tables on Base.metadata
so Alembic autogenerate and tests' create_all discover them."""

from app.models.inventory import InventoryTransaction
from app.models.payment import Payment
from app.models.product import Product
from app.models.purchase import Purchase, PurchaseItem
from app.models.sale import Sale, SaleItem
from app.models.subscription import SubscriptionPlan, TenantSubscription
from app.models.supplier import Supplier
from app.models.tenant import Tenant
from app.models.usage import BillUsage
from app.models.user import User

__all__ = [
    "Tenant",
    "User",
    "SubscriptionPlan",
    "TenantSubscription",
    "BillUsage",
    "Product",
    "Sale",
    "SaleItem",
    "Payment",
    "InventoryTransaction",
    "Supplier",
    "Purchase",
    "PurchaseItem",
]
