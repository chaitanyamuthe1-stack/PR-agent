/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#142B4A',
          dark: '#0E1F36',
          light: '#1C3B65',
          subtle: '#264B7D',
        },
        canvas: '#F3F5F8',
        'soft-blue': {
          DEFAULT: '#DCE7F5',
          hover: '#C8DBF0',
          dark: '#142B4A',
        },
        lavender: {
          DEFAULT: '#E9E2F5',
          dark: '#4A2E7A',
          border: '#D7C7ED',
        },
        mint: {
          DEFAULT: '#DDF2E5',
          dark: '#1B5E36',
          border: '#C4E7D0',
        },
        body: {
          DEFAULT: '#343A40',
          muted: '#606973',
        },
        border: {
          DEFAULT: '#E2E6EC',
          subtle: '#EAECEF',
        },
        ag: {
          navy: '#142B4A',
          'navy-dark': '#0E1F36',
          'navy-light': '#1C3B65',
          ivory: '#F3F5F8',
          white: '#FFFFFF',
          canvas: '#F3F5F8',
          sage: '#DCE7F5',
          'sage-dark': '#142B4A',
          'sage-darker': '#0E1F36',
          'sage-subtle': '#DCE7F5',
          'soft-blue': '#DCE7F5',
          beige: '#E2E6EC',
          'beige-dark': '#343A40',
          lavender: '#E9E2F5',
          'lavender-dark': '#4A2E7A',
          mint: '#DDF2E5',
          'mint-dark': '#1B5E36',
          text: '#343A40',
          'text-muted': '#606973',
          border: '#E2E6EC',
          'amber-bg': '#FEF3C7',
          'amber-border': '#FDE68A',
          'amber-text': '#92400E',
          'red-bg': '#FEE2E2',
          'red-border': '#FECACA',
          'red-text': '#991B1B'
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace']
      }
    },
  },
  plugins: [],
}


