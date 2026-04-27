"use client";

import { useState } from "react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { auth } from "@/lib/firebase";
import { createUserWithEmailAndPassword, signInWithEmailAndPassword, GoogleAuthProvider, signInWithPopup } from "firebase/auth";

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

  const finishLogin = async () => {
    try {
      const meResp = await api.get("/api/auth/me");
      login(meResp.data.username, meResp.data.role);
    } catch (err: any) {
      throw err;
    }
  };

  const handleGoogleSignIn = async () => {
    setError("");
    setLoading(true);
    try {
      const provider = new GoogleAuthProvider();
      const userCred = await signInWithPopup(auth, provider);
      const token = await userCred.user.getIdToken();
      
      await api.post("/api/auth/google", { token });
      await finishLogin();
    } catch (err: any) {
      const msg = err?.response?.data?.detail 
        || err.message 
        || "Google Authentication failed.";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") {
        const userCred = await createUserWithEmailAndPassword(auth, form.email, form.password);
        const token = await userCred.user.getIdToken();
        await api.post("/api/auth/register", form);
        await api.post("/api/auth/google", { token });
        await finishLogin();
      } else {
        const formData = new FormData();
        formData.append("username", form.username || form.email);
        formData.append("password", form.password);
        await api.post("/api/auth/token", formData);
        await finishLogin();
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail 
        || err.message 
        || "Authentication failed.";
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
          suppressHydrationWarning
          onClick={() => setMode("login")}
          className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
            mode === "login" ? "bg-white shadow text-primary" : "text-gray-500"
          }`}
        >
          Login
        </button>
        <button
          suppressHydrationWarning
          onClick={() => setMode("register")}
          className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
            mode === "register" ? "bg-white shadow text-primary" : "text-gray-500"
          }`}
        >
          Register
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === "register" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
              suppressHydrationWarning
              type="text"
              required
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <input
            suppressHydrationWarning
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {mode === "register" && (
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
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <input
            suppressHydrationWarning
            type="password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {error && (
          <p className="text-red-500 text-sm bg-red-50 rounded-lg px-3 py-2 break-words">
            {error}
          </p>
        )}

        <button
          suppressHydrationWarning
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-60 mb-2"
        >
          {loading ? "Please wait…" : mode === "login" ? "Login" : "Register"}
        </button>

        <div className="relative flex py-2 items-center">
            <div className="flex-grow border-t border-gray-300"></div>
            <span className="flex-shrink-0 mx-4 text-gray-400 text-xs">OR</span>
            <div className="flex-grow border-t border-gray-300"></div>
        </div>

        <button
          suppressHydrationWarning
          type="button"
          disabled={loading}
          onClick={handleGoogleSignIn}
          className="w-full bg-white border border-gray-300 text-gray-700 py-2.5 rounded-lg font-medium hover:bg-gray-50 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
        >
          <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
            <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
            <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
            <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
            <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
          </svg>
          Sign in with Google
        </button>
      </form>
    </div>
  );
}
