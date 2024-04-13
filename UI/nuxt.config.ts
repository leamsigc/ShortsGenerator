// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  ssr: false,
  devtools: { enabled: true },
  modules: [
    "@bg-dev/nuxt-naiveui",
    "@vueuse/nuxt",
    "@nuxtjs/tailwindcss",
    "@nuxt/content",
    "nuxt-icon",
    "@pinia/nuxt",
    "@unocss/nuxt",
    "@nuxtjs/i18n",
    "nuxt-lodash",
  ],
  css: ["~/assets/scss/main.scss"],
  tailwindcss: {
    exposeConfig: {
      write: true,
    },
  },
  content: {
    markdown: {
      anchorLinks: false,
    },
  },
  i18n: {
    locales: [
      {
        code: "en",
        file: "en-US.json",
      },
    ],
    lazy: true,
    langDir: "locales",
    defaultLocale: "en",
  },
  runtimeConfig: {
    public: {
      pexelsApiKey: process.env.PEXELS_API_KEY,
    },
  },
});
