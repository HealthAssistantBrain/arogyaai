# ArogyaAI Navigation Architecture (Final)

> **Version:** 3.0 — Production-Ready Edition  
> **Base Source:** ArogyaAI Navigation · Routing · Debug Structure v2.0  
> **Scope:** 59 Routes · 11 Modules · 65 API Endpoints  
> **Status:** FINAL — Debuggable · Loop-Safe · Scalable · Backend-Synced

---

## 1. Route Tree

> All 59 routes across 11 modules. Dynamic routes marked `[DYNAMIC]`. New v2.0 routes marked `[★]`. Guard annotations are **authoritative** — no route renders without completing its guard chain.

```
ROOT /
│
├── [MODULE 1] AUTHENTICATION — 7 routes — PUBLIC / GUEST_GUARD
│   ├── /                          → Landing Page                        [PUBLIC]
│   ├── /login                     → Login                               [GUEST_GUARD]
│   ├── /signup                    → Sign Up                             [GUEST_GUARD]
│   ├── /forgot-password           → Forgot Password                     [PUBLIC]
│   ├── /email-verification        → Email Verification           [★]    [GUEST_GUARD + EMAIL_VERIFICATION_GUARD]
│   ├── /reset-password            → Reset Password               [★]    [PUBLIC · query: ?token=<jwt>]
│   └── /account-created           → Account Created / Welcome    [★]    [GUEST_GUARD]
│
├── [MODULE 2] ONBOARDING — 6 routes — AUTH_GUARD + ONBOARDING_GUARD
│   ├── /onboarding                → Namespace redirect (→ step-1)
│   ├── /onboarding/step-1         → Basic Profile                       [step=1]
│   ├── /onboarding/step-2         → Medical History                     [step=2]
│   ├── /onboarding/step-3         → Lifestyle Assessment                [step=3]
│   ├── /onboarding/step-4         → Device Connection                   [step=4]
│   ├── /onboarding/summary        → Onboarding Summary           [★]    [step=5]
│   └── /onboarding/completion     → Onboarding Completion        [★]    [step=6 · final gate]
│
├── [MODULE 3] DASHBOARD — 2 routes — AUTH_GUARD + ONBOARDING_GUARD
│   ├── /dashboard                 → Main Dashboard                      [default authenticated entry]
│   └── /dashboard/alt             → Dashboard Alternate View            [responsive alt layout]
│
├── [MODULE 4] HEALTH INTELLIGENCE — 8 routes — AUTH_GUARD + DATA_GUARD
│   ├── /insights                  → AI Health Insights                  [primary ML output]
│   ├── /insights/desktop          → AI Insights Desktop Layout   [★]    [viewport ≥ 1024px]
│   ├── /simulator                 → Disease Simulator            [★]    [POST /prediction/simulate]
│   ├── /timeline                  → Health Timeline              [★]    [GET /health/timeline]
│   ├── /risk-explanation          → Risk Explanation             [★]    [SHAP factors]
│   ├── /recommendations           → Preventive Recommendations   [★]    [GET /prediction/shap-factors]
│   ├── /risk-report               → AI Risk Report               [★]    [GET /health/reports/export]
│   └── /aqi-monitor               → Air Quality Risk Monitor     [★]    [NEW CAPABILITY]
│
├── [MODULE 5] MEDICAL DATA — 8 routes — AUTH_GUARD + DATA_GUARD (partial)
│   ├── /lab-results               → Lab Test Results                    [GET /lab/reports · last uploaded]
│   ├── /medical-reports           → Medical Reports                     [GET /lab/reports · paginated]
│   ├── /sleep                     → Sleep Analysis                      [wearable sleep metrics]
│   ├── /devices                   → Device Manager                      [wearable device list]
│   ├── /devices/settings/:id      → Device Settings              [DYNAMIC · id=device UUID]
│   ├── /upload                    → Upload Medical Report        [★]    [POST /lab/upload]
│   ├── /report-processing         → Report Processing            [★]    [OCR in progress · polling]
│   └── /upload-success            → Upload Success               [★]    [confirmation · transient]
│
├── [MODULE 6] CONSULTATION — 4 routes — AUTH_GUARD
│   ├── /consultation              → Book Consultation                   [doctor list]
│   ├── /consultation/doctor/:id   → Doctor Profile               [★]    [DYNAMIC · id=doctor UUID]
│   ├── /consultation/confirm      → Appointment Confirmation     [★]    [POST /consultation/book]
│   └── /consultation/history      → Consultation History         [★]    [GET /consultation/history]
│
├── [MODULE 7] SETTINGS / ACCOUNT — 8 routes — AUTH_GUARD + SESSION_GUARD
│   ├── /settings                  → Settings Hub
│   ├── /settings/profile          → User Profile                        [GET /user/profile]
│   ├── /settings/security         → Security Audit               [★]    [GET /auth/sessions]
│   ├── /settings/privacy          → Data Privacy                        [GET /user/privacy-settings]
│   ├── /settings/notifications    → Notification Settings               [PUT /user/notifications-pref]
│   ├── /settings/password         → Change Password              [★]    [POST /auth/change-password]
│   ├── /settings/delete           → Delete Account               [★]    [DELETE /user/account]
│   └── /logout                    → Logout Confirmation          [★]    [POST /auth/logout]
│
├── [MODULE 8] NOTIFICATIONS — 4 routes — AUTH_GUARD
│   ├── /notifications             → Notification Centre                 [GET /notifications]
│   ├── /notifications/history     → Notification History                [GET /notifications?page=N]
│   ├── /notifications/alert/:id   → Alert Details               [★]    [DYNAMIC · id=notification UUID]
│   └── /notifications/emergency   → Emergency Alert             [★]    [full-screen · no-dismiss]
│
├── [MODULE 9] HELP CENTER — 3 routes — PUBLIC  [★ NEW MODULE]
│   ├── /help                      → Help Center Home                    [GET /help/articles]
│   ├── /help/search               → Help Center Search                  [GET /help/search?q=]
│   └── /help/article/:slug        → Help Center Article         [DYNAMIC · slug=URL-safe string]
│
├── [MODULE 10] LEGAL — 3 routes — PUBLIC  [★ NEW MODULE]
│   ├── /terms                     → Terms of Service                    [GET /legal/terms]
│   ├── /privacy                   → Privacy Policy                      [GET /legal/privacy]
│   └── /data-consent              → Data Consent                        [POST /auth/consent]
│
└── [MODULE 11] SYSTEM — 6 routes — PUBLIC / AUTO-ROUTED
    ├── /loading                   → Loading Screen                      [app bootstrap · blocks render]
    ├── /status                    → System Status                       [GET /health · live]
    ├── /whats-new                 → What's New                          [release changelog]
    ├── /404                       → 404 Not Found               [★]    [wildcard catch *]
    ├── /500                       → 500 Internal Server Error   [★]    [global error boundary]
    ├── /maintenance               → Maintenance Page            [★]    [auto-refresh 60s]
    └── /system/error              → Loop / Critical Error               [loop detector escape hatch]
```

### Dynamic Route Index

| Route | Param | Type | Validation |
|---|---|---|---|
| `/devices/settings/:id` | `id` | UUID v4 | regex `/^[0-9a-f-]{36}$/` |
| `/consultation/doctor/:id` | `id` | UUID v4 | regex `/^[0-9a-f-]{36}$/` |
| `/notifications/alert/:id` | `id` | UUID v4 | regex `/^[0-9a-f-]{36}$/` |
| `/help/article/:slug` | `slug` | URL-safe string | regex `/^[a-z0-9-]+$/` |

### Route Access Matrix

| Module | Public | Auth Required | Onboarding Required | Data Required |
|---|---|---|---|---|
| Authentication | ✅ | — | — | — |
| Onboarding | — | ✅ | ❌ (in progress) | — |
| Dashboard | — | ✅ | ✅ | — |
| Health Intelligence | — | ✅ | ✅ | ✅ |
| Medical Data | — | ✅ | ✅ | Partial |
| Consultation | — | ✅ | ✅ | — |
| Settings / Account | — | ✅ | ✅ | — |
| Notifications | — | ✅ | ✅ | — |
| Help Center | ✅ | — | — | — |
| Legal | ✅ | — | — | — |
| System | ✅ | — | — | — |

---

## 2. Navigation Flow

> All flows are **deterministic**. Every branch has exactly one outcome. No ambiguous forks.

### 2.1 Global Entry — INIT_RESOLVER

```
APP_MOUNT
    │
    ├── show /loading (block all render)
    │
    ├── PARALLEL CHECKS:
    │   ├── [A] GET /health                    → backend liveness
    │   ├── [B] GET /auth/me (if token exists) → validate session
    │   └── [C] localStorage.getItem('token')  → hydrate store
    │
    ├── IF [A] fails (timeout > 5s OR non-200)
    │   └── → /maintenance
    │
    ├── IF [A] OK AND [C] empty
    │   └── → /  (Landing Page)
    │
    ├── IF [A] OK AND [C] present AND [B] returns 401
    │   └── → clear token → /login [state: { sessionExpired: true }]
    │
    ├── IF [A] OK AND [B] returns user { onboardingDone: false, onboardingStep: N }
    │   └── → /onboarding/step-{N}  (resume)
    │
    └── IF [A] OK AND [B] returns user { onboardingDone: true }
        └── → /dashboard
```

### 2.2 Module 1 — Authentication Flow

