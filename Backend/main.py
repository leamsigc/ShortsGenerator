import os
from utils import *
from dotenv import load_dotenv

# Load environment variables
# check if .env is in the folder or look one more level up
if os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv("../.env")
# Check if all required environment variables are set
# This must happen before importing video which uses API keys without checking
check_env_vars()

from gpt import *
from video import *
from search import *
from classes.Shorts import *
from uuid import uuid4
from tiktokvoice import *
from flask_cors import CORS
from termcolor import colored
from youtube import upload_video
from apiclient.errors import HttpError
from flask import Flask, request, jsonify
from moviepy.config import change_settings
from classes.instagram_downloader import InstagramDownloader

# Set environment variables
SESSION_ID = os.getenv("TIKTOK_SESSION_ID")
openai_api_key = os.getenv('OPENAI_API_KEY')
change_settings({"IMAGEMAGICK_BINARY": os.getenv("IMAGEMAGICK_BINARY")})


# Initialize Flask
app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# Constants
HOST = "0.0.0.0"
PORT = 8080
AMOUNT_OF_STOCK_VIDEOS = 5
GENERATING = False

# Create a method to create all the required folders
def create_folders():
    """Create all required folders for the application"""
    folders = [
        "static",
        "static/assets",
        "static/assets/temp",
        "static/assets/subtitles",
        "static/generated_videos",
        "static/generated_videos/instagram",
    ]
    
    for folder in folders:
        folder_path = os.path.join(os.path.dirname(__file__), folder)
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
        downloader = InstagramDownloader(output_path=os.path.join(os.path.dirname(__file__), "static/generated_videos/instagram"))
        
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
        clean_dir("static/assets/temp/")
        clean_dir("static/assets/subtitles/")


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
        # Print little information about the video which is to be generated
        print(colored("[Video to be generated]", "blue"))
        print(colored("   Subject: " + data["videoSubject"], "blue"))
        print(colored("   AI Model: " + ai_model, "blue"))  # Print the AI model being used
        print(colored("   Custom Prompt: " + data["customPrompt"], "blue"))  # Print the AI model being used



        if not GENERATING:
            return jsonify(
                {
                    "status": "error",
                    "message": "Video generation was cancelled.",
                    "data": [],
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
            client_secrets_file = os.path.abspath("./client_secret.json")
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
                    'video_path': os.path.abspath(f"../temp/{final_video_path}"),
                    'title': title,
                    'description': description,
                    'category': video_category_id,
                    'keywords': ",".join(keywords),
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

    clean_dir("static/assets/subtitles/")
    print(colored("[+] Received script request...", "green"))

    data = request.get_json()
    video_subject = data["videoSubject"]
    extra_prompt = data["extraPrompt"]
    ai_model = data["aiModel"]

    videoClass = Shorts(video_subject, 1, ai_model, "",extra_prompt=extra_prompt)
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

# Download the videos and split the script
@app.route("/api/search-and-download", methods=["POST"])
def search_and_download():
    # Set generating to true
    global GENERATING
    GENERATING = True 
     # Clean
    clean_dir("static/assets/temp")
    clean_dir("static/assets/subtitles")

    
    print(colored("[+] Received search and download request...", "green"))

    data = request.get_json()
    search_terms = data["search"]
    script = data["script"]
    ai_model = data["aiModel"]
    voice = data["voice"]
    selectedVideoUrls = data.get("selectedVideoUrls",[])

    # Extra options:
    custom_video = data.get("videoUrls",[])
    custom_voice = data.get("voiceUrl","")
    # Set the default subtitles_position to the center, bottom
    subtitles_position = data.get("subtitlesPosition", "center,bottom")
    n_threads = data.get('threads', 4) 

    if not voice:
        print(colored("[!] No voice was selected. Defaulting to \"en_us_001\"", "yellow"))
        voice = "en_us_001"
    # Search for a video of the given search term
    videoClass = Shorts("", 1, ai_model, '')
    videoClass.search_terms = search_terms
    videoClass.final_script = script
    videoClass.subtitles_position = subtitles_position

    videoClass.DownloadVideos(selectedVideoUrls)

    videoClass.GenerateVoice(voice)

    videoClass.CombineVideos()

    # videoClass.GenerateMetadata()
    videoClass.Stop()



    # FInal videoClass.get_final_video_path
    print(colored(f"[X] Next FInal video: {videoClass.get_final_video_path}", "green"))
    # if final video path is None return status code 500
    if videoClass.get_final_video_path is None:
        return jsonify(
            {
                "status": "error",
                "message": "Video generation was cancelled.",
                "data": [],
            }
        ),500
    
    return jsonify(
        {
            "status": "success",
            "message": "Search and download complete!",
            "data": {
                "finalAudio": videoClass.get_tts_path ,
                "subtitles": videoClass.get_subtitles_path,
                "finalVideo": videoClass.get_final_video_path
            }
        }
    )

# Add audio to the video
@app.route("/api/addAudio", methods=["POST"])
def addAudio():
    GENERATING = True
    data = request.get_json()
    final_video_path = data["finalVideo"]
    song_path = data["songPath"]
    ai_model = data["aiModel"]

    videoClass = Shorts("", 1, ai_model, '')
    videoClass.final_video_path = final_video_path

    videoClass.AddMusic(True,song_path)

    videoClass.Stop()
    return jsonify(
        {
            "status": "success",
            "message": "Search and download complete!",
            "data": {
                "finalVideo": "static/generated_videos/" + videoClass.get_final_music_video_path
            }
        }
    )


# Get all available songs
@app.route("/api/getSongs", methods=["GET"])
def get_songs():
    songs = os.listdir(os.path.join(os.path.dirname(__file__), "static/assets/music"))
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
    videos = os.listdir(os.path.join(os.path.dirname(__file__), "static/generated_videos"))
    videos = [video for video in videos if video.endswith(".mp4")]
    instagramVideos = os.listdir(os.path.join(os.path.dirname(__file__), "static/generated_videos/instagram"))
    instagramVideos = [video for video in instagramVideos if video.endswith(".mp4")]
    return jsonify(
        {
        "status": "success",
        "message": "Videos retrieved successfully!",
        "data": {
            "videos": videos,
            "instagram": instagramVideos
            }
        }
    )

# Get all available subtitles
@app.route("/api/getSubtitles", methods=["GET"])
def get_subtitles():
    subtitles = os.listdir(os.path.join(os.path.dirname(__file__), "static/assets/subtitles"))
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
    assets_path = os.path.join(os.path.dirname(__file__), "static/assets/temp")
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

if __name__ == "__main__":

    # Run Flask App
    app.run(debug=True, host=HOST, port=PORT)
