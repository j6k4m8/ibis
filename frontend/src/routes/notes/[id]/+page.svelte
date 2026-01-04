<script lang="ts">
  import { page } from '$app/stores';

  import NoteDetailView from '$lib/components/NoteDetailView.svelte';

  $: noteId = $page.params.id;
</script>

<NoteDetailView {noteId} />
