<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import { initPreferences, navPinned, setNavPinned } from '$lib/stores/preferences';
  import type { Job, Me } from '$lib/types';

  // TODO: get from server config
  const MAX_UPLOAD_BYTES = 1000 * 1024 * 1024;

  let token: string | null = null;
  let profile: Me | null = null;
  let loading = true;
  let error = '';
  let uploading = false;
  let uploadError = '';
  let uploadTitle = '';
  let selectedFile: File | null = null;
  let fileInput: HTMLInputElement | null = null;
  let jobs: Job[] = [];
  let loadingJobs = false;
  let jobError = '';
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let navPinnedValue = false;

  const unsubscribe = authStore.subscribe((state) => {
    token = state.token;
  });
  const unsubscribePrefs = navPinned.subscribe((value) => {
    navPinnedValue = value;
  });

  onMount(async () => {
    const state = await authStore.init();
    initPreferences();
    if (!state.token) {
      unsubscribe();
      unsubscribePrefs();
      goto('/login');
      return;
    }
    await loadProfile(state.token);
    await loadJobs(state.token);
    pollTimer = setInterval(() => {
      if (token) {
        loadJobs(token);
      }
    }, 8000);
    return () => {
      if (pollTimer) {
        clearInterval(pollTimer);
      }
      unsubscribe();
      unsubscribePrefs();
    };
  });

  async function loadProfile(activeToken: string) {
    loading = true;
    error = '';
    try {
      profile = await api.getMe(activeToken);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load account details.';
    } finally {
      loading = false;
    }
  }

  async function loadJobs(activeToken: string) {
    loadingJobs = true;
    jobError = '';
    try {
      jobs = await api.listJobs(activeToken);
    } catch (err) {
      jobError = err instanceof Error ? err.message : 'Unable to load processing jobs.';
    } finally {
      loadingJobs = false;
    }
  }

  function formatBytes(value: number) {
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

  function handleFileChange(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0] ?? null;
    if (!file) {
      selectedFile = null;
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      uploadError = 'File exceeds the 100MB limit.';
      selectedFile = null;
      if (fileInput) {
        fileInput.value = '';
      }
      return;
    }
    uploadError = '';
    selectedFile = file;
    if (!uploadTitle.trim()) {
      uploadTitle = file.name.replace(/\.[^/.]+$/, '');
    }
  }

  async function uploadVideo() {
    if (!token || !selectedFile) {
      return;
    }
    uploading = true;
    uploadError = '';
    try {
      await api.uploadVideo(token, selectedFile, uploadTitle.trim() || undefined);
      selectedFile = null;
      uploadTitle = '';
      if (fileInput) {
        fileInput.value = '';
      }
      await loadProfile(token);
      await loadJobs(token);
    } catch (err) {
      uploadError = err instanceof Error ? err.message : 'Unable to upload video.';
    } finally {
      uploading = false;
    }
  }

  function logout() {
    authStore.clear();
    goto('/login');
  }

  function handleNavPinnedChange(event: Event) {
    const target = event.currentTarget as HTMLInputElement | null;
    if (!target) {
      return;
    }
    setNavPinned(target.checked);
  }

  $: storageUsed = profile?.storage_used_bytes ?? 0;
  $: storageLimit = profile?.storage_limit_bytes ?? 1;
  $: usagePercent = Math.min(100, (storageUsed / storageLimit) * 100);
  $: recentJobs = jobs.slice(0, 6);
</script>

<svelte:head>
  <title>Account · Ibis</title>
</svelte:head>

