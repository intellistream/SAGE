import { useState, useEffect } from 'react'
import { Modal, Form, Input, Button, Space, message, Popconfirm, Tabs } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { getEnvVars, updateEnvVars } from '../services/api'
import MemorySettings from './MemorySettings'

interface SettingsProps {
    open: boolean
    onClose: () => void
}

export default function Settings({ open, onClose }: SettingsProps) {
    const [form] = Form.useForm()
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)

    // 加载环境变量
    useEffect(() => {
        if (open) {
            loadEnvVars()
        }
    }, [open])

    const loadEnvVars = async () => {
        setLoading(true)
        try {
            const envVars = await getEnvVars()
            // 将对象转换为表单字段数组
            const entries = Object.entries(envVars).map(([key, value]) => ({ key, value }))
            form.setFieldsValue({ envVars: entries })
        } catch (error) {
            message.error('加载环境变量失败')
        } finally {
            setLoading(false)
        }
    }

    const handleSave = async () => {
        try {
            const values = await form.validateFields()
            setSaving(true)

            // 将表单数组转换为对象
            const envVarsArray = values.envVars || []
            const envVarsObject: Record<string, string> = {}

            envVarsArray.forEach((item: { key: string; value: string }) => {
                if (item.key && item.key.trim()) {
                    envVarsObject[item.key.trim()] = item.value || ''
                }
            })

            await updateEnvVars(envVarsObject)
            message.success('环境变量保存成功')
            onClose()
        } catch (error) {
            if (error instanceof Error) {
                message.error(`保存失败: ${error.message}`)
            }
        } finally {
            setSaving(false)
        }
    }

    return (
        <Modal
            title="系统设置"
            open={open}
            onCancel={onClose}
            footer={null}
            width={900}
        >
            <Tabs defaultActiveKey="env">
                <Tabs.TabPane tab="环境变量" key="env">
                    <div className="py-4">
                        <p className="text-sm text-gray-600 mb-4">
                            配置流程运行时所需的环境变量，例如 API 密钥、服务端点等。
                        </p>

                        {loading ? (
                            <div className="text-center py-8 text-gray-400">加载中...</div>
                        ) : (
                            <Form form={form} layout="vertical">
                                <Form.List name="envVars">
                                    {(fields, { add, remove }) => (
                                        <>
                                            {fields.map(({ key, name, ...restField }) => (
                                                <Space
                                                    key={key}
                                                    className="flex items-start w-full mb-2"
                                                    align="baseline"
                                                >
                                                    <Form.Item
                                                        {...restField}
                                                        name={[name, 'key']}
                                                        rules={[
                                                            { required: true, message: '请输入变量名' },
                                                        ]}
                                                        className="mb-0 flex-1"
                                                    >
                                                        <Input placeholder="变量名 (例如: OPENAI_API_KEY)" />
                                                    </Form.Item>

                                                    <Form.Item
                                                        {...restField}
                                                        name={[name, 'value']}
                                                        className="mb-0 flex-1"
                                                    >
                                                        <Input.Password
                                                            placeholder="变量值"
                                                            autoComplete="off"
                                                        />
                                                    </Form.Item>

                                                    <Popconfirm
                                                        title="确定删除此环境变量？"
                                                        onConfirm={() => remove(name)}
                                                        okText="确定"
                                                        cancelText="取消"
                                                    >
                                                        <Button
                                                            type="text"
                                                            danger
                                                            icon={<DeleteOutlined />}
                                                        />
                                                    </Popconfirm>
                                                </Space>
                                            ))}

                                            <Form.Item className="mb-0">
                                                <Button
                                                    type="dashed"
                                                    onClick={() => add()}
                                                    block
                                                    icon={<PlusOutlined />}
                                                >
                                                    添加环境变量
                                                </Button>
                                            </Form.Item>
                                        </>
                                    )}
                                </Form.List>
                            </Form>
                        )}

                        <div className="mt-4 flex justify-end gap-2">
                            <Button onClick={onClose}>取消</Button>
                            <Button type="primary" onClick={handleSave} loading={saving}>
                                保存
                            </Button>
                        </div>
                    </div>
                </Tabs.TabPane>

                <Tabs.TabPane tab="记忆管理" key="memory">
                    <MemorySettings />
                </Tabs.TabPane>
            </Tabs>
        </Modal>
    )
}
