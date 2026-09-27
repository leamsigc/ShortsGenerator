import requests

from typing import List
from termcolor import colored

def search_for_stock_videos(query: str, api_key: str, it: int, min_dur: int) -> List[str]:
    """
    Searches for stock videos based on a query.

    Args:
        query (str): The query to search for.
        api_key (str): The API key to use.

    Returns:
        List[str]: A list of stock videos.
    """
    
    # Build headers
    headers = {
        "Authorization": api_key
    }

    # Build URL
    from urllib.parse import quote
    qurl = f"https://api.pexels.com/videos/search?query={quote(query)}&per_page={it}"

    # Send the request
    try:
        r = requests.get(qurl, headers=headers, timeout=30)
    except Exception as e:
        print(colored(f"[-] Pexels request failed: {e}", "red"))
        return []

    # log response
    print(colored(f"Response: {r.status_code}", "green"))

    if r.status_code != 200:
        print(colored(f"[-] Pexels API error {r.status_code}: {r.text[:200]}", "red"))
        return []

    # Parse the response
    try:
        response = r.json()
    except Exception as e:
        print(colored(f"[-] Pexels response is not valid JSON: {e}", "red"))
        return []

    # Parse each video
    raw_urls = []
    video_url = []
    video_res = 0
    try:
        videos = response.get("videos", [])
        for video_data in videos:
            # check if video has desired minimum duration
            if video_data.get("duration", 0) < min_dur:
                continue
            raw_urls = video_data.get("video_files", [])

            temp_video_url = ""
            video_res = 0

            # loop through each url to determine the best quality
            for video in raw_urls:
                # Check if video has a valid download link
                if ".com" in video.get("link", ""):
                    # Only save the URL with the largest resolution
                    if (video.get("width", 0) * video.get("height", 0)) > video_res:
                        temp_video_url = video["link"]
                        video_res = video.get("width", 0) * video.get("height", 0)

            # add the url to the return list if it's not empty
            if temp_video_url != "":
                video_url.append(temp_video_url)

    except Exception as e:
        print(colored("[-] No Videos found.", "red"))
        print(colored(e, "red"))

    # Let user know
    print(colored(f"\t=> \"{query}\" found {len(video_url)} Videos", "cyan"))

    # Return the video url
    return video_url
