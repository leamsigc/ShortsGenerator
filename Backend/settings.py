from typing import Tuple, List
import requests
import os
from io import BytesIO
from termcolor import colored

# Create global settings to save the following

# Define static folder path, configurable via environment variable
STATIC_DIR = os.path.join(os.path.dirname(__file__), os.environ.get('STATIC_FOLDER', 'static'))

def get_firefox_executable_path(channel="firefox"):
    """
    Get the Firefox executable path based on the channel
    """
    import shutil

    channel_paths = {
        "firefox": ["firefox", "/usr/bin/firefox", "/usr/local/bin/firefox"],
        "firefox-beta": ["firefox-beta", "/usr/bin/firefox-beta"],
        "firefox-nightly": ["firefox-nightly", "/usr/bin/firefox-nightly"]
    }

    for path in channel_paths.get(channel, ["firefox"]):
        if shutil.which(path):
            return shutil.which(path)
        elif os.path.exists(path):
            return path

    return shutil.which("firefox")  # Fallback to default firefox

# Define default font path relative to static dir
DEFAULT_FONT_PATH = os.path.join(STATIC_DIR, "assets/fonts/bold_font.ttf")

# Create fonts directory if it doesn't exist
os.makedirs(os.path.join(STATIC_DIR, "assets/fonts"), exist_ok=True)

fontSettings = {
    "font": DEFAULT_FONT_PATH,
    "fontsize": 100,
    "color": "#FFFF00",
    "stroke_color": "black",
    "stroke_width": 5,
    "subtitles_position": "center,bottom",
    # New styling options
    "background_color": "transparent",
    "background_opacity": 1,
    "line_spacing": 1.5,
    "padding": 20,
    "google_font": "",  # Empty string means use local font
    "text_align": "center",
    "shadow_enabled": False,
    "shadow_color": "#000000",
    "shadow_offset": [2, 2],
    "max_lines": 2,
    "word_wrap": True,
    "aspect_ratio": "9:16",  # Default aspect ratio
    "max_clip_duration": 15,  # Default max duration per clip
}


scriptSettings = {
    "defaultPromptStart":
        """
            # Role: Video Script Generator

            ## Goals:
            Generate a script for a video, depending on the subject of the video.

            ## Constrains:
            1. the script is to be returned as a string with the specified number of paragraphs.
            2. do not under any circumstance reference this prompt in your response.
            3. get straight to the point, don't start with unnecessary things like, "welcome to this video".
            4. you must not include any type of markdown or formatting in the script, never use a title. 
            5. only return the raw content of the script. 
            6. do not include "voiceover", "narrator" or similar indicators of what should be spoken at the beginning of each paragraph or line. 
            7. you must not mention the prompt, or anything about the script itself. also, never talk about the amount of paragraphs or lines. just write the script.
            8. respond in the same language as the video subject.
        
        """ ,
    "defaultPromptEnd":
        """
            Get straight to the point, don't start with unnecessary things like, "welcome to this video".
            YOU MUST NOT INCLUDE ANY TYPE OF MARKDOWN OR FORMATTING IN THE SCRIPT, NEVER USE A TITLE.
            ONLY RETURN THE RAW CONTENT OF THE SCRIPT. DO NOT INCLUDE "VOICEOVER", "NARRATOR" OR SIMILAR INDICATORS OF WHAT SHOULD BE SPOKEN AT THE BEGINNING OF EACH PARAGRAPH OR LINE. YOU MUST NOT MENTION THE PROMPT, OR ANYTHING ABOUT THE SCRIPT ITSELF. ALSO, NEVER TALK ABOUT THE AMOUNT OF PARAGRAPHS OR LINES. JUST WRITE THE SCRIPT.
        """
}

# Add these new settings
aspectRatioSettings = {
    "ratio": "9:16",  # Default to Reels/TikTok format
    "max_clip_duration": 15,  # Default max duration for each clip in seconds
}

