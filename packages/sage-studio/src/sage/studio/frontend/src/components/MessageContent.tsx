/**
 * MessageContent Component - Renders chat messages with Markdown and syntax highlighting
 */

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface MessageContentProps {
    content: string
    isUser: boolean
    isStreaming?: boolean
    streamingMessageId?: string | null
    messageId?: string
}

export default function MessageContent({
    content,
    isUser,
    isStreaming,
    streamingMessageId,
    messageId,
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
    return (
        <div className="prose prose-sm max-w-none dark:prose-invert">
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

                        // 行内代码
                        return (
                            <code
                                className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-sm font-mono"
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
                                <table className="min-w-full divide-y divide-gray-300" {...props}>
                                    {children}
                                </table>
                            </div>
                        )
                    },

                    // 列表样式
                    ul({ children, ...props }: any) {
                        return (
                            <ul className="list-disc list-inside space-y-1 my-2" {...props}>
                                {children}
                            </ul>
                        )
                    },

                    ol({ children, ...props }: any) {
                        return (
                            <ol className="list-decimal list-inside space-y-1 my-2" {...props}>
                                {children}
                            </ol>
                        )
                    },

                    // 引用块样式
                    blockquote({ children, ...props }: any) {
                        return (
                            <blockquote
                                className="border-l-4 border-gray-300 pl-4 my-2 italic text-gray-700"
                                {...props}
                            >
                                {children}
                            </blockquote>
                        )
                    },

                    // 标题样式
                    h1({ children, ...props }: any) {
                        return (
                            <h1 className="text-2xl font-bold mt-4 mb-2" {...props}>
                                {children}
                            </h1>
                        )
                    },

                    h2({ children, ...props }: any) {
                        return (
                            <h2 className="text-xl font-bold mt-3 mb-2" {...props}>
                                {children}
                            </h2>
                        )
                    },

                    h3({ children, ...props }: any) {
                        return (
                            <h3 className="text-lg font-bold mt-2 mb-1" {...props}>
                                {children}
                            </h3>
                        )
                    },

                    // 段落样式
                    p({ children, ...props }: any) {
                        return (
                            <p className="my-2 leading-relaxed" {...props}>
                                {children}
                            </p>
                        )
                    },
                }}
            >
                {content}
            </ReactMarkdown>

            {/* 流式输入光标 */}
            {isStreaming && streamingMessageId === messageId && (
                <span className="inline-block w-2 h-4 ml-1 bg-gray-800 animate-pulse" />
            )}
        </div>
    )
}
