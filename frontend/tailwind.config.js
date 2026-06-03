/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          orange:  "#ff5c35",
          purple:  "#2a1653",
          pink:    "#b6507b",
          dark:    "#0d0d1a",
          lime:    "#c0d850",
          cyan:    "#1aacd2",
          yellow:  "#fdbb36",
          gray:    "#616175",
          lgray:   "#c0c0c8",
          offwhite:"#f2f2f2",
        },
      },
      fontFamily: {
        sans: ["Renault Group", "Inter", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #ff5c35 0%, #b6507b 50%, #2a1653 100%)",
        "brand-gradient-h": "linear-gradient(90deg, #ff5c35 0%, #b6507b 50%, #2a1653 100%)",
        "sidebar-bg": "linear-gradient(180deg, #2a1653 0%, #1a0d33 100%)",
      },
      boxShadow: {
        "brand": "0 4px 24px rgba(255, 92, 53, 0.18)",
        "card":  "0 2px 16px rgba(42, 22, 83, 0.10)",
      },
    },
  },
  plugins: [],
};
