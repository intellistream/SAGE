import { useState, useRef, useCallback, useEffect } from 'react'
import { Layout, Spin } from 'antd'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Toolbar from './components/Toolbar'
import NodePalette from './components/NodePalette'
import FlowEditor from './components/FlowEditor'
import PropertiesPanel from './components/PropertiesPanel'
import StatusBar from './components/StatusBar'
import LogViewer from './components/LogViewer'
import ChatMode from './components/ChatMode'
import FinetunePanel from './components/FinetunePanel'
import { LoginPage } from './components/LoginPage'
import { useAuthStore } from './store/authStore'
import { useIsMobile } from './hooks/useIsMobile'

const { Header, Footer } = Layout

export type AppMode = 'chat' | 'canvas' | 'finetune'

function RequireAuth({ children }: { children: JSX.Element }) {
    const { isAuthenticated, isLoading, checkAuth } = useAuthStore()
    const location = useLocation()
    const [isChecking, setIsChecking] = useState(true)

    useEffect(() => {
        const initAuth = async () => {
            await checkAuth()
            setIsChecking(false)
        }
        initAuth()
    }, [checkAuth])

    if (isChecking || isLoading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <Spin size="large" tip="Loading..." />
            </div>
        )
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />
    }

    return children
}

function StudioLayout() {
    const [mode, setMode] = useState<AppMode>('chat')
    const [leftWidth, setLeftWidth] = useState(280)
    const [rightWidth, setRightWidth] = useState(320)
    const [bottomHeight, setBottomHeight] = useState(250)
    const [isDraggingLeft, setIsDraggingLeft] = useState(false)
    const [isDraggingRight, setIsDraggingRight] = useState(false)
    const [isDraggingBottom, setIsDraggingBottom] = useState(false)
    const [showLogs, setShowLogs] = useState(false)
    const containerRef = useRef<HTMLDivElement>(null)

    // Mobile detection
    const isMobile = useIsMobile()

    // Force chat mode on mobile
    const effectiveMode = isMobile ? 'chat' : mode

    // 左侧拖拽处理
    const handleLeftMouseDown = useCallback(() => {
        setIsDraggingLeft(true)
    }, [])

    // 右侧拖拽处理
    const handleRightMouseDown = useCallback(() => {
        setIsDraggingRight(true)
    }, [])

    // 底部拖拽处理
    const handleBottomMouseDown = useCallback(() => {
        setIsDraggingBottom(true)
    }, [])

    // 鼠标移动处理
    const handleMouseMove = useCallback(
        (e: MouseEvent) => {
            if (!containerRef.current) return

            const containerRect = containerRef.current.getBoundingClientRect()

            if (isDraggingLeft) {
                const newWidth = e.clientX - containerRect.left
                // 限制最小和最大宽度
                if (newWidth >= 200 && newWidth <= 500) {
                    setLeftWidth(newWidth)
                }
            }

            if (isDraggingRight) {
                const newWidth = containerRect.right - e.clientX
                // 限制最小和最大宽度
                if (newWidth >= 250 && newWidth <= 600) {
                    setRightWidth(newWidth)
                }
            }

            if (isDraggingBottom) {
                const newHeight = containerRect.bottom - e.clientY - 40 // 减去 footer 高度
                // 限制最小和最大高度
                if (newHeight >= 150 && newHeight <= 500) {
                    setBottomHeight(newHeight)
                }
            }
        },
        [isDraggingLeft, isDraggingRight, isDraggingBottom]
    )

    // 鼠标释放处理
    const handleMouseUp = useCallback(() => {
        setIsDraggingLeft(false)
        setIsDraggingRight(false)
        setIsDraggingBottom(false)
    }, [])

    // 添加和移除全局事件监听
    useEffect(() => {
        if (isDraggingLeft || isDraggingRight || isDraggingBottom) {
            document.addEventListener('mousemove', handleMouseMove)
            document.addEventListener('mouseup', handleMouseUp)
            // 防止文本选择
            document.body.style.userSelect = 'none'
            document.body.style.cursor = isDraggingBottom ? 'row-resize' : 'col-resize'
        } else {
            document.removeEventListener('mousemove', handleMouseMove)
            document.removeEventListener('mouseup', handleMouseUp)
            document.body.style.userSelect = ''
            document.body.style.cursor = ''
        }

        return () => {
            document.removeEventListener('mousemove', handleMouseMove)
            document.removeEventListener('mouseup', handleMouseUp)
            document.body.style.userSelect = ''
            document.body.style.cursor = ''
        }
    }, [isDraggingLeft, isDraggingRight, isDraggingBottom, handleMouseMove, handleMouseUp])

    return (
        <div
            ref={containerRef}
            className={isMobile ? 'h-[100dvh]' : ''}
            style={isMobile ? {
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
            } : {
                height: '100vh',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
            }}
        >
            {/* Desktop Header - Hidden on mobile (ChatMode has its own mobile header) */}
            {!isMobile && (
                <Header
                    style={{
                        padding: 0,
                        height: 64,
                        lineHeight: 'normal',
                        flexShrink: 0,
                    }}
                    className="bg-[--gemini-main-bg]"
                >
                    <Toolbar mode={mode} onModeChange={setMode} />
                </Header>
            )}

            {/* Main Content - Force Chat mode on mobile */}
            {effectiveMode === 'canvas' ? (
                <div
                    style={{
                        flex: 1,
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden',
                        position: 'relative',
                    }}
                >
                    {/* 顶部区域（节点面板 + 画布 + 属性面板） */}
                    <div
                        style={{
                            flex: 1,
                            display: 'flex',
                            overflow: 'hidden',
                        }}
                    >
                        {/* 左侧面板 - 可滚动 */}
                        <div
                            style={{
                                width: leftWidth,
                                height: '100%',
                                borderRight: '1px solid var(--gemini-border)',
                                overflow: 'auto',
                                flexShrink: 0,
                            }}
                            className="bg-[--gemini-main-bg]"
                        >
                            <NodePalette />
                        </div>

                        {/* 左侧拖拽手柄 */}
                        <div
                            onMouseDown={handleLeftMouseDown}
                            style={{
                                width: 4,
                                height: '100%',
                                cursor: 'col-resize',
                                backgroundColor: isDraggingLeft ? '#1890ff' : 'transparent',
                                transition: isDraggingLeft ? 'none' : 'background-color 0.2s',
                                flexShrink: 0,
                                position: 'relative',
                                zIndex: 10,
                            }}
                            onMouseEnter={(e) => {
                                if (!isDraggingLeft) {
                                    e.currentTarget.style.backgroundColor = '#e8e8e8'
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (!isDraggingLeft) {
                                    e.currentTarget.style.backgroundColor = 'transparent'
                                }
                            }}
                        />

                        {/* 中间画布区域 - 不滚动 */}
                        <div
                            style={{
                                flex: 1,
                                height: '100%',
                                overflow: 'hidden',
                                position: 'relative',
                            }}
                        >
                            <FlowEditor />
                        </div>

                        {/* 右侧拖拽手柄 */}
                        <div
                            onMouseDown={handleRightMouseDown}
                            style={{
                                width: 4,
                                height: '100%',
                                cursor: 'col-resize',
                                backgroundColor: isDraggingRight ? '#1890ff' : 'transparent',
                                transition: isDraggingRight ? 'none' : 'background-color 0.2s',
                                flexShrink: 0,
                                position: 'relative',
                                zIndex: 10,
                            }}
                            onMouseEnter={(e) => {
                                if (!isDraggingRight) {
                                    e.currentTarget.style.backgroundColor = '#e8e8e8'
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (!isDraggingRight) {
                                    e.currentTarget.style.backgroundColor = 'transparent'
                                }
                            }}
                        />

                        {/* 右侧面板 - 可滚动 */}
                        <div
                            style={{
                                width: rightWidth,
                                height: '100%',
                                borderLeft: '1px solid var(--gemini-border)',
                                overflow: 'auto',
                                flexShrink: 0,
                            }}
                            className="bg-[--gemini-main-bg]"
                        >
                            <PropertiesPanel />
                        </div>
                    </div>

                    {/* 底部日志面板 */}
                    {showLogs && (
                        <>
                            {/* 底部拖拽手柄 */}
                            <div
                                onMouseDown={handleBottomMouseDown}
                                style={{
                                    height: 4,
                                    width: '100%',
                                    cursor: 'row-resize',
                                    backgroundColor: isDraggingBottom ? '#1890ff' : 'transparent',
                                    transition: isDraggingBottom ? 'none' : 'background-color 0.2s',
                                    flexShrink: 0,
                                    position: 'relative',
                                    zIndex: 10,
                                }}
                                onMouseEnter={(e) => {
                                    if (!isDraggingBottom) {
                                        e.currentTarget.style.backgroundColor = '#e8e8e8'
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!isDraggingBottom) {
                                        e.currentTarget.style.backgroundColor = 'transparent'
                                    }
                                }}
                            />

                            {/* 日志查看器 */}
                            <div
                                style={{
                                    height: bottomHeight,
                                    borderTop: '1px solid var(--gemini-border)',
                                    overflow: 'hidden',
                                    flexShrink: 0,
                                }}
                                className="bg-[--gemini-main-bg]"
                            >
                                <LogViewer />
                            </div>
                        </>
                    )}
                </div>
            ) : effectiveMode === 'chat' ? (
                /* Chat 模式 - 全新界面 (includes mobile support) */
                <div style={{ flex: 1, overflow: 'hidden' }}>
                    <ChatMode onModeChange={setMode} isMobile={isMobile} />
                </div>
            ) : (
                /* Finetune 模式 - 模型微调 (Desktop only) */
                <div style={{ flex: 1, overflow: 'hidden' }} className="bg-[--gemini-main-bg]">
                    <FinetunePanel />
                </div>
            )}

            {/* 底部状态栏 - 仅在 Canvas 模式且非移动端显示 */}
            {effectiveMode === 'canvas' && !isMobile && (
                <Footer
                    style={{
                        padding: '8px 16px',
                        height: 40,
                        lineHeight: 'normal',
                        flexShrink: 0,
                    }}
                >
                    <StatusBar showLogs={showLogs} onToggleLogs={() => setShowLogs(!showLogs)} />
                </Footer>
            )}
        </div>
    )
}

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route
                    path="/"
                    element={
                        <RequireAuth>
                            <StudioLayout />
                        </RequireAuth>
                    }
                />
            </Routes>
        </BrowserRouter>
    )
}

export default App
