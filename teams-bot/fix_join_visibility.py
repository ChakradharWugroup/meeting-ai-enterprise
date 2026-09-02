import os

file_path = r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\teams-bot\join_meeting.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make the join button locator STRICTLY look for visible buttons, avoiding hidden DOM elements
old_join = """                let joinBtns = frame.getByRole('button', { name: /join now/i });
                if (await joinBtns.count() === 0) {
                    joinBtns = frame.locator('button[data-tid="prejoin-join-button"]');
                }
                if (await joinBtns.count() === 0) {
                    joinBtns = frame.getByText(/join now/i).locator('xpath=./ancestor-or-self::button');
                }
                if (await joinBtns.count() === 0) {
                    joinBtns = frame.getByText(/join now/i); // Absolute fallback
                }"""

new_join = """                let joinBtns = frame.getByRole('button', { name: /join now/i });
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
                }"""

content = content.replace(old_join, new_join)

# Update the click logic to use the visible button
old_click = """                if (await joinBtns.count() > 0) {
                    const btn = joinBtns.first();"""

new_click = """                if (visibleBtns.length > 0) {
                    const btn = visibleBtns[0];"""

content = content.replace(old_click, new_click)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed Join button to strictly check visibility.')
