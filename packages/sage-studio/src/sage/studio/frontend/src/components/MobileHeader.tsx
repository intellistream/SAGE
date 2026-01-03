/**
 * MobileHeader Component - Simplified header for mobile devices
 *
 * Design:
 * - Left: Hamburger menu to toggle sidebar drawer
 * - Center: Model selector (tap to switch models)
 * - Right: Theme toggle + User menu + New chat button
 */

import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Menu, Plus, Sun, Moon, User, LogOut, ChevronDown, Check } from 'lucide-react'
import { SageIcon } from './SageIcon'
import { useThemeStore } from '../store/themeStore'
import { useAuthStore } from '../store/authStore'
import type { LLMStatus } from '../services/api'

interface MobileHeaderProps {
    onMenuClick: () => void
    onNewChat: () => void
    title?: string
    llmStatus?: LLMStatus | null
    onSelectModel?: (modelName: string, baseUrl: string) => void
}

export default function MobileHeader({ onMenuClick, onNewChat, llmStatus, onSelectModel }: MobileHeaderProps) {
    const { resolvedTheme, toggleTheme } = useThemeStore()
    const { user, logout, isAuthenticated } = useAuthStore()
    const [showUserMenu, setShowUserMenu] = useState(false)
    const [showModelMenu, setShowModelMenu] = useState(false)
    const modelButtonRef = useRef<HTMLButtonElement>(null)
    const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 })

    // Get current model display name
    const modelName = llmStatus?.model_name
        ? (llmStatus.model_name.split('/').pop() || llmStatus.model_name.split('__').pop() || 'Model')
        : 'SAGE'
    const isHealthy = llmStatus?.healthy

    // Update menu position when opening
    useEffect(() => {
        if (showModelMenu && modelButtonRef.current) {
            const rect = modelButtonRef.current.getBoundingClientRect()
            setMenuPosition({
                top: rect.bottom + 8,
                left: rect.left + rect.width / 2,
            })
        }
    }, [showModelMenu])

    const handleModelSelect = (model: { name: string; base_url: string }) => {
        onSelectModel?.(model.name, model.base_url)
        setShowModelMenu(false)
    }

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

            {/* Center: Model Selector */}
            <div className="relative flex items-center">
                <button
                    ref={modelButtonRef}
                    onClick={() => setShowModelMenu(!showModelMenu)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-full hover:bg-[--gemini-hover-bg] transition-colors"
                    aria-label="Select model"
                >
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                        <SageIcon size={12} className="text-white" />
                    </div>
                    <span className="text-sm font-medium text-[--gemini-text-primary] truncate max-w-[100px]">
                        {modelName}
                    </span>
                    <ChevronDown size={14} className="text-[--gemini-text-secondary]" />
                    {isHealthy && (
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                    )}
                </button>
            </div>

            {/* Model Dropdown Menu - Rendered via Portal to escape stacking context */}
            {showModelMenu && createPortal(
                <>
                    {/* Backdrop - covers entire screen */}
                    <div
                        className="fixed inset-0 z-[9998]"
                        onClick={() => setShowModelMenu(false)}
                        style={{ background: 'transparent' }}
                    />
                    {/* Dropdown menu */}
                    <div
                        className="fixed w-64 max-h-[60vh] overflow-y-auto bg-[--gemini-main-bg] rounded-xl shadow-lg border border-[--gemini-border] py-2 z-[9999]"
                        style={{
                            top: menuPosition.top,
                            left: menuPosition.left,
                            transform: 'translateX(-50%)',
                        }}
                    >
                        <div className="px-4 py-2 border-b border-[--gemini-border]">
                            <div className="text-xs font-medium text-[--gemini-text-secondary] uppercase tracking-wide">
                                Select Model
                            </div>
                        </div>
                        {llmStatus?.available_models && llmStatus.available_models.length > 0 ? (
                            llmStatus.available_models.map((model) => (
                                <button
                                    key={model.name}
                                    onClick={() => handleModelSelect(model)}
                                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[--gemini-hover-bg] transition-colors"
                                >
                                    <div className="flex-1 text-left">
                                        <div className="text-sm font-medium text-[--gemini-text-primary]">
                                            {model.name}
                                        </div>
                                        <div className="text-xs text-[--gemini-text-secondary]">
                                            {model.description || (model.is_local ? 'Local Model' : 'Cloud Model')}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div
                                            className={`w-2 h-2 rounded-full ${model.healthy ? 'bg-green-500' : 'bg-red-400'}`}
                                            title={model.healthy ? 'Running' : 'Stopped'}
                                        />
                                        {llmStatus?.model_name === model.name && (
                                            <Check size={16} className="text-[--gemini-accent]" />
                                        )}
                                    </div>
                                </button>
                            ))
                        ) : (
                            <div className="px-4 py-3 text-sm text-[--gemini-text-secondary]">
                                <div className="font-medium text-[--gemini-text-primary]">{modelName}</div>
                                <div className="text-xs mt-1">
                                    {llmStatus?.is_local ? 'Local Model' : 'Cloud Model'} · {isHealthy ? 'Connected' : 'Disconnected'}
                                </div>
                            </div>
                        )}
                    </div>
                </>,
                document.body
            )}

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
