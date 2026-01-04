<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  import * as api from '$lib/api';
  import { ApiError } from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import type { Note, TranscriptChunk, Video } from '$lib/types';
  import TranscriptScroller from '$lib/components/TranscriptScroller.svelte';

  let token: string | null = null;
  let video: Video | null = null;
  let loading = true;
  let error = '';
  let youtubeId: string | null = null;
  let resolvedVideoUrl: string | null = null;
  let videoTitle = '';
  let noteTitle = '';
  let tagsText = '';
  let creating = false;
  let createdNote: Note | null = null;
  let linkedNotes: Note[] = [];
  let loadingNotes = false;
  let deleting = false;
  let savingVideoTitle = false;
  let transcriptChunks: TranscriptChunk[] = [];
  let transcriptError = '';
  let loadingTranscript = false;
  let activeChunkId: string | null = null;
  let videoElement: HTMLVideoElement | null = null;
  let createdAtInput = '';
  let updatingCreatedAt = false;
  let showDeleteModal = false;

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
    await Promise.all([
      loadVideo(state.token, $page.params.id),
      loadLinkedNotes(state.token, $page.params.id),
      loadTranscript(state.token, $page.params.id),
    ]);
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
      videoTitle = video.title ?? fallbackTitle(video);
      noteTitle = videoTitle;
      resolveVideo(video);
      createdAtInput = toDatetimeLocal(video.original_created_at ?? video.created_at);
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

  async function loadTranscript(activeToken: string, videoId: string) {
    loadingTranscript = true;
    transcriptError = '';
    try {
      transcriptChunks = await api.listTranscriptChunks(activeToken, videoId);
    } catch (err) {
      transcriptError = err instanceof Error ? err.message : 'Unable to load transcript.';
    } finally {
      loadingTranscript = false;
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

  function formatVideoCreatedAt(videoData: Video) {
    const timestamp = videoData.original_created_at ?? videoData.created_at;
    return new Date(timestamp).toLocaleString(undefined, {
      dateStyle: 'long',
      timeStyle: 'short',
    });
  }

  function handleTranscriptSeek(seconds: number) {
    if (video?.source_type === 'local' && videoElement) {
      videoElement.currentTime = seconds;
      videoElement.play();
      return;
    }
    if (youtubeId) {
      const url = new URL(
        video?.video_url ?? `https://www.youtube.com/watch?v=${youtubeId}`,
      );
      url.searchParams.set('t', `${Math.floor(seconds)}s`);
      window.open(url.toString(), '_blank');
    }
  }

  function handleVideoTimeUpdate(event: Event) {
    const target = event.currentTarget as HTMLVideoElement | null;
    if (!target) {
      return;
    }
    updateActiveChunk(target.currentTime);
  }

  function updateActiveChunk(currentTime: number) {
    if (transcriptChunks.length === 0) {
      activeChunkId = null;
      return;
    }
    const current = transcriptChunks.find(
      (chunk) => currentTime >= chunk.start_seconds && currentTime <= chunk.end_seconds,
    );
    activeChunkId = current?.id ?? null;
  }

  async function createNote() {
    if (!token || !video) {
      return;
    }
    creating = true;
    error = '';
    try {
      const payload = {
        title: noteTitle.trim() || fallbackTitle(video),
        body: '',
        tags: parseTags(tagsText),
        video_id: video.id,
        video_title: noteTitle.trim() || undefined,
      };
      createdNote = await api.createNote(token, payload);
      await loadLinkedNotes(token, video.id);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to create note.';
    } finally {
      creating = false;
    }
  }

  async function deleteVideo() {
    if (!token || !video) {
      return;
    }
    if (linkedNotes.length > 0) {
      error = 'This video is attached to at least one note. Remove those links first.';
      return;
    }
    const confirmed = window.confirm(
      `Delete "${video.title ?? fallbackTitle(video)}"? This cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }
    deleting = true;
    error = '';
    try {
      await api.deleteVideo(token, video.id);
      goto('/library/videos');
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        error = 'This video is attached to at least one note. Remove those links first.';
      } else {
        error = err instanceof Error ? err.message : 'Unable to delete video.';
      }
    } finally {
      deleting = false;
    }
  }

  async function saveVideoTitle() {
    if (!token || !video) {
      return;
    }
    const trimmed = videoTitle.trim() || undefined;
    if ((video.title ?? undefined) === trimmed) {
      return;
    }
    savingVideoTitle = true;
    error = '';
    try {
      const updated = await api.updateVideo(token, video.id, {
        title: trimmed,
      });
      video = updated;
      videoTitle = updated.title ?? fallbackTitle(updated);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update video title.';
    } finally {
      savingVideoTitle = false;
    }
  }

  async function saveCreatedAt() {
    if (!token || !video) {
      return;
    }
    updatingCreatedAt = true;
    error = '';
    try {
      const updated = await api.updateVideo(token, video.id, {
        created_at: fromDatetimeLocal(createdAtInput),
      });
      video = updated;
      createdAtInput = toDatetimeLocal(updated.created_at);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update created time.';
    } finally {
      updatingCreatedAt = false;
    }
  }

  function toDatetimeLocal(value?: string | null) {
    if (!value) {
      return '';
    }
    const date = new Date(value);
    const offsetMs = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
  }

  function fromDatetimeLocal(value: string) {
    if (!value) {
      return undefined;
    }
    const date = new Date(value);
    return date.toISOString();
  }

  $: canCreate = noteTitle.trim().length > 0;
</script>

<svelte:head>
  <title>{video ? `${video.title ?? 'Video'} · Library` : 'Video · Library'}</title>
</svelte:head>

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div class="space-y-2">
      <div class="flex flex-wrap items-center gap-3">
        <input
          class="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-lg font-semibold shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100 sm:max-w-md"
          type="text"
          bind:value={videoTitle}
          placeholder="Video title"
          on:blur={saveVideoTitle}
        />
        {#if savingVideoTitle}
          <span class="text-xs text-slate-400">Saving...</span>
        {/if}
      </div>
      {#if video}
        <p class="text-sm text-slate-500">
          Uploaded {formatVideoCreatedAt(video)}
        </p>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <label class="text-[11px] uppercase tracking-widest text-slate-400">Created</label>
          <input
            class="rounded-xl border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
            type="datetime-local"
            bind:value={createdAtInput}
          />
          <button
            type="button"
            class="rounded-full border border-slate-200 px-2 py-1 text-[11px] text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
            on:click={saveCreatedAt}
            disabled={updatingCreatedAt}
          >
            {updatingCreatedAt ? 'Saving...' : 'Update'}
          </button>
        </div>
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
            <video
              class="aspect-video w-full"
              src={resolvedVideoUrl}
              controls
              bind:this={videoElement}
              on:timeupdate={handleVideoTimeUpdate}
            ></video>
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
        {#if transcriptError}
          <div class="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
            {transcriptError}
          </div>
        {:else if loadingTranscript}
          <div class="mt-6 text-xs text-slate-500">Loading transcript...</div>
        {:else}
          <div class="mt-6">
            <TranscriptScroller
              title="Transcript"
              helperText={video.source_type === 'local'
                ? 'Play the video to follow along. Click a line to jump.'
                : 'Click a line to open YouTube at that timestamp.'}
              chunks={transcriptChunks}
              activeId={activeChunkId}
              onSeek={handleTranscriptSeek}
              compact={true}
            />
          </div>
        {/if}
      </div>

      <div class="space-y-4">
        <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
          <h2 class="text-lg font-semibold text-slate-900">Create a note</h2>
          <p class="mt-1 text-xs text-slate-500">Attach this video to a new note.</p>
          <form class="mt-4 space-y-3" on:submit|preventDefault={createNote}>
            <label class="block text-xs text-slate-600">
              Note title
              <input
                class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                type="text"
                bind:value={noteTitle}
                placeholder="Note title"
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

        <div class="rounded-3xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 shadow-xl">
          <div class="flex items-center justify-between">
            <div>
              <div class="font-semibold">Delete video</div>
              <div class="mt-1 text-xs text-red-600">
                This permanently removes the video and its assets.
              </div>
            </div>
            <button
              type="button"
              class="rounded-full border border-red-200 px-4 py-2 text-xs text-red-700 transition hover:border-red-300 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
              on:click={() => (showDeleteModal = true)}
              disabled={linkedNotes.length > 0}
              title={linkedNotes.length > 0
                ? 'Remove the linked notes before deleting this video.'
                : 'Delete this video'}
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</section>

{#if showDeleteModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4 py-10">
    <div class="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl">
      <h3 class="text-lg font-semibold text-slate-900">Delete this video?</h3>
      <p class="mt-2 text-sm text-slate-500">
        This will permanently remove the video and its assets. This action cannot be undone.
      </p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button
          type="button"
          class="rounded-full border border-slate-200 px-4 py-2 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
          on:click={() => (showDeleteModal = false)}
          disabled={deleting}
        >
          Cancel
        </button>
        <button
          type="button"
          class="rounded-full bg-red-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-red-500 disabled:opacity-60"
          on:click={deleteVideo}
          disabled={deleting}
        >
          {deleting ? 'Deleting...' : 'Delete'}
        </button>
      </div>
    </div>
  </div>
{/if}
