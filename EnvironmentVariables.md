# Environment Variables

## Required

- TIKTOK_SESSION_ID: Your TikTok session ID is required. Obtain it by logging into TikTok in your browser and copying the value of the `sessionid` cookie.

- IMAGEMAGICK_BINARY: The filepath to the ImageMagick binary (.exe file) is needed. Obtain it [here](https://imagemagick.org/script/download.php).

- PEXELS_API_KEY: Your unique Pexels API key is required. Obtain yours [here](https://www.pexels.com/api/).

## Optional

- OPENAI_API_KEY: Your unique OpenAI API key is required. Obtain yours [here](https://platform.openai.com/api-keys), only nessecary if you want to use the OpenAI models.

- GOOGLE_API_KEY: Your Gemini API key is essential for Gemini Pro Model. Generate one securely at [Get API key | Google AI Studio](https://makersuite.google.com/app/apikey)

* ASSEMBLY_AI_API_KEY: Your unique AssemblyAI API key is required. You can obtain one [here](https://www.assemblyai.com/app/). This field is optional; if left empty, the subtitle will be created based on the generated script. Subtitles can also be created locally.

- FIREFOX_PROFILE_PATH: Path to your Firefox profile directory. If not set, the application will try to find the default Firefox profile automatically. Example: `/home/user/.mozilla/firefox/abc123.default-release`

- FIREFOX_HEADLESS: Set to "true" to run Firefox in headless mode (no visible browser window). Default is "false".

- FIREFOX_CHANNEL: Firefox channel to use. Options: "firefox" (stable), "firefox-beta", "firefox-nightly". Default is "firefox" (stable).

Join the [Discord](https://dsc.gg/fuji-community) for support and updates.