```
/
├── [CTA: Login]   → /login
└── [CTA: Sign Up] → /terms → /privacy → /data-consent
                                              │
                                    [accept] → POST /auth/register
                                              → /email-verification
                                              │
                                    /email-verification
                                    ├── [link clicked] GET /auth/verify?token=
                                    │   ├── valid   → /account-created → (3s) → /onboarding/step-1
                                    │   └── expired → /email-verification [state: { expired: true }]
                                    └── [resend]  POST /auth/resend-verification

/login
├── [credentials OK, onboardingDone=true]  → /dashboard
├── [credentials OK, onboardingDone=false] → /onboarding/step-{N}
├── [email_not_verified]                   → /email-verification
└── [credentials FAIL]                     → /login [inline error · no navigate]

/forgot-password → POST /auth/forgot-password → email sent toast
    └── email link → /reset-password?token=<token>
                        ├── [mount: validate token] GET /auth/validate-token?token=
                        │   ├── valid   → show form → POST /auth/reset-password → /login
                        │   └── expired → /forgot-password [toast: 'Link expired']
                        └── [no token param] → /404
```

### 2.3 Module 2 — Onboarding Flow (Sequential · Enforced)

```
/onboarding/step-1 [POST /user/profile]
    → /onboarding/step-2 [POST /user/medical-history]
        → /onboarding/step-3 [POST /user/lifestyle]
            → /onboarding/step-4 [POST /wearable/providers]
                → /onboarding/summary
                    │
                    ├── [edit step N] → /onboarding/step-N?return=summary
                    │                   └── [submit] → /onboarding/summary  (return)
                    │
                    ├── [confirm]    → POST /prediction/compute
                    │                   ├── [202 Accepted] → /onboarding/completion
                    │                   │       └── poll GET /health/score
                    │                   │           ├── [ready]   → set onboardingDone=true (backend+store) → (3s) → /dashboard
                    │                   │           └── [timeout] → show retry CTA
                    │                   └── [error] → inline error on /onboarding/summary
                    │
                    └── [back]       → /onboarding/step-4

RULE: Each step validates onboardingStep from backend on mount.
      Step access denied if onboardingStep < requested step.
```

### 2.4 Module 3 — Dashboard Flow

```
/dashboard
├── [AI insights card]       → /insights
├── [notification bell]      → /notifications
├── [lab results card]       → /lab-results
├── [book doctor CTA]        → /consultation
├── [timeline card]          → /timeline
├── [upload prompt]          → /upload
└── [toggle: alt view]       ↔ /dashboard/alt
```

### 2.5 Module 4 — Health Intelligence Flow

```
/insights
├── [viewport ≥ 1024px toggle] → /insights/desktop  ↔ /insights
├── [risk detail]              → /risk-explanation
│       ├── [view actions]     → /recommendations
│       └── [book consult]     → /consultation
├── [simulate]                 → /simulator
│       ├── [generate report]  → /risk-report
│       └── [book doctor]      → /consultation
├── [timeline CTA]             → /timeline
│       ├── [alert event]      → /notifications/alert/:id
│       └── [lab event]        → /lab-results
├── [recommendations]          → /recommendations
├── [generate report]          → /risk-report
│       ├── [view recs]        → /recommendations
│       ├── [book doctor]      → /consultation
│       └── [back]             → /dashboard
└── [AQI widget]               → /aqi-monitor → back → /insights
```

### 2.6 Module 5 — Medical Data Flow

```
/upload → POST /lab/upload
    ├── [success] → /report-processing
    │       ├── poll GET /lab/reports/:id every 5s (max 24 polls)
    │       ├── [status: complete]  → /upload-success
    │       │       ├── [view results]  → /lab-results
    │       │       └── [view insights] → /insights
    │       ├── [status: failed]    → /500 [retry → /upload]
    │       └── [timeout: 2min]     → inline error + retry CTA → /upload
    └── [cancel] → /lab-results

/devices → /devices/settings/:id  [DYNAMIC_ROUTE_GUARD · UUID validation]
/lab-results → /timeline [event tap] / /sleep [sleep event tap]
```

### 2.7 Module 6 — Consultation Flow

```
/consultation
    → /consultation/doctor/:id   [DYNAMIC_ROUTE_GUARD]
        → /consultation/confirm  [POST /consultation/book]
            ├── [booked]  → /consultation/history
            └── [cancel]  → /consultation
/consultation/history
    ├── [doctor tap]   → /consultation/doctor/:id
    ├── [book again]   → /consultation
    └── [cancel appt]  → PUT /consultation/:id/cancel → refresh list
```

### 2.8 Module 7 — Settings / Account Flow

```
/settings
├── /settings/profile
├── /settings/security
│       ├── [force logout all] DELETE /auth/sessions → /login
│       └── [change password]  → /settings/password
├── /settings/privacy   → [manage consent] → /data-consent
├── /settings/notifications
├── /settings/password  [POST /auth/change-password]
│       ├── [success] → /login  (re-auth enforced)
│       └── [cancel]  → /settings
├── /settings/delete    [3-step confirmation · transactional]
│       └── [confirm final] → soft-delete → /logout
└── /logout
        ├── [confirm] POST /auth/logout → clear store → /
        └── [cancel]  → /settings
```

### 2.9 Module 8 — Notifications Flow

```
/notifications
├── [alert tap]  → /notifications/alert/:id
│       ├── [risk detail] → /risk-explanation
│       ├── [book consult] → /consultation
│       └── [back] → /notifications
├── [view all]   → /notifications/history
└── [emergency]  → /notifications/emergency  [NO browser-back dismiss]
        ├── [view insights] → /insights
        └── [book doctor]   → /consultation
```

### 2.10 Modules 9–10 — Help + Legal Flow

```
/help → /help/search → /help/article/:slug  [DYNAMIC]
/terms    → [accept]   → /signup
/privacy  → [continue] → /data-consent
/data-consent
    ├── [accept · onboarding context] → /onboarding/step-1
    └── [accept · settings context]   → /settings/privacy
```

### 2.11 Module 11 — System Flow

```
unmatched route          → /404  [React Router wildcard *]
global error boundary    → /500
/500
    ├── [check status]   → /status
    └── [go home]        → /
maintenanceMode = true   → /maintenance  [all routes intercepted]
/maintenance             → poll GET /health every 60s → auto-redirect on recovery
loop detector fires      → /system/error  [always reachable · no guards applied]
```

---

## 3. Route Guards

### 3.1 Guard Definitions

#### AUTH_GUARD
```
APPLIES TO : All protected routes (Modules 2–8)
TRIGGER    : useAuthStore.isAuthenticated === false
             OR no token in store/localStorage
             OR GET /auth/me returns 401

ACTION     :
  1. Save currentLocation.pathname → state.from
  2. navigate('/login', { state: { from: currentLocation } })
  3. Post-login success → navigate(state.from ?? '/dashboard')

NOTE       : Never trust localStorage alone.
             Always verify with GET /auth/me during INIT.
```

#### GUEST_GUARD
```
APPLIES TO : /login, /signup, /account-created, /email-verification
TRIGGER    : useAuthStore.isAuthenticated === true

ACTION     :
  IF onboardingDone === true  → navigate('/dashboard')
  IF onboardingDone === false → navigate('/onboarding/step-' + onboardingStep)

NOTE       : Prevents authenticated users from re-entering auth pages.
             Must run AFTER auth store is hydrated.
```

#### ONBOARDING_GUARD
```
APPLIES TO : /dashboard and all Modules 3–8
TRIGGER    : isAuthenticated === true AND onboardingDone === false

ACTION     :
  Read onboardingStep (authoritative source: backend, not store)
  step 0–1  → /onboarding/step-1
  step 2    → /onboarding/step-2
  step 3    → /onboarding/step-3
  step 4    → /onboarding/step-4
  step 5    → /onboarding/summary
  step 6+   → /onboarding/completion

NOTE       : onboardingStep MUST be fetched from GET /user/onboarding-status.
             Do NOT rely on store value alone — it may be stale after back-navigation.
```

#### EMAIL_VERIFICATION_GUARD
```
APPLIES TO : Login flow
TRIGGER    : POST /auth/login response body contains { error: 'email_not_verified' }

ACTION     :
  1. DO NOT set isAuthenticated = true
  2. Store pendingEmail in sessionStorage
  3. navigate('/email-verification')
  4. On /email-verification: POST /auth/resend-verification on demand
```

#### DATA_GUARD
```
APPLIES TO : /insights, /simulator, /risk-explanation, /recommendations,
             /risk-report, /lab-results
TRIGGER    : GET /health/score → { status: 'no_data' } OR score === null

ACTION     :
  DO NOT redirect
  Render in-page empty state UI:
    → CTA: "Upload Lab Report" → /upload
    → CTA: "Connect Wearable" → /devices
  Block: simulation, report generation, SHAP factor fetch

NOTE       : Non-redirecting guard. Inline degradation only.
```

#### SESSION_GUARD
```
APPLIES TO : All authenticated API calls (Axios interceptor layer)
TRIGGER    : Any API response with HTTP 401

ACTION     :
  1. Attempt POST /auth/refresh { refresh_token }
  2. IF 200 → store new access token → retry original request (once only)
  3. IF 401/403 on refresh:
       clearAuthStore()
       clearLocalStorage(['token', 'refreshToken', 'user'])
       navigate('/login', { state: { sessionExpired: true } })
       toast('Session expired. Please log in again.')

NOTE       : Max 1 refresh attempt per request. No infinite refresh chains.
             Use a request queue to prevent concurrent refresh storms.
```

