/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: 'rgb(var(--color-background) / <alpha-value>)',
        text: 'rgb(var(--color-text) / <alpha-value>)',
        muted: 'rgb(var(--color-muted) / <alpha-value>)',
        border: 'rgb(var(--color-border) / <alpha-value>)',
        primary: 'rgb(var(--color-primary) / <alpha-value>)',
        danger: 'rgb(var(--color-danger) / <alpha-value>)',
      },
      boxShadow: {
        soft: 'var(--shadow-soft)',
        panel: 'var(--shadow-panel)',
        button: 'var(--shadow-button)',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      backgroundImage: {
        'primary-gradient': 'var(--gradient-primary)',
        'panel-tint': 'var(--gradient-panel-tint)',
      },
    },
  },
  plugins: [],
};
