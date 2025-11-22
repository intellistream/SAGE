/**
 * Fine-tune Panel Component - Model fine-tuning interface
 */

import { useEffect, useState } from 'react'
import {
    Button,
    Card,
    Form,
    InputNumber,
    Progress,
    Select,
    Table,
    Tag,
    Upload,
    message,
    Space,
    Typography,
    Divider,
    Switch,
    Collapse,
    Radio,
    Modal,
    Alert,
} from 'antd'
import {
    Upload as UploadIcon,
    Play,
    CheckCircle,
    XCircle,
    Clock,
    Cpu,
    AlertCircle,
    Download,
} from 'lucide-react'
import type { UploadFile, UploadProps } from 'antd'

const { Title, Text, Paragraph } = Typography
const { Panel } = Collapse
const { Option } = Select

interface FinetuneTask {
    task_id: string
    model_name: string
    dataset_path: string
    output_dir: string
    status: 'pending' | 'queued' | 'preparing' | 'training' | 'completed' | 'failed' | 'cancelled'
    progress: number
    current_epoch: number
    total_epochs: number
    loss: number
    created_at: string
    started_at?: string
    completed_at?: string
    error_message?: string
    logs: string[]
    config: Record<string, any>
}

interface Model {
    name: string
    type: 'base' | 'finetuned'
    description: string
    task_id?: string
    created_at?: string
}

