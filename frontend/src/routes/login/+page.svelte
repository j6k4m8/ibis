<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import { authStore } from '$lib/stores/auth';

  let email = '';
  let password = '';
  let error = '';
  let loading = false;

  onMount(async () => {
    const state = await authStore.init();
    if (state.token) {
      goto('/notes');
    }
  });

  async function submit() {
    error = '';
    loading = true;
    try {
      await authStore.login(email, password);
      goto('/notes');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Login failed.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Log in · Ibis</title>
</svelte:head>

<section class="relative mx-auto max-w-3xl overflow-hidden rounded-[32px] border border-slate-200 bg-white/80 p-8 shadow-2xl">
  <div class="pointer-events-none absolute -right-10 -top-16 h-48 w-48 rounded-full bg-orange-200/70 blur-3xl"></div>
  <div class="pointer-events-none absolute -bottom-12 left-6 h-40 w-40 rounded-full bg-amber-100/80 blur-3xl"></div>

  <div class="grid gap-8 md:grid-cols-[0.9fr_1.1fr]">
    <div class="space-y-4">
      <span class="inline-flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50 px-3 py-1 text-xs uppercase tracking-[0.3em] text-orange-700">
        Welcome back
      </span>
      <h1 class="text-3xl sm:text-4xl">Pick up where you left off.</h1>
      <p class="text-sm text-slate-600">
        Sign in to sync lesson notes, jump through timelines, and keep history intact.
      </p>
      <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-4 text-xs text-slate-500">
        Tip: Use the same account for teachers + students to share sessions later.
      </div>
    </div>

    <form class="space-y-4" on:submit|preventDefault={submit}>
      <label class="block text-sm text-slate-600">
        Email
        <input
          class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-orange-100"
          type="email"
          bind:value={email}
          placeholder="you@example.com"
          required
        />
      </label>
      <label class="block text-sm text-slate-600">
        Password
        <input
          class="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-orange-100"
          type="password"
          bind:value={password}
          placeholder="••••••••"
          minlength="8"
          required
        />
      </label>

      {#if error}
        <div class="rounded-2xl border border-red-200 bg-red-50/80 px-4 py-3 text-xs text-red-600">
          {error}
        </div>
      {/if}

      <button
        type="submit"
        class="w-full rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-slate-700 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-900/20 transition hover:-translate-y-0.5 hover:shadow-xl disabled:translate-y-0 disabled:opacity-60"
        disabled={loading}
      >
        {loading ? 'Signing in...' : 'Log in'}
      </button>
    </form>
  </div>

  <p class="mt-6 text-center text-xs text-slate-500">
    Need an account?
    <a href="/register" class="text-orange-600 hover:underline">Create one</a>.
  </p>
</section>
