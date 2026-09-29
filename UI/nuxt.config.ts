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
  app: {
    head: {
      // Poppins is the editor + caption font (canvas preview/export resolve
      // it through document fonts). Loaded via <link> — the old SCSS
      // @import sat after @use output, so browsers ignored it and the font
      // silently fell back to system sans-serif.
      link: [
        { rel: "preconnect", href: "https://fonts.googleapis.com" },
        { rel: "preconnect", href: "https://fonts.gstatic.com", crossorigin: "" },
        {
          rel: "stylesheet",
          href: "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap",
        },
      ],
    },
  },
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
  vite: {
    // @elah/core spawns its MP4 export worker via `new URL(...)` — module
    // workers require format 'es', and pre-bundling breaks the worker ref.
    worker: {
      format: "es",
    },
    optimizeDeps: {
      exclude: ["@elah/core", "mediabunny"],
    },
  },
});
