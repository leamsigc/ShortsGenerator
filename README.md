## ShortsGenerator
![ShortGenerator](/logo.jpeg)
### How to run locally 🚀 Docker is required
---

2. Clone the repository

```sh
git clone git@github.com:leamsigc/ShortsGenerator.git video Generator

```



3. Go to the folder:"

```sh
cd videoGenerator

```

4. Copy the `.env-example`  to `.env`
5. Update the Pexel API key if you want to use Video from Pexel
6. The TikTok key is not needed anymore
7. `docker compose up -d `
8. Go to 'http://localhost:5000/generate' to start generating videos
9. Click on the Setting  `...` to get images and videos to use in the video
---


Automate the creation of YouTube Shorts locally with a couple of simple steps.



1. Give a video subject
    1. Add extra prompt information if needed
2. Review the script
    1. Add custom search keywords
    2. Select a specific voice to use or set a global default voice for all generations
3. Generate the video
4. Review the video - Regenerate video
5. Add music to the video
6. View all generated videos

7. ***Profit!***

## Facebook Upload Setup

To use the Facebook upload feature, you need to configure your Firefox profile:

### 1. Find Your Firefox Profile Path

Run the helper script to find your Firefox profiles:

```bash
cd Backend
python find_firefox_profile.py
```

This will show you all available Firefox profiles on your system.

### 2. Configure Environment Variables

Add the following to your `.env` file:

```env
# Firefox profile path (use the path from step 1)
FIREFOX_PROFILE_PATH=/home/user/.mozilla/firefox/abc123.default-release

# Run Firefox in headless mode (optional, default: false)
FIREFOX_HEADLESS=false
```

### 3. First Time Setup

1. Make sure Firefox is installed and you've logged into Facebook at least once
2. Run the profile finder script to get the correct path
3. Add the path to your `.env` file
4. Restart the application

### 4. Usage

- Go to the Videos page
- Select videos to upload
- Click "Upload to Facebook" button
- The system will open Firefox and navigate to Facebook Creator Studio
- If not logged in, you'll need to log in manually the first time
- Subsequent uploads will use your saved session

## Overview

> **🎥** Watch the video on 
[YouTube](https://youtu.be/s7wZ7OxjMxA) or click on the image.
[![Short Generator](/logo.jpeg)](https://youtu.be/s7wZ7OxjMxA "Short generator, video generator")

![Generate](/static/assets/images/Screen1.png)
![Generate 2](/static/assets/images/Screenshot2.png?raw=true)
![Generate 3](/static/assets/images/Screenshot3.png?raw=true)
- [x] Generate the script first
- [x] Let users review the script before audio and video generation
- [x] Let users view all the generated videos in a single place
- [x] Let users view the generated video in the browser
- [x] Let users select the audio music to add to the video

- [ ] Update the view to have a better user experience
- [x] Let users preview the generated video in the same view and let users iterate on the video
- [ ] Let users download the generated video
- [ ] Let users upload videos to be used in video creation
- [ ] Let users upload audio to be used in video creation
- [x] Let users have general configuration
- [ ] Let users add multiple video links to download
- [ ] Let users select the font and upload fonts
- [x] Let users select the color for the text

### Features 🚀 plans: 
- [ ] Let users schedule video uploads to [YouTube, Facebook Business, LinkedIn]
- [ ] Let users create videos from the calendar and schedule them to be uploaded


## Installation 📥

1. Clone the repository

```bash
git clone https://github.com/leamsigc/ShortsGenerator.git
cd ShortsGenerator
Copy the `.env.example` file to `.env` and fill in the required values
```
2. Please install Docker if you haven't already done so

3. Build the containers:
```bash
docker-compose build
```

4. Run the containers:
```bash
docker-compose up -d
```
5. Open `http://localhost:5000` in your browser

See [`.env.example`](.env.example) for the required environment variables.

If you need help, open [EnvironmentVariables.md](EnvironmentVariables.md) for more information.



## Music 🎵

To use your own music, upload it to the `static/assets/music` folder.

## Fonts 🅰

Add your fonts to the `static/assets/fonts` and change the font name in the global settings.


## Next Development FE:

Before running the front end create the following folders:

1. `static`
2. `static/generated_videos` -> All videos generated that have music will be here
3. `static/Songs` -> Put the mp4 songs that you want to use here

Start the front end:
1. `cd UI`
2. `npm install`
3. `npm run dev`

The alternative front end will be on port 3000

The frontend depends on the backend.
You can run the Docker container or you can run the backend locally


## Donate 🎁

If you like and enjoy `ShortsGenerator`, and would like to donate, you can do that by clicking on the button on the right-hand side of the repository. ❤️
You will have your name (and/or logo) added to this repository as a supporter as a sign of appreciation.

## Contributing 🤝

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Star History 🌟

[![Star History Chart](https://api.star-history.com/svg?repos=leamsigc/ShortsGenerator&type=Date)](https://star-history.com/#leamsigc/ShortsGenerator&Date)

## License 📝

See [`LICENSE`](LICENSE) file for more information.
