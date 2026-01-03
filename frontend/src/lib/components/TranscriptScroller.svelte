<script lang="ts">
  import { afterUpdate } from 'svelte';
  import type { TranscriptChunk } from '$lib/types';

  export let title = 'Transcript';
  export let helperText = '';
  export let emptyText = 'No transcript yet. Transcription runs in the background.';
  export let chunks: TranscriptChunk[] = [];
  export let activeId: string | null = null;
  export let onSeek: (seconds: number) => void = () => {};
  export let compact = false;
  let container: HTMLDivElement | null = null;
  let lastScrollId: string | null = null;

  function formatTime(seconds: number) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  function handleClick(chunk: TranscriptChunk) {
    onSeek(chunk.start_seconds);
  }

  $: panelClasses = compact ? 'p-3' : 'p-4';
  $: listClasses = compact ? 'max-h-56' : 'max-h-64';

  afterUpdate(() => {
    if (!activeId || !container || activeId === lastScrollId) {
      return;
    }
    const target = container.querySelector(`#transcript-${activeId}`) as HTMLElement | null;
    if (!target) {
      return;
    }
    lastScrollId = activeId;
    const relativeTop = target.offsetTop - container.offsetTop;
    const nextTop = Math.max(0, relativeTop - container.clientHeight / 2);
    container.scrollTo({ top: nextTop, behavior: 'smooth' });
  });
</script>

<div class={`rounded-3xl border border-slate-200 bg-white/90 shadow-sm ${panelClasses}`}>
  <div class="flex items-center justify-between">
    <h2 class={compact ? 'text-sm font-semibold text-slate-900' : 'text-base font-semibold text-slate-900'}>
      {title}
    </h2>
    <span class="text-[11px] text-slate-500">{chunks.length} lines</span>
  </div>
  {#if helperText && !compact}
    <p class="mt-1 text-[11px] text-slate-500">{helperText}</p>
  {/if}
  {#if chunks.length === 0}
    <div class="mt-3 text-xs text-slate-500">{emptyText}</div>
  {:else}
    <div
      class={`mt-2 space-y-1 overflow-y-auto pr-2 text-sm ${listClasses}`}
      bind:this={container}
    >
      {#each chunks as chunk}
        <button
          id={`transcript-${chunk.id}`}
          type="button"
          class={`w-full rounded-xl border px-2 py-1.5 text-left transition ${
            activeId === chunk.id
              ? 'border-orange-200 bg-orange-50 text-slate-900'
              : 'border-transparent hover:border-orange-100 hover:bg-orange-50/40'
          }`}
          on:click={() => handleClick(chunk)}
        >
          <div class="text-[10px] uppercase tracking-wide text-slate-400">
            {formatTime(chunk.start_seconds)} - {formatTime(chunk.end_seconds)}
          </div>
          <div class="mt-0.5 text-xs text-slate-700">{chunk.text}</div>
        </button>
      {/each}
    </div>
  {/if}
</div>
