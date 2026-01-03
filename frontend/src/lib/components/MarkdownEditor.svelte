<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  import { renderMarkdown } from '$lib/utils/markdown';
  import { parseTimestamp } from '$lib/utils/timestamps';

  export let value = '';
  export let placeholder = 'Write your notes...';

  const dispatch = createEventDispatcher<{ timestamp: number }>();

  $: previewHtml = renderMarkdown(value);

  function handlePreviewClick(event: MouseEvent) {
    const target = event.target as HTMLElement | null;
    if (!target) {
      return;
    }

    const timestamp = target.getAttribute('data-timestamp');
    if (!timestamp) {
      return;
    }

    const seconds = parseTimestamp(timestamp);
    if (seconds === null) {
      return;
    }

    dispatch('timestamp', seconds);
  }
</script>

<div class="grid gap-4 lg:grid-cols-2">
  <label class="block text-sm text-slate-600">
    Notes (Markdown)
    <textarea
      class="mt-2 min-h-[360px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
      bind:value
      placeholder={placeholder}
    ></textarea>
  </label>

  <div class="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm">
    <div class="mb-2 text-xs uppercase tracking-[0.3em] text-slate-400">Preview</div>
    <div class="ibis-markdown" on:click={handlePreviewClick}>
      {@html previewHtml}
    </div>
  </div>
</div>
