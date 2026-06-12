"""Product repository — tenant-scoped CRUD, search, pagination."""

from sqlalchemy import func, or_, select

from app.models.product import Product
from app.repositories.base import TenantRepository


class ProductRepository(TenantRepository[Product]):
    model = Product

    def get_by_code(self, code: str) -> Product | None:
        return self.db.scalar(self._scoped(select(Product)).where(Product.product_code == code))

    def code_exists(self, code: str, *, exclude_id=None) -> bool:
        stmt = self._scoped(select(Product.id)).where(Product.product_code == code)
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        return self.db.scalar(stmt) is not None

    def search(
        self, *, search: str | None, page: int, limit: int, active: bool | None
    ) -> tuple[list[Product], int]:
        conditions = []
        if active is not None:
            conditions.append(Product.is_active.is_(active))
        if search:
            like = f"%{search.lower()}%"
            conditions.append(
                or_(
                    func.lower(Product.name).like(like),
                    func.lower(Product.product_code).like(like),
                    func.lower(func.coalesce(Product.hsn_code, "")).like(like),
                )
            )

        base = self._scoped(select(Product))
        count_stmt = self._scoped(select(func.count(Product.id)))
        for cond in conditions:
            base = base.where(cond)
            count_stmt = count_stmt.where(cond)

        total = self.db.scalar(count_stmt) or 0
        rows = list(
            self.db.scalars(base.order_by(Product.name).offset((page - 1) * limit).limit(limit))
        )
        return rows, total