#### API_GUARD
```
APPLIES TO : All API calls (global Axios interceptor)
TRIGGER    : ERR_CONNECTION_REFUSED
             OR response timeout > 10s
             OR GET /health returns non-200

ACTION     :
  IF health check fails → maintenanceMode = true → navigate('/maintenance')
  IF single endpoint fails → show inline error + retry button
  DO NOT redirect globally on single endpoint failure

NOTE       : Timeout threshold is 10s per request, not 30s (30s is excessive for UX).
```

#### DYNAMIC_ROUTE_GUARD
```
APPLIES TO : /devices/settings/:id, /consultation/doctor/:id,
             /notifications/alert/:id, /help/article/:slug
TRIGGER    : Component mount with :param value

ACTION     :
  1. Validate param format (UUID regex or slug regex) BEFORE API call
  2. IF invalid format → navigate('/404')
  3. IF format valid → fire API request
  4. IF API returns 404 → navigate('/404')
  5. IF API returns 403 → AUTH_GUARD takes over → navigate('/login')
```

---

## 4. Error Handling

### 4.1 HTTP Error Map

| Code | Name | Cause | Frontend Action |
|---|---|---|---|
| `400` | Bad Request | Malformed body, invalid token param | Inline form error · no navigate |
| `401` | Unauthorized — Token Invalid | JWT absent, expired, or signature fail | SESSION_GUARD → refresh → /login |
| `401` | Unauthorized — Email Unverified | `email_not_verified` in response body | EMAIL_VERIFICATION_GUARD → /email-verification |
| `403` | Forbidden | Resource belongs to another user | Navigate /404 (obscure existence) · log security event |
| `404` | Not Found | Route, endpoint, or resource missing | Inline error or /404 depending on context |
| `409` | Conflict | Duplicate email on register, duplicate booking | Inline error · do not navigate |
| `422` | Unprocessable Entity | Validation failure | Field-level errors in form · no navigate |
| `429` | Rate Limited | Too many auth requests | Disable submit · countdown toast · auto-retry |
| `500` | Internal Server Error | Backend crash, DB failure, Celery task crash | Navigate /500 · offer retry + /status CTA |
| `503` | Service Unavailable | Backend in maintenance, overloaded | maintenanceMode=true → /maintenance |

### 4.2 Network-Level Errors

| Error | Symptom | Action |
|---|---|---|
| `ERR_CONNECTION_REFUSED` | API calls all fail silently | Axios interceptor → GET /health → if fails → /maintenance |
| `ERR_NETWORK` | DNS failure, no internet | Show inline "No connection" toast · retry button |
| `ERR_TIMED_OUT` | Request exceeds 10s | Abort via AbortController · show timeout error inline |
| CORS policy blocked | No 4xx visible · console error only | Log to Sentry · show "Service unavailable" inline |

### 4.3 Database / Infrastructure Errors

| ID | Name | Cause | Detection | Fix |
|---|---|---|---|---|
| `DB-1` | Table Missing | Docker volume reset without Alembic migration | Backend 500 on all data endpoints | `alembic upgrade head` before app starts |
| `DB-2` | TimescaleDB Extension Absent | Clean Docker install · extension not initialized | `hypertable` creation 500 | `CREATE EXTENSION IF NOT EXISTS timescaledb;` in init SQL |
| `DB-3` | Qdrant Collection Missing | Container restart without persistent volume | RAG endpoints return 500 | Re-create collection · re-embed documents |
| `DB-4` | Redis Unavailable | Redis container stopped | Celery queue fails · session ops fail | `docker compose up redis -d` |
| `DB-5` | RabbitMQ Broker Down | Celery worker cannot connect | All async tasks silently queue forever | Check `RABBITMQ_URL` in env · restart broker container |
| `DB-6` | Feast Feature Store Stale | Feature view not materialized after schema change | ML prediction returns stale values | `feast materialize-incremental $(date +%Y-%m-%dT%H:%M:%S)` |

### 4.4 Routing Errors

| ID | Cause | Symptom | Fix |
|---|---|---|---|
| `RT-1` | Invalid dynamic param (not UUID) | Component crash or silent 500 | DYNAMIC_ROUTE_GUARD pre-validates param before mount |
| `RT-2` | Stale Zustand after logout + browser back | Protected route renders with dead token | Clear store on logout · SESSION_GUARD on all 401s |
| `RT-3` | Deep link to protected route pre-auth | state.from lost · user lands on /dashboard after login blindly | AUTH_GUARD stores from.pathname · restores post-login |
| `RT-4` | /onboarding namespace accessed directly | No redirect logic on parent route | /onboarding → redirect to /onboarding/step-1 explicitly |
| `RT-5` | /report-processing accessed without upload context | No reportId in state · polling fails immediately | On mount: if no reportId in location.state → redirect /upload |

### 4.5 Celery / Async Task Errors

| Task | Failure Mode | Frontend Detection | Recovery |
|---|---|---|---|
| OCR Processing | Task crashes mid-execution | `GET /lab/reports/:id` → `{ status: 'failed' }` | Show error + retry CTA → /upload |
| ML Prediction (onboarding) | `POST /prediction/compute` times out | Poll `GET /health/score` → no `ready` in 5min | Show retry on /onboarding/completion |
| Wearable Sync | Celery worker queue overflow | `GET /wearable/metrics/:type` returns stale data | Show "Data may be outdated" banner · manual sync CTA |

---

## 5. Edge Cases

### EDGE-01 — Direct URL Access Bypassing Auth

```
TRIGGER  : Browser bar navigation to /dashboard without session
SYMPTOM  : Zustand not hydrated at render time → AUTH_GUARD does not fire → page flash
FIX      : Render /loading until INIT_RESOLVER completes (blocks all route render)
           INIT_RESOLVER validates session BEFORE routing decision
           No route renders without resolved auth state
```

### EDGE-02 — Docker Volume Reset / Empty Database

```
TRIGGER  : docker compose down -v → all Postgres data destroyed
SYMPTOM  : Backend 500 on all data endpoints · app unusable
FIX      : Compose healthcheck on postgres before app starts
           Entrypoint runs: alembic upgrade head && python scripts/seed.py
           Add: depends_on: postgres: condition: service_healthy
```

### EDGE-03 — Backend Not Running / Frontend Loads

```
TRIGGER  : FastAPI container stopped · Nginx serves frontend correctly
SYMPTOM  : All API calls return ERR_CONNECTION_REFUSED · app appears frozen
FIX      : Global Axios interceptor catches network errors
           INIT_RESOLVER: GET /health timeout → /maintenance (non-blocking render of maintenance page)
```

### EDGE-04 — API Prefix Mismatch

```
TRIGGER  : VITE_API_BASE_URL missing /api/v1 prefix
SYMPTOM  : All calls return 404 despite backend healthy
FIX      : Axios baseURL = process.env.VITE_API_BASE_URL (must be http://host:port/api/v1)
           CI/CD pipeline: assert VITE_API_BASE_URL ends with /api/v1 before build
           Verify: curl $VITE_API_BASE_URL/health returns 200
```

### EDGE-05 — Remote Session Revocation (State Desync)

```
TRIGGER  : Admin or security audit revokes session while user is active
SYMPTOM  : Zustand shows isAuthenticated=true · all API calls return 401 · empty screens
FIX      : Global 401 interceptor fires SESSION_GUARD
           Refresh attempt → if fails → clearAuthStore() → navigate /login
           Never render protected content after 401 + failed refresh
```

### EDGE-06 — Onboarding Step Skip via Browser URL

```
TRIGGER  : Manual navigation to /onboarding/step-4 while on step-2
SYMPTOM  : Step-4 data submitted without step-2/3 data → silent data gaps
FIX      : ONBOARDING_GUARD fetches onboardingStep from GET /user/onboarding-status on EVERY step mount
           IF requested step > authoritative step → redirect to authoritative step
```

### EDGE-07 — Password Reset Link Expired

```
TRIGGER  : User clicks reset link after TTL=1h expires
SYMPTOM  : POST /auth/reset-password returns 400 · user stuck on form
FIX      : On /reset-password mount:
             IF no ?token param → navigate /404
             ELSE GET /auth/validate-token?token=
               valid   → render form
               invalid → navigate /forgot-password [toast: 'Link expired. Request a new one.']
```

### EDGE-08 — OCR Polling Memory Leak

```
TRIGGER  : User navigates away from /report-processing during polling
SYMPTOM  : setInterval continues in background · ghost fetches · potential double-navigate on return
FIX      : useEffect cleanup: clearInterval(intervalRef.current)
           AbortController per fetch call
           Polling state stored in ref (not state) to avoid re-render loops
           On remount: if reportId matches a completed report → skip polling → navigate /upload-success
```

### EDGE-09 — External AQI API Unavailable

```
TRIGGER  : AQI provider returns 503 or backend rate-limited
SYMPTOM  : GET /health/aqi-risk returns 503 · /aqi-monitor page blank
FIX      : Backend: cache last AQI data in Redis (TTL 30min)
           Frontend: show stale-data banner with timestamp
           Graceful degradation: render risk overlay with "Data unavailable" state
```

### EDGE-10 — Emergency Alert Back-Button Dismiss

