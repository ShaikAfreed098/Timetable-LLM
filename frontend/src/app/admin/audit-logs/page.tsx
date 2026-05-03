"use client";

import { useEffect, useState } from "react";
import { fetchAuditLogs, AuditLog } from "@/lib/api";
import { toast } from "sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, RefreshCw, ShieldCheck, ChevronLeft, ChevronRight } from "lucide-react";
import { format } from "date-fns";

const LIMIT = 20;

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  const loadLogs = async (currentOffset: number) => {
    setLoading(true);
    try {
      const data = await fetchAuditLogs(LIMIT, currentOffset);
      setLogs(data.items);
      setTotal(data.total);
    } catch (err: any) {
      toast.error("Failed to load audit logs: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs(offset);
  }, [offset]);

  const handleNext = () => {
    if (offset + LIMIT < total) {
      setOffset(offset + LIMIT);
    }
  };

  const handlePrev = () => {
    if (offset - LIMIT >= 0) {
      setOffset(offset - LIMIT);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">System Audit Logs</h1>
        <Button onClick={() => loadLogs(offset)} variant="outline" size="icon">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      <Card className="glass-card border-white/10 bg-white/5 backdrop-blur-md overflow-hidden">
        <CardHeader className="border-b border-white/10">
          <CardTitle className="flex items-center gap-2 text-lg">
            <ShieldCheck className="w-5 h-5 text-green-400" />
            Activity History ({total} total entries)
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-white/5">
              <TableRow className="border-white/10 hover:bg-transparent">
                <TableHead>Timestamp</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Entity</TableHead>
                <TableHead>User ID</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead className="text-right">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i} className="border-white/10">
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}><div className="h-4 w-full bg-white/10 animate-pulse rounded" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">
                    No audit logs found.
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log) => (
                  <TableRow key={log.id} className="border-white/10 hover:bg-white/5 transition-colors">
                    <TableCell className="font-mono text-xs">
                      {format(new Date(log.created_at), "yyyy-MM-dd HH:mm:ss")}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                        {log.action}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {log.entity_type && (
                        <span className="text-xs text-muted-foreground">
                          {log.entity_type} <span className="text-zinc-500">#{log.entity_id}</span>
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-zinc-400">{log.user_id || "System"}</TableCell>
                    <TableCell className="text-xs text-zinc-500">{log.ip_address || "N/A"}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" onClick={() => {
                        console.log(log.details);
                        toast.info("Details logged to console");
                      }}>
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="flex items-center justify-end space-x-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrev}
          disabled={offset === 0 || loading}
          className="gap-1"
        >
          <ChevronLeft className="w-4 h-4" /> Previous
        </Button>
        <div className="text-xs text-muted-foreground px-4">
          Showing {offset + 1} to {Math.min(offset + LIMIT, total)} of {total}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleNext}
          disabled={offset + LIMIT >= total || loading}
          className="gap-1"
        >
          Next <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
