import os
from utils import *

from settings import *
from gpt import *
from search import *
from termcolor import colored
from flask import jsonify,json
from video import *
from tiktokvoice import *
from uuid import uuid4
from apiclient.errors import HttpError
from moviepy.config import change_settings

class Shorts:
    """
    Class for creating VideoShorts.

    Steps to create a Video Short:
    1. Generate a script [DONE]
    2. Generate metadata (Title, Description, Tags) [DONE]
    3. Get subtitles [DONE]
    4. Get Videos related to the search term [DONE]
    5. Convert Text-to-Speech [DONE]
    6. Combine Videos [DONE]
    7. Combine Videos with the Text-to-Speech [DONE]
    7. Combine Videos with the Text-to-Speech [DONE]
    """
    def __init__(self,video_subject: str, paragraph_number: int, ai_model: str,customPrompt: str="", extra_prompt: str = ""):
        """
        Constructor for YouTube Class.

        Args:
            video_subject (str): The subject of the video.
            paragraph_number (int): The number of paragraphs to generate.
            ai_model (str): The AI model to use for generation.
            customPrompt (str): The custom prompt to use for generation.
            extra_prompt (str): The extra prompt to use for generation.

        Returns:
            None
        """
        global GENERATING
        GENERATING = True


        change_settings({"IMAGEMAGICK_BINARY": os.getenv("IMAGEMAGICK_BINARY")})


        self.video_subject = video_subject
        self.paragraph_number = paragraph_number
        self.ai_model = ai_model
        self.customPrompt = customPrompt
        self.extra_prompt = extra_prompt
        self.globalSettings = get_settings()


        # Generate a script
        self.final_script = ""
        self.search_terms = []
        self.AMOUNT_OF_STOCK_VIDEOS= 5

        # Video from pexels
        self.video_urls = []
        self.video_paths = []
        self.videos_quantity_search = 15
        self.min_duration_search = 5
        # Voice related variables
        self.voice = "en_us_001"
        self.voice_prefix = self.voice[:2]

        # Audio and subtitles
        self.tts_path = None
        self.subtitles_path = None

        # Final video
        self.final_video_path = None

        # Video metadata
        self.video_title = None
        self.video_description = None
        self.video_tags = None

        # Subtitle
        self.subtitles_position=""
        self.final_music_video_path=""

    @property
    def get_final_video_path(self):
        return self.final_video_path
    @property
    def get_final_music_video_path(self):
        return self.final_music_video_path

    @property
    def get_final_script(self):
        return self.final_script
    
    @property
    def get_tts_path(self):
        return self.tts_path

    @property
    def get_subtitles_path(self):
        return self.subtitles_path

    @property
    def get_video_paths(self):
        return self.video_paths

    def GenerateScript(self):
        """
        Generate a script for a video, depending on the subject of the video, the number of paragraphs, and the AI model.

        Args:
            video_subject (str): The subject of the video.
            paragraph_number (int): The number of paragraphs to generate.
            ai_model (str): The AI model to use for generation.
        Returns:

            str: The script for the video.
        """
        
        if self.customPrompt and self.customPrompt != "":
            prompt = self.customPrompt
        else:
            prompt = self.globalSettings["scriptSettings"]["defaultPromptStart"]

        prompt += f"""
        # Initialization:
        - video subject: {self.video_subject}
        - number of paragraphs: {self.paragraph_number}
        {self.extra_prompt}
        
        """
        # Add the global prompt end
        prompt += self.globalSettings["scriptSettings"]["defaultPromptEnd"]

        # Generate script
        response = generate_response(prompt, self.ai_model)

        print(colored(response, "cyan"))

        # Return the generated script
        if response:
            # Clean the script
            # Remove asterisks, hashes
            response = response.replace("*", "")
            response = response.replace("#", "")

            # Remove markdown syntax
            response = re.sub(r"\[.*\]", "", response)
            response = re.sub(r"\(.*\)", "", response)

            # Split the script into paragraphs
            paragraphs = response.split("\n\n")

            # Select the specified number of paragraphs
            selected_paragraphs = paragraphs[:self.paragraph_number]

            # Join the selected paragraphs into a single string
            final_script = "\n\n".join(selected_paragraphs)

            # Print to console the number of paragraphs used
            print(colored(f"Number of paragraphs used: {len(selected_paragraphs)}", "green"))

            self.final_script = final_script

            return final_script
        else:
            print(colored("[-] GPT returned an empty response.", "red"))
            return None

    def GenerateSearchTerms(self):
        self.search_terms = get_search_terms(self.video_subject, self.AMOUNT_OF_STOCK_VIDEOS, self.final_script, self.ai_model)

        return self.search_terms

    #Download the videos base on the search terms from pexel api
    def DownloadVideos(self):
        global GENERATING
        # Search for videos
        for search_term in self.search_terms:
            global GENERATING
            if not GENERATING:
                return jsonify(
                    {
                        "status": "error",
                        "message": "Video generation was cancelled.",
                        "data": [],
                    }
                )
            found_urls = search_for_stock_videos(
                search_term, os.getenv("PEXELS_API_KEY"), self.videos_quantity_search, self.min_duration_search
            )
            # Check for duplicates
            for url in found_urls:
                if url not in self.video_urls:
                    self.video_urls.append(url)
                    break

        # Check if video_urls is empty
        if not self.video_urls:
            print(colored("[-] No videos found to download.", "red"))
            return jsonify(
                {
                    "status": "error",
                    "message": "No videos found to download.",
                    "data": [],
                }
            )
        
        # Download the videos
        video_paths = []
        # Let user know
        print(colored(f"[+] Downloading {len(self.video_urls)} videos...", "blue"))
        # Save the videos
        for video_url in self.video_urls:
            if not GENERATING:
                return jsonify(
                    {
                        "status": "error",
                        "message": "Video generation was cancelled.",
                        "data": [],
                    }
                )
            try:
                saved_video_path = save_video(video_url)
                video_paths.append(saved_video_path)
            except Exception:
                print(colored(f"[-] Could not download video: {video_url}", "red"))

        # Let user know
        print(colored("[+] Videos downloaded!", "green"))
        self.video_paths = video_paths


    def GenerateMetadata(self):
        self.video_title, self.video_description, self.video_tags = generate_metadata(self.video_subject, self.final_script, self.ai_model)

        # Write the metadata in a json file with the video title as the filename
        self.WriteMetadataToFile(self.video_title, self.video_description, self.video_tags)
        
    def GenerateVoice(self,voice):
        print(colored(f"[X] Generating voice: {voice} ", "green"))
        global GENERATING
        self.voice = voice
        self.voice_prefix = self.voice[:2]

        # Split script into sentences
        sentences = self.final_script.split(". ")

        # Remove empty strings
        sentences = list(filter(lambda x: x != "", sentences))
        paths = []

        # Generate TTS for every sentence
        for sentence in sentences:
            if not GENERATING:
                return jsonify(
                    {
                        "status": "error",
                        "message": "Video generation was cancelled.",
                        "data": [],
                    }
                )
            fileId = uuid4()
            current_tts_path = f"../static/assets/temp/{fileId}.mp3"
            tts(sentence, self.voice, filename=current_tts_path)

            # Add the audio clip to the list
            print(colored(f"[X] Save Audio ", "green"))
            audio_clip = AudioFileClip(f"../static/assets/temp/{fileId}.mp3")
            paths.append(audio_clip)

        # Combine all TTS files using moviepy

        print(colored(f"[X] Start saving the audio ", "green"))
        final_audio = concatenate_audioclips(paths)
        self.tts_path = f"../static/assets/temp/{uuid4()}.mp3"
        final_audio.write_audiofile(self.tts_path)

        # Generate the subtitles
        try:
            self.subtitles_path = generate_subtitles(audio_path=self.tts_path, sentences=sentences, audio_clips=paths, voice=self.voice_prefix)
        except Exception as e:
            print(colored(f"[-] Error generating subtitles: {e}", "red"))
            self.subtitles_path = None

    def CombineVideos(self):
        temp_audio = AudioFileClip(self.tts_path)
        n_threads = 2
        combined_video_path = combine_videos(self.video_paths, temp_audio.duration, 10, n_threads or 2)

        print(colored(f"[-] Next step: {combined_video_path}", "green"))
        # Put everything together
        try:
            self.final_video_path = generate_video(combined_video_path, self.tts_path, self.subtitles_path, n_threads or 2, self.subtitles_position)
        except Exception as e:
            print(colored(f"[-] Error generating final video: {e}", "red"))
            self.final_video_path = None

    def WriteMetadataToFile(video_title, video_description, video_tags):
            metadata = {
                "title": video_title,
                "description": video_description,
                "tags": video_tags
            }
            # Remplace spaces with underscores
            fileName = video_title.replace(" ", "_")

            with open(f"../../static/assets/temp/{fileName}.json", "w") as file:
                json.dump(metadata, file) 

    def AddMusic(self, use_music,custom_song_path=""):
        video_clip = VideoFileClip(f"../{self.final_video_path}")

        self.final_music_video_path = f"{uuid4()}-music.mp4"
        n_threads = 2
        if use_music:
            # if no song path choose random song
            song_path = f"../static/assets/music/{custom_song_path}"
            if not custom_song_path:
                song_path = choose_random_song()
            

            # Add song to video at 30% volume using moviepy
            original_duration = video_clip.duration
            original_audio = video_clip.audio
            song_clip = AudioFileClip(song_path).set_fps(44100)

            # Set the volume of the song to 10% of the original volume
            song_clip = song_clip.volumex(0.1).set_fps(44100)

            # Add the song to the video
            comp_audio = CompositeAudioClip([original_audio, song_clip])
            video_clip = video_clip.set_audio(comp_audio)
            video_clip = video_clip.set_fps(30)
            video_clip = video_clip.set_duration(original_duration)

            video_clip.write_videofile(f"../static/generated_videos/{self.final_music_video_path}", threads=n_threads or 1)
        else:
            video_clip.write_videofile(f"../static/generated_videos/{self.final_music_video_path}", threads=n_threads or 1)

    def Stop(self):
        global GENERATING
        # Stop FFMPEG processes
        if os.name == "nt":
            # Windows
            os.system("taskkill /f /im ffmpeg.exe")
        else:
            # Other OS
            os.system("pkill -f ffmpeg")

        GENERATING = False