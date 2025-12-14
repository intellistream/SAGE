/**
 * MessageContent Component - Gemini-style message rendering
 *
 * Design principles:
 * - Clean typography with generous line height (leading-relaxed to leading-loose)
 * - No background bubble for AI messages (displayed on white background)
 * - Subtle code block styling
 * - Proper spacing between elements
 */

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check } from 'lucide-react'
import { useState } from 'react'
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

/**
 * Copy button for code blocks
 */
function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false)

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(text)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            // Clipboard API not available
        }
    }

    return (
        <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
        >
            {copied ? (
                <>
                    <Check size={14} />
                    <span>Copied</span>
                </>
            ) : (
                <>
                    <Copy size={14} />
                    <span>Copy</span>
                </>
            )}
        </button>
    )
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
            <div className="whitespace-pre-wrap break-words text-base leading-relaxed">
                {content}
            </div>
        )
    }

    // AI 消息使用 Markdown 渲染 - Gemini Style
    return (
        <div className="gemini-prose">
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
                            // 正确处理 children，可能是数组或字符串
                            const codeString = Array.isArray(children)
                                ? children.join('')
                                : String(children).replace(/\n$/, '')
                            return (
                                <div className="my-4 rounded-xl overflow-hidden border border-[--gemini-border]">
                                    <div className="bg-gray-900 dark:bg-black text-gray-300 text-xs px-4 py-2.5 flex justify-between items-center">
                                        <span className="font-mono text-[--gemini-accent]">{language}</span>
                                        <CopyButton text={codeString} />
                                    </div>
                                    <SyntaxHighlighter
                                        style={oneDark as any}
                                        language={language}
                                        PreTag="div"
                                        customStyle={{
                                            margin: 0,
                                            borderRadius: 0,
                                            fontSize: '0.875rem',
                                            lineHeight: '1.5',
                                        }}
                                        {...props}
                                    >
                                        {codeString}
                                    </SyntaxHighlighter>
                                </div>
                            )
                        }

                        // 行内代码 - Gemini style
                        return (
                            <code
                                className="px-1.5 py-0.5 bg-[--gemini-sidebar-bg] text-[--gemini-text-primary] rounded-md text-[0.9em] font-mono"
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
                                className="text-[--gemini-accent] hover:text-[--gemini-accent]/80 underline decoration-1 underline-offset-2"
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
                            <div className="overflow-x-auto my-4 rounded-xl border border-[--gemini-border]">
                                <table className="min-w-full divide-y divide-[--gemini-border]" {...props}>
                                    {children}
                                </table>
                            </div>
                        )
                    },

                    thead({ children, ...props }: any) {
                        return (
                            <thead className="bg-[--gemini-sidebar-bg]" {...props}>
                                {children}
                            </thead>
                        )
                    },

                    th({ children, ...props }: any) {
                        return (
                            <th className="px-4 py-3 text-left text-sm font-semibold text-[--gemini-text-primary]" {...props}>
                                {children}
                            </th>
                        )
                    },

                    td({ children, ...props }: any) {
                        return (
                            <td className="px-4 py-3 text-sm text-[--gemini-text-secondary] border-t border-[--gemini-border]" {...props}>
                                {children}
                            </td>
                        )
                    },

                    // 列表样式
                    ul({ children, ...props }: any) {
                        return (
                            <ul className="list-disc pl-6 space-y-2 my-4 text-[--gemini-text-primary]" {...props}>
                                {children}
                            </ul>
                        )
                    },

                    ol({ children, ...props }: any) {
                        return (
                            <ol className="list-decimal pl-6 space-y-2 my-4 text-[--gemini-text-primary]" {...props}>
                                {children}
                            </ol>
                        )
                    },

                    li({ children, ...props }: any) {
                        return (
                            <li className="text-[--gemini-text-primary] leading-relaxed pl-1" {...props}>
                                {children}
                            </li>
                        )
                    },

                    // 引用块样式 - Gemini style
                    blockquote({ children, ...props }: any) {
                        return (
                            <blockquote
                                className="border-l-4 border-[--gemini-accent] bg-[--gemini-accent]/10 pl-4 pr-4 py-3 my-4 rounded-r-xl text-[--gemini-text-primary]"
                                {...props}
                            >
                                {children}
                            </blockquote>
                        )
                    },

                    // 标题样式
                    h1({ children, ...props }: any) {
                        return (
                            <h1 className="text-2xl font-semibold mt-6 mb-3 text-[--gemini-text-primary]" {...props}>
                                {children}
                            </h1>
                        )
                    },

                    h2({ children, ...props }: any) {
                        return (
                            <h2 className="text-xl font-semibold mt-5 mb-2.5 text-[--gemini-text-primary]" {...props}>
                                {children}
                            </h2>
                        )
                    },

                    h3({ children, ...props }: any) {
                        return (
                            <h3 className="text-lg font-semibold mt-4 mb-2 text-[--gemini-text-primary]" {...props}>
                                {children}
                            </h3>
                        )
                    },

                    h4({ children, ...props }: any) {
                        return (
                            <h4 className="text-base font-semibold mt-4 mb-2 text-[--gemini-text-primary]" {...props}>
                                {children}
                            </h4>
                        )
                    },

                    // 段落样式 - 关键：使用较大的行高
                    p({ children, ...props }: any) {
                        return (
                            <p className="my-3 leading-7 text-[--gemini-text-primary] text-base" {...props}>
                                {children}
                            </p>
                        )
                    },

                    // 强调文字样式
                    strong({ children, ...props }: any) {
                        return (
                            <strong className="font-semibold text-[--gemini-text-primary]" {...props}>
                                {children}
                            </strong>
                        )
                    },

                    // 斜体文字样式
                    em({ children, ...props }: any) {
                        return (
                            <em className="italic text-[--gemini-text-primary]" {...props}>
                                {children}
                            </em>
                        )
                    },

                    // 水平线样式
                    hr({ ...props }: any) {
                        return (
                            <hr className="my-6 border-[--gemini-border]" {...props} />
                        )
                    },

                    // 预格式化文本
                    pre({ children, ...props }: any) {
                        return (
                            <pre className="bg-gray-900 dark:bg-black text-gray-100 rounded-xl overflow-x-auto" {...props}>
                                {children}
                            </pre>
                        )
                    },
                }}
            >
                {content}
            </ReactMarkdown>

            {/* 流式输入光标 - Gemini style */}
            {isStreaming && streamingMessageId === messageId && (
                <span className="inline-block w-0.5 h-5 ml-0.5 bg-[--gemini-accent] animate-pulse rounded-sm" />
            )}
        </div>
    )
}
