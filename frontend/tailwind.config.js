/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
    "./src/types/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: {
          primary: "var(--color-bg-primary)",
          secondary: "var(--color-bg-secondary)",
          tertiary: "var(--color-bg-tertiary)"
        },
        border: {
          DEFAULT: "var(--color-border)",
          bright: "var(--color-border-bright)"
        },
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          muted: "var(--color-text-muted)"
        },
        accent: {
          DEFAULT: "var(--color-accent)",
          dim: "var(--color-accent-dim)",
          hover: "var(--color-accent-hover)"
        },
        position: {
          gk: "var(--color-pos-gk)",
          def: "var(--color-pos-def)",
          mid: "var(--color-pos-mid)",
          fwd: "var(--color-pos-fwd)"
        },
        status: {
          fresh: "var(--color-fresh)",
          stale: "var(--color-stale)",
          old: "var(--color-old)"
        },
        chart: {
          1: "var(--chart-1)",
          2: "var(--chart-2)",
          3: "var(--chart-3)",
          4: "var(--chart-4)",
          5: "var(--chart-5)"
        }
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
        mono: ["var(--font-mono)"]
      },
      borderRadius: {
        panel: "8px"
      },
      boxShadow: {
        panel: "0 16px 50px rgba(0, 0, 0, 0.22)"
      }
    }
  },
  plugins: []
};
