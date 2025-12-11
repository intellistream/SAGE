/**
 * Theme Store - Manages light/dark theme state with persistence
 *
 * Features:
 * - Persistent storage in localStorage
 * - System preference detection
 * - Real-time DOM class synchronization
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Theme = 'light' | 'dark' | 'system'

interface ThemeState {
    theme: Theme
    /** The actual resolved theme (light or dark), considering system preference */
    resolvedTheme: 'light' | 'dark'
    setTheme: (theme: Theme) => void
    toggleTheme: () => void
}

/**
 * Get the system's preferred color scheme
 */
function getSystemTheme(): 'light' | 'dark' {
    if (typeof window === 'undefined') return 'light'
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * Resolve the actual theme based on user preference and system setting
 */
function resolveTheme(theme: Theme): 'light' | 'dark' {
    if (theme === 'system') {
        return getSystemTheme()
    }
    return theme
}

/**
 * Apply theme to the DOM by toggling the 'dark' class on documentElement
 */
function applyThemeToDOM(resolvedTheme: 'light' | 'dark') {
    if (typeof document === 'undefined') return

    const root = document.documentElement

    if (resolvedTheme === 'dark') {
        root.classList.add('dark')
    } else {
        root.classList.remove('dark')
    }

    // Also update the color-scheme for native UI elements
    root.style.colorScheme = resolvedTheme
}

export const useThemeStore = create<ThemeState>()(
    persist(
        (set, get) => ({
            theme: 'light',
            resolvedTheme: 'light',

            setTheme: (theme: Theme) => {
                const resolvedTheme = resolveTheme(theme)
                applyThemeToDOM(resolvedTheme)
                set({ theme, resolvedTheme })
            },

            toggleTheme: () => {
                const { theme } = get()
                // If system, resolve to actual and then toggle
                const currentResolved = resolveTheme(theme)
                const newTheme = currentResolved === 'light' ? 'dark' : 'light'
                const resolvedTheme = newTheme
                applyThemeToDOM(resolvedTheme)
                set({ theme: newTheme, resolvedTheme })
            },
        }),
        {
            name: 'sage-studio-theme',
            // Only persist the theme preference, not the resolved value
            partialize: (state) => ({ theme: state.theme }),
            onRehydrateStorage: () => (state) => {
                // After rehydration, resolve and apply the theme
                if (state) {
                    const resolvedTheme = resolveTheme(state.theme)
                    applyThemeToDOM(resolvedTheme)
                    state.resolvedTheme = resolvedTheme
                }
            },
        }
    )
)

// Initialize theme on first load (for SSR/initial render)
if (typeof window !== 'undefined') {
    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', () => {
        const state = useThemeStore.getState()
        if (state.theme === 'system') {
            const resolvedTheme = getSystemTheme()
            applyThemeToDOM(resolvedTheme)
            useThemeStore.setState({ resolvedTheme })
        }
    })

    // Apply theme immediately on load (before React hydration)
    const stored = localStorage.getItem('sage-studio-theme')
    if (stored) {
        try {
            const parsed = JSON.parse(stored)
            const theme = parsed.state?.theme || 'light'
            const resolvedTheme = resolveTheme(theme)
            applyThemeToDOM(resolvedTheme)
        } catch {
            applyThemeToDOM('light')
        }
    }
}
