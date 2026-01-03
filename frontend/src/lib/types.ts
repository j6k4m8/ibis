export type User = {
  id: string;
  email: string;
  display_name?: string | null;
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
  video_url?: string | null;
};

export type NoteVersion = {
  id: string;
  note_id: string;
  title: string;
  body: string;
  tags: string[];
  created_at: string;
};
