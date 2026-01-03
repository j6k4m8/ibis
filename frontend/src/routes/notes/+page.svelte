<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import type { Note } from '$lib/types';

  let notes: Note[] = [];
  let loading = true;
  let error = '';

  let title = '';
  let videoUrl = '';
  let tagsText = '';
  let body = '';
  let creating = false;

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

    await loadNotes(state.token);

    return () => unsubscribe();
  });

  function parseTags(text: string): string[] {
    return text
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
  }

  async function loadNotes(activeToken: string) {
    loading = true;
    error = '';
    try {
      notes = await api.listNotes(activeToken);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load notes.';
    } finally {
      loading = false;
    }
  }

  async function createNote() {
    if (!token) {
      return;
    }

    creating = true;
    error = '';

    try {
      await api.createNote(token, {
        title,
        body,
        tags: parseTags(tagsText),
        video_url: videoUrl || undefined,
      });
      title = '';
      videoUrl = '';
      tagsText = '';
      body = '';
      await loadNotes(token);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to create note.';
    } finally {
      creating = false;
    }
  }
</script>

<svelte:head>
  <title>Notes · Ibis</title>
</svelte:head>

<section class="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
  <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl">Your notes</h1>
      <span class="text-xs text-slate-500">{notes.length} total</span>
    </div>

    {#if error}
      <div class="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
        {error}
      </div>
    {/if}

    <div class="mt-6 space-y-3">
      {#if loading}
        <div class="text-sm text-slate-500">Loading notes...</div>
      {:else if notes.length === 0}
        <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          No notes yet. Create your first lesson note to get started.
        </div>
      {:else}
        {#each notes as note}
          <a
            href={`/notes/${note.id}`}
            class="block rounded-2xl border border-transparent bg-slate-50 px-4 py-4 transition hover:border-slate-200 hover:bg-white"
          >
            <div class="flex items-center justify-between text-xs text-slate-500">
              <span>{new Date(note.updated_at).toLocaleString()}</span>
              <span class="rounded-full bg-orange-100 px-2 py-1 text-[10px] uppercase tracking-widest text-orange-700">
                {note.tags.length} tags
              </span>
            </div>
            <div class="mt-2 text-lg font-semibold text-slate-900">{note.title}</div>
            <p class="mt-1 text-sm text-slate-600">
              {note.body || 'No notes yet. Click to start writing.'}
            </p>
          </a>
        {/each}
      {/if}
    </div>
  </div>

  <div class="rounded-3xl border border-orange-100 bg-white/90 p-6 shadow-xl">
    <h2 class="text-2xl">Create a new lesson</h2>
    <p class="mt-2 text-sm text-slate-500">Add a title, optional video link, and tags.</p>

    <form class="mt-6 space-y-4" on:submit|preventDefault={createNote}>
      <label class="block text-sm text-slate-600">
        Title
        <input
          class="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:border-orange-300 focus:outline-none"
          type="text"
          bind:value={title}
          placeholder="Lesson title"
          required
        />
      </label>
      <label class="block text-sm text-slate-600">
        Video link
        <input
          class="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:border-orange-300 focus:outline-none"
          type="url"
          bind:value={videoUrl}
          placeholder="https://youtube.com/..."
        />
      </label>
      <label class="block text-sm text-slate-600">
        Tags (comma separated)
        <input
          class="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:border-orange-300 focus:outline-none"
          type="text"
          bind:value={tagsText}
          placeholder="technique, rhythm, harmony"
        />
      </label>
      <label class="block text-sm text-slate-600">
        Starter notes
        <textarea
          class="mt-2 min-h-[140px] w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:border-orange-300 focus:outline-none"
          bind:value={body}
          placeholder="Write a quick outline or leave blank."
        ></textarea>
      </label>

      <button
        type="submit"
        class="w-full rounded-xl bg-orange-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-orange-400 disabled:opacity-60"
        disabled={creating || !title}
      >
        {creating ? 'Creating...' : 'Create note'}
      </button>
    </form>
  </div>
</section>
