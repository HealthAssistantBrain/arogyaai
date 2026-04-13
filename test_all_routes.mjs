import { chromium } from 'playwright';

const routes = [
    { name: 'Simulate', url: 'http://localhost:5173/simulator' },
    { name: 'Reports', url: 'http://localhost:5173/medical-reports' },
    { name: 'AI Insights', url: 'http://localhost:5173/insights' },
    { name: 'Devices', url: 'http://localhost:5173/devices' },
    { name: 'Data Privacy', url: 'http://localhost:5173/settings/privacy' },
    { name: 'Security Audits', url: 'http://localhost:5173/settings/security' },
    { name: 'System Status', url: 'http://localhost:5173/status' },
    { name: "What's New", url: 'http://localhost:5173/whats-new' },
    { name: 'Help Center', url: 'http://localhost:5173/help' },
];

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const results = [];

    console.log('\n=== ArogyaAI Route Verification ===\n');

    try {
        // Go to root first to prime domain
        await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });

        // KEY FIX: The authStore uses 'arogyaai-auth' as the persist key, NOT 'auth-storage'
        // Also: when a token exists, onRehydrateStorage calls hydrateAuth() which hits backend
        // So we must set token=null to skip backend call and let isHydrated=true be the only thing needed
        await page.evaluate(() => {
            // This matches the Zustand persist key in authStore.js line 301
            localStorage.setItem('arogyaai-auth', JSON.stringify({
                state: {
                    isAuthenticated: true,
                    isEmailVerified: true,
                    onboardingDone: true,
                    onboardingStep: 6,
                    token: null,  // null token → no backend call, goes direct to setHydrated()
                    refreshToken: null,
                    user: { id: '123', name: 'Test User' },
                    role: 'user',
                },
                version: 0
            }));
        });

        for (const route of routes) {
            try {
                await page.goto(route.url, { waitUntil: 'networkidle', timeout: 8000 });
                const finalUrl = page.url();
                const html = await page.content();

                const hitNotFound = html.includes('Node Offline') || finalUrl.includes('/404');
                const hitServerError = finalUrl.includes('/500');
                const redirected = finalUrl !== route.url && !finalUrl.startsWith(route.url);

                let status;
                if (hitNotFound) status = '❌ NODE OFFLINE (404)';
                else if (hitServerError) status = '❌ SERVER ERROR (500)';
                else if (redirected) status = `⚠️  REDIRECTED → ${finalUrl}`;
                else status = '✅ OK';

                console.log(`${status.padEnd(40)} ${route.name}`);
                results.push({ ...route, status, finalUrl });
            } catch (e) {
                console.log(`❌ TIMEOUT ${''.padEnd(30)} ${route.name}`);
                results.push({ ...route, status: 'ERROR', error: e.message });
            }
        }
    } finally {
        await browser.close();
    }

    console.log('\n=== Summary ===');
    const failed = results.filter(r => !r.status.startsWith('✅'));
    console.log(`Passed: ${results.length - failed.length}/${results.length}`);
    if (failed.length) {
        console.log('\nFailed:');
        failed.forEach(r => console.log(` - ${r.name}: ${r.status}`));
    }
})();
