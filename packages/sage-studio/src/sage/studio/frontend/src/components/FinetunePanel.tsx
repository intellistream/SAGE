/**
 * Fine-tune Panel Component - Gemini-style model fine-tuning interface
 *
 * Design follows the Gemini design system:
 * - Clean white background with centered content
 * - Consistent colors with ChatMode (#F0F4F9, #1a73e8, etc.)
 * - Icons instead of emojis
 */

import { useEffect, useState } from 'react'
import {
    Form,
    InputNumber,
    Progress,
    Select,
    Table,
    Tag,
    Upload,
    message,
    Switch,
    Collapse,
    Radio,
    Modal,
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
    ArrowRightCircle,
    Zap,
    Settings,
    Lightbulb,
    FileText,
    FolderOpen,
    Shield,
    Gauge,
    Rocket,
    Sparkles,
    MessageSquare,
    ChevronDown,
    Trash2,
} from 'lucide-react'
import type { UploadFile, UploadProps } from 'antd'

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

// ============================================================================
// Gemini-Style UI Components
// ============================================================================

/** Section Card with Gemini styling */
function SectionCard({
    title,
    icon,
    children,
    className = '',
}: {
    title: string
    icon?: React.ReactNode
    children: React.ReactNode
    className?: string
}) {
    return (
        <div className={`bg-[--gemini-main-bg] rounded-2xl border border-[--gemini-border] p-6 ${className}`}>
            {title && (
                <div className="flex items-center gap-2 mb-4">
                    {icon && <span className="text-[--gemini-accent]">{icon}</span>}
                    <h3 className="text-base font-medium text-[--gemini-text-primary]">{title}</h3>
                </div>
            )}
            {children}
        </div>
    )
}

/** Gemini-style primary button */
function PrimaryButton({
    children,
    onClick,
    disabled = false,
    loading = false,
    icon,
    size = 'default',
}: {
    children: React.ReactNode
    onClick?: () => void
    disabled?: boolean
    loading?: boolean
    icon?: React.ReactNode
    size?: 'small' | 'default' | 'large'
}) {
    const sizeClasses = {
        small: 'px-3 py-1.5 text-sm',
        default: 'px-4 py-2 text-sm',
        large: 'px-6 py-3 text-base',
    }
    return (
        <button
            onClick={onClick}
            disabled={disabled || loading}
            className={`
                flex items-center gap-2 rounded-full font-medium
                bg-[--gemini-accent] text-white hover:opacity-90 hover:shadow-md
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-all duration-200 ease-out
                ${sizeClasses[size]}
            `}
        >
            {loading ? (
                <span className="animate-spin">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                </span>
            ) : icon}
            {children}
        </button>
    )
}

/** Gemini-style secondary button */
function SecondaryButton({
    children,
    onClick,
    disabled = false,
    icon,
    danger = false,
    size = 'default',
}: {
    children: React.ReactNode
    onClick?: () => void
    disabled?: boolean
    icon?: React.ReactNode
    danger?: boolean
    size?: 'small' | 'default' | 'large'
}) {
    const sizeClasses = {
        small: 'px-3 py-1.5 text-sm',
        default: 'px-4 py-2 text-sm',
        large: 'px-6 py-3 text-base',
    }
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`
                flex items-center gap-2 rounded-full font-medium
                border transition-all duration-200 ease-out
                disabled:opacity-50 disabled:cursor-not-allowed
                ${danger
                    ? 'border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20'
                    : 'border-[--gemini-border] text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg]'
                }
                ${sizeClasses[size]}
            `}
        >
            {icon}
            {children}
        </button>
    )
}

/** Info banner component */
function InfoBanner({
    icon,
    children,
    type = 'info',
}: {
    icon?: React.ReactNode
    children: React.ReactNode
    type?: 'info' | 'warning' | 'success'
}) {
    const bgColors = {
        info: 'bg-[#E8F0FE] dark:bg-[#1e3a5f]',
        warning: 'bg-amber-50 dark:bg-amber-900/20',
        success: 'bg-green-50 dark:bg-green-900/20',
    }
    const iconColors = {
        info: 'text-[--gemini-accent]',
        warning: 'text-amber-600 dark:text-amber-400',
        success: 'text-green-600 dark:text-green-400',
    }
    return (
        <div className={`${bgColors[type]} rounded-xl p-4 flex items-start gap-3 my-4`}>
            {icon && <span className={`${iconColors[type]} flex-shrink-0 mt-0.5`}>{icon}</span>}
            <div className="text-sm text-[--gemini-text-primary]">{children}</div>
        </div>
    )
}

