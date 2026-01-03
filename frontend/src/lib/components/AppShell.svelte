<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
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

  $: currentPath = $page.url.pathname;
  $: isNotesDetail = currentPath.startsWith('/notes/') && currentPath !== '/notes';
  $: isTasks = currentPath.startsWith('/tasks');
  $: isMe = currentPath.startsWith('/me');
  $: isLibrary = currentPath.startsWith('/library');
  $: mainClass = isNotesDetail ? 'mt-8 w-full' : 'mx-auto mt-8 w-full max-w-5xl';
  $: navClass =
    'flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white/80 px-6 py-4 shadow-lg shadow-orange-100 backdrop-blur';
</script>

<div class="min-h-screen px-4 py-6 sm:px-8">
  {#if showNav}
    <nav class={navClass}>
      <a href="/" class="flex items-center gap-3 text-lg font-semibold text-slate-900">
        <span class="grid h-9 w-9 place-items-center rounded-full bg-orange-200 text-xl">𓅜</span>
        Ibis
      </a>
      <div class="flex items-center gap-4 text-sm">
        <a
          href="/tasks"
          class={`rounded-full px-4 py-2 transition ${isTasks ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'}`}
        >
          Tasks
        </a>
        <a
          href="/library"
          class={`rounded-full px-4 py-2 transition ${isLibrary ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'}`}
        >
          Library
        </a>
        {#if authState?.user}
          <a
            href="/me"
            class={`hidden rounded-full px-4 py-2 text-sm transition sm:flex ${
              isMe ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
            }`}
          >
            {authState.user.display_name ?? authState.user.email}
          </a>
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

  <main class={mainClass}>
    <slot />
  </main>
</div>
