# Security and Tenancy

## Purpose

This document describes the security model and multi-tenancy architecture for the EventSales AI POC.

## POC Scope

The POC implements basic authentication and a single-tenant data model sufficient for local testing. Production multi-tenant hardening, enterprise SSO, and MFA are deferred to MVP.

## Authentication (POC)

- **Method:** JWT (JSON Web Tokens)
- **Flow:** Email + password login → JWT issued → included in `Authorization: Bearer` header on all API requests
- **Session:** Short-lived access token with refresh token support
- **Password storage:** Bcrypt hashing

POC does not require OAuth, Google/Microsoft SSO, or MFA.

## Authorisation

### Roles (POC)

| Role | Permissions |
|---|---|
| Sales Manager | Manage pricing rules, personas, workflows; view analytics |
| Sales Representative | View enquiries, handle escalations, view proposals |
| Administrator | Manage users, environments, view audit logs |

Role-based access is enforced via FastAPI dependency injection. Route handlers check role from the JWT claims.

## Multi-Tenancy

### POC Model

The POC operates as a **single tenant** (one hospitality group). Multi-tenant isolation is not production-hardened for POC.

All data records include a `tenant_id` column so the schema is **tenant-aware** and can support multi-tenancy in MVP without a schema redesign.

### MVP Target

Full multi-tenant isolation requires:
- row-level tenant filtering on all queries
- tenant-aware middleware that injects `tenant_id` from JWT
- isolated pricing rules, personas, and workflows per tenant

This is designed into the schema now but enforced only lightly during POC.

## API Security

- All API routes require authentication except `/health` and the test webform intake
- HTTPS not required for local POC (`http://localhost`)
- CORS configured to allow frontend origin (`localhost:3000`)
- No rate limiting during POC

## Secrets Management (POC)

Environment variables via `.env` (from `.env.example`).

Do not commit `.env` to version control. `.env.example` contains placeholder keys only.

Critical secrets:
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `SECRET_KEY` — JWT signing key
- `SMTP_USERNAME` / `SMTP_PASSWORD` — Gmail test credentials

## POC Limitations

- No enterprise SSO
- No MFA
- No row-level security (PostgreSQL RLS)
- No audit encryption
- No production secrets management (Vault, AWS Secrets Manager, etc.)
- No penetration testing
- Single tenant only during POC
