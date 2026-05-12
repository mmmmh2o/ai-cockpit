import { useCallback, useMemo, useState, useEffect } from 'react'
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  Handle,
  Position,
  NodeProps,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { apiGet, apiPost, apiDelete } from '../lib/api'
import { Save, Play, Plus, Trash2, Zap, MessageCircle, GitBranch, Swords, User, Clock, Variable } from 'lucide-react'

// ── 节点类型定义 ──────────────────────────────────

interface StepData {
  label: string
  instanceId: string
  promptTemplate: string
  timeout: number
  retries: number
  stepType: 'ai' | 'condition' | 'human' | 'delay' | 'variable'
}

const stepTypeConfig = {
  ai: { icon: '🤖', color: 'border-cockpit-accent', bg: 'bg-cockpit-accent/10' },
  condition: { icon: '🔀', color: 'border-yellow-500', bg: 'bg-yellow-500/10' },
  human: { icon: '👤', color: 'border-green-500', bg: 'bg-green-500/10' },
  delay: { icon: '⏱️', color: 'border-gray-500', bg: 'bg-gray-500/10' },
  variable: { icon: '📝', color: 'border-purple-500', bg: 'bg-purple-500/10' },
}

function AINode({ data, selected }: NodeProps<StepData>) {
  const cfg = stepTypeConfig[data.stepType] || stepTypeConfig.ai
  return (
    <div className={`min-w-[200px] rounded-lg border-2 ${selected ? 'border-white' : cfg.color} ${cfg.bg} p-3`}>
      <Handle type="target" position={Position.Top} className="!bg-cockpit-accent" />
      <div className="flex items-center gap-2 mb-1">
        <span>{cfg.icon}</span>
        <span className="font-medium text-sm">{data.label}</span>
      </div>
      {data.instanceId && (
        <div className="text-xs text-gray-400 truncate">{data.instanceId}</div>
      )}
      {data.promptTemplate && (
        <div className="text-xs text-gray-500 mt-1 truncate max-w-[180px]">
          {data.promptTemplate.slice(0, 40)}...
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-cockpit-accent" />
    </div>
  )
}

const nodeTypes = { aiNode: AINode }

// ── 主组件 ────────────────────────────────────────

interface Workflow {
  id: string
  name: string
  mode: string
  steps: { id: string; name: string; instance_id: string; prompt_template: string; timeout: number; retries: number }[]
}

interface Instance {
  account_id: string
  display_name: string
  platform: string
  status: string
}

export default function WorkflowEditor() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [instances, setInstances] = useState<Instance[]>([])
  const [selectedWf, setSelectedWf] = useState<Workflow | null>(null)
  const [wfName, setWfName] = useState('')
  const [wfMode, setWfMode] = useState('pipeline')
  const [runInput, setRunInput] = useState('')
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [activeRun, setActiveRun] = useState<Record<string, unknown> | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [showPanel, setShowPanel] = useState(false)

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // 加载
  const refresh = async () => {
    const [w, i] = await Promise.all([
      apiGet<Workflow[]>('/api/workflows'),
      apiGet<Instance[]>('/api/instances'),
    ])
    setWorkflows(w)
    setInstances(i)
  }
  useEffect(() => { refresh() }, [])

  // 工作流 -> React Flow 节点
  const loadWorkflowToCanvas = (wf: Workflow) => {
    setSelectedWf(wf)
    setWfName(wf.name)
    setWfMode(wf.mode)

    const newNodes: Node<StepData>[] = wf.steps.map((step, i) => ({
      id: step.id,
      type: 'aiNode',
      position: { x: 250, y: i * 150 },
      data: {
        label: step.name,
        instanceId: step.instance_id,
        promptTemplate: step.prompt_template,
        timeout: step.timeout,
        retries: step.retries,
        stepType: 'ai',
      },
    }))

    const newEdges: Edge[] = wf.steps.slice(0, -1).map((step, i) => ({
      id: `e-${step.id}-${wf.steps[i + 1].id}`,
      source: step.id,
      target: wf.steps[i + 1].id,
      animated: true,
      style: { stroke: '#6366f1' },
    }))

    setNodes(newNodes)
    setEdges(newEdges)
  }

  // 从画布创建工作流步骤
  const canvasToSteps = () => {
    // 按 y 坐标排序
    const sorted = [...nodes].sort((a, b) => a.position.y - b.position.y)
    return sorted.map(n => ({
      id: n.id,
      name: n.data.label,
      instance_id: n.data.instanceId,
      prompt_template: n.data.promptTemplate,
      timeout: n.data.timeout,
      retries: n.data.retries,
    }))
  }

  // 连线
  const onConnect = useCallback((params: Connection) => {
    setEdges(eds => addEdge({ ...params, animated: true, style: { stroke: '#6366f1' } }, eds))
  }, [setEdges])

  // 添加节点
  const addNode = (type: StepData['stepType'] = 'ai') => {
    const id = `step-${Date.now()}`
    const newNode: Node<StepData> = {
      id,
      type: 'aiNode',
      position: { x: 250 + Math.random() * 100, y: nodes.length * 150 },
      data: {
        label: `步骤 ${nodes.length + 1}`,
        instanceId: '',
        promptTemplate: '',
        timeout: 300,
        retries: 0,
        stepType: type,
      },
    }
    setNodes(nds => [...nds, newNode])
  }

  // 删除选中节点
  const deleteSelected = () => {
    if (!selectedNode) return
    setNodes(nds => nds.filter(n => n.id !== selectedNode))
    setEdges(eds => eds.filter(e => e.source !== selectedNode && e.target !== selectedNode))
    setSelectedNode(null)
  }

  // 选中节点
  const onNodeClick = useCallback((_: unknown, node: Node) => {
    setSelectedNode(node.id)
    setShowPanel(true)
  }, [])

  // 更新节点数据
  const updateNodeData = (id: string, patch: Partial<StepData>) => {
    setNodes(nds => nds.map(n => n.id === id ? { ...n, data: { ...n.data, ...patch } } : n))
  }

  // 保存
  const handleSave = async () => {
    const steps = canvasToSteps()
    if (!wfName || steps.length === 0) return

    const payload = { name: wfName, mode: wfMode, steps }

    if (selectedWf) {
      await apiPut(`/api/workflows/${selectedWf.id}`, payload)
    } else {
      await apiPost('/api/workflows', payload)
    }
    refresh()
  }

  // 运行
  const handleRun = async () => {
    if (!selectedWf || !runInput.trim()) return
    const res = await apiPost<{ run_id: string }>(`/api/workflows/${selectedWf.id}/run`, { input: runInput })
    setActiveRunId(res.run_id)
    setRunInput('')
  }

  // 轮询执行状态
  useEffect(() => {
    if (!activeRunId) return
    const poll = setInterval(async () => {
      try {
        const run = await apiGet<Record<string, unknown>>(`/api/workflows/run/${activeRunId}`)
        setActiveRun(run)
        if (['success', 'failed', 'aborted'].includes(run.status as string)) {
          clearInterval(poll)
        }
      } catch { /* */ }
    }, 2000)
    return () => clearInterval(poll)
  }, [activeRunId])

  // 删除工作流
  const handleDelete = async (id: string) => {
    await apiDelete(`/api/workflows/${id}`)
    if (selectedWf?.id === id) {
      setSelectedWf(null)
      setNodes([])
      setEdges([])
    }
    refresh()
  }

  const selectedNodeData = nodes.find(n => n.id === selectedNode)?.data as StepData | undefined
  const onlineInstances = instances.filter(i => i.status === 'online')

  const modeIcons: Record<string, typeof Zap> = { pipeline: Zap, roundtable: MessageCircle, review_loop: GitBranch, debate: Swords }

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏 */}
      <div className="h-12 border-b border-cockpit-border bg-cockpit-card flex items-center px-4 gap-3">
        <input
          type="text"
          value={wfName}
          onChange={e => setWfName(e.target.value)}
          placeholder="工作流名称"
          className="bg-cockpit-bg border border-cockpit-border rounded px-3 py-1 text-sm w-48"
        />
        <select
          value={wfMode}
          onChange={e => setWfMode(e.target.value)}
          className="bg-cockpit-bg border border-cockpit-border rounded px-3 py-1 text-sm"
        >
          <option value="pipeline">⚡ 流水线</option>
          <option value="roundtable">💬 圆桌</option>
          <option value="review_loop">🔄 审核</option>
          <option value="debate">⚔️ 辩论</option>
        </select>

        <div className="flex-1" />

        <button onClick={() => addNode('ai')} className="flex items-center gap-1 px-3 py-1 bg-cockpit-accent/20 text-cockpit-accent rounded text-sm hover:bg-cockpit-accent/30">
          <Plus size={14} /> AI 节点
        </button>
        <button onClick={() => addNode('human')} className="flex items-center gap-1 px-3 py-1 bg-green-500/20 text-green-400 rounded text-sm hover:bg-green-500/30">
          <User size={14} /> 人工
        </button>
        <button onClick={() => addNode('condition')} className="flex items-center gap-1 px-3 py-1 bg-yellow-500/20 text-yellow-400 rounded text-sm hover:bg-yellow-500/30">
          🔀 条件
        </button>
        <button onClick={deleteSelected} disabled={!selectedNode} className="p-1.5 text-gray-500 hover:text-cockpit-danger disabled:opacity-30">
          <Trash2 size={16} />
        </button>

        <div className="w-px h-6 bg-cockpit-border mx-1" />

        <button onClick={handleSave} className="flex items-center gap-1 px-3 py-1 bg-cockpit-accent rounded text-sm hover:opacity-80">
          <Save size={14} /> 保存
        </button>
      </div>

      <div className="flex-1 flex min-h-0">
        {/* 左侧：工作流列表 */}
        <div className="w-56 border-r border-cockpit-border bg-cockpit-card overflow-auto p-3 space-y-2">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">已保存</div>
          {workflows.map(wf => {
            const Icon = modeIcons[wf.mode] || Zap
            return (
              <div
                key={wf.id}
                onClick={() => loadWorkflowToCanvas(wf)}
                className={`p-2.5 rounded-lg cursor-pointer text-sm transition-colors ${
                  selectedWf?.id === wf.id ? 'bg-cockpit-accent/20 border border-cockpit-accent' : 'hover:bg-cockpit-border border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon size={14} className="text-gray-400" />
                  <span className="truncate">{wf.name}</span>
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{wf.steps.length} 步</div>
              </div>
            )
          })}

          <button
            onClick={() => { setSelectedWf(null); setWfName(''); setNodes([]); setEdges([]) }}
            className="w-full p-2 rounded-lg border border-dashed border-cockpit-border text-sm text-gray-500 hover:border-cockpit-accent hover:text-cockpit-accent"
          >
            + 新建空白
          </button>
        </div>

        {/* 中间：React Flow 画布 */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            className="!bg-cockpit-bg"
          >
            <Controls className="!bg-cockpit-card !border-cockpit-border" />
            <MiniMap
              className="!bg-cockpit-card !border-cockpit-border"
              nodeColor="#6366f1"
              maskColor="rgba(0,0,0,0.5)"
            />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#1e1e2e" />
          </ReactFlow>

          {/* 空状态 */}
          {nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center text-gray-600">
                <p className="text-lg mb-2">拖拽节点到画布</p>
                <p className="text-sm">从左侧选择工作流，或点上方按钮添加节点</p>
              </div>
            </div>
          )}

          {/* 执行面板 overlay */}
          {activeRun && (
            <div className="absolute bottom-4 right-4 w-96 bg-cockpit-card border border-cockpit-border rounded-xl shadow-2xl overflow-hidden z-10">
              <div className="p-3 border-b border-cockpit-border flex items-center justify-between">
                <span className="text-sm font-medium">{(activeRun as Record<string, unknown>).workflow_name as string}</span>
                <span className={`text-xs ${
                  (activeRun as Record<string, unknown>).status === 'success' ? 'text-cockpit-success' :
                  (activeRun as Record<string, unknown>).status === 'failed' ? 'text-cockpit-danger' : 'text-cockpit-accent'
                }`}>
                  {(activeRun as Record<string, unknown>).status as string}
                </span>
              </div>
              <div className="p-3 space-y-2 max-h-60 overflow-auto">
                {((activeRun as Record<string, unknown>).steps as Array<Record<string, unknown>>)?.map((step) => (
                  <div key={step.id as string} className="flex items-start gap-2 text-xs">
                    <span>{step.status === 'done' ? '✅' : step.status === 'failed' ? '❌' : step.status === 'running' ? '🔄' : '⏳'}</span>
                    <div>
                      <span className="font-medium">{step.name as string}</span>
                      {step.output && <div className="text-gray-500 mt-0.5 max-h-16 overflow-hidden">{(step.output as string).slice(0, 100)}...</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 右侧：属性面板 */}
        {showPanel && selectedNodeData && (
          <div className="w-72 border-l border-cockpit-border bg-cockpit-card overflow-auto p-4 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">节点属性</span>
              <button onClick={() => setShowPanel(false)} className="text-gray-500 hover:text-white text-xs">✕</button>
            </div>

            <div>
              <label className="text-xs text-gray-400 block mb-1">名称</label>
              <input
                type="text"
                value={selectedNodeData.label}
                onChange={e => updateNodeData(selectedNode!, { label: e.target.value })}
                className="w-full bg-cockpit-bg border border-cockpit-border rounded px-2 py-1.5 text-sm"
              />
            </div>

            <div>
              <label className="text-xs text-gray-400 block mb-1">实例</label>
              <select
                value={selectedNodeData.instanceId}
                onChange={e => updateNodeData(selectedNode!, { instanceId: e.target.value })}
                className="w-full bg-cockpit-bg border border-cockpit-border rounded px-2 py-1.5 text-sm"
              >
                <option value="">选择实例</option>
                {onlineInstances.map(inst => (
                  <option key={inst.account_id} value={inst.account_id}>
                    {inst.display_name} ({inst.platform})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs text-gray-400 block mb-1">Prompt 模板</label>
              <textarea
                value={selectedNodeData.promptTemplate}
                onChange={e => updateNodeData(selectedNode!, { promptTemplate: e.target.value })}
                placeholder="支持 {user.input}, {prev.output}"
                rows={6}
                className="w-full bg-cockpit-bg border border-cockpit-border rounded px-2 py-1.5 text-sm resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-gray-400 block mb-1">超时(秒)</label>
                <input
                  type="number"
                  value={selectedNodeData.timeout}
                  onChange={e => updateNodeData(selectedNode!, { timeout: Number(e.target.value) })}
                  className="w-full bg-cockpit-bg border border-cockpit-border rounded px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">重试</label>
                <input
                  type="number"
                  value={selectedNodeData.retries}
                  onChange={e => updateNodeData(selectedNode!, { retries: Number(e.target.value) })}
                  className="w-full bg-cockpit-bg border border-cockpit-border rounded px-2 py-1.5 text-sm"
                />
              </div>
            </div>

            {/* 运行区 */}
            {selectedWf && (
              <div className="pt-3 border-t border-cockpit-border space-y-2">
                <input
                  type="text"
                  value={runInput}
                  onChange={e => setRunInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleRun()}
                  placeholder="输入内容，回车运行..."
                  className="w-full bg-cockpit-bg border border-cockpit-border rounded px-2 py-1.5 text-sm"
                />
                <button onClick={handleRun} className="w-full flex items-center justify-center gap-1 py-1.5 bg-cockpit-accent rounded text-sm hover:opacity-80">
                  <Play size={14} /> 运行工作流
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// Re-export apiPut since it's used
async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}
