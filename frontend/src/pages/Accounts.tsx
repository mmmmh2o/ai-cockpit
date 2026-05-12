import { useEffect, useState } from 'react'
import { apiGet, apiPost, apiDelete } from '../lib/api'
import { Plus, Play, Square, Trash2 } from 'lucide-react'

interface Account {
  id: string
  platform: string
  display_name: string
  status?: string
  tags: string[]
}

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ platform: 'chatgpt', display_name: '' })

  const refresh = () => apiGet<Account[]>('/api/accounts').then(setAccounts)

  useEffect(() => { refresh() }, [])

  const handleAdd = async () => {
    if (!form.display_name) return
    await apiPost('/api/accounts', form)
    setForm({ platform: 'chatgpt', display_name: '' })
    setShowAdd(false)
    refresh()
  }

  const handleDelete = async (id: string) => {
    await apiDelete(`/api/accounts/${id}`)
    refresh()
  }

  const handleStart = async (id: string) => {
    await apiPost(`/api/instances/${id}/start`)
  }

  const handleStop = async (id: string) => {
    await apiPost(`/api/instances/${id}/stop`)
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">👤 账号管理</h1>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-2 px-4 py-2 bg-cockpit-accent rounded-lg hover:opacity-80"
        >
          <Plus size={16} /> 添加账号
        </button>
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
                <option value="chatgpt">ChatGPT</option>
                <option value="deepseek">DeepSeek</option>
                <option value="gemini">Gemini</option>
                <option value="doubao">豆包</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="text-sm text-gray-400 block mb-1">名称</label>
              <input
                type="text"
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
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

      {/* 账号列表 */}
      <div className="bg-cockpit-card border border-cockpit-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-cockpit-border text-gray-400 text-sm">
              <th className="text-left p-4">平台</th>
              <th className="text-left p-4">名称</th>
              <th className="text-left p-4">状态</th>
              <th className="text-left p-4">标签</th>
              <th className="text-right p-4">操作</th>
            </tr>
          </thead>
          <tbody>
            {accounts.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-gray-600">
                  暂无账号，点击右上角添加
                </td>
              </tr>
            ) : (
              accounts.map((acc) => (
                <tr key={acc.id} className="border-b border-cockpit-border hover:bg-cockpit-bg/50">
                  <td className="p-4">
                    <span className="px-2 py-1 rounded text-xs bg-cockpit-accent/20 text-cockpit-accent">
                      {acc.platform}
                    </span>
                  </td>
                  <td className="p-4">{acc.display_name}</td>
                  <td className="p-4">
                    <span className="text-gray-500 text-sm">{acc.status || '未启动'}</span>
                  </td>
                  <td className="p-4">
                    {acc.tags.map((tag) => (
                      <span key={tag} className="px-2 py-0.5 rounded text-xs bg-cockpit-border mr-1">
                        {tag}
                      </span>
                    ))}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex gap-2 justify-end">
                      <button onClick={() => handleStart(acc.id)} className="p-1.5 hover:text-cockpit-success" title="启动">
                        <Play size={16} />
                      </button>
                      <button onClick={() => handleStop(acc.id)} className="p-1.5 hover:text-cockpit-warning" title="停止">
                        <Square size={16} />
                      </button>
                      <button onClick={() => handleDelete(acc.id)} className="p-1.5 hover:text-cockpit-danger" title="删除">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
