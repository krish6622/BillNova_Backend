# BillNova — Security Posture (Phase 1)

## Authentication
- Passwords hashed with **bcrypt** (Passlib); never stored or returned in plaintext.
- **JWT** access + refresh tokens (python-jose, HS256). Access carries `sub`, `tenant_id`, `role`, `type`.
- **Logout / password reset** bump the user's `token_version`, invalidating outstanding refresh tokens.
- Login returns a **generic 401** on bad credentials or inactive users (no account enumeration).

## Authorization (RBAC)
- Two roles: **OWNER** (all modules) and **CASHIER** (create bills, view products).
- Enforced **server-side** on every route via `require_owner` / route dependencies — never UI-only.
- Cashiers are blocked (403) from product writes, purchases, inventory, reports, users, and settings.

## Multi-tenancy & isolation
- Every business row carries `tenant_id`, taken from the JWT — clients never send it.
- Repositories scope all queries by `tenant_id`; direct access to another tenant's id returns **404**
  (existence is not leaked), verified by tests.

## Secrets & configuration
- All secrets via **environment variables**; `.env` is gitignored, only `.env.example` (placeholders) is committed.
- No environment-specific URLs or credentials in code.
- Manual subscription activation is gated by `ADMIN_API_KEY` (platform ops); **disabled when unset** —
  owners cannot self-upgrade.

## Data integrity
- All money/quantity stored as `NUMERIC`; GST math uses `Decimal` with half-up rounding (no float drift).
- Bill save (sale + items + payments + stock-out + usage increment) is a **single DB transaction** — it
  fully rolls back on any failure (no partial sale, stock, or usage change).
- Subscription guard blocks billing when inactive/expired or over the monthly limit; payments must equal the
  grand total; insufficient stock blocks the sale.

## Transport / deployment
- CORS restricted to configured origins.
- Run behind TLS in production; rotate `JWT_SECRET` and `ADMIN_API_KEY` per environment.
- Uniform error envelope (`{ "error": { code, message, details } }`) — no stack traces leaked to clients.

## Verification
- Backend test suite (CI gate ≥80% coverage) covers auth flows, RBAC (403), tenant isolation (404),
  no password-hash leakage, admin gating, and the atomic billing path.
