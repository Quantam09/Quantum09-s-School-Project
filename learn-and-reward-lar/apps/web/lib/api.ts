/** Typed API client for the Learn-and-Reward-LAR API (Mission B endpoints).
 *
 * Hand-written to match docs/contracts; can be regenerated from the OpenAPI
 * document with openapi-typescript once the API contract is frozen.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;

  constructor(code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

type ApiOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  auth?: boolean;
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("lar_token");
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem("lar_token", token);
  else window.localStorage.removeItem("lar_token");
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (options.auth !== false && token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = (payload as { error?: { code?: string; message?: string; details?: Record<string, unknown> } }).error;
    throw new ApiError(
      error?.code ?? "UNKNOWN_ERROR",
      error?.message ?? `Request failed with status ${response.status}`,
      error?.details ?? {},
    );
  }
  return payload as T;
}

// --- Types shared with the backend contract --------------------------------

export type CourseLevel = "beginner" | "intermediate" | "advanced";

export type CourseSummary = {
  id: string;
  slug: string;
  title: string;
  description: string;
  language: string;
  level: CourseLevel;
  price_coins: number;
  is_published: boolean;
  lesson_count: number;
};

export type LessonSummary = {
  id: string;
  order_index: number;
  title: string;
  completed: boolean;
};

export type EnrollmentSummary = {
  id: string;
  course_id: string;
  status: "active" | "completed";
  lessons_completed: number;
  total_lessons: number;
  created_at: string;
  completed_at: string | null;
};

export type CourseDetail = CourseSummary & {
  lessons: LessonSummary[];
  enrollment: EnrollmentSummary | null;
};

export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

export type UserResponse = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
};

export type TokenResponse = { access_token: string; token_type: string; user: UserResponse };

export type VocabularyItem = { term: string; translation: string; pronunciation: string | null };

export type ExercisePublic = {
  id: string;
  order_index: number;
  type: "multiple_choice" | "fill_in_blank" | "translation";
  prompt: string;
  options: string[] | null;
  points: number;
};

export type LessonDetail = {
  id: string;
  course_id: string;
  course_title: string;
  order_index: number;
  title: string;
  content: string;
  vocabulary: VocabularyItem[];
  exercises: ExercisePublic[];
};

export type PracticeSessionSummary = {
  id: string;
  kind: "lesson_exercises" | "free_conversation";
  status: "in_progress" | "completed";
  lesson_id: string | null;
  total_exercises: number;
  correct_exercises: number;
  coins_awarded: number;
  created_at: string;
  completed_at: string | null;
};

export type ExerciseFeedback = {
  correct: boolean;
  expected: string | null;
  explanation: string;
  ai_hint: string | null;
};

export type SubmitResponse = {
  message_id: string;
  feedback: ExerciseFeedback | null;
  reply: string | null;
  citations: unknown[];
  session: PracticeSessionSummary;
  coins_awarded: number;
};

export type Citation = { index: number; chunk_id: string; resource_id: string; snippet: string };

export type AiChatResponse = {
  session_id: string;
  reply: string;
  citations: Citation[];
  disclaimer: string;
};

export type CertificateResponse = {
  id: string;
  code: string;
  course_id: string;
  title: string;
  issued_at: string;
  revoked: boolean;
};

export type CertificateVerifyResponse = {
  valid: boolean;
  code: string;
  title: string;
  issued_at: string;
  revoked: boolean;
};

// --- Endpoint wrappers -------------------------------------------------------

export const apiClient = {
  register: (body: { email: string; password: string; display_name: string }) =>
    api<UserResponse>("/auth/register", { method: "POST", body, auth: false }),
  login: (body: { email: string; password: string }) =>
    api<TokenResponse>("/auth/login", { method: "POST", body, auth: false }),
  me: () => api<UserResponse>("/users/me"),

  listCourses: (limit = 20, offset = 0) =>
    api<Page<CourseSummary>>(`/courses?limit=${limit}&offset=${offset}`),
  getCourse: (courseId: string) => api<CourseDetail>(`/courses/${courseId}`),
  enroll: (courseId: string) =>
    api<{ enrollment: EnrollmentSummary; coins_spent: number }>(
      `/courses/${courseId}/enroll`,
      { method: "POST" },
    ),

  getLesson: (lessonId: string) => api<LessonDetail>(`/lessons/${lessonId}`),

  createSession: (kind: "lesson_exercises" | "free_conversation", lessonId?: string) =>
    api<PracticeSessionDetail>(`/practice/sessions`, {
      method: "POST",
      body: { kind, lesson_id: lessonId ?? null },
    }),
  getSession: (sessionId: string) => api<PracticeSessionDetail>(`/practice/sessions/${sessionId}`),
  submitExercise: (sessionId: string, exerciseId: string, answer: string | number) =>
    api<SubmitResponse>(`/practice/sessions/${sessionId}/messages`, {
      method: "POST",
      body: { exercise_id: exerciseId, answer },
    }),
  submitFreeMessage: (sessionId: string, content: string) =>
    api<AiChatResponse>(`/practice/sessions/${sessionId}/messages`, {
      method: "POST",
      body: { content },
    }),

  aiChat: (message: string, sessionId?: string | null) =>
    api<AiChatResponse>(`/ai/chat`, { method: "POST", body: { message, session_id: sessionId ?? null } }),

  claimCertificate: (courseId: string) =>
    api<CertificateResponse>(`/certificates/claim`, { method: "POST", body: { course_id: courseId } }),
  listCertificates: () => api<CertificateResponse[]>(`/certificates`),
  verifyCertificate: (code: string) =>
    api<CertificateVerifyResponse>(
      `/certificates/${encodeURIComponent(code)}/verify`,
      { auth: false },
    ),
};

export type PracticeSessionDetail = PracticeSessionSummary & {
  exercises: ExercisePublic[];
  messages: {
    id: string;
    session_id: string | null;
    role: "user" | "assistant" | "system";
    content: string;
    citations: Citation[] | null;
    created_at: string;
  }[];
};
