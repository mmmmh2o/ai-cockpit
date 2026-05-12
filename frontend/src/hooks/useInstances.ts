import { useEffect, useCallback } from 'react'
import { useInstanceStore } from '../stores/instanceStore'
import { apiGet, apiPost } from '../lib/api'
import type { InstanceState } from '../stores/instanceStore'

export function useInstances() {
  const { instances, setInstances } = useInstanceStore()

  const refresh = useCallback(async () => {
    try {
      const data = await apiGet<InstanceState[]>('/api/instances')
      setInstances(data)
    } catch (e) {
      console.error('获取实例列表失败:', e)
    }
  }, [setInstances])

  const startInstance = useCallback(async (accountId: string) => {
    await apiPost(`/api/instances/${accountId}/start`)
    await refresh()
  }, [refresh])

  const stopInstance = useCallback(async (accountId: string) => {
    await apiPost(`/api/instances/${accountId}/stop`)
    await refresh()
  }, [refresh])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 5000)
    return () => clearInterval(timer)
  }, [refresh])

  return { instances, refresh, startInstance, stopInstance }
}
