<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import { authStore } from '$lib/stores/auth';
  import { markWelcomeSeen } from '$lib/utils/welcome';

  onMount(async () => {
    const state = await authStore.init();
    if (!state.token) {
      goto('/login');
      return;
    }
    markWelcomeSeen(state.user?.id);
  });
</script>

<svelte:head>
  <title>Welcome · Ibis</title>
</svelte:head>

<section class="mx-auto max-w-3xl space-y-6 rounded-[36px] border border-slate-200 bg-white/90 p-10 shadow-2xl shadow-orange-100">
  <div class="space-y-3">
    <p class="text-xs uppercase tracking-[0.4em] text-slate-400">Welcome</p>
    <h1 class="text-3xl sm:text-4xl">Start your first session</h1>
    <p class="text-sm text-slate-600">
      Ibis keeps your videos and notes connected, with tasks, timestamps, and history all in one
      place.
    </p>
  </div>

  <div class="grid gap-4 md:grid-cols-3">
    <div class="rounded-3xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-600 shadow-sm">
      <div class="text-xs font-semibold uppercase tracking-widest text-slate-400">1</div>
      <div class="mt-2 font-semibold text-slate-900">Upload a video</div>
      <p class="mt-2 text-xs text-slate-500">
        Drag in a lesson recording or link a YouTube clip. We’ll index it automatically.
      </p>
    </div>
    <div class="rounded-3xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-600 shadow-sm">
      <div class="text-xs font-semibold uppercase tracking-widest text-slate-400">2</div>
      <div class="mt-2 font-semibold text-slate-900">Write your notes</div>
      <p class="mt-2 text-xs text-slate-500">
        Use <code class="rounded bg-slate-100 px-1">==1:23==</code> for timestamps or tasks with
        <code class="rounded bg-slate-100 px-1">- [ ]</code>.
      </p>
    </div>
    <div class="rounded-3xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-600 shadow-sm">
      <div class="text-xs font-semibold uppercase tracking-widest text-slate-400">3</div>
      <div class="mt-2 font-semibold text-slate-900">Stay organized</div>
      <p class="mt-2 text-xs text-slate-500">
        Lessons auto-group nearby uploads into timelines so you can replay sessions fast.
      </p>
    </div>
  </div>

  <div class="flex flex-wrap items-center gap-3">
    <a
      href="/library/videos"
      class="rounded-full bg-orange-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:-translate-y-0.5 hover:bg-orange-400"
    >
      Go to video library
    </a>
    <a href="/notes" class="text-sm text-slate-500 hover:text-orange-600 hover:underline">
      Skip for now
    </a>
  </div>
</section>
