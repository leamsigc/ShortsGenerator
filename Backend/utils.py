import os
import sys
import json
import random
import logging
import zipfile
import requests

from termcolor import colored
from settings import STATIC_DIR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_dir(path: str) -> None:
    """
    Removes every file in a directory.

    Args:
        path (str): Path to directory.

    Returns:
        None
    """
    try:
        # Ensure the path is absolute
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(__file__), path)

        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.info(f"Created directory: {path}")

        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            os.remove(file_path)
            logger.info(f"Removed file: {file_path}")

        logger.info(colored(f"Cleaned {path} directory", "green"))
    except Exception as e:
        logger.error(f"Error occurred while cleaning directory {path}: {str(e)}")

def fetch_songs(zip_url: str) -> None:
    """
    Downloads songs into songs/ directory to use with geneated videos.

    Args:
        zip_url (str): The URL to the zip file containing the songs.

    Returns:
        None
    """
    try:
        logger.info(colored(f" => Fetching songs...", "magenta"))

        files_dir = os.path.join(STATIC_DIR, "assets", "music")
        if not os.path.exists(files_dir):
            os.makedirs(files_dir)
            logger.info(colored(f"Created directory: {files_dir}", "green"))
        else:
            # Skip if songs are already downloaded
            return

        # Download songs
        response = requests.get(zip_url)

        # Save the zip file
        with open(os.path.join(files_dir, "songs.zip"), "wb") as file:
            file.write(response.content)

        # Unzip the file
        with zipfile.ZipFile(os.path.join(files_dir, "songs.zip"), "r") as file:
            file.extractall(files_dir)

        # Remove the zip file
        os.remove(os.path.join(files_dir, "songs.zip"))

        logger.info(colored(f" => Downloaded Songs to {os.path.join(STATIC_DIR, 'assets/music')}.", "green"))

    except Exception as e:
        logger.error(colored(f"Error occurred while fetching songs: {str(e)}", "red"))

def get_random_song() -> str:
    """
    Chooses a random song from the songs/ directory.

    Returns:
        str: The path to the chosen song.
    """
    try:
        music_dir = os.path.join(STATIC_DIR, "assets", "music")
        songs = os.listdir(music_dir)
        if not songs:
            raise ValueError("No songs found in music directory")
        song = random.choice(songs)
        logger.info(colored(f"Chose song: {song}", "green"))
        return os.path.join(music_dir, song)
    except Exception as e:
        logger.error(colored(f"Error occurred while choosing random song: {str(e)}", "red"))
        return ""


def check_env_vars() -> None:
    """
    Checks if the necessary environment variables are set.

    Returns:
        None

    Raises:
        SystemExit: If any required environment variables are missing.
    """
    try:
        required_vars = ["PEXELS_API_KEY", "IMAGEMAGICK_BINARY"]
        missing_vars = []
        for var in required_vars:
            value = os.getenv(var)
            if value is None or len(value) == 0:
                missing_vars.append(var)  

        if missing_vars:
            missing_vars_str = ", ".join(missing_vars)
            logger.error(colored(f"The following environment variables are missing: {missing_vars_str}", "red"))
            logger.error(colored("Please consult 'EnvironmentVariables.md' for instructions on how to set them.", "yellow"))
            sys.exit(1)  # Aborts the program
    except Exception as e:
        logger.error(f"Error occurred while checking environment variables: {str(e)}")
        sys.exit(1)  # Aborts the program if an unexpected error occurs
