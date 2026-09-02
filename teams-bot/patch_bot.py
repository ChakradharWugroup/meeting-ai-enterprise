import os

file_path = r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\teams-bot\join_meeting.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Patch the in-meeting detection
old_admit_logic = """            const status = await page.evaluate(() => {
                const text = document.body.innerText.toLowerCase();
                const inLobby = text.includes("we've let people in the meeting know you're waiting") ||
                                text.includes("when the meeting starts") ||
                                text.includes("someone in the meeting should let you in");
                const inMeeting = text.includes("leave") && (text.includes("react") || text.includes("chat"));
                return { inLobby, inMeeting };
            });"""

new_admit_logic = """            const status = await page.evaluate(() => {
                const text = document.body.innerText.toLowerCase();
                const inLobby = text.includes("we've let people in the meeting know you're waiting") ||
                                text.includes("when the meeting starts") ||
                                text.includes("someone in the meeting should let you in");
                // More robust inMeeting detection: look for common meeting UI text, or if the user is told they are alone
                const inMeeting = text.includes("leave") || 
                                  text.includes("react") || 
                                  text.includes("waiting for others to join") ||
                                  document.querySelector('button[id*="leave"]') != null ||
                                  document.querySelector('button[data-tid*="leave"]') != null ||
                                  document.querySelector('button[aria-label*="Leave"]') != null;
                return { inLobby, inMeeting };
            });"""

if old_admit_logic in content:
    content = content.replace(old_admit_logic, new_admit_logic)
    print("Patched admit logic!")
else:
    print("Admit logic not found, maybe already patched?")

# 2. Add an overall timeout to the while(!isAdmitted) loop so it doesn't hang forever
old_admit_loop = """    let isAdmitted = false;
    let stuckCount = 0;
    while (!isAdmitted) {"""

new_admit_loop = """    let isAdmitted = false;
    let stuckCount = 0;
    let loopStartTime = Date.now();
    while (!isAdmitted) {
        if (Date.now() - loopStartTime > 5 * 60 * 1000) { // 5 minutes max
            fileLog("Timed out waiting for admission. Exiting...");
            process.exit(1);
        }"""

if old_admit_loop in content:
    content = content.replace(old_admit_loop, new_admit_loop)
    print("Patched admit loop timeout!")
else:
    print("Admit loop start not found!")

# 3. Patch the exitReason logic to be more robust for kicks
old_exit_logic = """            const exitReason = await page.evaluate(() => {
                const text = document.body.innerText.toLowerCase();
                if (text.includes('you have been removed') || text.includes('you\\'ve been removed') || text.includes('you?ve been removed') || text.includes('been removed from this meeting') || text.includes('removed you from the meeting') || text.includes('someone removed you') || text.includes('you were removed')) {
                    return 'kicked_out';
                }"""

# Fallback string replace in case of unicode issues
content = content.replace("you?ve been removed", "you've been removed")
content = content.replace("you?ve been removed", "you've been removed")

new_exit_logic = """            const exitReason = await page.evaluate(() => {
                const text = document.body.innerText.toLowerCase();
                
                // Very aggressive check for being kicked
                if (text.includes('removed from this meeting') || 
                    text.includes('someone removed you') || 
                    text.includes('you were removed') ||
                    text.includes("you've been removed") ||
                    text.includes("you have been removed") ||
                    document.querySelector('button[aria-label="Rejoin"]') != null ||
                    text.includes("rejoin")) {
                    return 'kicked_out';
                }"""

# Use regex to replace the first part of exitReason
import re
content = re.sub(r'const exitReason = await page\.evaluate\(\(\) => \{\s*const text = document\.body\.innerText\.toLowerCase\(\);\s*if \(text\.includes\([^)]+\) \|\|[^}]+\)\s*\{\s*return \'kicked_out\';\s*\}', new_exit_logic, content)

# 4. Make alone detection more robust
old_alone_logic = """                if (
                    text.includes("you're the only one in this meeting") || 
                    text.includes("waiting for others to join") ||
                    text.includes("you are the only one here") ||
                    text.includes("you're the only one here") ||
                    text.includes("you are the only one in the meeting") ||
                    text.includes("only one in the meeting")
                ) {
                    return "alone";
                }"""

new_alone_logic = """                if (
                    text.includes("you're the only one in this meeting") || 
                    text.includes("waiting for others to join") ||
                    text.includes("you are the only one here") ||
                    text.includes("you're the only one here") ||
                    text.includes("you are the only one in the meeting") ||
                    text.includes("only one in the meeting") ||
                    text.includes("you're the only participant") ||
                    (text.includes("leave") && !text.includes("admit") && (text.includes("waiting for others") || text.includes("alone")))
                ) {
                    return "alone";
                }"""

if old_alone_logic in content:
    content = content.replace(old_alone_logic, new_alone_logic)
    print("Patched alone logic!")
else:
    print("Alone logic not found!")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished patching join_meeting.js")
