<script lang="ts">
import { onMount } from 'svelte';
import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { ApiError } from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import type { Video } from '$lib/types';

  // TODO: get from server config
  const MAX_UPLOAD_BYTES = 1000 * 1024 * 1024;

  let token: string | null = null;
  let videos: Video[] = [];
  let loading = true;
  let error = '';
  let filter: 'all' | 'youtube' | 'uploads' | 'external' = 'all';
  let sort: 'recent' | 'title' | 'size' = 'recent';
  let search = '';
  let editingVideoId: string | null = null;
  let editingTitle = '';
  let deletingVideoId: string | null = null;
  let dragActive = false;
  let uploadError = '';
  let fileInput: HTMLInputElement | null = null;
  let uploadingQueue = false;

  type UploadItem = {
    id: string;
    file: File;
    title: string;
    status: 'queued' | 'uploading' | 'done' | 'error';
    progress: number;
    error?: string;
  };

  let uploadQueue: UploadItem[] = [];

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

  function resolveThumbnailUrl(video: Video) {
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

  async function deleteVideo(video: Video) {
    if (!token) {
      return;
    }
    const confirmed = window.confirm(
      `Delete "${video.title ?? fallbackTitle(video)}"? This cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }
    deletingVideoId = video.id;
    error = '';
    try {
      await api.deleteVideo(token, video.id);
      videos = videos.filter((item) => item.id !== video.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        error = 'This video is attached to at least one note. Remove those links first.';
      } else {
        error = err instanceof Error ? err.message : 'Unable to delete video.';
      }
    } finally {
      deletingVideoId = null;
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    dragActive = true;
  }

  function handleDragLeave(event: DragEvent) {
    event.preventDefault();
    dragActive = false;
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    dragActive = false;
    const files = event.dataTransfer ? Array.from(event.dataTransfer.files) : [];
    if (!files.length) {
      return;
    }
    enqueueFiles(files);
  }

  function handleFileChange(event: Event) {
    const target = event.target as HTMLInputElement;
    const files = target.files ? Array.from(target.files) : [];
    if (!files.length) {
      return;
    }
    enqueueFiles(files);
    if (fileInput) {
      fileInput.value = '';
    }
  }

  function enqueueFiles(files: File[]) {
    uploadError = '';
    const incoming: UploadItem[] = [];
    for (const file of files) {
      if (!file.type.startsWith('video/')) {
        continue;
      }
      if (file.size > MAX_UPLOAD_BYTES) {
        uploadError = 'One or more files exceed the 100MB limit.';
        incoming.push({
          id: `${file.name}-${Date.now()}`,
          file,
          title: defaultTitle(file),
          status: 'error',
          progress: 0,
          error: 'File exceeds the 100MB limit.',
        });
        continue;
      }
      incoming.push({
        id: `${file.name}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        file,
        title: defaultTitle(file),
        status: 'queued',
        progress: 0,
      });
    }
    if (!incoming.length) {
      return;
    }
    uploadQueue = [...uploadQueue, ...incoming];
    void processQueue();
  }

  function defaultTitle(file: File) {
    return file.name.replace(/\.[^/.]+$/, '');
  }

  function updateUploadItem(id: string, patch: Partial<UploadItem>) {
    uploadQueue = uploadQueue.map((item) => (item.id === id ? { ...item, ...patch } : item));
  }

  async function processQueue() {
    if (uploadingQueue || !token) {
      return;
    }
    const shouldNavigate = uploadQueue.length === 1;
    let navigated = false;
    uploadingQueue = true;
    while (true) {
      const next = uploadQueue.find((item) => item.status === 'queued');
      if (!next) {
        break;
      }
      updateUploadItem(next.id, { status: 'uploading', progress: 0, error: undefined });
      try {
        const uploaded = await api.uploadVideoWithProgress(
          token,
          next.file,
          next.title.trim() || undefined,
          (percent) => updateUploadItem(next.id, { progress: percent }),
        );
        updateUploadItem(next.id, { status: 'done', progress: 100 });
        await loadVideos(token);
        if (shouldNavigate && !navigated) {
          navigated = true;
          goto(`/library/${uploaded.id}`);
        }
      } catch (err) {
        updateUploadItem(next.id, {
          status: 'error',
          error: err instanceof Error ? err.message : 'Unable to upload video.',
        });
      }
    }
    uploadingQueue = false;
  }

  function updateQueuedTitle(event: Event, itemId: string) {
    const target = event.currentTarget as HTMLInputElement | null;
    if (!target) {
      return;
    }
    updateUploadItem(itemId, { title: target.value });
  }

  function clearCompletedUploads() {
    uploadQueue = uploadQueue.filter(
      (item) => item.status !== 'done' && item.status !== 'error',
    );
  }

  function formatDuration(seconds?: number | null) {
    if (!seconds && seconds !== 0) {
      return '—';
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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

  $: totalUploadBytes = uploadQueue.reduce((acc, item) => acc + item.file.size, 0);
  $: uploadedBytes = uploadQueue.reduce(
    (acc, item) => acc + item.file.size * (item.progress / 100),
    0,
  );
  $: totalUploadPercent =
    totalUploadBytes > 0 ? Math.min(100, Math.round((uploadedBytes / totalUploadBytes) * 100)) : 0;
</script>

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h2 class="text-xl">Videos</h2>
      <p class="text-sm text-slate-500">Manage uploaded and linked videos.</p>
    </div>
    <a
      href="/processing"
      class="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
    >
      Processing queue
    </a>
  </div>

  <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold text-slate-900">Upload videos</h3>
      <span class="text-xs text-slate-500">Max 100MB per file</span>
    </div>
    <div class="mt-4 space-y-4">
      <div
        class={`flex flex-col items-center justify-center rounded-3xl border border-dashed px-4 py-8 text-center text-sm transition ${
          dragActive
            ? 'border-orange-400 bg-orange-50 text-orange-700'
            : 'border-slate-200 bg-slate-50 text-slate-500'
        }`}
        on:dragover={handleDragOver}
        on:dragleave={handleDragLeave}
        on:drop={handleDrop}
      >
        <p class="text-sm font-semibold">Drop videos here</p>
        <p class="mt-1 text-xs text-slate-400">or select multiple files to upload.</p>
        <label class="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold text-white">
          Choose files
          <input
            bind:this={fileInput}
            class="hidden"
            type="file"
            multiple
            accept="video/*"
            on:change={handleFileChange}
          />
        </label>
      </div>

      {#if uploadError}
        <div class="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {uploadError}
        </div>
      {/if}

      {#if uploadQueue.length > 0}
        <div class="space-y-3">
          <div class="flex items-center justify-between text-xs text-slate-500">
            <span>{uploadQueue.length} files in queue</span>
            <button
              type="button"
              class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
              on:click={clearCompletedUploads}
            >
              Clear completed
            </button>
          </div>
          <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600">
            <div class="flex items-center justify-between">
              <span class="text-xs text-slate-500">Total upload progress</span>
              <span class="text-[11px] text-slate-400">{totalUploadPercent}%</span>
            </div>
            <div class="mt-2 h-2 w-full rounded-full bg-slate-100">
              <div
                class="h-full rounded-full bg-orange-500 transition-all"
                style={`width: ${totalUploadPercent}%`}
              ></div>
            </div>
          </div>
          {#each uploadQueue as item}
            <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="text-sm font-semibold text-slate-900">{item.file.name}</div>
                <span class="text-[10px] uppercase tracking-widest text-slate-400">
                  {item.status}
                </span>
              </div>
              <div class="mt-1 text-[11px] text-slate-400">
                {formatBytes(item.file.size)}
              </div>
              {#if item.status === 'queued'}
                <input
                  class="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
                  type="text"
                  value={item.title}
                  placeholder="Video title"
                  on:input={(event) => updateQueuedTitle(event, item.id)}
                />
              {:else}
                <div class="mt-3 text-xs text-slate-500">{item.title}</div>
              {/if}
              <div class="mt-3 h-2 w-full rounded-full bg-slate-100">
                <div
                  class="h-full rounded-full bg-orange-500 transition-all"
                  style={`width: ${item.progress}%`}
                ></div>
              </div>
              {#if item.error}
                <div class="mt-2 text-[11px] text-red-600">{item.error}</div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
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
      No videos yet. Upload one above to get started.
    </div>
  {:else}
    <div class="space-y-3">
      {#each sortedVideos as video}
        <div class="rounded-3xl border border-slate-200 bg-white/90 px-5 py-4 shadow-sm">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="flex items-start gap-4">
              <div class="h-16 w-28 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                {#if resolveThumbnailUrl(video)}
                  <img
                    class="h-full w-full object-cover"
                    src={resolveThumbnailUrl(video)}
                    alt="Video thumbnail"
                  />
                {:else}
                  <div class="flex h-full items-center justify-center text-[10px] text-slate-400">
                    No thumbnail
                  </div>
                {/if}
              </div>
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
                {formatDuration(video.duration_seconds)} · {new Date(video.created_at).toLocaleString()}
              </div>
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
                <button
                  type="button"
                  class="rounded-full border border-red-200 px-3 py-1 text-red-600 transition hover:border-red-300 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                  on:click={() => deleteVideo(video)}
                  disabled={deletingVideoId === video.id}
                >
                  {deletingVideoId === video.id ? 'Deleting...' : 'Delete'}
                </button>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>
