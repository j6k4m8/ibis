<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import { renderMarkdownPreview } from '$lib/utils/markdownPreview';
  import { formatTimestamp } from '$lib/utils/timestamps';
  import type { Note, SearchResponse, Video } from '$lib/types';

  let token: string | null = null;
  let searchQuery = '';
  let results: SearchResponse | null = null;
  let loading = false;
  let error = '';
  let ready = false;
  let searchCounter = 0;
  let debounceId: ReturnType<typeof setTimeout> | null = null;
  let notesByVideoId = new Map<string, Note[]>();

  const unsubscribe = authStore.subscribe((state) => {
    token = state.token;
  });

  onMount(async () => {
    const state = await authStore.init();
    if (!state.token) {
      unsubscribe();
      goto('/login');
      return;
    }
    ready = true;
  });

  onDestroy(() => {
    if (debounceId) {
      clearTimeout(debounceId);
    }
    unsubscribe();
  });

  function resolveThumbnail(video: Video) {
    if (!video.thumbnail_url) {
      return null;
    }
    if (video.source_type !== 'local' || !token) {
      return video.thumbnail_url;
    }
    const url = new URL(video.thumbnail_url);
    url.searchParams.set('token', token);
    return url.toString();
  }

  function videoLabel(video: Video) {
    if (video.source_type === 'local') {
      return 'Uploaded video';
    }
    if (video.video_url?.includes('youtube.com') || video.video_url?.includes('youtu.be')) {
      return 'YouTube video';
    }
    return 'External video';
  }

  function fallbackVideoTitle(video: Video) {
    if (video.source_type === 'local') {
      return video.original_filename ?? 'Untitled upload';
    }
    if (video.video_url?.includes('youtube.com') || video.video_url?.includes('youtu.be')) {
      return 'YouTube video';
    }
    return 'External video';
  }

  async function runSearch(query: string) {
    if (!token) {
      return;
    }
    if (debounceId) {
      clearTimeout(debounceId);
    }
    const trimmed = query.trim();
    if (!trimmed) {
      results = null;
      error = '';
      loading = false;
      return;
    }
    const currentSearch = (searchCounter += 1);
    loading = true;
    error = '';
    debounceId = setTimeout(async () => {
      try {
        const payload = await api.searchLibrary(token, trimmed);
        if (currentSearch !== searchCounter) {
          return;
        }
        results = payload;
      } catch (err) {
        if (currentSearch !== searchCounter) {
          return;
        }
        error = err instanceof Error ? err.message : 'Unable to search library.';
        results = null;
      } finally {
        if (currentSearch === searchCounter) {
          loading = false;
        }
      }
    }, 250);
  }

  $: if (ready) {
    runSearch(searchQuery);
  }

  $: notesByVideoId = new Map();
  $: if (results) {
    results.notes.forEach((note) => {
      if (!note.video_id) {
        return;
      }
      const list = notesByVideoId.get(note.video_id) ?? [];
      list.push(note);
      notesByVideoId.set(note.video_id, list);
    });
  }

  $: totalResults =
    results?.notes.length +
      results?.videos.length +
      results?.lessons.length +
      results?.tags.length +
      results?.transcript_matches.length || 0;
</script>

<svelte:head>
  <title>Library · Search</title>
