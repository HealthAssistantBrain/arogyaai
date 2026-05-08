# Profile Architecture

## Goal

ArogyaAI now has one canonical profile contract:

- backend API: `GET /api/v1/profile`
- frontend canonical store: `apps/frontend/src/store/profileStore.js`

Existing flat profile endpoints remain in place as adapters so onboarding, dashboard, settings, and report flows keep working during migration.

## Canonical API

`GET /api/v1/profile` returns:

```json
{
  "success": true,
  "status": "ready",
  "source": "db",
  "error": null,
  "data": {
    "user": {},
    "profile": {},
    "onboarding": {},
    "medical_history": {},
    "wearable": {},
    "settings": {},
    "preferences": {},
    "health_baseline": {}
  },
  "last_updated": "2026-05-08T12:30:00+00:00"
}
```

## Ownership rules

### `user`

Owned by:

- `users`
- `user_profile.supabase_id` for identity linkage

Contains:

- identity
- role
- email verification state
- canonical auth linkage

### `profile`

Owned by:

- `user_profile`

Contains:

- editable demographics
- phone
- DOB
- age
- gender
- body metrics
- core lifestyle fields currently persisted on `user_profile`

### `onboarding`

Owned by:

- `users.is_onboarding_done`
- `users.onboarding_step`
- `clinical_history` for the initial clinical snapshot

### `medical_history`

Owned by:

- `medical_history.conditions`
- `user_profile` for allergies/family-history/medications/surgeries/hospitalization fields

### `wearable`

Owned by:

- `google_fit_connections`
- `user_devices`
- `wearable_metrics`

### `settings`

Owned by:

- `user_settings`

### `preferences`

Owned by:

- `notification_preferences`

### `health_baseline`

Owned by:

- `baseline_metrics`

## Frontend normalization

Canonical store:

- `useProfileStore`

Compatibility adapters:

- `useUserStore` now derives its legacy flat `user` shape from `useProfileStore`
- `useAuthStore` synchronizes the canonical bundle after auth/session hydration

This lets current pages continue reading old keys like:

- `dob`
- `height`
- `weight`
- `onboardingCompleted`
- `device_connections`

while the canonical bundle remains the real profile source of truth underneath.

## Migration-safe behavior

Still supported:

- `GET /api/v1/users/me`
- `GET /api/v1/user/profile`
- `PUT /api/v1/user/profile`
- `POST /api/v1/users/profile`

These routes are now compatibility surfaces, not the long-term contract.

## Recommended next phase

Phase B should migrate more frontend consumers directly onto `useProfileStore` and `GET /api/v1/profile`, then Phase C can shrink the remaining flat adapters once manual smoke tests are complete.
