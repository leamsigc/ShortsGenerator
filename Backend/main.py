import asyncio
import os
import threading
from utils import *
from dotenv import load_dotenv

# Load environment variables
# For Docker containers, use environment variables directly
# For local development, load from .env files
script_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(script_dir, ".env")):
    load_dotenv(os.path.join(script_dir, ".env"))
elif os.path.exists(os.path.join(script_dir, "..", ".env")):
    load_dotenv(os.path.join(script_dir, "..", ".env"))
# Note: In Docker, environment variables should be set in docker-compose.yml
# Check if all required environment variables are set
# This must happen before importing video which uses API keys without checking
check_env_vars()

from gpt import *
from video import *
from search import *
from classes.Shorts import *
from uuid import uuid4
from voice import *
from flask_cors import CORS
from termcolor import colored
from youtube import upload_video
from flask import Flask, request, jsonify
import json
from moviepy.config import change_settings
from classes.instagram_downloader import InstagramDownloader
from facebook_upload import FacebookUploader

# Set environment variables
SESSION_ID = os.getenv("TIKTOK_SESSION_ID")
openai_api_key = os.getenv('OPENAI_API_KEY')
change_settings({"IMAGEMAGICK_BINARY": os.getenv("IMAGEMAGICK_BINARY")})

# Get the script directory for absolute paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# Initialize Flask
from settings import STATIC_DIR
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
CORS(app)

# Constants
HOST = "0.0.0.0"
PORT = 8080

# Global progress for generation
PROGRESS = 0
AMOUNT_OF_STOCK_VIDEOS = 5
GENERATING = False
generation_status = {
    "is_running": False,
    "current_step": "",
    "progress": 0,
    "final_video": None,
    "error": None
}

# Create a method to create all the required folders
def create_folders():
    """Create all required folders for the application"""
    folders = [
        "",
        "assets",
        "assets/temp",
        "assets/subtitles",
        "generated_videos",
        "generated_videos/instagram",
    ]

    for folder in folders:
        folder_path = os.path.join(STATIC_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"Created/verified folder: {folder_path}")

# Create folders
create_folders()

