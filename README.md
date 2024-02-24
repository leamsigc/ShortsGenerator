## ShortsGenerator
![ShortGenerator](/logo.jpeg)

Automate the creation of YouTube Shorts locally with a couple simple steps.

1.Give a video subject
    1. Add extra prompt information if needed
2.Review the script
    3.Add custom search keywords
    2.Select specific voice to use or set a global default voice for all generations
3.Generate the video
4.Review the video - Regenerate video
5.Add music to the video
6.View all generated videos

7. ***Profit***


## Overview

> **🎥** Watch the video on 
![YouTube](https://youtu.be/s7wZ7OxjMxA). or click in the image.
[![Short Generator](/logo.jpeg)](https://youtu.be/s7wZ7OxjMxA "Short generator, video generator")



![Generate](/static/assets/images/Screen1.png)
![Generate 2](/static/assets/images/Screenshot2.png?raw=true)
![Generate 3](/static/assets/images/Screenshot3.png?raw=true)
- [x] Generate the script first
- [x] Let user review the script before the audio and video generation
- [x] Let the user view all the generated video in a single place
- [x] Let user view the generated video in the browser
- [x] Let user select the audio music to add to the video

- [ ] Update the view to have a better user experience
- [x] Let user preview the generate video in the same view and let user iterated on the video
- [ ] Let user download the generated video
- [ ] Let user upload videos to be use in the video it self
- [ ] Let user upload audio to be use in the video it self
- [x] Let user have general configuration
- [ ] Let add multiple video link to download
- [ ] Let user select the font and upload font
- [x] Let user select the color for the text

### Features 🚀 planes: 
- [ ] Let user schedule the video upload to [youtube,facebook bussines,linkedin]
- [ ] Let user create video from the calendar and schedule it to be uploaded


## Installation 📥

1. Clone the repository

```bash
git clone https://github.com/leamsigc/ShortsGenerator.git
cd ShortsGenerator
 Copy the `.env.example` file to `.env` and fill in the required values
```
2. Please install docker if you haven't already done so

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

Add your fonts to the `static/assets/fonts` and schange the font name in the global settigns.


## Nuxt Development FE:

Before runing the front end create the fallowing folders

1. `static`
2. `static/generated_videos` -> All videos generated that have music will be here
3. `static/Songs` -> Put the mp4 songs that you want to use here

Start the front end:
1. `cd UI`
2. `npm install`
3. `npm run dev`

Alternative front end will be in port 3000

The frontend depend in the backend.
You can run the docker container or you run the backend locally


## Donate 🎁

If you like and enjoy `ShortsGenerator`, and would like to donate, you can do that by clicking on the button on the right hand side of the repository. ❤️
You will have your name (and/or logo) added to this repository as a supporter as a sign of appreciation.

## Contributing 🤝

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Star History 🌟

[![Star History Chart](https://api.star-history.com/svg?repos=leamsigc/ShortsGenerator&type=Date)](https://star-history.com/#leamsigc/ShortsGenerator&Date)

## License 📝

See [`LICENSE`](LICENSE) file for more information.
