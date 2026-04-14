/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Legacy (mantener compat temporal)
        primary: '#3b82f6',
        success: '#10b981',
        danger: '#ef4444',
        warning: '#f59e0b',
        dark: '#1f2937',
        // TradingView (legacy)
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
        // Nueva paleta fintech light (Stripe/Mercury inspired)
        'fm-bg': '#fafafa',
        'fm-surface': '#ffffff',
        'fm-surface-2': '#f5f5f7',
        'fm-border': '#e5e5e7',
        'fm-border-strong': '#d2d2d7',
        'fm-text': '#1d1d1f',
        'fm-text-2': '#424245',
        'fm-text-dim': '#86868b',
        'fm-primary': '#635bff',
        'fm-primary-hover': '#5850ec',
        'fm-primary-soft': '#f0efff',
        'fm-success': '#00875a',
        'fm-success-soft': '#e4f5ed',
        'fm-danger': '#de1c00',
        'fm-danger-soft': '#fde8e5',
        'fm-warning': '#b85c00',
        'fm-warning-soft': '#fef3e4',
        'fm-accent': '#7a5af8',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        'fm-sm': '0 1px 2px rgba(17,24,39,0.04), 0 0 0 1px rgba(17,24,39,0.05)',
        'fm-md': '0 4px 12px rgba(17,24,39,0.06), 0 0 0 1px rgba(17,24,39,0.04)',
        'fm-lg': '0 12px 24px rgba(17,24,39,0.08), 0 0 0 1px rgba(17,24,39,0.04)',
        'fm-focus': '0 0 0 4px rgba(99,91,255,0.15)',
        'panel': '0 0 0 1px rgba(42,46,57,0.6)',
        'panel-hover': '0 0 0 1px rgba(41,98,255,0.3)',
      },
    },
  },
  plugins: [],
}
