import os

file_path = r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\teams-bot\join_meeting.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the join button selector to be robust
old_join = "const joinBtns = frame.getByText(/join now/i);"
new_join = """// Try multiple robust selectors for the Join button
                let joinBtns = frame.getByRole('button', { name: /join now/i });
                if (await joinBtns.count() === 0) {
                    joinBtns = frame.locator('button[data-tid="prejoin-join-button"]');
                }
                if (await joinBtns.count() === 0) {
                    joinBtns = frame.getByText(/join now/i).locator('xpath=./ancestor-or-self::button');
                }
                if (await joinBtns.count() === 0) {
                    joinBtns = frame.getByText(/join now/i); // Absolute fallback
                }"""
content = content.replace(old_join, new_join)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed Join Now selector.')