```
TRIGGER  : /notifications/emergency (full-screen) · user presses browser back
SYMPTOM  : Alert dismissed without acknowledgement · critical health event missed
FIX      : useBlocker (React Router v6) while on /notifications/emergency
           Block navigation until user explicitly taps acknowledge or dismiss
           Log acknowledgement: PUT /notifications/:id/acknowledge
```

### EDGE-11 — Concurrent Multi-Device Sessions

```
TRIGGER  : Same user logged in on mobile + desktop
SYMPTOM  : Older device token silently invalid · 401 on data fetches
FIX      : SESSION_GUARD handles 401 on each device independently
           /settings/security shows all active sessions via GET /auth/sessions
           User can revoke individual sessions: DELETE /auth/sessions/:sessionId
```

### EDGE-12 — Delete Account Flow Interrupted Mid-Confirmation

```
TRIGGER  : User closes browser during 3-step delete confirmation
SYMPTOM  : Account in ambiguous soft-delete state · re-login may partially succeed
FIX      : Soft-delete only executed on FINAL confirmation POST
           Nightly cleanup job removes stale soft-delete flags older than 48h
           Re-login attempt with soft-deleted account → return 403 with account_deleted error
             → navigate /account-created [state: { deleted: true }] with recovery option
```

### EDGE-13 — /consultation/confirm Revisited via Back

```
TRIGGER  : User presses back from /consultation/history to /consultation/confirm
SYMPTOM  : Re-submission of POST /consultation/book → duplicate booking
FIX      : /consultation/confirm stores bookingId in location.state on success
           On mount: if bookingId already exists → redirect /consultation/history immediately
           Backend: idempotency key on POST /consultation/book
```

### EDGE-14 — /onboarding/completion Auto-redirect Interrupted

```
TRIGGER  : User closes tab during 3s auto-redirect after completion
SYMPTOM  : onboardingDone set to true on backend but false in Zustand · ONBOARDING_GUARD loops
FIX      : INIT_RESOLVER always fetches onboarding status from backend on app mount
           Backend is authoritative source — Zustand mirrors, never leads
```

### EDGE-15 — Mobile Viewport on /insights/desktop

```
TRIGGER  : User directly navigates to /insights/desktop on a mobile viewport (< 1024px)
SYMPTOM  : Layout broken · no redirect logic to /insights mobile view
FIX      : /insights/desktop: on mount check window.innerWidth < 1024 → navigate /insights
           Responsive listener: if resize below 1024 → navigate /insights automatically
```

---

## 6. Identified Flaws ⚠️

### FLAW-01 — No Single-Redirect Enforcement on Guards

```
NAME   : Guard Double-Fire / Multiple Redirect Chain
CAUSE  : Multiple guards (AUTH + ONBOARDING + DATA) can each independently fire
         and navigate in the same render cycle. No gate prevents two guards from
         both calling navigate() on the same route transition.
IMPACT : Multiple navigation events queued. Race condition between guard redirects.
         Console errors. React Router history corruption.
FIX    : Implement single-redirect enforcement:
           const redirectFired = useRef(false)
           In each guard: IF redirectFired.current === true → return (abort)
           ELSE redirectFired.current = true → navigate(...)
         Reset redirectFired on successful route resolution.
         Centralize all guard logic through INIT_RESOLVER before render.
```

### FLAW-02 — Zustand Hydration Race Condition

```
NAME   : Store Not Ready at Route Evaluation
CAUSE  : React renders route components before Zustand's persist middleware
         rehydrates from localStorage. Guards read isAuthenticated=false
         on first render even if a valid token exists.
IMPACT : Flash of login page for authenticated users. AUTH_GUARD misfires.
         Possible double-redirect on app load.
FIX    : Add hasHydrated flag to Zustand store:
           const useAuthStore = create(persist(..., {
             onRehydrateStorage: () => (state) => { state.setHydrated(true) }
           }))
         Block all route rendering until hasHydrated === true (show /loading).
         INIT_RESOLVER only runs after hasHydrated === true.
```

### FLAW-03 — Onboarding Step Authority Conflict (Store vs Backend)

```
NAME   : Split-Brain Onboarding State
CAUSE  : ONBOARDING_GUARD reads onboardingStep from Zustand store.
         Store can be stale after browser back or partial submissions.
         Step N may appear complete in store but incomplete on backend.
IMPACT : User advances to step N+1 with missing backend data.
         ML prediction computed on incomplete profile. Silent data corruption.
FIX    : ONBOARDING_GUARD must ALWAYS call GET /user/onboarding-status before redirecting.
         Never route based on store onboardingStep alone.
         Backend is single source of truth for step progress.
```

### FLAW-04 — SESSION_GUARD Refresh Storm

```
NAME   : Concurrent 401 → Multiple Parallel Refresh Calls
CAUSE  : Multiple API calls fire simultaneously. All return 401.
         SESSION_GUARD fires for each one independently.
         Multiple POST /auth/refresh calls sent in parallel.
IMPACT : Refresh token consumed/rotated by first call. All subsequent refresh calls fail.
         User logged out unexpectedly despite valid session.
FIX    : Implement refresh queue in Axios interceptor:
           let isRefreshing = false
           let failedQueue: Promise[] = []
           IF isRefreshing → queue request
           ELSE isRefreshing = true → POST /auth/refresh
                → on success: process queue with new token
                → on fail: reject all queued requests → logout
```

### FLAW-05 — /reset-password Missing Token Param Validation on Mount

```
NAME   : Silent Crash on /reset-password Without Token
CAUSE  : User navigates to /reset-password directly (no ?token param).
         Component mounts, form renders, POST /auth/reset-password fires with no token.
         API returns 400. User sees generic error with no guidance.
IMPACT : Confusing UX. No escape path. User cannot resolve without manual URL correction.
FIX    : On /reset-password mount:
           IF !searchParams.get('token') → navigate('/404') immediately
           ELSE validate token via GET /auth/validate-token?token= before rendering form
```

### FLAW-06 — /report-processing Accessible Without Upload Context

```
NAME   : Orphaned Processing Screen
CAUSE  : /report-processing can be accessed directly via URL with no reportId
         in location.state (not passed by /upload redirect).
IMPACT : Polling fires with undefined reportId. GET /lab/reports/undefined returns 404.
         User sees infinite processing spinner with no escape.
FIX    : On /report-processing mount:
           IF !location.state?.reportId → navigate('/upload') immediately
           ELSE start polling with validated reportId
```

### FLAW-07 — /consultation/confirm Lacks Idempotency Protection

```
NAME   : Duplicate Booking on Page Refresh / Back-Navigation
CAUSE  : /consultation/confirm component mounts with booking data in location.state.
         User refreshes page → POST /consultation/book fires again.
IMPACT : Duplicate appointments created. Double-charges if paid. Confusing history.
FIX    : Frontend: store bookingId in sessionStorage after first POST.
         On remount: if sessionStorage.bookingId exists → navigate /consultation/history.
         Backend: enforce idempotency key (slot_id + doctor_id + user_id + date) → return 409 on duplicate.
```

### FLAW-08 — CORS Error Invisible to Error Handling Pipeline

```
NAME   : CORS Failures Bypass All Error Interceptors
CAUSE  : Browser blocks CORS responses before they reach Axios interceptors.
         Error appears only in DevTools console as a network error, not as a 4xx/5xx.
         Global error handling does not catch CORS failures.
IMPACT : App silently fails. No toast, no redirect, no user feedback.
FIX    : Configure FastAPI CORS exactly:
           allow_origins = [FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"]
         Never use allow_origins=["*"] in production.
         Add CI assertion: FRONTEND_URL env var must be set before deployment.
         Catch ERR_NETWORK in Axios interceptor as a fallback for CORS-style failures.
```

### FLAW-09 — No Centralized Route Configuration

```
NAME   : Distributed Route Definitions (No Single Registry)
CAUSE  : Routes defined across multiple files/components with no central registry.
         Guard assignments are implicit (applied at component level).
IMPACT : Adding a new route requires updating multiple files.
         Easy to forget guard assignment on new routes.
         No programmatic way to audit route access policies.
FIX    : Create routes.config.ts:
           interface RouteConfig {
             path: string
             component: React.LazyExoticComponent<any>
             guards: Guard[]
             module: string
             public: boolean
           }
           export const ROUTES: RouteConfig[] = [...]
         All guard assignments live in ROUTES. No guards at component level.
         Generate route audit report from ROUTES config automatically.
```

### FLAW-10 — Emergency Alert Has No Acknowledgement Persistence

```
NAME   : Emergency Alert Acknowledgement Not Synced to Backend
CAUSE  : /notifications/emergency blocks navigation but does not persist
         acknowledgement to backend when user taps dismiss.
IMPACT : Emergency alert re-appears on next app load. User sees same critical alert repeatedly.
FIX    : On acknowledge: PUT /notifications/:id/acknowledge
         Store acknowledged IDs in Zustand + backend.
         On /notifications/emergency mount: check if already acknowledged → skip to /dashboard.
```

### FLAW-11 — Onboarding /completion Auto-Redirect Ignores Prediction Failure

