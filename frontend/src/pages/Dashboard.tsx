import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiGet } from '../lib/api'
import { useInstanceStore } from '../stores/instanceStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { Play, Wifi, WifiOff, Zap, Activity } from 'lucide-react'

interface HealthStatus {
  status: string
  instances: number
  max_concurrent: number
}

interface WorkflowRun {
  run_id: string
  workflow_name: string
  mode: string
  status: string
  progress: number
  duration: number
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [runs, setRuns] = useState<WorkflowRun[]>([])
  const { instances } = useInstanceStore()

  // 全局状态 WS
  const handleGlobalMsg = (msg: unknown) => {
    const data = msg as { type: string; data: Record<string, unknown> }
    if (data.type === 'status' && data.data.instances) {
      // useInstanceStore handles this
    }
  }

  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  useWebSocket(`${wsProtocol}//${location.host}/ws/global`, handleGlobalMsg)

  useEffect(() => {
    apiGet<HealthStatus>('/health').then(setHealth).catch(() => {})
    apiGet<WorkflowRun[]>('/api/workflows/runs').then(setRuns).catch(() => {})
    const timer = setInterval(() => {
      apiGet<HealthStatus>('/health').then(setHealth).catch(() => {})
      apiGet<WorkflowRun[]>('/api/workflows/runs').then(setRuns).catch(() => {})
    }, 5000)
    return () => clearInterval(timer)
  }, [])

  const activeRuns = runs.filter(r => r.status === 'running' || r.status === 'paused')
  const recentRuns = runs.slice(0, 5)

  const statusColors: Record<string, string> = {
    online: 'bg-cockpit-success',
    busy: 'bg-cockpit-accent',
    offline: 'bg-gray-600',
    starting: 'bg-cockpit-warning animate-pulse',
    logged_out: 'bg-cockpit-danger',
    captcha: 'bg-cockpit-warning',
    error: 'bg-cockpit-danger',
  }

  const runStatusColors: Record<string, string> = {
    running: 'text-cockpit-accent',
    success: 'text-cockpit-success',
    failed: 'text-cockpit-danger',
    paused: 'text-cockpit-warning',
    aborted: 'text-gray-500',
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">🎮 AI Cockpit</h1>

      {/* 状态卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
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
            {instances.filter(i => i.status !== 'offline').length} / {instances.length}
          </div>
        </div>

        <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <Zap className="text-cockpit-warning" size={20} />
            <span className="text-gray-400 text-sm">工作流运行中</span>
          </div>
          <div className="text-2xl font-bold">{activeRuns.length}</div>
        </div>

        <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <Activity className="text-cockpit-success" size={20} />
            <span className="text-gray-400 text-sm">总执行次数</span>
          </div>
          <div className="text-2xl font-bold">{runs.length}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 浏览器墙 */}
        <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4">🖥️ 浏览器墙</h2>
          {instances.length === 0 ? (
            <div className="aspect-video bg-cockpit-bg rounded-lg border border-cockpit-border flex items-center justify-center text-gray-600">
              <div className="text-center">
                <p>暂无实例</p>
                <button onClick={() => navigate('/accounts')} className="mt-2 text-sm text-cockpit-accent hover:underline">
                  去添加账号 →
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {instances.map(inst => (
                <div
                  key={inst.account_id}
                  onClick={() => navigate(`/live/${inst.account_id}`)}
                  className="bg-cockpit-bg rounded-lg border border-cockpit-border p-3 cursor-pointer hover:border-cockpit-accent/30 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className={`w-2 h-2 rounded-full ${statusColors[inst.status]}`} />
                    <span className="text-sm font-medium truncate">{inst.display_name}</span>
                  </div>
                  <div className="text-xs text-gray-500">{inst.platform} · {inst.status}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 最近工作流执行 */}
        <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">⚡ 最近执行</h2>
            <button onClick={() => navigate('/workflows')} className="text-sm text-cockpit-accent hover:underline">
              查看全部 →
            </button>
          </div>
          {recentRuns.length === 0 ? (
            <div className="aspect-video bg-cockpit-bg rounded-lg border border-cockpit-border flex items-center justify-center text-gray-600">
              <div className="text-center">
                <p>暂无执行记录</p>
                <button onClick={() => navigate('/workflows')} className="mt-2 text-sm text-cockpit-accent hover:underline">
                  去创建工作流 →
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {recentRuns.map(run => (
                <div key={run.run_id} className="bg-cockpit-bg rounded-lg border border-cockpit-border p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{run.workflow_name}</span>
                    <span className={`text-xs ${runStatusColors[run.status]}`}>{run.status}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-cockpit-card rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full ${
                          run.status === 'success' ? 'bg-cockpit-success' :
                          run.status === 'failed' ? 'bg-cockpit-danger' : 'bg-cockpit-accent'
                        }`}
                        style={{ width: `${Math.max(run.progress * 100, 3)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">{run.duration.toFixed(1)}s</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 快速操作 */}
      <div className="mt-6 bg-cockpit-card border border-cockpit-border rounded-xl p-5">
        <h2 className="text-lg font-semibold mb-4">快速操作</h2>
        <div className="flex gap-3">
          <button onClick={() => navigate('/accounts')} className="px-4 py-2 bg-cockpit-accent rounded-lg hover:opacity-80 transition-opacity text-sm">
            管理账号
          </button>
          <button onClick={() => navigate('/workflows')} className="px-4 py-2 bg-cockpit-border rounded-lg hover:bg-cockpit-card transition-colors text-sm">
            工作流编辑器
          </button>
        </div>
      </div>
    </div>
  )
}
