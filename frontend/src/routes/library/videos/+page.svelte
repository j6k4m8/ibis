<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import type { Video } from '$lib/types';

  let token: string | null = null;
  let videos: Video[] = [];
  let loading = true;
  let error = '';
  let filter: 'all' | 'youtube' | 'uploads' | 'external' = 'all';
  let sort: 'recent' | 'title' | 'size' = 'recent';
  let search = '';
  let editingVideoId: string | null = null;
  let editingTitle = '';

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
    await loadVideos(state.token);
    return () => unsubscribe();
  });

  async function loadVideos(activeToken: string) {
    loading = true;
    error = '';
    try {
      videos = await api.listVideos(activeToken);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load videos.';
    } finally {
      loading = false;
    }
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

  function fallbackTitle(video: Video) {
    if (video.source_type === 'local') {
      return video.original_filename ?? 'Untitled upload';
    }
    if (video.video_url?.includes('youtube.com') || video.video_url?.includes('youtu.be')) {
      return 'YouTube video';
    }
    return 'External video';
  }

  function formatBytes(value: number | null | undefined) {
    if (!value && value !== 0) {
      return '—';
    }
    if (value < 1024) {
      return `${value} B`;
    }
    const units = ['KB', 'MB', 'GB', 'TB'];
    let size = value;
    let unitIndex = -1;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex += 1;
    }
    return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
  }

  function startRename(video: Video) {
    editingVideoId = video.id;
    editingTitle = video.title ?? '';
  }

  function cancelRename() {
    editingVideoId = null;
    editingTitle = '';
  }

  async function saveRename(videoId: string) {
    if (!token) {
      return;
    }
    try {
      const updated = await api.updateVideo(token, videoId, {
        title: editingTitle.trim() || undefined,
      });
      videos = videos.map((video) => (video.id === updated.id ? updated : video));
      cancelRename();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update video title.';
    }
  }

  $: filteredVideos = videos.filter((video) => {
    if (filter === 'uploads' && video.source_type !== 'local') {
      return false;
    }
    if (filter === 'youtube') {
      const isYoutube =
        video.video_url?.includes('youtube.com') || video.video_url?.includes('youtu.be');
      if (!isYoutube) {
        return false;
      }
    }
    if (filter === 'external') {
      const isYoutube =
        video.video_url?.includes('youtube.com') || video.video_url?.includes('youtu.be');
      if (video.source_type === 'local' || isYoutube) {
        return false;
      }
    }
    const query = search.trim().toLowerCase();
    if (!query) {
      return true;
    }
    const title = (video.title ?? fallbackTitle(video)).toLowerCase();
    const filename = (video.original_filename ?? '').toLowerCase();
    return title.includes(query) || filename.includes(query);
  });

  $: sortedVideos = [...filteredVideos].sort((a, b) => {
    if (sort === 'title') {
      const titleA = (a.title ?? fallbackTitle(a)).toLowerCase();
      const titleB = (b.title ?? fallbackTitle(b)).toLowerCase();
      return titleA.localeCompare(titleB);
    }
    if (sort === 'size') {
      return (b.file_size_bytes ?? 0) - (a.file_size_bytes ?? 0);
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
</script>

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h2 class="text-xl">Videos</h2>
      <p class="text-sm text-slate-500">Manage uploaded and linked videos.</p>
    </div>
    <a
      href="/me"
      class="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
    >
      Upload videos
    </a>
  </div>

  <div class="grid gap-3 lg:grid-cols-[2fr_1fr_1fr]">
    <input
      class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
      type="search"
      bind:value={search}
      placeholder="Search videos"
    />
    <div class="relative">
      <select
        class="w-full appearance-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
        bind:value={filter}
      >
        <option value="all">All sources</option>
        <option value="uploads">Uploads</option>
        <option value="youtube">YouTube</option>
        <option value="external">Other external</option>
      </select>
      <span class="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
        ▾
      </span>
    </div>
    <div class="relative">
      <select
        class="w-full appearance-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
        bind:value={sort}
      >
        <option value="recent">Newest first</option>
        <option value="title">Title A-Z</option>
        <option value="size">Largest files</option>
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

  {#if loading}
    <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
      Loading videos...
    </div>
  {:else if sortedVideos.length === 0}
    <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
      No videos yet. Upload one from your account page.
    </div>
  {:else}
    <div class="space-y-3">
      {#each sortedVideos as video}
        <div class="rounded-3xl border border-slate-200 bg-white/90 px-5 py-4 shadow-sm">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="space-y-1">
              {#if editingVideoId === video.id}
                <input
                  class="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                  type="text"
                  bind:value={editingTitle}
                  placeholder={fallbackTitle(video)}
                />
              {:else}
                <a
                  class="text-sm font-semibold text-slate-900 hover:text-orange-700"
                  href={`/library/${video.id}`}
                >
                  {video.title ?? fallbackTitle(video)}
                </a>
              {/if}
              <div class="text-xs text-slate-500">
                {videoLabel(video)} · {formatBytes(video.file_size_bytes)} ·
                {new Date(video.created_at).toLocaleString()}
              </div>
            </div>
            <div class="flex items-center gap-2 text-xs">
              {#if editingVideoId === video.id}
                <button
                  type="button"
                  class="rounded-full border border-slate-200 px-3 py-1 text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                  on:click={() => saveRename(video.id)}
                >
                  Save
                </button>
                <button
                  type="button"
                  class="rounded-full border border-slate-200 px-3 py-1 text-slate-500 transition hover:border-slate-300 hover:bg-slate-50"
                  on:click={cancelRename}
                >
                  Cancel
                </button>
              {:else}
                <button
                  type="button"
                  class="rounded-full border border-slate-200 px-3 py-1 text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                  on:click={() => startRename(video)}
                >
                  Rename
                </button>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>
