import type { Note } from '$lib/types';

export type TaskItem = {
  noteId: string;
  noteTitle: string;
  text: string;
  completed: boolean;
};

const TASK_REGEX = /^\s*-\s*\[( |x|X)]\s+(.*)$/;

export function extractTasks(notes: Note[]): TaskItem[] {
  const tasks: TaskItem[] = [];

  for (const note of notes) {
    const lines = note.body.split('\n');
    for (const line of lines) {
      const match = line.match(TASK_REGEX);
      if (!match) {
        continue;
      }

      tasks.push({
        noteId: note.id,
        noteTitle: note.title,
        text: match[2].trim(),
        completed: match[1].toLowerCase() === 'x',
      });
    }
  }

  return tasks;
}
