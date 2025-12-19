import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface WorkflowState {
  activeId: string | null;
  setActiveId: (id: string | null) => void;
}

export const useWorkflowStore = create<WorkflowState>()(
  persist(
    (set) => ({
      activeId: null,
      setActiveId: (id) => set({ activeId: id }),
    }),
    {
      name: 'active-workflow-id', // LocalStorage key
      storage: createJSONStorage(() => localStorage), // 自动处理 SSR/Window check
      // 自动处理跨 Tab 同步 (storage 事件)
    }
  )
);
