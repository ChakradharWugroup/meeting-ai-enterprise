import os
import re

file_path = r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\teams-bot\join_meeting.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix the name filling logic so React actually registers the input and enables the Join button
old_name = """                // Fill guest name - extremely aggressive
                let nameFilled = false;
                // Try specific ID first
                const specificInput = frame.locator('input#username, input[data-tid="prejoin-display-name-input"]');
                if (await specificInput.count() > 0 && await specificInput.first().isVisible()) {
                    await specificInput.first().fill(guestName);
                    nameFilled = true;
                }
                
                // Fallback: fill ANY visible text input on the pre-join screen that is empty
                if (!nameFilled) {
                    const nameInputs = await frame.locator('input[type="text"]').all();
                    for (const input of nameInputs) {
                        if (await input.isVisible()) {
                            const val = await input.inputValue();
                            if (val === '') {
                                await input.fill(guestName);
                                break;
                            }
                        }
                    }
                }"""

new_name = """                // Fill guest name - extremely aggressive using human-like typing
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
                }"""

content = content.replace(old_name, new_name)

# 2. Fix the admission check so it doesn't falsely trigger on the word "chat" or "leave" in the pre-join privacy text
old_admit = """            const admitted = await page.evaluate(() => {
                const text = document.body.innerText.toLowerCase();
                // If we see "Leave", we are inside the meeting
                return document.querySelector('button[id*="leave"]') != null || 
                       document.querySelector('button[data-tid*="leave"]') != null ||
                       document.querySelector('button[aria-label*="Leave"]') != null ||
                       text.includes("leave") || text.includes("react") || text.includes("chat");
            });"""

new_admit = """            const admitted = await page.evaluate(() => {
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
            });"""

content = content.replace(old_admit, new_admit)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed Name typing and false admission detection.')
