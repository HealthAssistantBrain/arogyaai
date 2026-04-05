const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  page.on('pageerror', err => {
    console.error(`PAGE_ERROR: ${err.message}`);
    console.error(`STACK: ${err.stack}`);
  });
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
       console.error(`CONSOLE_ERROR: ${msg.text()}`);
    }
  });

  await page.goto('http://localhost:5173/dashboard');
  
  await page.evaluate(() => {
    localStorage.setItem('auth-storage', JSON.stringify({
      state: {
         user: { id: "test", name: "test" },
         token: "test",
         isAuthenticated: true
      },
      version: 0
    }));
  });

  await page.goto('http://localhost:5173/device-settings/google-fit');
  await page.waitForTimeout(3000);
  
  console.log("Done checking errors.");
  await browser.close();
})();
