/** UIUX_BRIEF S3 design tokens */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0E1116', surface: '#161B22', surface2: '#1E252E', border: '#2A323D',
        text: '#E6EDF3', dim: '#9AA7B4',
        ok: '#3FB950', warn: '#D29922', danger: '#F85149', info: '#58A6FF', grad: '#A371F7',
      },
      fontFamily: { mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'] },
      borderRadius: { DEFAULT: '8px' },
    },
  },
  plugins: [],
}
