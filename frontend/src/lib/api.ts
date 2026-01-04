import type {
  AuthResponse,
  Job,
  Lesson,
  Me,
  Note,
  NoteVersion,
  Task,
  TranscriptChunk,
  User,
  Video,
} from './types';

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

  const isFormData =
    typeof FormData !== 'undefined' && options.body instanceof FormData;
  if (options.body && !headers.has('Content-Type') && !isFormData) {
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

export async function getMe(token: string): Promise<Me> {
  return request<Me>('/me', {}, token);
}

export async function updateMe(
  token: string,
  payload: { lesson_autogroup_hours?: number },
): Promise<Me> {
  return request<Me>(
    '/me',
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function listNotes(
  token: string,
  params?: { video_id?: string },
): Promise<Note[]> {
  const searchParams = params?.video_id
    ? `?video_id=${encodeURIComponent(params.video_id)}`
    : '';
  return request<Note[]>(`/notes${searchParams}`, {}, token);
}

export async function getNote(token: string, noteId: string): Promise<Note> {
  return request<Note>(`/notes/${noteId}`, {}, token);
}

export async function createNote(
  token: string,
  payload: {
    title: string;
    body?: string;
    tags?: string[];
    video_url?: string;
    video_id?: string;
    video_title?: string;
    video_start_seconds?: number | null;
    video_end_seconds?: number | null;
    created_at?: string;
  },
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
  payload: {
    title?: string;
    body?: string;
    tags?: string[];
    archived?: boolean;
    video_start_seconds?: number | null;
    video_end_seconds?: number | null;
    created_at?: string;
  },
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

export async function deleteNote(token: string, noteId: string): Promise<void> {
  await request<void>(
    `/notes/${noteId}`,
    {
      method: 'DELETE',
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

export async function listVideos(token: string): Promise<Video[]> {
  return request<Video[]>('/videos', {}, token);
}

export async function getVideo(token: string, videoId: string): Promise<Video> {
  return request<Video>(`/videos/${videoId}`, {}, token);
}

export async function uploadVideo(
  token: string,
  file: File,
  title?: string,
): Promise<Video> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) {
    formData.append('title', title);
  }
  if (typeof file.lastModified === 'number') {
    formData.append('last_modified_ms', file.lastModified.toString());
  }
  return request<Video>(
    '/videos/upload',
    {
      method: 'POST',
      body: formData,
    },
    token,
  );
}

export async function uploadVideoWithProgress(
  token: string,
  file: File,
  title: string | undefined,
  onProgress: (percent: number) => void,
): Promise<Video> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    if (title) {
      formData.append('title', title);
    }
    if (typeof file.lastModified === 'number') {
      formData.append('last_modified_ms', file.lastModified.toString());
    }

    const requestUrl = `${baseUrl}/videos/upload`;
    const xhr = new XMLHttpRequest();
    xhr.open('POST', requestUrl, true);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.setRequestHeader('Accept', 'application/json');

    xhr.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable) {
        return;
      }
      const percent = Math.round((event.loaded / event.total) * 100);
      onProgress(percent);
    });

    xhr.onreadystatechange = () => {
      if (xhr.readyState !== XMLHttpRequest.DONE) {
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as Video);
        } catch {
          reject(new ApiError('Invalid response from server.', xhr.status));
        }
        return;
      }
      let detail = xhr.statusText || 'Upload failed.';
      try {
        const body = JSON.parse(xhr.responseText) as { detail?: string };
        if (body.detail) {
          detail = body.detail;
        }
      } catch {
        // ignore invalid json
      }
      reject(new ApiError(detail, xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError('Network error during upload.', 0));
    };

    xhr.send(formData);
  });
}

export async function updateVideo(
  token: string,
  videoId: string,
  payload: { title?: string; created_at?: string },
): Promise<Video> {
  return request<Video>(
    `/videos/${videoId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function deleteVideo(token: string, videoId: string): Promise<void> {
  await request<void>(
    `/videos/${videoId}`,
    {
      method: 'DELETE',
    },
    token,
  );
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

export async function listJobs(token: string): Promise<Job[]> {
  return request<Job[]>('/jobs', {}, token);
}

export async function listLessons(token: string): Promise<Lesson[]> {
  return request<Lesson[]>('/lessons', {}, token);
}

export async function getLesson(token: string, lessonId: string): Promise<Lesson> {
  return request<Lesson>(`/lessons/${lessonId}`, {}, token);
}

export async function createLesson(
  token: string,
  payload: { title?: string; created_at?: string },
): Promise<Lesson> {
  return request<Lesson>(
    '/lessons',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function updateLesson(
  token: string,
  lessonId: string,
  payload: { title?: string },
): Promise<Lesson> {
  return request<Lesson>(
    `/lessons/${lessonId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function listLessonNotes(token: string, lessonId: string): Promise<Note[]> {
  return request<Note[]>(`/lessons/${lessonId}/notes`, {}, token);
}

export async function listLessonVideos(token: string, lessonId: string): Promise<Video[]> {
  return request<Video[]>(`/lessons/${lessonId}/videos`, {}, token);
}

export async function listLessonTasks(token: string, lessonId: string): Promise<Task[]> {
  return request<Task[]>(`/lessons/${lessonId}/tasks`, {}, token);
}

export async function addLessonNote(
  token: string,
  lessonId: string,
  noteId: string,
): Promise<Lesson> {
  return request<Lesson>(
    `/lessons/${lessonId}/notes`,
    {
      method: 'POST',
      body: JSON.stringify({ note_id: noteId }),
    },
    token,
  );
}

export async function removeLessonNote(
  token: string,
  lessonId: string,
  noteId: string,
): Promise<void> {
  await request<void>(
    `/lessons/${lessonId}/notes/${noteId}`,
    {
      method: 'DELETE',
    },
    token,
  );
}

export async function addLessonVideo(
  token: string,
  lessonId: string,
  videoId: string,
): Promise<Lesson> {
  return request<Lesson>(
    `/lessons/${lessonId}/videos`,
    {
      method: 'POST',
      body: JSON.stringify({ video_id: videoId }),
    },
    token,
  );
}

export async function removeLessonVideo(
  token: string,
  lessonId: string,
  videoId: string,
): Promise<void> {
  await request<void>(
    `/lessons/${lessonId}/videos/${videoId}`,
    {
      method: 'DELETE',
    },
    token,
  );
}

export async function listNoteLessons(token: string, noteId: string): Promise<Lesson[]> {
  return request<Lesson[]>(`/lessons/notes/${noteId}`, {}, token);
}

export async function listTranscriptChunks(
  token: string,
  videoId: string,
): Promise<TranscriptChunk[]> {
  return request<TranscriptChunk[]>(`/videos/${videoId}/transcript`, {}, token);
}

export { ApiError };
