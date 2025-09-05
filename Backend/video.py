import os
import uuid

import requests
import srt_equalizer
import assemblyai as aai
from uuid import uuid4


from settings import *
from typing import List
from moviepy.editor import *
from termcolor import colored
from dotenv import load_dotenv
from datetime import timedelta
from moviepy.video.fx.all import crop
from moviepy.video.tools.subtitles import SubtitlesClip

load_dotenv("../.env")

ASSEMBLY_AI_API_KEY = os.getenv("ASSEMBLY_AI_API_KEY")

# Add these constants at the top of the file
ASPECT_RATIOS = {
    "9:16": (1080, 1920),  # Reels, TikTok, Stories
    "16:9": (1920, 1080),  # Landscape YouTube
    "1:1": (1080, 1080),   # Square Instagram
    "4:5": (1080, 1350),   # Instagram Portrait
}


def save_video(video_url: str, directory: str = None) -> str:
    """
    Downloads a video from the given URL and saves it to a specified directory.

    Args:
        video_url (str): The URL of the video to download.
        directory (str): The path of the temporary directory to save the video to.

    Returns:
        str: The path to the saved video.
    """
    if directory is None:
        directory = os.path.join(STATIC_DIR, "assets/temp")
    # Ensure the directory exists
    os.makedirs(directory, exist_ok=True)

    video_id = uuid.uuid4()
    video_path = os.path.join(directory, f"{video_id}.mp4")

    # Set headers to mimic a browser request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
    }

    try:
        response = requests.get(video_url, headers=headers, stream=True)
        response.raise_for_status()  # Check if the request was successful

        # Write the video content to the file in chunks
        with open(video_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)

        return video_path

    except requests.exceptions.RequestException as e:
        print(f"Error downloading the video: {e}")
        return None
    except Exception as e:
        print(f"Error processing the video: {e}")
        return None


def __generate_subtitles_assemblyai(audio_path: str, voice: str) -> str:
    """
    Generates subtitles from a given audio file and returns the path to the subtitles.

    Args:
        audio_path (str): The path to the audio file to generate subtitles from.

    Returns:
        str: The generated subtitles
    """

    language_mapping = {
        "br": "pt",
        "id": "en", #AssemblyAI doesn't have Indonesian 
        "jp": "ja",
        "kr": "ko",
    }

    if voice in language_mapping:
        lang_code = language_mapping[voice]
    else:
        lang_code = voice

    aai.settings.api_key = ASSEMBLY_AI_API_KEY
    config = aai.TranscriptionConfig(language_code=lang_code)
    transcriber = aai.Transcriber(config=config)
    transcript = transcriber.transcribe(audio_path)
    subtitles = transcript.export_subtitles_srt()

    return subtitles


def __generate_subtitles_locally(sentences: List[str], audio_clips: List[AudioFileClip]) -> str:
    """
    Generates subtitles from a given audio file and returns the path to the subtitles.

    Args:
        sentences (List[str]): all the sentences said out loud in the audio clips
        audio_clips (List[AudioFileClip]): all the individual audio clips which will make up the final audio track
    Returns:
        str: The generated subtitles
    """

    def convert_to_srt_time_format(total_seconds):
        # Convert total seconds to the SRT time format: HH:MM:SS,mmm
        if total_seconds == 0:
            return "0:00:00,0"
        return str(timedelta(seconds=total_seconds)).rstrip('0').replace('.', ',')

    start_time = 0
    subtitles = []

    for i, (sentence, audio_clip) in enumerate(zip(sentences, audio_clips), start=1):
        duration = audio_clip.duration
        end_time = start_time + duration

        # Format: subtitle index, start time --> end time, sentence
        subtitle_entry = f"{i}\n{convert_to_srt_time_format(start_time)} --> {convert_to_srt_time_format(end_time)}\n{sentence}\n"
        subtitles.append(subtitle_entry)

        start_time += duration  # Update start time for the next subtitle

    return "\n".join(subtitles)


def generate_subtitles(audio_path: str, sentences: List[str], audio_clips: List[AudioFileClip], voice: str) -> str:
    """
    Generates subtitles from a given audio file and returns the path to the subtitles.

    Args:
        audio_path (str): The path to the audio file to generate subtitles from.
        sentences (List[str]): all the sentences said out loud in the audio clips
        audio_clips (List[AudioFileClip]): all the individual audio clips which will make up the final audio track

    Returns:
        str: The path to the generated subtitles.
    """

    def equalize_subtitles(srt_path: str, max_chars: int = 10) -> None:
        # Equalize subtitles
        srt_equalizer.equalize_srt_file(srt_path, srt_path, max_chars)

    # Save subtitles
    subtitles_path = os.path.join(STATIC_DIR, "assets/subtitles", f"{uuid.uuid4()}.srt")

    if ASSEMBLY_AI_API_KEY is not None and ASSEMBLY_AI_API_KEY != "":
        print(colored("[+] Creating subtitles using AssemblyAI", "blue"))
        subtitles = __generate_subtitles_assemblyai(audio_path, voice)
    else:
        print(colored("[+] Creating subtitles locally", "blue"))
        subtitles = __generate_subtitles_locally(sentences, audio_clips)

    with open(subtitles_path, "w") as file:
        file.write(subtitles)

    # Equalize subtitles
    equalize_subtitles(subtitles_path)

    print(colored("[+] Subtitles generated.", "green"))

    return subtitles_path


