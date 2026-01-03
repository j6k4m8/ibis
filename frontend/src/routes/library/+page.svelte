<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import { renderMarkdownPreview } from '$lib/utils/markdownPreview';
  import type { Note, Video } from '$lib/types';

  let token: string | null = null;
  let notes: Note[] = [];
  let videos: Video[] = [];
  let loading = true;
  let error = '';
  let searchQuery = '';
  let selectedTag = 'all';
  let sortOption: 'updated' | 'created' | 'title' = 'updated';

  let title = '';
  let videoUrl = '';
  let videoTitle = '';
  let selectedVideoId = '';
  let tagsText = '';
  let body = '';
  let creating = false;
  let modalOpen = false;
  let videoSource: 'none' | 'youtube' | 'library' = 'youtube';

  const unsubscribe = authStore.subscribe((state) => {
    token = state.token;
  });

  onMount(async () => {
    const state = await authStore.init();
    if (!state.token) {
      goto('/login');
      return;
    }

    await Promise.all([loadNotes(state.token), loadVideos(state.token)]);

    return () => unsubscribe();
  });

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

  async function loadVideos(activeToken: string) {
    try {
      videos = await api.listVideos(activeToken);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load videos.';
    }
  }

  function parseTags(text: string): string[] {
    return text
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
  }

  function openModal() {
    modalOpen = true;
  }

  function closeModal() {
    modalOpen = false;
  }

  function handleOverlayClick(event: MouseEvent) {
    if (event.currentTarget === event.target) {
      closeModal();
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      closeModal();
    }
  }

  async function createNote() {
    if (!token) {
      return;
    }

    creating = true;
    error = '';
    try {
      const payload: {
        title: string;
        body: string;
        tags: string[];
        video_url?: string;
        video_id?: string;
        video_title?: string;
      } = {
        title,
        body,
        tags: parseTags(tagsText),
      };

      const trimmedTitle = videoTitle.trim();
      if (trimmedTitle) {
        payload.video_title = trimmedTitle;
      }
      if (videoSource === 'youtube' && videoUrl.trim()) {
        payload.video_url = videoUrl.trim();
      }
      if (videoSource === 'library' && selectedVideoId) {
        payload.video_id = selectedVideoId;
      }

      await api.createNote(token, payload);
      title = '';
      videoUrl = '';
      videoTitle = '';
      selectedVideoId = '';
      tagsText = '';
      body = '';
      videoSource = 'youtube';
      modalOpen = false;
      await loadNotes(token);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to create note.';
    } finally {
      creating = false;
    }
  }

  $: availableTags = Array.from(new Set(notes.flatMap((note) => note.tags))).sort();
  $: localVideos = videos.filter((video) => video.source_type === 'local');
  $: canCreate = title.trim().length > 0 && (videoSource !== 'library' || selectedVideoId);

  $: filteredNotes = notes.filter((note) => {
    const query = searchQuery.trim().toLowerCase();
    const matchesQuery =
      query.length === 0 ||
      note.title.toLowerCase().includes(query) ||
      note.body.toLowerCase().includes(query) ||
      note.tags.some((tag) => tag.toLowerCase().includes(query));
    const matchesTag = selectedTag === 'all' || note.tags.includes(selectedTag);
    return matchesQuery && matchesTag;
  });

  $: sortedNotes = [...filteredNotes].sort((a, b) => {
    if (sortOption === 'created') {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    }
    if (sortOption === 'title') {
      return a.title.localeCompare(b.title);
    }
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  $: if (videoSource === 'library' && !videoTitle.trim()) {
    const selected = localVideos.find((video) => video.id === selectedVideoId);
    if (selected?.title) {
      videoTitle = selected.title;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h2 class="text-xl">Notes</h2>
      <p class="text-sm text-slate-500">{notes.length} total</p>
    </div>
    <button
      type="button"
      class="rounded-full bg-orange-500 px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:-translate-y-0.5 hover:bg-orange-400"
      on:click={openModal}
    >
      New lesson
    </button>
  </div>

  <div class="grid gap-3 lg:grid-cols-[2fr_1fr_1fr]">
    <input
      class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
      type="search"
      bind:value={searchQuery}
      placeholder="Search notes, tags, or text"
    />
    <div class="relative">
      <select
        class="w-full appearance-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
        bind:value={selectedTag}
      >
        <option value="all">All tags</option>
        {#each availableTags as tag}
          <option value={tag}>{tag}</option>
        {/each}
      </select>
      <span class="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
        ▾
      </span>
    </div>
    <div class="relative">
      <select
        class="w-full appearance-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
        bind:value={sortOption}
      >
        <option value="updated">Recently updated</option>
        <option value="created">Recently created</option>
        <option value="title">Title A-Z</option>
      </select>
      <span class="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
        ▾
      </span>
    </div>
  </div>

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
      {error}
    </div>
  {/if}

  <div class="grid gap-4 lg:grid-cols-2">
    {#if loading}
      <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
        Loading notes...
      </div>
    {:else if sortedNotes.length === 0}
      <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
        No notes yet. Create your first lesson note to get started.
      </div>
    {:else}
      {#each sortedNotes as note}
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
</section>

{#if modalOpen}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4 py-10"
    on:click={handleOverlayClick}
  >
    <div class="w-full max-w-xl rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-xl">Create a new lesson</h2>
          <p class="mt-1 text-sm text-slate-500">Add a title, optional video, and tags.</p>
        </div>
        <button
          type="button"
          class="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
          on:click={closeModal}
        >
          Close
        </button>
      </div>

      <form class="mt-6 space-y-4" on:submit|preventDefault={createNote}>
        <label class="block text-sm text-slate-600">
          Title
          <input
            class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
            type="text"
            bind:value={title}
            placeholder="Lesson title"
            required
          />
        </label>

        <div class="space-y-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-4">
          <div class="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Video source
          </div>
          <div class="grid gap-2 sm:grid-cols-3">
            <button
              type="button"
              class={`rounded-2xl border px-3 py-2 text-xs transition ${
                videoSource === 'none'
                  ? 'border-orange-400 bg-orange-50 text-orange-700'
                  : 'border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-100'
              }`}
              on:click={() => (videoSource = 'none')}
            >
              No video
            </button>
            <button
              type="button"
              class={`rounded-2xl border px-3 py-2 text-xs transition ${
                videoSource === 'youtube'
                  ? 'border-orange-400 bg-orange-50 text-orange-700'
                  : 'border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-100'
              }`}
              on:click={() => (videoSource = 'youtube')}
            >
              YouTube link
            </button>
            <button
              type="button"
              class={`rounded-2xl border px-3 py-2 text-xs transition ${
                videoSource === 'library'
                  ? 'border-orange-400 bg-orange-50 text-orange-700'
                  : 'border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-100'
              }`}
              on:click={() => (videoSource = 'library')}
            >
              Video library
            </button>
          </div>
          {#if videoSource === 'youtube'}
            <label class="block text-sm text-slate-600">
              Video link
              <input
                class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                type="url"
                bind:value={videoUrl}
                placeholder="https://youtube.com/..."
              />
            </label>
          {:else if videoSource === 'library'}
            <label class="block text-sm text-slate-600">
              Choose an uploaded video
              <select
                class="mt-2 w-full appearance-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                bind:value={selectedVideoId}
              >
                <option value="">Select a video</option>
                {#each localVideos as video}
                  <option value={video.id}>
                    {video.title ?? video.original_filename ?? 'Untitled upload'}
                  </option>
                {/each}
              </select>
            </label>
            {#if loading}
              <div class="text-xs text-slate-500">Loading your library...</div>
            {:else if localVideos.length === 0}
              <div class="text-xs text-slate-500">
                No uploads yet. Add a video in <a class="text-orange-600 hover:underline" href="/me">your library</a>.
              </div>
            {/if}
          {/if}
          {#if videoSource !== 'none'}
            <label class="block text-sm text-slate-600">
              Video title (optional)
              <input
                class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                type="text"
                bind:value={videoTitle}
                placeholder={videoSource === 'youtube' ? 'Auto-detected from YouTube' : 'Name this video'}
              />
            </label>
          {/if}
        </div>

        <label class="block text-sm text-slate-600">
          Tags (comma separated)
          <input
            class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
            type="text"
            bind:value={tagsText}
            placeholder="technique, rhythm, harmony"
          />
        </label>
        <label class="block text-sm text-slate-600">
          Starter notes
          <textarea
            class="mt-2 min-h-[140px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
            bind:value={body}
            placeholder="Write a quick outline or leave blank."
          ></textarea>
        </label>

        <button
          type="submit"
          class="w-full rounded-2xl bg-orange-500 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:-translate-y-0.5 hover:bg-orange-400 disabled:translate-y-0 disabled:opacity-60"
          disabled={creating || !canCreate}
        >
          {creating ? 'Creating...' : 'Create note'}
        </button>
      </form>
    </div>
  </div>
{/if}
