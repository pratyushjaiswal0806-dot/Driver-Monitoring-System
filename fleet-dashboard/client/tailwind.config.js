/** @type {import('tailwindcss').Config} */
export default {
    content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
    theme: {
        extend: {
            fontFamily: {
                display: ['Space Grotesk', 'sans-serif'],
                body: ['Manrope', 'sans-serif']
            },
            boxShadow: {
                soft: '0 20px 60px rgba(0, 0, 0, 0.28)',
                glass: '0 4px 24px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
                critical: '0 0 20px rgba(220, 38, 38, 0.35), 0 0 60px rgba(220, 38, 38, 0.1)'
            },
            colors: {
                app: {
                    background: '#080b14',
                    backgroundTop: '#0d1526',
                    panel: 'rgba(255, 255, 255, 0.03)',
                    border: 'rgba(255, 255, 255, 0.07)'
                },
                risk: {
                    safe: '#22c55e',
                    mild: '#eab308',
                    warning: '#f97316',
                    high: '#ef4444',
                    critical: '#dc2626',
                    criticalGlow: 'rgba(220, 38, 38, 0.4)'
                },
                app: {
                    panelAlt: '#151b2d'
                }
            },
            keyframes: {
                pageReveal: {
                    '0%': { opacity: 0, transform: 'translateY(12px)' },
                    '100%': { opacity: 1, transform: 'translateY(0)' }
                },
                surfaceLift: {
                    '0%': { opacity: 0, transform: 'translateY(10px) scale(0.99)' },
                    '100%': { opacity: 1, transform: 'translateY(0) scale(1)' }
                },
                sheenDrift: {
                    '0%': { transform: 'translateX(-120%)' },
                    '100%': { transform: 'translateX(120%)' }
                },
                pulseCritical: {
                    '0%, 100%': {
                        transform: 'scale(1)',
                        boxShadow: '0 0 20px rgba(220, 38, 38, 0.24), 0 0 60px rgba(220, 38, 38, 0.08)'
                    },
                    '50%': {
                        transform: 'scale(1.02)',
                        boxShadow: '0 0 28px rgba(220, 38, 38, 0.36), 0 0 80px rgba(220, 38, 38, 0.14)'
                    }
                },
                skeletonShimmer: {
                    '0%': { backgroundPosition: '0 0' },
                    '100%': { backgroundPosition: '200% 0' }
                },
                pulseGlow: {
                    '0%, 100%': { boxShadow: '0 0 6px rgba(34, 197, 94, 0.6)' },
                    '50%': { boxShadow: '0 0 10px rgba(34, 197, 94, 0.9)' }
                },
                rowReveal: {
                    '0%': { opacity: 0, transform: 'translateY(4px)' },
                    '100%': { opacity: 1, transform: 'translateY(0)' }
                },
                heroDrift: {
                    '0%, 100%': { transform: 'translate3d(0, 0, 0) scale(1)' },
                    '50%': { transform: 'translate3d(-2%, -4%, 0) scale(1.04)' }
                }
            },
            animation: {
                pageReveal: 'pageReveal 400ms ease-out both',
                surfaceLift: 'surfaceLift 200ms ease-out both',
                sheenDrift: 'sheenDrift 600ms ease-out both',
                pulseCritical: 'pulseCritical 2s ease-in-out infinite',
                skeletonShimmer: 'skeletonShimmer 1.5s linear infinite',
                pulseGlow: 'pulseGlow 2s ease-in-out infinite',
                rowReveal: 'rowReveal 400ms ease-out both',
                heroDrift: 'heroDrift 14s ease-in-out infinite'
            }
        }
    },
    plugins: []
};
