<script lang="ts">
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';

  import type { Editor } from '@milkdown/core';

  import { timestamp } from '$lib/milkdown/timestamp';
  import { parseTimestamp } from '$lib/utils/timestamps';

  export let value = '';

  const dispatch = createEventDispatcher<{ timestamp: number; value: string }>();

  let editorRoot: HTMLDivElement | null = null;
  let editor: Editor | null = null;

  onMount(() => {
    if (!editorRoot) {
      return;
    }

    const setup = async () => {
      const { Editor, defaultValueCtx, rootCtx } = await import('@milkdown/core');
      const { listener, listenerCtx } = await import('@milkdown/plugin-listener');
      const { commonmark } = await import('@milkdown/preset-commonmark');
      const { gfm } = await import('@milkdown/preset-gfm');

      editor = Editor.make()
        .config((ctx) => {
          ctx.set(rootCtx, editorRoot as HTMLElement);
          ctx.set(defaultValueCtx, value);

          ctx.get(listenerCtx).markdownUpdated((_ctx, markdown) => {
            value = markdown;
            dispatch('value', markdown);
          });
        })
        .use(commonmark)
        .use(gfm)
        .use(listener)
        .use(timestamp);

      try {
        await editor.create();
      } catch (err) {
        console.error('Failed to initialize editor.', err);
      }
    };

    setup();
  });

  onDestroy(() => {
    editor?.destroy();
  });

  function handleClick(event: MouseEvent) {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    const button = target.closest<HTMLButtonElement>('button[data-timestamp]');
    if (!button) {
      return;
    }

    const timestamp = button.dataset.timestamp;
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

<div class="space-y-3">
  <div class="flex items-center justify-between text-sm text-slate-600">
    <span>Notes</span>
    <span class="text-xs text-slate-400">Use ==1:23== for timestamps</span>
  </div>
  <div class="ibis-editor" bind:this={editorRoot} on:click={handleClick}></div>
</div>