export default function FinetunePanel() {
    const [form] = Form.useForm()
    const [tasks, setTasks] = useState<FinetuneTask[]>([])
    const [models, setModels] = useState<Model[]>([])
    const [currentModel, setCurrentModel] = useState<string>('')
    const [uploadedFile, setUploadedFile] = useState<string | null>(null)
    const [fileList, setFileList] = useState<UploadFile[]>([])
    const [loading, setLoading] = useState(false)
    const [refreshInterval, setRefreshInterval] = useState<number | null>(null)
    const [gpuInfo, setGpuInfo] = useState<{
        available: boolean
        count: number
        devices: Array<{ id: number; name: string; memory_gb: number }>
        recommendation: string
    } | null>(null)

    useEffect(() => {
        loadTasks()
        loadModels()
        loadCurrentModel()
        loadGpuInfo()

        // Auto-refresh every 3 seconds when training
        const interval = setInterval(() => {
            loadTasks()
        }, 3000)
        setRefreshInterval(interval as unknown as number)

        return () => {
            if (refreshInterval) clearInterval(refreshInterval)
        }
    }, [])

    const loadGpuInfo = async () => {
        try {
            const response = await fetch('/api/system/gpu-info')
            if (response.ok) {
                const data = await response.json()
                setGpuInfo(data)
            }
        } catch (error) {
            console.error('Failed to load GPU info:', error)
        }
    }

    const loadTasks = async () => {
        try {
            const response = await fetch('/api/finetune/tasks')
            if (response.ok) {
                const data = await response.json()
                setTasks(data)
            }
        } catch (error) {
            console.error('Failed to load tasks:', error)
        }
    }

    const loadModels = async () => {
        try {
            const response = await fetch('/api/finetune/models')
            if (response.ok) {
                const data = await response.json()
                setModels(data)
            }
        } catch (error) {
            console.error('Failed to load models:', error)
        }
    }

    const loadCurrentModel = async () => {
        try {
            const response = await fetch('/api/finetune/current-model')
            if (response.ok) {
                const data = await response.json()
                setCurrentModel(data.current_model)
            }
        } catch (error) {
            console.error('Failed to load current model:', error)
        }
    }

    const uploadProps: UploadProps = {
        name: 'file',
        accept: '.json,.jsonl',
        maxCount: 1,
        fileList,
        customRequest: async ({ file, onSuccess, onError }) => {
            const formData = new FormData()
            formData.append('file', file as File)

            try {
                const response = await fetch('/api/finetune/upload-dataset', {
                    method: 'POST',
                    body: formData,
                })

                if (response.ok) {
                    const data = await response.json()
                    setUploadedFile(data.file_path)
                    message.success(`${data.filename} 上传成功`)
                    onSuccess?.(data)
                } else {
                    throw new Error('Upload failed')
                }
            } catch (error) {
                message.error('上传失败')
                onError?.(error as Error)
            }
        },
        onChange: (info) => {
            setFileList(info.fileList.slice(-1))
        },
    }

    const handleCreateTask = async (values: any) => {
        if (!uploadedFile) {
            message.error('请先上传数据集')
            return
        }

        setLoading(true)
        try {
            const response = await fetch('/api/finetune/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...values,
                    dataset_file: uploadedFile,
                }),
            })

            if (response.ok) {
                const data = await response.json()

                // 显示 OOM 警告（如果有）
                if (data.warnings && data.warnings.length > 0) {
                    Modal.warning({
                        title: '⚠️ 显存警告',
                        content: (
                            <div className="space-y-2">
                                {data.warnings.map((warning: string, index: number) => (
                                    <div key={index}>{warning}</div>
                                ))}
                                <div className="mt-4 text-gray-600">
                                    任务已创建，但建议重新配置参数以降低 OOM 风险。
                                </div>
                            </div>
                        ),
                        okText: '知道了',
                    })
                }

                message.success('微调任务已创建并开始训练')
                form.resetFields()
                setFileList([])
                setUploadedFile(null)
                loadTasks()
            } else {
                const error = await response.json()
                message.error(error.detail || '创建任务失败')
            }
        } catch (error) {
            message.error('创建任务失败')
        } finally {
            setLoading(false)
        }
    }

    const handleSwitchModel = async (modelPath: string) => {
        try {
            const response = await fetch(
                `/api/finetune/switch-model?model_path=${encodeURIComponent(modelPath)}`,
                { method: 'POST' }
            )

            if (response.ok) {
                message.success('模型已切换')
                loadCurrentModel()
            } else {
                message.error('切换模型失败')
            }
        } catch (error) {
            message.error('切换模型失败')
        }
    }

    const handlePrepareSageDocs = async () => {
        const hide = message.loading('正在下载 SAGE 文档并准备训练数据...', 0)
        try {
            const response = await fetch('/api/finetune/prepare-sage-docs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            })

            if (response.ok) {
                const data = await response.json()
                setUploadedFile(data.data_file)
                message.success(`SAGE 文档已准备完成！共 ${data.stats.total_samples} 条训练数据`)
            } else {
                const error = await response.json().catch(() => ({ detail: response.statusText }))
                message.error(error.detail || '准备文档失败')
                console.error('Prepare docs error:', error)
            }
        } catch (error) {
            console.error('Prepare docs exception:', error)
            message.error(`准备文档失败: ${error instanceof Error ? error.message : '未知错误'}`)
        } finally {
            hide()
        }
    }

    const handleUseAsBackend = async (taskId: string) => {
        Modal.confirm({
            title: '切换为对话后端',
            content: '确定要将此微调模型设置为 Studio 的对话后端吗？当前对话将使用此模型。',
            okText: '确定',
            cancelText: '取消',
            onOk: async () => {
                try {
                    const response = await fetch(
                        '/api/finetune/use-as-backend',
                        {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ task_id: taskId }),
                        }
                    )

                    if (response.ok) {
                        const data = await response.json()
                        message.success(`✅ ${data.message}`)
                        message.info('请在对话面板测试微调后的模型效果', 5)
                    } else {
                        const error = await response.json()
                        message.error(error.detail || '切换后端失败')
                    }
                } catch (error) {
                    message.error('切换后端失败')
                }
            },
        })
    }

    const getStatusTag = (status: FinetuneTask['status']) => {
        const statusConfig = {
            pending: { color: 'default', icon: <Clock className="w-3 h-3" />, text: '等待中' },
            queued: { color: 'warning', icon: <Clock className="w-3 h-3" />, text: '排队中' },
            preparing: { color: 'processing', icon: <Cpu className="w-3 h-3" />, text: '准备中' },
            training: { color: 'processing', icon: <Cpu className="w-3 h-3" />, text: '训练中' },
            completed: {
                color: 'success',
                icon: <CheckCircle className="w-3 h-3" />,
                text: '已完成',
            },
            failed: { color: 'error', icon: <XCircle className="w-3 h-3" />, text: '失败' },
            cancelled: { color: 'default', icon: <AlertCircle className="w-3 h-3" />, text: '已取消' },
        }

        const config = statusConfig[status]
        return (
            <Tag color={config.color} icon={config.icon}>
                {config.text}
            </Tag>
        )
    }

    const taskColumns = [
        {
            title: '任务 ID',
            dataIndex: 'task_id',
            key: 'task_id',
            width: 200,
            render: (text: string) => <Text code>{text}</Text>,
        },
        {
            title: '基础模型',
            dataIndex: 'model_name',
            key: 'model_name',
            width: 200,
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: (status: FinetuneTask['status']) => getStatusTag(status),
        },
        {
            title: '进度',
            key: 'progress',
            width: 200,
            render: (_: any, record: FinetuneTask) => (
                <div>
                    <Progress
                        percent={Math.round(record.progress)}
                        size="small"
                        status={record.status === 'failed' ? 'exception' : 'active'}
                    />
                    <Text type="secondary" className="text-xs">
                        Epoch {record.current_epoch}/{record.total_epochs} • Loss: {record.loss.toFixed(4)}
                    </Text>
                </div>
            ),
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 150,
            render: (text: string) => new Date(text).toLocaleString('zh-CN'),
        },
        {
            title: '操作',
            key: 'action',
            width: 280,
            render: (_: any, record: FinetuneTask) => (
                <Space>
                    {record.status === 'completed' && (
                        <>
                            <Button
                                size="small"
                                type="primary"
                                onClick={() => handleSwitchModel(record.output_dir)}
                            >
                                使用此模型
                            </Button>
                            <Button
                                size="small"
                                type="default"
                                onClick={() => handleUseAsBackend(record.task_id)}
                            >
                                设为后端
                            </Button>
                            <Button
                                size="small"
                                icon={<Download className="w-3 h-3" />}
                                onClick={() => handleDownloadModel(record.task_id)}
                            >
                                下载
                            </Button>
                        </>
                    )}
                    {(record.status === 'training' || record.status === 'preparing' || record.status === 'queued') && (
                        <Button
                            size="small"
                            danger
                            onClick={() => handleCancelTask(record.task_id)}
                        >
                            取消
                        </Button>
                    )}
                    {(record.status === 'failed' || record.status === 'completed' || record.status === 'cancelled') && (
                        <Button
                            size="small"
                            danger
                            icon={<XCircle className="w-3 h-3" />}
                            onClick={() => handleDeleteTask(record.task_id)}
                        >
                            删除
                        </Button>
                    )}
                </Space>
            ),
        },
    ]

    const handleDownloadModel = async (taskId: string) => {
        try {
            const response = await fetch(`/api/finetune/tasks/${taskId}/download`)
            if (response.ok) {
                const blob = await response.blob()
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `${taskId}_finetuned_model.tar.gz`
                document.body.appendChild(a)
                a.click()
                window.URL.revokeObjectURL(url)
                document.body.removeChild(a)
                message.success('模型下载已开始')
            } else {
                message.error('下载失败')
            }
        } catch (error) {
            message.error('下载失败')
        }
    }

    const handleDeleteTask = async (taskId: string) => {
        Modal.confirm({
            title: '确认删除',
            content: '确定要删除此任务吗？此操作无法撤销。',
            okText: '删除',
            okType: 'danger',
            cancelText: '取消',
            async onOk() {
                try {
                    const response = await fetch(`/api/finetune/tasks/${taskId}`, {
                        method: 'DELETE',
                    })
                    if (response.ok) {
                        message.success('任务已删除')
                        loadTasks() // 刷新任务列表
                    } else {
                        const error = await response.json().catch(() => ({ detail: '删除失败' }))
                        message.error(error.detail || '删除失败')
                    }
                } catch (error) {
                    message.error('删除失败')
                }
            },
        })
    }

    const handleCancelTask = async (taskId: string) => {
        Modal.confirm({
            title: '确认取消',
            content: '确定要取消此任务吗？训练进度将会丢失。',
            okText: '取消任务',
            okType: 'danger',
            cancelText: '继续训练',
            async onOk() {
                try {
                    const response = await fetch(`/api/finetune/tasks/${taskId}/cancel`, {
                        method: 'POST',
                    })
                    if (response.ok) {
                        message.success('任务已取消')
                        loadTasks() // 刷新任务列表
                    } else {
                        const error = await response.json().catch(() => ({ detail: '取消失败' }))
                        message.error(error.detail || '取消失败')
                    }
                } catch (error) {
                    message.error('取消失败')
                }
            },
        })
    }

    return (
        <div className="h-full overflow-auto p-6 bg-gray-50">
            <div className="max-w-7xl mx-auto space-y-6">
                <div>
                    <Title level={2}>🔧 模型微调</Title>
                    <Paragraph type="secondary">
                        使用自定义数据微调 LLM 模型，提升特定任务的性能。微调后的模型可直接用于 RAG Pipeline。
                        <br />
                        💡 <Text strong>{gpuInfo ? gpuInfo.recommendation : '正在检测 GPU...'}</Text>
                    </Paragraph>
                </div>

                {/* Current Model */}
                <Card>
                    <Space direction="vertical" className="w-full">
                        <Text strong>当前使用的模型</Text>
                        <div className="flex items-center justify-between">
                            <Text code className="text-lg" style={{ wordBreak: 'break-all' }}>
                                {currentModel}
                            </Text>
                            <Select
                                value={currentModel}
                                onChange={handleSwitchModel}
                                style={{ width: 400 }}
                                placeholder="切换模型"
                                optionLabelProp="label"
                            >
                                {models.map((model) => (
                                    <Option
                                        key={model.name}
                                        value={model.name}
                                        label={
                                            <span style={{ fontSize: '13px' }}>
                                                {model.name.length > 35 ? `${model.name.substring(0, 35)}...` : model.name}
                                            </span>
                                        }
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                                            <span style={{
                                                fontSize: '13px',
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap',
                                                flex: 1
                                            }}>
                                                {model.name}
                                            </span>
                                            <Tag color={model.type === 'base' ? 'blue' : 'green'} style={{ margin: 0 }}>
                                                {model.type === 'base' ? '基础' : '微调'}
                                            </Tag>
                                        </div>
                                    </Option>
                                ))}
                            </Select>
                        </div>
                    </Space>
                </Card>

                {/* Create Fine-tune Task */}
                <Card title="创建微调任务">
                    <Form
                        form={form}
                        layout="vertical"
                        onFinish={handleCreateTask}
                        initialValues={{
                            model_name: 'Qwen/Qwen2.5-7B-Instruct',
                            num_epochs: 3,
                            batch_size: 1,
                            gradient_accumulation_steps: 16,
                            learning_rate: 0.00005,
                            max_length: 1024,
                            load_in_8bit: true,
                        }}
                    >
                        <Form.Item
                            label="基础模型"
                            name="model_name"
                            tooltip="选择要微调的基础模型（推荐使用 1.5B 模型适配 RTX 3060）"
                            rules={[{ required: true }]}
                        >
                            <Select placeholder="选择基础模型" style={{ width: '100%' }}>
                                <Option value="Qwen/Qwen2.5-Coder-1.5B-Instruct">
                                    <div style={{ lineHeight: '1.4' }}>
                                        <div style={{ fontSize: '14px', marginBottom: '2px' }}>✨ Qwen 2.5 Coder 1.5B (推荐)</div>
                                        <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                                            显存: 6-8GB | 时间: 2-4h
                                        </Text>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-Coder-0.5B-Instruct">
                                    <div style={{ lineHeight: '1.4' }}>
                                        <div style={{ fontSize: '14px', marginBottom: '2px' }}>🚀 Qwen 2.5 Coder 0.5B (超快)</div>
                                        <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                                            显存: 2-4GB | 时间: 1-2h | ✅ 推荐新手
                                        </Text>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-Coder-1.5B-Instruct">
                                    <div style={{ lineHeight: '1.4' }}>
                                        <div style={{ fontSize: '14px', marginBottom: '2px' }}>✨ Qwen 2.5 Coder 1.5B</div>
                                        <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                                            显存: 4-6GB | 时间: 2-4h | ✅ RTX 3060
                                        </Text>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-0.5B-Instruct">
                                    <div style={{ lineHeight: '1.4' }}>
                                        <div style={{ fontSize: '14px', marginBottom: '2px' }}>🚀 Qwen 2.5 0.5B (超快)</div>
                                        <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                                            显存: 2-4GB | 时间: 1-2h
                                        </Text>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-1.5B-Instruct">
                                    <div style={{ lineHeight: '1.4' }}>
                                        <div style={{ fontSize: '14px', marginBottom: '2px' }}>💬 Qwen 2.5 1.5B (通用)</div>
                                        <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                                            显存: 4-6GB | 时间: 2-4h
                                        </Text>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-3B-Instruct">
                                    <div style={{ lineHeight: '1.4' }}>
                                        <div style={{ fontSize: '14px', marginBottom: '2px' }}>⚡ Qwen 2.5 3B (高级)</div>
                                        <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                                            显存: 8-10GB | 时间: 4-6h | ⚠️ 可能 OOM
                                        </Text>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-7B-Instruct">
                                    <div style={{ lineHeight: '1.4' }}>
                                        <div style={{ fontSize: '14px', marginBottom: '2px' }}>🔥 Qwen 2.5 7B (需要强卡)</div>
                                        <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                                            显存: 14-16GB | 时间: 8-12h | ❌ RTX 3060
                                        </Text>
                                    </div>
                                </Option>
                            </Select>
                        </Form.Item>

                        <Form.Item label="训练数据集" required>
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <Radio.Group
                                    onChange={async (e) => {
                                        const useSageDocs = e.target.value === 'sage-docs'
                                        if (useSageDocs) {
                                            await handlePrepareSageDocs()
                                        }
                                    }}
                                    defaultValue="upload"
                                >
                                    <Space direction="vertical">
                                        <Radio value="upload">
                                            📁 上传本地数据集
                                            <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                                                支持 JSON/JSONL (Alpaca 格式)
                                            </Text>
                                        </Radio>
                                        <Radio value="sage-docs">
                                            📚 使用 SAGE 官方文档
                                            <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                                                自动从 GitHub 下载并准备训练数据
                                            </Text>
                                        </Radio>
                                    </Space>
                                </Radio.Group>

                                {uploadedFile && (
                                    <Text type="success" style={{ fontSize: 12 }}>
                                        ✅ 数据已准备: {uploadedFile.split('/').pop()}
                                    </Text>
                                )}

                                <Upload {...uploadProps}>
                                    <Button icon={<UploadIcon className="w-4 h-4" />}>点击上传数据集</Button>
                                </Upload>
                                <Text type="secondary" className="text-xs">
                                    Alpaca 格式: {'{instruction, input, output}'}
                                </Text>
                            </Space>
                        </Form.Item>

                        {/* 安全模式预设 */}
                        <Alert
                            message="💡 配置建议"
                            description={
                                <div className="space-y-2">
                                    <div>
                                        针对 RTX 3060 12GB 显卡，推荐使用以下配置以避免 OOM（显存不足）错误：
                                    </div>
                                    <Space>
                                        <Button
                                            size="small"
                                            type="primary"
                                            onClick={() => {
                                                form.setFieldsValue({
                                                    num_epochs: 3,
                                                    batch_size: 1,
                                                    gradient_accumulation_steps: 16,
                                                    learning_rate: 0.00005,
                                                    max_length: 512,
                                                    load_in_8bit: true,
                                                })
                                                message.success('已应用安全配置（推荐）')
                                            }}
                                        >
                                            🛡️ 应用安全配置
                                        </Button>
                                        <Button
                                            size="small"
                                            onClick={() => {
                                                form.setFieldsValue({
                                                    num_epochs: 3,
                                                    batch_size: 2,
                                                    gradient_accumulation_steps: 8,
                                                    learning_rate: 0.00005,
                                                    max_length: 1024,
                                                    load_in_8bit: true,
                                                })
                                                message.success('已应用平衡配置')
                                            }}
                                        >
                                            ⚖️ 平衡配置
                                        </Button>
                                        <Button
                                            size="small"
                                            onClick={() => {
                                                form.setFieldsValue({
                                                    num_epochs: 3,
                                                    batch_size: 4,
                                                    gradient_accumulation_steps: 4,
                                                    learning_rate: 0.00005,
                                                    max_length: 2048,
                                                    load_in_8bit: false,
                                                })
                                                message.warning('高性能配置可能导致 OOM')
                                            }}
                                        >
                                            🚀 高性能配置
                                        </Button>
                                    </Space>
                                </div>
                            }
                            type="info"
                            showIcon
                            className="mb-4"
                        />

                        <Collapse ghost>
                            <Panel header="高级配置" key="1">
                                <div className="grid grid-cols-2 gap-4">
                                    <Form.Item label="训练轮数 (Epochs)" name="num_epochs">
                                        <InputNumber min={1} max={10} className="w-full" />
                                    </Form.Item>

                                    <Form.Item label="Batch Size" name="batch_size">
                                        <InputNumber min={1} max={8} className="w-full" />
                                    </Form.Item>

                                    <Form.Item label="梯度累积步数" name="gradient_accumulation_steps">
                                        <InputNumber min={1} max={64} className="w-full" />
                                    </Form.Item>

                                    <Form.Item label="学习率" name="learning_rate">
                                        <InputNumber min={0.00001} max={0.001} step={0.00001} className="w-full" />
                                    </Form.Item>

                                    <Form.Item label="最大序列长度" name="max_length">
                                        <InputNumber min={128} max={4096} step={128} className="w-full" />
                                    </Form.Item>

                                    <Form.Item label="8-bit 量化" name="load_in_8bit" valuePropName="checked">
                                        <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                                    </Form.Item>
                                </div>
                            </Panel>
                        </Collapse>

                        <Divider />

                        <Form.Item>
                            <Button
                                type="primary"
                                htmlType="submit"
                                loading={loading}
                                icon={<Play className="w-4 h-4" />}
                                size="large"
                            >
                                开始微调
                            </Button>
                        </Form.Item>
                    </Form>
                </Card>

                {/* Task List */}
                <Card title="微调任务列表">
                    <Table
                        dataSource={tasks}
                        columns={taskColumns}
                        rowKey="task_id"
                        pagination={{ pageSize: 10 }}
                        expandable={{
                            expandedRowRender: (record) => (
                                <div className="bg-gray-50 p-4 rounded">
                                    <Title level={5}>训练日志</Title>
                                    <div className="bg-black text-green-400 p-4 rounded font-mono text-sm max-h-64 overflow-auto">
                                        {record.logs.length > 0 ? (
                                            record.logs.map((log, idx) => <div key={idx}>{log}</div>)
                                        ) : (
                                            <Text type="secondary">暂无日志</Text>
                                        )}
                                    </div>
                                    {record.error_message && (
                                        <div className="mt-4">
                                            <Text type="danger">错误信息: {record.error_message}</Text>
                                        </div>
                                    )}
                                </div>
                            ),
                        }}
                    />
                </Card>
            </div>
        </div>
    )
}
