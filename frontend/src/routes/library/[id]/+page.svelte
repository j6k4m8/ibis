<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import type { Note, Video } from '$lib/types';

  let token: string | null = null;
  let video: Video | null = null;
  let loading = true;
  let error = '';
  let youtubeId: string | null = null;
  let resolvedVideoUrl: string | null = null;
  let title = '';
  let tagsText = '';
  let creating = false;
  let createdNote: Note | null = null;
  let linkedNotes: Note[] = [];
  let loadingNotes = false;

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
    await Promise.all([loadVideo(state.token, $page.params.id), loadLinkedNotes(state.token, $page.params.id)]);
    return () => unsubscribe();
  });

  onDestroy(() => {
    unsubscribe();
  });

  function parseTags(text: string): string[] {
    return text
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
  }

  async function loadVideo(activeToken: string, videoId: string) {
    loading = true;
    error = '';
    try {
      video = await api.getVideo(activeToken, videoId);
      title = video.title ?? fallbackTitle(video);
      resolveVideo(video);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load video.';
    } finally {
      loading = false;
    }
  }

  async function loadLinkedNotes(activeToken: string, videoId: string) {
    loadingNotes = true;
    try {
      linkedNotes = await api.listNotes(activeToken, { video_id: videoId });
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load linked notes.';
    } finally {
      loadingNotes = false;
    }
  }

  function resolveVideo(videoData: Video) {
    youtubeId = getYouTubeId(videoData.video_url ?? '');
    if (videoData.source_type === 'local' && videoData.video_url && token) {
      const url = new URL(videoData.video_url);
      url.searchParams.set('token', token);
      resolvedVideoUrl = url.toString();
    } else {
      resolvedVideoUrl = videoData.video_url ?? null;
    }
  }

  function getYouTubeId(url: string): string | null {
    if (!url) {
      return null;
    }
    if (url.includes('youtu.be/')) {
      const id = url.split('youtu.be/')[1];
      return id?.split('?')[0] ?? null;
    }
    const match = url.match(/[?&]v=([^&]+)/);
    return match ? match[1] : null;
  }

  function fallbackTitle(videoData: Video) {
    if (videoData.source_type === 'local') {
      return videoData.original_filename ?? 'Untitled upload';
    }
    if (videoData.video_url?.includes('youtube.com') || videoData.video_url?.includes('youtu.be')) {
      return 'YouTube video';
    }
    return 'External video';
  }

  async function createNote() {
    if (!token || !video) {
      return;
    }
    creating = true;
    error = '';
    try {
      const payload = {
        title: title.trim() || fallbackTitle(video),
        body: '',
        tags: parseTags(tagsText),
        video_id: video.id,
        video_title: title.trim() || undefined,
      };
      createdNote = await api.createNote(token, payload);
      await loadLinkedNotes(token, video.id);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to create note.';
    } finally {
      creating = false;
    }
  }

  $: canCreate = title.trim().length > 0;
</script>

<svelte:head>
  <title>{video ? `${video.title ?? 'Video'} · Library` : 'Video · Library'}</title>
</svelte:head>

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl">{video ? video.title ?? fallbackTitle(video) : 'Video'}</h1>
      {#if video}
        <p class="text-sm text-slate-500">
          Uploaded {new Date(video.created_at).toLocaleString()}
        </p>
      {/if}
    </div>
    <a
      href="/library"
      class="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
    >
      Back to library
    </a>
  </div>

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
      Loading video...
    </div>
  {:else if video}
    <div class="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
        <div class="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
          {#if youtubeId}
            <iframe
              class="aspect-video w-full"
              src={`https://www.youtube.com/embed/${youtubeId}`}
              title={video.title ?? 'YouTube video'}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
            ></iframe>
          {:else if resolvedVideoUrl}
            <video class="aspect-video w-full" src={resolvedVideoUrl} controls></video>
          {:else}
            <div class="flex h-64 items-center justify-center text-sm text-slate-400">
              No preview available.
            </div>
          {/if}
        </div>
        {#if video.video_url}
          <div class="mt-3 text-xs text-slate-500">
            <a href={video.video_url} target="_blank" rel="noreferrer" class="hover:underline">
              {video.video_url}
            </a>
          </div>
        {/if}
      </div>

      <div class="space-y-4">
        <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
          <h2 class="text-lg font-semibold text-slate-900">Create a lesson note</h2>
          <p class="mt-1 text-xs text-slate-500">Attach this video to a new note.</p>
          <form class="mt-4 space-y-3" on:submit|preventDefault={createNote}>
            <label class="block text-xs text-slate-600">
              Lesson title
              <input
                class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                type="text"
                bind:value={title}
                placeholder="Lesson title"
              />
            </label>
            <label class="block text-xs text-slate-600">
              Tags (optional)
              <input
                class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                type="text"
                bind:value={tagsText}
                placeholder="technique, rhythm"
              />
            </label>
            <button
              type="submit"
              class="w-full rounded-2xl bg-orange-500 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:-translate-y-0.5 hover:bg-orange-400 disabled:translate-y-0 disabled:opacity-60"
              disabled={!canCreate || creating}
            >
              {creating ? 'Creating...' : 'Create note'}
            </button>
          </form>
        </div>

        {#if createdNote}
          <div class="rounded-3xl border border-emerald-200 bg-emerald-50 p-6 text-sm text-emerald-700 shadow-xl">
            Note created. <a class="font-semibold underline" href={`/notes/${createdNote.id}`}>Open it</a>.
          </div>
        {/if}

        <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-slate-900">Notes using this video</h3>
            <span class="text-xs text-slate-500">{linkedNotes.length} notes</span>
          </div>
          <div class="mt-4 space-y-2">
            {#if loadingNotes}
              <div class="text-xs text-slate-500">Loading linked notes...</div>
            {:else if linkedNotes.length === 0}
              <div class="text-xs text-slate-500">No notes yet for this video.</div>
            {:else}
              {#each linkedNotes as note}
                <a
                  class="block rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700 transition hover:border-orange-200 hover:bg-orange-50"
                  href={`/notes/${note.id}`}
                >
                  <div class="font-semibold text-slate-900">{note.title}</div>
                  <div class="mt-1 text-[11px] text-slate-500">
                    Updated {new Date(note.updated_at).toLocaleString()}
                  </div>
                </a>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    </div>
  {/if}
</section>
