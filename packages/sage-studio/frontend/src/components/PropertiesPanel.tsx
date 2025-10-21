import { Form, Input, Switch, Divider, InputNumber, Select } from 'antd'
import { useFlowStore } from '../store/flowStore'

export default function PropertiesPanel() {
    const selectedNode = useFlowStore((state) => state.selectedNode)
    const updateNode = useFlowStore((state) => state.updateNode)

    // 获取节点的配置参数定义
    const getNodeConfig = () => {
        // TODO: 从后端 API 获取节点配置定义
        // Issue URL: https://github.com/intellistream/SAGE/issues/984
        // 这里先返回一些示例配置
        return {
            text: [
                { name: 'input_text', label: '输入文本', type: 'textarea', defaultValue: '' },
                { name: 'max_length', label: '最大长度', type: 'number', defaultValue: 100 },
            ],
            api: [
                { name: 'url', label: 'API地址', type: 'text', defaultValue: '' },
                { name: 'method', label: '请求方法', type: 'select', options: ['GET', 'POST', 'PUT', 'DELETE'], defaultValue: 'GET' },
            ],
            // 可以为其他节点类型添加配置
        }
    }

    if (!selectedNode) {
        return (
            <div className="properties-panel">
                <div className="text-center py-8 text-gray-500">
                    <p>选择一个节点查看属性</p>
                </div>
            </div>
        )
    }

    const handleValueChange = (field: string, value: any) => {
        updateNode(selectedNode.id, {
            [field]: value,
        })
    }

    return (
        <div className="properties-panel">
            <div className="mb-4">
                <h3 className="text-lg font-semibold">节点属性</h3>
                <p className="text-sm text-gray-500">{selectedNode.data.label}</p>
            </div>

            <Divider />

            <Form layout="vertical" size="small">
                <Form.Item label="节点名称">
                    <Input
                        value={selectedNode.data.label}
                        onChange={(e) => handleValueChange('label', e.target.value)}
                        placeholder="输入节点名称"
                    />
                </Form.Item>

                <Form.Item label="节点ID">
                    <Input value={selectedNode.data.nodeId} disabled />
                </Form.Item>

                <Form.Item label="描述">
                    <Input.TextArea
                        value={selectedNode.data.description || ''}
                        onChange={(e) => handleValueChange('description', e.target.value)}
                        placeholder="输入节点描述"
                        rows={3}
                    />
                </Form.Item>

                <Divider>配置参数</Divider>

                {/* 动态渲染配置项 */}
                {(() => {
                    const nodeType = selectedNode.data.nodeId
                    const configs = getNodeConfig()
                    const nodeConfigs = configs[nodeType as keyof typeof configs] || []

                    if (nodeConfigs.length === 0) {
                        return (
                            <div className="text-sm text-gray-500">
                                <p>该节点类型暂无可配置参数</p>
                            </div>
                        )
                    }

                    return nodeConfigs.map((config: any) => {
                        const value = selectedNode.data[config.name] ?? config.defaultValue

                        return (
                            <Form.Item key={config.name} label={config.label}>
                                {config.type === 'text' && (
                                    <Input
                                        value={value}
                                        onChange={(e) => handleValueChange(config.name, e.target.value)}
                                        placeholder={`请输入${config.label}`}
                                    />
                                )}

                                {config.type === 'textarea' && (
                                    <Input.TextArea
                                        value={value}
                                        onChange={(e) => handleValueChange(config.name, e.target.value)}
                                        placeholder={`请输入${config.label}`}
                                        rows={3}
                                    />
                                )}

                                {config.type === 'number' && (
                                    <InputNumber
                                        value={value}
                                        onChange={(val) => handleValueChange(config.name, val)}
                                        className="w-full"
                                    />
                                )}

                                {config.type === 'select' && (
                                    <Select
                                        value={value}
                                        onChange={(val) => handleValueChange(config.name, val)}
                                        className="w-full"
                                    >
                                        {config.options?.map((opt: string) => (
                                            <Select.Option key={opt} value={opt}>
                                                {opt}
                                            </Select.Option>
                                        ))}
                                    </Select>
                                )}
                            </Form.Item>
                        )
                    })
                })()}

                <Form.Item label="启用" className="mt-4">
                    <Switch
                        checked={selectedNode.data.enabled !== false}
                        onChange={(checked) => handleValueChange('enabled', checked)}
                    />
                </Form.Item>
            </Form>

            <Divider />

            <div className="text-xs text-gray-400">
                <p>位置: ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})</p>
                <p>ID: {selectedNode.id}</p>
            </div>
        </div>
    )
}
