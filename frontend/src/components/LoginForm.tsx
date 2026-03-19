"use client";

import { useState } from "react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function LoginForm() {
  const { login } = useAuthStore();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    role: "department_admin",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") {
        await api.post("/api/auth/register", form);
      }
      // Login
      const fd = new URLSearchParams();
      fd.append("username", form.username);
      fd.append("password", form.password);
      const resp = await api.post("/api/auth/token", fd, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      const meResp = await api.get("/api/auth/me", {
        headers: { Authorization: `Bearer ${resp.data.access_token}` },
      });
      login(resp.data.access_token, meResp.data.username, meResp.data.role);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Authentication failed.";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
      <div className="text-center mb-6">
        <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-white text-2xl font-bold">T</span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Timetable LLM</h1>
        <p className="text-gray-500 text-sm mt-1">AI-Powered College Scheduling</p>
      </div>

      <div className="flex gap-2 mb-6 bg-gray-100 p-1 rounded-lg">
        <button
          onClick={() => setMode("login")}
          className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
            mode === "login" ? "bg-white shadow text-primary" : "text-gray-500"
          }`}
        >
          Login
        </button>
        <button
          onClick={() => setMode("register")}
          className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
            mode === "register" ? "bg-white shadow text-primary" : "text-gray-500"
          }`}
        >
          Register
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Username
          </label>
          <input
            type="text"
            required
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {mode === "register" && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Role
              </label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="super_admin">Super Admin</option>
                <option value="department_admin">Department Admin</option>
                <option value="faculty">Faculty</option>
              </select>
            </div>
          </>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <input
            type="password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {error && (
          <p className="text-red-500 text-sm bg-red-50 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-60"
        >
          {loading ? "Please wait…" : mode === "login" ? "Login" : "Register"}
        </button>
      </form>
    </div>
  );
}
