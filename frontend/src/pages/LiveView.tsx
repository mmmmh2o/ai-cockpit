import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useInstanceStore } from '../stores/instanceStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { apiGet, apiPost } from '../lib/api'
import { Send, MessageSquare, LogIn, Trash2, Plus } from 'lucide-react'

interface ChatMsg {
  role: string
  content: string
}

export default function LiveView() {
  const { id } = useParams()
  const { instances } = useInstanceStore()
  const [selectedId, setSelectedId] = useState<string | undefined>(id)
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('offline')
  const [chatInput, setChatInput] = useState('')
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  // 选中实例
  useEffect(() => {
    if (!selectedId && instances.length > 0) {
      setSelectedId(instances[0].account_id)
    }
  }, [instances, selectedId])

  // 加载历史
  useEffect(() => {
    if (selectedId) {
      apiGet<ChatMsg[]>(`/api/instances/${selectedId}/history`)
        .then(setMessages)
        .catch(() => setMessages([]))
    }
  }, [selectedId])

  // WebSocket 截图流
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsBase = `${wsProtocol}//${location.host}`

  const handleScreenMsg = useCallback((msg: unknown) => {
    const data = msg as { type: string; data: { image?: string; status?: string } }
    if (data.type === 'screenshot') {
      if (data.data.image) {
        setScreenshot(`data:image/jpeg;base64,${data.data.image}`)
      }
      if (data.data.status) {
        setStatus(data.data.status)
      }
    }
  }, [])

  useWebSocket(selectedId ? `${wsBase}/ws/instances/${selectedId}/screen` : '', handleScreenMsg)

  // WebSocket 对话流
  const handleChatMsg = useCallback((msg: unknown) => {
    const data = msg as { type: string; data: Record<string, unknown> }

    switch (data.type) {
      case 'chat':
        // 完整消息
        setMessages(prev => [...prev, { role: data.data.role as string, content: data.data.content as string }])
        setIsStreaming(false)
        setStreamingText('')
        break
      case 'chat_chunk':
        // 流式片段
        setIsStreaming(true)
        setStreamingText(prev => prev + (data.data.chunk as string))
        break
      case 'status_change':
        if (data.data.new_status) {
          setStatus(data.data.new_status as string)
        }
        break
      case 'error':
        setMessages(prev => [...prev, { role: 'system', content: `错误: ${data.data.message}` }])
        setIsStreaming(false)
        setStreamingText('')
        break
      case 'system':
        setMessages(prev => [...prev, { role: 'system', content: data.data.message as string }])
        break
    }
  }, [])

  const chatWsRef = useWebSocket(selectedId ? `${wsBase}/ws/instances/${selectedId}/chat` : '', handleChatMsg)

  // 发送消息（通过 WebSocket）
  const handleSend = () => {
    if (!chatInput.trim() || !selectedId) return
    const msg = chatInput.trim()
    setChatInput('')

    // 先在本地显示用户消息
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setIsStreaming(true)
    setStreamingText('')

    // 通过 WebSocket 发送
    const ws = chatWsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'chat', message: msg }))
    } else {
      // fallback: HTTP API
      setIsStreaming(false)
      apiPost<{ response: string }>(`/api/instances/${selectedId}/chat`, { message: msg })
        .then(res => {
          setMessages(prev => [...prev, { role: 'assistant', content: res.response }])
        })
        .catch(e => {
          setMessages(prev => [...prev, { role: 'system', content: `错误: ${e}` }])
        })
    }
  }

  // 新建对话
  const handleNewChat = () => {
    if (!selectedId) return
    const ws = chatWsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'new_chat' }))
    } else {
      apiPost(`/api/instances/${selectedId}/new-chat`)
    }
    setMessages([])
    setStreamingText('')
  }

  // 登录
  const handleLogin = async () => {
    if (!selectedId) return
    await apiPost(`/api/instances/${selectedId}/login`)
    setMessages(prev => [...prev, { role: 'system', content: '登录流程已启动，请在浏览器窗口中完成登录' }])
  }

  // 清空历史
  const handleClearHistory = async () => {
    if (!selectedId) return
    await apiDelete(`/api/instances/${selectedId}/history`)
    setMessages([])
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  // 状态颜色
  const statusColors: Record<string, string> = {
    online: 'text-cockpit-success',
    busy: 'text-cockpit-accent',
    offline: 'text-gray-500',
    starting: 'text-cockpit-warning animate-pulse',
    logged_out: 'text-cockpit-danger',
    captcha: 'text-cockpit-warning',
    rate_limited: 'text-cockpit-warning',
    error: 'text-cockpit-danger',
  }

  const statusLabels: Record<string, string> = {
    online: '在线',
    busy: '对话中',
    offline: '离线',
    starting: '启动中...',
    logged_out: '需要登录',
    captcha: '需要验证',
    rate_limited: '限流中',
    error: '错误',
  }

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">🖥️ 实时视图</h1>
          {selectedId && (
            <span className={`text-sm ${statusColors[status] || 'text-gray-500'}`}>
              ● {statusLabels[status] || status}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedId || ''}
            onChange={(e) => { setSelectedId(e.target.value); setMessages([]); setStreamingText('') }}
            className="bg-cockpit-card border border-cockpit-border rounded-lg px-3 py-2 text-white text-sm"
          >
            <option value="" disabled>选择实例</option>
            {instances.map((inst) => (
              <option key={inst.account_id} value={inst.account_id}>
                {inst.display_name} ({inst.status})
              </option>
            ))}
          </select>
          {status === 'logged_out' && (
            <button onClick={handleLogin} className="flex items-center gap-1 px-3 py-2 bg-cockpit-warning rounded-lg hover:opacity-80 text-sm">
              <LogIn size={14} /> 登录
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* 浏览器画面 */}
        <div className="flex-1 bg-cockpit-card border border-cockpit-border rounded-xl overflow-hidden flex flex-col">
          <div className="p-3 border-b border-cockpit-border flex items-center justify-between">
            <span className="text-sm text-gray-400">浏览器画面</span>
            <span className={`text-xs ${statusColors[status]}`}>{statusLabels[status]}</span>
          </div>
          <div className="flex-1 flex items-center justify-center bg-black/30">
            {screenshot ? (
              <img src={screenshot} alt="browser" className="max-w-full max-h-full object-contain" />
            ) : (
              <div className="text-gray-600 text-center">
                <svg className="mx-auto mb-2" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                  <line x1="8" y1="21" x2="16" y2="21"></line>
                  <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
                <p className="text-sm">启动实例后显示实时画面</p>
              </div>
            )}
          </div>
        </div>

        {/* 对话面板 */}
        <div className="w-96 bg-cockpit-card border border-cockpit-border rounded-xl flex flex-col">
          <div className="p-3 border-b border-cockpit-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare size={14} className="text-cockpit-accent" />
              <span className="text-sm text-gray-400">对话</span>
            </div>
            <div className="flex gap-1">
              <button onClick={handleNewChat} className="p-1 hover:text-cockpit-accent" title="新建对话">
                <Plus size={14} />
              </button>
              <button onClick={handleClearHistory} className="p-1 hover:text-cockpit-danger" title="清空历史">
                <Trash2 size={14} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-auto p-4 space-y-3">
            {messages.length === 0 && !isStreaming && (
              <div className="text-gray-600 text-center text-sm mt-8">
                <p>发送消息开始对话</p>
                <p className="text-xs mt-2">消息将通过浏览器发送到 AI 网页</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-cockpit-accent text-white'
                    : msg.role === 'assistant'
                    ? 'bg-cockpit-border text-gray-200'
                    : 'bg-cockpit-danger/20 text-cockpit-danger text-xs'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}

            {/* 流式回复 */}
            {isStreaming && streamingText && (
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-lg px-3 py-2 text-sm bg-cockpit-border text-gray-200 whitespace-pre-wrap">
                  {streamingText}
                  <span className="inline-block w-1.5 h-4 bg-cockpit-accent ml-0.5 animate-pulse" />
                </div>
              </div>
            )}
            {isStreaming && !streamingText && (
              <div className="flex justify-start">
                <div className="rounded-lg px-3 py-2 text-sm bg-cockpit-border text-gray-400">
                  <span className="animate-pulse">思考中...</span>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          <div className="p-3 border-t border-cockpit-border">
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder={status === 'online' ? '输入消息...' : '等待实例就绪...'}
                disabled={status !== 'online' && status !== 'busy'}
                className="flex-1 bg-cockpit-bg border border-cockpit-border rounded-lg px-3 py-2 text-white text-sm disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={status !== 'online' && status !== 'busy'}
                className="p-2 bg-cockpit-accent rounded-lg hover:opacity-80 disabled:opacity-50"
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

async function apiDelete(path: string) {
  const res = await fetch(path, { method: 'DELETE' })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}
