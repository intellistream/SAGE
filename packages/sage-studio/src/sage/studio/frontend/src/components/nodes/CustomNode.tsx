import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Card } from 'antd'
import { PlayCircle, AlertCircle, CheckCircle } from 'lucide-react'

interface CustomNodeData {
    label: string
    nodeId: string
    status?: 'idle' | 'running' | 'success' | 'error'
    description?: string
}

function CustomNode({ data, selected }: NodeProps<CustomNodeData>) {
    const getStatusIcon = () => {
        switch (data.status) {
            case 'running':
                return <PlayCircle className="w-4 h-4 text-blue-500" />
            case 'success':
                return <CheckCircle className="w-4 h-4 text-green-500" />
            case 'error':
                return <AlertCircle className="w-4 h-4 text-red-500" />
            default:
                return null
        }
    }

    const getStatusClass = () => {
        if (selected) return 'custom-node selected'
        if (data.status === 'running') return 'custom-node running'
        if (data.status === 'error') return 'custom-node error'
        return 'custom-node'
    }

    return (
        <div className={getStatusClass()}>
            <Handle type="target" position={Position.Top} />
            <Card
                size="small"
                title={
                    <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-[--gemini-text-primary]">{data.label}</span>
                        {getStatusIcon()}
                    </div>
                }
                bordered={false}
                style={{ minWidth: 180 }}
                className="custom-node-card"
            >
                {data.description && (
                    <p className="text-xs text-[--gemini-text-secondary] mt-1">{data.description}</p>
                )}
                <div className="text-xs text-[--gemini-text-secondary] mt-2">
                    ID: {data.nodeId}
                </div>
            </Card>
            <Handle type="source" position={Position.Bottom} />
        </div>
    )
}

export default memo(CustomNode)
