import os
import os
import multiprocessing
import psutil
import threading
from typing import Optional
from datetime import datetime
from utils import *

from settings import *
from gpt import *
from search import *
from termcolor import colored
from flask import jsonify,json
from video import *
from voice import *
from uuid import uuid4
from main import PROGRESS
from apiclient.errors import HttpError
from moviepy.config import change_settings
from moviepy.editor import *
from moviepy.video.fx.all import crop
from moviepy.video.tools.subtitles import SubtitlesClip


class ResourceManager:
    """Manages system resources to prevent system freeze during video processing"""

    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.memory_gb = psutil.virtual_memory().total / (1024**3)
        self.max_memory_usage = 0.7  # Use max 70% of available memory
        self.min_free_memory_gb = 1.0  # Keep at least 1GB free

    def get_optimal_threads(self, requested_threads=None):
        """Calculate optimal number of threads based on system resources"""
        if requested_threads and requested_threads > 0:
            # Respect user request but cap it
            optimal = min(requested_threads, self.cpu_count)
        else:
            # Auto-calculate based on system
            optimal = max(1, self.cpu_count - 2)  # Leave 2 cores for system

        # Further reduce if memory is low
        available_memory = psutil.virtual_memory().available / (1024**3)
        if available_memory < self.min_free_memory_gb * 2:
            optimal = max(1, optimal // 2)  # Use half the threads if memory is low

        return optimal

    def check_memory_usage(self):
        """Check current memory usage and return if it's safe to continue"""
        memory = psutil.virtual_memory()
        memory_usage_percent = memory.percent / 100.0

        if memory_usage_percent > self.max_memory_usage:
            print(colored(f"[!] High memory usage detected: {memory_usage_percent:.1%}", "yellow"))
            return False

        available_gb = memory.available / (1024**3)
        if available_gb < self.min_free_memory_gb:
            print(colored(f"[!] Low memory available: {available_gb:.1f}GB", "yellow"))
            return False

        return True

    def get_cpu_usage(self):
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=1)

    def should_throttle(self):
        """Check if processing should be throttled due to high resource usage"""
        cpu_usage = self.get_cpu_usage()
        memory_ok = self.check_memory_usage()

        if cpu_usage > 80:
            print(colored(f"[!] High CPU usage detected: {cpu_usage:.1f}%", "yellow"))
            return True

        if not memory_ok:
            return True

        return False

    def cleanup_resources(self):
        """Clean up resources and force garbage collection"""
        import gc
        gc.collect()

        # Try to free up memory by clearing caches if available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
