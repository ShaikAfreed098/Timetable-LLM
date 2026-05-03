"use client";

import React, { useState, useEffect } from "react";
import RoleGuard from "@/components/RoleGuard";
import { fetchInvites, createInvite } from "@/lib/api"; // I'll need to ensure these exist in api.ts

export default function AdminInvitesPage() {
  const [invites, setInvites] = useState<any[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("department_admin");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadInvites();
  }, []);

  const loadInvites = async () => {
    try {
      const data = await fetchInvites();
      setInvites(data);
    } catch (error) {
      console.error("Failed to load invites", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createInvite({ email, role });
      setEmail("");
      loadInvites();
    } catch (error) {
      alert("Failed to create invite");
    }
  };

  return (
    <RoleGuard allowedRoles={["super_admin", "department_admin"]}>
      <div className="p-8 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Manage Invitations</h1>
        
        <form onSubmit={handleCreate} className="bg-white p-6 rounded-xl shadow mb-8 flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Email Address</label>
            <input 
              type="email" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              className="w-full border rounded-lg px-3 py-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Role</label>
            <select 
              value={role} 
              onChange={e => setRole(e.target.value)}
              className="border rounded-lg px-3 py-2"
            >
              <option value="department_admin">Department Admin</option>
              <option value="faculty">Faculty</option>
            </select>
          </div>
          <button type="submit" className="bg-primary text-white px-6 py-2 rounded-lg font-medium">
            Send Invite
          </button>
        </form>

        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left">Email</th>
                <th className="px-6 py-3 text-left">Role</th>
                <th className="px-6 py-3 text-left">Status</th>
                <th className="px-6 py-3 text-left">Sent</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {loading ? (
                <tr><td colSpan={4} className="px-6 py-4 text-center">Loading...</td></tr>
              ) : invites.length === 0 ? (
                <tr><td colSpan={4} className="px-6 py-4 text-center text-gray-500">No invites sent yet.</td></tr>
              ) : invites.map(invite => (
                <tr key={invite.id}>
                  <td className="px-6 py-4">{invite.email}</td>
                  <td className="px-6 py-4 capitalize">{invite.role}</td>
                  <td className="px-6 py-4">
                    {invite.used_at ? (
                      <span className="text-green-600 font-medium">Accepted</span>
                    ) : new Date(invite.expires_at) < new Date() ? (
                      <span className="text-red-600 font-medium">Expired</span>
                    ) : (
                      <span className="text-blue-600 font-medium">Pending</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {new Date(invite.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </RoleGuard>
  );
}
