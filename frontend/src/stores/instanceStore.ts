import { create } from 'zustand'

export interface InstanceState {
  account_id: string
  platform: string
  display_name: string
  status: string
  pid: number | null
  uptime_seconds: number
  last_error: string | null
  screenshot_url: string | null
}

interface InstanceStore {
  instances: InstanceState[]
  setInstances: (instances: InstanceState[]) => void
  updateInstance: (id: string, patch: Partial<InstanceState>) => void
}

export const useInstanceStore = create<InstanceStore>((set) => ({
  instances: [],
  setInstances: (instances) => set({ instances }),
  updateInstance: (id, patch) =>
    set((state) => ({
      instances: state.instances.map((inst) =>
        inst.account_id === id ? { ...inst, ...patch } : inst
      ),
    })),
}))