```
NAME   : False Completion on Prediction Timeout
CAUSE  : /onboarding/completion sets onboardingDone=true and redirects /dashboard
         after 3s regardless of whether POST /prediction/compute has resolved.
IMPACT : User enters /dashboard with no baseline health score.
         DATA_GUARD fires immediately → empty state on /insights.
         Prediction may never complete if backend Celery worker is busy.
FIX    : DO NOT auto-redirect after 3s blindly.
         Poll GET /health/score until { status: 'ready' } OR timeout (5min).
         Show progress indicator on /onboarding/completion during poll.
         Only set onboardingDone=true AND redirect AFTER prediction is confirmed ready.
         On timeout: allow user to proceed with "Prediction still computing" banner on dashboard.
```

### FLAW-12 — Missing /system/error Route in Router Config

```
NAME   : Loop Detector Escape Route Not Registered
CAUSE  : /system/error is the designated escape hatch for the loop detector.
         If this route is not explicitly registered in React Router, the loop detector
         navigate('/system/error') itself causes a 404 → loop detector fires again → infinite loop.
IMPACT : Loop detector creates a new loop on its own escape route.
FIX    : Register /system/error as the FIRST route in router config.
         Apply NO guards to /system/error — it must always be reachable.
         Render: error details (dev mode) + "Clear session and restart" CTA.
```

---

## 7. Error-Causing Logic

### BUG-01 — Auth Infinite Loop

```
STEPS:
  1. AUTH_GUARD fires → isAuthenticated=false → redirect /login
  2. /login mounts → finds stale token in localStorage → sets isAuthenticated=true (no server check)
  3. GUEST_GUARD fires → isAuthenticated=true → redirect /dashboard
  4. AUTH_GUARD fires → GET /auth/me returns 401 → redirect /login
  5. REPEAT indefinitely

RESULT : /login ↔ /dashboard infinite redirect loop

ROOT CAUSE : localStorage token trusted without server validation.
             isAuthenticated set from localStorage, not from /auth/me response.

FIX :
  INIT_RESOLVER always calls GET /auth/me before any routing decision.
  IF 401 → clear token → set isAuthenticated=false → navigate('/')
  NEVER set isAuthenticated=true from localStorage alone.
  NEVER call navigate() from both AUTH_GUARD and GUEST_GUARD in same cycle (FLAW-01 fix).
```

### BUG-02 — Onboarding Completion Loop

```
STEPS:
  1. User completes /onboarding/step-4 → navigates to /dashboard
  2. ONBOARDING_GUARD reads onboardingDone=false from store (not yet persisted)
  3. Redirects to /onboarding/step-4
  4. User re-submits → navigates to /dashboard → loop repeats

RESULT : /dashboard ↔ /onboarding/step-4 infinite loop

ROOT CAUSE : onboardingDone set in store before backend confirms /prediction/compute success.

FIX :
  onboardingDone=true set ONLY after:
    POST /prediction/compute → 202
    Poll GET /health/score → { status: 'ready' }
    PATCH /user/onboarding-status { done: true } → 200
  All three must succeed before store update.
```

### BUG-03 — API Prefix Mismatch

```
STEPS:
  1. VITE_API_BASE_URL = http://localhost:8000  (missing /api/v1)
  2. Axios: GET /health → http://localhost:8000/health
  3. FastAPI routes at /api/v1/* → 404 Not Found
  4. All API calls fail with 404 · API_GUARD does not fire (not a network error)

RESULT : App fully non-functional. No error visible to user. 404s everywhere.

FIX :
  VITE_API_BASE_URL must equal http://localhost:8000/api/v1
  Enforce in CI: grep VITE_API_BASE_URL .env | grep -q "api/v1" || exit 1
  Backend: add /health at root level (no prefix) for INIT_RESOLVER liveness check only.
  All data endpoints remain at /api/v1/*.
```

### BUG-04 — DB Migration Race Condition on Docker Start

```
STEPS:
  1. docker compose down -v → volume destroyed
  2. docker compose up → postgres + app start simultaneously
  3. App entrypoint starts FastAPI before Alembic migration finishes
  4. First request hits DB → relation 'users' does not exist → 500

RESULT : All endpoints return 500. App unusable until manual intervention.

FIX :
  docker-compose.yml:
    app:
      depends_on:
        postgres:
          condition: service_healthy
  postgres healthcheck: pg_isready -U $POSTGRES_USER
  app entrypoint.sh:
    alembic upgrade head
    python scripts/create_extensions.py  # timescaledb, pgvector
    uvicorn main:app
```

### BUG-05 — Stale Zustand After Remote Session Revocation

```
STEPS:
  1. User active. isAuthenticated=true. Token valid in store.
  2. Backend admin revokes token (DELETE /auth/sessions).
  3. Frontend Zustand unchanged. isAuthenticated still true.
  4. API calls return 401. Axios interceptor not configured → ignored.
  5. Components render with empty/null data. No error shown.

RESULT : Authenticated-looking UI with completely broken data layer.

FIX :
  Global Axios response interceptor (SESSION_GUARD):
    if (error.response?.status === 401) {
      const refreshed = await attemptTokenRefresh()
      if (!refreshed) {
        clearAuthStore()
        navigate('/login', { state: { sessionExpired: true } })
      }
    }
  This fires on EVERY 401, regardless of which endpoint triggered it.
```

### BUG-06 — Onboarding Back-Button Step Jump

```
STEPS:
  1. User at /onboarding/step-4 → presses browser back three times
  2. Lands on /onboarding/step-1 → edits data → submits
  3. PATCH /user/profile fires with new step-1 data
  4. Store onboardingStep = 1 (overwritten)
  5. /onboarding/summary (reached later) shows stale data from step-2/3

RESULT : Prediction computed on inconsistent baseline. Silent data corruption.

FIX :
  On each step mount: GET /user/onboarding-status → use server onboardingStep
  Backend: validate that step submission order is sequential (reject out-of-order PATCHes)
  Store: treat onboardingStep as read-only mirror of backend value
```

### BUG-07 — OCR Polling Memory Leak and Ghost Navigation

```
STEPS:
  1. POST /lab/upload → reportId returned → polling starts (setInterval 5s)
  2. User navigates away to /dashboard
  3. Interval not cleared (no useEffect cleanup) → polling continues in background
  4. OCR completes → navigate('/upload-success') fires from unmounted component
  5. User teleported from /dashboard to /upload-success unexpectedly

RESULT : Ghost navigation. Memory leak. Broken UX on return to /dashboard.

FIX :
  const intervalRef = useRef<NodeJS.Timer>()
  const abortRef = useRef(new AbortController())

  useEffect(() => {
    intervalRef.current = setInterval(pollStatus, 5000)
    return () => {
      clearInterval(intervalRef.current)
      abortRef.current.abort()
    }
  }, [])

  All fetch calls pass: signal: abortRef.current.signal
  Navigate only if component is still mounted: if (isMountedRef.current) navigate(...)
```

### BUG-08 — CORS Failure Silent Bypass

```
STEPS:
  1. Frontend: http://localhost:5173 (Vite default)
  2. FastAPI allow_origins: ["http://localhost:3000"] (wrong port)
  3. Browser preflight OPTIONS blocked
  4. Axios never receives a response → no status code → interceptors do not fire
  5. App hangs silently. No toast. No redirect. No user feedback.

RESULT : Total API failure with no observable error in the application UI.

FIX :
  FastAPI CORS config (main.py):
    allow_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
  .env:
    ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://arogyaai.in
  Axios: catch ERR_NETWORK in interceptor as proxy for CORS-type failures → show toast.
  Never hardcode origins. Always drive from environment.
```

### BUG-09 — /insights/desktop Rendered on Mobile Without Redirect

```
STEPS:
  1. Mobile user shares /insights/desktop URL
  2. Recipient opens on mobile (viewport 375px)
  3. Desktop layout renders: overflow, broken grid, unusable UI
  4. No redirect logic on /insights/desktop for small viewports

RESULT : Broken layout on mobile. No escape path without manual URL edit.

FIX :
  /insights/desktop: useLayoutEffect check viewport on mount
    if (window.innerWidth < 1024) navigate('/insights', { replace: true })
  Add ResizeObserver: if width drops below 1024 mid-session → navigate('/insights')
```

### BUG-10 — /data-consent Context Ambiguity

```
STEPS:
  1. Existing user navigates to /settings/privacy → clicks "Review Consent"
  2. Navigates to /data-consent
  3. /data-consent has no way to distinguish onboarding vs settings context
  4. On accept: always redirects to /onboarding/step-1 (wrong for existing user)

RESULT : Existing user unexpectedly sent to onboarding after updating consent.

FIX :
  /data-consent reads context from location.state.from:
    IF from === 'onboarding' → navigate('/onboarding/step-1')
    IF from === 'settings'   → navigate('/settings/privacy')
    IF from undefined        → navigate('/dashboard') (safe fallback)
  Callers must pass location.state.from explicitly.
```

---

## 8. Loop Detection System

### 8.1 Detection Engine

