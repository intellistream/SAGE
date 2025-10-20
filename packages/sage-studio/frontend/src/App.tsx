import { useState, useRef, useCallback, useEffect } from 'react'
import { Layout } from 'antd'
import Toolbar from './components/Toolbar'
import NodePalette from './components/NodePalette'
import FlowEditor from './components/FlowEditor'
import PropertiesPanel from './components/PropertiesPanel'
import StatusBar from './components/StatusBar'

const { Header, Footer } = Layout

function App() {
    const [leftWidth, setLeftWidth] = useState(280)
    const [rightWidth, setRightWidth] = useState(320)
    const [isDraggingLeft, setIsDraggingLeft] = useState(false)
    const [isDraggingRight, setIsDraggingRight] = useState(false)
    const containerRef = useRef<HTMLDivElement>(null)

    // 左侧拖拽处理
    const handleLeftMouseDown = useCallback(() => {
        setIsDraggingLeft(true)
    }, [])

    // 右侧拖拽处理
    const handleRightMouseDown = useCallback(() => {
        setIsDraggingRight(true)
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
        },
        [isDraggingLeft, isDraggingRight]
    )

    // 鼠标释放处理
    const handleMouseUp = useCallback(() => {
        setIsDraggingLeft(false)
        setIsDraggingRight(false)
    }, [])

    // 添加和移除全局事件监听
    useEffect(() => {
        if (isDraggingLeft || isDraggingRight) {
            document.addEventListener('mousemove', handleMouseMove)
            document.addEventListener('mouseup', handleMouseUp)
            // 防止文本选择
            document.body.style.userSelect = 'none'
            document.body.style.cursor = 'col-resize'
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
    }, [isDraggingLeft, isDraggingRight, handleMouseMove, handleMouseUp])

    return (
        <div
            ref={containerRef}
            style={{
                height: '100vh',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
            }}
        >
            {/* 顶部工具栏 - 固定 */}
            <Header
                style={{
                    padding: 0,
                    height: 64,
                    lineHeight: 'normal',
                    flexShrink: 0,
                }}
            >
                <Toolbar />
            </Header>

            {/* 主要内容区域 */}
            <div
                style={{
                    flex: 1,
                    display: 'flex',
                    overflow: 'hidden',
                    position: 'relative',
                }}
            >
                {/* 左侧面板 - 可滚动 */}
                <div
                    style={{
                        width: leftWidth,
                        height: '100%',
                        backgroundColor: '#fff',
                        borderRight: '1px solid #e8e8e8',
                        overflow: 'auto',
                        flexShrink: 0,
                    }}
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
                        backgroundColor: '#fff',
                        borderLeft: '1px solid #e8e8e8',
                        overflow: 'auto',
                        flexShrink: 0,
                    }}
                >
                    <PropertiesPanel />
                </div>
            </div>

            {/* 底部状态栏 - 固定 */}
            <Footer
                style={{
                    padding: '8px 16px',
                    height: 40,
                    lineHeight: 'normal',
                    flexShrink: 0,
                }}
            >
                <StatusBar />
            </Footer>
        </div>
    )
}

export default App
