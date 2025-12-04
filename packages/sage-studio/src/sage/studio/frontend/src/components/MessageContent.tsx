/**
 * MessageContent Component - Renders chat messages with Markdown and syntax highlighting
 */

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import ReasoningAccordion, { type ReasoningStep } from './ReasoningAccordion'

interface MessageContentProps {
    content: string
    isUser: boolean
    isStreaming?: boolean
    streamingMessageId?: string | null
    messageId?: string
    reasoningSteps?: ReasoningStep[]
    isReasoning?: boolean
}

export default function MessageContent({
    content,
    isUser,
    isStreaming,
    streamingMessageId,
    messageId,
    reasoningSteps,
    isReasoning,
}: MessageContentProps) {
    // 用户消息使用简单渲染
    if (isUser) {
        return (
            <div className="whitespace-pre-wrap break-words">
                {content}
            </div>
        )
    }

    // AI 消息使用 Markdown 渲染
    // 注意：不使用 prose-invert，因为 AI 消息背景是浅色 (bg-gray-100)
    return (
        <div className="prose prose-sm max-w-none prose-gray">
            {/* 推理过程手风琴 */}
            {reasoningSteps && reasoningSteps.length > 0 && (
                <ReasoningAccordion
                    steps={reasoningSteps}
                    isStreaming={isReasoning || false}
                />
            )}

            {/* 主要内容 */}
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    // 代码块高亮
                    code({ className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '')
                        const language = match ? match[1] : ''
                        const isInline = !className

                        if (!isInline && language) {
                            return (
                                <div className="my-4 rounded-lg overflow-hidden">
                                    <div className="bg-gray-800 text-gray-200 text-xs px-4 py-2 flex justify-between items-center">
                                        <span className="font-mono">{language}</span>
                                        <button
                                            onClick={() => {
                                                navigator.clipboard.writeText(String(children))
                                            }}
                                            className="text-gray-400 hover:text-white transition-colors text-xs"
                                        >
                                            Copy
                                        </button>
                                    </div>
                                    <SyntaxHighlighter
                                        style={vscDarkPlus as any}
                                        language={language}
                                        PreTag="div"
                                        customStyle={{
                                            margin: 0,
                                            borderRadius: 0,
                                        }}
                                        {...props}
                                    >
                                        {String(children).replace(/\n$/, '')}
                                    </SyntaxHighlighter>
                                </div>
                            )
                        }

                        // 行内代码 - 确保在浅色背景上可读
                        return (
                            <code
                                className="px-1.5 py-0.5 bg-gray-200 text-gray-800 rounded text-sm font-mono"
                                {...props}
                            >
                                {children}
                            </code>
                        )
                    },

                    // 链接样式
                    a({ children, ...props }: any) {
                        return (
                            <a
                                className="text-blue-600 hover:text-blue-800 underline"
                                target="_blank"
                                rel="noopener noreferrer"
                                {...props}
                            >
                                {children}
                            </a>
                        )
                    },

                    // 表格样式
                    table({ children, ...props }: any) {
                        return (
                            <div className="overflow-x-auto my-4">
                                <table className="min-w-full divide-y divide-gray-300 text-gray-800" {...props}>
                                    {children}
                                </table>
                            </div>
                        )
                    },

                    // 表头样式
                    th({ children, ...props }: any) {
                        return (
                            <th className="px-3 py-2 text-left text-sm font-semibold text-gray-900 bg-gray-50" {...props}>
                                {children}
                            </th>
                        )
                    },

                    // 表格单元格样式
                    td({ children, ...props }: any) {
                        return (
                            <td className="px-3 py-2 text-sm text-gray-700" {...props}>
                                {children}
                            </td>
                        )
                    },

                    // 列表样式
                    ul({ children, ...props }: any) {
                        return (
                            <ul className="list-disc list-inside space-y-1 my-2 text-gray-800" {...props}>
                                {children}
                            </ul>
                        )
                    },

                    ol({ children, ...props }: any) {
                        return (
                            <ol className="list-decimal list-inside space-y-1 my-2 text-gray-800" {...props}>
                                {children}
                            </ol>
                        )
                    },

                    // 列表项样式
                    li({ children, ...props }: any) {
                        return (
                            <li className="text-gray-800" {...props}>
                                {children}
                            </li>
                        )
                    },

                    // 引用块样式 - 确保文字在浅色背景上可读
                    blockquote({ children, ...props }: any) {
                        return (
                            <blockquote
                                className="border-l-4 border-blue-400 bg-blue-50 pl-4 pr-2 py-2 my-2 italic text-gray-700 rounded-r"
                                {...props}
                            >
                                {children}
                            </blockquote>
                        )
                    },

                    // 标题样式 - 确保深色文字
                    h1({ children, ...props }: any) {
                        return (
                            <h1 className="text-2xl font-bold mt-4 mb-2 text-gray-900" {...props}>
                                {children}
                            </h1>
                        )
                    },

                    h2({ children, ...props }: any) {
                        return (
                            <h2 className="text-xl font-bold mt-3 mb-2 text-gray-900" {...props}>
                                {children}
                            </h2>
                        )
                    },

                    h3({ children, ...props }: any) {
                        return (
                            <h3 className="text-lg font-bold mt-2 mb-1 text-gray-900" {...props}>
                                {children}
                            </h3>
                        )
                    },

                    h4({ children, ...props }: any) {
                        return (
                            <h4 className="text-base font-bold mt-2 mb-1 text-gray-900" {...props}>
                                {children}
                            </h4>
                        )
                    },

                    // 段落样式 - 确保深色文字
                    p({ children, ...props }: any) {
                        return (
                            <p className="my-2 leading-relaxed text-gray-800" {...props}>
                                {children}
                            </p>
                        )
                    },

                    // 强调文字样式
                    strong({ children, ...props }: any) {
                        return (
                            <strong className="font-bold text-gray-900" {...props}>
                                {children}
                            </strong>
                        )
                    },

                    // 斜体文字样式
                    em({ children, ...props }: any) {
                        return (
                            <em className="italic text-gray-800" {...props}>
                                {children}
                            </em>
                        )
                    },

                    // 水平线样式
                    hr({ ...props }: any) {
                        return (
                            <hr className="my-4 border-gray-300" {...props} />
                        )
                    },

                    // 预格式化文本（无语言的代码块）
                    pre({ children, ...props }: any) {
                        // 如果子元素是代码块，直接渲染子元素（由 code 组件处理）
                        return (
                            <pre className="bg-gray-800 text-gray-100 rounded-lg overflow-x-auto" {...props}>
                                {children}
                            </pre>
                        )
                    },
                }}
            >
                {content}
            </ReactMarkdown>

            {/* 流式输入光标 */}
            {isStreaming && streamingMessageId === messageId && (
                <span className="inline-block w-2 h-4 ml-1 bg-gray-600 animate-pulse" />
            )}
        </div>
    )
}