```typescript
// useRouteLoopDetector.ts
// Install: wrap RouterProvider in App.tsx

const LOOP_THRESHOLD     = 3      // same route N times triggers loop
const LOOP_WINDOW_MS     = 2000   // within this window
const REDIRECT_THRESHOLD = 5      // consecutive unique redirects
const ESCAPE_ROUTE       = '/system/error'
const LOOP_CLEARED_PARAM = 'loop_cleared'

interface HistoryEntry {
  path: string
  ts: number
  isRedirect: boolean
}

let history: HistoryEntry[] = []
let consecutiveRedirects = 0
let loopDetectorActive = true  // disable during escape navigation

export function useRouteLoopDetector() {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!loopDetectorActive) return
    if (location.pathname === ESCAPE_ROUTE) return  // never trigger on escape route
    if (location.pathname === '/system/error') return

    const now = Date.now()
    const isRedirect = !!(location.state as any)?.isGuardRedirect

    history.push({ path: location.pathname, ts: now, isRedirect })

    // Prune entries outside window
    history = history.filter(e => now - e.ts < LOOP_WINDOW_MS)

    // Rule 1: Same route > LOOP_THRESHOLD times in window
    const sameRoute = history.filter(e => e.path === location.pathname)
    if (sameRoute.length >= LOOP_THRESHOLD) {
      triggerEscape('same_route_loop', location.pathname)
      return
    }

    // Rule 2: Consecutive redirect chain
    if (isRedirect) {
      consecutiveRedirects++
    } else {
      consecutiveRedirects = 0
    }
    if (consecutiveRedirects >= REDIRECT_THRESHOLD) {
      triggerEscape('redirect_chain_loop', `${consecutiveRedirects}_consecutive`)
      return
    }

  }, [location.pathname])
}

function triggerEscape(reason: string, detail: string) {
  console.error('[LOOP_DETECTOR]', { reason, detail, history: [...history] })
  loopDetectorActive = false
  history = []
  consecutiveRedirects = 0

  // Nuclear: clear auth state to prevent guard re-fires
  clearAuthStore()
  clearLocalStorage(['token', 'refreshToken'])

  // Navigate to escape route (no guards apply here)
  window.location.replace(`/system/error?reason=${reason}&detail=${encodeURIComponent(detail)}`)

  // Re-enable detector after navigation settles
  setTimeout(() => { loopDetectorActive = true }, 3000)
}
```

### 8.2 Loop Rules

| ID | Condition | Recovery Action |
|---|---|---|
| `LOOP-01` | Same route visited ≥ 3 times within 2000ms | clearAuthStore → /system/error?reason=same_route_loop |
| `LOOP-02` | Consecutive redirect chain ≥ 5 | clearAuthStore → /system/error?reason=redirect_chain_loop |
| `LOOP-03` | AUTH_GUARD + GUEST_GUARD ping-pong ≥ 2 cycles | Clear localStorage token → hard reload /login?loop_cleared=1 |
| `LOOP-04` | ONBOARDING_GUARD ↔ /dashboard ≥ 2 cycles | Reset onboardingDone=false → GET /user/onboarding-status → resume |
| `LOOP-05` | /maintenance ↔ APP_INIT cycle detected | Disable auto-redirect → static maintenance page · manual refresh only |
| `LOOP-06` | SESSION_GUARD refresh → /login → SESSION_GUARD | Max 1 refresh attempt. On fail: abort all queued requests → clearAuthStore → /login |
| `LOOP-07` | OCR poll → navigate → remount → poll | Check isMounted ref. If already at /upload-success → skip poll. |
| `LOOP-08` | /system/error triggers loop detector | /system/error is excluded from detector. Always reachable. |

### 8.3 Escape Routes

| Loop Type | Escape Route | Recovery Action |
|---|---|---|
| Auth guard loop | `/login?loop_cleared=1` | Clear token → reload page completely |
| Onboarding loop | `/onboarding/step-1` | Reset step → re-fetch from backend |
| Maintenance loop | `/maintenance` (static, no auto-poll) | Manual refresh button only |
| Generic redirect | `/system/error` | Log path history · show debug panel in dev mode |
| Session refresh | `/login` | abort refresh · clearAuthStore · force:true |
| Critical unknown | `/system/error` | Always reachable · no guards · nuclear clear |

### 8.4 Logging

```typescript
// All loop events must be logged for post-mortem analysis

interface LoopEvent {
  reason: string
  detail: string
  historySnapshot: HistoryEntry[]
  userId?: string
  timestamp: string
  userAgent: string
}

function logLoopEvent(event: LoopEvent) {
  // Development: console table
  console.table(event.historySnapshot)

  // Production: send to observability pipeline
  if (import.meta.env.PROD) {
    navigator.sendBeacon('/api/v1/telemetry/loop-event', JSON.stringify(event))
    // Also send to Sentry if configured
    Sentry?.captureEvent({ message: 'RouteLoop', extra: event, level: 'error' })
  }
}
```

---

## 9. Future-Proofing Enhancements 🚀

### 9.1 Scalability

#### Route Modularization
```typescript
// routes/index.ts — Central registry
import { authRoutes }         from './modules/auth.routes'
import { onboardingRoutes }   from './modules/onboarding.routes'
import { dashboardRoutes }    from './modules/dashboard.routes'
import { healthRoutes }       from './modules/health.routes'
import { medicalRoutes }      from './modules/medical.routes'
import { consultationRoutes } from './modules/consultation.routes'
import { settingsRoutes }     from './modules/settings.routes'
import { notificationRoutes } from './modules/notification.routes'
import { helpRoutes }         from './modules/help.routes'
import { legalRoutes }        from './modules/legal.routes'
import { systemRoutes }       from './modules/system.routes'

export const ROUTE_REGISTRY = [
  ...authRoutes,
  ...onboardingRoutes,
  ...dashboardRoutes,
  ...healthRoutes,
  ...medicalRoutes,
  ...consultationRoutes,
  ...settingsRoutes,
  ...notificationRoutes,
  ...helpRoutes,
  ...legalRoutes,
  ...systemRoutes,
]
```

#### Lazy Loading Strategy
```typescript
// All route components use React.lazy() + Suspense

const Dashboard        = lazy(() => import('@/pages/Dashboard'))
const Insights         = lazy(() => import('@/pages/health/Insights'))
const Simulator        = lazy(() => import('@/pages/health/Simulator'))
const RiskReport       = lazy(() => import('@/pages/health/RiskReport'))

// Preload high-traffic routes on idle
const preloadOnIdle = (importFn: () => Promise<any>) => {
  if ('requestIdleCallback' in window) {
    requestIdleCallback(() => importFn())
  }
}

// After /dashboard loads: preload /insights, /notifications
preloadOnIdle(() => import('@/pages/health/Insights'))
preloadOnIdle(() => import('@/pages/notifications/NotificationCentre'))
```

#### Micro-Frontend Readiness
```
When team grows beyond 5 engineers:
  - auth module     → independent deployment unit
  - health module   → independent deployment unit
  - consultation    → independent deployment unit

Use Module Federation (Webpack 5) or single-spa:
  - Each module exposes its ROUTE_REGISTRY
  - Shell app composes all registries
  - Guards remain centralized in shell
  - Shared: useAuthStore, apiClient, design tokens
```

---

### 9.2 State Management

#### Centralized Auth Validation
```typescript
// useAuthStore.ts — Backend-first truth enforcement

interface AuthState {
  isAuthenticated: boolean
  hasHydrated: boolean       // store rehydrated from localStorage
  isValidating: boolean      // GET /auth/me in-flight
  user: User | null
  onboardingDone: boolean
  onboardingStep: number
}

// RULE: isAuthenticated is only set to true AFTER GET /auth/me returns 200
// RULE: onboardingDone is only set from GET /user/onboarding-status response
// RULE: localStorage is a cache — backend is always authoritative
// RULE: Store hydration (hasHydrated) blocks all routing until complete
```

#### Backend-First Truth Pattern
```typescript
// INIT_RESOLVER (runs before any route renders)

async function resolveInitialRoute(): Promise<string> {
  // Step 1: Wait for store hydration
  await waitForHydration()

  // Step 2: Check backend health
  const health = await checkHealth()  // GET /health (5s timeout)
  if (!health.ok) return '/maintenance'

  // Step 3: Validate session (if token exists)
  const token = getStoredToken()
  if (!token) return '/'

  const user = await validateSession()  // GET /auth/me
  if (!user) {
    clearAuthStore()
    return '/login'
  }

  // Step 4: Check onboarding status from backend
  const status = await getOnboardingStatus()  // GET /user/onboarding-status
  if (!status.done) return `/onboarding/step-${status.step}`

  return '/dashboard'
}
```

---

### 9.3 API Integration

#### Unified API Client
```typescript
// lib/apiClient.ts

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,  // must include /api/v1
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' }
})

// Request: inject auth token
apiClient.interceptors.request.use(config => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response: handle 401 with refresh queue
apiClient.interceptors.response.use(
  response => response,
  async error => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshed = await refreshTokenQueue()
      if (refreshed) {
        original.headers.Authorization = `Bearer ${useAuthStore.getState().accessToken}`
        return apiClient(original)
      }
      forceLogout()
    }
    return Promise.reject(error)
  }
)
```

#### API Versioning Strategy
```
Current : /api/v1/*    (all endpoints)
Future  : /api/v2/*    (breaking changes)

Transition rules:
  - v1 remains active for 6 months after v2 launch
  - VITE_API_BASE_URL switches to /api/v2 per deployment
  - Frontend: never hardcode version string in component files
  - Always route through apiClient.ts (single version source)

Health check endpoint: GET /health (no version prefix)
  → Always available regardless of API version
  → Used by INIT_RESOLVER and API_GUARD
```

