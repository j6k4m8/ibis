<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  import * as api from '$lib/api';
  import MarkdownEditor from '$lib/components/MarkdownEditor.svelte';
  import { authStore } from '$lib/stores/auth';
  import type { Note, NoteVersion } from '$lib/types';

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
  let videoStart = 0;
  let videoElement: HTMLVideoElement | null = null;

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

  async function loadNote(activeToken: string, noteId: string) {
    loading = true;
    error = '';
    try {
      note = await api.getNote(activeToken, noteId);
      title = note.title;
      body = note.body;
      tagsText = note.tags.join(', ');
      lastSavedAt = new Date(note.updated_at);
      lastSavedPayload = JSON.stringify({ title, body, tagsText });
      ready = true;
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
      });
      note = updated;
      lastSavedAt = new Date();
      lastSavedPayload = JSON.stringify({ title, body, tagsText });
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

    const payload = JSON.stringify({ title, body, tagsText });
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

  function handleTimestamp(event: CustomEvent<number>) {
    if (!note?.video_url) {
      return;
    }
    const seconds = event.detail;
    const youtubeId = getYouTubeId(note.video_url);
    if (youtubeId) {
      videoStart = seconds;
      return;
    }

    if (videoElement) {
      videoElement.currentTime = seconds;
      videoElement.play();
    }
  }

  $: if (ready) {
    title;
    body;
    tagsText;
    scheduleSave();
  }

  $: noteTags = parseTags(tagsText);
  $: youtubeId = note?.video_url ? getYouTubeId(note.video_url) : null;
  $: youtubeEmbed = youtubeId
    ? `https://www.youtube.com/embed/${youtubeId}?start=${videoStart}&autoplay=1&rel=0`
    : null;
  $: saveStatus = saving
    ? 'Saving...'
    : lastSavedAt
      ? `Saved ${lastSavedAt.toLocaleTimeString()}`
      : 'Not saved yet';
</script>

<svelte:head>
  <title>{note ? `${note.title} · Ibis` : 'Note · Ibis'}</title>
</svelte:head>

<div class="mb-6 text-sm text-slate-500">
  <a href="/notes" class="hover:underline">← Back to notes</a>
</div>

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
  <section class="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
    <div class="space-y-6">
      <div class="rounded-3xl border border-orange-100 bg-white/90 p-6 shadow-xl">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-xl">Lesson video</h2>
            {#if note.video_url}
              <p class="mt-2 text-sm text-slate-600">{note.video_url}</p>
              <a
                class="mt-3 inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                href={note.video_url}
                target="_blank"
                rel="noreferrer"
              >
                Open video
              </a>
            {:else}
              <p class="mt-2 text-sm text-slate-500">No video link attached yet.</p>
            {/if}
          </div>
          <div class="text-right text-xs text-slate-500">
            <div>Created {new Date(note.created_at).toLocaleDateString()}</div>
            <div>Updated {new Date(note.updated_at).toLocaleDateString()}</div>
          </div>
        </div>

        <div class="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
          {#if note.video_url}
            {#if youtubeEmbed}
              <iframe
                title="Lesson video"
                src={youtubeEmbed}
                class="aspect-video w-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen
              ></iframe>
            {:else}
              <video
                bind:this={videoElement}
                class="aspect-video w-full"
                src={note.video_url}
                controls
              ></video>
            {/if}
          {:else}
            <div class="flex h-64 items-center justify-center text-sm text-slate-400">
              Add a video link to start syncing timestamps.
            </div>
          {/if}
        </div>
      </div>

      <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="text-xl">History</h2>
          <span class="text-xs text-slate-500">{versions.length} snapshots</span>
        </div>
        <div class="mt-4 space-y-3">
          {#if versions.length === 0}
            <div class="text-sm text-slate-500">No history yet.</div>
          {:else}
            {#each versions as version}
              <button
                type="button"
                on:click={() => (versionPreview = version)}
                class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-left text-sm text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
              >
                <div class="text-xs text-slate-500">
                  {new Date(version.created_at).toLocaleString()}
                </div>
                <div class="font-semibold text-slate-900">{version.title}</div>
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
          <div class="mt-2 text-lg font-semibold text-slate-900">{versionPreview.title}</div>
          <p class="mt-2 whitespace-pre-wrap text-sm text-slate-700">{versionPreview.body}</p>
        </div>
      {/if}
    </div>

    <div class="space-y-6">
      <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
        <div class="space-y-4">
          <label class="block text-sm text-slate-600">
            Title
            <input
              class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
              type="text"
              bind:value={title}
            />
          </label>
          <label class="block text-sm text-slate-600">
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
                  href={`/tags?tag=${encodeURIComponent(tag)}`}
                  class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-500 hover:border-orange-200 hover:text-orange-700"
                >
                  #{tag}
                </a>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
        {#key note.id}
          <MarkdownEditor bind:value={body} on:timestamp={handleTimestamp} />
        {/key}
        <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
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
    </div>
  </section>
{/if}
