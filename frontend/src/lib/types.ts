export type User = {
  id: string;
  email: string;
  display_name?: string | null;
  lesson_autogroup_hours?: number;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type Note = {
  id: string;
  title: string;
  body: string;
  tags: string[];
  archived: boolean;
  created_at: string;
  updated_at: string;
  video_id?: string | null;
  video_title?: string | null;
  video_source_type?: string | null;
  video_url?: string | null;
  video_start_seconds?: number | null;
  video_end_seconds?: number | null;
};

export type NoteVersion = {
  id: string;
  note_id: string;
  title: string;
  body: string;
  tags: string[];
  created_at: string;
};

export type Task = {
  id: string;
  note_id: string;
  note_title: string;
  text: string;
  completed: boolean;
  created_at: string;
  updated_at: string;
};

export type Lesson = {
  id: string;
  title?: string | null;
  created_at: string;
  updated_at: string;
};

export type Video = {
  id: string;
  title?: string | null;
  source_type: string;
  video_url?: string | null;
  thumbnail_url?: string | null;
  file_size_bytes?: number | null;
  original_filename?: string | null;
  mime_type?: string | null;
  original_created_at?: string | null;
  duration_seconds?: number | null;
  created_at: string;
  updated_at: string;
};

export type Me = {
  user: User;
  storage_used_bytes: number;
  storage_limit_bytes: number;
};

export type Job = {
  id: string;
  video_id: string;
  job_type: string;
  status: string;
  progress?: number | null;
  detail?: string | null;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  finished_at?: string | null;
};

export type TranscriptChunk = {
  id: string;
  start_seconds: number;
  end_seconds: number;
  text: string;
  created_at: string;
};
