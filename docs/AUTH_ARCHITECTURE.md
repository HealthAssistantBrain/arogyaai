# Auth Architecture

## Target flow

Frontend -> Supabase Auth -> Supabase JWT -> FastAPI JWT verification -> domain user/profile loading

Supabase is now the only active authority for:

- signup
- login
- password reset
- email verification
- OAuth/social auth
- session persistence and refresh

FastAPI is responsible for:

- verifying Supabase bearer tokens through JWKS
- enforcing issuer, audience, and expiration checks
- loading or auto-creating the domain `users` and `user_profile` rows
- RBAC and downstream authorization

## Canonical backend dependency

Protected backend routes now resolve identity through `apps/backend/core/auth.py`.

Primary dependencies:

- `get_supabase_claims_from_header()`
- `get_current_user_from_header()`
- `get_current_doctor_from_header()`

Legacy mixed-token resolution in `apps/backend/routes/users.py` was removed in favor of those shared Supabase-only dependencies.

## Deprecated backend auth endpoints

The following routes are intentionally retained but return `410 Gone`:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/refresh-token`
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/oauth`
- `PUT /api/v1/auth/update-password`

These endpoints are preserved as explicit migration markers so old callers fail clearly instead of silently using the wrong authority.

## Frontend auth cleanup

Frontend email login now uses Supabase `signInWithPassword`.

Session restoration now:

1. reads the current Supabase session
2. refreshes it through Supabase when needed
3. synchronizes the domain user through `/api/v1/auth/social-login`
4. hydrates the canonical profile bundle through `GET /api/v1/profile`

Duplicate client implementations were collapsed by making `apps/frontend/src/lib/apiClient.ts` a thin alias of `apps/frontend/src/lib/axios.js`.

## Identity linking

`user_profile.supabase_id` is the canonical identity key for domain linkage.

Linking behavior:

- existing linked users are resolved by `user_profile.supabase_id`
- legacy rows can be adopted by matching email once
- missing `users`, `user_profile`, and `user_settings` rows are auto-created

## Rollback notes

Rollback is safe as long as:

- Supabase remains the login authority
- deprecated backend endpoints stay present
- `user_profile.supabase_id` is not removed

Do not re-enable backend HS256 access-token issuance unless the frontend is also reverted to the old login/refresh flow.
