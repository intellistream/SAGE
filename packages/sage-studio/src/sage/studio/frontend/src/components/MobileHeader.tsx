/**
 * MobileHeader Component - Simplified header for mobile devices
 *
 * Design:
 * - Left: Hamburger menu to toggle sidebar drawer
 * - Center: SAGE logo/title
 * - Right: Theme toggle + User menu + New chat button
 */

import { useState } from 'react'
import { Menu, Plus, Sun, Moon, User, LogOut } from 'lucide-react'
import { SageIcon } from './SageIcon'
import { useThemeStore } from '../store/themeStore'
import { useAuthStore } from '../store/authStore'

interface MobileHeaderProps {
    onMenuClick: () => void
    onNewChat: () => void
    title?: string
}

export default function MobileHeader({ onMenuClick, onNewChat, title }: MobileHeaderProps) {
    const { resolvedTheme, toggleTheme } = useThemeStore()
    const { user, logout, isAuthenticated } = useAuthStore()
    const [showUserMenu, setShowUserMenu] = useState(false)

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
                    <SageIcon size={14} className="text-white" />
                </div>
                <span className="text-base font-medium text-[--gemini-text-primary] truncate max-w-[150px]">
                    {title || 'SAGE'}
                </span>
            </div>

            {/* Right: Theme Toggle + User Menu + New Chat Button */}
            <div className="flex items-center gap-1">
                <button
                    onClick={toggleTheme}
                    className="p-2 rounded-full hover:bg-[--gemini-hover-bg] transition-colors text-[--gemini-text-secondary]"
                    aria-label={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                    {resolvedTheme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
                </button>

                {/* User Menu */}
                <div className="relative">
                    {isAuthenticated ? (
                        <button
                            onClick={() => setShowUserMenu(!showUserMenu)}
                            className="p-1 rounded-full hover:bg-[--gemini-hover-bg] transition-colors"
                            aria-label="User menu"
                        >
                            <div className="w-7 h-7 rounded-full bg-[--gemini-accent] flex items-center justify-center text-white text-xs font-medium">
                                {user?.username?.[0]?.toUpperCase() || <User size={14} />}
                            </div>
                        </button>
                    ) : (
                        <button
                            onClick={() => (window.location.href = '/login')}
                            className="p-2 rounded-full hover:bg-[--gemini-hover-bg] transition-colors text-[--gemini-accent]"
                            aria-label="Login"
                        >
                            <User size={20} />
                        </button>
                    )}

                    {/* User Dropdown Menu */}
                    {showUserMenu && isAuthenticated && (
                        <>
                            <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)} />
                            <div className="absolute right-0 top-full mt-2 w-48 bg-[--gemini-main-bg] rounded-xl shadow-lg border border-[--gemini-border] py-2 z-50">
                                <div className="px-4 py-2 border-b border-[--gemini-border]">
                                    <div className="text-sm font-medium text-[--gemini-text-primary]">
                                        {user?.username || 'User'}
                                    </div>
                                    {user?.is_guest && (
                                        <div className="text-xs text-[--gemini-text-secondary]">Guest Mode</div>
                                    )}
                                </div>
                                {user?.is_guest && (
                                    <button
                                        onClick={() => {
                                            setShowUserMenu(false)
                                            window.location.href = '/login'
                                        }}
                                        className="w-full flex items-center gap-2 px-4 py-2 text-sm text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg] transition-colors"
                                    >
                                        <User size={16} />
                                        Login / Sign up
                                    </button>
                                )}
                                <button
                                    onClick={() => {
                                        setShowUserMenu(false)
                                        logout()
                                    }}
                                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors"
                                >
                                    <LogOut size={16} />
                                    {user?.is_guest ? 'Exit Guest Mode' : 'Logout'}
                                </button>
                            </div>
                        </>
                    )}
                </div>

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