# Instagram video download endpoint
@app.route("/api/instagram/download", methods=["POST"])
def download_instagram_video():
    try:
        data = request.get_json()
        video_url = data.get('url')
        
        if not video_url:
            return jsonify({
                "status": "error",
                "message": "No Instagram URL provided",
            }), 400

        # Initialize downloader with output path in static/assets
        downloader = InstagramDownloader(output_path=os.path.join(STATIC_DIR, "generated_videos/instagram"))
        
        # Download the video
        result = downloader.download_video(video_url)
        
        return jsonify({
            "status": "success",
            "message": "Video downloaded successfully",
            "data": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


# Generation Endpoint
@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        # Set global variable
        global GENERATING
        GENERATING = True

        # Clean
        clean_dir(os.path.join(STATIC_DIR, "assets/temp"))
        clean_dir(os.path.join(STATIC_DIR, "assets/subtitles"))


        # Parse JSON
        data = request.get_json()
        paragraph_number = int(data.get('paragraphNumber', 1))  # Default to 1 if not provided
        ai_model = data.get('aiModel')  # Get the AI model selected by the user
        n_threads = data.get('threads')  # Amount of threads to use for video generation
        subtitles_position = data.get('subtitlesPosition')  # Position of the subtitles in the video

        # Get 'useMusic' from the request data and default to False if not provided
        use_music = data.get('useMusic', False)

        # Get 'automateYoutubeUpload' from the request data and default to False if not provided
        automate_youtube_upload = data.get('automateYoutubeUpload', False)
        # Get 'automateFacebookUpload' from the request data and default to False if not provided
        automate_facebook_upload = data.get('automateFacebookUpload', False)
        facebook_schedule_date = data.get('facebookScheduleDate', '')
        facebook_schedule_time = data.get('facebookScheduleTime', '09:00')
        # Get 'background' from the request data and default to False if not provided
        background = data.get('background', False)

        # Get personalization settings
        text_settings = data.get('textSettings', {})
        aspect_ratio = data.get('aspectRatio', '9:16')

        voice = data.get("voice", "en_us_001")
        voice_prefix = voice[:2]

        if not voice:
            print(colored("[!] No voice was selected. Defaulting to \"en_us_001\"", "yellow"))
            voice = "en_us_001"
            voice_prefix = voice[:2]
        if background:
            # Generate script and search terms first
            videoClass = Shorts(data["videoSubject"], paragraph_number, ai_model, data["customPrompt"], threads=n_threads)
            videoClass.GenerateScript()
            videoClass.GenerateSearchTerms()

            # Prepare data for background generation
            bg_data = {
                "search": videoClass.search_terms,
                "script": videoClass.final_script,
                "aiModel": ai_model,
                "voice": voice,
                "selectedVideoUrls": [],
                "subtitlesPosition": subtitles_position,
                "threads": n_threads,
                "automateFacebookUpload": automate_facebook_upload,
                "facebookScheduleDate": facebook_schedule_date,
                "facebookScheduleTime": facebook_schedule_time,
                "useMusic": use_music,
                "automateYoutubeUpload": automate_youtube_upload,
            }

            # Start generation in background
            thread = threading.Thread(target=run_generation, args=(bg_data,))
            thread.start()

            return jsonify({
                "status": "success",
                "message": "Generation started in background",
                "data": {}
            })
        else:
            # Synchronous generation
            # Generate script and search terms first
            videoClass = Shorts(data["videoSubject"], paragraph_number, ai_model, data["customPrompt"], threads=n_threads)
            videoClass.GenerateScript()
            videoClass.GenerateSearchTerms()

            # Prepare data for background generation
            bg_data = {
                "search": videoClass.search_terms,
                "script": videoClass.final_script,
                "aiModel": ai_model,
                "voice": voice,
                "selectedVideoUrls": [],
                "subtitlesPosition": subtitles_position,
                "threads": n_threads,
                "automateFacebookUpload": automate_facebook_upload,
                "facebookScheduleDate": facebook_schedule_date,
                "facebookScheduleTime": facebook_schedule_time,
                "useMusic": use_music,
                "automateYoutubeUpload": automate_youtube_upload,
            }

            # Start generation in background
            thread = threading.Thread(target=run_generation, args=(bg_data,))
            thread.start()

            return jsonify({
                "status": "success",
                "message": "Generation started in background",
                "data": {}
            })

            if automate_youtube_upload:
                # Start Youtube Uploader
                # Check if the CLIENT_SECRETS_FILE exists
                client_secrets_file = os.path.join(SCRIPT_DIR, "client_secret.json")
                SKIP_YT_UPLOAD = False
                if not os.path.exists(client_secrets_file):
                    SKIP_YT_UPLOAD = True
                    print(colored("[-] Client secrets file missing. YouTube upload will be skipped.", "yellow"))
                    print(colored("[-] Please download the client_secret.json from Google Cloud Platform and store this inside the /Backend directory.", "red"))

                # Only proceed with YouTube upload if the toggle is True  and client_secret.json exists.
                if not SKIP_YT_UPLOAD:
                    # Choose the appropriate category ID for your videos
                    video_category_id = "28"  # Science & Technology
                    privacyStatus = "private"  # "public", "private", "unlisted"
                    video_metadata = {
                        'video_path': os.path.abspath(videoClass.get_final_video_path) if videoClass.get_final_video_path else "",
                        'title': videoClass.video_title,
                        'description': videoClass.video_description,
                        'category': video_category_id,
                        'keywords': ",".join(videoClass.video_tags) if videoClass.video_tags else "",
                        'privacyStatus': privacyStatus,
                    }

                    # Upload the video to YouTube
                    try:
                        # Unpack the video_metadata dictionary into individual arguments
                        video_response = upload_video(
                            video_path=video_metadata['video_path'],
                            title=video_metadata['title'],
                            description=video_metadata['description'],
                            category=video_metadata['category'],
                            keywords=video_metadata['keywords'],
                            privacy_status=video_metadata['privacyStatus']
                        )
                        print(f"Uploaded video ID: {video_response.get('id')}")
                    except HttpError as e:
                        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")

            if automate_facebook_upload and videoClass.get_final_video_path:
                try:
                    schedule_time = None
                    if facebook_schedule_date and facebook_schedule_time:
                        schedule_time = f"{facebook_schedule_date}T{facebook_schedule_time}:00Z"

                    uploader = FacebookUploader()
                    asyncio.run(uploader.upload_video(
                        video_path=os.path.abspath(videoClass.get_final_video_path),
                        title=videoClass.video_title or "Generated Video",
                        description=videoClass.video_description or "Auto-generated video",
                        schedule_time=schedule_time
                    ))
                    print(colored("[+] Video uploaded to Facebook!", "green"))
                except Exception as e:
                    print(colored(f"[-] Error uploading to Facebook: {str(e)}", "red"))

            videoClass.AddMusic(use_music)
            # Let user know
            print(colored(f"[+] Video generated: {videoClass.get_final_video_path}!", "green"))
            videoClass.Stop()

            # Return JSON
            return jsonify(
                {
                    "status": "success",
                    "message": "Video generated! See MoneyPrinter/output.mp4 for result.",
                    "data": videoClass.get_final_video_path,
                }
            )
        
        voice = data["voice"]
        voice_prefix = voice[:2]


        if not voice:
            print(colored("[!] No voice was selected. Defaulting to \"en_us_001\"", "yellow"))
            voice = "en_us_001"
            voice_prefix = voice[:2]


        videoClass = Shorts(data["videoSubject"], paragraph_number, ai_model, data["customPrompt"])
        # Generate a script
        videoClass.GenerateScript()
        # Generate search terms
        videoClass.GenerateSearchTerms()

        videoClass.DownloadVideos()

        if not GENERATING:
            return jsonify(
                {
                    "status": "error",
                    "message": "Video generation was cancelled.",
                    "data": [],
                }
            )

        videoClass.GenerateVoice(voice)
        # Concatenate videos
        videoClass.CombineVideos()

        videoClass.GenerateMetadata()

        if automate_youtube_upload:
            # Start Youtube Uploader
            # Check if the CLIENT_SECRETS_FILE exists
            client_secrets_file = os.path.join(SCRIPT_DIR, "client_secret.json")
            SKIP_YT_UPLOAD = False
            if not os.path.exists(client_secrets_file):
                SKIP_YT_UPLOAD = True
                print(colored("[-] Client secrets file missing. YouTube upload will be skipped.", "yellow"))
                print(colored("[-] Please download the client_secret.json from Google Cloud Platform and store this inside the /Backend directory.", "red"))

            # Only proceed with YouTube upload if the toggle is True  and client_secret.json exists.
            if not SKIP_YT_UPLOAD:
                # Choose the appropriate category ID for your videos
                video_category_id = "28"  # Science & Technology
                privacyStatus = "private"  # "public", "private", "unlisted"
                video_metadata = {
                    'video_path': os.path.abspath(videoClass.get_final_video_path),
                    'title': videoClass.video_title,
                    'description': videoClass.video_description,
                    'category': video_category_id,
                    'keywords': ",".join(videoClass.video_tags),
                    'privacyStatus': privacyStatus,
                }

                # Upload the video to YouTube
                try:
                    # Unpack the video_metadata dictionary into individual arguments
                    video_response = upload_video(
                        video_path=video_metadata['video_path'],
                        title=video_metadata['title'],
                        description=video_metadata['description'],
                        category=video_metadata['category'],
                        keywords=video_metadata['keywords'],
                        privacy_status=video_metadata['privacyStatus']
                    )
                    print(f"Uploaded video ID: {video_response.get('id')}")
                except HttpError as e:
                    print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")

        if automate_facebook_upload and videoClass.get_final_video_path:
            try:
                schedule_time = None
                if facebook_schedule_date and facebook_schedule_time:
                    schedule_time = f"{facebook_schedule_date}T{facebook_schedule_time}:00Z"

                uploader = FacebookUploader()
                asyncio.run(uploader.upload_video(
                    video_path=os.path.abspath(videoClass.get_final_video_path),
                    title=videoClass.video_title or "Generated Video",
                    description=videoClass.video_description or "Auto-generated video",
                    schedule_time=schedule_time
                ))
                print(colored("[+] Video uploaded to Facebook!", "green"))
            except Exception as e:
                print(colored(f"[-] Error uploading to Facebook: {str(e)}", "red"))

        videoClass.AddMusic(use_music)
        # Let user know
        print(colored(f"[+] Video generated: {videoClass.get_final_video_path}!", "green"))
        videoClass.Stop()

        # Return JSON
        return jsonify(
            {
                "status": "success",
                "message": "Video generated! See MoneyPrinter/output.mp4 for result.",
                "data": videoClass.get_final_video_path,
            }
        )
    except Exception as err:
        print(colored(f"[-] Error: {str(err)}", "red"))
        return jsonify(
            {
                "status": "error",
                "message": f"Could not retrieve stock videos: {str(err)}",
                "data": [],
            }
        )


@app.route("/api/cancel", methods=["POST"])
def cancel():
    print(colored("[!] Received cancellation request...", "yellow"))

    global GENERATING
    GENERATING = False

    return jsonify({"status": "success", "message": "Cancelled video generation."})

# Route to generate the script and return the video script
@app.route("/api/script", methods=["POST"])
def generate_script_only():
    # Set generating to true
    GENERATING = True

    clean_dir(os.path.join(STATIC_DIR, "assets/subtitles"))
    print(colored("[+] Received script request...", "green"))

    data = request.get_json()
    video_subject = data["videoSubject"]
    extra_prompt = data["extraPrompt"]
    ai_model = data["aiModel"]

    videoClass = Shorts(video_subject, 1, ai_model, "", extra_prompt=extra_prompt)
    script = videoClass.GenerateScript()



    search_terms = videoClass.GenerateSearchTerms()
    
    # Show the search terms 
    print(colored(f"Search terms: {', '.join(search_terms)}", "cyan"))

    return jsonify(
        {
            "status": "success",
            "message": "Script generated!",
            "data": {
                "script": script,
                "search": search_terms
            },
        }
    )

def run_generation(data):
    global generation_status, GENERATING
    try:
        generation_status["is_running"] = True
        generation_status["current_step"] = "Starting generation"
        generation_status["progress"] = 0
        generation_status["error"] = None

        # Set generating to true
        GENERATING = True
        # Clean
        clean_dir(os.path.join(STATIC_DIR, "assets/temp"))
        clean_dir(os.path.join(STATIC_DIR, "assets/subtitles"))

        print(colored("[+] Starting background generation...", "green"))

        search_terms = data["search"]
        script = data["script"]
        ai_model = data["aiModel"]
        voice = data.get("voice")
        selectedVideoUrls = data.get("selectedVideoUrls", [])
        custom_tts_audio_path = data.get("customTtsAudioPath")

        # Extra options:
        custom_video = data.get("videoUrls", [])
        custom_voice = data.get("voiceUrl", "")
        # Set the default subtitles_position to the center, bottom
        subtitles_position = data.get("subtitlesPosition", "center,bottom")
        n_threads = data.get('threads', 4)

        # Facebook upload options
        automate_facebook_upload = data.get('automateFacebookUpload', False)
        facebook_schedule_date = data.get('facebookScheduleDate', '')
        facebook_schedule_time = data.get('facebookScheduleTime', '09:00')

        # Personalization settings
        text_settings = data.get('textSettings', {})
        aspect_ratio = data.get('aspectRatio', '9:16')

        print(colored(f"[+] Received text settings: {text_settings}", "cyan"))
        print(colored(f"[+] Received aspect ratio: {aspect_ratio}", "cyan"))

        if not voice and not custom_tts_audio_path:
            print(colored("[!] No voice was selected. Defaulting to \"en_us_001\"", "yellow"))
            voice = "en_us_001"

        # Search for a video of the given search term
        videoClass = Shorts("", 1, ai_model, '', threads=n_threads)
        videoClass.search_terms = search_terms
        videoClass.final_script = script
        videoClass.subtitles_position = subtitles_position

        # Apply personalization settings
        if text_settings:
            videoClass.apply_text_settings(text_settings)
        if aspect_ratio:
            videoClass.aspect_ratio = aspect_ratio

        generation_status["current_step"] = "Downloading Videos"
        generation_status["progress"] = 20
        videoClass.DownloadVideos(selectedVideoUrls)

        generation_status["current_step"] = "Generating Voice"
        generation_status["progress"] = 40
        videoClass.GenerateVoice(voice, custom_tts_audio_path)

        generation_status["current_step"] = "Generating Video (Optimized)"
        generation_status["progress"] = 60
        videoClass.GenerateVideoOptimized()

        generation_status["current_step"] = "Generating Metadata"
        generation_status["progress"] = 80
        videoClass.GenerateMetadata()

        # Handle YouTube upload if requested
        if 'automateYoutubeUpload' in data and data['automateYoutubeUpload']:
            try:
                # Check if the CLIENT_SECRETS_FILE exists
                client_secrets_file = os.path.join(SCRIPT_DIR, "client_secret.json")
                SKIP_YT_UPLOAD = False
                if not os.path.exists(client_secrets_file):
                    SKIP_YT_UPLOAD = True
                    print(colored("[-] Client secrets file missing. YouTube upload will be skipped.", "yellow"))
                    print(colored("[-] Please download the client_secret.json from Google Cloud Platform and store this inside the /Backend directory.", "red"))

                # Only proceed with YouTube upload if the toggle is True  and client_secret.json exists.
                if not SKIP_YT_UPLOAD:
                    # Choose the appropriate category ID for your videos
                    video_category_id = "28"  # Science & Technology
                    privacyStatus = "private"  # "public", "private", "unlisted"
                    video_metadata = {
                        'video_path': os.path.abspath(videoClass.get_final_video_path),
                        'title': videoClass.video_title,
                        'description': videoClass.video_description,
                        'category': video_category_id,
                        'keywords': ",".join(videoClass.video_tags),
                        'privacyStatus': privacyStatus,
                    }

                    # Upload the video to YouTube
                    try:
                        # Unpack the video_metadata dictionary into individual arguments
                        video_response = upload_video(
                            video_path=video_metadata['video_path'],
                            title=video_metadata['title'],
                            description=video_metadata['description'],
                            category=video_metadata['category'],
                            keywords=video_metadata['keywords'],
                            privacy_status=video_metadata['privacyStatus']
                        )
                        print(f"Uploaded video ID: {video_response.get('id')}")
                    except HttpError as e:
                        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
            except Exception as e:
                print(colored(f"[-] Error uploading to YouTube: {str(e)}", "red"))

        # Add music if requested
        if 'useMusic' in data and data['useMusic']:
            generation_status["current_step"] = "Adding Music"
            generation_status["progress"] = 85
            videoClass.AddMusic(data['useMusic'])

        # Handle Facebook upload if requested
        if automate_facebook_upload and videoClass.get_final_video_path:
            try:
                schedule_time = None
                if facebook_schedule_date and facebook_schedule_time:
                    schedule_time = f"{facebook_schedule_date}T{facebook_schedule_time}:00Z"

                uploader = FacebookUploader()
                asyncio.run(uploader.upload_video(
                    video_path=os.path.abspath(videoClass.get_final_video_path),
                    title=videoClass.video_title or "Generated Video",
                    description=videoClass.video_description or "Auto-generated video",
                    schedule_time=schedule_time
                ))
                print(colored("[+] Video uploaded to Facebook!", "green"))
            except Exception as e:
                print(colored(f"[-] Error uploading to Facebook: {str(e)}", "red"))

        generation_status["current_step"] = "Saving Final Video"
        generation_status["progress"] = 100
        videoClass.Stop()

        generation_status["final_video"] = videoClass.get_final_video_path
        generation_status["is_running"] = False
        generation_status["current_step"] = "Completed"

        print(colored(f"[+] Background generation completed: {videoClass.get_final_video_path}", "green"))

    except Exception as e:
        generation_status["error"] = str(e)
        generation_status["is_running"] = False
        print(colored(f"[-] Error in background generation: {str(e)}", "red"))

# Download the videos and split the script
@app.route("/api/search-and-download", methods=["POST"])
def search_and_download():
    global generation_status

    if generation_status["is_running"]:
        return jsonify({
            "status": "error",
            "message": "Generation already in progress",
        }), 400

    # Check if request has files (FormData) or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form.to_dict()
        # Handle file uploads
        custom_tts_file = request.files.get('customTtsAudio')
        if custom_tts_file:
            # Save the uploaded file
            custom_audio_path = os.path.join(STATIC_DIR, "assets/temp", f"custom_tts_{uuid4()}.wav")
            custom_tts_file.save(custom_audio_path)
            data['customTtsAudioPath'] = custom_audio_path
    else:
        data = request.get_json()

    # Parse JSON strings back to objects
    if 'search' in data and isinstance(data['search'], str):
        data['search'] = json.loads(data['search'])
    if 'selectedVideoUrls' in data and isinstance(data['selectedVideoUrls'], str):
        data['selectedVideoUrls'] = json.loads(data['selectedVideoUrls'])

    # Start generation in background thread
    thread = threading.Thread(target=run_generation, args=(data,))
    thread.start()

    return jsonify({
        "status": "success",
        "message": "Generation started in background",
        "data": {}
    })

# Add audio to the video
@app.route("/api/addAudio", methods=["POST"])
def addAudio():
    GENERATING = True
    data = request.get_json()
    final_video_path = data["finalVideo"]
    song_path = data["songPath"]
    ai_model = data["aiModel"]

    videoClass = Shorts("", 1, ai_model, '', threads=4)
    videoClass.final_video_path = final_video_path

    videoClass.AddMusic(True,song_path)

    videoClass.Stop()
    return jsonify(
        {
            "status": "success",
            "message": "Search and download complete!",
            "data": {
                "finalVideo": os.path.join("static/generated_videos/", videoClass.get_final_music_video_path)
            }
        }
    )


# Get all available songs
@app.route("/api/getSongs", methods=["GET"])
def get_songs():
    songs = os.listdir(os.path.join(STATIC_DIR, "assets/music"))
    return jsonify({
        "status": "success",
        "message": "Songs retrieved successfully!",
        "data": {
            "songs": songs
        }
    })

# Get all available videos
@app.route("/api/getVideos", methods=["GET"])
def get_videos():
    # Get all videos mp4 only
    videos = os.listdir(os.path.join(STATIC_DIR, "generated_videos"))
    videos = [video for video in videos if video.endswith(".mp4")]

    # Get all files to find metadata
    all_files = os.listdir(os.path.join(STATIC_DIR, "generated_videos"))
    metadata_files = [f for f in all_files if f.endswith("_metadata.json")]

    instagramVideos = os.listdir(os.path.join(STATIC_DIR, "generated_videos/instagram"))
    instagramVideos = [video for video in instagramVideos if video.endswith(".mp4")]
    return jsonify(
        {
        "status": "success",
        "message": "Videos retrieved successfully!",
        "data": {
            "videos": videos,
            "metadata": metadata_files,
            "instagram": instagramVideos
            }
        }
    )

# Get all available subtitles
@app.route("/api/getSubtitles", methods=["GET"])
def get_subtitles():
    subtitles = os.listdir(os.path.join(STATIC_DIR, "assets/subtitles"))
    return jsonify(
        {
        "status": "success",
        "message": "Songs retrieved successfully!",
        "data": {
            "subtitles": subtitles
            }
        }
    )


#Get all available models and voices
@app.route("/api/models", methods=["GET"])
def get_models():
    return jsonify(
        {
        "status": "success",
        "message": "Songs retrieved successfully!",
        "data": {
            "voices": available_voices()
            }
        }
    )


@app.route("/api/assets", methods=["GET"])
def get_assets():
    assets_path = os.path.join(STATIC_DIR, "assets/temp")
    video_assets = os.listdir(assets_path)
    videos = [video for video in video_assets if video.endswith(".mp4")]
    return jsonify(
        {
        "status": "success",
        "message": "Assets retrieved successfully!",
        "data": {
            "videos": videos
            }
        }
    )

# Single Facebook upload endpoint
@app.route("/api/facebook/upload", methods=["POST"])
def facebook_upload():
    try:
        data = request.get_json()
        video_path = data.get('video_path')
        title = data.get('title', 'Generated Video')
        description = data.get('description', 'Auto-generated video')
        schedule_time = data.get('schedule_time')

        if not video_path:
            return jsonify({
                "status": "error",
                "message": "Video path is required",
            }), 400

        uploader = FacebookUploader()
        asyncio.run(uploader.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            schedule_time=schedule_time
        ))

        return jsonify({
            "status": "success",
            "message": "Video uploaded to Facebook successfully"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500

# Bulk Facebook upload endpoint
@app.route("/api/facebook/bulk-upload", methods=["POST"])
def bulk_facebook_upload():
    try:
        data = request.get_json()
        videos = data.get('videos', [])
        schedule_from = data.get('schedule_from')
        schedule_to = data.get('schedule_to')
        schedule_time = data.get('schedule_time', '09:00')  # Default to 9 AM
        videos_per_day = data.get('videos_per_day', 1)

        if not videos:
            return jsonify({
                "status": "error",
                "message": "No videos provided",
            }), 400

        # If date range is provided, distribute videos across dates
        if schedule_from and schedule_to:
            from datetime import datetime, timedelta
            start_date = datetime.fromisoformat(schedule_from.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(schedule_to.replace('Z', '+00:00'))

            # Calculate total days
            total_days = (end_date - start_date).days + 1
            videos_per_date = max(1, len(videos) // total_days)

            current_date = start_date
            video_index = 0

            for video in videos:
                if video_index < len(videos):
                    # Calculate schedule time for this video
                    schedule_datetime = current_date.replace(
                        hour=int(schedule_time.split(':')[0]),
                        minute=int(schedule_time.split(':')[1]),
                        second=0,
                        microsecond=0
                    )

                    video['schedule_time'] = schedule_datetime.isoformat()

                    # Move to next date after videos_per_day videos
                    if (video_index + 1) % videos_per_day == 0:
                        current_date += timedelta(days=1)
                        if current_date > end_date:
                            current_date = end_date

                    video_index += 1

        uploader = FacebookUploader()
        results = []
        for video in videos:
            try:
                asyncio.run(uploader.upload_video(
                    video_path=video['path'],
                    title=video.get('title', 'Generated Video'),
                    description=video.get('description', 'Auto-generated video'),
                    schedule_time=video.get('schedule_time')
                ))
                results.append({"video": video['path'], "status": "success"})
            except Exception as e:
                results.append({"video": video['path'], "status": "error", "error": str(e)})

        return jsonify({
            "status": "success",
            "message": "Bulk upload completed",
            "data": results
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500



@app.route("/api/settings", methods=["GET"])
def get_global_settings():
    global_settings = get_settings()
    return jsonify(
        {
        "status": "success",
        "message": "System settings retrieved successfully!",
        "data": global_settings
        }
    )

@app.route("/api/settings", methods=["POST"])
def update_global_settings():
    try:
        data = request.get_json()
        setting_type = data.get("type", "FONT")  # Default to FONT settings
        new_settings = data.get("settings", {})

        if not new_settings:
            return jsonify({
                "status": "error",
                "message": "No settings provided",
            }), 400

        # Update the settings
        update_settings(new_settings, setting_type)

        return jsonify({
            "status": "success",
            "message": f"{setting_type} settings updated successfully",
            "data": get_settings()
        })

    except Exception as e:
        print(colored(f"[-] Error updating settings: {str(e)}", "red"))
        return jsonify({
            "status": "error",
            "message": f"Could not update settings: {str(e)}",
        }), 500

@app.route("/api/generation-status", methods=["GET"])
def get_generation_status():
    global PROGRESS
    generation_status["progress"] = PROGRESS
    return jsonify({
        "status": "success",
        "data": generation_status
    })

if __name__ == "__main__":

    # Run Flask App
    app.run(debug=True, host=HOST, port=PORT)
