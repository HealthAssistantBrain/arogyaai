import { chromium } from 'playwright';

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    try {
        await page.goto('http://localhost:5173/help', { waitUntil: 'networkidle' });

        console.log('Current URL:', page.url());

        // Log the text content of the body to see what rendered
        const text = await page.locator('body').innerText();
        console.log('Page Text:', text.substring(0, 1000));

    } catch (err) {
        console.error('Test failed:', err);
    } finally {
        await browser.close();
    }
})();
