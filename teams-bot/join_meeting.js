
const fs = require('fs');
function fileLog(msg) {
    fs.appendFileSync('bot_debug.txt', new Date().toISOString() + ' - ' + msg + '\n');
}
const { chromium } = require('playwright');
const WebSocket = require('ws');

// Usage: node join_meeting.js <MEETING_URL> <MEETING_ID> <WS_URL>
const meetingUrl = process.argv[2];
const meetingId = process.argv[3];
const wsUrl = process.argv[4] || `ws://127.0.0.1:8080/meeting/${meetingId}/ws`;
const guestName = "AI Notetaker";

if (!meetingUrl || !meetingId) {
    console.error("Please provide a meeting URL and Meeting ID.");
    process.exit(1);
}

(async () => {
    fileLog(`Starting headless bot for meeting ${meetingId}...`);
    
    // Connect to our FastAPI WebSocket
    const ws = new WebSocket(wsUrl);
    ws.on('open', () => fileLog('Connected to Backend AI WebSocket.'));
    ws.on('error', (err) => fileLog('WebSocket error:', err.message));
    
    // Launch Chrome completely hidden
    const browser = await chromium.launch({
        headless: true,
        args: [
            '--use-fake-ui-for-media-stream',
            '--disable-web-security',
            '--window-size=1920,1080' // Ensure it's large enough so things aren't hidden
        ]
    });
    
    const context = await browser.newContext({
        permissions: ['microphone', 'camera'],
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    fileLog(`Navigating to ${meetingUrl}...`);
    
    // Expose the audio streaming function immediately
    await page.exposeFunction('onAudioData', (dataArray) => {
        const buffer = Buffer.from(dataArray);
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(buffer);
        }
    });

    await page.goto(meetingUrl);
    
    try {
        fileLog("Waiting for 'Continue on this browser' button...");
        const continueBtn = page.getByText('Continue on this browser').first();
        await continueBtn.waitFor({ state: 'visible', timeout: 15000 });
        // Force click ignores overlapping elements like native prompts
        await continueBtn.click({ force: true });
        
        fileLog("Waiting 5 seconds for lobby to load...");
        await page.waitForTimeout(5000);
        
        fileLog("Searching all frames for Guest Name input...");
        let inputFilled = false;
        
        // Wait an extra few seconds to make sure the iframe is fully loaded
        await page.waitForTimeout(5000);
        
        for (const frame of page.frames()) {
            try {
                const input = frame.getByPlaceholder('Type your name');
                if (await input.count() > 0) {
                    await input.first().fill(guestName, { force: true });
                    inputFilled = true;
                    fileLog("Successfully filled guest name!");
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
                        inputFilled = true;
                        fileLog("Successfully filled guest name using generic text input!");
                        break;
                    }
                } catch (e) {}
            }
        }
        
        if (!inputFilled) {
            fileLog("WARNING: Could not find Guest Name input! Saving screenshot of current UI.");
            try {
                await page.screenshot({ path: 'debug_name_input.png', fullPage: true });
            } catch(e) {}
        }
        
        fileLog("Disabling mic and camera...");
        for (const frame of page.frames()) {
            try {
                const switches = await frame.getByRole('switch', { checked: true }).all();
                for (const toggle of switches) {
                    await toggle.click({ force: true });
                }
            } catch (e) {}
        }
        
        fileLog("Joining meeting...");
        let joined = false;
        for (let attempt = 0; attempt < 10; attempt++) {
            for (const frame of page.frames()) {
                try {
                    // Teams sometimes uses divs instead of buttons, so search by text
                    const joinBtn = frame.getByText(/join now/i).locator('..'); // Sometimes the text is inside a span inside the button
                    const fallbackBtn = frame.locator('[data-tid="prejoin-join-button"]');
                    
                    if (await fallbackBtn.count() > 0) {
                        await fallbackBtn.first().click({ force: true });
                        fileLog("Successfully clicked Join Now (via data-tid)!");
                        joined = true; break;
                    } else if (await joinBtn.count() > 0) {
                        await joinBtn.first().click({ force: true });
                        fileLog("Successfully clicked Join Now (via text)!");
                        joined = true; break;
                    } else {
                        // absolute fallback
                        const anyJoin = frame.locator('text="Join now"');
                        if (await anyJoin.count() > 0) {
                            await anyJoin.first().click({ force: true });
                            fileLog("Successfully clicked Join Now (via exact text)!");
                            joined = true; break;
                        }
                    }
                } catch (e) {}
            }
            if (joined) break;
            await page.waitForTimeout(1000);
        }
        
        // Handle "Continue without audio or video" prompt if it appears
        for (let attempt = 0; attempt < 3; attempt++) {
            await page.waitForTimeout(1000);
            for (const frame of page.frames()) {
                try {
                    const continueBtn = frame.getByText(/continue without audio or video/i);
                    if (await continueBtn.count() > 0) {
                        await continueBtn.first().click({ force: true });
                        fileLog("Clicked 'Continue without audio or video' prompt.");
                        break;
                    }
                } catch (e) {}
            }
        }
        
    } catch (e) {
        fileLog("⚠️ Automatic navigation failed.");
        fileLog("Error details:", e.message);
        try {
            await page.screenshot({ path: 'debug_error.png' });
            require('fs').writeFileSync('debug_error.txt', e.message);
        } catch(err) {}
    }

    fileLog("Waiting for admission or joining...");
    let isAdmitted = false;
    let stuckCount = 0;
    while (!isAdmitted) {
        await page.waitForTimeout(2000);
        try {
            const status = await page.evaluate(() => {
                const text = document.body.innerText.toLowerCase();
                const inLobby = text.includes("we've let people in the meeting know you're waiting") ||
                                text.includes("when the meeting starts") ||
                                text.includes("someone in the meeting should let you in");
                const inMeeting = text.includes("leave") && (text.includes("react") || text.includes("chat"));
                return { inLobby, inMeeting };
            });
            
            if (status.inMeeting) {
                isAdmitted = true;
            } else if (!status.inLobby) {
                stuckCount++;
                if (stuckCount % 3 === 0) {
                    fileLog("Still not in lobby or meeting, trying to click Join Now again...");
                    for (const frame of page.frames()) {
                        try {
                            const btn = frame.locator('[data-tid="prejoin-join-button"]');
                            if (await btn.count() > 0) await btn.first().click();
                            
                            const btn2 = frame.getByText(/join now/i).locator('..');
                            if (await btn2.count() > 0) await btn2.first().click();
                            
                            const continueBtn = frame.getByText(/continue without audio or video/i);
                            if (await continueBtn.count() > 0) await continueBtn.first().click();
                        } catch (e) {}
                    }
                }
            } else {
                stuckCount = 0; // reset if we are genuinely in the lobby
            }
        } catch (e) {}
    }
    fileLog("Admitted to meeting!");

    fileLog("Injecting audio capture script with AudioContext mixer...");
    // Inject JS to capture all remote speaker audio (audio elements) + mic
    await page.evaluate(() => {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const dest = audioCtx.createMediaStreamDestination();

            const hookAudioElements = () => {
                const elements = document.querySelectorAll('audio, video');
                elements.forEach(el => {
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
            setInterval(hookAudioElements, 2000);

            navigator.mediaDevices.getUserMedia({ audio: true }).then(micStream => {
                try {
                    const micSource = audioCtx.createMediaStreamSource(micStream);
                    micSource.connect(dest);
                } catch(e) {}
            }).catch(() => {});

            const mediaRecorder = new MediaRecorder(dest.stream, { mimeType: 'audio/webm' });
            mediaRecorder.ondataavailable = async (e) => {
                if (e.data.size > 0) {
                    const buffer = await e.data.arrayBuffer();
                    window.onAudioData(Array.from(new Uint8Array(buffer)));
                }
            };
            mediaRecorder.start(1000);
        } catch(err) {
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
        }
    });

    fileLog("Streaming audio to backend...");
    
    // Periodically check if the meeting has ended, bot was kicked, or bot is alone
    while (true) {
        await page.waitForTimeout(5000);
        try {
            const rawText = await page.evaluate(() => document.body.innerText);
            require('fs').writeFileSync('page_text.txt', rawText);
            
            const exitReason = await page.evaluate(() => {
                const text = document.body.innerText.toLowerCase();
                if (text.includes('you have been removed') || text.includes('you\'ve been removed') || text.includes('you’ve been removed') || text.includes('been removed from this meeting') || text.includes('removed you from the meeting') || text.includes('someone removed you') || text.includes('you were removed')) {
                    return 'kicked_out';
                }
                if (
                    text.includes("you're the only one in this meeting") || 
                    text.includes("waiting for others to join") ||
                    text.includes("you are the only one here") ||
                    text.includes("you're the only one here") ||
                    text.includes("you are the only one in the meeting") ||
                    text.includes("only one in the meeting")
                ) {
                    return "alone";
                }
                if (text.includes('you left the meeting') || text.includes('meeting has ended') || text.includes('has ended the meeting') || text.includes('return to home screen')) {
                    return "ended";
                }
                if (text.includes("can't join this meeting") || text.includes("denied your request to join") || text.includes("denied entry") || text.includes("couldn't join") || text.includes("could not join")) {
                    return "denied";
                }
                return null;
            });

            if (exitReason) {
                fileLog(`Meeting exit condition met: ${exitReason}. Exiting bot to trigger completion...`);
                process.exit(0);
            } else {
                try {
                    await page.screenshot({ path: 'current_bot_view.png', fullPage: true });
                } catch(e) {}
            }
        } catch (e) {
            fileLog("Page evaluation failed (likely closed). Exiting... " + e.message);
            process.exit(0);
        }
    }
})();
