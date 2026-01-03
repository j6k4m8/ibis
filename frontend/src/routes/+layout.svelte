<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';

  import AppShell from '$lib/components/AppShell.svelte';

  $: showNav = !['/login', '/register'].includes($page.url.pathname);
</script>

<AppShell {showNav}>
  <slot />
</AppShell>