#### Retry + Circuit Breaker
```typescript
// lib/retryClient.ts

const RETRY_ATTEMPTS = 3
const RETRY_DELAY_MS = 1000  // exponential: 1s, 2s, 4s
const CIRCUIT_OPEN_THRESHOLD = 5   // failures in 30s to open circuit
const CIRCUIT_RESET_MS = 30000

let failureCount = 0
let circuitOpen = false
let circuitResetTimer: NodeJS.Timer

function withRetry<T>(fn: () => Promise<T>): Promise<T> {
  if (circuitOpen) return Promise.reject(new Error('CIRCUIT_OPEN'))

  return fn().catch(async err => {
    failureCount++
    if (failureCount >= CIRCUIT_OPEN_THRESHOLD) {
      circuitOpen = true
      circuitResetTimer = setTimeout(() => {
        circuitOpen = false
        failureCount = 0
      }, CIRCUIT_RESET_MS)
      navigateToMaintenance()
    }

    if (canRetry(err) && RETRY_ATTEMPTS > 0) {
      await delay(RETRY_DELAY_MS * Math.pow(2, 3 - RETRY_ATTEMPTS))
      return withRetry(fn)
    }
    throw err
  })
}

// Retry on: 503, 429 (after Retry-After header), ERR_NETWORK
// Do NOT retry on: 400, 401, 403, 404, 422
```

---

### 9.4 Observability

#### Navigation Logging Hook
```typescript
// hooks/useNavigationLogger.ts

export function useNavigationLogger() {
  const location = useLocation()

  useEffect(() => {
    const event = {
      type: 'ROUTE_CHANGE',
      path: location.pathname,
      params: location.search,
      state: location.state,
      ts: new Date().toISOString(),
      userId: useAuthStore.getState().user?.id,
      sessionId: getSessionId(),
    }

    // Dev: console
    if (import.meta.env.DEV) console.log('[NAV]', event)

    // Prod: analytics + Sentry breadcrumb
    if (import.meta.env.PROD) {
      Sentry?.addBreadcrumb({ category: 'navigation', data: event, level: 'info' })
      sendAnalytics('page_view', { path: event.path, userId: event.userId })
    }
  }, [location.pathname])
}
```

#### Error Tracking (Sentry-Style Integration)
```typescript
// main.tsx

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  integrations: [
    new Sentry.BrowserTracing({
      routingInstrumentation: Sentry.reactRouterV6Instrumentation(
        React.useEffect, useLocation, useNavigationType, createRoutesFromChildren, matchRoutes
      )
    })
  ],
  tracesSampleRate: import.meta.env.PROD ? 0.1 : 1.0,
  environment: import.meta.env.MODE,

  // Capture guard failures as distinct issues
  beforeSend(event) {
    if (event.tags?.isGuardFailure) event.fingerprint = ['guard-failure', event.tags.guardName]
    return event
  }
})
```

#### Route Analytics
```
Track per route:
  - time_on_page (ms)
  - bounce_rate (immediate back-navigation)
  - guard_block_rate (how often each guard fires per route)
  - error_rate (API failures per route)
  - conversion_rate (onboarding steps: step-1 → completion)

Onboarding funnel specifically:
  step-1 → step-2 → step-3 → step-4 → summary → completion → dashboard
  Drop-off rate per step → identify friction points
  Target: < 5% drop-off between any two consecutive steps
```

---

### 9.5 Security

#### Token Handling Improvements
```typescript
// CURRENT (vulnerable): token stored in localStorage
// IMPROVED: access token in memory only · refresh token in httpOnly cookie

// Backend: set refresh token as httpOnly cookie
// response.set_cookie('refresh_token', token, httponly=True, secure=True, samesite='strict')

// Frontend: access token in Zustand memory only (not persisted)
// Refresh endpoint reads cookie automatically (no JS access needed)
// On page reload: INIT_RESOLVER calls POST /auth/refresh → gets new access token from cookie

interface AuthStore {
  accessToken: string | null  // in-memory only, never persisted
  user: User | null           // persisted (non-sensitive)
  isAuthenticated: boolean    // derived from accessToken
}
```

#### Route-Level Access Policies
```typescript
// routes.config.ts — Declarative security policy

interface RoutePolicy {
  path: string
  guards: GuardName[]
  requiredRoles?: Role[]          // future RBAC
  rateLimit?: number              // future: page-level rate limit
  requiresDataConsent?: boolean   // show consent gate if not accepted
  sensitivityLevel: 'public' | 'private' | 'sensitive'
}

// Examples:
{ path: '/settings/delete',   sensitivityLevel: 'sensitive', guards: ['AUTH', 'SESSION'] }
{ path: '/settings/security', sensitivityLevel: 'sensitive', guards: ['AUTH', 'SESSION'] }
{ path: '/data-consent',      requiresDataConsent: false,    sensitivityLevel: 'public' }
{ path: '/simulator',         sensitivityLevel: 'private',   guards: ['AUTH', 'ONBOARDING', 'DATA'] }
```

---

### 9.6 Performance

#### Route Prefetching
```typescript
// Prefetch strategy by user context:

// After /login success → prefetch /dashboard, /notifications
// After /dashboard load → prefetch /insights, /consultation on idle
// After /insights load → prefetch /simulator, /risk-explanation on idle
// During /onboarding/step-4 → prefetch /onboarding/summary

function prefetchRoute(path: string) {
  const route = ROUTE_REGISTRY.find(r => r.path === path)
  if (route?.component) {
    // Trigger dynamic import without rendering
    route.component._payload?._result ?? route.component._init(route.component._payload)
  }
}
```

#### API Response Caching
```typescript
// Cache strategy per endpoint:

// GET /health/score        → stale-while-revalidate, TTL 60s
// GET /notifications       → stale-while-revalidate, TTL 30s
// GET /user/profile        → cache until mutation
// GET /health/timeline     → cache with date range key, TTL 5min
// GET /legal/terms         → cache aggressively, TTL 24h (changes rarely)
// GET /help/articles       → cache, TTL 1h
// GET /health/aqi-risk     → stale-while-revalidate, TTL 30min (Redis-backed on server)

// Use TanStack Query (React Query):
const { data } = useQuery({
  queryKey: ['health-score', userId],
  queryFn: () => apiClient.get('/health/score'),
  staleTime: 60_000,
  gcTime: 300_000,
})
```

---

### 9.7 DevOps / Infrastructure

#### Environment-Based Routing Config
```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_ENABLE_MOCK_API=false
VITE_LOOP_DETECTOR_ENABLED=true
VITE_SENTRY_DSN=
VITE_ANALYTICS_ENABLED=false
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# .env.staging
VITE_API_BASE_URL=https://api-staging.arogyaai.in/api/v1
VITE_ENABLE_MOCK_API=false
VITE_LOOP_DETECTOR_ENABLED=true
VITE_SENTRY_DSN=https://xxx@sentry.io/project
VITE_ANALYTICS_ENABLED=true
ALLOWED_ORIGINS=https://staging.arogyaai.in

# .env.production
VITE_API_BASE_URL=https://api.arogyaai.in/api/v1
VITE_ENABLE_MOCK_API=false
VITE_LOOP_DETECTOR_ENABLED=true
VITE_SENTRY_DSN=https://xxx@sentry.io/project
VITE_ANALYTICS_ENABLED=true
ALLOWED_ORIGINS=https://arogyaai.in
```

#### Health Check Standardization
```
Required health endpoints (all return { status: 'ok'|'degraded'|'down' }):

GET /health           → overall system health (no auth required)
GET /health/db        → PostgreSQL + TimescaleDB connectivity
GET /health/redis     → Redis connectivity
GET /health/qdrant    → Qdrant connectivity
GET /health/celery    → Celery worker availability
GET /health/ml        → ML model loaded and responsive

INIT_RESOLVER uses:  GET /health  (aggregate)
/status page uses:   GET /health/db, /health/redis, /health/qdrant, /health/celery
Compose healthcheck: GET /health (postgres ready + migrations done)
```

#### Graceful Degradation Modes
```
DEGRADED MODE (partial service — some backends unavailable):
  Redis down       → disable notifications polling · show static counts
  Qdrant down      → disable RAG features · show "AI insights temporarily unavailable"
  Celery down      → disable /simulator, /report-processing · show maintenance banner
  TimescaleDB down → disable /timeline, wearable metrics · show "Historical data unavailable"

FULL MAINTENANCE MODE (FastAPI down):
  All routes → /maintenance
  No API calls attempted
  Auto-poll GET /health every 60s
  Restore normal routing on health recovery

PROGRESSIVE ENHANCEMENT:
  Core flows always available: auth, profile, consultation (sync endpoints only)
  ML features degrade independently without blocking core app
```

---

## 10. Guard Priority System

### 10.1 Execution Order (Strict)

