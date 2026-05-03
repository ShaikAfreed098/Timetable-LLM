"use client";

import RoleGuard from "@/components/RoleGuard";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard allowedRoles={["super_admin"]}>
      <div className="container mx-auto py-8">
        {children}
      </div>
    </RoleGuard>
  );
}
