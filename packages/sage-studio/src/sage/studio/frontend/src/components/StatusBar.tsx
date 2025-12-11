import { Space, Tag, Button } from 'antd'
import { Activity, Circle, Terminal } from 'lucide-react'
import { useFlowStore } from '../store/flowStore'

interface StatusBarProps {
    showLogs: boolean
    onToggleLogs: () => void
}

export default function StatusBar({ showLogs, onToggleLogs }: StatusBarProps) {
    const nodes = useFlowStore((state) => state.nodes)
    const edges = useFlowStore((state) => state.edges)

    return (
        <div className="status-bar">
            <Space>
                <Activity size={14} />
                <span>就绪</span>
                <Button
                    type={showLogs ? 'primary' : 'default'}
                    size="small"
                    icon={<Terminal size={14} />}
                    onClick={onToggleLogs}
                >
                    {showLogs ? '隐藏日志' : '显示日志'}
                </Button>
            </Space>

            <Space size="large">
                <Space>
                    <Circle size={10} fill="#52c41a" stroke="#52c41a" />
                    <span>节点: {nodes.length}</span>
                </Space>
                <Space>
                    <Circle size={10} fill="#1890ff" stroke="#1890ff" />
                    <span>连接: {edges.length}</span>
                </Space>
                <Tag color="#1890ff">SAGE-alpha</Tag>
            </Space>
        </div>
    )
}
