import { Form, Input, Switch, Divider, InputNumber, Select, Tabs } from 'antd'
import { useState, useEffect } from 'react'
import { useFlowStore } from '../store/flowStore'
import { getNodes, type NodeDefinition, type ParameterConfig } from '../services/api'
import OutputPreview from './OutputPreview'

const { TabPane } = Tabs

export default function PropertiesPanel() {
    const selectedNode = useFlowStore((state) => state.selectedNode)
    const updateNode = useFlowStore((state) => state.updateNode)
    const [nodeDefinitions, setNodeDefinitions] = useState<NodeDefinition[]>([])

    // 加载节点定义
    useEffect(() => {
        const loadNodeDefinitions = async () => {
            try {
                console.log('📡 Loading node definitions...')
                const nodes = await getNodes()
                console.log('✅ Loaded nodes:', nodes.length)
                console.log('📋 Sample node:', nodes[0])
                setNodeDefinitions(nodes)
            } catch (error) {
                console.error('❌ Failed to load node definitions:', error)
            }
        }
        loadNodeDefinitions()
    }, [])

    // 获取当前节点的参数配置
    const getNodeParameters = (): ParameterConfig[] => {
        if (!selectedNode) return []

        const nodeId = selectedNode.data.nodeId

        // 调试日志
        console.log('🔍 PropertiesPanel Debug:')
        console.log('  - Selected nodeId:', nodeId)
        console.log('  - Available nodes:', nodeDefinitions.map(n => n.name))
        console.log('  - Node definitions count:', nodeDefinitions.length)

        const nodeDef = nodeDefinitions.find(n => n.name === nodeId)
        console.log('  - Found definition:', nodeDef ? `✅ ${nodeDef.name}` : '❌ Not found')
        console.log('  - Parameters:', nodeDef?.parameters?.length || 0)

        return nodeDef?.parameters || []
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

            <Tabs defaultActiveKey="config">
                <TabPane tab="配置" key="config">
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
                            const nodeParameters = getNodeParameters()

                            if (nodeParameters.length === 0) {
                                return (
                                    <div className="text-sm text-gray-500 text-center py-4">
                                        <p>该节点类型暂无可配置参数</p>
                                    </div>
                                )
                            }

                            return nodeParameters.map((param) => {
                                // 从节点的 config 对象中读取值，或使用默认值
                                const currentConfig = selectedNode.data.config || {}
                                const value = currentConfig[param.name] ?? param.defaultValue

                                const isRequired = param.required
                                const label = isRequired ? `${param.label} *` : param.label

                                return (
                                    <Form.Item
                                        key={param.name}
                                        label={label}
                                        help={param.description}
                                        required={isRequired}
                                    >
                                        {param.type === 'text' && (
                                            <Input
                                                value={value}
                                                onChange={(e) => {
                                                    const newConfig = { ...currentConfig, [param.name]: e.target.value }
                                                    handleValueChange('config', newConfig)
                                                }}
                                                placeholder={param.placeholder || `请输入${param.label}`}
                                            />
                                        )}

                                        {param.type === 'password' && (
                                            <Input.Password
                                                value={value}
                                                onChange={(e) => {
                                                    const newConfig = { ...currentConfig, [param.name]: e.target.value }
                                                    handleValueChange('config', newConfig)
                                                }}
                                                placeholder={param.placeholder || `请输入${param.label}`}
                                            />
                                        )}

                                        {param.type === 'textarea' && (
                                            <Input.TextArea
                                                value={value}
                                                onChange={(e) => {
                                                    const newConfig = { ...currentConfig, [param.name]: e.target.value }
                                                    handleValueChange('config', newConfig)
                                                }}
                                                placeholder={param.placeholder || `请输入${param.label}`}
                                                rows={4}
                                            />
                                        )}

                                        {param.type === 'number' && (
                                            <InputNumber
                                                value={value}
                                                onChange={(val) => {
                                                    const newConfig = { ...currentConfig, [param.name]: val }
                                                    handleValueChange('config', newConfig)
                                                }}
                                                min={param.min}
                                                max={param.max}
                                                step={param.step}
                                                className="w-full"
                                                placeholder={param.placeholder}
                                            />
                                        )}

                                        {param.type === 'select' && (
                                            <Select
                                                value={value}
                                                onChange={(val) => {
                                                    const newConfig = { ...currentConfig, [param.name]: val }
                                                    handleValueChange('config', newConfig)
                                                }}
                                                className="w-full"
                                                placeholder={param.placeholder || `请选择${param.label}`}
                                            >
                                                {param.options?.map((opt: string) => (
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
                </TabPane>

                <TabPane tab="输出预览" key="output">
                    <OutputPreview
                        nodeId={selectedNode.id}
                        flowId={selectedNode.data.flowId}
                    />
                </TabPane>
            </Tabs>

            <Divider />

            <div className="text-xs text-gray-400">
                <p>位置: ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})</p>
                <p>ID: {selectedNode.id}</p>
            </div>
        </div>
    )
}
