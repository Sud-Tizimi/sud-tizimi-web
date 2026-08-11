import type { Config } from 'tailwindcss';

/**
 * Design system: "Justice Infrastructure"
 * Source: Stitch project 12139961574422030019 (Faysal AI Dashboard).
 * Tokens are intentionally fixed here — do not loosen.
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: '1rem',
        md: '2rem',
      },
    },
    extend: {
      colors: {
        // Brand
        primary: {
          50: '#E2DFFF',
          100: '#C3C0FF',
          200: '#9D98FF',
          300: '#7A72FF',
          400: '#5C50F0',
          500: '#4F46E5', // brand — primary-container in design system
          600: '#3525CD', // primary
          700: '#2A1FA8',
          800: '#1F1780',
          900: '#150F58',
        },
        navy: {
          DEFAULT: '#0F172A',
          50: '#EAF1FF',
          100: '#D3E4FE',
          200: '#A6BFE3',
          300: '#7897C2',
          400: '#4A6FA1',
          500: '#213145',
          600: '#172033',
          700: '#0F172A',
          800: '#0B1C30',
          900: '#0B1C30',
        },
        emerald: {
          50: '#E6FBF1',
          100: '#6FFBBE', // tertiary-fixed
          200: '#4EDEA3', // tertiary-fixed-dim
          300: '#10B981', // brand emerald
          400: '#0E9968',
          500: '#006E4B', // tertiary-container
          600: '#005338', // tertiary
          700: '#003824',
        },
        // Surfaces / neutrals
        surface: {
          DEFAULT: '#F8F9FF', // background
          dim: '#CBDBF5',
          bright: '#F8F9FF',
          'container-lowest': '#FFFFFF',
          'container-low': '#EFF4FF',
          container: '#E5EEFF',
          high: '#DCE9FF',
          highest: '#D3E4FE',
          variant: '#D3E4FE',
        },
        ink: {
          DEFAULT: '#0B1C30', // on-surface
          muted: '#464555', // on-surface-variant
          subtle: '#5C647A',
        },
        outline: {
          DEFAULT: '#777587',
          variant: '#C7C4D8',
          soft: '#E2E8F0',
        },
        error: {
          DEFAULT: '#BA1A1A',
          container: '#FFDAD6',
          on: '#FFFFFF',
          onContainer: '#93000A',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        // Stitch typographic scale
        'display-lg': ['3rem', { lineHeight: '3.5rem', letterSpacing: '-0.02em', fontWeight: '700' }],
        'headline-lg': ['2rem', { lineHeight: '2.5rem', letterSpacing: '-0.01em', fontWeight: '600' }],
        'headline-lg-mobile': ['1.5rem', { lineHeight: '2rem', letterSpacing: '-0.01em', fontWeight: '600' }],
        'headline-md': ['1.5rem', { lineHeight: '2rem', fontWeight: '600' }],
        'title-lg': ['1.125rem', { lineHeight: '1.75rem', fontWeight: '600' }],
        'body-lg': ['1rem', { lineHeight: '1.5rem', fontWeight: '400' }],
        'body-md': ['0.875rem', { lineHeight: '1.25rem', fontWeight: '400' }],
        'label-md': ['0.75rem', { lineHeight: '1rem', fontWeight: '500' }],
        caption: ['0.75rem', { lineHeight: '1rem', fontWeight: '400' }],
      },
      spacing: {
        // 4px baseline grid
        '4.5': '1.125rem',
        sidebar: '280px',
        topbar: '4rem',
        gutter: '1.25rem', // 20px
      },
      borderRadius: {
        sm: '0.25rem',
        DEFAULT: '0.5rem',
        md: '0.75rem',
        lg: '1rem',
        xl: '1.5rem',
      },
      boxShadow: {
        // Used sparingly — only for floating elements
        floating: '0 4px 6px -1px rgba(15, 23, 42, 0.10), 0 2px 4px -2px rgba(15, 23, 42, 0.05)',
        soft: '0 1px 2px 0 rgba(15, 23, 42, 0.04)',
      },
      animation: {
        'pulse-live': 'pulseLive 1.6s ease-in-out infinite',
        'pulse-dot': 'pulseDot 1.4s ease-in-out infinite',
      },
      keyframes: {
        pulseLive: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(16, 185, 129, 0.5)' },
          '50%': { boxShadow: '0 0 0 8px rgba(16, 185, 129, 0)' },
        },
        pulseDot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