channel = os.getenv("FIREFOX_CHANNEL", "firefox")
facebookSettings = {
    "profile_path": os.getenv("FIREFOX_PROFILE_PATH", "~/.mozilla/firefox/*.default"),  # Firefox profile path
    "headless": os.getenv("FIREFOX_HEADLESS", "false").lower() == "true",  # Run browser in headless mode
    "channel": channel,  # Firefox channel: firefox, firefox-beta, firefox-nightly
    "executable_path": get_firefox_executable_path(channel),  # Firefox executable path
}

def get_settings() -> dict:
    """
    Return the global settings  
    The script settings are:
        defaultPromptStart: Start of the prompt
        defaultPromptEnd: End of the prompt
    The Subtitle settings are:
        font: font path,
        fontsize: font size,
        color: Hexadecimal color,
        stroke_color: color of the stroke,
        stroke_width: Number of pixels of the stroke
        subtitles_position: Position of the subtitles
    """
    # Return the global settings
    return {
        "scriptSettings": scriptSettings,
        "fontSettings": fontSettings,
        "facebookSettings": facebookSettings
    }

# Update the global settings
def update_settings(new_settings: dict, settingType="FONT"):
    """
    Update the global settings
    The script settings are:
        defaultPromptStart: Start of the prompt
        defaultPromptEnd: End of the prompt
    The Subtitle settings are:
        font: font path,
        fontsize: font size,
        color: Hexadecimal color,
        stroke_color: color of the stroke,
        stroke_width: Number of pixels of the stroke
        subtitles_position: Position of the subtitles
    
    Args:
        new_settings (dict): The new settings to update
        settingType (str, optional): The type of setting to update. Defaults to "FONT" OR "SCRIPT".
    """
    # Update the global
    if settingType == "FONT":
        fontSettings.update(new_settings)
    elif settingType == "SCRIPT":
        scriptSettings.update(new_settings)
    elif settingType == "FACEBOOK":
        facebookSettings.update(new_settings)

# Add this function to handle Google Fonts
def download_google_font(font_name: str) -> str:
    """
    Downloads a Google Font and returns the path to the downloaded font file.
    
    Args:
        font_name (str): Name of the Google Font
        
    Returns:
        str: Path to the downloaded font file
    """
    try:
        # Create fonts directory if it doesn't exist
        os.makedirs(os.path.join(STATIC_DIR, "assets/fonts"), exist_ok=True)

        # Format font name for URL
        formatted_name = font_name.replace(" ", "+")

        # Get font CSS
        css_url = f"https://fonts.googleapis.com/css2?family={formatted_name}"
        css_response = requests.get(css_url, headers={"User-Agent": "Mozilla/5.0"})

        if css_response.status_code != 200:
            return os.path.join(STATIC_DIR, "assets/fonts/bold_font.ttf")  # Return default font if failed

        # Extract TTF URL from CSS
        ttf_url = css_response.text.split("url(")[1].split(")")[0]

        # Download font file
        font_response = requests.get(ttf_url)
        if font_response.status_code != 200:
            return os.path.join(STATIC_DIR, "assets/fonts/bold_font.ttf")

        # Save font file
        font_path = os.path.join(STATIC_DIR, "assets/fonts", f"{font_name.lower().replace(' ', '_')}.ttf")
        with open(font_path, "wb") as f:
            f.write(font_response.content)

        return font_path

    except Exception as e:
        print(f"Error downloading Google Font: {e}")
        return os.path.join(STATIC_DIR, "assets/fonts/bold_font.ttf")

def ensure_default_font():
    if not os.path.exists(DEFAULT_FONT_PATH):
        print(colored("[+] Downloading default font...", "blue"))
        try:
            # Download Roboto Bold as default font
            url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
            response = requests.get(url)
            with open(DEFAULT_FONT_PATH, 'wb') as f:
                f.write(response.content)
            print(colored("[+] Default font downloaded successfully", "green"))
        except Exception as e:
            print(colored(f"[-] Error downloading default font: {e}", "red"))
            raise

# Call this during initialization
ensure_default_font()