from video import ASPECT_RATIOS

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
    def __init__(self,video_subject: str, paragraph_number: int, ai_model: str,customPrompt: str="", extra_prompt: str = "", threads: Optional[int] = None):
        """
        Constructor for YouTube Class.

        Args:
            video_subject (str): The subject of the video.
            paragraph_number (int): The number of paragraphs to generate.
            ai_model (str): The AI model to use for generation.
            customPrompt (str): The custom prompt to use for generation.
            extra_prompt (str): The extra prompt to use for generation.
            threads (int): Number of threads to use for video processing. If None, uses CPU count.

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

        # Initialize resource manager
        self.resource_manager = ResourceManager()

        # Set threads based on resource manager recommendations
        if threads is None or threads <= 0:
            self.threads = self.resource_manager.get_optimal_threads()
        else:
            self.threads = self.resource_manager.get_optimal_threads(threads)

        print(colored(f"[+] Using {self.threads} threads for video processing", "green"))


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

        # Personalization settings
        self.aspect_ratio = "9:16"
        self.custom_text_settings = {}

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
    def DownloadVideos(self, selectedVideoUrls):
        global GENERATING

        # Search for videos
        # Check if the selectedVideoUrls is empty
        if selectedVideoUrls and len(selectedVideoUrls) > 0:
            print(colored(f"Selected videos: {selectedVideoUrls}", "green"))
            # filter the selectedVideoUrls is a Array of objects with videoUrl object that has a link key with a value we use the value of the link key
            self.video_urls = [video_url["videoUrl"]["link"] for video_url in selectedVideoUrls]
            # log the selectedVideoUrls
            print(colored(f"Selected video urls: {self.video_urls}", "green"))
        else:
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
                api_key = os.getenv("PEXELS_API_KEY")
                if not api_key:
                    print(colored("[-] PEXELS_API_KEY not set", "red"))
                    continue
                found_urls = search_for_stock_videos(
                    search_term, api_key, self.videos_quantity_search, self.min_duration_search
                )
                # check if found_urls is empty
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
                print(colored(f"[+] Saved video: {saved_video_path}", "green"))
                video_paths.append(saved_video_path)
            except Exception:
                print(colored(f"[-] Could not download video: {video_url}", "red"))

        # Let user know
        print(colored("[+] Videos downloaded!", "green"))
        self.video_paths = video_paths
        # print the video_paths
        print(colored(f"Video paths: {self.video_paths}", "green"))


    def GenerateMetadata(self):
        self.video_title, self.video_description, self.video_tags, self.formatted_metadata = generate_metadata(self.video_subject, self.final_script, self.ai_model)

        # Write the metadata in a json file with the video title as the filename
        self.WriteMetadataToFile(self.video_title, self.video_description, self.video_tags)

        # Create comprehensive JSON metadata file
        self.CreateVideoMetadataJSON()
        
    def GenerateVoice(self, voice, custom_tts_audio_path=None):
        print(colored(f"[X] Generating voice: {voice} ", "green"))
        global GENERATING
        self.voice = voice
        self.voice_prefix = self.voice[:2] if voice else "en"

        # If custom audio is provided, use it directly
        if custom_tts_audio_path:
            print(colored(f"[X] Using custom TTS audio: {custom_tts_audio_path}", "green"))
            self.tts_path = custom_tts_audio_path

            # Generate basic subtitles from custom audio
            try:
                sentences = self.final_script.split(". ")
                sentences = list(filter(lambda x: x != "", sentences))
                self.subtitles_path = self._generate_basic_subtitles(sentences)
            except Exception as e:
                print(colored(f"[-] Error generating subtitles from custom audio: {e}", "red"))
                self.subtitles_path = None
            return

        # Generate TTS for the entire script in one shot
        if not GENERATING:
            return jsonify(
                {
                    "status": "error",
                    "message": "Video generation was cancelled.",
                    "data": [],
                }
            )

        fileId = uuid4()
        self.tts_path = os.path.join(STATIC_DIR, "assets/temp", f"{fileId}.wav")  # Changed to .wav
        tts(self.final_script, self.voice, filename=self.tts_path)

        # Verify TTS file was created
        if not self.tts_path or not os.path.exists(self.tts_path) or os.path.getsize(self.tts_path) == 0:
            print(colored(f"[-] TTS file was not created or is empty: {self.tts_path}", "red"))
            self.tts_path = None
            print(colored("[!] Continuing without voice - video will be silent", "yellow"))
            return

        print(colored(f"[+] TTS file created successfully: {self.tts_path} ({os.path.getsize(self.tts_path)} bytes)", "green"))

        # Split script into sentences for subtitles
        sentences = self.final_script.split(". ")
        sentences = list(filter(lambda x: x != "", sentences))

        # Generate the subtitles
        try:
            # For single-shot TTS, we need to create audio clips for each sentence timing
            audio_clip = AudioFileClip(self.tts_path)
            total_duration = audio_clip.duration
            num_sentences = len(sentences)
            time_per_sentence = total_duration / num_sentences if num_sentences > 0 else total_duration

            paths = []
            current_time = 0
            for i, sentence in enumerate(sentences):
                start_time = current_time
                end_time = min(current_time + time_per_sentence, total_duration)
                # Create a subclips for timing estimation
                sub_clip = audio_clip.subclip(start_time, end_time)
                paths.append(sub_clip)
                current_time = end_time

            self.subtitles_path = generate_subtitles(audio_path=self.tts_path, sentences=sentences, audio_clips=paths, voice=self.voice_prefix)
        except Exception as e:
            print(colored(f"[-] Error generating subtitles: {e}", "red"))
            self.subtitles_path = None

    def CombineVideos(self):
        temp_audio = AudioFileClip(self.tts_path)
        combined_video_path = combine_videos(self.video_paths, temp_audio.duration, 10, self.threads)

        print(colored(f"[-] Next step: {combined_video_path}", "green"))
        # Put everything together
        if self.tts_path and self.subtitles_path:
            try:
                self.final_video_path = generate_video(combined_video_path, self.tts_path, self.subtitles_path, self.threads, self.subtitles_position)
            except Exception as e:
                print(colored(f"[-] Error generating final video: {e}", "red"))
                self.final_video_path = None
        elif self.subtitles_path:
            # Generate video without audio if TTS failed
            print(colored("[!] Generating video without audio (TTS failed)", "yellow"))
            try:
                self.final_video_path = generate_video(combined_video_path, None, self.subtitles_path, self.threads, self.subtitles_position)
            except Exception as e:
                print(colored(f"[-] Error generating video without audio: {e}", "red"))
                self.final_video_path = None
        else:
            print(colored("[-] No TTS or subtitles available, cannot generate final video", "red"))
            self.final_video_path = None

    def GenerateVideoOptimized(self):
        """
        Optimized method that combines video combination, text overlay, and voice addition in one step
        """
        print(colored("[+] Starting optimized video generation...", "green"))
        global GENERATING

        if not GENERATING:
            return

        # Check initial resource availability
        if not self.resource_manager.check_memory_usage():
            print(colored("[!] Insufficient memory for video generation. Reducing thread count.", "yellow"))
            self.threads = max(1, self.threads // 2)

        # Set process priority to below normal to be less intrusive
        try:
            import os
            os.nice(10)  # Lower priority (higher nice value = lower priority)
        except:
            pass  # Windows doesn't have nice(), skip on Windows

        # Get audio duration for video length calculation
        temp_audio = AudioFileClip(self.tts_path)
        max_duration = temp_audio.duration

        # Combine videos in one step with text and audio
        video_id = uuid4()
        final_video_path = os.path.join(STATIC_DIR, "generated_videos", f"{video_id}.mp4")

        # Get settings and apply personalization
        settings = get_settings()
        font_settings = settings["fontSettings"]

        # Use custom aspect ratio if set, otherwise use default
        aspect_ratio = self.aspect_ratio if hasattr(self, 'aspect_ratio') and self.aspect_ratio else font_settings["aspect_ratio"]
        target_width, target_height = ASPECT_RATIOS.get(aspect_ratio, (1080, 1920))

        # Apply custom text settings if available
        if self.custom_text_settings:
            print(colored(f"[+] Applying custom text settings to font_settings", "cyan"))
            print(colored(f"[+] Before update - font_settings fontsize: {font_settings.get('fontsize')}", "cyan"))
            font_settings.update(self.custom_text_settings)
            print(colored(f"[+] After update - font_settings fontsize: {font_settings.get('fontsize')}", "cyan"))
            print(colored(f"[+] After update - font_settings color: {font_settings.get('color')}", "cyan"))

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
            size=(target_width - 2*font_settings.get("padding", 20), None),
            method='caption',
            align=font_settings.get("text_align", "center"),
            interline=font_settings.get("line_spacing", 1.5),
            kerning=0
        )

        # Split the subtitles position into horizontal and vertical
        horizontal_subtitles_position, vertical_subtitles_position = font_settings["subtitles_position"].split(",")

        # if subtitle position is not the same as the setting and is not empty we override
        if self.subtitles_position != font_settings["subtitles_position"] and self.subtitles_position != "":
            horizontal_subtitles_position, vertical_subtitles_position = self.subtitles_position.split(",")

        # Prepare video clips with resource monitoring
        clips = []
        tot_dur = 0
        processed_clips = 0

        while tot_dur < max_duration:
            # Check resources before processing each clip
            if processed_clips > 0 and processed_clips % 3 == 0:  # Check every 3 clips
                if self.resource_manager.should_throttle():
                    print(colored("[!] Throttling due to high resource usage. Taking a break...", "yellow"))
                    import time
                    time.sleep(2)  # Brief pause to let system recover

                    # Re-check thread count
                    optimal_threads = self.resource_manager.get_optimal_threads(self.threads)
                    if optimal_threads < self.threads:
                        print(colored(f"[!] Reducing threads from {self.threads} to {optimal_threads}", "yellow"))
                        self.threads = optimal_threads

                # Clean up resources periodically
                if processed_clips % 5 == 0:
                    self.resource_manager.cleanup_resources()

            for video_path in self.video_paths:
                clip = VideoFileClip(video_path)
                if clip is None:
                    continue

                clip = clip.without_audio()

                # Apply duration limits
                if (max_duration - tot_dur) < clip.duration:
                    clip = clip.subclip(0, (max_duration - tot_dur))
                elif 10 < clip.duration:  # max_clip_duration
                    clip = clip.subclip(0, 10)

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
                processed_clips += 1

        # Combine video clips
        combined_clip = concatenate_videoclips(clips)
        combined_clip = combined_clip.set_fps(30)

        # Add subtitles
        if self.subtitles_path:
            subtitles = SubtitlesClip(self.subtitles_path, generator)
            # Position the subtitles correctly
            try:
                positioned_subtitles = subtitles.set_position((horizontal_subtitles_position, vertical_subtitles_position))
            except AttributeError:
                # Fallback for different MoviePy versions
                positioned_subtitles = subtitles
            combined_clip = CompositeVideoClip([
                combined_clip,
                positioned_subtitles
            ])

        # Add audio
        combined_clip = combined_clip.set_audio(temp_audio)

        # Write final video with resource monitoring
        print(colored(f"[+] Writing final video with {self.threads} threads...", "green"))

        # Final resource check before writing
        if not self.resource_manager.check_memory_usage():
            print(colored("[!] Low memory before final write. Reducing threads.", "yellow"))
            self.threads = max(1, self.threads // 2)

        combined_clip.write_videofile(final_video_path, threads=self.threads)

        # Clean up resources after video generation
        self.resource_manager.cleanup_resources()

        # Remove the Backend directory from the video_name to return static/generated_videos/...
        backend_dir = os.path.dirname(STATIC_DIR) + os.sep
        self.final_video_path = final_video_path.replace(backend_dir, "")

        print(colored(f"[+] Optimized video generation completed: {self.final_video_path}", "green"))

    def WriteMetadataToFile(self, video_title, video_description, video_tags, other=None):
        # Create a metadata string
        metadata = (
            f"title: {video_title}\n"
            f"description: {video_description}\n"
            f"tags: {video_tags}\n"
            f"formatted_metadata: {self.formatted_metadata}\n"
            f"other: {other}\n"
        )

        # Define the directory to save files and ensure it exists
        output_dir = os.path.join(STATIC_DIR, "generated_videos")
        os.makedirs(output_dir, exist_ok=True)

        # Generate a unique filename using uuid4
        file_name = f"{uuid4()}.txt"
        file_path = os.path.join(output_dir, file_name)

        # Logging the operation using colored output
        print(colored("[X] Save Metadata", "green"))
        print(colored(f"Metadata: {metadata}", "green"))

        # Save metadata string to a text file
        with open(file_path, "w") as file:
            file.write(metadata)

        print(colored(f"Metadata saved to: {file_path}", "green"))

    def CreateVideoMetadataJSON(self):
        """Create a comprehensive JSON metadata file for the generated video"""

        # Prepare metadata dictionary
        video_metadata = {
            "path": self.final_video_path,
            "name": os.path.basename(self.final_video_path) if self.final_video_path else "",
            "title": self.video_title,
            "script": self.final_script,
            "type": "short_video",
            "metadata": {
                "title": self.video_title,
                "description": self.video_description,
                "tags": self.video_tags,
                "formatted_metadata": self.formatted_metadata
            },
            "created_at": datetime.now().isoformat(),
            "video_subject": self.video_subject,
            "ai_model": self.ai_model,
            "search_terms": self.search_terms
        }

        # Define the directory to save JSON files
        output_dir = os.path.join(STATIC_DIR, "generated_videos")
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename based on video name or UUID
        video_name = os.path.splitext(os.path.basename(self.final_video_path))[0] if self.final_video_path else str(uuid4())
        json_filename = f"{video_name}_metadata.json"
        json_path = os.path.join(output_dir, json_filename)

        # Save JSON metadata
        with open(json_path, "w", encoding="utf-8") as json_file:
            json.dump(video_metadata, json_file, indent=2, ensure_ascii=False)

        print(colored(f"JSON metadata saved to: {json_path}", "green"))


    def AddMusic(self, use_music,custom_song_path=""):
        video_clip = VideoFileClip(f"{self.final_video_path}")

        self.final_music_video_path = f"{uuid4()}-music.mp4"
        if use_music:
            # if no song path choose random song
            song_path = os.path.join(STATIC_DIR, "assets/music", custom_song_path)
            if not custom_song_path:
                song_path = get_random_song()


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

            PROGRESS = 50
            video_clip.write_videofile(os.path.join(STATIC_DIR, "generated_videos", self.final_music_video_path), threads=self.threads)
            PROGRESS = 100
        else:
            PROGRESS = 50
            video_clip.write_videofile(os.path.join(STATIC_DIR, "generated_videos", self.final_music_video_path), threads=self.threads)
            PROGRESS = 100

    def _generate_basic_subtitles(self, sentences):
        """Generate basic subtitles for custom audio based on script timing estimates"""
        from moviepy.editor import AudioFileClip

        # Load the audio to get duration
        audio_clip = AudioFileClip(self.tts_path)
        total_duration = audio_clip.duration

        # Estimate timing for each sentence
        num_sentences = len(sentences)
        if num_sentences == 0:
            return None

        # Simple equal distribution of time
        time_per_sentence = total_duration / num_sentences

        subtitles_content = ""
        current_time = 0

        for i, sentence in enumerate(sentences, 1):
            start_time = current_time
            end_time = min(current_time + time_per_sentence, total_duration)

            # Format timestamps
            start_timestamp = self._format_timestamp(start_time)
            end_timestamp = self._format_timestamp(end_time)

            subtitles_content += f"{i}\n{start_timestamp} --> {end_timestamp}\n{sentence.strip()}\n\n"

            current_time = end_time

        # Save subtitles file
        subtitles_path = os.path.join(STATIC_DIR, "assets/subtitles", f"{uuid4()}.srt")
        with open(subtitles_path, "w") as file:
            file.write(subtitles_content)

        return subtitles_path

    def _format_timestamp(self, seconds):
        """Format seconds into SRT timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return "02d"

    def apply_text_settings(self, text_settings):
        """
        Apply custom text settings for video generation
        """
        self.custom_text_settings = text_settings
        print(colored(f"[+] Applied custom text settings: {text_settings}", "green"))
        print(colored(f"[+] Custom settings keys: {list(text_settings.keys()) if text_settings else 'None'}", "cyan"))

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