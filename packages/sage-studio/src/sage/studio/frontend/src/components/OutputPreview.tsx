import { useState, useEffect } from 'react'
import { Card, Spin, Alert, Tabs, Empty, Typography } from 'antd'
import { FileJson, Code } from 'lucide-react'
import { getNodeOutput } from '../services/api'

const { Paragraph } = Typography
const { TabPane } = Tabs

interface OutputPreviewProps {
    nodeId: string
    flowId?: string
}

export default function OutputPreview({ nodeId, flowId }: OutputPreviewProps) {
    const [output, setOutput] = useState<any>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (!flowId) {
            setOutput(null)
            return
        }

        loadOutput()
    }, [nodeId, flowId])

    const loadOutput = async () => {
        if (!flowId) return

        try {
            setLoading(true)
            setError(null)
            const data = await getNodeOutput(flowId, nodeId)
            setOutput(data)
        } catch (err) {
            setError(err instanceof Error ? err.message : '加载输出数据失败')
        } finally {
            setLoading(false)
        }
    }

    if (!flowId) {
        return (
            <Empty
                description="请先保存并运行 Flow 以查看输出"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
        )
    }

    if (loading) {
        return (
            <div className="flex justify-center items-center py-8">
                <Spin tip="加载输出数据..." />
            </div>
        )
    }

    if (error) {
        return (
            <Alert
                type="warning"
                message="暂无输出数据"
                description={error}
                showIcon
            />
        )
    }

    if (!output) {
        return (
            <Empty
                description="该节点尚未执行或无输出数据"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
        )
    }

    const renderOutput = () => {
        const { data, type, timestamp } = output

        return (
            <div>
                <div className="mb-4 text-xs text-gray-500">
                    最后更新: {new Date(timestamp).toLocaleString()}
                </div>

                <Tabs defaultActiveKey="formatted">
                    <TabPane
                        tab={
                            <span>
                                <FileJson className="inline mr-1" size={14} />
                                格式化
                            </span>
                        }
                        key="formatted"
                    >
                        {type === 'json' && (
                            <pre className="bg-gray-50 p-4 rounded overflow-auto max-h-96">
                                {JSON.stringify(data, null, 2)}
                            </pre>
                        )}
                        {type === 'text' && (
                            <Paragraph className="bg-gray-50 p-4 rounded overflow-auto max-h-96">
                                {data}
                            </Paragraph>
                        )}
                        {type === 'error' && (
                            <Alert type="error" message="执行错误" description={data} />
                        )}
                    </TabPane>

                    <TabPane
                        tab={
                            <span>
                                <Code className="inline mr-1" size={14} />
                                原始数据
                            </span>
                        }
                        key="raw"
                    >
                        <pre className="bg-gray-50 p-4 rounded overflow-auto max-h-96">
                            {JSON.stringify(output, null, 2)}
                        </pre>
                    </TabPane>
                </Tabs>
            </div>
        )
    }

    return <Card size="small">{renderOutput()}</Card>
}
