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
    # Buffer time in seconds after voice audio ends
    VIDEO_END_BUFFER = 3.0
    def __init__(self,video_subject: str, paragraph_number: int, ai_model: str,customPrompt: str="", extra_prompt: str = "", script_template: str = ""):
        """
        Constructor for YouTube Class.

        Args:
            video_subject (str): The subject of the video.
            paragraph_number (int): The number of paragraphs to generate.
            ai_model (str): The AI model to use for generation.
            customPrompt (str): The custom prompt to use for generation.
            extra_prompt (str): The extra prompt to use for generation.
            script_template (str): The script template to use.

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
        self.script_template = script_template
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
        self.subtitle_template = "classic"
        self.aspect_ratio = "9:16"
        self.custom_subtitle = ""
        self.final_music_video_path=""
        self.image_paths = []
        self.image_duration = 5.0
        self.image_durations = []
        self.clip_duration = self.globalSettings.get("clipDurationSettings", {}).get("default", 10)

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
            templates = self.globalSettings.get("scriptTemplates", {}).get("options", [])
            selected = next((t for t in templates if t["value"] == self.script_template), None)
            if selected and selected.get("promptStart"):
                prompt = selected["promptStart"]
            else:
                prompt = self.globalSettings["scriptSettings"]["defaultPromptStart"]

        prompt += f"""
        # Initialization:
        - video subject: {self.video_subject}
        {self.extra_prompt}
        
        """
        # Add the global prompt end
        prompt_end = self.globalSettings["scriptSettings"]["defaultPromptEnd"] or ""
        prompt += prompt_end

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

            self.final_script = response

            return response
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
                found_urls = search_for_stock_videos(
                    search_term, os.getenv("PEXELS_API_KEY"), self.videos_quantity_search, self.min_duration_search
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

        # Optional: rerank candidate clips with TwelveLabs Pegasus so the most
        # relevant ones download first. No-op unless TWELVELABS_API_KEY is set.
        from twelvelabs_select import rerank_clips
        self.video_urls = rerank_clips(self.video_urls, self.video_subject, self.final_script)

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
                # Construct the absolute path to the static/assets/temp directory
                temp_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "assets", "temp"))
                saved_video_path = save_video(video_url, directory=temp_dir_path)
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
        self.video_title, self.video_description, self.video_tags, self.video_post_content = generate_metadata(self.video_subject, self.final_script, self.ai_model)

        # Compute a suggested schedule (next weekday at 12:00 UTC)
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        next_day = now + timedelta(days=1)
        if next_day.weekday() == 5:
            next_day += timedelta(days=2)
        elif next_day.weekday() == 6:
            next_day += timedelta(days=1)
        self.suggested_schedule = next_day.replace(hour=12, minute=0, second=0, microsecond=0).isoformat()

        # Write the metadata in a json file with the video title as the filename
        self.WriteMetadataToFile(self.video_title, self.video_description, self.video_tags, self.video_post_content, self.suggested_schedule)
        
    def GenerateVoice(self, voice, custom_audio_path="", audio_start_time=0, audio_end_time=0, quality=None, speed=None):
        print(colored(f"[X] Generating voice: {voice} ", "green"))
        global GENERATING
        self.voice = voice
        self.voice_prefix = voice[:2]

        if self.custom_subtitle and self.custom_subtitle.strip():
            sentences = [s.strip() for s in self.custom_subtitle.split(". ") if s.strip()]
        else:
            sentences = self.final_script.split(". ")
            sentences = list(filter(lambda x: x != "", sentences))

        temp_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "assets", "temp"))
        paths = []
        self.tts_path = None
        sentence_durations = None

        # Custom audio path — skip TTS, use uploaded audio
        if custom_audio_path:
            abs_custom_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', custom_audio_path))
            if not os.path.exists(abs_custom_path):
                abs_custom_path = custom_audio_path
            custom_audio_path = abs_custom_path
        if custom_audio_path and os.path.exists(custom_audio_path):
            print(colored(f"[+] Using custom audio: {custom_audio_path}", "green"))
            try:
                audio_clip = AudioFileClip(custom_audio_path)
                dur = float(audio_clip.duration)
                audio_start = float(audio_start_time) if audio_start_time > 0 else 0
                audio_end = float(audio_end_time) if audio_end_time > 0 else dur
                if audio_end > dur:
                    audio_end = dur
                if audio_end > audio_start:
                    audio_clip = audio_clip.subclip(audio_start, audio_end)
                trimmed_path = os.path.join(temp_dir_path, f"{uuid4()}.mp3")
                audio_clip.write_audiofile(trimmed_path)
                audio_clip.close()
                self.tts_path = trimmed_path
                paths = [AudioFileClip(self.tts_path)]
                print(colored(f"[+] Custom audio trimmed to {audio_start}-{audio_end}s", "green"))
            except Exception as e:
                print(colored(f"[-] Error processing custom audio: {e}", "red"))
                self.tts_path = None

        if not paths:
            engine = get_tts_engine()

            if engine == "supertonic":
                if not GENERATING:
                    return jsonify({"status": "error", "message": "Video generation was cancelled.", "data": []})

                tts_settings = get_tts_settings()
                fileId = uuid4()
                supertonic_path = os.path.join(temp_dir_path, f"{fileId}.mp3")

                result = tts_with_fallback(
                    self.final_script,
                    self.voice,
                    filename=supertonic_path,
                    lang=tts_settings.get("tts_lang", "en"),
                    quality=quality if quality is not None else tts_settings.get("tts_quality", 8),
                    speed=speed if speed is not None else tts_settings.get("tts_speed", 1.05),
                )

                if result["success"] and os.path.exists(supertonic_path):
                    audio_clip = AudioFileClip(supertonic_path)
                    paths = [audio_clip]
                    self.tts_path = supertonic_path
                    print(colored(f"[+] Supertonic generated full audio ({len(sentences)} sentences in one call)", "green"))
                else:
                    print(colored("[-] Supertonic failed, using TikTok sentence-by-sentence fallback", "yellow"))

            # Fallback: TikTok sentence-by-sentence
            if not paths:
                tiktok_voice = "en_us_001"
                sentence_durations = []
                print(colored(f"[*] Using TikTok TTS sentence-by-sentence (voice: {tiktok_voice})", "yellow"))
                for sentence in sentences:
                    if not GENERATING:
                        return jsonify({"status": "error", "message": "Video generation was cancelled.", "data": []})
                    fileId = uuid4()
                    current_tts_path = os.path.join(temp_dir_path, f"{fileId}.mp3")
                    tts_with_fallback(sentence, tiktok_voice, filename=current_tts_path)
                    if os.path.exists(current_tts_path):
                        try:
                            audio_clip = AudioFileClip(current_tts_path)
                            sentence_durations.append(float(audio_clip.duration))
                            paths.append(audio_clip)
                        except Exception as e:
                            print(colored(f"[-] Failed to load audio clip: {e}", "red"))
                            sentence_durations.append(0.0)

                if paths:
                    print(colored(f"[X] Combining {len(paths)} sentence audio files", "green"))
                    final_audio = concatenate_audioclips(paths)
                    self.tts_path = os.path.join(temp_dir_path, f"{uuid4()}.mp3")
                    final_audio.write_audiofile(self.tts_path)
                else:
                    print(colored("[-] No audio clips generated", "red"))

        # Generate subtitles
        if paths and self.tts_path and os.path.exists(self.tts_path):
            try:
                self.subtitles_path = generate_subtitles(audio_path=self.tts_path, sentences=sentences, voice=self.voice_prefix, sentence_durations=sentence_durations)
            except Exception as e:
                print(colored(f"[-] Error generating subtitles: {e}", "red"))
                self.subtitles_path = None
        else:
            print(colored("[-] No audio generated for subtitles", "red"))
            self.subtitles_path = None

    def CombineVideos(self):
        temp_audio = AudioFileClip(self.tts_path)
        n_threads = 2
        aspect_ratio = getattr(self, "aspect_ratio", "9:16") or "9:16"
        subtitle_template = getattr(self, "subtitle_template", "classic") or "classic"

        clip_duration = getattr(self, "clip_duration", 10)

        combined_video_path = combine_videos(
            self.video_paths,
            temp_audio.duration,
            clip_duration,
            n_threads or 2,
            aspect_ratio=aspect_ratio,
            image_paths=self.image_paths if hasattr(self, 'image_paths') else None,
            image_duration=self.image_duration if hasattr(self, 'image_duration') else 5.0,
            image_durations=self.image_durations if hasattr(self, 'image_durations') else None,
            buffer_time=self.VIDEO_END_BUFFER,
        )

        print(colored(f"[-] Next step: {combined_video_path}", "green"))
        # Put everything together
        try:
            self.final_video_path = generate_video(
                combined_video_path,
                self.tts_path,
                self.subtitles_path,
                n_threads or 2,
                self.subtitles_position,
                subtitle_template=subtitle_template,
                aspect_ratio=aspect_ratio,
                buffer_time=self.VIDEO_END_BUFFER,
            )
        except Exception as e:
            print(colored(f"[-] Error generating final video: {e}", "red"))
            self.final_video_path = None

    def WriteMetadataToFile(self, video_title, video_description, video_tags, video_post_content="", suggested_schedule=""):
        metadata = {
            "title": video_title,
            "description": video_description,
            "tags": video_tags,
            "post_content": video_post_content,
            "suggested_schedule": suggested_schedule
        }
        if self.final_video_path:
            basename = os.path.splitext(os.path.basename(self.final_video_path))[0]
        else:
            basename = video_title.replace(" ", "_")

        dest_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "generated_videos"))
        filepath = os.path.join(dest_dir, f"{basename}.json")
        with open(filepath, "w") as file:
            json.dump(metadata, file, indent=2) 

    def _copy_metadata_to(self, source_video_path: str, dest_video_path: str):
        dest_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "generated_videos"))
        source_basename = os.path.splitext(os.path.basename(source_video_path))[0]
        dest_basename = os.path.splitext(os.path.basename(dest_video_path))[0]
        source_meta = os.path.join(dest_dir, f"{source_basename}.json")
        dest_meta = os.path.join(dest_dir, f"{dest_basename}.json")
        if os.path.exists(source_meta):
            import shutil
            shutil.copy2(source_meta, dest_meta)
            print(colored(f"[+] Copied metadata to {dest_basename}.json", "green"))

    def AddMusic(self, use_music, custom_song_path="", music_source="library"):
        original_video_path = self.final_video_path
        dest_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "generated_videos"))
        output_filename = f"{uuid4()}-music.mp4"
        output_path = os.path.join(dest_dir, output_filename)

        if not use_music:
            import shutil
            shutil.copy2(original_video_path, output_path)
            self.final_music_video_path = output_filename
            if original_video_path:
                self._copy_metadata_to(original_video_path, output_path)
            return

        try:
            if music_source == "video" and custom_song_path and os.path.exists(custom_song_path):
                song_path = custom_song_path
            else:
                music_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "assets", "music"))
                if custom_song_path:
                    candidate = os.path.join(music_dir, custom_song_path)
                    song_path = candidate if os.path.exists(candidate) else choose_random_song()
                else:
                    song_path = choose_random_song()

            if ffmpeg_add_music_to_video(original_video_path, song_path, output_path, volume=0.1):
                self.final_music_video_path = output_filename
                if original_video_path:
                    self._copy_metadata_to(original_video_path, output_path)
                return

            print(colored("[*] Falling back to MoviePy for audio mix.", "yellow"))
            video_clip = VideoFileClip(original_video_path)
            original_duration = video_clip.duration
            original_audio = video_clip.audio

            song_clip = AudioFileClip(song_path).set_fps(44100)
            song_clip = song_clip.volumex(0.1).set_fps(44100)

            if song_clip.duration < original_duration:
                n_loops = int(original_duration / song_clip.duration) + 1
                song_clip = concatenate_audioclips([song_clip] * n_loops).set_duration(original_duration)

            comp_audio = CompositeAudioClip([original_audio, song_clip])
            video_clip = video_clip.set_audio(comp_audio)
            video_clip = video_clip.set_fps(30)
            video_clip = video_clip.set_duration(original_duration)

            video_clip.write_videofile(output_path, threads=2)

            if original_video_path:
                self._copy_metadata_to(original_video_path, output_path)

            try:
                video_clip.close()
            except Exception:
                pass
            try:
                song_clip.close()
            except Exception:
                pass

            self.final_music_video_path = output_filename
        except Exception as e:
            print(colored(f"[-] Error adding music: {e}", "red"))

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