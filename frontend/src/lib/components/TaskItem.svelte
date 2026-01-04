<script lang="ts">
  import type { Task } from '$lib/types';

  export let task: Task;
  export let onToggle: ((task: Task) => void) | null = null;
  export let recentlyCompleted = false;
  export let showNoteLink = true;
  export let showTimestamp = true;
  export let compact = false;

  function handleToggle() {
    if (onToggle) {
      onToggle(task);
    }
  }
</script>

<div
  class={`flex items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-4 transition ${
    recentlyCompleted ? 'task-fade' : ''
  } ${compact ? 'py-3' : ''}`}
>
  <div>
    <div class="flex items-center gap-2 text-sm text-slate-900">
      <button
        type="button"
        class={`inline-flex h-6 w-6 items-center justify-center rounded-full border transition ${
          task.completed
            ? 'border-emerald-400 bg-emerald-100 text-emerald-600'
            : 'border-slate-300 bg-white text-slate-400 hover:border-orange-300 hover:bg-orange-50'
        }`}
        on:click={handleToggle}
        aria-label={task.completed ? 'Mark as incomplete' : 'Mark as complete'}
      >
        {task.completed ? '✓' : ''}
      </button>
      <span
        class={`${
          task.completed ? 'text-slate-400 task-complete' : ''
        } ${recentlyCompleted ? 'task-strike' : ''}`}
      >
        {task.text || 'Untitled task'}
      </span>
    </div>
    {#if showNoteLink}
      <a href={`/notes/${task.note_id}`} class="mt-1 block text-xs text-slate-500 hover:underline">
        {task.note_title}
      </a>
    {/if}
  </div>
  {#if showTimestamp}
    <div class="text-right text-[11px] text-slate-400">
      <div class="uppercase tracking-widest">{task.completed ? 'Done' : 'Open'}</div>
      <div>
        {new Date(task.created_at).toLocaleString(undefined, {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
        })}
      </div>
    </div>
  {/if}
</div>
