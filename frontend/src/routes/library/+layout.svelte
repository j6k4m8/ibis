<script lang="ts">
  import { page } from '$app/stores';

  const tabs = [
    { label: 'Lessons', href: '/library/lessons' },
    { label: 'Notes', href: '/library/notes' },
    { label: 'Videos', href: '/library/videos' },
    { label: 'Tags', href: '/library/tags' },
  ];

  $: currentPath = $page.url.pathname;
  $: activeHref =
    tabs.find((tab) => tab.href === currentPath)?.href ?? '/library/lessons';
</script>

<section class="space-y-6">
  <div>
    <h1 class="text-2xl">Library</h1>
    <p class="text-sm text-slate-500">Lessons, notes, videos, and tags in one place.</p>
  </div>
  <nav class="inline-flex flex-wrap gap-2 rounded-full border border-slate-200 bg-white/80 p-2 shadow-sm">
    {#each tabs as tab}
      <a
        href={tab.href}
        class={`rounded-full px-4 py-2 text-sm transition ${
          activeHref === tab.href
            ? 'bg-slate-900 text-white'
            : 'text-slate-600 hover:bg-slate-100'
        }`}
      >
        {tab.label}
      </a>
    {/each}
  </nav>
  <slot />
</section>
