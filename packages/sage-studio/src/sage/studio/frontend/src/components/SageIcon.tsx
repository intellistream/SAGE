/**
 * SAGE 图标组件 - 主题自适应
 * 浅色模式：黑色
 * 深色模式：白色
 * 背景透明
 */
//import React from 'react'

interface SageIconProps {
    size?: number
    className?: string
}

export function SageIcon({ size = 24, className = '' }: SageIconProps) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className={className}
        >
            {/* SAGE 流 & 算子 概念图标 - 表示数据流和处理节点 */}
            {/* 使用 currentColor 实现主题自适应 */}

            {/* 中心节点 - 代表算子 */}
            <circle
                cx="12"
                cy="12"
                r="4"
                fill="currentColor"
            />

            {/* 输入流 - 左侧 */}
            <path
                d="M2 12H6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
            />
            <circle cx="2" cy="12" r="1.5" fill="currentColor" />

            {/* 输出流 - 右侧 */}
            <path
                d="M18 12H22"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
            />
            <circle cx="22" cy="12" r="1.5" fill="currentColor" />

            {/* 上方流 */}
            <path
                d="M12 2V6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
            />
            <circle cx="12" cy="2" r="1.5" fill="currentColor" />

            {/* 下方流 */}
            <path
                d="M12 18V22"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
            />
            <circle cx="22" cy="12" r="1.5" fill="currentColor" />

            {/* 对角连接线 - 表示更复杂的数据流 */}
            <path
                d="M6 6L8.5 8.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                opacity="0.7"
            />
            <path
                d="M18 6L15.5 8.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                opacity="0.7"
            />
            <path
                d="M6 18L8.5 15.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                opacity="0.7"
            />
            <path
                d="M18 18L15.5 15.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                opacity="0.7"
            />
        </svg>
    )
}

export default SageIcon
