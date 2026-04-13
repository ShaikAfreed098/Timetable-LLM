"use client";

import { useState, useEffect, useCallback } from "react";
import Chat from "@/components/Chat";
import TimetableGrid from "@/components/TimetableGrid";
import LoginForm from "@/components/LoginForm";
import { useAuthStore } from "@/store/auth";
import {
  Faculty, Subject, Room, Batch, Assignment,
  fetchFaculty, createFaculty, deleteFaculty,
  fetchSubjects, createSubject, deleteSubject,
  fetchRooms, createRoom, deleteRoom,
  fetchBatches, createBatch, deleteBatch,
  fetchAssignments, createAssignment, deleteAssignment,
} from "@/lib/api";

type Section = "chat" | "timetable" | "faculty" | "subjects" | "rooms" | "batches" | "assignments";

const NAV_ITEMS: { id: Section; label: string; icon: string }[] = [
  { id: "chat",        label: "AI Chat",     icon: "💬" },
  { id: "timetable",  label: "Timetable",   icon: "📅" },
  { id: "faculty",    label: "Faculty",     icon: "👩‍🏫" },
  { id: "subjects",   label: "Subjects",    icon: "📚" },
  { id: "rooms",      label: "Rooms",       icon: "🏫" },
  { id: "batches",    label: "Batches",     icon: "👥" },
  { id: "assignments",label: "Assignments", icon: "🔗" },
];

// ─── Shared helpers ────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function EmptyState({ icon, title, sub }: { icon: string; title: string; sub: string }) {
  return (
    <div className="text-center py-20 text-gray-400">
      <div className="text-5xl mb-3">{icon}</div>
      <p className="font-medium text-gray-500">{title}</p>
      <p className="text-sm mt-1">{sub}</p>
    </div>
  );
}

