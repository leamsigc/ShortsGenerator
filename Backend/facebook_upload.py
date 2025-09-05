import asyncio
from playwright.async_api import async_playwright
import os
from pathlib import Path
from settings import get_settings
from termcolor import colored

class FacebookUploader:
    def __init__(self, profile_path=None):
        settings = get_settings()
        self.profile_path = profile_path or os.path.expanduser(settings["facebookSettings"]["profile_path"])
        self.headless = settings["facebookSettings"]["headless"]
        self.channel = settings["facebookSettings"]["channel"]
        self.executable_path = settings["facebookSettings"]["executable_path"]

        # Find the default profile if wildcard or if path doesn't exist
        if "*" in self.profile_path or not os.path.exists(self.profile_path):
            profiles_dir = Path("~/.mozilla/firefox").expanduser()
            if profiles_dir.exists():
                # First try to find stable/beta profiles, avoid nightly
                stable_profiles = []
                nightly_profiles = []

                for profile in profiles_dir.iterdir():
                    if profile.is_dir():
                        if profile.name.endswith(".default") or profile.name.endswith(".default-release"):
                            stable_profiles.append(str(profile))
                        elif profile.name.endswith(".default-nightly") or "nightly" in profile.name.lower():
                            nightly_profiles.append(str(profile))

                # Prefer stable profiles over nightly
                if stable_profiles:
                    self.profile_path = stable_profiles[0]
                    print(colored(f"[+] Using stable Firefox profile: {self.profile_path}", "green"))
                elif nightly_profiles:
                    self.profile_path = nightly_profiles[0]
                    print(colored(f"[+] Using nightly Firefox profile: {self.profile_path}", "yellow"))
                    # If using nightly profile, adjust channel accordingly
                    if self.channel == "firefox":
                        self.channel = "firefox-nightly"
                        print(colored(f"[+] Adjusted channel to match nightly profile: {self.channel}", "yellow"))
                else:
                    print(colored(f"[-] No suitable Firefox profiles found in {profiles_dir}", "red"))
            else:
                print(colored(f"[-] Firefox profiles directory not found: {profiles_dir}", "red"))
                print(colored("[-] Please ensure Firefox is installed and has been run at least once.", "yellow"))
                print(colored(f"[-] You can also set FIREFOX_PROFILE_PATH environment variable to your profile path", "yellow"))

    async def upload_video(self, video_path, title="", description="", schedule_time=None):
        print(colored(f"[+] Starting Facebook upload for: {video_path}", "blue"))
        print(colored(f"[+] Using Firefox profile: {self.profile_path}", "blue"))
        print(colored(f"[+] Headless mode: {self.headless}", "blue"))
        print(colored(f"[+] Firefox channel: {self.channel}", "blue"))
        print(colored(f"[+] Firefox executable: {self.executable_path}", "blue"))

        async with async_playwright() as p:
            browser = await p.firefox.launch_persistent_context(
                user_data_dir=self.profile_path,
                headless=self.headless,
                executable_path=self.executable_path
            )
            print(colored("[+] Firefox browser launched successfully", "green"))

            try:
                page = await browser.new_page()

                # Navigate to Facebook Business Portal
                print(colored("[+] Navigating to Facebook Creator Studio...", "blue"))
                await page.goto("https://business.facebook.com/creatorstudio")

                # Wait for login if needed
                await page.wait_for_load_state('networkidle')

                # Check if logged in
                if "login" in page.url.lower():
                    print(colored("[!] Please login to Facebook in the browser window", "yellow"))
                    print(colored("[!] Waiting for login to complete...", "yellow"))
                    await page.wait_for_url(lambda url: "creatorstudio" in url, timeout=300000)  # 5 min timeout
                    print(colored("[+] Login detected, continuing with upload", "green"))
            except Exception as e:
                print(colored(f"[-] Error during Facebook upload setup: {str(e)}", "red"))
                await browser.close()
                raise

            # Navigate to video upload
            await page.click('text="Create post"')
            await page.click('text="Video"')

            # Upload file
            file_input = await page.query_selector('input[type="file"]')
            if file_input:
                await file_input.set_input_files(video_path)
            else:
                raise Exception("Could not find file input element on Facebook upload page")

            # Wait for upload
            await page.wait_for_selector('text="Video uploaded successfully"', timeout=600000)  # 10 min

            # Add title and description
            if title:
                title_input = await page.query_selector('[placeholder*="title"]')
                if title_input:
                    await title_input.fill(title)
                else:
                    print("Warning: Could not find title input field")

            if description:
                desc_input = await page.query_selector('[placeholder*="description"]')
                if desc_input:
                    await desc_input.fill(description)
                else:
                    print("Warning: Could not find description input field")

            # Schedule if time provided
            if schedule_time:
                await page.click('text="Schedule"')
                # Implement scheduling logic here
                # This would require interacting with Facebook's scheduling UI

            # Publish
            await page.click('text="Publish"')

            await browser.close()

    async def bulk_upload(self, videos_list):
        for video in videos_list:
            await self.upload_video(**video)
            await asyncio.sleep(5)  # Delay between uploads

def find_firefox_profiles():
    """
    Utility function to help users find their Firefox profile paths
    """
    profiles_dir = Path("~/.mozilla/firefox").expanduser()

    if not profiles_dir.exists():
        print(colored(f"[-] Firefox profiles directory not found: {profiles_dir}", "red"))
        print(colored("[-] Please ensure Firefox is installed and has been run at least once.", "yellow"))
        return []

    profiles = []
    print(colored(f"[+] Found Firefox profiles in: {profiles_dir}", "green"))

    for profile in profiles_dir.iterdir():
        if profile.is_dir() and not profile.name.startswith('.'):
            profiles.append(str(profile))
            print(colored(f"  - {profile.name}: {profile}", "blue"))

    if not profiles:
        print(colored("[-] No Firefox profiles found", "yellow"))

    return profiles

# Usage example
if __name__ == "__main__":
    print("Finding Firefox profiles...")
    profiles = find_firefox_profiles()

    if profiles:
        print("\nTo use a specific profile, set the environment variable:")
        print(f"export FIREFOX_PROFILE_PATH=\"{profiles[0]}\"")
        print("\nOr add it to your .env file:")
        print(f"FIREFOX_PROFILE_PATH={profiles[0]}")

    uploader = FacebookUploader()
    asyncio.run(uploader.upload_video(
        "/path/to/video.mp4",
        title="My Video",
        description="Description"
    ))