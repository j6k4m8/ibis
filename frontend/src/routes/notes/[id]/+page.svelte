<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  import * as api from '$lib/api';
  import MarkdownEditor from '$lib/components/MarkdownEditor.svelte';
  import TranscriptScroller from '$lib/components/TranscriptScroller.svelte';
  import { authStore } from '$lib/stores/auth';
  import { renderMarkdown, renderMarkdownPreview } from '$lib/utils/markdownPreview';
  import { parseSegments } from '$lib/utils/segments';
  import { formatTimestamp, parseTimestamp } from '$lib/utils/timestamps';
  import type { Note, NoteVersion, TranscriptChunk } from '$lib/types';

  let note: Note | null = null;
  let versions: NoteVersion[] = [];
  let versionPreview: NoteVersion | null = null;

  let title = '';
  let body = '';
  let tagsText = '';
  let error = '';
  let loading = true;
  let saving = false;
  let token: string | null = null;
  let ready = false;
  let lastSavedAt: Date | null = null;
  let lastSavedPayload = '';
  let saveTimer: ReturnType<typeof setTimeout> | null = null;
  let youtubeContainer: HTMLDivElement | null = null;
  let youtubePlayer: any = null;
  let youtubeReady = false;
  let youtubeLoopTimer: ReturnType<typeof setInterval> | null = null;
  let youtubeTranscriptTimer: ReturnType<typeof setInterval> | null = null;
  let youtubeApiPromise: Promise<void> | null = null;
  let youtubePlayerId: string | null = null;
  let segmentLoop: { start: number; end: number } | null = null;
  let videoStartSeconds: number | null = null;
  let videoEndSeconds: number | null = null;
  let videoStartText = '';
  let videoEndText = '';
  let videoElement: HTMLVideoElement | null = null;
  let resolvedVideoUrl: string | null = null;
  let transcriptChunks: TranscriptChunk[] = [];
  let transcriptError = '';
  let loadingTranscript = false;
  let activeTranscriptId: string | null = null;
  let createdAtInput = '';
  let updatingCreatedAt = false;

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

  onDestroy(() => {
    if (youtubeLoopTimer) {
      clearInterval(youtubeLoopTimer);
      youtubeLoopTimer = null;
    }
    if (youtubeTranscriptTimer) {
      clearInterval(youtubeTranscriptTimer);
      youtubeTranscriptTimer = null;
    }
    if (youtubePlayer && typeof youtubePlayer.destroy === 'function') {
      youtubePlayer.destroy();
    }
  });

  function parseTags(text: string): string[] {
    return text
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
  }

  function getYouTubeId(url: string): string | null {
    if (url.includes('youtu.be/')) {
      const id = url.split('youtu.be/')[1];
      return id?.split('?')[0] ?? null;
    }

    const match = url.match(/[?&]v=([^&]+)/);
    return match ? match[1] : null;
  }

  async function loadYouTubeApi() {
    if (youtubeApiPromise) {
      return youtubeApiPromise;
    }
    youtubeApiPromise = new Promise<void>((resolve) => {
      if (typeof window === 'undefined') {
        resolve();
        return;
      }
      const win = window as typeof window & {
        YT?: { Player?: any };
        onYouTubeIframeAPIReady?: () => void;
      };

      if (win.YT?.Player) {
        resolve();
        return;
      }

      if (!document.querySelector('script[data-ibis-youtube]')) {
        const script = document.createElement('script');
        script.src = 'https://www.youtube.com/iframe_api';
        script.async = true;
        script.dataset.ibisYoutube = 'true';
        document.body.appendChild(script);
      }

      const previous = win.onYouTubeIframeAPIReady;
      win.onYouTubeIframeAPIReady = () => {
        if (typeof previous === 'function') {
          previous();
        }
        resolve();
      };
    });

    return youtubeApiPromise;
  }

  async function initializeYouTubePlayer(videoId: string) {
    if (!youtubeContainer) {
      return;
    }
    await loadYouTubeApi();

    const win = window as typeof window & { YT?: { Player?: any } };
    if (!win.YT?.Player) {
      return;
    }

    if (youtubePlayer && typeof youtubePlayer.destroy === 'function') {
      youtubePlayer.destroy();
    }
    youtubeReady = false;
    youtubePlayerId = videoId;

    youtubePlayer = new win.YT.Player(youtubeContainer, {
      videoId,
      width: '100%',
      height: '100%',
      playerVars: {
        rel: 0,
        modestbranding: 1,
        playsinline: 1,
      },
      events: {
        onReady: () => {
          youtubeReady = true;
          const start = videoStartSeconds ?? null;
          if (start !== null) {
            youtubePlayer.seekTo(start, true);
            youtubePlayer.pauseVideo();
          }
          updateYouTubeLoopMonitor();
          updateYouTubeTranscriptMonitor();
        },
      },
    });
  }

  function updateYouTubeLoopMonitor() {
    if (!youtubeReady || !youtubePlayer || typeof youtubePlayer.getCurrentTime !== 'function') {
      if (youtubeLoopTimer) {
        clearInterval(youtubeLoopTimer);
        youtubeLoopTimer = null;
      }
      return;
    }

    const loopEnd = segmentLoop?.end ?? videoEndSeconds;
    if (loopEnd === null || loopEnd === undefined) {
      if (youtubeLoopTimer) {
        clearInterval(youtubeLoopTimer);
        youtubeLoopTimer = null;
      }
      return;
    }

    const loopStart = segmentLoop?.start ?? videoStartSeconds ?? 0;
    if (youtubeLoopTimer) {
      clearInterval(youtubeLoopTimer);
    }
    youtubeLoopTimer = setInterval(() => {
      if (!youtubePlayer || typeof youtubePlayer.getCurrentTime !== 'function') {
        return;
      }
      const current = youtubePlayer.getCurrentTime();
      if (current >= loopEnd - 0.15) {
        youtubePlayer.seekTo(loopStart, true);
        youtubePlayer.playVideo();
      }
    }, 250);
  }

  function updateYouTubeTranscriptMonitor() {
    if (youtubeTranscriptTimer) {
      clearInterval(youtubeTranscriptTimer);
      youtubeTranscriptTimer = null;
    }
    if (!youtubeReady || !youtubePlayer || typeof youtubePlayer.getCurrentTime !== 'function') {
      return;
    }
    if (transcriptChunks.length === 0) {
      return;
    }
    youtubeTranscriptTimer = setInterval(() => {
      if (!youtubePlayer || typeof youtubePlayer.getCurrentTime !== 'function') {
        return;
      }
      const current = youtubePlayer.getCurrentTime();
      updateActiveTranscript(current);
    }, 500);
  }

  async function loadNote(activeToken: string, noteId: string) {
    loading = true;
    error = '';
    try {
      note = await api.getNote(activeToken, noteId);
      title = note.title;
      body = note.body;
      tagsText = note.tags.join(', ');
      videoStartSeconds = note.video_start_seconds ?? null;
      videoEndSeconds = note.video_end_seconds ?? null;
      videoStartText = videoStartSeconds !== null ? formatTimestamp(videoStartSeconds) : '';
      videoEndText = videoEndSeconds !== null ? formatTimestamp(videoEndSeconds) : '';
      lastSavedAt = new Date(note.updated_at);
      lastSavedPayload = JSON.stringify({
        title,
        body,
        tagsText,
        videoStartSeconds,
        videoEndSeconds,
      });
      ready = true;
      createdAtInput = toDatetimeLocal(note.created_at);
      if (note.video_id) {
        await loadTranscript(activeToken, note.video_id);
      } else {
        transcriptChunks = [];
        activeTranscriptId = null;
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load note.';
    } finally {
      loading = false;
    }
  }

  async function loadVersions(activeToken: string, noteId: string) {
    try {
      versions = await api.listNoteVersions(activeToken, noteId);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load history.';
    }
  }

  async function loadTranscript(activeToken: string, videoId: string) {
    loadingTranscript = true;
    transcriptError = '';
    try {
      transcriptChunks = await api.listTranscriptChunks(activeToken, videoId);
      activeTranscriptId = null;
      updateYouTubeTranscriptMonitor();
    } catch (err) {
      transcriptError = err instanceof Error ? err.message : 'Unable to load transcript.';
    } finally {
      loadingTranscript = false;
    }
  }

  async function saveNote() {
    if (!token || !note) {
      return;
    }
    saving = true;
    error = '';
    try {
      const updated = await api.updateNote(token, note.id, {
        title,
        body,
        tags: parseTags(tagsText),
        video_start_seconds: videoStartSeconds,
        video_end_seconds: videoEndSeconds,
        created_at: fromDatetimeLocal(createdAtInput),
      });
      note = updated;
      createdAtInput = toDatetimeLocal(updated.created_at);
      lastSavedAt = new Date();
      lastSavedPayload = JSON.stringify({
        title,
        body,
        tagsText,
        videoStartSeconds,
        videoEndSeconds,
      });
      await loadVersions(token, note.id);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to save note.';
    } finally {
      saving = false;
    }
  }

  function scheduleSave() {
    if (!ready || !note || !token) {
      return;
    }

    const payload = JSON.stringify({
      title,
      body,
      tagsText,
      videoStartSeconds,
      videoEndSeconds,
    });
    if (payload === lastSavedPayload) {
      return;
    }

    if (saveTimer) {
      clearTimeout(saveTimer);
    }
    saveTimer = setTimeout(() => {
      saveNote();
    }, 900);
  }

  function seekToTimestamp(seconds: number, clearLoop = true) {
    if (!note?.video_url) {
      return;
    }
    if (clearLoop) {
      stopSegmentLoop();
    }
    const youtubeId = getYouTubeId(note.video_url);
    if (youtubeId) {
      if (youtubePlayer && youtubeReady) {
        youtubePlayer.seekTo(seconds, true);
        youtubePlayer.playVideo();
      }
      return;
    }

    if (videoElement) {
      videoElement.currentTime = seconds;
      videoElement.play();
    }
  }

  function handleTimestamp(event: CustomEvent<number>) {
    seekToTimestamp(event.detail, true);
  }

  function startSegmentLoop(start: number, end: number) {
    if (!note?.video_url) {
      return;
    }
    const ordered = start <= end ? [start, end] : [end, start];
    segmentLoop = { start: ordered[0], end: ordered[1] };
    updateYouTubeLoopMonitor();

    if (youtubePlayer && youtubeReady) {
      youtubePlayer.seekTo(ordered[0], true);
      youtubePlayer.playVideo();
      return;
    }

    if (videoElement) {
      videoElement.currentTime = ordered[0];
      videoElement.play();
    }
  }

  function stopSegmentLoop() {
    segmentLoop = null;
    updateYouTubeLoopMonitor();
  }

  function handleSegment(event: CustomEvent<{ start: number; end: number }>) {
    startSegmentLoop(event.detail.start, event.detail.end);
  }

  function handleVideoLoaded() {
    if (videoElement) {
      const start = segmentLoop?.start ?? videoStartSeconds;
      if (start !== null && start !== undefined) {
        videoElement.currentTime = start;
      }
    }
  }

  function handleVideoTimeUpdate() {
    if (!videoElement) {
      return;
    }

    updateActiveTranscript(videoElement.currentTime);
    const loopEnd = segmentLoop?.end ?? videoEndSeconds;
    if (loopEnd === null || loopEnd === undefined) {
      return;
    }
    const loopStart = segmentLoop?.start ?? videoStartSeconds ?? 0;
    if (videoElement.currentTime >= loopEnd) {
      videoElement.currentTime = loopStart;
      videoElement.play();
    }
  }

  function updateActiveTranscript(currentTime: number) {
    if (transcriptChunks.length === 0) {
      activeTranscriptId = null;
      return;
    }
    const current = transcriptChunks.find(
      (chunk) => currentTime >= chunk.start_seconds && currentTime <= chunk.end_seconds,
    );
    activeTranscriptId = current?.id ?? null;
  }

  function handleTranscriptSeek(seconds: number) {
    if (!note?.video_url) {
      return;
    }
    const youtubeId = getYouTubeId(note.video_url);
    if (youtubeId) {
      if (youtubePlayer && youtubeReady) {
        youtubePlayer.seekTo(seconds, true);
        youtubePlayer.playVideo();
      }
      return;
    }
    if (videoElement) {
      videoElement.currentTime = seconds;
      videoElement.play();
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

  async function saveCreatedAt() {
    if (!token || !note) {
      return;
    }
    updatingCreatedAt = true;
    error = '';
    try {
      const updated = await api.updateNote(token, note.id, {
        created_at: fromDatetimeLocal(createdAtInput),
      });
      note = updated;
      createdAtInput = toDatetimeLocal(updated.created_at);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update created time.';
    } finally {
      updatingCreatedAt = false;
    }
  }

  function updateVideoRange() {
    const startParsed = parseTimestamp(videoStartText);
    const endParsed = parseTimestamp(videoEndText);

    if (videoStartText.trim() === '') {
      videoStartSeconds = null;
    } else if (startParsed !== null) {
      videoStartSeconds = startParsed;
    }

    if (videoEndText.trim() === '') {
      videoEndSeconds = null;
    } else if (endParsed !== null) {
      videoEndSeconds = endParsed;
    }

    if (videoStartSeconds !== null && videoEndSeconds !== null) {
      if (videoEndSeconds < videoStartSeconds) {
        const temp = videoEndSeconds;
        videoEndSeconds = videoStartSeconds;
        videoStartSeconds = temp;
        videoStartText = formatTimestamp(videoStartSeconds);
        videoEndText = formatTimestamp(videoEndSeconds);
      }
    }

    segmentLoop = null;
    updateYouTubeLoopMonitor();
  }


  $: if (ready) {
    title;
    body;
    tagsText;
    scheduleSave();
  }

  $: noteTags = parseTags(tagsText);
  $: segments = parseSegments(body);
  $: youtubeId = note?.video_url ? getYouTubeId(note.video_url) : null;
  $: resolvedVideoUrl = note?.video_url ?? null;
  $: if (note?.video_source_type === 'local') {
    if (note.video_url && token) {
      const url = new URL(note.video_url);
      url.searchParams.set('token', token);
      resolvedVideoUrl = url.toString();
    } else {
      resolvedVideoUrl = null;
    }
  }
  $: if (youtubeId && youtubeContainer && youtubeId !== youtubePlayerId) {
    initializeYouTubePlayer(youtubeId);
  }
  $: if (!youtubeId && youtubePlayer && typeof youtubePlayer.destroy === 'function') {
    youtubePlayer.destroy();
    youtubePlayer = null;
    youtubeReady = false;
    if (youtubeLoopTimer) {
      clearInterval(youtubeLoopTimer);
      youtubeLoopTimer = null;
    }
    if (youtubeTranscriptTimer) {
      clearInterval(youtubeTranscriptTimer);
      youtubeTranscriptTimer = null;
    }
  }
  $: saveStatus = saving
    ? 'Saving...'
    : lastSavedAt
      ? `Saved ${lastSavedAt.toLocaleTimeString()}`
      : 'Not saved yet';
  $: recentVersions = versions.slice(0, 3);
  $: transcriptHelperText = youtubeId
    ? 'Click a line to jump to that timestamp.'
    : 'Play the video to follow along. Click a line to jump.';
  $: transcriptEmptyText = note?.video_id
    ? 'No transcript yet. Transcription runs in the background.'
    : 'Attach a video to see transcripts.';
</script>

<svelte:head>
  <title>{note ? `${note.title} · Ibis` : 'Note · Ibis'}</title>
</svelte:head>

{#if error}
  <div class="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
    {error}
  </div>
{/if}

{#if loading}
  <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
    Loading note...
  </div>
{:else if note}
  <section class="grid gap-8 lg:grid-cols-[2fr_1fr]">
    <div class="space-y-6">
      <div class="rounded-3xl border border-orange-100 bg-white/90 p-6 shadow-xl">
        <div class="flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
          <div>Created {new Date(note.created_at).toLocaleDateString()}</div>
          <div>Updated {new Date(note.updated_at).toLocaleDateString()}</div>
        </div>

        <div class="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
          {#if note.video_url}
            {#if youtubeId}
              <div class="aspect-video w-full" bind:this={youtubeContainer}></div>
            {:else}
            <video
              bind:this={videoElement}
              class="aspect-video w-full"
              src={resolvedVideoUrl}
              controls
              on:loadedmetadata={handleVideoLoaded}
              on:timeupdate={handleVideoTimeUpdate}
            ></video>
          {/if}
          {:else}
            <div class="flex h-64 items-center justify-center text-sm text-slate-400">
              Add a video link to start syncing timestamps.
            </div>
          {/if}
        </div>

        {#if note.video_url}
          <div class="mt-3 text-xs text-slate-500">
            <a
              href={resolvedVideoUrl}
              target="_blank"
              rel="noreferrer"
              class="hover:underline"
            >
              {note.video_url}
            </a>
            {#if note.video_id}
              <span class="mx-2 text-slate-300">•</span>
              <a
                href={`/library/${note.video_id}`}
                class="text-slate-500 hover:text-orange-600 hover:underline"
              >
                View in library
              </a>
            {/if}
          </div>
        {:else}
          <div class="mt-3 text-xs text-slate-400">No video link attached yet.</div>
        {/if}
        {#if segments.length > 0 || segmentLoop}
          <div class="mt-4 rounded-2xl border border-slate-100 bg-white px-4 py-4">
            <div class="flex items-center justify-between">
              <div class="text-xs font-semibold uppercase tracking-widest text-slate-500">
                Segments
              </div>
              {#if segmentLoop}
                <button
                  type="button"
                  class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                  on:click={stopSegmentLoop}
                >
                  Stop looping
                </button>
              {/if}
            </div>
            {#if segments.length === 0}
              <div class="mt-3 text-xs text-slate-400">
                Add a segment like <code>|:0:30 - 1:10:|</code> in your notes.
              </div>
            {:else}
              <div class="mt-3 space-y-2">
                {#each segments as segment}
                  <button
                    type="button"
                    class="flex w-full flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200 px-3 py-2 text-left text-xs text-slate-600 transition hover:border-sky-200 hover:bg-sky-50"
                    on:click={() => startSegmentLoop(segment.start, segment.end)}
                  >
                    <span class="inline-flex items-center gap-2">
                      <span class="rounded-full bg-sky-100 px-2 py-1 text-[11px] font-semibold text-sky-700">
                        {segment.startLabel}–{segment.endLabel}
                      </span>
                      <span class="text-slate-500">
                        {segment.contextBefore}
                        {segment.contextBefore && segment.contextAfter ? ' ' : ''}
                        {segment.contextAfter}
                      </span>
                    </span>
                    <span class="text-[11px] text-slate-400">Play loop</span>
                  </button>
                  <div class="flex flex-wrap gap-2 pl-3 text-[11px] text-slate-400">
                    <button
                      type="button"
                      class="rounded-full border border-slate-200 px-2 py-1 transition hover:border-sky-200 hover:bg-sky-50"
                      on:click={() => seekToTimestamp(segment.start, false)}
                    >
                      {segment.startLabel}
                    </button>
                    <button
                      type="button"
                      class="rounded-full border border-slate-200 px-2 py-1 transition hover:border-sky-200 hover:bg-sky-50"
                      on:click={() => seekToTimestamp(segment.end, false)}
                    >
                      {segment.endLabel}
                    </button>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
        <div class="mt-4 grid gap-4 lg:grid-cols-[1fr_1.2fr]">
          <div class="space-y-3 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-3">
            <label class="block text-xs text-slate-600">
              Tags
              <input
                class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                type="text"
                bind:value={tagsText}
                placeholder="technique, rhythm"
              />
            </label>
            {#if noteTags.length > 0}
              <div class="flex flex-wrap gap-2">
                {#each noteTags as tag}
                  <a
                    href={`/library/tags?tag=${encodeURIComponent(tag)}`}
                    class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-500 hover:border-orange-200 hover:text-orange-700"
                  >
                    #{tag}
                  </a>
                {/each}
              </div>
            {/if}
            <div class="space-y-2">
              <div class="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                Playback range
              </div>
              <div class="grid gap-2 sm:grid-cols-2">
                <label class="block text-[11px] text-slate-500">
                  Start
                  <input
                    class="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                    type="text"
                    bind:value={videoStartText}
                    placeholder="0:00"
                    on:blur={() => {
                      updateVideoRange();
                      scheduleSave();
                    }}
                    on:input={() => {
                      updateVideoRange();
                      scheduleSave();
                    }}
                  />
                </label>
                <label class="block text-[11px] text-slate-500">
                  End
                  <input
                    class="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                    type="text"
                    bind:value={videoEndText}
                    placeholder="3:30"
                    on:blur={() => {
                      updateVideoRange();
                      scheduleSave();
                    }}
                    on:input={() => {
                      updateVideoRange();
                      scheduleSave();
                    }}
                  />
                </label>
              </div>
              <p class="text-[10px] text-slate-400">
                Use mm:ss or hh:mm:ss. Leave blank for full video.
              </p>
            </div>
          </div>
          <div class="space-y-3">
            {#if transcriptError}
              <div class="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
                {transcriptError}
              </div>
            {:else if loadingTranscript}
              <div class="text-xs text-slate-500">Loading transcript...</div>
            {:else}
              <TranscriptScroller
                title="Transcript"
                helperText={transcriptHelperText}
                emptyText={transcriptEmptyText}
                chunks={transcriptChunks}
                activeId={activeTranscriptId}
                onSeek={handleTranscriptSeek}
                compact={true}
              />
            {/if}
          </div>
        </div>
      </div>
    </div>

    <div class="space-y-6">
      <div class="space-y-3">
        <input
          class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-lg font-semibold shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
          type="text"
          bind:value={title}
          placeholder="Note title"
          aria-label="Note title"
        />
        <div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span class="text-[11px] uppercase tracking-widest text-slate-400">Created</span>
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
      </div>
      <div class="rounded-3xl border border-slate-200 bg-white/90 px-0 py-4 shadow-xl">
        {#key note.id}
          <MarkdownEditor
            bind:value={body}
            on:timestamp={handleTimestamp}
            on:segment={handleSegment}
          />
        {/key}
        <div class="mt-4 flex flex-wrap items-center justify-between gap-3 px-4 text-xs text-slate-500">
          <span>{saveStatus}</span>
          <button
            type="button"
            on:click={saveNote}
            class="rounded-full border border-slate-200 px-4 py-2 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
          >
            Save now
          </button>
        </div>
      </div>

      <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="text-xl">History</h2>
          <div class="flex items-center gap-3 text-xs text-slate-500">
            <span>{versions.length} snapshots</span>
            <a href={`/notes/${note.id}/history`} class="hover:underline">
              View all
            </a>
          </div>
        </div>
        <div class="mt-4 space-y-3">
          {#if recentVersions.length === 0}
            <div class="text-sm text-slate-500">No history yet.</div>
          {:else}
            {#each recentVersions as version}
              <button
                type="button"
                on:click={() => (versionPreview = version)}
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-left text-sm text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
              >
                <div class="text-xs font-semibold text-slate-500">
                  {new Date(version.created_at).toLocaleString()}
                </div>
                {#if version.body}
                  <div class="ibis-markdown mt-2 text-sm text-slate-700">
                    {@html renderMarkdownPreview(version.body, 2)}
                  </div>
                {:else}
                  <div class="mt-1 text-sm text-slate-400">Empty snapshot</div>
                {/if}
              </button>
            {/each}
          {/if}
        </div>
      </div>

      {#if versionPreview}
        <div class="rounded-3xl border border-orange-200 bg-orange-50 p-6 shadow-xl">
          <div class="flex items-center justify-between">
            <h3 class="text-lg">Snapshot preview</h3>
            <button
              type="button"
              class="text-xs text-orange-700 hover:underline"
              on:click={() => (versionPreview = null)}
            >
              Close
            </button>
          </div>
          <div class="mt-3 text-xs text-orange-700">
            {new Date(versionPreview.created_at).toLocaleString()}
          </div>
          {#if versionPreview.body}
            <div class="ibis-markdown mt-3 text-sm text-slate-700">
              {@html renderMarkdown(versionPreview.body)}
            </div>
          {:else}
            <div class="mt-3 text-sm text-slate-400">Empty snapshot</div>
          {/if}
        </div>
      {/if}
    </div>
  </section>
{/if}