interface ModalProps { title: string; onClose: () => void; children: React.ReactNode }
function Modal({ title, onClose, children }: ModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="px-6 py-4 border-b flex items-center justify-between bg-primary text-white">
          <h2 className="font-semibold text-lg">{title}</h2>
          <button onClick={onClose} className="text-white/70 hover:text-white text-2xl leading-none">×</button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

function FormField({
  label, name, type = "text", value, onChange, required, min, options
}: {
  label: string; name: string; type?: string;
  value: string | number; onChange: (v: string) => void;
  required?: boolean; min?: number;
  options?: { value: string; label: string }[];
}) {
  const cls = "w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary mt-1";
  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      {options ? (
        <select className={cls} value={value} onChange={e => onChange(e.target.value)} required={required}>
          {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      ) : (
        <input className={cls} type={type} value={value} min={min}
          onChange={e => onChange(e.target.value)} required={required} />
      )}
    </div>
  );
}

function DeleteBtn({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="text-red-400 hover:text-red-600 transition-colors text-sm font-medium px-2 py-1 rounded hover:bg-red-50">
      Delete
    </button>
  );
}

function TableHeader({ cols }: { cols: string[] }) {
  return (
    <thead className="bg-primary text-white text-left text-xs uppercase tracking-wider">
      <tr>{cols.map(c => <th key={c} className="px-4 py-3 font-semibold">{c}</th>)}</tr>
    </thead>
  );
}

// ─── Faculty Section ──────────────────────────────────────────────────────────

function FacultySection() {
  const [data, setData] = useState<Faculty[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: "", department: "", email: "", max_periods_per_day: "5" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await fetchFaculty()); } catch { setError("Failed to load faculty."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await createFaculty({ ...form, max_periods_per_day: Number(form.max_periods_per_day) });
      setShowModal(false);
      setForm({ name: "", department: "", email: "", max_periods_per_day: "5" });
      load();
    } catch { setError("Failed to create faculty."); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this faculty?")) return;
    try { await deleteFaculty(id); load(); } catch { setError("Delete failed."); }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Faculty</h1>
        <button onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          + Add Faculty
        </button>
      </div>
      {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}
      {loading ? <Spinner /> : data.length === 0 ? (
        <EmptyState icon="👩‍🏫" title="No faculty yet" sub="Add your first faculty member to get started." />
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <TableHeader cols={["Name", "Department", "Email", "Max Periods/Day", "Status", "Actions"]} />
            <tbody className="divide-y divide-gray-100">
              {data.map((f, i) => (
                <tr key={f.id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="px-4 py-3 font-medium text-gray-800">{f.name}</td>
                  <td className="px-4 py-3 text-gray-600">{f.department}</td>
                  <td className="px-4 py-3 text-gray-500">{f.email || "—"}</td>
                  <td className="px-4 py-3 text-center text-gray-600">{f.max_periods_per_day}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${f.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {f.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3"><DeleteBtn onClick={() => handleDelete(f.id)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {showModal && (
        <Modal title="Add Faculty" onClose={() => setShowModal(false)}>
          <form onSubmit={handleCreate}>
            <FormField label="Full Name" name="name" value={form.name} onChange={v => setForm({ ...form, name: v })} required />
            <FormField label="Department" name="department" value={form.department} onChange={v => setForm({ ...form, department: v })} required />
            <FormField label="Email" name="email" type="email" value={form.email} onChange={v => setForm({ ...form, email: v })} />
            <FormField label="Max Periods per Day" name="max_periods_per_day" type="number" min={1} value={form.max_periods_per_day} onChange={v => setForm({ ...form, max_periods_per_day: v })} required />
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            <button type="submit" disabled={saving}
              className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-60">
              {saving ? "Saving…" : "Add Faculty"}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

// ─── Subjects Section ─────────────────────────────────────────────────────────

function SubjectsSection() {
  const [data, setData] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", department: "", credits: "3", periods_per_week: "3", requires_lab: "false" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await fetchSubjects()); } catch { setError("Failed to load subjects."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await createSubject({
        ...form, credits: Number(form.credits),
        periods_per_week: Number(form.periods_per_week),
        requires_lab: form.requires_lab === "true",
      });
      setShowModal(false);
      setForm({ name: "", code: "", department: "", credits: "3", periods_per_week: "3", requires_lab: "false" });
      load();
    } catch { setError("Failed to create subject."); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this subject?")) return;
    try { await deleteSubject(id); load(); } catch { setError("Delete failed."); }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Subjects</h1>
        <button onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          + Add Subject
        </button>
      </div>
      {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}
      {loading ? <Spinner /> : data.length === 0 ? (
        <EmptyState icon="📚" title="No subjects yet" sub="Add subjects to assign them to faculty and batches." />
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <TableHeader cols={["Name", "Code", "Department", "Credits", "Periods/Week", "Lab?", "Actions"]} />
            <tbody className="divide-y divide-gray-100">
              {data.map((s, i) => (
                <tr key={s.id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="px-4 py-3 font-medium text-gray-800">{s.name}</td>
                  <td className="px-4 py-3"><span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-mono">{s.code}</span></td>
                  <td className="px-4 py-3 text-gray-600">{s.department}</td>
                  <td className="px-4 py-3 text-center text-gray-600">{s.credits}</td>
                  <td className="px-4 py-3 text-center text-gray-600">{s.periods_per_week}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.requires_lab ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-500"}`}>
                      {s.requires_lab ? "Lab" : "Class"}
                    </span>
                  </td>
                  <td className="px-4 py-3"><DeleteBtn onClick={() => handleDelete(s.id)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {showModal && (
        <Modal title="Add Subject" onClose={() => setShowModal(false)}>
          <form onSubmit={handleCreate}>
            <FormField label="Subject Name" name="name" value={form.name} onChange={v => setForm({ ...form, name: v })} required />
            <FormField label="Code (e.g. CS201)" name="code" value={form.code} onChange={v => setForm({ ...form, code: v })} required />
            <FormField label="Department" name="department" value={form.department} onChange={v => setForm({ ...form, department: v })} required />
            <FormField label="Credits" name="credits" type="number" min={1} value={form.credits} onChange={v => setForm({ ...form, credits: v })} required />
            <FormField label="Periods per Week" name="periods_per_week" type="number" min={1} value={form.periods_per_week} onChange={v => setForm({ ...form, periods_per_week: v })} required />
            <FormField label="Requires Lab?" name="requires_lab" value={form.requires_lab} onChange={v => setForm({ ...form, requires_lab: v })}
              options={[{ value: "false", label: "No (Classroom)" }, { value: "true", label: "Yes (Lab)" }]} />
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            <button type="submit" disabled={saving}
              className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-60">
              {saving ? "Saving…" : "Add Subject"}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

// ─── Rooms Section ────────────────────────────────────────────────────────────

function RoomsSection() {
  const [data, setData] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ room_number: "", capacity: "60", type: "classroom", floor: "", building: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await fetchRooms()); } catch { setError("Failed to load rooms."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await createRoom({
        room_number: form.room_number,
        capacity: Number(form.capacity),
        type: form.type as "classroom" | "lab",
        floor: form.floor ? Number(form.floor) : undefined,
        building: form.building || undefined,
      });
      setShowModal(false);
      setForm({ room_number: "", capacity: "60", type: "classroom", floor: "", building: "" });
      load();
    } catch { setError("Failed to create room."); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this room?")) return;
    try { await deleteRoom(id); load(); } catch { setError("Delete failed."); }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Rooms</h1>
        <button onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          + Add Room
        </button>
      </div>
      {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}
      {loading ? <Spinner /> : data.length === 0 ? (
        <EmptyState icon="🏫" title="No rooms yet" sub="Add classrooms and labs to schedule timetable slots." />
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <TableHeader cols={["Room No.", "Type", "Capacity", "Floor", "Building", "Actions"]} />
            <tbody className="divide-y divide-gray-100">
              {data.map((r, i) => (
                <tr key={r.id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="px-4 py-3 font-medium text-gray-800">{r.room_number}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${r.type === "lab" ? "bg-purple-100 text-purple-700" : "bg-green-100 text-green-700"}`}>
                      {r.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-gray-600">{r.capacity}</td>
                  <td className="px-4 py-3 text-gray-500">{r.floor ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{r.building || "—"}</td>
                  <td className="px-4 py-3"><DeleteBtn onClick={() => handleDelete(r.id)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {showModal && (
        <Modal title="Add Room" onClose={() => setShowModal(false)}>
          <form onSubmit={handleCreate}>
            <FormField label="Room Number" name="room_number" value={form.room_number} onChange={v => setForm({ ...form, room_number: v })} required />
            <FormField label="Type" name="type" value={form.type} onChange={v => setForm({ ...form, type: v })}
              options={[{ value: "classroom", label: "Classroom" }, { value: "lab", label: "Laboratory" }]} />
            <FormField label="Capacity" name="capacity" type="number" min={1} value={form.capacity} onChange={v => setForm({ ...form, capacity: v })} required />
            <FormField label="Floor (optional)" name="floor" type="number" value={form.floor} onChange={v => setForm({ ...form, floor: v })} />
            <FormField label="Building (optional)" name="building" value={form.building} onChange={v => setForm({ ...form, building: v })} />
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            <button type="submit" disabled={saving}
              className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-60">
              {saving ? "Saving…" : "Add Room"}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

// ─── Batches Section ──────────────────────────────────────────────────────────

function BatchesSection() {
  const [data, setData] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: "", department: "", semester: "1", student_count: "60", year: new Date().getFullYear().toString() });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await fetchBatches()); } catch { setError("Failed to load batches."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await createBatch({
        ...form, semester: Number(form.semester),
        student_count: Number(form.student_count), year: Number(form.year),
      });
      setShowModal(false);
      setForm({ name: "", department: "", semester: "1", student_count: "60", year: new Date().getFullYear().toString() });
      load();
    } catch { setError("Failed to create batch."); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this batch?")) return;
    try { await deleteBatch(id); load(); } catch { setError("Delete failed."); }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Student Batches</h1>
        <button onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          + Add Batch
        </button>
      </div>
      {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}
      {loading ? <Spinner /> : data.length === 0 ? (
        <EmptyState icon="👥" title="No batches yet" sub="Add student groups (sections) to schedule timetables for." />
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <TableHeader cols={["Name", "Department", "Semester", "Students", "Year", "Actions"]} />
            <tbody className="divide-y divide-gray-100">
              {data.map((b, i) => (
                <tr key={b.id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="px-4 py-3 font-medium text-gray-800">{b.name}</td>
                  <td className="px-4 py-3 text-gray-600">{b.department}</td>
                  <td className="px-4 py-3 text-center text-gray-600">Sem {b.semester}</td>
                  <td className="px-4 py-3 text-center text-gray-600">{b.student_count}</td>
                  <td className="px-4 py-3 text-gray-500">{b.year}</td>
                  <td className="px-4 py-3"><DeleteBtn onClick={() => handleDelete(b.id)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {showModal && (
        <Modal title="Add Batch" onClose={() => setShowModal(false)}>
          <form onSubmit={handleCreate}>
            <FormField label="Batch Name (e.g. CS-A)" name="name" value={form.name} onChange={v => setForm({ ...form, name: v })} required />
            <FormField label="Department" name="department" value={form.department} onChange={v => setForm({ ...form, department: v })} required />
            <FormField label="Semester" name="semester" type="number" min={1} value={form.semester} onChange={v => setForm({ ...form, semester: v })} required />
            <FormField label="Student Count" name="student_count" type="number" min={1} value={form.student_count} onChange={v => setForm({ ...form, student_count: v })} required />
            <FormField label="Year" name="year" type="number" min={2000} value={form.year} onChange={v => setForm({ ...form, year: v })} required />
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            <button type="submit" disabled={saving}
              className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-60">
              {saving ? "Saving…" : "Add Batch"}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

// ─── Assignments Section ──────────────────────────────────────────────────────

function AssignmentsSection() {
  const [data, setData] = useState<Assignment[]>([]);
  const [faculty, setFaculty] = useState<Faculty[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ faculty_id: "", subject_id: "", batch_id: "", semester: "1" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, f, s, b] = await Promise.all([fetchAssignments(), fetchFaculty(), fetchSubjects(), fetchBatches()]);
      setData(a); setFaculty(f); setSubjects(s); setBatches(b);
      if (f.length > 0 && !form.faculty_id) setForm(prev => ({ ...prev, faculty_id: String(f[0].id) }));
      if (s.length > 0 && !form.subject_id) setForm(prev => ({ ...prev, subject_id: String(s[0].id) }));
      if (b.length > 0 && !form.batch_id) setForm(prev => ({ ...prev, batch_id: String(b[0].id) }));
    } catch { setError("Failed to load data."); }
    finally { setLoading(false); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load(); }, [load]);

  const getFacultyName = (id: number) => faculty.find(f => f.id === id)?.name ?? `#${id}`;
  const getSubjectName = (id: number) => subjects.find(s => s.id === id)?.name ?? `#${id}`;
  const getBatchName = (id: number) => batches.find(b => b.id === id)?.name ?? `#${id}`;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await createAssignment({
        faculty_id: Number(form.faculty_id),
        subject_id: Number(form.subject_id),
        batch_id: Number(form.batch_id),
        semester: Number(form.semester),
      });
      setShowModal(false); load();
    } catch { setError("Failed to create assignment. Check for duplicates."); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this assignment?")) return;
    try { await deleteAssignment(id); load(); } catch { setError("Delete failed."); }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Assignments</h1>
        <button onClick={() => setShowModal(true)} disabled={faculty.length === 0 || subjects.length === 0 || batches.length === 0}
          className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
          title={faculty.length === 0 ? "Add faculty, subjects, and batches first" : ""}>
          + Assign Faculty
        </button>
      </div>
      {faculty.length === 0 && !loading && (
        <div className="mb-4 p-3 bg-amber-50 text-amber-700 rounded-lg text-sm">
          ⚠️ You need to add Faculty, Subjects, and Batches before creating assignments.
        </div>
      )}
      {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}
      {loading ? <Spinner /> : data.length === 0 ? (
        <EmptyState icon="🔗" title="No assignments yet" sub="Link faculty to subjects and batches. The scheduler uses these to generate the timetable." />
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <TableHeader cols={["Faculty", "Subject", "Batch", "Semester", "Actions"]} />
            <tbody className="divide-y divide-gray-100">
              {data.map((a, i) => (
                <tr key={a.id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="px-4 py-3 font-medium text-gray-800">{getFacultyName(a.faculty_id)}</td>
                  <td className="px-4 py-3 text-gray-600">{getSubjectName(a.subject_id)}</td>
                  <td className="px-4 py-3 text-gray-600">{getBatchName(a.batch_id)}</td>
                  <td className="px-4 py-3 text-center text-gray-600">Sem {a.semester}</td>
                  <td className="px-4 py-3"><DeleteBtn onClick={() => handleDelete(a.id)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {showModal && (
        <Modal title="Create Assignment" onClose={() => setShowModal(false)}>
          <form onSubmit={handleCreate}>
            <FormField label="Faculty" name="faculty_id" value={form.faculty_id} onChange={v => setForm({ ...form, faculty_id: v })}
              options={faculty.map(f => ({ value: String(f.id), label: `${f.name} (${f.department})` }))} />
            <FormField label="Subject" name="subject_id" value={form.subject_id} onChange={v => setForm({ ...form, subject_id: v })}
              options={subjects.map(s => ({ value: String(s.id), label: `${s.name} (${s.code})` }))} />
            <FormField label="Batch" name="batch_id" value={form.batch_id} onChange={v => setForm({ ...form, batch_id: v })}
              options={batches.map(b => ({ value: String(b.id), label: `${b.name} – Sem ${b.semester}` }))} />
            <FormField label="Semester" name="semester" type="number" min={1} value={form.semester} onChange={v => setForm({ ...form, semester: v })} required />
            {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
            <button type="submit" disabled={saving}
              className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-60">
              {saving ? "Saving…" : "Create Assignment"}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

// ─── Main App Layout ──────────────────────────────────────────────────────────

export default function HomePage() {
  const { token, username, role, logout } = useAuthStore();
  const [section, setSection] = useState<Section>("chat");
  const [timetableId, setTimetableId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <LoginForm />
      </div>
    );
  }

  const renderSection = () => {
    switch (section) {
      case "chat":        return <Chat onTimetableGenerated={(id) => { setTimetableId(id); setSection("timetable"); }} />;
      case "timetable":  return <TimetableGrid timetableId={timetableId} />;
      case "faculty":    return <FacultySection />;
      case "subjects":   return <SubjectsSection />;
      case "rooms":      return <RoomsSection />;
      case "batches":    return <BatchesSection />;
      case "assignments":return <AssignmentsSection />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-primary text-white px-4 py-3 flex items-center justify-between shadow-md z-10">
        <div className="flex items-center gap-3">
          <button onClick={() => setSidebarOpen(o => !o)}
            className="text-white/70 hover:text-white transition-colors p-1 rounded">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center flex-shrink-0">
            <span className="text-primary font-bold text-sm">T</span>
          </div>
          <h1 className="text-lg font-bold hidden sm:block">Timetable LLM</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium">{username}</p>
            <p className="text-xs text-white/60 capitalize">{role?.replace("_", " ")}</p>
          </div>
          <button onClick={logout}
            className="text-sm text-white/70 hover:text-white transition-colors border border-white/20 hover:border-white/40 px-3 py-1.5 rounded-lg">
            Logout
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className={`${sidebarOpen ? "w-52" : "w-0"} flex-shrink-0 bg-white border-r transition-all duration-300 overflow-hidden`}>
          <nav className="py-4 space-y-1 px-2">
            {NAV_ITEMS.map(item => (
              <button key={item.id} onClick={() => setSection(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  section === item.id ? "bg-primary text-white shadow-sm" : "text-gray-600 hover:bg-gray-100"
                }`}>
                <span className="text-lg leading-none">{item.icon}</span>
                <span>{item.label}</span>
                {item.id === "assignments" && (
                  <span className="ml-auto text-xs opacity-60">→ Schedule</span>
                )}
              </button>
            ))}
          </nav>

          <div className="px-4 py-3 border-t mt-2">
            <p className="text-xs text-gray-400 leading-relaxed">
              <strong className="text-gray-500">Workflow:</strong><br/>
              Faculty → Subjects →<br/>Rooms → Batches →<br/>Assignments → Chat
            </p>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto">
          {renderSection()}
        </main>
      </div>
    </div>
  );
}
