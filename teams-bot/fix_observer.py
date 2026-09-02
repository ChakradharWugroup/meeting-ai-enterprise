import os

file_path = r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\teams-bot\join_meeting.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the AI observer to ignore hidden DOM elements!
old_observer = """    // 🧠 INTELLIGENCE ENGINE 3: In-Browser MutationObserver (Instant Reaction)
    fileLog("Injecting AI Observer into browser context...");
    await page.evaluate(() => {
        const analyzeScreen = () => {
            const text = document.body.innerText.toLowerCase();
            
            // Kicked Out
            if (text.includes('removed from this meeting') || text.includes('someone removed you') || 
                text.includes('you were removed') || text.includes("you've been removed") || 
                document.querySelector('button[aria-label="Rejoin"]') != null) {
                window.onBotStateChange('kicked_out', 'Detected removal text or rejoin button');
            }"""

new_observer = """    // 🧠 INTELLIGENCE ENGINE 3: In-Browser MutationObserver (Instant Reaction)
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
            }"""

content = content.replace(old_observer, new_observer)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed AI observer hidden element bug.')
