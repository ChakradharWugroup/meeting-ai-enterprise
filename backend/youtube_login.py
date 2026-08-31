from playwright.sync_api import sync_playwright
import json
import os

def export_cookies_to_netscape(playwright_cookies, output_file):
    with open(output_file, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# http://curl.haxx.se/rfc/cookie_spec.html\n")
        f.write("# This is a generated file!  Do not edit.\n\n")
        
        for cookie in playwright_cookies:
            domain = cookie.get('domain', '')
            include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
            path = cookie.get('path', '/')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
            expires = str(int(cookie.get('expires', 0))) if cookie.get('expires', -1) > 0 else '0'
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            
            f.write(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")

def login_and_save_cookies():
    print("Starting Playwright to capture YouTube cookies...")
    with sync_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), 'youtube_auth_profile')
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome"
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/")
        
        print("Please log into YouTube in the browser window.")
        print("Waiting for you to manually close the window when you are done...")
        
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
            
        print("Window closed! Exporting cookies...")
        cookies = browser.cookies()
        cookie_file = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')
        export_cookies_to_netscape(cookies, cookie_file)
        print(f"Cookies saved successfully to {cookie_file}")
        
        try:
            browser.close()
        except:
            pass

if __name__ == "__main__":
    login_and_save_cookies()
