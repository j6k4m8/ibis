<script lang="ts">
  import { onMount } from 'svelte';

  import { authStore } from '$lib/stores/auth';

  let authState;
  const unsubscribe = authStore.subscribe((state) => (authState = state));

  onMount(() => {
    authStore.init();
    return () => unsubscribe();
  });
</script>

<svelte:head>
  <title>Ibis</title>
</svelte:head>

<section class="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
  <div class="space-y-6 rounded-3xl border border-orange-100 bg-white/80 p-8 shadow-xl shadow-orange-100">
    <div class="space-y-3">
      <p class="text-xs uppercase tracking-[0.5em] text-slate-500">Ibis</p>
      <h1 class="text-4xl sm:text-5xl">Notes that live inside the video timeline.</h1>
      <p class="text-base text-slate-600">
        Capture timestamps, collect tasks, and keep a running history of every session. Notes stay
        synced, searchable, and ready for students.
      </p>
    </div>
    <div class="flex flex-wrap gap-3">
      {#if authState?.user}
        <a
          href="/notes"
          class="rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          Jump to notes
        </a>
      {:else}
        <a
          href="/register"
          class="rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          Create account
        </a>
        <a
          href="/login"
          class="rounded-full border border-slate-200 px-5 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
        >
          Log in
        </a>
      {/if}
    </div>
  </div>

  <div class="space-y-4 rounded-3xl border border-slate-200 bg-white/70 p-6 shadow-lg">
    <h2 class="text-xl">What you can do today</h2>
    <ul class="space-y-3 text-sm text-slate-600">
      <li>Track sessions with timestamped notes and a full edit history.</li>
      <li>Attach video links (YouTube/public for now) and jump by timestamp.</li>
      <li>Search and tag moments to keep practice materials organized.</li>
    </ul>
    <div class="rounded-2xl border border-dashed border-orange-200 bg-orange-50 p-4 text-xs text-orange-700">
      Collaboration, uploads, and transcription are queued for the next milestones.
    </div>
  </div>
</section>
