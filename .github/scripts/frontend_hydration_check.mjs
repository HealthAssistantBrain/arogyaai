import { chromium } from 'playwright';

const baseUrl = process.env.FRONTEND_BASE_URL ?? 'http://127.0.0.1:4173';
const routes = [
  '/',
  '/login',
  '/privacy',
  '/data-consent',
  '/dashboard',
  '/recommendations',
  '/status',
  '/settings/profile',
  '/device-settings/google-fit',
];

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();
const errors = [];

page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
page.on('console', (message) => {
  if (message.type() === 'error') {
    const text = message.text();
    if (!/favicon|Failed to load resource/i.test(text)) {
      errors.push(`console.error: ${text}`);
    }
  }
});

try {
  await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.evaluate(() => {
    localStorage.setItem('arogyaai-auth', JSON.stringify({
      state: {
        isAuthenticated: true,
        isEmailVerified: true,
        onboardingDone: true,
        onboardingStep: 6,
        token: null,
        refreshToken: null,
        user: { id: 'ci-user', name: 'CI User' },
        role: 'user',
        isHydrated: true,
        hasBootstrappedAuth: true,
      },
      version: 0,
    }));
  });

  for (const route of routes) {
    const response = await page.goto(`${baseUrl}${route}`, {
      waitUntil: 'domcontentloaded',
      timeout: 15000,
    });
    if (!response || !response.ok()) {
      errors.push(`${route}: HTTP ${response?.status() ?? 'no response'}`);
    }
    await page.waitForSelector('#root', { timeout: 5000 });
    const bodyText = await page.locator('body').innerText({ timeout: 5000 });
    if (/Configuration Error|CRITICAL STARTUP FAILURE|Node Offline/i.test(bodyText)) {
      errors.push(`${route}: rendered startup or route failure`);
    }
  }
} finally {
  await browser.close();
}

if (errors.length) {
  for (const error of errors) {
    console.error(`::error::${error}`);
  }
  process.exit(1);
}

console.log(`[FRONTEND] Hydration and route smoke passed for ${routes.length} routes.`);
