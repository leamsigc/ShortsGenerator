import re
import json
import g4f
# from openai import OpenAI
from typing import Tuple, List  
from termcolor import colored
from dotenv import load_dotenv
import os
import google.generativeai as genai

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv("../.env")

# Set environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# openai.api_key = OPENAI_API_KEY
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# openaiClient = OpenAI(
#     api_key=OPENAI_API_KEY ,  # This is the default and can be omitted
# )

# Configure g4f
g4f.debug.logging = True  # Enable debug logging
g4f.debug.version_check = False  # Disable automatic version checking

def generate_response(prompt: str, ai_model: str) -> str:
    """
    Generate a script for a video, depending on the subject of the video.

    Args:
        video_subject (str): The subject of the video.
        ai_model (str): The AI model to use for generation.

    Returns:
        str: The response from the AI model.
    """

    if ai_model == 'g4f':
        client = g4f.Client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=False
            # Add any other necessary parameters
        )
        return response if isinstance(response, str) else str(response.choices[0].message.content)

    # elif ai_model in ["gpt3.5-turbo", "gpt4"]:
        
    #     model_name = "gpt-3.5-turbo" if ai_model == "gpt3.5-turbo" else "gpt-4-1106-preview"
    #     response = openaiClient.chat.completions.create(
    #         model=model_name,
    #         messages=[{"role": "user", "content": prompt}],
    #     ).choices[0].message.content

    elif ai_model == 'gemmini':
        model = genai.GenerativeModel('gemini-pro')
        response_model = model.generate_content(prompt)
        response = response_model.text

    else:
        raise ValueError("Invalid AI model selected.")

    return response



def get_search_terms(video_subject: str, amount: int, script: str, ai_model: str) -> List[str]:
    """
    Generate a JSON-Array of search terms for stock videos,
    depending on the subject of a video.

    Args:
        video_subject (str): The subject of the video.
        amount (int): The amount of search terms to generate.
        script (str): The script of the video.
        ai_model (str): The AI model to use for generation.

    Returns:
        List[str]: The search terms for the video subject.
    """

    # Build prompt
    prompt = f"""
    # Elite Viral Search Terms Generator
    Generate {amount} precision search terms for stock videos that capture the video's viral essence and visual narrative.

    ## Optimization Matrix:
    1. **Emotional Core**: Terms matching script's psychological triggers and viral moments
    2. **Visual Precision**: High-converting terms that deliver cinematic, engaging footage
    3. **Trending Integration**: Current popular search patterns and visual styles
    4. **Platform Mastery**: Optimized for Pexels, Shutterstock, Pixabay premium results

    ## Technical Specs:
    - Return JSON array of strings only
    - 2-4 words per term for exact visual matching
    - Core emotional/action keywords from script required
    - Visual storytelling focus over generic topics
    - English terms exclusively

    ## Output Format:
    ["dramatic slow motion", "emotional reaction", "surprised expression", "intense concentration", "viral moment"]

    ## Video Context:
    Subject: {video_subject}
    Script: {script}

    Generate terms that unlock the most compelling, shareable visual content for maximum viral impact.
    """.strip()


    # Let user know
    print(colored(f"Generating {amount} search terms for {video_subject}...", "cyan"))

    # Generate search terms
    response = generate_response(prompt, ai_model)

    # Let user know
    print(colored(f"Response: {response}", "cyan"))
    # Parse response into a list of search terms
    search_terms = []
    
    try:
        search_terms = json.loads(response)
        if not isinstance(search_terms, list) or not all(isinstance(term, str) for term in search_terms):
            raise ValueError("Response is not a list of strings.")

    except (json.JSONDecodeError, ValueError):
        print(colored("[*] GPT returned an unformatted response. Attempting to clean...", "yellow"))

        # Attempt to extract list-like string and convert to list
        match = re.search(r'\["(?:[^"\\]|\\.)*"(?:,\s*"[^"\\]*")*\]', response)
        if match:
            try:
                search_terms = json.loads(match.group())
            except json.JSONDecodeError:
                print(colored("[-] Could not parse response.", "red"))
                return []



    # Let user know
    print(colored(f"\nGenerated {len(search_terms)} search terms: {', '.join(search_terms)}", "cyan"))

    # Return search terms
    return search_terms


def generate_metadata(video_subject: str, script: str, ai_model: str) -> Tuple[str, str, List[str], str]:
    """
    Generate metadata for a YouTube video, including the title, description, and keywords.

    Args:
        video_subject (str): The subject of the video.
        script (str): The script of the video.
        ai_model (str): The AI model to use for generation.

    Returns:
        Tuple[str, str, List[str]]: The title, description, and keywords for the video.
    """

    # Build prompt for title
    title_prompt = f"""
    Generate an elite viral title for a mobile social media short video about {video_subject}.

    ## Elite Title Engineering:
    - **Length**: 45-65 characters for perfect mobile display
    - **Nuclear Power Words**: "SHOCKING TRUTH", "FORBIDDEN SECRET", "UNBELIEVABLE FACT", "MIND-BLOWING REVELATION", "LIFE-CHANGING DISCOVERY"
    - **SEO Domination**: Primary keyword + emotional triggers + trending elements
    - **Psychological Triggers**: Fear, curiosity, outrage, excitement, urgency, FOMO
    - **Mobile Supremacy**: Fits notification previews, loads instantly, demands clicks
    - **Viral Formats**: "X Things That...", "You Won't Believe...", "The Truth About...", "They Don't Want You To Know..."
    - **Algorithm Hack**: Optimized for TikTok, Instagram, YouTube Shorts discovery

    ## Advanced Mobile Optimization:
    - Numbers and lists = 300% higher engagement
    - Question format = 250% more curiosity clicks
    - Emojis for visual pop (max 2, strategic placement)
    - ALL CAPS for power words that demand attention
    - Universal appeal that transcends demographics

    Return ONLY the title, no quotes or extra text.
    """

    # Generate title
    title = generate_response(title_prompt, ai_model).strip()

    # Build prompt for description
    description_prompt = f"""
    Craft an elite viral description for a mobile social media short video about {video_subject}.

    ## Elite Description Engineering:
    - **Nuclear Hook**: First 8 words must freeze the scroll
    - **SEO Domination**: 4-6 keywords woven naturally with emotional triggers
    - **Conversion CTA**: Irresistible calls-to-action that drive massive engagement
    - **Social Proof Weapons**: Credibility builders that establish authority
    - **Engagement Hijackers**: Questions and curiosity gaps that demand interaction
    - **Mobile Supremacy**: Scannable format, short paragraphs, instant readability
    - **Hashtag Arsenal**: 4-6 trending, relevant hashtags for algorithmic boost
    - **Length**: 120-160 characters for perfect mobile display and SEO

    ## Advanced Viral Elements:
    - Open with psychological trigger question or shocking revelation
    - Deploy emotional warfare (amazing, terrifying, life-changing, mind-blowing)
    - Create exclusivity and urgency ("Before it's too late", "Limited time access")
    - End with engagement command that overrides free will
    - Make it so shareable it spreads like digital wildfire

    ## Video Context:
    {script}

    Return ONLY the description text, no quotes or formatting.
    """

    # Generate description
    description = generate_response(description_prompt, ai_model).strip()

    # Generate keywords
    keywords = get_search_terms(video_subject, 6, script, ai_model)

    # Format for easy copy-paste
    formatted_output = f"""TITLE: {title}

DESCRIPTION: {description}

TAGS: {', '.join(keywords)}"""

    return title, description, keywords, formatted_output  
