import os

file_path = r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\teams-bot\join_meeting.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make the bot repeatedly click "Join Now" until it actually leaves the prejoin screen
old_join_logic = """                if (await joinBtns.count() > 0) {
                    const btn = joinBtns.first();
                    const isDisabled = await btn.evaluate(node => node.disabled || node.getAttribute('aria-disabled') === 'true');
                    if (!isDisabled) {
                        await btn.click({ force: true });
                        fileLog("Dynamically clicked Join Now!");
                        joined = true;
                        break;
                    } else {
                        fileLog("Join Now button found, but it is disabled. Waiting...");
                    }
                }"""

new_join_logic = """                if (await joinBtns.count() > 0) {
                    const btn = joinBtns.first();
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
                }"""

content = content.replace(old_join_logic, new_join_logic)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed Join Now click verification.')
