/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#070B14",
        panel: "#0E1628",
        cyan: "#2DE2E6",
        mint: "#93F9B9",
        indigo: "#6E7FF3"
      },
      boxShadow: {
        glass: "0 16px 44px rgba(0, 0, 0, 0.3)"
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};
