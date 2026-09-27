import type { Config } from "tailwindcss";

export default <Partial<Config>>{
  darkMode: "class",
  plugins: [require("@tailwindcss/typography")],
  theme: {
    extend: {
      colors: {
        clipper: {
          green: "#00DC82",
          ink: "#0F172A",
          white: "#ffffff",
        },
      },
      fontFamily: {
        poppins: ["Poppins", "sans-serif"],
      },
      maxWidth: {
        clipper: "1440px",
      },
      borderRadius: {
        clipper: "8px",
      },
    },
  },
};
