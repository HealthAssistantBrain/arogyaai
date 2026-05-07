# Google Fit Integration Setup Guide

This guide walks you through configuring Google Fit integration for ArogyaAI, enabling wearable data sync (steps, heart rate, sleep, blood pressure).

---

## Prerequisites

- A Google account
- Access to [Google Cloud Console](https://console.cloud.google.com/)

---

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Name: `ArogyaAI` (or any name)
4. Click **Create**

---

## Step 2: Enable the Fitness API

1. In your project, go to **APIs & Services** → **Library**
2. Search for **Fitness API**
3. Click **Fitness API** → **Enable**

---

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** user type → **Create**
3. Fill in:
   - **App name:** `ArogyaAI`
   - **User support email:** Your email
   - **Developer contact email:** Your email
4. Click **Save and Continue**
5. Add scopes:
   - `https://www.googleapis.com/auth/fitness.activity.read`
   - `https://www.googleapis.com/auth/fitness.blood_pressure.read`
   - `https://www.googleapis.com/auth/fitness.heart_rate.read`
   - `https://www.googleapis.com/auth/fitness.sleep.read`
   - `https://www.googleapis.com/auth/fitness.body.read`
6. Click **Save and Continue**
7. Add test users (your Google account email)
8. Click **Save and Continue** → **Back to Dashboard**

---

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Application type: **Web application**
4. Name: `ArogyaAI Local Dev`
5. **Authorized redirect URIs:** Add:
   ```
   http://localhost:8000/api/v1/google-fit/oauth/callback
   ```
6. Click **Create**
7. **Copy the Client ID and Client Secret**

---

## Step 5: Configure `.env`

Add to your `.env` file:

```env
GOOGLE_FIT_CLIENT_ID=your_client_id_from_step_4.apps.googleusercontent.com
GOOGLE_FIT_CLIENT_SECRET=GOCSPX-your_client_secret_from_step_4
GOOGLE_FIT_REDIRECT_URI=http://localhost:8000/api/v1/google-fit/oauth/callback
GOOGLE_FIT_DEFAULT_TIMEZONE=Asia/Kolkata
```

---

## Step 6: Test the Integration

1. Start the stack: `docker compose up --build`
2. Log in to ArogyaAI at http://localhost:5173
3. Navigate to **Settings** → **Google Fit**
4. Click **Connect Google Fit**
5. Complete the Google OAuth flow
6. Data sync should begin within 60 seconds

---

## Required OAuth Scopes

| Scope | Purpose |
|-------|---------|
| `fitness.activity.read` | Steps, calories, distance |
| `fitness.heart_rate.read` | Heart rate measurements |
| `fitness.blood_pressure.read` | Blood pressure readings |
| `fitness.sleep.read` | Sleep sessions and stages |
| `fitness.body.read` | Weight, height, BMI |

---

## Production Deployment Notes

For production, update:

1. **Redirect URI:** Change to your production domain:
   ```
   https://api.yourdomain.com/api/v1/google-fit/oauth/callback
   ```
2. **OAuth Consent Screen:** Submit for Google verification
3. **SSL:** Ensure your production backend uses HTTPS

---

## Troubleshooting

### "Access blocked: This app's request is invalid"
- Check that the redirect URI in Google Cloud Console **exactly matches** `GOOGLE_FIT_REDIRECT_URI` in your `.env`

### "Error 403: access_denied"
- Ensure your Google account is added as a **test user** in the OAuth consent screen

### No data appearing after connection
- Google Fit data syncs every 60 seconds (configurable via `EMERGENCY_CHECK_INTERVAL_SECONDS`)
- Ensure you have recent data in Google Fit (use a Fitbit, Wear OS device, or the Google Fit mobile app)

### SSL Errors (Corporate Proxy)
- Set `GOOGLE_FIT_SSL_VERIFY=false` in `.env` (dev only)
- Or provide your CA bundle: `GOOGLE_FIT_CA_BUNDLE=/path/to/ca-bundle.crt`
