"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

export default function RoleGuard({ children, allowedRoles }: { children: React.ReactNode, allowedRoles: string[] }) {
  const { role, username } = useAuthStore();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && (!username || !role || !allowedRoles.includes(role))) {
      router.push("/");
    }
  }, [role, username, router, allowedRoles, mounted]);

  if (!mounted || !username || !role || !allowedRoles.includes(role)) {
    return null;
  }

  return <>{children}</>;
}
