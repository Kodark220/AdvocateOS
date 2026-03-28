/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Syne', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        void: '#0a0a0a',
        core: '#111111',
        surface: '#1a1a1a',
        edge: '#2a2a2a',
        muted: '#555555',
        ghost: '#999999',
        wire: '#cccccc',
        signal: '#f5f5f5',
        acid: '#e8ff00',
        burn: '#ff4444',
        pulse: '#00e5ff',
        valid: '#00ff88',
        warn: '#ffaa00',
      },
      borderRadius: {
        sm: '2px',
      },
    },
  },
  plugins: [],
}