// ============================================================================
// Main Component
// ============================================================================

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

                if (data.warnings && data.warnings.length > 0) {
                    Modal.warning({
                        title: '显存警告',
                        icon: <AlertCircle className="text-amber-500" />,
                        content: (
                            <div className="space-y-2">
                                {data.warnings.map((warning: string, index: number) => (
                                    <div key={index}>{warning}</div>
                                ))}
                                <div className="mt-4 text-[--gemini-text-secondary]">
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
        const hide = message.loading('正在切换模型...', 0)
        try {
            const response = await fetch(
                `/api/finetune/switch-model?model_path=${encodeURIComponent(modelPath)}`,
                { method: 'POST' }
            )

            if (response.ok) {
                const data = await response.json()
                hide()

                if (data.llm_service_restarted) {
                    message.success('模型已切换并生效，LLM 服务已自动重启')
                } else {
                    message.warning('模型已切换，需要重启 Studio 后生效')
                }

                loadCurrentModel()
            } else {
                hide()
                message.error('切换模型失败')
            }
        } catch (error) {
            hide()
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
                message.success(`SAGE 文档已准备完成，共 ${data.stats.total_samples} 条训练数据`)
            } else {
                const error = await response.json().catch(() => ({ detail: response.statusText }))
                message.error(error.detail || '准备文档失败')
            }
        } catch (error) {
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
                    const response = await fetch('/api/finetune/use-as-backend', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ task_id: taskId }),
                    })

                    if (response.ok) {
                        const data = await response.json()
                        message.success(data.message)
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
            completed: { color: 'success', icon: <CheckCircle className="w-3 h-3" />, text: '已完成' },
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
                        loadTasks()
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
                        loadTasks()
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

    const taskColumns = [
        {
            title: '任务 ID',
            dataIndex: 'task_id',
            key: 'task_id',
            width: 200,
            render: (text: string) => <code className="text-xs bg-[--gemini-input-bg] px-2 py-1 rounded text-[--gemini-text-primary]">{text}</code>,
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
                        className="gemini-progress"
                    />
                    <span className="text-xs text-[--gemini-text-secondary]">
                        Epoch {record.current_epoch}/{record.total_epochs} | Loss: {record.loss.toFixed(4)}
                    </span>
                </div>
            ),
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 150,
            render: (text: string) => <span className="text-sm">{new Date(text).toLocaleString('zh-CN')}</span>,
        },
        {
            title: '操作',
            key: 'action',
            width: 320,
            render: (_: any, record: FinetuneTask) => (
                <div className="flex items-center gap-2 flex-wrap">
                    {record.status === 'completed' && (
                        <>
                            <SecondaryButton
                                size="small"
                                icon={<ArrowRightCircle size={14} />}
                                onClick={() => handleSwitchModel(record.output_dir)}
                            >
                                应用
                            </SecondaryButton>
                            <SecondaryButton
                                size="small"
                                icon={<MessageSquare size={14} />}
                                onClick={() => handleUseAsBackend(record.task_id)}
                            >
                                设为后端
                            </SecondaryButton>
                            <SecondaryButton
                                size="small"
                                icon={<Download size={14} />}
                                onClick={() => handleDownloadModel(record.task_id)}
                            >
                                下载
                            </SecondaryButton>
                        </>
                    )}
                    {(record.status === 'training' || record.status === 'preparing' || record.status === 'queued') && (
                        <SecondaryButton
                            size="small"
                            danger
                            onClick={() => handleCancelTask(record.task_id)}
                        >
                            取消
                        </SecondaryButton>
                    )}
                    {(record.status === 'failed' || record.status === 'completed' || record.status === 'cancelled') && (
                        <SecondaryButton
                            size="small"
                            danger
                            icon={<Trash2 size={14} />}
                            onClick={() => handleDeleteTask(record.task_id)}
                        >
                            删除
                        </SecondaryButton>
                    )}
                </div>
            ),
        },
    ]

    return (
        <div className="h-full overflow-auto bg-[--gemini-main-bg]">
            {/* Centered content container - matches ChatMode's max-w-[830px] style */}
            <div className="max-w-4xl mx-auto py-8 px-6 space-y-6">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                            <Zap size={20} className="text-white" />
                        </div>
                        <h1 className="text-2xl font-medium text-[--gemini-text-primary]">模型微调</h1>
                    </div>
                    <p className="text-[--gemini-text-secondary] ml-[52px]">
                        使用自定义数据微调 LLM 模型，提升特定任务的性能
                    </p>
                    {gpuInfo && (
                        <div className="ml-[52px] mt-2 flex items-center gap-2 text-sm text-[--gemini-accent]">
                            <Cpu size={14} />
                            <span>{gpuInfo.recommendation}</span>
                        </div>
                    )}
                </div>

                {/* Current Model Section */}
                <SectionCard title="当前模型" icon={<Settings size={18} />}>
                    <p className="text-sm text-[--gemini-text-secondary] mb-4">
                        Chat 模式会优先使用本地 LLM 服务的模型
                    </p>
                    <div className="flex items-end gap-4">
                        <div className="flex-1">
                            <label className="block text-sm text-[--gemini-text-secondary] mb-2">基础模型（用于微调）</label>
                            <Select
                                value={currentModel}
                                onChange={(value) => setCurrentModel(value)}
                                style={{ width: '100%' }}
                                placeholder="选择基础模型"
                                optionLabelProp="label"
                            >
                                {models.map((model) => (
                                    <Option
                                        key={model.name}
                                        value={model.name}
                                        label={model.name.length > 35 ? `${model.name.substring(0, 35)}...` : model.name}
                                    >
                                        <div className="flex items-center justify-between gap-2">
                                            <span className="text-sm truncate flex-1">{model.name}</span>
                                            <Tag color={model.type === 'base' ? 'blue' : 'green'} style={{ margin: 0 }}>
                                                {model.type === 'base' ? '基础' : '微调'}
                                            </Tag>
                                        </div>
                                    </Option>
                                ))}
                            </Select>
                        </div>
                        <PrimaryButton
                            onClick={() => handleSwitchModel(currentModel)}
                            icon={<ArrowRightCircle size={16} />}
                        >
                            应用到 Chat
                        </PrimaryButton>
                    </div>
                    <InfoBanner icon={<Lightbulb size={16} />} type="info">
                        <strong>提示</strong>：选择模型后点击"应用到 Chat"，LLM 服务会自动重启并加载新模型，无需重启 Studio
                    </InfoBanner>
                </SectionCard>

                {/* Create Fine-tune Task */}
                <SectionCard title="创建微调任务" icon={<Sparkles size={18} />}>
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
                            label={<span className="text-[--gemini-text-primary]">基础模型</span>}
                            name="model_name"
                            tooltip="选择要微调的基础模型（推荐使用 1.5B 模型适配 RTX 3060）"
                            rules={[{ required: true }]}
                        >
                            <Select placeholder="选择基础模型" style={{ width: '100%' }}>
                                <Option value="Qwen/Qwen2.5-Coder-1.5B-Instruct">
                                    <div className="py-1">
                                        <div className="flex items-center gap-2 text-sm">
                                            <Sparkles size={14} className="text-[--gemini-accent]" />
                                            Qwen 2.5 Coder 1.5B (推荐)
                                        </div>
                                        <div className="text-xs text-[--gemini-text-secondary] ml-5">显存: 6-8GB | 时间: 2-4h</div>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-Coder-0.5B-Instruct">
                                    <div className="py-1">
                                        <div className="flex items-center gap-2 text-sm">
                                            <Rocket size={14} className="text-green-500" />
                                            Qwen 2.5 Coder 0.5B (超快)
                                        </div>
                                        <div className="text-xs text-[--gemini-text-secondary] ml-5">显存: 2-4GB | 时间: 1-2h | 推荐新手</div>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-0.5B-Instruct">
                                    <div className="py-1">
                                        <div className="flex items-center gap-2 text-sm">
                                            <Rocket size={14} className="text-green-500" />
                                            Qwen 2.5 0.5B (超快)
                                        </div>
                                        <div className="text-xs text-[--gemini-text-secondary] ml-5">显存: 2-4GB | 时间: 1-2h</div>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-1.5B-Instruct">
                                    <div className="py-1">
                                        <div className="flex items-center gap-2 text-sm">
                                            <MessageSquare size={14} className="text-blue-500" />
                                            Qwen 2.5 1.5B (通用)
                                        </div>
                                        <div className="text-xs text-[--gemini-text-secondary] ml-5">显存: 4-6GB | 时间: 2-4h</div>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-3B-Instruct">
                                    <div className="py-1">
                                        <div className="flex items-center gap-2 text-sm">
                                            <Zap size={14} className="text-amber-500" />
                                            Qwen 2.5 3B (高级)
                                        </div>
                                        <div className="text-xs text-[--gemini-text-secondary] ml-5">显存: 8-10GB | 时间: 4-6h | 可能 OOM</div>
                                    </div>
                                </Option>
                                <Option value="Qwen/Qwen2.5-7B-Instruct">
                                    <div className="py-1">
                                        <div className="flex items-center gap-2 text-sm">
                                            <AlertCircle size={14} className="text-red-500" />
                                            Qwen 2.5 7B (需要强卡)
                                        </div>
                                        <div className="text-xs text-[--gemini-text-secondary] ml-5">显存: 14-16GB | 时间: 8-12h | 不适合 RTX 3060</div>
                                    </div>
                                </Option>
                            </Select>
                        </Form.Item>

                        <Form.Item label={<span className="text-[--gemini-text-primary]">训练数据集</span>} required>
                            <div className="space-y-3">
                                <Radio.Group
                                    onChange={async (e) => {
                                        if (e.target.value === 'sage-docs') {
                                            await handlePrepareSageDocs()
                                        }
                                    }}
                                    defaultValue="upload"
                                >
                                    <div className="space-y-2">
                                        <Radio value="upload" className="flex items-center">
                                            <div className="flex items-center gap-2 ml-2">
                                                <FolderOpen size={16} className="text-[--gemini-text-secondary]" />
                                                <span>上传本地数据集</span>
                                                <span className="text-xs text-[--gemini-text-secondary]">支持 JSON/JSONL (Alpaca 格式)</span>
                                            </div>
                                        </Radio>
                                        <Radio value="sage-docs" className="flex items-center">
                                            <div className="flex items-center gap-2 ml-2">
                                                <FileText size={16} className="text-[--gemini-text-secondary]" />
                                                <span>使用 SAGE 官方文档</span>
                                                <span className="text-xs text-[--gemini-text-secondary]">自动从 GitHub 下载</span>
                                            </div>
                                        </Radio>
                                    </div>
                                </Radio.Group>

                                {uploadedFile && (
                                    <div className="flex items-center gap-2 text-sm text-green-600">
                                        <CheckCircle size={14} />
                                        数据已准备: {uploadedFile.split('/').pop()}
                                    </div>
                                )}

                                <Upload {...uploadProps}>
                                    <SecondaryButton icon={<UploadIcon size={16} />}>
                                        点击上传数据集
                                    </SecondaryButton>
                                </Upload>
                                <p className="text-xs text-[--gemini-text-secondary]">
                                    Alpaca 格式: {'{ instruction, input, output }'}
                                </p>
                            </div>
                        </Form.Item>

                        {/* Configuration Presets */}
                        <InfoBanner icon={<Lightbulb size={16} />} type="info">
                            <div className="space-y-3">
                                <div>
                                    针对 RTX 3060 12GB 显卡，推荐使用以下配置以避免 OOM（显存不足）错误：
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <SecondaryButton
                                        size="small"
                                        icon={<Shield size={14} />}
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
                                        安全配置
                                    </SecondaryButton>
                                    <SecondaryButton
                                        size="small"
                                        icon={<Gauge size={14} />}
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
                                        平衡配置
                                    </SecondaryButton>
                                    <SecondaryButton
                                        size="small"
                                        icon={<Rocket size={14} />}
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
                                        高性能配置
                                    </SecondaryButton>
                                </div>
                            </div>
                        </InfoBanner>

                        <Collapse
                            ghost
                            className="mt-4"
                            expandIcon={({ isActive }) => (
                                <ChevronDown size={16} className={`transition-transform ${isActive ? 'rotate-180' : ''}`} />
                            )}
                        >
                            <Panel
                                header={
                                    <span className="flex items-center gap-2 text-[--gemini-text-secondary]">
                                        <Settings size={16} />
                                        高级配置
                                    </span>
                                }
                                key="1"
                            >
                                <div className="grid grid-cols-2 gap-4 pt-2">
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

                        <div className="border-t border-[--gemini-border] pt-6 mt-6">
                            <PrimaryButton
                                loading={loading}
                                icon={<Play size={16} />}
                                size="large"
                                onClick={() => form.submit()}
                            >
                                开始微调
                            </PrimaryButton>
                        </div>
                    </Form>
                </SectionCard>

                {/* Task List */}
                <SectionCard title="微调任务列表" icon={<FileText size={18} />}>
                    <Table
                        dataSource={tasks}
                        columns={taskColumns}
                        rowKey="task_id"
                        pagination={{ pageSize: 10 }}
                        className="gemini-table"
                        expandable={{
                            expandedRowRender: (record) => (
                                <div className="bg-[--gemini-sidebar-bg] p-4 rounded-xl">
                                    <h4 className="text-sm font-medium text-[--gemini-text-primary] mb-2">训练日志</h4>
                                    <div className="bg-gray-900 dark:bg-black text-green-400 p-4 rounded-lg font-mono text-xs max-h-64 overflow-auto">
                                        {record.logs.length > 0 ? (
                                            record.logs.map((log, idx) => <div key={idx}>{log}</div>)
                                        ) : (
                                            <span className="text-[--gemini-text-secondary]">暂无日志</span>
                                        )}
                                    </div>
                                    {record.error_message && (
                                        <div className="mt-4 flex items-center gap-2 text-red-600 text-sm">
                                            <XCircle size={14} />
                                            错误信息: {record.error_message}
                                        </div>
                                    )}
                                </div>
                            ),
                        }}
                    />
                </SectionCard>
            </div>
        </div>
    )
}
