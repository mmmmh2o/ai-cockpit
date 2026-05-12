import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { Monitor, Users, Workflow, LayoutDashboard, GitCompare } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import LiveView from './pages/LiveView'
import WorkflowEditor from './pages/WorkflowEditor'
import CompareView from './pages/CompareView'

const navItems = [
  { path: '/', label: '总览', icon: LayoutDashboard },
  { path: '/accounts', label: '账号', icon: Users },
  { path: '/live', label: '实时', icon: Monitor },
  { path: '/workflows', label: '工作流', icon: Workflow },
  { path: '/compare', label: '对比', icon: GitCompare },
]

export default function App() {
  const location = useLocation()

  return (
    <div className="flex h-screen">
      {/* 侧边栏 */}
      <aside className="w-16 bg-cockpit-card border-r border-cockpit-border flex flex-col items-center py-4 gap-2">
        <div className="text-2xl mb-4">🎮</div>
        {navItems.map((item) => {
          const Icon = item.icon
          const active = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors
                ${active ? 'bg-cockpit-accent text-white' : 'text-gray-500 hover:text-white hover:bg-cockpit-border'}`}
              title={item.label}
            >
              <Icon size={20} />
            </Link>
          )
        })}
      </aside>

      {/* 主内容 */}
      <main className="flex-1 overflow-auto bg-cockpit-bg">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/live/:id?" element={<LiveView />} />
          <Route path="/workflows" element={<WorkflowEditor />} />
          <Route path="/compare" element={<CompareView />} />
        </Routes>
      </main>
    </div>
  )
}
