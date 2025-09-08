# author: GiorDior aka Giorgio
# date: 12.06.2023
# topic: Chatterbox-TTS
# version: 2.0
# credits: https://github.com/resemble-ai/chatterbox

# --- MODIFIED VERSION FOR CHATTERBOX --- #

import threading
import os
import torch

# Force CPU mode by disabling CUDA
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Set number of threads to half of available CPUs
num_cpus = os.cpu_count() or 1
torch.set_num_threads(num_cpus // 2)

# Patch torch.load to always use map_location='cpu' for CPU-only machines
original_load = torch.load
def patched_load(*args, **kwargs):
        # Always force CPU loading to avoid CUDA issues
        kwargs['map_location'] = 'cpu'
        return original_load(*args, **kwargs)
torch.load = patched_load

from typing import List, Optional
from termcolor import colored
from playsound import playsound
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
from chatterbox.mtl_tts import ChatterboxMultilingualTTS


# Supported languages in Chatterbox
LANGUAGES = [
    "ar",  # Arabic
    "da",  # Danish
    "de",  # German
    "el",  # Greek
    "en",  # English
    "es",  # Spanish
    "fi",  # Finnish
    "fr",  # French
    "he",  # Hebrew
    "hi",  # Hindi
    "it",  # Italian
    "ja",  # Japanese
    "ko",  # Korean
    "ms",  # Malay
    "nl",  # Dutch
    "no",  # Norwegian
    "pl",  # Polish
    "pt",  # Portuguese
    "ru",  # Russian
    "sv",  # Swedish
    "sw",  # Swahili
    "tr",  # Turkish
    "zh",  # Chinese
]

# Initialize models
english_model = None
multilingual_model = None
device = None
model_lock = threading.Lock()

def get_device():
    """Automatically detect the best available device"""
    global device
    if device is None:
        # Check if CUDA is available
        if torch.cuda.is_available():
            device = torch.device("cuda")
            print(colored(f"[+] Using device: {device}", "green"))
        else:
        # Force CPU usage to avoid CUDA issues
            device = torch.device("cpu")
            print(colored(f"[+] Using device: {device}", "green"))
    return device


def initialize_models():
    global english_model, multilingual_model
    with model_lock:
        if english_model is None or multilingual_model is None:
            dev = get_device()
            if english_model is None:
                english_model = ChatterboxTTS.from_pretrained(device=dev)
            if multilingual_model is None:
                multilingual_model = ChatterboxMultilingualTTS.from_pretrained(device=dev)


# Map old TikTok voice names to Chatterbox language codes
VOICE_TO_LANGUAGE = {
    # English voices
    "en_us_001": "en",
    "en_us_002": "en",
    "en_us_006": "en",
    "en_us_007": "en",
    "en_us_009": "en",
    "en_us_010": "en",
    "en_au_001": "en",
    "en_au_002": "en",
    "en_uk_001": "en",
    "en_uk_003": "en",
    # European voices
    "fr_001": "fr",
    "fr_002": "fr",
    "de_001": "de",
    "de_002": "de",
    "es_002": "es",
    "it_001": "it",
    "pt_001": "pt",
    "nl_001": "nl",
    "pl_001": "pl",
    "ru_001": "ru",
    "sv_001": "sv",
    "da_001": "da",
    "no_001": "no",
    "fi_001": "fi",
    "el_001": "el",
    # Asian voices
    "ja_001": "ja",
    "ja_003": "ja",
    "ja_005": "ja",
    "ja_006": "ja",
    "ko_002": "ko",
    "ko_003": "ko",
    "ko_004": "ko",
    "zh_001": "zh",
    "hi_001": "hi",
    "ar_001": "ar",
    "he_001": "he",
    "id_001": "id",
    "ms_001": "ms",
    "tr_001": "tr",
    "sw_001": "sw",
    # Default fallback
    "none": "en"
}

def map_voice_to_language(voice: str) -> str:
    """Map old TikTok voice names to Chatterbox language codes"""
    return VOICE_TO_LANGUAGE.get(voice, "en")

# in one conversion, the text can have a maximum length of 300 characters
TEXT_BYTE_LIMIT = 300


# create a list by splitting a string, every element has n chars
def split_string(string: str, chunk_size: int) -> List[str]:
    words = string.split()
    result = []
    current_chunk = ""
    for word in words:
        if (
            len(current_chunk) + len(word) + 1 <= chunk_size
        ):  # Check if adding the word exceeds the chunk size
            current_chunk += f" {word}"
        else:
            if current_chunk:  # Append the current chunk if not empty
                result.append(current_chunk.strip())
            current_chunk = word
    if current_chunk:  # Append the last chunk if not empty
        result.append(current_chunk.strip())
    return result


# saving the audio file using torchaudio
def save_audio_file(wav, sr, filename: str = "output.wav") -> None:
    # Ensure the filename has the correct extension
    if not filename.endswith('.wav'):
        filename = filename.replace('.mp3', '.wav')
    ta.save(filename, wav, sr)


# generate audio using Chatterbox
def generate_audio(text: str, language: str = "en", audio_prompt_path: Optional[str] = None) -> tuple:
    initialize_models()

    if language == "en":
        if english_model is None:
            raise Exception("English TTS model failed to initialize")
        model = english_model
        if audio_prompt_path:
            wav = model.generate(text, audio_prompt_path=audio_prompt_path)
        else:
            wav = model.generate(text)
    else:
        if multilingual_model is None:
            raise Exception("Multilingual TTS model failed to initialize")
        model = multilingual_model
        if audio_prompt_path:
            wav = model.generate(text, language_id=language, audio_prompt_path=audio_prompt_path)
        else:
            wav = model.generate(text, language_id=language)

    return wav, model.sr


# creates an text to speech audio file
def tts(
    text: str,
    voice: str = "en_us_001",
    filename: str = "output.wav",
    play_sound: bool = False,
    audio_prompt_path: Optional[str] = None,
) -> None:
    # Map voice to language if it's an old TikTok voice name
    language = map_voice_to_language(voice)

    # checking if arguments are valid
    if not text:
        print(colored("[-] Please specify a text", "red"))
        return

    # creating the audio file
    try:
        if len(text) < TEXT_BYTE_LIMIT:
            print(colored(f"[+] Generating TTS for short text: {len(text)} chars", "blue"))
            wav, sr = generate_audio(text, language, audio_prompt_path)
            save_audio_file(wav, sr, filename)

        else:
            # Split longer text into smaller parts
            text_parts = split_string(text, 299)
            print(colored(f"[+] Generating TTS for long text: {len(text_parts)} parts", "blue"))
            audio_parts = []

            # Define a thread function to generate audio for each text part
            def generate_audio_thread(text_part, index):
                try:
                    wav, sr = generate_audio(text_part, language, audio_prompt_path)
                    audio_parts.append((wav, sr))
                    print(colored(f"[+] Generated audio part {index + 1}/{len(text_parts)}", "green"))
                except Exception as e:
                    print(colored(f"[-] Error generating audio part {index + 1}: {e}", "red"))

            threads = []
            for index, text_part in enumerate(text_parts):
                # Create and start a new thread for each text part
                thread = threading.Thread(
                    target=generate_audio_thread, args=(text_part, index)
                )
                thread.start()
                threads.append(thread)

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Concatenate audio parts
            if audio_parts:
                print(colored(f"[+] Concatenating {len(audio_parts)} audio parts", "blue"))
                wavs = [part[0] for part in audio_parts]
                sr = audio_parts[0][1]

                # Handle variable length tensors by padding shorter ones
                max_length = max(wav.shape[1] for wav in wavs)
                padded_wavs = []

                for wav in wavs:
                    if wav.shape[1] < max_length:
                        # Pad with zeros to match max length
                        padding_size = max_length - wav.shape[1]
                        padding = torch.zeros((wav.shape[0], padding_size))
                        padded_wav = torch.cat([wav, padding], dim=1)
                        padded_wavs.append(padded_wav)
                    else:
                        padded_wavs.append(wav)

                # Concatenate the padded tensors
                combined_wav = torch.cat(padded_wavs, dim=1)
                save_audio_file(combined_wav, sr, filename)
            else:
                raise Exception("No audio parts were generated successfully")

        # Verify file was created
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            print(colored(f"[+] Audio file saved successfully as '{filename}' ({os.path.getsize(filename)} bytes)", "green"))
            if play_sound:
                playsound(filename)
        else:
            raise Exception(f"Audio file was not created or is empty: {filename}")

    except Exception as e:
        print(colored(f"[-] An error occurred during TTS: {e}", "red"))
        # Clean up any partial file
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass


# Return the available voices
def available_voices() -> list:
    return list(VOICE_TO_LANGUAGE.keys())