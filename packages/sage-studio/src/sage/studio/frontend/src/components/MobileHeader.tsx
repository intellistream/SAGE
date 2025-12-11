/**
 * MobileHeader Component - Simplified header for mobile devices
 *
 * Design:
 * - Left: Hamburger menu to toggle sidebar drawer
 * - Center: SAGE logo/title
 * - Right: Theme toggle + New chat button
 */

import { Menu, Plus, Zap, Sun, Moon } from 'lucide-react'
import { useThemeStore } from '../store/themeStore'

interface MobileHeaderProps {
    onMenuClick: () => void
    onNewChat: () => void
    title?: string
}

export default function MobileHeader({ onMenuClick, onNewChat, title }: MobileHeaderProps) {
    const { resolvedTheme, toggleTheme } = useThemeStore()

    return (
        <header
            className="fixed top-0 left-0 right-0 h-14 bg-[--gemini-main-bg]/95 backdrop-blur-md border-b border-[--gemini-border] flex items-center justify-between px-4 z-50"
            style={{ paddingTop: 'env(safe-area-inset-top)' }}
        >
            {/* Left: Menu Button */}
            <button
                onClick={onMenuClick}
                className="p-2 -ml-2 rounded-full hover:bg-[--gemini-hover-bg] transition-colors text-[--gemini-text-secondary]"
                aria-label="Open menu"
            >
                <Menu size={24} />
            </button>

            {/* Center: Logo & Title */}
            <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                    <Zap size={14} className="text-white" />
                </div>
                <span className="text-base font-medium text-[--gemini-text-primary] truncate max-w-[150px]">
                    {title || 'SAGE'}
                </span>
            </div>

            {/* Right: Theme Toggle + New Chat Button */}
            <div className="flex items-center gap-1">
                <button
                    onClick={toggleTheme}
                    className="p-2 rounded-full hover:bg-[--gemini-hover-bg] transition-colors text-[--gemini-text-secondary]"
                    aria-label={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                    {resolvedTheme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
                </button>
                <button
                    onClick={onNewChat}
                    className="p-2 -mr-2 rounded-full hover:bg-[--gemini-hover-bg] transition-colors text-[--gemini-accent]"
                    aria-label="New chat"
                >
                    <Plus size={24} />
                </button>
            </div>
        </header>
    )
}
