import { useEffect, useState, useRef } from 'react'
import { apiGet, apiPost } from '../lib/api'
import { Send, RefreshCw, Copy, Check, RotateCcw } from 'lucide-react'

interface Instance {
  account_id: string
  display_name: string
  platform: string
  status: string
}

interface ChatMsg {
  role: string
  content: string
}

const platformColors: Record<string, string> = {
  chatgpt: 'border-green-500 bg-green-500/5',
  deepseek: 'border-blue-500 bg-blue-500/5',
  gemini: 'border-purple-500 bg-purple-500/5',
  doubao: 'border-orange-500 bg-orange-500/5',
}

const platformLabels: Record<string, string> = {
  chatgpt: 'ChatGPT',
  deepseek: 'DeepSeek',
  gemini: 'Gemini',
  doubao: '豆包',
}

export default function CompareView() {
  const [instances, setInstances] = useState<Instance[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [prompt, setPrompt] = useState('')
  const [responses, setResponses] = useState<Record<string, { loading: boolean; text: string; error?: string; time?: number }>>({})
  const [copied, setCopied] = useState<Record<string, boolean>>({})
  const resultsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    apiGet<Instance[]>('/api/instances').then(setInstances)
  }, [])

  const onlineInstances = instances.filter(i => i.status === 'online')

  const toggleSelect = (id: string) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const handleSend = async () => {
    if (!prompt.trim() || selected.length === 0) return

    // 初始化所有选中的实例为 loading
    const init: typeof responses = {}
    selected.forEach(id => { init[id] = { loading: true, text: '' } })
    setResponses(init)

    // 并发发送
    const tasks = selected.map(async (id) => {
      const start = Date.now()
      try {
        const res = await apiPost<{ response: string }>(`/api/instances/${id}/chat`, { message: prompt })
        setResponses(prev => ({
          ...prev,
          [id]: { loading: false, text: res.response, time: Date.now() - start },
        }))
      } catch (e) {
        setResponses(prev => ({
          ...prev,
          [id]: { loading: false, text: '', error: String(e), time: Date.now() - start },
        }))
      }
    })

    await Promise.all(tasks)
  }

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(prev => ({ ...prev, [id]: true }))
    setTimeout(() => setCopied(prev => ({ ...prev, [id]: false })), 2000)
  }

  const handleClear = () => {
    setResponses({})
    setPrompt('')
  }

  const hasResults = Object.keys(responses).length > 0

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">🔍 多平台对比</h1>
        {hasResults && (
          <button onClick={handleClear} className="flex items-center gap-1 px-3 py-1.5 bg-cockpit-border rounded-lg text-sm hover:bg-cockpit-card">
            <RotateCcw size={14} /> 清空
          </button>
        )}
      </div>

      {/* 选择实例 */}
      <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-4 mb-4">
        <span className="text-sm text-gray-400 block mb-2">选择要对比的 AI（在线实例）</span>
        <div className="flex flex-wrap gap-2">
          {instances.map(inst => {
            const isSelected = selected.includes(inst.account_id)
            const isOnline = inst.status === 'online'
            return (
              <button
                key={inst.account_id}
                onClick={() => isOnline && toggleSelect(inst.account_id)}
                disabled={!isOnline}
                className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                  isSelected
                    ? `${platformColors[inst.platform] || 'border-cockpit-accent bg-cockpit-accent/10'} border-2`
                    : isOnline
                    ? 'border-cockpit-border hover:border-gray-500'
                    : 'border-cockpit-border opacity-40 cursor-not-allowed'
                }`}
              >
                <span className="mr-1">{inst.platform === 'chatgpt' ? '🤖' : inst.platform === 'deepseek' ? '🐋' : inst.platform === 'gemini' ? '💎' : '🫘'}</span>
                {inst.display_name}
                {!isOnline && <span className="ml-1 text-xs text-gray-600">({inst.status})</span>}
              </button>
            )
          })}
          {instances.length === 0 && (
            <span className="text-sm text-gray-600">暂无实例，请先在账号页启动</span>
          )}
        </div>
      </div>

      {/* 输入区 */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="输入 prompt，同时发送给所有选中的 AI..."
          className="flex-1 bg-cockpit-card border border-cockpit-border rounded-lg px-4 py-2.5 text-white"
        />
        <button
          onClick={handleSend}
          disabled={selected.length === 0 || !prompt.trim()}
          className="px-5 py-2.5 bg-cockpit-accent rounded-lg hover:opacity-80 disabled:opacity-50 flex items-center gap-2"
        >
          <Send size={16} /> 发送
        </button>
      </div>

      {/* 结果对比 */}
      <div ref={resultsRef} className="flex-1 min-h-0 overflow-auto">
        {!hasResults ? (
          <div className="flex items-center justify-center h-full text-gray-600">
            <div className="text-center">
              <svg className="mx-auto mb-3" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
              </svg>
              <p>选择 AI 实例，输入 prompt，对比不同平台的回答</p>
              <p className="text-sm mt-1">支持同时发送给多个 AI，并排查看结果</p>
            </div>
          </div>
        ) : (
          <div className={`grid gap-4 ${selected.length === 1 ? 'grid-cols-1' : selected.length === 2 ? 'grid-cols-2' : 'grid-cols-2 xl:grid-cols-3'}`}>
            {selected.map(id => {
              const inst = instances.find(i => i.account_id === id)
              const res = responses[id]
              if (!inst) return null

              return (
                <div key={id} className={`border rounded-xl overflow-hidden ${platformColors[inst.platform] || 'border-cockpit-border'} bg-cockpit-card`}>
                  {/* 头部 */}
                  <div className="p-3 border-b border-cockpit-border flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span>{inst.platform === 'chatgpt' ? '🤖' : inst.platform === 'deepseek' ? '🐋' : inst.platform === 'gemini' ? '💎' : '🫘'}</span>
                      <span className="font-medium text-sm">{inst.display_name}</span>
                      <span className="text-xs text-gray-500">{platformLabels[inst.platform]}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {res?.time && (
                        <span className="text-xs text-gray-500">{(res.time / 1000).toFixed(1)}s</span>
                      )}
                      {res?.text && (
                        <button
                          onClick={() => handleCopy(id, res.text)}
                          className="p-1 hover:text-cockpit-accent"
                          title="复制"
                        >
                          {copied[id] ? <Check size={14} className="text-cockpit-success" /> : <Copy size={14} />}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 内容 */}
                  <div className="p-4 min-h-[200px] max-h-[500px] overflow-auto">
                    {res?.loading ? (
                      <div className="flex items-center justify-center h-32">
                        <div className="flex items-center gap-2 text-gray-400">
                          <RefreshCw size={16} className="animate-spin" />
                          <span>等待回复...</span>
                        </div>
                      </div>
                    ) : res?.error ? (
                      <div className="text-cockpit-danger text-sm bg-cockpit-danger/10 rounded-lg p-3">
                        {res.error}
                      </div>
                    ) : res?.text ? (
                      <div className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                        {res.text}
                      </div>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
