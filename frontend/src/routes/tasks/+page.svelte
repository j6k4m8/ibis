<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import type { Task } from '$lib/types';

  let tasks: Task[] = [];
  let loading = true;
  let error = '';
  let showCompleted = false;
  let searchQuery = '';
  let token: string | null = null;

  const unsubscribe = authStore.subscribe((state) => {
    token = state.token;
  });

  onMount(async () => {
    const state = await authStore.init();
    if (!state.token) {
      goto('/login');
      return;
    }

    await loadTasks(state.token);

    return () => unsubscribe();
  });

  async function loadTasks(activeToken: string) {
    loading = true;
    error = '';
    try {
      tasks = await api.listTasks(activeToken);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load tasks.';
    } finally {
      loading = false;
    }
  }

  async function toggleTask(task: Task) {
    if (!token) {
      return;
    }
    const nextCompleted = !task.completed;
    try {
      const updated = await api.updateTask(token, task.id, { completed: nextCompleted });
      tasks = tasks.map((item) => (item.id === updated.id ? updated : item));
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update task.';
    }
  }

  $: sortedTasks = [...tasks].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );

  $: filteredTasks = sortedTasks.filter((task) => {
    if (!showCompleted && task.completed) {
      return false;
    }

    if (!searchQuery.trim()) {
      return true;
    }

    const query = searchQuery.toLowerCase();
    return (
      task.text.toLowerCase().includes(query) || task.note_title.toLowerCase().includes(query)
    );
  });
</script>

<svelte:head>
  <title>Tasks · Ibis</title>
</svelte:head>

<section class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl">Tasks</h1>
      <p class="text-sm text-slate-500">Checklist items pulled from your notes.</p>
    </div>
    <label class="inline-flex items-center gap-2 text-xs text-slate-500">
      <input type="checkbox" bind:checked={showCompleted} class="h-4 w-4 rounded border-slate-300" />
      Show completed
    </label>
  </div>

  <div class="mt-4">
    <input
      class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
      type="search"
      bind:value={searchQuery}
      placeholder="Search tasks or note titles"
    />
  </div>

  {#if error}
    <div class="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
      {error}
    </div>
  {/if}

  <div class="mt-6 space-y-3">
    {#if loading}
      <div class="text-sm text-slate-500">Loading tasks...</div>
    {:else if filteredTasks.length === 0}
      <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
        No tasks found. Add a line like <code>- [ ] Practice arpeggios</code> in any note.
      </div>
    {:else}
      {#each filteredTasks as task}
          <div class="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-4">
            <div>
              <div class="flex items-center gap-2 text-sm text-slate-900">
                <button
                  type="button"
                  class={`inline-flex h-6 w-6 items-center justify-center rounded-full border transition ${
                    task.completed
                      ? 'border-emerald-400 bg-emerald-100 text-emerald-600'
                      : 'border-slate-300 bg-white text-slate-400 hover:border-orange-300 hover:bg-orange-50'
                  }`}
                  on:click={() => toggleTask(task)}
                  aria-label={task.completed ? 'Mark as incomplete' : 'Mark as complete'}
                >
                  {task.completed ? '✓' : ''}
                </button>
                <span class={task.completed ? 'text-slate-400 line-through' : ''}>
                  {task.text || 'Untitled task'}
                </span>
              </div>
              <a
                href={`/notes/${task.note_id}`}
                class="mt-1 block text-xs text-slate-500 hover:underline"
              >
                {task.note_title}
              </a>
            </div>
            <div class="text-right text-[11px] text-slate-400">
              <div class="uppercase tracking-widest">{task.completed ? 'Done' : 'Open'}</div>
              <div>{new Date(task.created_at).toLocaleDateString()}</div>
            </div>
          </div>
      {/each}
    {/if}
  </div>
</section>
