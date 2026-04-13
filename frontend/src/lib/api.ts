import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: API_URL });

// Attach JWT token from localStorage automatically
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    try {
      const raw = localStorage.getItem("timetable-auth");
      if (raw) {
        const token = JSON.parse(raw)?.state?.token;
        if (token) config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // ignore parse errors
    }
  }
  return config;
});

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Faculty {
  id: number;
  name: string;
  department: string;
  email?: string;
  max_periods_per_day: number;
  is_active: boolean;
}

export interface Subject {
  id: number;
  name: string;
  code: string;
  department: string;
  credits: number;
  periods_per_week: number;
  requires_lab: boolean;
}

export interface Room {
  id: number;
  room_number: string;
  capacity: number;
  type: "classroom" | "lab";
  floor?: number;
  building?: string;
}

export interface Batch {
  id: number;
  name: string;
  department: string;
  semester: number;
  student_count: number;
  year: number;
}

export interface Assignment {
  id: number;
  faculty_id: number;
  subject_id: number;
  batch_id: number;
  semester: number;
  faculty?: Faculty;
  subject?: Subject;
  batch?: Batch;
}

// ─── Faculty ─────────────────────────────────────────────────────────────────

export const fetchFaculty = () =>
  api.get<Faculty[]>("/api/faculty").then((r) => r.data);

export const createFaculty = (data: Omit<Faculty, "id" | "is_active">) =>
  api.post<Faculty>("/api/faculty", data).then((r) => r.data);

export const updateFaculty = (id: number, data: Partial<Faculty>) =>
  api.put<Faculty>(`/api/faculty/${id}`, data).then((r) => r.data);

export const deleteFaculty = (id: number) =>
  api.delete(`/api/faculty/${id}`);

// ─── Subjects ────────────────────────────────────────────────────────────────

export const fetchSubjects = () =>
  api.get<Subject[]>("/api/subjects").then((r) => r.data);

export const createSubject = (data: Omit<Subject, "id">) =>
  api.post<Subject>("/api/subjects", data).then((r) => r.data);

export const updateSubject = (id: number, data: Partial<Subject>) =>
  api.put<Subject>(`/api/subjects/${id}`, data).then((r) => r.data);

export const deleteSubject = (id: number) =>
  api.delete(`/api/subjects/${id}`);

// ─── Rooms ───────────────────────────────────────────────────────────────────

export const fetchRooms = () =>
  api.get<Room[]>("/api/rooms").then((r) => r.data);

export const createRoom = (data: Omit<Room, "id">) =>
  api.post<Room>("/api/rooms", data).then((r) => r.data);

export const updateRoom = (id: number, data: Partial<Room>) =>
  api.put<Room>(`/api/rooms/${id}`, data).then((r) => r.data);

export const deleteRoom = (id: number) =>
  api.delete(`/api/rooms/${id}`);

// ─── Batches ─────────────────────────────────────────────────────────────────

export const fetchBatches = () =>
  api.get<Batch[]>("/api/batches").then((r) => r.data);

export const createBatch = (data: Omit<Batch, "id">) =>
  api.post<Batch>("/api/batches", data).then((r) => r.data);

export const updateBatch = (id: number, data: Partial<Batch>) =>
  api.put<Batch>(`/api/batches/${id}`, data).then((r) => r.data);

export const deleteBatch = (id: number) =>
  api.delete(`/api/batches/${id}`);

// ─── Assignments ─────────────────────────────────────────────────────────────

export const fetchAssignments = () =>
  api.get<Assignment[]>("/api/timetable/assignments").then((r) => r.data);

export const createAssignment = (data: {
  faculty_id: number;
  subject_id: number;
  batch_id: number;
  semester: number;
}) => api.post<Assignment>("/api/timetable/assignments", data).then((r) => r.data);

export const deleteAssignment = (id: number) =>
  api.delete(`/api/timetable/assignments/${id}`);

export default api;
