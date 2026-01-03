import { describe, expect, it } from 'vitest';

import { extractTasks } from '../lib/utils/tasks';
import type { Note } from '../lib/types';

describe('extractTasks', () => {
  it('extracts tasks across notes', () => {
    const notes: Note[] = [
      {
        id: 'note-1',
        title: 'Lesson A',
        body: '- [ ] First task\n- [x] Done task\n* [ ] Star task\nNo task here',
        tags: [],
        archived: false,
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
        video_url: null,
      },
      {
        id: 'note-2',
        title: 'Lesson B',
        body: 'Intro\n- [ ] Another task\n+ [x] Plus task\n- [ ]',
        tags: [],
        archived: false,
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
        video_url: null,
      },
    ];

    const tasks = extractTasks(notes);
    expect(tasks).toHaveLength(6);
    expect(tasks[0]).toMatchObject({ noteId: 'note-1', completed: false, text: 'First task' });
    expect(tasks[1]).toMatchObject({ noteId: 'note-1', completed: true, text: 'Done task' });
    expect(tasks[2]).toMatchObject({ noteId: 'note-1', completed: false, text: 'Star task' });
    expect(tasks[3]).toMatchObject({ noteId: 'note-2', completed: false, text: 'Another task' });
    expect(tasks[4]).toMatchObject({ noteId: 'note-2', completed: true, text: 'Plus task' });
    expect(tasks[5]).toMatchObject({ noteId: 'note-2', completed: false, text: 'Untitled task' });
  });
});
