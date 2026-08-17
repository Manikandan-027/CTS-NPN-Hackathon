/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        bg: {
          base: '#080B10',
          panel: '#0F1520',
          panel2: '#141B29',
          raised: '#1A2233',
        },
        border: {
          subtle: 'rgba(255,255,255,0.07)',
          DEFAULT: 'rgba(255,255,255,0.10)',
        },
        ink: {
          primary: '#E7EDF6',
          secondary: '#9BA8BC',
          muted: '#697386',
        },
        accent: {
          cyan: '#2DD9E8',
          blue: '#4C8DFF',
        },
        state: {
          success: '#38D98F',
          warning: '#F3B94E',
          danger: '#FA6A6A',
          qwen: '#B18CF5',
        },
      },
      boxShadow: {
        glass: '0 8px 32px rgba(0,0,0,0.45)',
        glow: '0 0 24px rgba(45,217,232,0.25)',
      },
      backgroundImage: {
        'grid-fade': 'radial-gradient(circle at 20% 0%, rgba(45,217,232,0.08), transparent 40%), radial-gradient(circle at 80% 20%, rgba(177,140,245,0.06), transparent 35%)',
      },
      keyframes: {
        pulseSoft: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.55 },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        pulseSoft: 'pulseSoft 2s ease-in-out infinite',
        shimmer: 'shimmer 2.5s linear infinite',
      },
    },
  },
  plugins: [],
}
