import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiGet, apiPost, apiDelete } from '../lib/api'
import { useInstances } from '../hooks/useInstances'
import { Plus, Play, Square, Trash2, LogIn, Monitor, RefreshCw } from 'lucide-react'

interface Account {
  id: string
  platform: string
  display_name: string
  tags: string[]
}

const platformIcons: Record<string, string> = {
  chatgpt: '🤖',
  deepseek: '🐋',
  gemini: '💎',
  doubao: '🫘',
  lmarena: '🏟️',
}

const statusColors: Record<string, string> = {
  online: 'bg-cockpit-success',
  busy: 'bg-cockpit-accent',
  offline: 'bg-gray-600',
  starting: 'bg-cockpit-warning animate-pulse',
  logged_out: 'bg-cockpit-danger',
  captcha: 'bg-cockpit-warning',
  rate_limited: 'bg-cockpit-warning',
  error: 'bg-cockpit-danger',
}

export default function Accounts() {
  const navigate = useNavigate()
  const [accounts, setAccounts] = useState<Account[]>([])
  const { instances, refresh: refreshInstances, startInstance, stopInstance } = useInstances()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ platform: 'chatgpt', display_name: '' })
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  const refresh = () => {
    apiGet<Account[]>('/api/accounts').then(setAccounts)
    refreshInstances()
  }

  useEffect(() => { refresh() }, [])

  const handleAdd = async () => {
    if (!form.display_name) return
    await apiPost('/api/accounts', form)
    setForm({ platform: 'chatgpt', display_name: '' })
    setShowAdd(false)
    refresh()
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除？')) return
    await apiDelete(`/api/accounts/${id}`)
    refresh()
  }

  const handleStart = async (id: string) => {
    setLoading(prev => ({ ...prev, [id]: true }))
    try {
      await startInstance(id)
    } catch (e) {
      console.error(e)
    }
    setLoading(prev => ({ ...prev, [id]: false }))
  }

  const handleStop = async (id: string) => {
    setLoading(prev => ({ ...prev, [id]: true }))
    try {
      await stopInstance(id)
    } catch (e) {
      console.error(e)
    }
    setLoading(prev => ({ ...prev, [id]: false }))
  }

  const handleLogin = async (id: string) => {
    await apiPost(`/api/instances/${id}/login`)
  }

  // 获取实例状态
  const getInstance = (accountId: string) => {
    return instances.find(i => i.account_id === accountId)
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">👤 账号管理</h1>
        <div className="flex gap-2">
          <button onClick={refresh} className="p-2 bg-cockpit-card border border-cockpit-border rounded-lg hover:bg-cockpit-border">
            <RefreshCw size={16} />
          </button>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-2 px-4 py-2 bg-cockpit-accent rounded-lg hover:opacity-80"
          >
            <Plus size={16} /> 添加账号
          </button>
        </div>
      </div>

      {/* 添加账号表单 */}
      {showAdd && (
        <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5 mb-6">
          <div className="flex gap-4 items-end">
            <div>
              <label className="text-sm text-gray-400 block mb-1">平台</label>
              <select
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
                className="bg-cockpit-bg border border-cockpit-border rounded-lg px-3 py-2 text-white"
              >
                <option value="chatgpt">🤖 ChatGPT</option>
                <option value="deepseek">🐋 DeepSeek</option>
                <option value="gemini">💎 Gemini</option>
                <option value="doubao">🫘 豆包</option>
                <option value="lmarena">🏟️ LMArena</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="text-sm text-gray-400 block mb-1">名称</label>
              <input
                type="text"
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
                placeholder="例如：ChatGPT Plus 主力号"
                className="w-full bg-cockpit-bg border border-cockpit-border rounded-lg px-3 py-2 text-white"
              />
            </div>
            <button onClick={handleAdd} className="px-4 py-2 bg-cockpit-accent rounded-lg hover:opacity-80">
              创建
            </button>
          </div>
        </div>
      )}

      {/* 账号卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {accounts.length === 0 && (
          <div className="col-span-full bg-cockpit-card border border-cockpit-border rounded-xl p-12 text-center text-gray-600">
            暂无账号，点击右上角添加
          </div>
        )}
        {accounts.map((acc) => {
          const inst = getInstance(acc.id)
          const instStatus = inst?.status || 'offline'
          const isLoading = loading[acc.id]

          return (
            <div key={acc.id} className="bg-cockpit-card border border-cockpit-border rounded-xl p-5 hover:border-cockpit-accent/30 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{platformIcons[acc.platform] || '🔧'}</span>
                  <div>
                    <div className="font-medium">{acc.display_name}</div>
                    <div className="text-xs text-gray-500">{acc.platform}</div>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full ${statusColors[instStatus]}`} />
                  <span className="text-xs text-gray-400">{instStatus}</span>
                </div>
              </div>

              {/* 标签 */}
              {acc.tags.length > 0 && (
                <div className="flex gap-1 mb-3">
                  {acc.tags.map((tag) => (
                    <span key={tag} className="px-2 py-0.5 rounded text-xs bg-cockpit-border">{tag}</span>
                  ))}
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex gap-2 pt-3 border-t border-cockpit-border">
                {instStatus === 'offline' || instStatus === 'error' ? (
                  <button
                    onClick={() => handleStart(acc.id)}
                    disabled={isLoading}
                    className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-cockpit-success/20 text-cockpit-success rounded-lg hover:bg-cockpit-success/30 text-sm disabled:opacity-50"
                  >
                    <Play size={14} /> {isLoading ? '启动中...' : '启动'}
                  </button>
                ) : instStatus === 'logged_out' ? (
                  <button
                    onClick={() => handleLogin(acc.id)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-cockpit-warning/20 text-cockpit-warning rounded-lg hover:bg-cockpit-warning/30 text-sm"
                  >
                    <LogIn size={14} /> 登录
                  </button>
                ) : (
                  <button
                    onClick={() => navigate(`/live/${acc.id}`)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-cockpit-accent/20 text-cockpit-accent rounded-lg hover:bg-cockpit-accent/30 text-sm"
                  >
                    <Monitor size={14} /> 查看
                  </button>
                )}

                {(instStatus === 'online' || instStatus === 'busy') && (
                  <button
                    onClick={() => handleStop(acc.id)}
                    disabled={isLoading}
                    className="px-3 py-1.5 bg-cockpit-warning/20 text-cockpit-warning rounded-lg hover:bg-cockpit-warning/30 text-sm disabled:opacity-50"
                  >
                    <Square size={14} />
                  </button>
                )}

                {instStatus === 'offline' && (
                  <button
                    onClick={() => handleDelete(acc.id)}
                    className="px-3 py-1.5 bg-cockpit-danger/20 text-cockpit-danger rounded-lg hover:bg-cockpit-danger/30 text-sm"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
