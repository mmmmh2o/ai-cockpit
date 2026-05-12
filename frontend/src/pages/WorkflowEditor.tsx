export default function WorkflowEditor() {
  return (
    <div className="p-6 h-full flex flex-col">
      <h1 className="text-2xl font-bold mb-6">🔗 工作流编辑器</h1>

      <div className="flex-1 bg-cockpit-card border border-cockpit-border rounded-xl flex items-center justify-center">
        <div className="text-center text-gray-600">
          <svg className="mx-auto mb-4" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 3v3m6.36-.64-2.12 2.12M21 12h-3M18.36 18.36l-2.12-2.12M12 21v-3m-4.24.64 2.12-2.12M3 12h3M5.64 5.64l2.12 2.12" />
          </svg>
          <p className="text-lg mb-2">工作流编辑器</p>
          <p className="text-sm">拖拽节点、连线编排 AI 协同工作流</p>
          <p className="text-sm mt-4 text-gray-700">Phase 3 实现</p>
        </div>
      </div>
    </div>
  )
}
