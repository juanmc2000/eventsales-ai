import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "nav-bg": "#070A1F",
        "nav-bg-2": "#0B102B",
        "topbar-bg": "#080B24",
        "page-bg": "#F8F7FC",
        surface: "#FFFFFF",
        "surface-soft": "#FBFAFF",
        border: "#E7E3F2",
        "text-primary": "#151525",
        "text-secondary": "#6B6680",
        "text-muted": "#9A94AD",
        "brand-purple": "#6D3DF5",
        "brand-pink": "#ED3D96",
        "brand-orange": "#FF7A1A",
        "brand-teal": "#2CC7C9",
        "brand-gold": "#F5B84B",
        success: "#16A66A",
        warning: "#E99A1C",
        danger: "#E5484D",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "16px",
      },
      boxShadow: {
        card: "0 12px 32px rgba(22, 16, 64, 0.08)",
        hover: "0 18px 50px rgba(22, 16, 64, 0.14)",
      },
    },
  },
  plugins: [],
};

export default config;
