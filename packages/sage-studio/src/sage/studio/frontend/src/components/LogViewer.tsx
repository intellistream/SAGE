import { useState, useEffect, useRef } from 'react'
import { Card, Button, Space, Select, Switch, Tag } from 'antd'
import { Terminal, Trash2, Download } from 'lucide-react'
import { useFlowStore } from '../store/flowStore'
import { getLogs } from '../services/api'

interface LogEntry {
    id: number
    timestamp: string
    level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'
    message: string
    nodeId?: string
}

export default function LogViewer() {
    const { currentJobId, nodes } = useFlowStore()
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [selectedNode, setSelectedNode] = useState<string | null>(null)
    const [selectedLevel, setSelectedLevel] = useState<string | null>(null)
    const [autoScroll, setAutoScroll] = useState(true)
    const [lastId, setLastId] = useState(0)
    const logsEndRef = useRef<HTMLDivElement>(null)

    // 自动滚动到底部
    useEffect(() => {
        if (autoScroll && logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
        }
    }, [logs, autoScroll])

    // 实时日志轮询
    useEffect(() => {
        if (!currentJobId) {
            setLogs([])
            setLastId(0)
            return
        }

        // 轮询获取新日志
        const interval = setInterval(async () => {
            try {
                const result = await getLogs(currentJobId, lastId)
                if (result.logs.length > 0) {
                    setLogs(prev => [...prev, ...result.logs])
                    setLastId(result.last_id)
                }
            } catch (error) {
                // 静默失败，避免干扰用户
                console.error('获取日志失败:', error)
            }
        }, 2000)

        return () => clearInterval(interval)
    }, [currentJobId, lastId])

    // 过滤日志
    const filteredLogs = logs.filter(log => {
        if (selectedNode && log.nodeId !== selectedNode) return false
        if (selectedLevel && log.level !== selectedLevel) return false
        return true
    })

    // 清空日志
    const handleClear = () => {
        setLogs([])
    }

    // 导出日志
    const handleExport = () => {
        const logText = filteredLogs
            .map(log => `[${log.timestamp}] [${log.level}] ${log.nodeId ? `[${log.nodeId}] ` : ''}${log.message}`)
            .join('\n')

        const blob = new Blob([logText], { type: 'text/plain' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `logs_${currentJobId}_${Date.now()}.txt`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
    }

    // 日志级别颜色
    const getLevelColor = (level: string) => {
        switch (level) {
            case 'ERROR':
                return 'red'
            case 'WARNING':
                return 'orange'
            case 'INFO':
                return 'blue'
            case 'DEBUG':
                return 'default'
            default:
                return 'default'
        }
    }

    return (
        <Card
            title={
                <Space>
                    <Terminal size={16} />
                    <span>实时日志</span>
                </Space>
            }
            extra={
                <Space>
                    <Select
                        placeholder="过滤节点"
                        allowClear
                        style={{ width: 150 }}
                        value={selectedNode}
                        onChange={setSelectedNode}
                        size="small"
                    >
                        {nodes.map(node => (
                            <Select.Option key={node.id} value={node.id}>
                                {node.data.label || node.id}
                            </Select.Option>
                        ))}
                    </Select>

                    <Select
                        placeholder="过滤级别"
                        allowClear
                        style={{ width: 120 }}
                        value={selectedLevel}
                        onChange={setSelectedLevel}
                        size="small"
                    >
                        <Select.Option value="INFO">INFO</Select.Option>
                        <Select.Option value="WARNING">WARNING</Select.Option>
                        <Select.Option value="ERROR">ERROR</Select.Option>
                        <Select.Option value="DEBUG">DEBUG</Select.Option>
                    </Select>

                    <Space.Compact>
                        <Switch
                            checked={autoScroll}
                            onChange={setAutoScroll}
                            size="small"
                            checkedChildren="自动滚动"
                            unCheckedChildren="手动滚动"
                        />
                    </Space.Compact>

                    <Button icon={<Download size={14} />} size="small" onClick={handleExport}>
                        导出
                    </Button>

                    <Button icon={<Trash2 size={14} />} size="small" danger onClick={handleClear}>
                        清空
                    </Button>
                </Space>
            }
            className="h-full log-viewer-card"
            bodyStyle={{ padding: 0, height: 'calc(100% - 57px)', overflow: 'hidden' }}
        >
            <div
                className="h-full overflow-y-auto p-4 bg-gray-900 dark:bg-black font-mono text-sm"
                style={{ fontFamily: 'Consolas, Monaco, monospace' }}
            >
                {filteredLogs.length === 0 ? (
                    <div className="text-gray-400 text-center py-8">
                        {currentJobId ? '暂无日志' : '请先运行流程以查看日志'}
                    </div>
                ) : (
                    filteredLogs.map((log, index) => (
                        <div key={index} className="mb-2 text-gray-200">
                            <span className="text-gray-400">[{new Date(log.timestamp).toLocaleTimeString()}]</span>{' '}
                            <Tag color={getLevelColor(log.level)} className="font-bold">
                                {log.level}
                            </Tag>
                            {log.nodeId && <span className="text-blue-400">[{log.nodeId}]</span>}{' '}
                            <span>{log.message}</span>
                        </div>
                    ))
                )}
                <div ref={logsEndRef} />
            </div>
        </Card>
    )
}
