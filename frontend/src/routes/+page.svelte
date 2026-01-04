<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import TaskItem from '$lib/components/TaskItem.svelte';
  import { authStore } from '$lib/stores/auth';
  import type { Lesson, Task } from '$lib/types';

  let token: string | null = null;
  let tasks: Task[] = [];
  let lessons: Lesson[] = [];
  let loading = true;
  let error = '';

  const unsubscribe = authStore.subscribe((state) => {
    token = state.token;
  });

  onMount(async () => {
    const state = await authStore.init();
    if (!state.token) {
      loading = false;
      return () => unsubscribe();
    }

    try {
      const [taskList, lessonList] = await Promise.all([
        api.listTasks(state.token),
        api.listLessons(state.token),
      ]);
      tasks = taskList;
      lessons = lessonList;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load dashboard.';
    } finally {
      loading = false;
    }

    return () => unsubscribe();
  });

  async function toggleTask(task: Task) {
    if (!token) {
      return;
    }
    try {
      const updated = await api.updateTask(token, task.id, { completed: !task.completed });
      tasks = tasks.map((item) => (item.id === updated.id ? updated : item));
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update task.';
    }
  }

  $: openTasks = tasks
    .filter((task) => !task.completed)
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .slice(0, 3);
  $: recentLessons = lessons.slice(0, 2);
</script>

<svelte:head>
  <title>Ibis</title>
</svelte:head>

{#if !token}
  <section class="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
    <div class="space-y-6 rounded-3xl border border-orange-100 bg-white/80 p-8 shadow-xl shadow-orange-100">
      <div class="space-y-3">
        <p class="text-xs uppercase tracking-[0.5em] text-slate-500">Ibis</p>
        <h1 class="text-4xl sm:text-5xl">Notes that live inside the video timeline.</h1>
        <p class="text-base text-slate-600">
          Capture timestamps, collect tasks, and keep a running history of every session. Notes stay
          synced, searchable, and ready for students.
        </p>
      </div>
      <div class="flex flex-wrap gap-3">
        <a
          href="/register"
          class="rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          Create account
        </a>
        <a
          href="/login"
          class="rounded-full border border-slate-200 px-5 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
        >
          Log in
        </a>
      </div>
    </div>

    <div class="space-y-4 rounded-3xl border border-slate-200 bg-white/70 p-6 shadow-lg">
      <h2 class="text-xl">What you can do today</h2>
      <ul class="space-y-3 text-sm text-slate-600">
        <li>Track sessions with timestamped notes and a full edit history.</li>
        <li>Attach video links (YouTube/public for now) and jump by timestamp.</li>
        <li>Search and tag moments to keep practice materials organized.</li>
      </ul>
      <div class="rounded-2xl border border-dashed border-orange-200 bg-orange-50 p-4 text-xs text-orange-700">
        Collaboration, uploads, and transcription are queued for the next milestones.
      </div>
    </div>
  </section>
{:else}
  <section class="space-y-8">
    <div class="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-xl">Up next</h2>
            <p class="text-sm text-slate-500">Your next three open tasks.</p>
          </div>
          <a href="/tasks" class="text-sm text-orange-600 hover:underline">
            View all
          </a>
        </div>
        {#if error}
          <div class="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
            {error}
          </div>
        {/if}
        <div class="mt-4 space-y-3">
          {#if loading}
            <div class="text-sm text-slate-500">Loading tasks...</div>
          {:else if openTasks.length === 0}
            <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
              No open tasks right now.
            </div>
          {:else}
            {#each openTasks as task}
              <TaskItem {task} onToggle={toggleTask} showTimestamp={false} compact={true} />
            {/each}
          {/if}
        </div>
      </div>

      <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-xl">Latest lessons</h2>
            <p class="text-sm text-slate-500">Jump back into recent sessions.</p>
          </div>
          <a href="/lessons" class="text-sm text-orange-600 hover:underline">
            View all
          </a>
        </div>
        <div class="mt-4 space-y-3">
          {#if loading}
            <div class="text-sm text-slate-500">Loading lessons...</div>
          {:else if recentLessons.length === 0}
            <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
              No lessons yet.
            </div>
          {:else}
            {#each recentLessons as lesson}
              <a
                href={`/lessons/${lesson.id}`}
                class="block rounded-2xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-700 transition hover:border-orange-200 hover:shadow-sm"
              >
                <div class="text-xs text-slate-500">
                  {new Date(lesson.created_at).toLocaleString()}
                </div>
                <div class="mt-1 font-semibold text-slate-900">
                  {lesson.title && lesson.title.trim()
                    ? lesson.title
                    : new Date(lesson.created_at).toLocaleString(undefined, {
                        dateStyle: 'long',
                        timeStyle: 'short',
                      })}
                </div>
              </a>
            {/each}
          {/if}
        </div>
      </div>
    </div>

  </section>
{/if}
