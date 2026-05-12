import { useEffect, useState, useRef } from 'react'
import { apiGet, apiPost, apiDelete } from '../lib/api'
import { Play, Pause, Square, Trash2, Plus, Copy, Save, ChevronRight, ChevronDown, Zap, GitBranch, MessageCircle, Swords } from 'lucide-react'

interface WorkflowTemplate {
  id: string
  name: string
  description: string
  mode: string
  step_count: number
}

interface WorkflowStep {
  id: string
  name: string
  instance_id: string
  prompt_template: string
  timeout: number
  retries: number
}

interface Workflow {
  id: string
  name: string
  mode: string
  steps: WorkflowStep[]
  created_at: string
}

interface RunStep {
  id: string
  name: string
  instance_id: string
  status: string
  output: string
  error: string | null
}

interface WorkflowRun {
  run_id: string
  workflow_name: string
  mode: string
  status: string
  progress: number
  duration: number
  user_input: string
  steps: RunStep[]
  logs: { step_id: string; message: string; timestamp: string }[]
}

const modeIcons: Record<string, typeof Play> = {
  pipeline: Zap,
  roundtable: MessageCircle,
  review_loop: GitBranch,
  debate: Swords,
}

const modeLabels: Record<string, string> = {
  pipeline: '流水线',
  roundtable: '圆桌讨论',
  review_loop: '审核循环',
  debate: '辩论赛',
}

const modeColors: Record<string, string> = {
  pipeline: 'text-blue-400',
  roundtable: 'text-green-400',
  review_loop: 'text-yellow-400',
  debate: 'text-red-400',
}

