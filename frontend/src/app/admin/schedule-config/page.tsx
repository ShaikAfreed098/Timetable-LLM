"use client";

import { useEffect, useState } from "react";
import { fetchScheduleConfig, updateScheduleConfig, ScheduleConfig } from "@/lib/api";
import { toast } from "sonner";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Loader2, Save } from "lucide-react";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function ScheduleConfigPage() {
  const [config, setConfig] = useState<ScheduleConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchScheduleConfig()
      .then(setConfig)
      .catch((err) => toast.error("Failed to load config: " + err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await updateScheduleConfig(config);
      toast.success("Schedule configuration updated");
    } catch (err: any) {
      toast.error("Failed to save config: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!config) return null;

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Schedule Configuration</h1>
        <Button onClick={handleSave} disabled={saving} className="gap-2">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Changes
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="glass-card border-white/10 bg-white/5 backdrop-blur-md">
          <CardHeader>
            <CardTitle>Working Days</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {DAYS.map((day) => (
              <div key={day} className="flex items-center space-x-2">
                <Checkbox
                  id={`day-${day}`}
                  checked={config.working_days.includes(day)}
                  onCheckedChange={(checked) => {
                    const newDays = checked
                      ? [...config.working_days, day]
                      : config.working_days.filter((d) => d !== day);
                    // Sort by DAYS order
                    const sortedDays = DAYS.filter(d => newDays.includes(d));
                    setConfig({ ...config, working_days: sortedDays });
                  }}
                />
                <Label htmlFor={`day-${day}`} className="cursor-pointer">
                  {day}
                </Label>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="glass-card border-white/10 bg-white/5 backdrop-blur-md">
          <CardHeader>
            <CardTitle>Daily Periods</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="periods">Teaching Periods per Day</Label>
              <Input
                id="periods"
                type="number"
                min={1}
                max={12}
                value={config.periods_per_day}
                onChange={(e) => {
                  const val = parseInt(e.target.value) || 1;
                  setConfig({ ...config, periods_per_day: val });
                }}
                className="bg-white/10 border-white/20"
              />
            </div>

            <div className="space-y-4 pt-4 border-t border-white/10">
              <Label>Period Timings</Label>
              <div className="grid gap-4">
                {Array.from({ length: config.periods_per_day }).map((_, i) => {
                  const pNum = (i + 1).toString();
                  return (
                    <div key={pNum} className="flex items-center gap-4">
                      <span className="w-20 text-sm font-medium text-muted-foreground">
                        Period {pNum}
                      </span>
                      <Input
                        placeholder="e.g. 09:00-10:00"
                        value={config.period_times[pNum] || ""}
                        onChange={(e) => {
                          setConfig({
                            ...config,
                            period_times: {
                              ...config.period_times,
                              [pNum]: e.target.value,
                            },
                          });
                        }}
                        className="bg-white/10 border-white/20"
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