def combine_videos(video_paths: List[str], max_duration: int, max_clip_duration: int, threads: int) -> str:
    """
    Combines a list of videos into one video and returns the path to the combined video.
    """
    video_id = uuid.uuid4()
    combined_video_path = os.path.join(STATIC_DIR, "assets/temp", f"{video_id}-combined.mp4")
    
    # Get settings
    settings = get_settings()
    aspect_ratio = settings["fontSettings"]["aspect_ratio"]
    target_width, target_height = ASPECT_RATIOS.get(aspect_ratio, (1080, 1920))
    
    clips = []
    tot_dur = 0
    
    while tot_dur < max_duration:
        for video_path in video_paths:
            clip = VideoFileClip(video_path)
            if clip is None:
                continue

            clip = clip.without_audio()
            
            # Apply duration limits
            if (max_duration - tot_dur) < clip.duration:
                clip = clip.subclip(0, (max_duration - tot_dur))
            elif max_clip_duration < clip.duration:
                clip = clip.subclip(0, max_clip_duration)

            # Calculate crop dimensions based on target aspect ratio
            target_ratio = target_width / target_height
            current_ratio = clip.w / clip.h

            if current_ratio > target_ratio:
                # Video is wider than target
                new_w = int(clip.h * target_ratio)
                clip = crop(clip, width=new_w, height=clip.h,
                          x_center=clip.w/2, y_center=clip.h/2)
            else:
                # Video is taller than target
                new_h = int(clip.w / target_ratio)
                clip = crop(clip, width=clip.w, height=new_h,
                          x_center=clip.w/2, y_center=clip.h/2)

            # Resize to target dimensions
            clip = clip.resize((target_width, target_height))

            clips.append(clip)
            tot_dur += clip.duration

    final_clip = concatenate_videoclips(clips)
    final_clip = final_clip.set_fps(30)
    final_clip.write_videofile(combined_video_path, threads=threads)

    return combined_video_path


def generate_video(combined_video_path: str, tts_path: str, subtitles_path: str, threads: int, subtitles_position: str) -> str:
    """
    Creates the final video with subtitles and audio.
    """
    print(colored("[+] Starting video generation...", "green"))

    # Get the Settings
    settings = get_settings()
    font_settings = settings["fontSettings"]

    # Define default font path
    default_font = os.path.join(STATIC_DIR, "assets/fonts/bold_font.ttf")
    
    # Handle Google Font if specified
    font_path = font_settings.get("font", default_font)
    
    if font_settings.get("google_font"):
        try:
            font_path = download_google_font(font_settings["google_font"])
        except Exception as e:
            print(colored(f"[!] Error downloading Google Font: {e}", "yellow"))
            print(colored("[!] Using default font instead", "yellow"))
            font_path = default_font
    
    # Ensure we have a valid font path
    if not font_path or not os.path.exists(font_path):
        print(colored("[!] Font path not found, using default font", "yellow"))
        font_path = default_font

    # Final check to ensure font exists
    if not os.path.exists(font_path):
        raise ValueError(f"Font file not found at: {font_path}")

    # Create text generator with all styling options
    generator = lambda txt: TextClip(
        txt,
        font=font_path,
        fontsize=font_settings.get("fontsize", 100),
        color=font_settings.get("color", "#FFFFFF"),
        stroke_color=font_settings.get("stroke_color", "black"),
        stroke_width=font_settings.get("stroke_width", 5),
        bg_color=font_settings.get("background_color", "transparent") 
            if font_settings.get("background_opacity", 0) > 0 else None,
        size=(ASPECT_RATIOS[font_settings.get("aspect_ratio", "9:16")][0] - 
              2*font_settings.get("padding", 20), None),
        method='caption',
        align=font_settings.get("text_align", "center"),
        interline=font_settings.get("line_spacing", 1.5),
        kerning=0
    )

    # Split the subtitles position into horizontal and vertical
    horizontal_subtitles_position, vertical_subtitles_position = font_settings["subtitles_position"].split(",")

    # if subtitle position is not the same as the setting and is not empty we override
    if subtitles_position != font_settings["subtitles_position"] and subtitles_position != "":
        horizontal_subtitles_position, vertical_subtitles_position = subtitles_position.split(",")
        
    # Burn the subtitles into the video
    print(colored(f"[+] Subtitles Path: {subtitles_path}", "green"))
    subtitles = SubtitlesClip(subtitles_path, generator)
    result = CompositeVideoClip([
        VideoFileClip(combined_video_path),
        subtitles.set_pos((horizontal_subtitles_position, vertical_subtitles_position))
    ])

    print(colored("[+] Adding audio...", "green"))
    # Add the audio
    audio = AudioFileClip(tts_path)
    result = result.set_audio(audio)
    print(colored("[+] Audio Done...", "green"))

    video_name = os.path.join(STATIC_DIR, "generated_videos", f"{uuid4()}.mp4")
    print(colored("[+] Writing video...", "green"))
    result.write_videofile(f"{video_name}", threads=threads)
    # Remove the Backend directory from the video_name to return static/generated_videos/...
    backend_dir = os.path.dirname(STATIC_DIR) + os.sep
    video_name = video_name.replace(backend_dir, "")
    print(colored(f"[+] Video name {video_name}...", "green"))
    return video_name
