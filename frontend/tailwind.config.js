/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7cc8fc',
          400: '#36abf8',
          500: '#0c8fe9',
          600: '#0171c7',
          700: '#025aa1',
          800: '#064c84',
          900: '#0b406e',
          950: '#072949',
        },
        doca: {
          navy:    '#020917',
          surface: '#080f1e',
          card:    '#0d1628',
          gold:    '#d97706',
          emerald: '#059669',
          crimson: '#dc2626',
        }
      },
      fontFamily: {
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'Inter', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glass':     '0 8px 32px 0 rgba(0, 0, 0, 0.3)',
        'glow':      '0 0 30px -5px rgba(12, 143, 233, 0.4)',
        'glow-lg':   '0 0 60px -10px rgba(12, 143, 233, 0.5)',
        'glow-rose': '0 0 30px -5px rgba(239, 68, 68, 0.4)',
        'glow-emerald': '0 0 30px -5px rgba(16, 185, 129, 0.4)',
        'modal':     '0 25px 80px rgba(0,0,0,0.6), 0 0 60px rgba(14,165,233,0.06)',
        'card':      '0 4px 24px rgba(0,0,0,0.4)',
        'premium':   '0 0 0 1px rgba(255,255,255,0.06), 0 8px 32px rgba(0,0,0,0.4)',
      },
      backgroundImage: {
        'gradient-brand':   'linear-gradient(135deg, #0171c7, #4f46e5)',
        'gradient-surface': 'linear-gradient(180deg, #080f1e 0%, #020917 100%)',
        'gradient-card':    'linear-gradient(135deg, rgba(14,165,233,0.08), rgba(99,102,241,0.05))',
        'noise':            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%' height='100%' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")",
      },
      animation: {
        'fade-in':    'fadeIn 0.4s ease-out both',
        'slide-up':   'slideInUp 0.4s ease-out both',
        'slide-right':'slideInRight 0.35s ease-out both',
        'float':      'float 4s ease-in-out infinite',
        'shimmer':    'shimmer 2.5s linear infinite',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
        'border-glow':'borderGlow 2s ease-in-out infinite',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
        '4xl': '1.5rem',
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
        '26': '6.5rem',
      }
    },
  },
  plugins: [],
}
