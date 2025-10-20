import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Military-inspired color palette (using standard color format)
        gray: {
          950: '#0a0a0a', // military-black
          900: '#1a1a1a', // military-dark  
          800: '#2a2a2a', // military-gray
          50: '#f5f5f5',  // military-light
        },
        red: {
          600: '#AF1E2D', // habs-red
        },
        blue: {
          900: '#192168', // habs-blue
          500: '#3b82f6', // data-blue
        },
        green: {
          500: '#22c55e', // success
        },
        amber: {
          500: '#f59e0b', // warning
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Monaco', 'Consolas', 'monospace'],
        military: ['var(--font-jetbrains-mono)', 'Monaco', 'Consolas', 'Courier New', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'typing': 'typing 1.5s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        typing: {
          '0%, 60%': { opacity: '1' },
          '30%': { opacity: '0.5' },
        },
      },
    },
  },
  plugins: [],
}

export default config