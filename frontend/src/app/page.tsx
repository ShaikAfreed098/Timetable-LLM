"use client";

import { useState } from "react";
import Chat from "@/components/Chat";
import TimetableGrid from "@/components/TimetableGrid";
import LoginForm from "@/components/LoginForm";
import { useAuthStore } from "@/store/auth";

export default function HomePage() {
  const { token } = useAuthStore();
  const [activeTab, setActiveTab] = useState<"chat" | "timetable">("chat");
  const [timetableId, setTimetableId] = useState<string | null>(null);

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <LoginForm />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-primary text-white px-6 py-4 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
            <span className="text-primary font-bold text-sm">T</span>
          </div>
          <h1 className="text-xl font-bold">Timetable LLM</h1>
        </div>
        <nav className="flex gap-2">
          <button
            onClick={() => setActiveTab("chat")}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              activeTab === "chat"
                ? "bg-white text-primary"
                : "text-white/80 hover:bg-white/20"
            }`}
          >
            Chat
          </button>
          <button
            onClick={() => setActiveTab("timetable")}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              activeTab === "timetable"
                ? "bg-white text-primary"
                : "text-white/80 hover:bg-white/20"
            }`}
          >
            Timetable
          </button>
        </nav>
        <LogoutButton />
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {activeTab === "chat" ? (
          <Chat onTimetableGenerated={setTimetableId} />
        ) : (
          <TimetableGrid timetableId={timetableId} />
        )}
      </main>
    </div>
  );
}

function LogoutButton() {
  const { logout } = useAuthStore();
  return (
    <button
      onClick={logout}
      className="text-sm text-white/80 hover:text-white transition-colors"
    >
      Logout
    </button>
  );
}
