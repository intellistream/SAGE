import { Space, Tag } from 'antd'
import { Activity, Circle } from 'lucide-react'
import { useFlowStore } from '../store/flowStore'

export default function StatusBar() {
    const nodes = useFlowStore((state) => state.nodes)
    const edges = useFlowStore((state) => state.edges)

    return (
        <div className="status-bar">
            <Space>
                <Activity size={14} />
                <span>就绪</span>
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
                <Tag color="#1890ff">SAGE Studio v2.0-alpha</Tag>
            </Space>
        </div>
    )
}
