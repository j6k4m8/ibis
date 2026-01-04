<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import TaskItem from '$lib/components/TaskItem.svelte';
  import { authStore } from '$lib/stores/auth';
  import type { Task } from '$lib/types';

  let tasks: Task[] = [];
  let loading = true;
  let error = '';
  let showCompleted = false;
  let searchQuery = '';
  let token: string | null = null;
  let recentlyCompletedIds = new Set<string>();
  let completionTimers: Record<string, ReturnType<typeof setTimeout>> = {};

  const COMPLETION_DISPLAY_MS = 1100;

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
      if (nextCompleted) {
        markRecentlyCompleted(task.id);
      } else {
        clearRecentlyCompleted(task.id);
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update task.';
    }
  }

  function markRecentlyCompleted(taskId: string) {
    recentlyCompletedIds = new Set([...recentlyCompletedIds, taskId]);
    if (completionTimers[taskId]) {
      clearTimeout(completionTimers[taskId]);
    }
    completionTimers[taskId] = setTimeout(() => {
      clearRecentlyCompleted(taskId);
    }, COMPLETION_DISPLAY_MS);
  }

  function clearRecentlyCompleted(taskId: string) {
    if (completionTimers[taskId]) {
      clearTimeout(completionTimers[taskId]);
      delete completionTimers[taskId];
    }
    const next = new Set(recentlyCompletedIds);
    next.delete(taskId);
    recentlyCompletedIds = next;
  }

  $: sortedTasks = [...tasks].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );

  $: filteredTasks = sortedTasks.filter((task) => {
    const isRecentlyCompleted = recentlyCompletedIds.has(task.id);
    if (!showCompleted && task.completed && !isRecentlyCompleted) {
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
        <TaskItem
          {task}
          onToggle={toggleTask}
          recentlyCompleted={recentlyCompletedIds.has(task.id) && !showCompleted}
        />
      {/each}
    {/if}
  </div>
</section>
