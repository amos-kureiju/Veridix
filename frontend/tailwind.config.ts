import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                vizora: {
                    dark: "#0b2520",
                    surface: "#12332c",
                    canvas: "#f1f5f5",
                    emerald: "#10b981",
                },
            },
        },
    },
    plugins: [],
};

export default config;