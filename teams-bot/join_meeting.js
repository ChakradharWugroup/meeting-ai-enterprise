const { chromium } = require('playwright');
const WebSocket = require('ws');
const fs = require('fs');

function fileLog(msg) {
    console.log(msg);
    fs.appendFileSync('bot_debug.txt', new Date().toISOString() + ' - ' + msg + '\n');
}

const meetingUrl = process.argv[2];
const meetingId = process.argv[3];
const wsUrl = process.argv[4] || `ws://127.0.0.1:8080/meeting/${meetingId}/ws`;
const guestName = "AI Notetaker";

if (!meetingUrl || !meetingId) {
    console.error("Please provide a meeting URL and Meeting ID.");
    process.exit(1);
}

(async () => {
    fileLog(`Starting INTELLIGENT headless bot for meeting ${meetingId}...`);
    
    const ws = new WebSocket(wsUrl);
    ws.on('open', () => fileLog('Connected to Backend AI WebSocket.'));
    ws.on('error', (err) => fileLog('WebSocket error:', err.message));
    
    const browser = await chromium.launch({
        headless: true,
        args: [
            '--use-fake-ui-for-media-stream',
            '--disable-web-security',
            '--window-size=1920,1080',
            '--autoplay-policy=no-user-gesture-required'
        ]
    });
    
    const context = await browser.newContext();
    const page = await context.newPage();
    
    await page.exposeFunction('onAudioData', (dataArray) => {
        const buffer = Buffer.from(dataArray);
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(buffer);
        }
    });

    await page.exposeFunction('onBotStateChange', (state, reason) => {
        fileLog(`🤖 INTELLIGENT BOT DETECTED STATE CHANGE: ${state} - Reason: ${reason}`);
        if (state === 'kicked_out' || state === 'alone' || state === 'ended' || state === 'denied') {
            fileLog(`Exiting bot to trigger completion...`);
            process.exit(0);
        }
    });

    fileLog("Navigating to meeting URL...");
    await page.goto(meetingUrl, { waitUntil: 'domcontentloaded' });
    
    // 🧠 INTELLIGENCE ENGINE 1: Auto-Dismiss Popups (Runs continuously in background)
    const autoDismiss = async () => {
        while (true) {
            try {
                for (const frame of page.frames()) {
                    const dismissTokens = [/continue without audio/i, /got it/i, /dismiss/i, /maybe later/i, /close/i];
                    for (const token of dismissTokens) {
                        const btns = frame.getByRole('button', { name: token });
                        if (await btns.count() > 0) {
                            await btns.first().click({ force: true, timeout: 500 }).catch(()=>{});
                        }
                    }
                }
            } catch (e) {}
            await page.waitForTimeout(3000);
        }
    };
    autoDismiss();

    // 🧠 INTELLIGENCE ENGINE 2: Dynamic Joiner
    fileLog("Analyzing pre-join screen...");
    let joined = false;
    for (let i = 0; i < 30; i++) {
        if (joined) break;
        await page.waitForTimeout(1000);
        
        for (const frame of page.frames()) {
            try {
                // Click 'Continue on browser'
                const continueBrowser = frame.getByText('Continue on this browser');
                if (await continueBrowser.count() > 0) {
                    await continueBrowser.first().click({ force: true });
                }

                // Fill guest name - extremely aggressive using human-like typing
                let nameFilled = false;
                const specificInput = frame.locator('input#username, input[data-tid="prejoin-display-name-input"], input[aria-label*="name"]');
                if (await specificInput.count() > 0) {
                    const input = specificInput.first();
                    if (await input.isVisible()) {
                        await input.click();
                        await input.fill('');
                        await input.pressSequentially(guestName, { delay: 100 });
                        nameFilled = true;
                    }
                }
                
                if (!nameFilled) {
                    const nameInputs = await frame.locator('input').all();
                    for (const input of nameInputs) {
                        if (await input.isVisible()) {
                            const type = await input.getAttribute('type');
                            if (type === 'text' || type === null) {
                                await input.click();
                                await input.fill('');
                                await input.pressSequentially(guestName, { delay: 100 });
                                break;
                            }
                        }
                    }
                }
                
                // Disable Mic/Cam toggles
                const toggles = await frame.locator('div[role="checkbox"], div[role="switch"]').all();
                for (const toggle of toggles) {
                    const checked = await toggle.getAttribute('aria-checked');
                    if (checked === 'true') await toggle.click({ force: true });
                }

                // Click Join
                // Try multiple robust selectors for the Join button
                let joinBtns = frame.getByRole('button', { name: /join now/i });
                if (await joinBtns.count() === 0) {
                    joinBtns = frame.locator('button[data-tid="prejoin-join-button"]');
                }
                if (await joinBtns.count() === 0) {
                    joinBtns = frame.getByText(/join now/i).locator('xpath=./ancestor-or-self::button');
                }
                // Filter to ONLY visible buttons so we don't accidentally check a hidden mobile menu button
                let visibleBtns = [];
                const allJoinBtns = await joinBtns.all();
                for (const b of allJoinBtns) {
                    if (await b.isVisible()) {
                        visibleBtns.push(b);
                    }
                }
                if (visibleBtns.length > 0) {
                    const btn = visibleBtns[0];
                    const isDisabled = await btn.evaluate(node => node.disabled || node.getAttribute('aria-disabled') === 'true');
                    if (!isDisabled) {
                        await page.waitForTimeout(1000); // Wait for React state to register the name
                        await btn.click();
                        fileLog("Dynamically clicked Join Now!");
                        await page.waitForTimeout(2000);
                        // Verify we actually left the prejoin screen
                        const stillHere = await frame.getByRole('button', { name: /join now/i }).count();
                        if (stillHere === 0) {
                            joined = true;
                            break;
                        } else {
                            fileLog("Click didn't register. Trying again...");
                        }
                    } else {
                        fileLog("Join Now button found, but it is disabled. Waiting...");
                    }
                }
            } catch (e) {}
        }
    }

    // 🧠 INTELLIGENCE ENGINE 3: In-Browser MutationObserver (Instant Reaction)
    fileLog("Injecting AI Observer into browser context...");
    await page.evaluate(() => {
        const analyzeScreen = () => {
            const text = document.body.innerText.toLowerCase();
            
            const rejoinBtn = document.querySelector('button[aria-label="Rejoin"]');
            const isRejoinVisible = rejoinBtn && rejoinBtn.offsetWidth > 0 && rejoinBtn.offsetHeight > 0;
            
            // Kicked Out
            if (text.includes('removed from this meeting') || text.includes('someone removed you') || 
                text.includes('you were removed') || text.includes("you've been removed") || 
                isRejoinVisible) {
                window.onBotStateChange('kicked_out', 'Detected removal text or rejoin button');
            }
            // Alone
            else if (text.includes("you're the only one in this meeting") || text.includes("waiting for others to join") ||
                     text.includes("you are the only one here") || text.includes("only one in the meeting") ||
                     text.includes("you're the only participant")) {
                window.onBotStateChange('alone', 'Detected alone text');
            }
            // Ended
            else if (text.includes('you left the meeting') || text.includes('meeting has ended') || 
                     text.includes('has ended the meeting')) {
                window.onBotStateChange('ended', 'Detected meeting ended');
            }
        };

        // Run immediately and then bind to DOM changes for 0-latency reaction
        analyzeScreen();
        const observer = new MutationObserver(() => analyzeScreen());
        observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    });

    fileLog("Waiting for admission or joining...");
    let isAdmitted = false;
    let loopStartTime = Date.now();
    while (!isAdmitted) {
        if (Date.now() - loopStartTime > 5 * 60 * 1000) {
            fileLog("Timed out waiting for admission. Exiting...");
            process.exit(1);
        }
        await page.waitForTimeout(2000);
        try {
            await page.screenshot({ path: 'current_bot_view.png', fullPage: true });
        } catch(e) {}
        try {
            const admitted = await page.evaluate(() => {
                // Strictly check for the physical Leave/Hangup buttons. Do not rely on plain text 
                // because the pre-join screen has a "Learn more about Teams privacy and chat" link.
                const leaveBtn = document.querySelector('button[id*="hangup"]') || 
                                 document.querySelector('button[data-tid*="leave"]') ||
                                 document.querySelector('button[aria-label*="Leave"]');
                
                const hasLeaveBtn = leaveBtn && leaveBtn.offsetWidth > 0;
                
                // Also check if we see typical meeting controls that aren't on the pre-join screen
                const hasReactBtn = document.querySelector('button[aria-label*="React"]') != null;
                const hasChatBtn = document.querySelector('button[aria-label*="Chat"]') != null;
                
                return hasLeaveBtn || hasReactBtn || hasChatBtn;
            });
            if (admitted) isAdmitted = true;
        } catch (e) {}
    }
    fileLog("Admitted to meeting! Starting intelligent audio capture...");

    // Inject Audio Context Hook
    await page.evaluate(() => {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const dest = audioCtx.createMediaStreamDestination();

            const hookAudioElements = () => {
                document.querySelectorAll('audio, video').forEach(el => {
                    if (!el._hooked) {
                        try {
                            const source = audioCtx.createMediaElementSource(el);
                            source.connect(dest);
                            source.connect(audioCtx.destination);
                            el._hooked = true;
                        } catch(e) {}
                    }
                });
            };
            hookAudioElements();
            setInterval(hookAudioElements, 1000); // Check for new speakers every second

            const mediaRecorder = new MediaRecorder(dest.stream, { mimeType: 'audio/webm' });
            mediaRecorder.ondataavailable = async (e) => {
                if (e.data.size > 0) {
                    const buffer = await e.data.arrayBuffer();
                    window.onAudioData(Array.from(new Uint8Array(buffer)));
                }
            };
            mediaRecorder.start(1000);
        } catch(err) {}
    });

    fileLog("Monitoring meeting indefinitely until state change...");
    // The MutationObserver handles exit conditions automatically, so we just keep the process alive
    while(true) {
        await page.waitForTimeout(10000);
        try {
            await page.screenshot({ path: 'current_bot_view.png', fullPage: true });
        } catch(e) {}
    }
})();
