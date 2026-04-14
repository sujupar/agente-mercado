/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta legacy (mantener compat)
        primary: '#3b82f6',
        success: '#10b981',
        danger: '#ef4444',
        warning: '#f59e0b',
        dark: '#1f2937',
        // Paleta TradingView
        'tv-bg': '#0b0e11',
        'tv-panel': '#131722',
        'tv-panel-2': '#1e222d',
        'tv-border': '#2a2e39',
        'tv-text': '#d1d4dc',
        'tv-text-dim': '#787b86',
        'tv-up': '#26a69a',
        'tv-down': '#ef5350',
        'tv-blue': '#2962ff',
        'tv-accent': '#f0b90b',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        'panel': '0 0 0 1px rgba(42,46,57,0.6)',
        'panel-hover': '0 0 0 1px rgba(41,98,255,0.3)',
      },
    },
  },
  plugins: [],
}