</svelte:head>

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <div>
      <h2 class="text-xl">Search</h2>
      <p class="text-sm text-slate-500">
        Search notes, lessons, videos, tags, and transcripts.
      </p>
    </div>
    {#if results}
      <span class="text-xs text-slate-500">{totalResults} results</span>
    {/if}
  </div>

  <input
    class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
    type="search"
    bind:value={searchQuery}
    placeholder="Search everything in your library"
  />

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
      Searching your library...
    </div>
  {:else if searchQuery.trim().length === 0}
    <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-6 py-8 text-sm text-slate-500">
      Start typing to search across your library.
    </div>
  {:else if results && totalResults === 0}
    <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-6 py-8 text-sm text-slate-500">
      No results found for "{searchQuery}".
    </div>
  {:else if results}
    <div class="space-y-6">
      {#if results.transcript_matches.length > 0}
        <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm">
          <div class="flex items-center justify-between">
            <h3 class="text-lg">Transcript matches</h3>
            <span class="text-xs text-slate-500">
              {results.transcript_matches.length} matches
            </span>
          </div>
          <div class="mt-4 grid gap-3">
            {#each results.transcript_matches as match}
              <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                  <span>
                    {formatTimestamp(match.start_seconds)} - {formatTimestamp(match.end_seconds)}
                  </span>
                  <a
                    href={`/library/${match.video_id}`}
                    class="text-orange-600 hover:underline"
                  >
                    {match.video_title ?? 'Open video'}
                  </a>
                </div>
                <div class="mt-2 text-sm text-slate-700">{match.text}</div>
                {#if notesByVideoId.get(match.video_id)?.length}
                  <div class="mt-3 flex flex-wrap gap-2">
                    {#each notesByVideoId.get(match.video_id) as note}
                      <a
                        href={`/notes/${note.id}`}
                        class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-600 transition hover:border-orange-200 hover:text-orange-700"
                      >
                        {note.title}
                      </a>
                    {/each}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if results.notes.length > 0}
        <div>
          <div class="flex items-center justify-between">
            <h3 class="text-lg">Notes</h3>
            <span class="text-xs text-slate-500">{results.notes.length} notes</span>
          </div>
          <div class="mt-4 grid gap-4 lg:grid-cols-2">
            {#each results.notes as note}
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
          </div>
        </div>
      {/if}

      {#if results.videos.length > 0}
        <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm">
          <div class="flex items-center justify-between">
            <h3 class="text-lg">Videos</h3>
            <span class="text-xs text-slate-500">{results.videos.length} videos</span>
          </div>
          <div class="mt-4 grid gap-4 lg:grid-cols-2">
            {#each results.videos as video}
              <a
                href={`/library/${video.id}`}
                class="group flex gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-4 transition hover:-translate-y-0.5 hover:border-orange-200 hover:shadow-md"
              >
                <div class="h-20 w-32 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                  {#if resolveThumbnail(video)}
                    <img
                      class="h-full w-full object-cover"
                      src={resolveThumbnail(video)}
                      alt="Video thumbnail"
                    />
                  {:else}
                    <div class="flex h-full items-center justify-center text-[10px] text-slate-400">
                      No thumbnail
                    </div>
                  {/if}
                </div>
                <div class="min-w-0">
                  <div class="text-xs uppercase tracking-widest text-slate-500">
                    {videoLabel(video)}
                  </div>
                  <div class="mt-1 truncate text-base font-semibold text-slate-900 group-hover:text-orange-700">
                    {video.title ?? fallbackVideoTitle(video)}
                  </div>
                  <div class="mt-1 text-xs text-slate-500">
                    Updated {new Date(video.updated_at).toLocaleDateString()}
                  </div>
                </div>
              </a>
            {/each}
          </div>
        </div>
      {/if}

      {#if results.lessons.length > 0}
        <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm">
          <div class="flex items-center justify-between">
            <h3 class="text-lg">Lessons</h3>
            <span class="text-xs text-slate-500">{results.lessons.length} lessons</span>
          </div>
          <div class="mt-4 space-y-3">
            {#each results.lessons as lesson}
              <a
                href={`/lessons/${lesson.id}`}
                class="block rounded-2xl border border-transparent bg-slate-50 px-4 py-4 transition hover:border-slate-200 hover:bg-white"
              >
                <div class="text-xs text-slate-500">
                  Updated {new Date(lesson.updated_at).toLocaleDateString()}
                </div>
                <div class="mt-1 text-base font-semibold text-slate-900">
                  {lesson.title ?? 'Untitled lesson'}
                </div>
              </a>
            {/each}
          </div>
        </div>
      {/if}

      {#if results.tags.length > 0}
        <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm">
          <div class="flex items-center justify-between">
            <h3 class="text-lg">Tags</h3>
            <span class="text-xs text-slate-500">{results.tags.length} tags</span>
          </div>
          <div class="mt-4 flex flex-wrap gap-2">
            {#each results.tags as tag}
              <a
                href={`/library/tags?tag=${encodeURIComponent(tag)}`}
                class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-500 transition hover:border-orange-200 hover:text-orange-700"
              >
                #{tag}
              </a>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</section>
