const { chromium } = require('playwright');
const path = require('path');

const meetingUrl = process.argv[2];

(async () => {
    console.log(`Debugging Teams navigation step 2 for ${meetingUrl}...`);
    
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
    
    console.log("Clicking continue...");
    try {
        const continueBtn = page.getByText('Continue on this browser').first();
        await continueBtn.waitFor({ state: 'visible', timeout: 15000 });
        await continueBtn.click();
    } catch (e) {
        console.log("Could not click continue.");
    }

    console.log("Waiting 15 seconds for lobby to load...");
    await page.waitForTimeout(15000);
    
    const screenshotPath = "C:\\Users\\KalleChakradhar\\.gemini\\antigravity\\brain\\3d422d37-ad77-4a23-965a-973dd8f844b7\\scratch\\teams_debug_2.png";
    await page.screenshot({ path: screenshotPath });
    
    const text = await page.evaluate(() => document.body.innerText);
    console.log("PAGE TEXT CONTENT:");
    console.log(text);
    
    await browser.close();
    console.log(`Screenshot saved to ${screenshotPath}`);
})();
