"""Idempotently seed the three subscription plans.

Run:  python -m seeds.seed_plans
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.subscription import SubscriptionPlan

PLANS = [
    {"name": "Starter", "monthly_bill_limit": 500, "price_inr": 0},
    {"name": "Standard", "monthly_bill_limit": 2000, "price_inr": 0},
    {"name": "Professional", "monthly_bill_limit": 5000, "price_inr": 0},
]


def seed(db) -> int:
    created = 0
    for spec in PLANS:
        existing = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.name == spec["name"]))
        if existing is None:
            db.add(SubscriptionPlan(**spec))
            created += 1
        else:
            existing.monthly_bill_limit = spec["monthly_bill_limit"]
    db.commit()
    return created


def main() -> None:
    db = SessionLocal()
    try:
        created = seed(db)
        print(f"Seed complete. Plans created: {created} (existing plans updated in place).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