<section class="space-y-8">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl">Your account</h1>
      <p class="text-sm text-slate-500">Manage uploads and storage for your library.</p>
      {#if profile?.user}
        <p class="text-xs text-slate-400">
          Signed in as {profile.user.display_name ?? profile.user.email}
        </p>
      {/if}
    </div>
    <button
      type="button"
      class="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
      on:click={logout}
    >
      Log out
    </button>
  </div>

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
      Loading account...
    </div>
  {:else}
    <div class="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-slate-900">Storage</h2>
          <span class="text-xs text-slate-500">
            {formatBytes(storageUsed)} of {formatBytes(storageLimit)}
          </span>
        </div>
        <div class="mt-4 h-3 w-full rounded-full bg-slate-100">
          <div
            class="h-full rounded-full bg-orange-500 transition-all"
            style={`width: ${usagePercent}%`}
          ></div>
        </div>
        <p class="mt-3 text-xs text-slate-500">
          Uploads contribute to your 5GB free tier.
        </p>
      </div>

      <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
        <h2 class="text-lg font-semibold text-slate-900">Upload a video</h2>
        <p class="mt-1 text-xs text-slate-500">Max 100MB per file.</p>
        <div class="mt-4 space-y-3">
          <label class="block text-xs text-slate-600">
            Video file
            <input
              bind:this={fileInput}
              class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
              type="file"
              accept="video/*"
              on:change={handleFileChange}
            />
          </label>
          <label class="block text-xs text-slate-600">
            Title (optional)
            <input
              class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
              type="text"
              bind:value={uploadTitle}
              placeholder="Give the clip a name"
            />
          </label>
          {#if uploadError}
            <div class="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
              {uploadError}
            </div>
          {/if}
          {#if selectedFile}
            <div class="text-xs text-slate-500">
              {selectedFile.name} · {formatBytes(selectedFile.size)}
            </div>
          {/if}
          <button
            type="button"
            class="w-full rounded-2xl bg-orange-500 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:-translate-y-0.5 hover:bg-orange-400 disabled:translate-y-0 disabled:opacity-60"
            on:click={uploadVideo}
            disabled={!selectedFile || uploading}
          >
            {uploading ? 'Uploading...' : 'Upload video'}
          </button>
        </div>
      </div>
    </div>

    <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-slate-900">Processing queue</h2>
        <span class="text-xs text-slate-500">{jobs.length} jobs</span>
      </div>
      <p class="mt-1 text-xs text-slate-500">
        Uploads process in the background. You can safely leave this page.
      </p>
      {#if jobError}
        <div class="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
          {jobError}
        </div>
      {/if}
      <div class="mt-4 space-y-3">
        {#if loadingJobs}
          <div class="text-xs text-slate-500">Loading jobs...</div>
        {:else if recentJobs.length === 0}
          <div class="text-xs text-slate-500">No processing jobs yet.</div>
        {:else}
          {#each recentJobs as job}
            <div class="rounded-2xl border border-slate-200 px-4 py-3 text-xs text-slate-600">
              <div class="flex items-center justify-between">
                <span class="font-semibold text-slate-900">
                  {job.job_type === 'transcode' ? 'Transcoding' : 'Transcription'}
                </span>
                <span class="uppercase tracking-widest text-[10px] text-slate-500">
                  {job.status}
                </span>
              </div>
              <div class="mt-1 text-[11px] text-slate-500">
                {new Date(job.created_at).toLocaleString()}
              </div>
              {#if job.detail}
                <div class="mt-1 text-[11px] text-slate-400">{job.detail}</div>
              {/if}
            </div>
          {/each}
        {/if}
      </div>
    </div>

    <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-slate-900">Video library</h2>
        <a class="text-xs text-orange-600 hover:underline" href="/library">Open library →</a>
      </div>
      <p class="mt-3 text-xs text-slate-500">
        Browse, sort, and rename uploads in the dedicated library view.
      </p>
    </div>

    <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-slate-900">Interface</h2>
      </div>
      <p class="mt-2 text-xs text-slate-500">
        Adjust navigation behavior on all pages.
      </p>
      <label class="mt-4 flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
        Pin the top navigation bar
        <input
          type="checkbox"
          class="h-4 w-4 accent-orange-500"
          checked={navPinnedValue}
          on:change={handleNavPinnedChange}
        />
      </label>
      <p class="mt-2 text-[11px] text-slate-400">
        When disabled, hover at the top of the page to reveal the navigation.
      </p>
    </div>
  {/if}
</section>