export default function WorkflowEditor() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [activeTab, setActiveTab] = useState<'list' | 'create' | 'run'>('list')
  const [selectedWf, setSelectedWf] = useState<Workflow | null>(null)
  const [runs, setRuns] = useState<WorkflowRun[]>([])
  const [activeRun, setActiveRun] = useState<WorkflowRun | null>(null)
  const [runInput, setRunInput] = useState('')
  const [form, setForm] = useState({ name: '', mode: 'pipeline' as string, steps: [] as WorkflowStep[] })
  const [instances, setInstances] = useState<{ account_id: string; display_name: string; status: string }[]>([])
  const pollRef = useRef<ReturnType<typeof setInterval>>()

  // 加载数据
  const refresh = async () => {
    const [t, w, i] = await Promise.all([
      apiGet<WorkflowTemplate[]>('/api/workflows/templates'),
      apiGet<Workflow[]>('/api/workflows'),
      apiGet<{ account_id: string; display_name: string; status: string }[]>('/api/instances'),
    ])
    setTemplates(t)
    setWorkflows(w)
    setInstances(i)
  }

  useEffect(() => { refresh() }, [])

  // 从模板创建工作流
  const handleFromTemplate = async (tid: string) => {
    const tmpl = await apiGet<{ name: string; mode: string; steps: WorkflowStep[] }>(`/api/workflows/templates/${tid}`)
    setForm({
      name: tmpl.name,
      mode: tmpl.mode,
      steps: tmpl.steps.map(s => ({ ...s, instance_id: '' })),
    })
    setActiveTab('create')
  }

  // 保存工作流
  const handleSave = async () => {
    if (!form.name) return
    await apiPost('/api/workflows', form)
    setForm({ name: '', mode: 'pipeline', steps: [] })
    setActiveTab('list')
    refresh()
  }

  // 删除工作流
  const handleDelete = async (id: string) => {
    await apiDelete(`/api/workflows/${id}`)
    refresh()
  }

  // 执行工作流
  const handleRun = async (wf: Workflow) => {
    if (!runInput.trim()) return
    const res = await apiPost<{ run_id: string }>(`/api/workflows/${wf.id}/run`, { input: runInput })
    setRunInput('')
    setActiveTab('run')
    // 开始轮询执行状态
    startPolling(res.run_id)
  }

  // 轮询执行状态
  const startPolling = (runId: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    const poll = async () => {
      try {
        const run = await apiGet<WorkflowRun>(`/api/workflows/run/${runId}`)
        setActiveRun(run)
        if (run.status === 'success' || run.status === 'failed' || run.status === 'aborted') {
          clearInterval(pollRef.current)
        }
      } catch { /* ignore */ }
    }
    poll()
    pollRef.current = setInterval(poll, 2000)
  }

  // 暂停/恢复/终止
  const handlePause = async () => { if (activeRun) await apiPost(`/api/workflows/run/${activeRun.run_id}/pause`) }
  const handleResume = async () => { if (activeRun) await apiPost(`/api/workflows/run/${activeRun.run_id}/resume`) }
  const handleAbort = async () => { if (activeRun) await apiPost(`/api/workflows/run/${activeRun.run_id}/abort`) }

  // 添加步骤
  const addStep = () => {
    setForm(prev => ({
      ...prev,
      steps: [...prev.steps, {
        id: `step-${prev.steps.length + 1}`,
        name: `步骤 ${prev.steps.length + 1}`,
        instance_id: '',
        prompt_template: '',
        timeout: 300,
        retries: 0,
      }],
    }))
  }

  // 更新步骤
  const updateStep = (index: number, patch: Partial<WorkflowStep>) => {
    setForm(prev => ({
      ...prev,
      steps: prev.steps.map((s, i) => i === index ? { ...s, ...patch } : s),
    }))
  }

  // 删除步骤
  const removeStep = (index: number) => {
    setForm(prev => ({
      ...prev,
      steps: prev.steps.filter((_, i) => i !== index),
    }))
  }

  const statusColors: Record<string, string> = {
    pending: 'text-gray-500',
    running: 'text-cockpit-accent animate-pulse',
    done: 'text-cockpit-success',
    success: 'text-cockpit-success',
    failed: 'text-cockpit-danger',
    aborted: 'text-cockpit-warning',
    paused: 'text-cockpit-warning',
  }

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">🔗 工作流</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('list')}
            className={`px-3 py-1.5 rounded-lg text-sm ${activeTab === 'list' ? 'bg-cockpit-accent' : 'bg-cockpit-card border border-cockpit-border'}`}
          >
            工作流列表
          </button>
          <button
            onClick={() => setActiveTab('create')}
            className={`px-3 py-1.5 rounded-lg text-sm ${activeTab === 'create' ? 'bg-cockpit-accent' : 'bg-cockpit-card border border-cockpit-border'}`}
          >
            <Plus size={14} className="inline mr-1" /> 新建
          </button>
          <button
            onClick={() => setActiveTab('run')}
            className={`px-3 py-1.5 rounded-lg text-sm ${activeTab === 'run' ? 'bg-cockpit-accent' : 'bg-cockpit-card border border-cockpit-border'}`}
          >
            执行监控
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-auto">
        {/* ── 工作流列表 ── */}
        {activeTab === 'list' && (
          <div className="space-y-4">
            {/* 模板 */}
            <div>
              <h2 className="text-lg font-semibold mb-3">📋 预置模板</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {templates.map(t => {
                  const Icon = modeIcons[t.mode] || Zap
                  return (
                    <div key={t.id} className="bg-cockpit-card border border-cockpit-border rounded-xl p-4 hover:border-cockpit-accent/30 transition-colors">
                      <div className="flex items-center gap-2 mb-2">
                        <Icon size={18} className={modeColors[t.mode]} />
                        <span className="font-medium">{t.name}</span>
                      </div>
                      <p className="text-sm text-gray-400 mb-3">{t.description}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">{t.step_count} 步</span>
                        <button
                          onClick={() => handleFromTemplate(t.id)}
                          className="flex items-center gap-1 px-3 py-1 bg-cockpit-accent/20 text-cockpit-accent rounded text-sm hover:bg-cockpit-accent/30"
                        >
                          <Copy size={12} /> 使用
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* 已保存的工作流 */}
            <div>
              <h2 className="text-lg font-semibold mb-3">💾 已保存的工作流</h2>
              {workflows.length === 0 ? (
                <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-8 text-center text-gray-600">
                  暂无工作流，从模板创建或手动新建
                </div>
              ) : (
                <div className="space-y-2">
                  {workflows.map(wf => {
                    const Icon = modeIcons[wf.mode] || Zap
                    return (
                      <div key={wf.id} className="bg-cockpit-card border border-cockpit-border rounded-xl p-4 flex items-center gap-4">
                        <Icon size={20} className={modeColors[wf.mode]} />
                        <div className="flex-1">
                          <div className="font-medium">{wf.name}</div>
                          <div className="text-xs text-gray-500">{modeLabels[wf.mode]} · {wf.steps.length} 步</div>
                        </div>
                        <input
                          type="text"
                          placeholder="输入内容后点运行..."
                          value={selectedWf?.id === wf.id ? runInput : ''}
                          onChange={(e) => { setSelectedWf(wf); setRunInput(e.target.value) }}
                          onKeyDown={(e) => e.key === 'Enter' && handleRun(wf)}
                          className="w-64 bg-cockpit-bg border border-cockpit-border rounded px-3 py-1.5 text-sm"
                        />
                        <button onClick={() => handleRun(wf)} className="p-2 hover:text-cockpit-success" title="运行">
                          <Play size={16} />
                        </button>
                        <button onClick={() => handleDelete(wf.id)} className="p-2 hover:text-cockpit-danger" title="删除">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── 创建/编辑工作流 ── */}
        {activeTab === 'create' && (
          <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">新建工作流</h2>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="text-sm text-gray-400 block mb-1">名称</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="例如：文章流水线"
                  className="w-full bg-cockpit-bg border border-cockpit-border rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400 block mb-1">模式</label>
                <select
                  value={form.mode}
                  onChange={(e) => setForm({ ...form, mode: e.target.value })}
                  className="w-full bg-cockpit-bg border border-cockpit-border rounded-lg px-3 py-2 text-white"
                >
                  <option value="pipeline">⚡ 流水线</option>
                  <option value="roundtable">💬 圆桌讨论</option>
                  <option value="review_loop">🔄 审核循环</option>
                  <option value="debate">⚔️ 辩论赛</option>
                </select>
              </div>
            </div>

            {/* 步骤列表 */}
            <div className="space-y-3 mb-4">
              {form.steps.map((step, i) => (
                <div key={i} className="bg-cockpit-bg border border-cockpit-border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-300">步骤 {i + 1}</span>
                    <button onClick={() => removeStep(i)} className="text-gray-500 hover:text-cockpit-danger">
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-3 mb-3">
                    <input
                      type="text"
                      value={step.name}
                      onChange={(e) => updateStep(i, { name: e.target.value })}
                      placeholder="步骤名称"
                      className="bg-cockpit-card border border-cockpit-border rounded px-3 py-1.5 text-sm"
                    />
                    <select
                      value={step.instance_id}
                      onChange={(e) => updateStep(i, { instance_id: e.target.value })}
                      className="bg-cockpit-card border border-cockpit-border rounded px-3 py-1.5 text-sm"
                    >
                      <option value="">选择实例</option>
                      {instances.filter(i => i.status === 'online').map(inst => (
                        <option key={inst.account_id} value={inst.account_id}>{inst.display_name}</option>
                      ))}
                    </select>
                    <input
                      type="number"
                      value={step.timeout}
                      onChange={(e) => updateStep(i, { timeout: Number(e.target.value) })}
                      placeholder="超时(秒)"
                      className="bg-cockpit-card border border-cockpit-border rounded px-3 py-1.5 text-sm"
                    />
                  </div>
                  <textarea
                    value={step.prompt_template}
                    onChange={(e) => updateStep(i, { prompt_template: e.target.value })}
                    placeholder="Prompt 模板（支持 {user.input}, {prev.output}）"
                    rows={3}
                    className="w-full bg-cockpit-card border border-cockpit-border rounded px-3 py-1.5 text-sm resize-none"
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <button onClick={addStep} className="flex items-center gap-1 px-4 py-2 bg-cockpit-border rounded-lg hover:bg-cockpit-card text-sm">
                <Plus size={14} /> 添加步骤
              </button>
              <button onClick={handleSave} className="flex items-center gap-1 px-4 py-2 bg-cockpit-accent rounded-lg hover:opacity-80 text-sm">
                <Save size={14} /> 保存
              </button>
            </div>
          </div>
        )}

        {/* ── 执行监控 ── */}
        {activeTab === 'run' && (
          <div>
            {!activeRun ? (
              <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-8 text-center text-gray-600">
                <p>暂无正在执行的工作流</p>
                <p className="text-sm mt-2">在列表中运行一个工作流后，这里会显示实时进度</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* 头部 */}
                <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-lg">{activeRun.workflow_name}</h3>
                      <span className="text-sm text-gray-500">{modeLabels[activeRun.mode]} · {activeRun.duration.toFixed(1)}s</span>
                    </div>
                    <div className="flex gap-2">
                      {activeRun.status === 'running' && (
                        <button onClick={handlePause} className="px-3 py-1.5 bg-cockpit-warning/20 text-cockpit-warning rounded text-sm">
                          <Pause size={14} className="inline mr-1" /> 暂停
                        </button>
                      )}
                      {activeRun.status === 'paused' && (
                        <button onClick={handleResume} className="px-3 py-1.5 bg-cockpit-success/20 text-cockpit-success rounded text-sm">
                          <Play size={14} className="inline mr-1" /> 恢复
                        </button>
                      )}
                      {(activeRun.status === 'running' || activeRun.status === 'paused') && (
                        <button onClick={handleAbort} className="px-3 py-1.5 bg-cockpit-danger/20 text-cockpit-danger rounded text-sm">
                          <Square size={14} className="inline mr-1" /> 终止
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 进度条 */}
                  <div className="w-full bg-cockpit-bg rounded-full h-2 mb-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-500 ${
                        activeRun.status === 'success' ? 'bg-cockpit-success' :
                        activeRun.status === 'failed' ? 'bg-cockpit-danger' :
                        'bg-cockpit-accent'
                      }`}
                      style={{ width: `${Math.max(activeRun.progress * 100, 5)}%` }}
                    />
                  </div>
                  <span className={`text-sm ${statusColors[activeRun.status]}`}>
                    {activeRun.status}
                  </span>
                </div>

                {/* 用户输入 */}
                <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-4">
                  <span className="text-xs text-gray-500">输入</span>
                  <p className="text-sm mt-1">{activeRun.user_input}</p>
                </div>

                {/* 步骤结果 */}
                <div className="space-y-2">
                  {activeRun.steps.map((step, i) => (
                    <div key={step.id} className="bg-cockpit-card border border-cockpit-border rounded-xl overflow-hidden">
                      <div className="p-4 flex items-center gap-3">
                        <span className={`text-lg ${statusColors[step.status]}`}>
                          {step.status === 'done' ? '✅' : step.status === 'failed' ? '❌' : step.status === 'running' ? '🔄' : '⏳'}
                        </span>
                        <div className="flex-1">
                          <span className="font-medium">{step.name}</span>
                          <span className="text-xs text-gray-500 ml-2">{step.instance_id}</span>
                        </div>
                      </div>
                      {step.output && (
                        <div className="px-4 pb-4">
                          <div className="bg-cockpit-bg rounded-lg p-3 text-sm text-gray-300 whitespace-pre-wrap max-h-48 overflow-auto">
                            {step.output}
                          </div>
                        </div>
                      )}
                      {step.error && (
                        <div className="px-4 pb-4">
                          <div className="bg-cockpit-danger/10 rounded-lg p-3 text-sm text-cockpit-danger">
                            {step.error}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* 日志 */}
                <div className="bg-cockpit-card border border-cockpit-border rounded-xl p-4">
                  <h3 className="text-sm font-medium text-gray-400 mb-2">执行日志</h3>
                  <div className="bg-cockpit-bg rounded-lg p-3 max-h-60 overflow-auto font-mono text-xs space-y-1">
                    {activeRun.logs.map((log, i) => (
                      <div key={i}>
                        <span className="text-gray-600">{log.timestamp.split('T')[1]?.split('.')[0]}</span>
                        <span className="text-cockpit-accent ml-2">[{log.step_id}]</span>
                        <span className="text-gray-300 ml-2">{log.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
