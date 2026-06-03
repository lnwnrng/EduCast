import { create } from 'zustand';

const PROJECT_KEY = 'educast.currentProjectId';

interface AppState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  /** 最近进入的项目 id，用于侧边栏「工作台」直达 */
  currentProjectId: string | null;
  setCurrentProject: (id: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  currentProjectId:
    typeof localStorage !== 'undefined' ? localStorage.getItem(PROJECT_KEY) : null,
  setCurrentProject: (id) => {
    if (typeof localStorage !== 'undefined') {
      if (id) localStorage.setItem(PROJECT_KEY, id);
      else localStorage.removeItem(PROJECT_KEY);
    }
    set({ currentProjectId: id });
  },
}));
