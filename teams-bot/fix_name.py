import os

file_path = r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\teams-bot\join_meeting.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_name = """                // Fill guest name
                const nameInputs = await frame.locator('input[type="text"]').all();
                for (const input of nameInputs) {
                    const ph = await input.getAttribute('placeholder');
                    if (ph && (ph.toLowerCase().includes('name') || ph.toLowerCase().includes('guest'))) {
                        const val = await input.inputValue();
                        if (val !== guestName) await input.fill(guestName);
                    }
                }"""

new_name = """                // Fill guest name - extremely aggressive
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

content = content.replace(old_name, new_name)

# Fix the join button to wait for it to be enabled BEFORE clicking
# Because force: true bypasses the disabled check, but the browser ignores the click.
old_join_click = """                if (await joinBtns.count() > 0) {
                    await joinBtns.first().click({ force: true });
                    fileLog("Dynamically clicked Join Now!");
                    joined = true;
                    break;
                }"""

new_join_click = """                if (await joinBtns.count() > 0) {
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

content = content.replace(old_join_click, new_join_click)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed Name filler and disabled check.')
