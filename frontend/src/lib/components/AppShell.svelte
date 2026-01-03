<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  import { authStore } from '$lib/stores/auth';

  export let showNav = true;

  let authState;
  const unsubscribe = authStore.subscribe((state) => {
    authState = state;
  });

  onDestroy(() => unsubscribe());

  onMount(() => {
    authStore.init();
  });

  function logout() {
    authStore.clear();
    goto('/login');
  }

  $: currentPath = $page.url.pathname;
  $: isNotes = currentPath.startsWith('/notes');
  $: isTasks = currentPath.startsWith('/tasks');
  $: isTags = currentPath.startsWith('/tags');
</script>

<div class="min-h-screen px-4 py-6 sm:px-8">
  {#if showNav}
    <nav class="mx-auto flex w-full max-w-5xl items-center justify-between rounded-2xl border border-slate-200 bg-white/80 px-6 py-4 shadow-lg shadow-orange-100 backdrop-blur">
      <a href="/" class="flex items-center gap-3 text-lg font-semibold text-slate-900">
        <span class="grid h-9 w-9 place-items-center rounded-full bg-orange-200 text-xl">𓅜</span>
        Ibis
      </a>
      <div class="flex items-center gap-4 text-sm">
        <a
          href="/notes"
          class={`rounded-full px-4 py-2 transition ${isNotes ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'}`}
        >
          Notes
        </a>
        <a
          href="/tasks"
          class={`rounded-full px-4 py-2 transition ${isTasks ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'}`}
        >
          Tasks
        </a>
        <a
          href="/tags"
          class={`rounded-full px-4 py-2 transition ${isTags ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'}`}
        >
          Tags
        </a>
        {#if authState?.user}
          <div class="hidden items-center gap-3 text-slate-600 sm:flex">
            <span>{authState.user.display_name ?? authState.user.email}</span>
            <button
              type="button"
              on:click={logout}
              class="rounded-full border border-slate-200 px-4 py-2 text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        {:else}
          <div class="flex items-center gap-2">
            <a
              href="/login"
              class="rounded-full border border-slate-200 px-4 py-2 text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              Log in
            </a>
            <a href="/register" class="rounded-full bg-orange-500 px-4 py-2 text-white hover:bg-orange-400">
              Sign up
            </a>
          </div>
        {/if}
      </div>
    </nav>
  {/if}

  <main class="mx-auto mt-8 w-full max-w-5xl">
    <slot />
  </main>
</div>
