import puppeteer from 'puppeteer';
import fs from 'fs';

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  let logs = [];
  page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', error => logs.push(`[PAGE ERROR] ${error.message}`));
  page.on('response', response => {
    if (!response.ok()) {
      logs.push(`[HTTP ${response.status()}] ${response.url()}`);
    }
  });

  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle0' });
  
  const html = await page.content();
  
  fs.writeFileSync('debug_login.txt', logs.join('\n') + '\n\nHTML:\n' + html);
  
  console.log('Debug info saved to debug_login.txt');
  await browser.close();
})();
