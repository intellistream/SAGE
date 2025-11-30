/**
 * Memory Settings Component - 记忆配置管理界面
 *
 * 功能：
 * 1. 显示当前记忆后端配置
 * 2. 查看各会话的记忆使用情况
 * 3. 提供记忆统计信息
 */

import { useEffect, useState } from 'react'
import { Card, Progress, Statistic, Row, Col, Table, Tag, Space, message } from 'antd'
import { Database, BarChart3, Settings as SettingsIcon } from 'lucide-react'
import { getMemoryConfig, getMemoryStats } from '../services/api'

interface MemoryConfig {
    backend: string
    max_dialogs: number
    config: Record<string, any>
    available_backends: string[]
}

interface MemoryStats {
    total_sessions: number
    sessions: Record<
        string,
        {
            backend: string
            dialog_count?: number
            max_dialogs?: number
            usage_percent?: number
            collection_name?: string
            has_index?: boolean
        }
    >
}

export default function MemorySettings() {
    const [config, setConfig] = useState<MemoryConfig | null>(null)
    const [stats, setStats] = useState<MemoryStats | null>(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        loadMemoryInfo()
    }, [])

    const loadMemoryInfo = async () => {
        setLoading(true)
        try {
            const [configRes, statsRes] = await Promise.all([
                getMemoryConfig(),
                getMemoryStats(),
            ])
            setConfig(configRes)
            setStats(statsRes)
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
            vdb: '向量数据库 (语义检索)',
            kv: '键值存储 (关键词检索)',
            graph: '图记忆 (关系推理)',
        }
        return names[backend] || backend
    }

    const getBackendColor = (backend: string): string => {
        const colors: Record<string, string> = {
            short_term: 'blue',
            vdb: 'green',
            kv: 'orange',
            graph: 'purple',
        }
        return colors[backend] || 'default'
    }

    const sessionColumns = [
        {
            title: '会话 ID',
            dataIndex: 'session_id',
            key: 'session_id',
            width: 280,
            render: (text: string) => (
                <span style={{ fontFamily: 'monospace', fontSize: '0.85em' }}>{text}</span>
            ),
        },
        {
            title: '后端类型',
            dataIndex: 'backend',
            key: 'backend',
            render: (backend: string) => (
                <Tag color={getBackendColor(backend)}>{getBackendDisplayName(backend)}</Tag>
            ),
        },
        {
            title: '记忆使用',
            key: 'usage',
            render: (_: any, record: any) => {
                if (record.backend === 'short_term') {
                    return (
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <div>
                                {record.dialog_count} / {record.max_dialogs} 轮对话
                            </div>
                            <Progress
                                percent={Math.round(record.usage_percent || 0)}
                                size="small"
                                status={record.usage_percent > 80 ? 'exception' : 'active'}
                            />
                        </Space>
                    )
                } else {
                    return (
                        <div>
                            <div>集合: {record.collection_name}</div>
                            <div>索引: {record.has_index ? '✅ 已创建' : '❌ 未创建'}</div>
                        </div>
                    )
                }
            },
        },
    ]

    const tableData = stats
        ? Object.entries(stats.sessions).map(([session_id, data]) => ({
              key: session_id,
              session_id,
              ...data,
          }))
        : []

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
                {config && (
                    <Row gutter={16}>
                        <Col span={8}>
                            <Statistic
                                title="记忆后端"
                                value={getBackendDisplayName(config.backend)}
                                prefix={<Database size={16} />}
                            />
                        </Col>
                        {config.backend === 'short_term' && (
                            <Col span={8}>
                                <Statistic
                                    title="最大对话轮数"
                                    value={config.max_dialogs}
                                    suffix="轮"
                                />
                            </Col>
                        )}
                        {config.backend === 'vdb' && config.config.embedding_model && (
                            <>
                                <Col span={8}>
                                    <Statistic
                                        title="嵌入模型"
                                        value={config.config.embedding_model}
                                        valueStyle={{ fontSize: '14px' }}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Statistic
                                        title="向量维度"
                                        value={config.config.embedding_dim || 384}
                                    />
                                </Col>
                            </>
                        )}
                    </Row>
                )}
            </Card>

            {/* 统计信息 */}
            <Card
                title={
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <BarChart3 size={16} />
                        使用统计
                    </span>
                }
                loading={loading}
                style={{ marginBottom: '24px' }}
            >
                {stats && (
                    <Row gutter={16}>
                        <Col span={8}>
                            <Statistic
                                title="活跃会话数"
                                value={stats.total_sessions}
                                suffix="个"
                            />
                        </Col>
                        <Col span={8}>
                            <Statistic
                                title="记忆后端类型"
                                value={config?.backend || 'unknown'}
                                valueStyle={{ fontSize: '16px' }}
                            />
                        </Col>
                    </Row>
                )}
            </Card>

            {/* 会话详情 */}
            <Card
                title="会话记忆详情"
                loading={loading}
                extra={
                    <span style={{ fontSize: '14px', color: '#888' }}>
                        共 {stats?.total_sessions || 0} 个会话
                    </span>
                }
            >
                <Table
                    columns={sessionColumns}
                    dataSource={tableData}
                    pagination={{ pageSize: 10 }}
                    size="small"
                />
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
                        轮对话，适合短期上下文管理
                    </p>
                    <p>
                        <Tag color="green">向量数据库</Tag> -
                        使用向量嵌入和语义检索，支持长期记忆和相关内容查找
                    </p>
                    <p>
                        <Tag color="orange">键值存储</Tag> -
                        使用关键词索引（BM25s），支持快速文本检索
                    </p>
                    <p>
                        <Tag color="purple">图记忆</Tag> -
                        使用图结构存储实体和关系，支持关系推理和知识图谱
                    </p>
                    <p style={{ marginTop: '16px', color: '#888', fontSize: '12px' }}>
                        💡 提示：记忆后端类型在 Gateway
                        启动时配置，当前版本不支持运行时切换。若需更换后端，请修改 Gateway
                        配置并重启服务。
                    </p>
                </div>
            </Card>
        </div>
    )
}
