/**
 * Memory Settings Component - 记忆配置管理界面
 *
 * 功能：
 * 1. 显示当前记忆后端配置
 * 2. 提供记忆统计信息
 */

import { useEffect, useState } from 'react'
import { Card, Statistic, Row, Col, Tag, message, Empty } from 'antd'
import { Database, BarChart3, Settings as SettingsIcon } from 'lucide-react'
import { getMemoryConfig, type MemoryConfig } from '../services/api'

export default function MemorySettings() {
    const [config, setConfig] = useState<MemoryConfig | null>(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        loadMemoryInfo()
    }, [])

    const loadMemoryInfo = async () => {
        setLoading(true)
        try {
            const configRes = await getMemoryConfig()
            console.log('Memory Config Response:', configRes)
            setConfig(configRes)
        } catch (error) {
            console.error('Failed to load memory info:', error)
            message.error('加载记忆配置失败')
        } finally {
            setLoading(false)
        }
    }

    const getBackendDisplayName = (backend: string): string => {
        const names: Record<string, string> = {
            short_term: '短期记忆 (滑动窗口)',
            long_term: '长期记忆 (向量检索)',
            vdb: '向量数据库 (语义检索)',
            kv: '键值存储 (关键词检索)',
            graph: '图记忆 (关系推理)',
        }
        return names[backend] || backend
    }

    const getBackendColor = (backend: string): string => {
        const colors: Record<string, string> = {
            short_term: 'blue',
            long_term: 'green',
            vdb: 'green',
            kv: 'orange',
            graph: 'purple',
        }
        return colors[backend] || 'default'
    }

    return (
        <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
            <h2 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Database size={24} />
                记忆管理
            </h2>

            {/* 当前配置 */}
            <Card
                title={
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <SettingsIcon size={16} />
                        当前配置
                    </span>
                }
                loading={loading}
                style={{ marginBottom: '24px' }}
            >
                {config ? (
                    <Row gutter={16}>
                        <Col span={8}>
                            <Statistic
                                title="记忆状态"
                                value={config.enabled ? '已启用' : '已禁用'}
                                valueStyle={{ color: config.enabled ? '#52c41a' : '#ff4d4f' }}
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="短期记忆容量"
                                value={config.short_term?.max_items || 20}
                                suffix="条"
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="长期记忆"
                                value={config.long_term?.enabled ? '已启用' : '已禁用'}
                                valueStyle={{ color: config.long_term?.enabled ? '#52c41a' : '#ff4d4f' }}
                            />
                        </Col>
                    </Row>
                ) : (
                    <Empty description="暂无配置信息" />
                )}
            </Card>

            {/* 可用后端 */}
            <Card
                title={
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <BarChart3 size={16} />
                        可用记忆后端
                    </span>
                }
                loading={loading}
                style={{ marginBottom: '24px' }}
            >
                {config?.backends && config.backends.length > 0 ? (
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {config.backends.map((backend) => (
                            <Tag key={backend} color={getBackendColor(backend)}>
                                {getBackendDisplayName(backend)}
                            </Tag>
                        ))}
                    </div>
                ) : (
                    <Empty description="暂无可用后端" />
                )}
            </Card>

            {/* 说明 */}
            <Card
                title="记忆后端说明"
                style={{ marginTop: '24px' }}
                bodyStyle={{ padding: '16px' }}
            >
                <div style={{ fontSize: '14px', lineHeight: '1.8' }}>
                    <p>
                        <Tag color="blue">短期记忆</Tag> - 使用滑动窗口机制，保留最近 N
                        条交互记录，适合短期上下文管理
                    </p>
                    <p>
                        <Tag color="green">长期记忆</Tag> -
                        使用向量嵌入存储重要信息，支持语义检索和长期知识保留
                    </p>
                    <p style={{ marginTop: '16px', color: '#888', fontSize: '12px' }}>
                        提示：记忆系统会自动管理对话上下文。短期记忆用于当前会话的上下文理解，
                        长期记忆用于跨会话的知识积累。
                    </p>
                </div>
            </Card>

            {/* 调试信息 */}
            <Card title="Debug Info" style={{ marginTop: '24px' }}>
                <pre>{JSON.stringify(config, null, 2)}</pre>
            </Card>
        </div>
    )
}
