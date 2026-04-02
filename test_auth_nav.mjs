import { chromium } from 'playwright';

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    try {
        await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });

        // Inject mock auth state
        const authState = JSON.stringify({
            state: {
                isAuthenticated: true,
                isEmailVerified: true,
                onboardingDone: true,
                onboardingStep: 6,
                token: "fake-jwt-token",
                user: { id: "123", name: "Elena Smith" },
            },
            version: 0
        });

        await page.evaluate((state) => {
            localStorage.setItem('auth-storage', state);
        }, authState);

        await page.reload({ waitUntil: 'networkidle' });

        console.log('Navigating to /devices...');
        await page.goto('http://localhost:5173/devices', { waitUntil: 'networkidle' });

        console.log('Current URL:', page.url());

        const text = await page.locator('body').innerText();
        console.log('Page Text:', text.substring(0, 300));

        const html = await page.content();
        if (html.includes('Node Offline')) {
            console.log('FAIL: Navigation hit Node Offline / 404.');
        } else {
            console.log('SUCCESS: Navigation resolved to expected page component.');
            await page.screenshot({ path: 'screenshot_devices.png' });
        }

    } catch (err) {
        console.error('Test failed:', err);
    } finally {
        await browser.close();
    }
})();
