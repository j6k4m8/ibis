<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import { authStore } from '$lib/stores/auth';

  let email = '';
  let password = '';
  let displayName = '';
  let error = '';
  let loading = false;

  onMount(async () => {
    const state = await authStore.init();
    if (state.token) {
      goto('/welcome');
    }
  });

  async function submit() {
    error = '';
    loading = true;
    try {
      await authStore.register(email, password, displayName || undefined);
      goto('/welcome');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Registration failed.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Register · Ibis</title>
</svelte:head>

<section class="mx-auto max-w-xl rounded-[32px] border border-slate-200 bg-white/90 p-8 shadow-2xl shadow-orange-100">
  <div class="space-y-3">
    <p class="text-xs uppercase tracking-[0.4em] text-slate-400">New here</p>
    <h1 class="text-3xl sm:text-4xl">Create your Ibis account</h1>
    <p class="text-sm text-slate-600">
      Start capturing notes with your students and build a searchable history.
    </p>
  </div>

  <form class="mt-8 space-y-5" on:submit|preventDefault={submit}>
    <label class="block text-sm text-slate-600">
      Display name
      <input
        class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
        type="text"
        bind:value={displayName}
        placeholder="Your name"
      />
    </label>
    <label class="block text-sm text-slate-600">
      Email
      <input
        class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
        type="email"
        bind:value={email}
        placeholder="you@example.com"
        required
      />
    </label>
    <label class="block text-sm text-slate-600">
      Password
      <input
        class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
        type="password"
        bind:value={password}
        placeholder="At least 8 characters"
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
      class="w-full rounded-2xl bg-orange-500 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-orange-200 transition hover:-translate-y-0.5 hover:bg-orange-400 disabled:translate-y-0 disabled:opacity-60"
      disabled={loading}
    >
      {loading ? 'Creating account...' : 'Create account'}
    </button>
  </form>

  <p class="mt-6 text-center text-xs text-slate-500">
    Already have an account?
    <a href="/login" class="text-orange-600 hover:underline">Log in</a>.
  </p>
</section>
