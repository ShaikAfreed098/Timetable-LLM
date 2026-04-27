import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  username: string | null;
  role: string | null;
  login: (username: string, role: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      username: null,
      role: null,
      login: (username, role) => set({ username, role }),
      logout: () => set({ username: null, role: null }),
    }),
    { name: "timetable-auth" }
  )
);
