"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { auth } from "@/lib/firebase";
import { GoogleAuthProvider, signInWithPopup, createUserWithEmailAndPassword } from "firebase/auth";

export default function InvitePage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;
  const { login } = useAuthStore();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [invite, setInvite] = useState<{ email: string; role: string } | null>(null);
  
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"choose" | "password">("choose");
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    api.get(`/api/invites/${token}`)
      .then(res => setInvite(res.data))
      .catch(err => setError(err.response?.data?.detail || "Invalid or expired invite token."))
      .finally(() => setLoading(false));
  }, [token]);

  const finishLogin = async () => {
    try {
      const meResp = await api.get("/api/auth/me");
      login(meResp.data.username, meResp.data.role);
      router.push("/");
    } catch (err: any) {
      setError("Failed to fetch user profile after login.");
    }
  };

  const handleGoogleSignIn = async () => {
    setActionLoading(true);
    setError("");
    try {
      const provider = new GoogleAuthProvider();
      // Ensure the user signs in with the invited email
      provider.setCustomParameters({ login_hint: invite?.email || "" });
      const userCred = await signInWithPopup(auth, provider);
      const idToken = await userCred.user.getIdToken();
      
      // The backend /api/auth/google endpoint will verify token, find invite, and create user
      await api.post("/api/auth/google", { token: idToken });
      await finishLogin();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Google Authentication failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handlePasswordSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invite) return;
    setActionLoading(true);
    setError("");
    try {
      // Create user in Firebase with email/password
      const userCred = await createUserWithEmailAndPassword(auth, invite.email, password);
      const idToken = await userCred.user.getIdToken();
      
      // Validate invite and create local DB user
      await api.post(`/api/invites/${token}/accept`, { password });
      
      // Sign in to get access cookie
      const formData = new FormData();
      formData.append("username", invite.email);
      formData.append("password", password);
      await api.post("/api/auth/token", formData);
      
      await finishLogin();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to set up password.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="flex justify-center p-20"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" /></div>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-white text-2xl font-bold">✉️</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Invitation to Join</h1>
        </div>

        {error ? (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg text-center">
            {error}
          </div>
        ) : invite ? (
          <>
            <p className="text-gray-600 text-center mb-6">
              You have been invited as <strong>{invite.role.replace("_", " ")}</strong>. 
              <br /> Email: {invite.email}
            </p>

            {mode === "choose" ? (
              <div className="space-y-4">
                <button
                  disabled={actionLoading}
                  onClick={handleGoogleSignIn}
                  className="w-full bg-white border border-gray-300 text-gray-700 py-3 rounded-lg font-medium hover:bg-gray-50 transition-colors disabled:opacity-60 flex items-center justify-center gap-2 shadow-sm"
                >
                  <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
                    <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
                    <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
                    <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
                    <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
                  </svg>
                  Accept & Sign in with Google
                </button>
                
                <div className="relative flex py-2 items-center">
                    <div className="flex-grow border-t border-gray-300"></div>
                    <span className="flex-shrink-0 mx-4 text-gray-400 text-xs">OR</span>
                    <div className="flex-grow border-t border-gray-300"></div>
                </div>

                <button
                  disabled={actionLoading}
                  onClick={() => setMode("password")}
                  className="w-full bg-gray-100 text-gray-700 py-3 rounded-lg font-medium hover:bg-gray-200 transition-colors disabled:opacity-60"
                >
                  Set up a password
                </button>
              </div>
            ) : (
              <form onSubmit={handlePasswordSetup} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Create Password
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary outline-none"
                    minLength={6}
                  />
                </div>
                
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-60"
                >
                  {actionLoading ? "Saving..." : "Create Account"}
                </button>
                
                <button
                  type="button"
                  onClick={() => setMode("choose")}
                  className="w-full text-gray-500 text-sm hover:underline"
                >
                  Back
                </button>
              </form>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}
