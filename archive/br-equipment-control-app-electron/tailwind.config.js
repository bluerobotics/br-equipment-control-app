/** @type {import('tailwindcss').Config} */
export default {
  // FIX: Added paths to your source files.
  // Tailwind will now scan these files for utility classes to include in the build.
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}", // <-- This line is crucial
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}