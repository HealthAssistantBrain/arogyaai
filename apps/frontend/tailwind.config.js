/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "rgb(var(--color-background) / <alpha-value>)",
                card: "rgb(var(--color-card) / <alpha-value>)",
                surface: "rgb(var(--color-surface) / <alpha-value>)",
                'surface-muted': "rgb(var(--color-surface-muted) / <alpha-value>)",
                stroke: "rgb(var(--color-stroke) / <alpha-value>)",
                primary: "#0A4DA1",
                landingPrimary: "#6043F4",
                accent: "#009CDE",
                navyCustom: "#13082A",
                backgroundLight: "#f8fafc",
                backgroundDark: "#0a0416",
                danger: "#FF4B26",
                success: "#00C48C",
                sleep: {
                    deep: "#4B6BF5",
                    light: "#FFB800",
                    rem: "#00C48C",
                    awake: "#FF4B26"
                },
                text: {
                    primary: "rgb(var(--color-text-primary) / <alpha-value>)",
                    secondary: "rgb(var(--color-text-secondary) / <alpha-value>)",
                    muted: "rgb(var(--color-text-muted) / <alpha-value>)"
                },
                warning: "#F6AD55",
                brandDanger: "#E53E3E"
            },
            borderRadius: {
                'card': '20px',
            },
            boxShadow: {
                'card': '0 2px 16px rgba(0,0,0,0.06)',
                'card-hover': '0 8px 28px rgba(0,0,0,0.12)',
            },
            fontFamily: {
                sans: ['"Inter"', '"DM Sans"', 'sans-serif'],
                display: ['"Plus Jakarta Sans"', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
