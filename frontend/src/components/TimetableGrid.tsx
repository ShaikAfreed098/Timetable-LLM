"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const TEACHING_PERIODS = [1, 2, 3, 4, 5, 6, 7];
const PERIOD_TIMES: Record<number, string> = {
  1: "09:10–10:00",
  2: "10:00–10:50",
  3: "11:00–11:50",
  4: "11:50–12:40",
  5: "13:30–14:20",
  6: "14:20–15:10",
  7: "15:10–16:00",
};

interface SlotData {
  id: number;
  day_of_week: string;
  period_number: number;
  slot_type: string;
  subject?: { name: string; code: string } | null;
  faculty?: { name: string } | null;
  room?: { room_number: string } | null;
  batch_id: number;
}

interface TimetableGridProps {
  timetableId: string | null;
}

export default function TimetableGrid({ timetableId }: TimetableGridProps) {
  const [slots, setSlots] = useState<SlotData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [inputId, setInputId] = useState("");
  const [batchIds, setBatchIds] = useState<number[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<number | null>(null);

  useEffect(() => {
    if (timetableId) {
      setInputId(timetableId);
      loadTimetable(timetableId);
    }
  }, [timetableId]);

  const loadTimetable = async (id: string) => {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get(`/api/timetable/${id}`);
      const data: SlotData[] = resp.data;
      setSlots(data);
      const ids = [...new Set(data.map((s) => s.batch_id))];
      setBatchIds(ids);
      setSelectedBatch(ids[0] ?? null);
    } catch {
      setError("Failed to load timetable. Check the timetable ID.");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: "pdf" | "excel") => {
    if (!inputId) return;
    try {
      const resp = await api.post(
        `/api/timetable/${inputId}/export?format=${format}`,
        {},
        { responseType: "blob" }
      );
      const url = window.URL.createObjectURL(resp.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `timetable_${inputId}.${format === "excel" ? "xlsx" : "pdf"}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      setError("Export failed.");
    }
  };

  const filteredSlots = slots.filter((s) => s.batch_id === selectedBatch);

  const getSlot = (day: string, period: number) =>
    filteredSlots.find(
      (s) => s.day_of_week === day && s.period_number === period
    );

  return (
    <div className="p-6" style={{ height: "calc(100vh - 64px)", overflowY: "auto" }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <input
          type="text"
          placeholder="Enter timetable ID…"
          value={inputId}
          onChange={(e) => setInputId(e.target.value)}
          className="border rounded-lg px-4 py-2 text-sm w-80 focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <button
          onClick={() => loadTimetable(inputId)}
          disabled={!inputId || loading}
          className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {loading ? "Loading…" : "Load"}
        </button>

        {slots.length > 0 && (
          <>
            <button
              onClick={() => handleExport("pdf")}
              className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600 transition-colors"
            >
              Export PDF
            </button>
            <button
              onClick={() => handleExport("excel")}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
            >
              Export Excel
            </button>
          </>
        )}
      </div>

      {/* Batch selector */}
      {batchIds.length > 1 && (
        <div className="flex gap-2 mb-4">
          {batchIds.map((id) => (
            <button
              key={id}
              onClick={() => setSelectedBatch(id)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                selectedBatch === id
                  ? "bg-primary text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              Batch {id}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">
          {error}
        </div>
      )}

      {slots.length === 0 && !loading && !error && (
        <div className="text-center py-20 text-gray-400">
          <div className="text-6xl mb-4">📅</div>
          <p className="text-lg font-medium">No timetable loaded</p>
          <p className="text-sm mt-1">
            Generate a timetable via Chat or enter a timetable ID above
          </p>
        </div>
      )}

      {/* Grid */}
      {slots.length > 0 && selectedBatch !== null && (
        <div className="bg-white rounded-xl shadow overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr>
                <th className="bg-primary text-white px-4 py-3 text-left font-semibold border border-blue-400 min-w-[120px]">
                  Day / Period
                </th>
                {TEACHING_PERIODS.map((p) => (
                  <th
                    key={p}
                    className="bg-primary text-white px-3 py-3 text-center font-semibold border border-blue-400 min-w-[130px]"
                  >
                    <div>P{p}</div>
                    <div className="text-xs font-normal opacity-80">
                      {PERIOD_TIMES[p]}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DAYS.map((day, dIdx) => (
                <tr
                  key={day}
                  className={dIdx % 2 === 0 ? "bg-white" : "bg-blue-50/40"}
                >
                  <td className="px-4 py-3 font-semibold text-gray-700 border border-gray-200">
                    {day}
                  </td>
                  {TEACHING_PERIODS.map((p) => {
                    const slot = getSlot(day, p);
                    return (
                      <td
                        key={p}
                        className="px-2 py-2 border border-gray-200 text-center align-top"
                      >
                        {slot && slot.slot_type === "class" && slot.subject ? (
                          <SlotCell slot={slot} />
                        ) : (
                          <span className="text-gray-300 text-xs">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Legend */}
          <div className="px-4 py-3 border-t bg-gray-50 flex gap-4 text-xs text-gray-500">
            <span>
              <strong>Break:</strong> 10:50–11:00
            </span>
            <span>
              <strong>Lunch:</strong> 12:40–13:30
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function SlotCell({ slot }: { slot: SlotData }) {
  return (
    <div className="bg-blue-50 border border-blue-100 rounded-lg p-1.5 text-left">
      <div className="font-semibold text-blue-900 text-xs truncate">
        {slot.subject?.code}
      </div>
      <div className="text-gray-600 text-xs truncate mt-0.5">
        {slot.subject?.name}
      </div>
      {slot.faculty && (
        <div className="text-gray-500 text-xs mt-0.5 truncate">
          {slot.faculty.name}
        </div>
      )}
      {slot.room && (
        <div className="text-xs text-gray-400 mt-0.5">
          Room: {slot.room.room_number}
        </div>
      )}
    </div>
  );
}
