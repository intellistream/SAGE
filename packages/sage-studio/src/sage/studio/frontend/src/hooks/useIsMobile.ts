/**
 * useIsMobile Hook - Detects mobile viewport
 *
 * Uses matchMedia for efficient reactive detection of mobile breakpoint (768px).
 * Returns true on mobile devices, false on desktop.
 */

import { useState, useEffect } from 'react'

const MOBILE_BREAKPOINT = 768

export function useIsMobile(): boolean {
    const [isMobile, setIsMobile] = useState<boolean>(() => {
        if (typeof window === 'undefined') return false
        return window.innerWidth < MOBILE_BREAKPOINT
    })

    useEffect(() => {
        // Use matchMedia for better performance
        const mediaQuery = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)

        const handleChange = (e: MediaQueryListEvent | MediaQueryList) => {
            setIsMobile(e.matches)
        }

        // Set initial value
        handleChange(mediaQuery)

        // Modern browsers
        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', handleChange)
            return () => mediaQuery.removeEventListener('change', handleChange)
        } else {
            // Legacy browsers
            mediaQuery.addListener(handleChange)
            return () => mediaQuery.removeListener(handleChange)
        }
    }, [])

    return isMobile
}

export default useIsMobile
