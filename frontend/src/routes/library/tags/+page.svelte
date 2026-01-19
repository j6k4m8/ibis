<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import { renderMarkdownPreview } from '$lib/utils/markdownPreview';
  import type { Note } from '$lib/types';

  let notes: Note[] = [];
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

    await loadNotes(state.token);

    return () => unsubscribe();
  });

  async function loadNotes(activeToken: string) {
    loading = true;
    error = '';
    try {
      notes = await api.listNotes(activeToken);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load tags.';
    } finally {
      loading = false;
    }
  }

  $: selectedTag = $page.url.searchParams.get('tag');
  $: tags = Array.from(new Set(notes.flatMap((note) => note.tags))).sort();
  $: filteredNotes = selectedTag
    ? notes.filter((note) => note.tags.includes(selectedTag))
    : notes;
</script>

<section class="grid gap-8 lg:grid-cols-[0.6fr_1.4fr]">
  <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
    <h2 class="text-2xl">Tags</h2>
    <p class="mt-2 text-sm text-slate-500">Browse notes by tag.</p>

    <div class="mt-4 flex flex-wrap gap-2">
      <a
        href="/library/tags"
        class={`rounded-full border px-3 py-1 text-[11px] ${
          selectedTag ? 'border-slate-200 text-slate-500' : 'border-orange-200 text-orange-700'
        }`}
      >
        All tags
      </a>
      {#each tags as tag}
        <a
          href={`/library/tags?tag=${encodeURIComponent(tag)}`}
          class={`rounded-full border px-3 py-1 text-[11px] ${
            selectedTag === tag
              ? 'border-orange-200 text-orange-700'
              : 'border-slate-200 text-slate-500 hover:border-orange-200 hover:text-orange-700'
          }`}
        >
          #{tag}
        </a>
      {/each}
    </div>
  </div>

  <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl">{selectedTag ? `#${selectedTag}` : 'All notes'}</h2>
      <span class="text-xs text-slate-500">{filteredNotes.length} notes</span>
    </div>

    {#if error}
      <div class="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
        {error}
      </div>
    {/if}

    <div class="mt-6 grid gap-4 lg:grid-cols-2">
      {#if loading}
        <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
          Loading notes...
        </div>
      {:else if filteredNotes.length === 0}
        <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          No notes found for this tag.
        </div>
      {:else}
        {#each filteredNotes as note}
          <a
            href={`/notes/${note.id}`}
            class="group block rounded-3xl border border-slate-200 bg-white/90 px-6 py-5 shadow-sm transition hover:-translate-y-0.5 hover:border-orange-200 hover:shadow-md"
          >
            <div class="flex items-center justify-between text-xs text-slate-500">
              <span>{new Date(note.updated_at).toLocaleString()}</span>
              {#if note.tags.length > 0}
                <span class="rounded-full bg-orange-100 px-2 py-1 text-[10px] uppercase tracking-widest text-orange-700">
                  {note.tags.length} tags
                </span>
              {/if}
            </div>
            <div class="mt-2 text-lg font-semibold text-slate-900 group-hover:text-orange-700">
              {note.title}
            </div>
            {#if note.body}
              <div class="ibis-markdown mt-1 text-sm text-slate-600">
                {@html renderMarkdownPreview(note.body, 3)}
              </div>
            {:else}
              <p class="mt-1 text-sm text-slate-600">No notes yet. Click to start writing.</p>
            {/if}
            {#if note.tags.length > 0}
              <div class="mt-3 flex flex-wrap gap-2">
                {#each note.tags as tag}
                  <span class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-500">
                    #{tag}
                  </span>
                {/each}
              </div>
            {/if}
          </a>
        {/each}
      {/if}
    </div>
  </div>
</section>
