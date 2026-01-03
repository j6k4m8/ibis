<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import { extractTasks } from '$lib/utils/tasks';
  import type { TaskItem } from '$lib/utils/tasks';

  let tasks: TaskItem[] = [];
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
      const notes = await api.listNotes(activeToken);
      tasks = extractTasks(notes);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load tasks.';
    } finally {
      loading = false;
    }
  }

  $: filteredTasks = tasks.filter((task) => {
    if (!showCompleted && task.completed) {
      return false;
    }

    if (!searchQuery.trim()) {
      return true;
    }

    const query = searchQuery.toLowerCase();
    return task.text.toLowerCase().includes(query) || task.noteTitle.toLowerCase().includes(query);
  });
</script>

<svelte:head>
  <title>Tasks · Ibis</title>
</svelte:head>

<section class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl">Tasks</h1>
      <p class="text-sm text-slate-500">Pulled from checklist items in your notes.</p>
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
            <div class="text-sm text-slate-900">
              <span
                class={`mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full border ${
                  task.completed
                    ? 'border-emerald-400 bg-emerald-100 text-emerald-600'
                    : 'border-slate-300 bg-white text-slate-400'
                }`}
              >
                {task.completed ? '✓' : ''}
              </span>
              {task.text}
            </div>
            <a href={`/notes/${task.noteId}`} class="mt-1 block text-xs text-slate-500 hover:underline">
              {task.noteTitle}
            </a>
          </div>
          <span class="text-[11px] uppercase tracking-widest text-slate-400">
            {task.completed ? 'Done' : 'Open'}
          </span>
        </div>
      {/each}
    {/if}
  </div>
</section>
