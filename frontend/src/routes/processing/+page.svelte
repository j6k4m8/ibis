<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import type { Job, Video } from '$lib/types';

  let token: string | null = null;
  let jobs: Job[] = [];
  let videos: Video[] = [];
  let loading = true;
  let error = '';
  let pollTimer: ReturnType<typeof setInterval> | null = null;

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
    await loadData(state.token);
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
    };
  });

  async function loadData(activeToken: string) {
    loading = true;
    error = '';
    try {
      [jobs, videos] = await Promise.all([
        api.listJobs(activeToken),
        api.listVideos(activeToken),
      ]);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load processing queue.';
    } finally {
      loading = false;
    }
  }

  async function loadJobs(activeToken: string) {
    try {
      jobs = await api.listJobs(activeToken);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load processing queue.';
    }
  }

  function jobLabel(job: Job) {
    if (job.job_type === 'transcode') return 'Transcoding';
    if (job.job_type === 'transcribe') return 'Transcription';
    if (job.job_type === 'thumbnail') return 'Thumbnail';
    if (job.job_type === 'duration') return 'Duration';
    return job.job_type;
  }

  $: videoMap = new Map(videos.map((video) => [video.id, video]));
  $: sortedJobs = [...jobs].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
</script>

<svelte:head>
  <title>Processing queue · Ibis</title>
</svelte:head>

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl">Processing queue</h1>
      <p class="text-sm text-slate-500">Background jobs for uploads.</p>
    </div>
    <a
      href="/library/videos"
      class="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
    >
      Back to videos
    </a>
  </div>

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
      Loading queue...
    </div>
  {:else if sortedJobs.length === 0}
    <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
      No processing jobs yet.
    </div>
  {:else}
    <div class="space-y-3">
          {#each sortedJobs as job}
            <div class="rounded-3xl border border-slate-200 bg-white/90 px-5 py-4 shadow-sm">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div class="text-sm font-semibold text-slate-900">
                    {jobLabel(job)}
                    {#if videoMap.get(job.video_id)}
                      <span class="text-slate-400">·</span>
                      <a
                        href={`/library/${job.video_id}`}
                        class="text-orange-700 hover:underline"
                      >
                        {videoMap.get(job.video_id)?.title ?? 'Untitled video'}
                      </a>
                    {/if}
                  </div>
                  <div class="mt-1 text-xs text-slate-500">
                    {new Date(job.created_at).toLocaleString()}
                  </div>
                  {#if job.detail}
                    <div class="mt-1 text-[11px] text-slate-400">{job.detail}</div>
                  {/if}
                </div>
                <div class="text-[10px] uppercase tracking-widest text-slate-500">
                  {job.status}
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
</section>
