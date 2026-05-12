import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useInstanceStore } from '../stores/instanceStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { apiGet, apiPost } from '../lib/api'
import { Send, RefreshCw, MessageSquare } from 'lucide-react'

export default function LiveView() {
  const { id } = useParams()
  const { instances } = useInstanceStore()
  const [selectedId, setSelectedId] = useState<string | undefined>(id)
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [chatInput, setChatInput] = useState('')
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const chatEndRef = useRef<HTMLDivElement>(null)

  // 如果没选中，选第一个
  useEffect(() => {
    if (!selectedId && instances.length > 0) {
      setSelectedId(instances[0].account_id)
    }
  }, [instances, selectedId])

  // WebSocket 截图流
  const wsUrl = selectedId
    ? `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/instances/${selectedId}/screen`
    : ''

  const handleWSMessage = useCallback((msg: unknown) => {
    const data = msg as { type: string; data: { image?: string } }
    if (data.type === 'screenshot' && data.data.image) {
      setScreenshot(`data:image/jpeg;base64,${data.data.image}`)
    }
  }, [])

  useWebSocket(wsUrl, handleWSMessage)

  // 发送消息
  const handleSend = async () => {
    if (!chatInput.trim() || !selectedId) return
    const msg = chatInput.trim()
    setChatInput('')
    setMessages((prev) => [...prev, { role: 'user', content: msg }])

    try {
      const res = await apiPost<{ response: string }>(`/api/instances/${selectedId}/chat`, { message: msg })
      setMessages((prev) => [...prev, { role: 'assistant', content: res.response }])
    } catch (e) {
      setMessages((prev) => [...prev, { role: 'system', content: `错误: ${e}` }])
    }
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">🖥️ 实时视图</h1>
        <select
          value={selectedId || ''}
          onChange={(e) => { setSelectedId(e.target.value); setMessages([]) }}
          className="bg-cockpit-card border border-cockpit-border rounded-lg px-3 py-2 text-white"
        >
          <option value="" disabled>选择实例</option>
          {instances.map((inst) => (
            <option key={inst.account_id} value={inst.account_id}>
              {inst.display_name} ({inst.status})
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* 浏览器画面 */}
        <div className="flex-1 bg-cockpit-card border border-cockpit-border rounded-xl overflow-hidden flex flex-col">
          <div className="p-3 border-b border-cockpit-border flex items-center justify-between">
            <span className="text-sm text-gray-400">浏览器画面</span>
            <button className="p-1 hover:text-cockpit-accent"><RefreshCw size={14} /></button>
          </div>
          <div className="flex-1 flex items-center justify-center bg-black/30">
            {screenshot ? (
              <img src={screenshot} alt="browser" className="max-w-full max-h-full object-contain" />
            ) : (
              <div className="text-gray-600 text-center">
                <Monitor className="mx-auto mb-2" size={48} />
                <p>启动实例后显示实时画面</p>
              </div>
            )}
          </div>
        </div>

        {/* 对话面板 */}
        <div className="w-96 bg-cockpit-card border border-cockpit-border rounded-xl flex flex-col">
          <div className="p-3 border-b border-cockpit-border flex items-center gap-2">
            <MessageSquare size={14} className="text-cockpit-accent" />
            <span className="text-sm text-gray-400">对话</span>
          </div>

          <div className="flex-1 overflow-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-gray-600 text-center text-sm mt-8">发送消息开始对话</div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-cockpit-accent text-white'
                    : msg.role === 'assistant'
                    ? 'bg-cockpit-border text-gray-200'
                    : 'bg-cockpit-danger/20 text-cockpit-danger'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div className="p-3 border-t border-cockpit-border">
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="输入消息..."
                className="flex-1 bg-cockpit-bg border border-cockpit-border rounded-lg px-3 py-2 text-white text-sm"
              />
              <button
                onClick={handleSend}
                className="p-2 bg-cockpit-accent rounded-lg hover:opacity-80"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Monitor(props: { className?: string; size: number }) {
  return (
    <svg className={props.className} width={props.size} height={props.size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
      <line x1="8" y1="21" x2="16" y2="21"></line>
      <line x1="12" y1="17" x2="12" y2="21"></line>
    </svg>
  )
}
