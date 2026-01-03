<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import { renderMarkdown } from '$lib/utils/markdownPreview';
  import type { Note, NoteVersion } from '$lib/types';

  let note: Note | null = null;
  let versions: NoteVersion[] = [];
  let selectedVersion: NoteVersion | null = null;
  let loading = true;
  let error = '';
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

    const noteId = $page.params.id;
    await Promise.all([loadNote(state.token, noteId), loadVersions(state.token, noteId)]);

    return () => unsubscribe();
  });

  async function loadNote(activeToken: string, noteId: string) {
    try {
      note = await api.getNote(activeToken, noteId);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load note.';
    }
  }

  async function loadVersions(activeToken: string, noteId: string) {
    loading = true;
    error = '';
    try {
      versions = await api.listNoteVersions(activeToken, noteId);
      selectedVersion = versions[0] ?? null;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load history.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>{note ? `${note.title} · History` : 'History · Ibis'}</title>
</svelte:head>

<section class="space-y-6">
  <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl">History</h1>
        <p class="text-sm text-slate-500">{note?.title ?? 'Lesson notes'}</p>
      </div>
      {#if note}
        <a
          href={`/notes/${note.id}`}
          class="rounded-full border border-slate-200 px-4 py-2 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
        >
          Back to note
        </a>
      {/if}
    </div>
  </div>

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
      {error}
    </div>
  {/if}

  <div class="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
    {#if loading}
      <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
        Loading history...
      </div>
    {:else if versions.length === 0}
      <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-6 py-8 text-sm text-slate-500">
        No history snapshots yet.
      </div>
    {:else}
      <div class="space-y-4">
        {#each versions as version}
          <button
            type="button"
            on:click={() => (selectedVersion = version)}
            class="w-full rounded-3xl border border-slate-200 bg-white/90 px-6 py-4 text-left text-sm text-slate-600 shadow-sm transition hover:border-slate-300 hover:bg-white"
          >
            <div class="text-xs font-semibold text-slate-500">
              {new Date(version.created_at).toLocaleString()}
            </div>
            <div class="mt-2 text-xs text-slate-400">
              {version.body ? 'View snapshot' : 'Empty snapshot'}
            </div>
          </button>
        {/each}
      </div>
      <div class="lg:sticky lg:top-6">
        {#if selectedVersion}
          <div class="rounded-3xl border border-orange-200 bg-orange-50 p-6 shadow-sm">
            <div class="text-xs font-semibold text-orange-700">
              {new Date(selectedVersion.created_at).toLocaleString()}
            </div>
            {#if selectedVersion.body}
              <div class="ibis-markdown mt-3 text-sm text-slate-700">
                {@html renderMarkdown(selectedVersion.body)}
              </div>
            {:else}
              <div class="mt-3 text-sm text-slate-400">Empty snapshot</div>
            {/if}
          </div>
        {:else}
          <div class="rounded-3xl border border-dashed border-slate-200 bg-slate-50 px-6 py-8 text-sm text-slate-500">
            Select a snapshot to preview.
          </div>
        {/if}
      </div>
    {/if}
  </div>
</section>
