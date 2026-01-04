<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import { initPreferences, navPinned, setNavPinned } from '$lib/stores/preferences';
  import type { Me } from '$lib/types';

  let token: string | null = null;
  let profile: Me | null = null;
  let loading = true;
  let error = '';
  let navPinnedValue = false;
  let lessonThreshold = 4;
  let updatingSettings = false;

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
    return () => {
      unsubscribe();
      unsubscribePrefs();
    };
  });

  async function loadProfile(activeToken: string) {
    loading = true;
    error = '';
    try {
      profile = await api.getMe(activeToken);
      lessonThreshold = profile.user.lesson_autogroup_hours ?? 4;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load account details.';
    } finally {
      loading = false;
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

  async function updateLessonThreshold(event: Event) {
    const target = event.currentTarget as HTMLInputElement | null;
    if (!target || !token) {
      return;
    }
    const value = Number.parseInt(target.value, 10);
    if (Number.isNaN(value)) {
      return;
    }
    updatingSettings = true;
    error = '';
    try {
      profile = await api.updateMe(token, { lesson_autogroup_hours: value });
      lessonThreshold = profile.user.lesson_autogroup_hours ?? value;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update settings.';
    } finally {
      updatingSettings = false;
    }
  }

  $: storageUsed = profile?.storage_used_bytes ?? 0;
  $: storageLimit = profile?.storage_limit_bytes ?? 1;
  $: usagePercent = Math.min(100, (storageUsed / storageLimit) * 100);
</script>

<svelte:head>
  <title>Account · Ibis</title>
</svelte:head>

<section class="space-y-8">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl">Your account</h1>
      <p class="text-sm text-slate-500">Manage storage and interface settings.</p>
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
          Uploads contribute to your 5GB free tier. YouTube links do not count against storage.
        </p>
      </div>
    </div>

    <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-slate-900">Video library</h2>
        <a class="text-xs text-orange-600 hover:underline" href="/library/lessons">Open library →</a>
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

    <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-slate-900">Lesson grouping</h2>
      </div>
      <p class="mt-2 text-xs text-slate-500">
        Group uploaded videos into lessons when they are created within this window.
      </p>
      <label class="mt-4 flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
        Auto-group window (hours)
        <input
          type="number"
          min="0"
          max="72"
          step="1"
          class="ml-4 w-20 rounded-xl border border-slate-200 px-2 py-1 text-sm text-slate-700 focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
          value={lessonThreshold}
          on:change={updateLessonThreshold}
          disabled={updatingSettings}
        />
      </label>
    </div>
  {/if}
</section>
