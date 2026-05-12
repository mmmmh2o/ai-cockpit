import { useEffect, useState } from 'react'
import { apiGet } from '../lib/api'
import { Play, Square, Wifi, WifiOff } from 'lucide-react'

interface HealthStatus {
  status: string
  instances: number
  max_concurrent: number
}

export default function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null)

  useEffect(() => {
    apiGet<HealthStatus>('/health').then(setHealth).catch(() => {})
  }, [])

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">🎮 AI Cockpit</h1>

      {/* 状态卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            {health?.status === 'ok' ? (
              <Wifi className="text-cockpit-success" size={20} />
            ) : (
              <WifiOff className="text-cockpit-danger" size={20} />
            )}
            <span className="text-gray-400 text-sm">服务状态</span>
          </div>
          <div className="text-2xl font-bold">
            {health?.status === 'ok' ? '运行中' : '检查中...'}
          </div>
        </div>

        <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <Play className="text-cockpit-accent" size={20} />
            <span className="text-gray-400 text-sm">活跃实例</span>
          </div>
          <div className="text-2xl font-bold">
            {health?.instances ?? 0} / {health?.max_concurrent ?? 5}
          </div>
        </div>

        <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <Square className="text-cockpit-warning" size={20} />
            <span className="text-gray-400 text-sm">工作流</span>
          </div>
          <div className="text-2xl font-bold">0 个运行中</div>
        </div>
      </div>

      {/* 快速操作 */}
      <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5">
        <h2 className="text-lg font-semibold mb-4">快速操作</h2>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-cockpit-accent rounded-lg hover:opacity-80 transition-opacity">
            一键启动全部
          </button>
          <button className="px-4 py-2 bg-cockpit-border rounded-lg hover:bg-cockpit-card transition-colors">
            一键停止全部
          </button>
        </div>
      </div>

      {/* 占位：浏览器墙 */}
      <div className="mt-8 bg-cockpit-card border border-cockpit-border rounded-xl p-5">
        <h2 className="text-lg font-semibold mb-4">🖥️ 浏览器墙</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="aspect-video bg-cockpit-bg rounded-lg border border-cockpit-border flex items-center justify-center text-gray-600">
            暂无实例
          </div>
        </div>
      </div>
    </div>
  )
}
