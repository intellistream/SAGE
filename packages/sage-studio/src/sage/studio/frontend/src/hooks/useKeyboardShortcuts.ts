import { useEffect } from 'react'
import { useFlowStore } from '../store/flowStore'
import { message } from 'antd'

/**
 * 键盘快捷键 Hook
 * 支持的快捷键：
 * - Ctrl/Cmd + Z: 撤销
 * - Ctrl/Cmd + Shift + Z 或 Ctrl/Cmd + Y: 重做
 * - Ctrl/Cmd + S: 保存（需要外部提供保存函数）
 * - Delete/Backspace: 删除选中节点
 */
export const useKeyboardShortcuts = (
    onSave?: () => void,
    enabled: boolean = true
) => {
    const {
        undo,
        redo,
        canUndo,
        canRedo,
        selectedNode,
        deleteNode,
    } = useFlowStore()

    useEffect(() => {
        if (!enabled) return

        const handleKeyDown = (event: KeyboardEvent) => {
            const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
            const ctrlOrCmd = isMac ? event.metaKey : event.ctrlKey

            // Ctrl/Cmd + Z: 撤销
            if (ctrlOrCmd && event.key === 'z' && !event.shiftKey) {
                event.preventDefault()
                if (canUndo()) {
                    undo()
                    message.success('已撤销')
                } else {
                    message.info('无法撤销')
                }
                return
            }

            // Ctrl/Cmd + Shift + Z 或 Ctrl/Cmd + Y: 重做
            if (
                (ctrlOrCmd && event.shiftKey && event.key === 'z') ||
                (ctrlOrCmd && event.key === 'y')
            ) {
                event.preventDefault()
                if (canRedo()) {
                    redo()
                    message.success('已重做')
                } else {
                    message.info('无法重做')
                }
                return
            }

            // Ctrl/Cmd + S: 保存（打开保存对话框）
            if (ctrlOrCmd && event.key === 's') {
                event.preventDefault()
                if (onSave) {
                    onSave()
                }
                return
            }

            // Delete 或 Backspace: 删除选中节点
            if (
                (event.key === 'Delete' || event.key === 'Backspace') &&
                selectedNode &&
                !isInputElement(event.target)
            ) {
                event.preventDefault()
                deleteNode(selectedNode.id)
                message.success('已删除节点')
                return
            }
        }

        window.addEventListener('keydown', handleKeyDown)

        return () => {
            window.removeEventListener('keydown', handleKeyDown)
        }
    }, [enabled, undo, redo, canUndo, canRedo, selectedNode, deleteNode, onSave])
}

/**
 * 检查当前焦点是否在输入元素上
 */
function isInputElement(target: EventTarget | null): boolean {
    if (!target || !(target instanceof HTMLElement)) {
        return false
    }

    const tagName = target.tagName.toLowerCase()
    return (
        tagName === 'input' ||
        tagName === 'textarea' ||
        target.isContentEditable
    )
}
