"""Tenant-scoped repository base.

Every business-table query MUST be scoped to a tenant. Subclasses build their
queries via `self._scoped(select(...))` so the tenant filter is never forgotten.
"""

import uuid
from typing import Generic, TypeVar

from sqlalchemy import Select
from sqlalchemy.orm import Session

T = TypeVar("T")


class TenantRepository(Generic[T]):
    model: type[T]

    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    def _scoped(self, stmt: Select) -> Select:
        return stmt.where(self.model.tenant_id == self.tenant_id)

    def get(self, entity_id: uuid.UUID) -> T | None:
        obj = self.db.get(self.model, entity_id)
        if obj is None or obj.tenant_id != self.tenant_id:
            return None  # cross-tenant access is indistinguishable from "not found"
        return obj

    def add(self, obj: T) -> T:
        self.db.add(obj)
        return obj