```
Every route transition executes guards in this exact order.
A guard that fires STOPS all subsequent guards from running.
Only one navigate() call is ever made per route transition.

PRIORITY 1  →  MAINTENANCE_CHECK
            IF maintenanceMode === true AND route !== '/maintenance'
            → navigate('/maintenance')  [STOP]

PRIORITY 2  →  LOOP_DETECTOR
            IF loop pattern detected
            → navigate('/system/error')  [STOP · nuclear clear]

PRIORITY 3  →  AUTH_GUARD
            IF route is protected AND isAuthenticated === false
            → navigate('/login', { state: { from } })  [STOP]

PRIORITY 4  →  SESSION_GUARD
            IF accessToken near expiry (< 60s remaining)
            → attempt silent refresh (async, non-blocking)
            [does not stop chain unless refresh fails and triggers AUTH_GUARD]

PRIORITY 5  →  EMAIL_VERIFICATION_GUARD
            IF isEmailVerified === false AND route is protected
            → navigate('/email-verification')  [STOP]

PRIORITY 6  →  GUEST_GUARD
            IF isAuthenticated === true AND route is auth-only (/login, /signup)
            → navigate('/dashboard' or '/onboarding/step-N')  [STOP]

PRIORITY 7  →  ONBOARDING_GUARD
            IF onboardingDone === false AND route requires completed onboarding
            → navigate('/onboarding/step-N')  [STOP]

PRIORITY 8  →  DATA_GUARD
            IF route requires data AND no health data exists
            → render empty state in-page  [does not navigate · does not stop chain]

PRIORITY 9  →  DYNAMIC_ROUTE_GUARD
            IF route has :param AND param invalid
            → navigate('/404')  [STOP]

PRIORITY 10 →  API_GUARD
            IF API health check fails (reactive, not blocking render)
            → set maintenanceMode → navigate('/maintenance')  [async]

[ROUTE RENDERS]
```

### 10.2 Conflict Resolution Rules

```
RULE 1 — Single Redirect Enforcement
  A global redirectFired flag (per navigation event) prevents multiple guards
  from each calling navigate(). First guard to fire wins. All others abort.

RULE 2 — MAINTENANCE overrides ALL
  If maintenanceMode=true, no other guard fires. User always sees /maintenance.

RULE 3 — LOOP_DETECTOR cannot be blocked
  Loop detector escape navigate() bypasses all guards. Uses window.location.replace().

RULE 4 — SESSION_GUARD is non-blocking
  Silent token refresh runs in background. Route renders immediately.
  Only blocks if refresh fails (triggers AUTH_GUARD on next protected API call).

RULE 5 — DATA_GUARD never redirects
  DATA_GUARD only controls in-page state. It never calls navigate().
  Route always renders — just with empty/disabled state if no data.

RULE 6 — ONBOARDING_GUARD reads backend, not store
  If onboardingStep in store disagrees with backend, backend wins.
  ONBOARDING_GUARD always calls GET /user/onboarding-status before redirecting.

RULE 7 — Guard chain executes synchronously before render
  All guards must resolve before React renders route component.
  Guards are evaluated inside INIT_RESOLVER (on load) and inside a
  central <GuardedRoute> component wrapper (on navigation).
```

### 10.3 Guard Application Matrix

| Route | MAINT | LOOP | AUTH | SESSION | EMAIL | GUEST | ONBOARD | DATA | DYNAMIC | API |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `/` | ✅ | ✅ | — | — | — | — | — | — | — | ✅ |
| `/login` | ✅ | ✅ | — | — | — | ✅ | — | — | — | ✅ |
| `/signup` | ✅ | ✅ | — | — | — | ✅ | — | — | — | ✅ |
| `/email-verification` | ✅ | ✅ | — | — | ✅ | ✅ | — | — | — | ✅ |
| `/reset-password` | ✅ | ✅ | — | — | — | — | — | — | — | ✅ |
| `/onboarding/*` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ |
| `/dashboard` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ |
| `/insights` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | — | ✅ |
| `/simulator` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | — | ✅ |
| `/devices/settings/:id` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | ✅ |
| `/consultation/doctor/:id` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | ✅ |
| `/notifications/alert/:id` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | ✅ |
| `/help/article/:slug` | ✅ | ✅ | — | — | — | — | — | — | ✅ | ✅ |
| `/settings/delete` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ |
| `/help` | ✅ | ✅ | — | — | — | — | — | — | — | ✅ |
| `/terms` | ✅ | ✅ | — | — | — | — | — | — | — | ✅ |
| `/404` | — | — | — | — | — | — | — | — | — | — |
| `/500` | — | — | — | — | — | — | — | — | — | — |
| `/maintenance` | — | — | — | — | — | — | — | — | — | — |
| `/system/error` | — | — | — | — | — | — | — | — | — | — |

---

## 11. Initialization Engine

### 11.1 INIT_RESOLVER — Full Specification

```typescript
// init/resolver.ts
// Runs ONCE on app mount. Blocks ALL route rendering until complete.
// Renders /loading during execution.

type InitResult =
  | { route: '/' }
  | { route: '/maintenance' }
  | { route: '/login'; state?: object }
  | { route: '/email-verification' }
  | { route: `/onboarding/step-${number}` }
  | { route: '/onboarding/summary' }
  | { route: '/onboarding/completion' }
  | { route: '/dashboard' }

export async function INIT_RESOLVER(): Promise<InitResult> {

  // ── PHASE 1: Wait for store hydration ──────────────────────────────────
  await waitForStoreHydration()  // polls hasHydrated flag, max 3s
  // If store hydration never completes → treat as unauthenticated

  // ── PHASE 2: Backend health check ──────────────────────────────────────
  const healthResult = await Promise.race([
    checkHealth(),                              // GET /health
    delay(5000).then(() => ({ ok: false }))    // 5s hard timeout
  ])
  if (!healthResult.ok) return { route: '/maintenance' }

  // ── PHASE 3: Token existence check ─────────────────────────────────────
  const storedToken = getStoredAccessToken()   // memory-first, localStorage fallback
  if (!storedToken) return { route: '/' }

  // ── PHASE 4: Server session validation ─────────────────────────────────
  let user: User | null = null
  try {
    const meResponse = await apiClient.get('/auth/me', { timeout: 5000 })
    user = meResponse.data
  } catch (err) {
    if (isAxiosError(err) && err.response?.status === 401) {
      // Try refresh before giving up
      const refreshed = await attemptTokenRefresh()
      if (refreshed) {
        const retryMe = await apiClient.get('/auth/me', { timeout: 5000 })
        user = retryMe.data
      } else {
        clearAuthStore()
        return { route: '/login', state: { sessionExpired: true } }
      }
    } else {
      // Network error during /auth/me → treat as maintenance
      return { route: '/maintenance' }
    }
  }

  // ── PHASE 5: Email verification check ──────────────────────────────────
  if (!user.isEmailVerified) {
    return { route: '/email-verification' }
  }

  // ── PHASE 6: Onboarding status from backend ─────────────────────────────
  let onboardingStatus: OnboardingStatus
  try {
    const statusResponse = await apiClient.get('/user/onboarding-status', { timeout: 5000 })
    onboardingStatus = statusResponse.data
  } catch {
    // Cannot determine onboarding status → safe default is start of onboarding
    return { route: '/onboarding/step-1' }
  }

  // Sync backend status into store (backend wins)
  useAuthStore.getState().setUser(user)
  useAuthStore.getState().setOnboardingStatus(onboardingStatus)

  if (!onboardingStatus.done) {
    const step = onboardingStatus.currentStep
    if (step <= 4) return { route: `/onboarding/step-${step}` }
    if (step === 5) return { route: '/onboarding/summary' }
    return { route: '/onboarding/completion' }
  }

  // ── PHASE 7: All checks passed ──────────────────────────────────────────
  return { route: '/dashboard' }
}
```

### 11.2 INIT_RESOLVER Integration in App.tsx

```typescript
// App.tsx

function App() {
  const [initResult, setInitResult] = useState<InitResult | null>(null)

  useEffect(() => {
    INIT_RESOLVER()
      .then(result => setInitResult(result))
      .catch(() => setInitResult({ route: '/maintenance' }))
  }, [])

  // Block ALL rendering until INIT_RESOLVER resolves
  if (!initResult) return <LoadingScreen />

  return (
    <RouterProvider
      router={createBrowserRouter(ROUTE_REGISTRY)}
      initialEntries={[initResult.route]}
      initialIndex={0}
    />
  )
}
```

### 11.3 INIT_RESOLVER State Machine

```
                    ┌─────────────────────────┐
                    │       APP_MOUNT          │
                    └─────────┬───────────────┘
                              │
                    ┌─────────▼───────────────┐
                    │   WAIT_HYDRATION         │  timeout 3s → treat as unauthenticated
                    └─────────┬───────────────┘
                              │
                    ┌─────────▼───────────────┐
                    │   CHECK_HEALTH           │  GET /health (5s timeout)
                    └──┬──────────────────────┘
               fail ←──┤──→ ok
               │        │
         /maintenance    │
                    ┌────▼────────────────────┐
                    │   CHECK_TOKEN            │  memory + localStorage
                    └──┬──────────────────────┘
            no token ←─┤──→ token exists
               │        │
               /         │
                    ┌────▼────────────────────┐
                    │   VALIDATE_SESSION       │  GET /auth/me
                    └──┬──────────────────────┘
              401 ←───┤──→ 200
               │        │
          try refresh    │
          │    │     ┌───▼─────────────────────┐
        fail  ok     │   CHECK_EMAIL_VERIFIED  │
          │    │     └──┬──────────────────────┘
         /login ←────────┤──→ verified
                    not  │
                  /email- │
                  verif.  │
                    ┌─────▼───────────────────┐
                    │   GET_ONBOARDING_STATUS  │  GET /user/onboarding-status
                    └──┬──────────────────────┘
              done=f ←─┤──→ done=true
               │        │
          /onboarding    │
          /step-N    /dashboard
```

---

*ArogyaAI Navigation Architecture — Final · v3.0 · March 2026*  
*Source: ArogyaAI PRD v2.0 · ArogyaAI Final Roadmap · Navigation Debug Structure v2.0*  
*59 Routes · 11 Modules · 65 API Endpoints · 10 Guard Types · 12 Identified Flaws*
