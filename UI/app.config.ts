import { _fontFamily } from "#tailwind-config/theme.mjs";

export default defineAppConfig({
  naiveui: {
    themeConfig: {
      shared: {
        common: {
          fontFamily: "'Poppins', sans-serif",
        },
      },
      light: {
        common: {
          primaryColor: "#00DC82",
          primaryColorHover: "rgba(0,220,130,0.90)",
          primaryColorPressed: "#00b86b",
          borderRadius: "8px",
          textColorBase: "#0F172A",
          borderColor: "rgba(15,23,42,0.08)",
        },
      },
      dark: {
        common: {
          primaryColor: "#00DC82",
          primaryColorHover: "rgba(0,220,130,0.90)",
          primaryColorPressed: "#00b86b",
        },
      },
    },
  },
});
