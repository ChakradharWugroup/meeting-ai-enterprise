const { chromium } = require('playwright');
const path = require('path');

const meetingUrl = process.argv[2];

(async () => {
    console.log(`Debugging Teams navigation for ${meetingUrl}...`);
    
    const browser = await chromium.launch({
        headless: true,
        args: [
            '--use-fake-ui-for-media-stream',
            '--use-fake-device-for-media-stream',
            '--disable-web-security'
        ]
    });
    
    const context = await browser.newContext();
    const page = await context.newPage();
    
    console.log("Navigating...");
    await page.goto(meetingUrl);
    
    console.log("Waiting 10 seconds for page to settle...");
    await page.waitForTimeout(10000);
    
    const screenshotPath = "C:\\Users\\KalleChakradhar\\.gemini\\antigravity\\brain\\3d422d37-ad77-4a23-965a-973dd8f844b7\\scratch\\teams_debug.png";
    await page.screenshot({ path: screenshotPath });
    
    // Also dump the text content of the page to help find locators
    const text = await page.evaluate(() => document.body.innerText);
    console.log("PAGE TEXT CONTENT:");
    console.log(text);
    
    await browser.close();
    console.log(`Screenshot saved to ${screenshotPath}`);
})();
