<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  onMount(() => {
    goto('/library/tags');
  });
</script>

<svelte:head>
  <title>Library · Ibis</title>
</svelte:head>

<div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
  Redirecting to your library...
</div>
