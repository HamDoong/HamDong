/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#F8FAFC',
        text: '#0F172A',
        muted: '#64748B',
        border: '#E2E8F0',
        primary: '#00A86B',
        danger: '#EF233C',
      },
      boxShadow: {
        soft: '0 14px 36px rgba(15, 23, 42, 0.05)',
        panel: '0 10px 28px rgba(15, 23, 42, 0.04)',
        button: '0 14px 32px rgba(0, 168, 107, 0.24)',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      backgroundImage: {
        'primary-gradient': 'linear-gradient(90deg, #00915F 0%, #00A86B 100%)',
        'panel-tint': 'linear-gradient(180deg, #FFFFFF 0%, #FBFEFD 100%)',
      },
    },
  },
  plugins: [],
};
