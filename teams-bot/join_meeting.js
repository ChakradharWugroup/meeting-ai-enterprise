const { chromium } = require('playwright');
const WebSocket = require('ws');

// Usage: node join_meeting.js <MEETING_URL> <MEETING_ID>
const meetingUrl = process.argv[2];
const meetingId = process.argv[3];
const guestName = "AI Notetaker";

if (!meetingUrl || !meetingId) {
    console.error("Please provide a meeting URL and Meeting ID.");
    process.exit(1);
}

const wsUrl = `ws://127.0.0.1:8000/meeting/${meetingId}/ws`;

(async () => {
    console.log(`Starting headless bot for meeting ${meetingId}...`);
    
    // Connect to our FastAPI WebSocket
    const ws = new WebSocket(wsUrl);
    ws.on('open', () => console.log('Connected to Backend AI WebSocket.'));
    ws.on('error', (err) => console.log('WebSocket error:', err.message));
    
    // Launch Chrome completely hidden
    const browser = await chromium.launch({
        headless: true,
        args: [
            '--use-fake-ui-for-media-stream',
            '--use-fake-device-for-media-stream',
            '--disable-web-security',
            '--window-size=1920,1080' // Ensure it's large enough so things aren't hidden
        ]
    });
    
    const context = await browser.newContext({
        permissions: ['microphone', 'camera'],
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    console.log(`Navigating to ${meetingUrl}...`);
    
    // Expose the audio streaming function immediately
    await page.exposeFunction('onAudioData', (dataArray) => {
        const buffer = Buffer.from(dataArray);
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(buffer);
        }
    });

    await page.goto(meetingUrl);
    
    try {
        console.log("Waiting for 'Continue on this browser' button...");
        const continueBtn = page.getByText('Continue on this browser').first();
        await continueBtn.waitFor({ state: 'visible', timeout: 15000 });
        // Force click ignores overlapping elements like native prompts
        await continueBtn.click({ force: true });
        
        console.log("Waiting 5 seconds for lobby to load...");
        await page.waitForTimeout(5000);
        
        console.log("Searching all frames for Guest Name input...");
        let inputFilled = false;
        for (const frame of page.frames()) {
            try {
                const input = frame.getByPlaceholder('Type your name');
                if (await input.count() > 0) {
                    await input.first().fill(guestName, { force: true });
                    inputFilled = true;
                    console.log("Successfully filled guest name!");
                    break;
                }
            } catch (e) {}
        }

        if (!inputFilled) {
            for (const frame of page.frames()) {
                try {
                    const backupInput = frame.locator('input[type="text"]');
                    if (await backupInput.count() > 0) {
                        await backupInput.first().fill(guestName, { force: true });
                        console.log("Successfully filled guest name using generic text input!");
                        break;
                    }
                } catch (e) {}
            }
        }
        
        console.log("Disabling mic and camera...");
        for (const frame of page.frames()) {
            try {
                const switches = await frame.getByRole('switch', { checked: true }).all();
                for (const toggle of switches) {
                    await toggle.click({ force: true });
                }
            } catch (e) {}
        }
        
        console.log("Joining meeting...");
        for (const frame of page.frames()) {
            try {
                const joinBtn = frame.getByRole('button', { name: /join now/i });
                if (await joinBtn.count() > 0) {
                    await joinBtn.first().click({ force: true });
                    console.log("Successfully clicked Join Now!");
                    break;
                }
            } catch (e) {}
        }
    } catch (e) {
        console.log("⚠️ Automatic navigation failed.");
        console.log("Error details:", e.message);
    }

    console.log("Injecting audio capture script...");
    // Inject JS to capture page audio output
    await page.evaluate(() => {
        navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
            const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            mediaRecorder.ondataavailable = async (e) => {
                if (e.data.size > 0) {
                    const buffer = await e.data.arrayBuffer();
                    window.onAudioData(Array.from(new Uint8Array(buffer)));
                }
            };
            mediaRecorder.start(1000);
        });
    });
    
    console.log("Streaming audio to backend...");
    
    // Keep process alive indefinitely
    await new Promise(() => {});
})();
