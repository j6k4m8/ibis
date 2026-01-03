import type { AuthResponse, Note, NoteVersion, Task, User } from './types';

const DEFAULT_BASE_URL = 'http://localhost:8000';
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL;

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore invalid json
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return null as T;
  }

  return (await response.json()) as T;
}

export async function register(
  email: string,
  password: string,
  displayName?: string,
): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      display_name: displayName,
    }),
  });
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function me(token: string): Promise<User> {
  return request<User>('/auth/me', {}, token);
}

export async function listNotes(token: string): Promise<Note[]> {
  return request<Note[]>('/notes', {}, token);
}

export async function getNote(token: string, noteId: string): Promise<Note> {
  return request<Note>(`/notes/${noteId}`, {}, token);
}

export async function createNote(
  token: string,
  payload: { title: string; body?: string; tags?: string[]; video_url?: string },
): Promise<Note> {
  return request<Note>(
    '/notes',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function updateNote(
  token: string,
  noteId: string,
  payload: { title?: string; body?: string; tags?: string[]; archived?: boolean },
): Promise<Note> {
  return request<Note>(
    `/notes/${noteId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function listNoteVersions(token: string, noteId: string): Promise<NoteVersion[]> {
  return request<NoteVersion[]>(`/notes/${noteId}/versions`, {}, token);
}

export async function getNoteVersion(
  token: string,
  noteId: string,
  versionId: string,
): Promise<NoteVersion> {
  return request<NoteVersion>(`/notes/${noteId}/versions/${versionId}`, {}, token);
}

export async function listTasks(token: string): Promise<Task[]> {
  return request<Task[]>('/tasks', {}, token);
}

export async function updateTask(
  token: string,
  taskId: string,
  payload: { completed?: boolean },
): Promise<Task> {
  return request<Task>(
    `/tasks/${taskId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export { ApiError };
