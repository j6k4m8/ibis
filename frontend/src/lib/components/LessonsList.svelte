<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import type { Lesson } from '$lib/types';

  export let title = 'Lessons';
  export let subtitle = 'Grouped note timelines.';
  export let showCreate = true;

  let token: string | null = null;
  let lessons: Lesson[] = [];
  let loading = true;
  let error = '';
  let creating = false;
  let modalOpen = false;
  let newTitle = '';

  const unsubscribe = authStore.subscribe((state) => {
    token = state.token;
  });

  onMount(async () => {
    const state = await authStore.init();
    if (!state.token) {
      goto('/login');
      return;
    }
    await loadLessons(state.token);
    return () => unsubscribe();
  });

  async function loadLessons(activeToken: string) {
    loading = true;
    error = '';
    try {
      lessons = await api.listLessons(activeToken);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load lessons.';
    } finally {
      loading = false;
    }
  }

  function formatLessonTitle(lesson: Lesson) {
    if (lesson.title && lesson.title.trim()) {
      return lesson.title;
    }
    return new Date(lesson.created_at).toLocaleString(undefined, {
      dateStyle: 'long',
      timeStyle: 'short',
    });
  }

  async function createLesson() {
    if (!token) {
      return;
    }
    creating = true;
    error = '';
    try {
      const lesson = await api.createLesson(token, { title: newTitle.trim() || undefined });
      lessons = [lesson, ...lessons];
      newTitle = '';
      modalOpen = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to create lesson.';
    } finally {
      creating = false;
    }
  }
</script>

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl">{title}</h1>
      <p class="text-sm text-slate-500">{subtitle}</p>
    </div>
    {#if showCreate}
      <button
        type="button"
        class="rounded-full bg-orange-500 px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:-translate-y-0.5 hover:bg-orange-400"
        on:click={() => (modalOpen = true)}
      >
        New lesson
      </button>
    {/if}
  </div>

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
      Loading lessons...
    </div>
  {:else if lessons.length === 0}
    <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
      No lessons yet. Upload a few videos close together to auto-create one.
    </div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2">
      {#each lessons as lesson}
        <a
          href={`/lessons/${lesson.id}`}
          class="block rounded-3xl border border-slate-200 bg-white/90 px-6 py-5 shadow-sm transition hover:-translate-y-0.5 hover:border-orange-200 hover:shadow-md"
        >
          <div class="text-xs text-slate-500">
            {new Date(lesson.created_at).toLocaleString()}
          </div>
          <div class="mt-2 text-lg font-semibold text-slate-900">
            {formatLessonTitle(lesson)}
          </div>
        </a>
      {/each}
    </div>
  {/if}
</section>

{#if modalOpen}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4 py-10">
    <div class="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-slate-900">Create a lesson</h2>
        <button
          type="button"
          class="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
          on:click={() => (modalOpen = false)}
        >
          Close
        </button>
      </div>
      <form class="mt-4 space-y-4" on:submit|preventDefault={createLesson}>
        <label class="block text-sm text-slate-600">
          Title (optional)
          <input
            class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
            type="text"
            bind:value={newTitle}
            placeholder="Leave blank to use the timestamp"
          />
        </label>
        <button
          type="submit"
          class="w-full rounded-2xl bg-orange-500 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:-translate-y-0.5 hover:bg-orange-400 disabled:translate-y-0 disabled:opacity-60"
          disabled={creating}
        >
          {creating ? 'Creating...' : 'Create lesson'}
        </button>
      </form>
    </div>
  </div>
{/if}
