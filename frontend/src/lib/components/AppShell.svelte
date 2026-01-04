<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { page } from '$app/stores';

  import { authStore } from '$lib/stores/auth';
  import { initPreferences, navPinned } from '$lib/stores/preferences';

  export let showNav = true;

  let authState;
  const unsubscribe = authStore.subscribe((state) => {
    authState = state;
  });

  let isPinned = false;
  let navHover = false;
  let triggerHover = false;

  const unsubscribePrefs = navPinned.subscribe((value) => {
    isPinned = value;
  });

  onMount(() => {
    authStore.init();
    initPreferences();
  });

  onDestroy(() => {
    unsubscribe();
    unsubscribePrefs();
  });

  $: currentPath = $page.url.pathname;
  $: isNotesDetail = currentPath.startsWith('/notes/') && currentPath !== '/notes';
  $: isLessonsDetail = currentPath.startsWith('/lessons/');
  $: isTasks = currentPath.startsWith('/tasks');
  $: isMe = currentPath.startsWith('/me');
  $: isLibrary = currentPath.startsWith('/library');
  $: navVisible = isPinned || navHover || triggerHover;
  $: mainClass =
    isNotesDetail || isLessonsDetail ? 'w-full pt-14' : 'mx-auto w-full max-w-5xl pt-14';
  $: navClass =
    'flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white/80 px-6 py-4 shadow-lg shadow-orange-100 backdrop-blur';
</script>

<div class="min-h-screen px-4 pb-6 sm:px-8">
  {#if showNav}
    <div class="fixed left-0 right-0 top-0 z-50">
      <div
        class="h-3 w-full"
        on:mouseenter={() => (triggerHover = true)}
        on:mouseleave={() => (triggerHover = false)}
      ></div>
      <div
        class={`w-full px-4 transition duration-300 sm:px-8 ${
          navVisible
            ? 'translate-y-0 opacity-100 pointer-events-auto'
            : '-translate-y-full opacity-0 pointer-events-none'
        }`}
        on:mouseenter={() => (navHover = true)}
        on:mouseleave={() => (navHover = false)}
        on:focusin={() => (navHover = true)}
        on:focusout={() => (navHover = false)}
      >
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
              href="/lessons"
              class={`rounded-full px-4 py-2 transition ${currentPath.startsWith('/lessons') ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'}`}
            >
              Lessons
            </a>
            <a
              href="/library/lessons"
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
      </div>
    </div>
  {/if}

  <main class={mainClass}>
    <slot />
  </main>
</div>
