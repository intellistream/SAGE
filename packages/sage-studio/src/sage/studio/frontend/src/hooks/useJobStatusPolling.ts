import { useEffect, useRef } from 'react'
import { useFlowStore } from '../store/flowStore'
import { getJobStatus } from '../services/api'

/**
 * 作业状态轮询 Hook
 * 自动轮询作业状态并更新节点状态
 */
export const useJobStatusPolling = (
    jobId: string | null,
    interval: number = 1000, // 默认每秒轮询一次
    enabled: boolean = true
) => {
    const {
        setJobStatus,
        setIsPolling,
        jobStatus,
    } = useFlowStore()

    const intervalRef = useRef<NodeJS.Timeout | null>(null)
    const isPollingRef = useRef(false)

    useEffect(() => {
        // 如果没有 jobId 或未启用，停止轮询
        if (!jobId || !enabled) {
            if (intervalRef.current) {
                clearInterval(intervalRef.current)
                intervalRef.current = null
                setIsPolling(false)
                isPollingRef.current = false
            }
            return
        }

        // 开始轮询
        const pollStatus = async () => {
            try {
                const status = await getJobStatus(jobId)
                setJobStatus(status)

                // 如果作业已停止或出错，停止轮询
                if (
                    status.status === 'stopped' ||
                    status.status === 'error' ||
                    status.status === 'idle'
                ) {
                    if (intervalRef.current) {
                        clearInterval(intervalRef.current)
                        intervalRef.current = null
                        setIsPolling(false)
                        isPollingRef.current = false
                    }
                }
            } catch (error) {
                console.error('Failed to poll job status:', error)
                // 出错时停止轮询
                if (intervalRef.current) {
                    clearInterval(intervalRef.current)
                    intervalRef.current = null
                    setIsPolling(false)
                    isPollingRef.current = false
                }
            }
        }

        // 立即执行一次
        if (!isPollingRef.current) {
            pollStatus()
            setIsPolling(true)
            isPollingRef.current = true
        }

        // 设置定时轮询
        intervalRef.current = setInterval(pollStatus, interval)

        // 清理函数
        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current)
                intervalRef.current = null
                setIsPolling(false)
                isPollingRef.current = false
            }
        }
    }, [jobId, interval, enabled, setJobStatus, setIsPolling])

    return {
        isPolling: isPollingRef.current,
        jobStatus,
    }
}
