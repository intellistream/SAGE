/**
 * MobileSidebar Component - Drawer-style sidebar for mobile devices
 *
 * Uses a slide-in drawer pattern with backdrop overlay.
 * Closes automatically when a session is selected.
 */

import { X, Plus, MessageSquare, MoreHorizontal, Trash2 } from 'lucide-react'
import { Dropdown, Spin } from 'antd'
import type { ChatSessionSummary } from '../services/api'

interface MobileSidebarProps {
    isOpen: boolean
    onClose: () => void
    sessions: ChatSessionSummary[]
    currentSessionId: string | null
    isLoading: boolean
    onSessionClick: (sessionId: string) => void
    onDeleteSession: (sessionId: string) => void
    onNewChat: () => void
}

export default function MobileSidebar({
    isOpen,
    onClose,
    sessions,
    currentSessionId,
    isLoading,
    onSessionClick,
    onDeleteSession,
    onNewChat,
}: MobileSidebarProps) {
    const handleSessionClick = (sessionId: string) => {
        onSessionClick(sessionId)
        onClose() // Auto-close drawer after selection
    }

    const handleNewChat = () => {
        onNewChat()
        onClose()
    }

    return (
        <>
            {/* Backdrop */}
            <div
                className={`
                    fixed inset-0 bg-black/40 z-40 transition-opacity duration-300 md:hidden
                    ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}
                `}
                onClick={onClose}
            />

            {/* Drawer */}
            <div
                className={`
                    fixed top-0 left-0 h-full w-[280px] max-w-[85vw] bg-[--gemini-sidebar-bg] z-50
                    transform transition-transform duration-300 ease-out md:hidden
                    flex flex-col shadow-xl
                    ${isOpen ? 'translate-x-0' : '-translate-x-full'}
                `}
            >
                {/* Drawer Header */}
                <div className="flex items-center justify-between p-4 border-b border-[--gemini-border]">
                    <span className="text-lg font-medium text-[--gemini-text-primary]">History</span>
                    <button
                        onClick={onClose}
                        className="p-2 -mr-2 rounded-full hover:bg-[--gemini-hover-bg] transition-colors text-[--gemini-text-secondary]"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* New Chat Button */}
                <div className="p-3">
                    <button
                        onClick={handleNewChat}
                        className="flex items-center gap-3 w-full px-4 py-3 rounded-full
                            bg-[--gemini-hover-bg] text-[--gemini-text-secondary] font-medium text-sm
                            hover:bg-[--gemini-main-bg] hover:shadow-md transition-all duration-200 active:scale-[0.98]"
                    >
                        <Plus size={20} />
                        <span>New chat</span>
                    </button>
                </div>

                {/* Session List */}
                <div className="flex-1 overflow-y-auto py-2">
                    {isLoading ? (
                        <div className="flex justify-center items-center h-32">
                            <Spin />
                        </div>
                    ) : sessions.length === 0 ? (
                        <div className="text-center text-[--gemini-text-secondary]/60 text-sm py-8 px-4">
                            No conversations yet
                        </div>
                    ) : (
                        <div className="space-y-1">
                            {sessions.map((session) => (
                                <div
                                    key={session.id}
                                    className={`
                                        group flex items-center gap-3 px-3 py-3 mx-2 rounded-xl cursor-pointer
                                        transition-all duration-200 ease-out active:scale-[0.98]
                                        ${currentSessionId === session.id
                                            ? 'bg-[#D3E3FD] dark:bg-[#394457] text-[--gemini-text-primary]'
                                            : 'hover:bg-[--gemini-hover-bg] text-[--gemini-text-secondary]'
                                        }
                                    `}
                                    onClick={() => handleSessionClick(session.id)}
                                >
                                    <MessageSquare size={18} className="flex-shrink-0" />
                                    <span className="flex-1 text-sm truncate font-medium">
                                        {session.title}
                                    </span>
                                    <Dropdown
                                        menu={{
                                            items: [
                                                {
                                                    key: 'delete',
                                                    label: 'Delete',
                                                    danger: true,
                                                    icon: <Trash2 size={14} />,
                                                    onClick: (e) => {
                                                        e.domEvent.stopPropagation()
                                                        onDeleteSession(session.id)
                                                    },
                                                },
                                            ],
                                        }}
                                        trigger={['click']}
                                    >
                                        <button
                                            className="p-1.5 rounded-full hover:bg-[#D3E3FD] dark:hover:bg-[#4a5568] transition-all"
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            <MoreHorizontal size={16} />
                                        </button>
                                    </Dropdown>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Safe area for iOS bottom */}
                <div className="h-safe-bottom" />
            </div>
        </>
    )
}
