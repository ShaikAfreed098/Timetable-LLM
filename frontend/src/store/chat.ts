import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatState {
  messages: Message[];
  sessionId: string;
  addMessage: (msg: Message) => void;
  updateLastMessage: (content: string) => void;
  appendErrorToLastMessage: (err: string) => void;
  replaceLastMessageError: (errMsg: string) => void;
  clearMessages: () => void;
}

const initialMessages: Message[] = [
  {
    role: "assistant",
    content:
      "Hello! I'm your Timetable AI assistant. I can help you manage faculty, subjects, rooms, batches, and generate conflict-free timetables.\n\nTry saying:\n- \"Add Dr. Ramesh Kumar from CSE department, max 5 periods per day\"\n- \"Generate timetable for CSE 3rd semester\"\n- \"Check conflicts for timetable [id]\"",
  },
];

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: initialMessages,
      sessionId: Math.random().toString(36).slice(2),
      
      addMessage: (msg) => 
        set((state) => ({ messages: [...state.messages, msg] })),
      
      updateLastMessage: (content) =>
        set((state) => {
          const updated = [...state.messages];
          if (updated.length > 0) {
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content,
            };
          }
          return { messages: updated };
        }),
        
      appendErrorToLastMessage: (err) =>
        set((state) => {
          const updated = [...state.messages];
          if (updated.length > 0) {
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: updated[updated.length - 1].content + `\n⚠️ Error: ${err}`,
            };
          }
          return { messages: updated };
        }),
        
      replaceLastMessageError: (errMsg) =>
        set((state) => {
          const updated = [...state.messages];
          if (updated.length > 0) {
            updated[updated.length - 1] = {
              role: "assistant",
              content: `⚠️ ${errMsg}`,
            };
          }
          return { messages: updated };
        }),

      clearMessages: () => 
        set({ 
          messages: initialMessages, 
          sessionId: Math.random().toString(36).slice(2) 
        }),
    }),
    {
      name: "timetable-chat-storage",
      storage: createJSONStorage(() => 
        typeof window !== "undefined" ? sessionStorage : ({} as any)
      ),
    }
  )
);
