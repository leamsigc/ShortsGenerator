# Create global settings to save the following


fontSettings = {
    "font": "static/assets/fonts/bold_font.ttf",
    "fontsize": 100,
    "color": "#FFFF00",
    "stroke_color": "black",
    "stroke_width": 5,
    "subtitles_position": "center,bottom",
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
        "fontSettings": fontSettings
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