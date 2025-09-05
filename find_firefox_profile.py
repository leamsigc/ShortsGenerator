#!/usr/bin/env python3
"""
Utility script to find Firefox profile paths and available Firefox channels for Facebook upload configuration
"""

import os
import shutil
import subprocess
from pathlib import Path
from termcolor import colored

def find_firefox_profiles():
    """
    Find all Firefox profiles on the system
    """
    profiles_dir = Path("~/.mozilla/firefox").expanduser()

    if not profiles_dir.exists():
        print(colored(f"❌ Firefox profiles directory not found: {profiles_dir}", "red"))
        print(colored("💡 Please ensure Firefox is installed and has been run at least once.", "yellow"))
        return []

    profiles = []
    print(colored(f"🔍 Found Firefox profiles in: {profiles_dir}", "green"))
    print()

    for profile in profiles_dir.iterdir():
        if profile.is_dir() and not profile.name.startswith('.') and ' ' not in profile.name:
            profiles.append(str(profile))
            print(colored(f"📁 {profile.name}", "blue"))
            print(colored(f"   Path: {profile}", "cyan"))

            # Check if it's a default profile and suggest channel
            if profile.name.endswith('.default') or profile.name.endswith('.default-release'):
                print(colored("   ⭐ This appears to be a stable/beta default profile", "green"))
                print(colored("   💡 Recommended FIREFOX_CHANNEL: firefox", "cyan"))
            elif profile.name.endswith('.default-nightly'):
                print(colored("   ⭐ This appears to be a nightly default profile", "green"))
                print(colored("   💡 Recommended FIREFOX_CHANNEL: firefox-nightly", "cyan"))
            elif 'nightly' in profile.name.lower():
                print(colored("   🌙 This appears to be a nightly profile", "yellow"))
                print(colored("   💡 Recommended FIREFOX_CHANNEL: firefox-nightly", "cyan"))
            print()

    if not profiles:
        print(colored("❌ No Firefox profiles found", "yellow"))
        return []

    return profiles

def find_firefox_channels():
    """
    Find available Firefox channels (stable, beta, nightly) and their versions
    """
    channels = {
        "firefox": ["firefox", "/usr/bin/firefox", "/usr/local/bin/firefox", "/opt/firefox/firefox"],
        "firefox-beta": ["firefox-beta", "/usr/bin/firefox-beta", "/opt/firefox-beta/firefox"],
        "firefox-nightly": ["firefox-nightly", "/usr/bin/firefox-nightly", "/opt/firefox-nightly/firefox"]
    }

    available_channels = []
    seen_paths = set()  # Track unique paths to avoid duplicates

    print(colored("🔍 Checking for Firefox channels...", "green"))
    print()

    for channel_name, possible_paths in channels.items():
        for path in possible_paths:
            actual_path = None
            if os.path.exists(path):
                actual_path = path
            else:
                found_path = shutil.which(path.split('/')[-1])
                if found_path:
                    actual_path = found_path

            if actual_path and actual_path not in seen_paths:
                try:
                    # Try to get version
                    cmd = [actual_path, "--version"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

                    if result.returncode == 0:
                        version = result.stdout.strip().split()[-1] if result.stdout.strip() else "Unknown"
                        available_channels.append({
                            "name": channel_name,
                            "path": actual_path,
                            "version": version
                        })
                        seen_paths.add(actual_path)
                        break
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                    continue

    return available_channels

def main():
    print(colored("🦊 Firefox Profile & Channel Finder", "cyan"))
    print(colored("=" * 50, "cyan"))
    print()

    # Find Firefox channels first
    channels = find_firefox_channels()

    if channels:
        print(colored("✅ Available Firefox Channels:", "green"))
        print()
        for channel in channels:
            print(colored(f"🔥 {channel['name'].upper()}", "blue"))
            print(colored(f"   Path: {channel['path']}", "cyan"))
            print(colored(f"   Version: {channel['version']}", "cyan"))
            print()
    else:
        print(colored("❌ No Firefox channels found", "red"))
        print(colored("💡 Please install Firefox from your package manager", "yellow"))
        print()

    # Find profiles
    profiles = find_firefox_profiles()

    if profiles:
        print(colored("✅ Setup Instructions:", "green"))
        print()
        print(colored("1. Choose a Firefox profile path from above", "white"))
        print(colored("2. Choose a Firefox channel from above (if multiple available)", "white"))
        print(colored("3. Add them to your .env file:", "white"))
        print()

        # Find the default profile if available
        default_profile = None
        for profile in profiles:
            if profile.endswith('.default') or profile.endswith('.default-release'):
                default_profile = profile
                break

        if default_profile:
            print(colored(f"   FIREFOX_PROFILE_PATH={default_profile}", "yellow"))
        else:
            print(colored(f"   FIREFOX_PROFILE_PATH={profiles[0]}", "yellow"))

        # Suggest channel based on available channels
        if channels:
            default_channel = "firefox"  # Default to stable
            if any(c["name"] == "firefox" for c in channels):
                default_channel = "firefox"
            elif channels:
                default_channel = channels[0]["name"]

            print(colored(f"   FIREFOX_CHANNEL={default_channel}", "yellow"))
        else:
            print(colored("   FIREFOX_CHANNEL=firefox  # Default stable channel", "yellow"))

        print(colored("   FIREFOX_HEADLESS=false", "yellow"))
        print()
        print(colored("4. Restart the application", "white"))
    else:
        print()
        print(colored("💡 To create a Firefox profile:", "yellow"))
        print(colored("   1. Open Firefox", "white"))
        print(colored("   2. Type 'about:profiles' in the address bar", "white"))
        print(colored("   3. Click 'Create a new profile'", "white"))
        print(colored("   4. Run this script again", "white"))

if __name__ == "__main__":
    main()