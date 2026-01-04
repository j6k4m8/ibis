<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  import * as api from '$lib/api';
  import { authStore } from '$lib/stores/auth';
  import { renderMarkdown } from '$lib/utils/markdownPreview';
  import NoteDetailView from '$lib/components/NoteDetailView.svelte';
  import type { Lesson, Note, Task, Video } from '$lib/types';

  let token: string | null = null;
  let lesson: Lesson | null = null;
  let lessonTitle = '';
  let notes: Note[] = [];
  let videos: Video[] = [];
  let tasks: Task[] = [];
  let allNotes: Note[] = [];
  let allVideos: Video[] = [];
  let loading = true;
  let error = '';
  let tab: 'timeline' | 'tasks' | 'library' = 'timeline';
  let viewMode: 'full' | 'birdseye' = 'birdseye';
  let savingTitle = false;
  let selectedNoteId = '';
  let selectedVideoId = '';
  let creatingNoteForVideo: Record<string, boolean> = {};
  let videoTitleDrafts: Record<string, string> = {};
  let savingVideos: Record<string, boolean> = {};

  const unsubscribe = authStore.subscribe((state) => {
    token = state.token;
  });

  onMount(async () => {
    const state = await authStore.init();
    if (!state.token) {
      goto('/login');
      return;
    }
    await loadLesson(state.token, $page.params.id);
    return () => unsubscribe();
  });

  async function loadLesson(activeToken: string, lessonId: string) {
    loading = true;
    error = '';
    try {
      const [lessonData, lessonNotes, lessonVideos, lessonTasks, notesData, videosData] =
        await Promise.all([
          api.getLesson(activeToken, lessonId),
          api.listLessonNotes(activeToken, lessonId),
          api.listLessonVideos(activeToken, lessonId),
          api.listLessonTasks(activeToken, lessonId),
          api.listNotes(activeToken),
          api.listVideos(activeToken),
        ]);
      lesson = lessonData;
      lessonTitle = lessonData.title ?? '';
      notes = lessonNotes;
      videos = lessonVideos;
      tasks = lessonTasks;
      allNotes = notesData;
      allVideos = videosData;
      videoTitleDrafts = Object.fromEntries(
        lessonVideos.map((video) => [video.id, video.title ?? '']),
      );
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to load lesson.';
    } finally {
      loading = false;
    }
  }

  function formatLessonTitle() {
    if (!lesson) {
      return '';
    }
    if (lesson.title && lesson.title.trim()) {
      return lesson.title;
    }
    return new Date(lesson.created_at).toLocaleString(undefined, {
      dateStyle: 'long',
      timeStyle: 'short',
    });
  }

  function formatVideoCreatedAt(video: Video): string {
    const timestamp = video.original_created_at ?? video.created_at;
    return new Date(timestamp).toLocaleString(undefined, {
      dateStyle: 'long',
      timeStyle: 'short',
    });
  }

  async function saveTitle() {
    if (!token || !lesson) {
      return;
    }
    const trimmed = lessonTitle.trim() || undefined;
    if ((lesson.title ?? undefined) === trimmed) {
      return;
    }
    savingTitle = true;
    error = '';
    try {
      lesson = await api.updateLesson(token, lesson.id, { title: trimmed });
      lessonTitle = lesson.title ?? '';
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update lesson title.';
    } finally {
      savingTitle = false;
    }
  }

  async function removeNote(noteId: string) {
    if (!token || !lesson) {
      return;
    }
    try {
      await api.removeLessonNote(token, lesson.id, noteId);
      notes = notes.filter((note) => note.id !== noteId);
      tasks = tasks.filter((task) => task.note_id !== noteId);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to remove note.';
    }
  }

  async function removeVideo(videoId: string) {
    if (!token || !lesson) {
      return;
    }
    try {
      await api.removeLessonVideo(token, lesson.id, videoId);
      videos = videos.filter((video) => video.id !== videoId);
      videoTitleDrafts = Object.fromEntries(
        Object.entries(videoTitleDrafts).filter(([key]) => key !== videoId),
      );
      notes = notes.filter((note) => note.video_id !== videoId);
      tasks = tasks.filter((task) => task.note_id && noteIdForVideo(videoId, task.note_id));
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to remove video.';
    }
  }

  function noteIdForVideo(videoId: string, noteId: string) {
    return !notes.find((note) => note.id === noteId && note.video_id === videoId);
  }

  function handleVideoTitleInput(videoId: string, event: Event) {
    const target = event.currentTarget as HTMLInputElement | null;
    if (!target) {
      return;
    }
    videoTitleDrafts = { ...videoTitleDrafts, [videoId]: target.value };
  }

  async function saveVideoTitle(video: Video) {
    if (!token) {
      return;
    }
    const trimmed = videoTitleDrafts[video.id]?.trim() || undefined;
    if ((video.title ?? undefined) === trimmed) {
      return;
    }
    savingVideos = { ...savingVideos, [video.id]: true };
    error = '';
    try {
      const updated = await api.updateVideo(token, video.id, { title: trimmed });
      videos = videos.map((item) => (item.id === updated.id ? updated : item));
      allVideos = allVideos.map((item) => (item.id === updated.id ? updated : item));
      videoTitleDrafts = { ...videoTitleDrafts, [updated.id]: updated.title ?? '' };
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update video title.';
    } finally {
      savingVideos = { ...savingVideos, [video.id]: false };
    }
  }

  async function createNoteForVideo(video: Video) {
    if (!token || !lesson) {
      return;
    }
    creatingNoteForVideo = { ...creatingNoteForVideo, [video.id]: true };
    error = '';
    try {
      const title =
        videoTitleDrafts[video.id]?.trim() ||
        video.title?.trim() ||
        formatVideoCreatedAt(video);
      const created = await api.createNote(token, {
        title,
        body: '',
        tags: [],
        video_id: video.id,
        created_at: video.original_created_at ?? video.created_at,
      });
      notes = [...notes, created];
      allNotes = [created, ...allNotes];
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to create note.';
    } finally {
      creatingNoteForVideo = { ...creatingNoteForVideo, [video.id]: false };
    }
  }

  async function addNoteToLesson() {
    if (!token || !lesson || !selectedNoteId) {
      return;
    }
    try {
      await api.addLessonNote(token, lesson.id, selectedNoteId);
      notes = await api.listLessonNotes(token, lesson.id);
      tasks = await api.listLessonTasks(token, lesson.id);
      selectedNoteId = '';
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to add note.';
    }
  }

  async function addVideoToLesson() {
    if (!token || !lesson || !selectedVideoId) {
      return;
    }
    try {
      await api.addLessonVideo(token, lesson.id, selectedVideoId);
      videos = await api.listLessonVideos(token, lesson.id);
      videoTitleDrafts = Object.fromEntries(
        videos.map((video) => [video.id, video.title ?? '']),
      );
      notes = await api.listLessonNotes(token, lesson.id);
      tasks = await api.listLessonTasks(token, lesson.id);
      selectedVideoId = '';
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to add video.';
    }
  }

  async function toggleTask(task: Task) {
    if (!token) {
      return;
    }
    try {
      const updated = await api.updateTask(token, task.id, { completed: !task.completed });
      tasks = tasks.map((item) => (item.id === updated.id ? updated : item));
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unable to update task.';
    }
  }

  function getYouTubeId(url: string | null | undefined): string | null {
    if (!url) {
      return null;
    }
    if (url.includes('youtu.be/')) {
      const id = url.split('youtu.be/')[1];
      return id?.split('?')[0] ?? null;
    }
    const match = url.match(/[?&]v=([^&]+)/);
    return match ? match[1] : null;
  }

  function resolveVideoUrl(video: Video): string | null {
    if (video.source_type === 'local') {
      if (!video.video_url || !token) {
        return null;
      }
      const url = new URL(video.video_url);
      url.searchParams.set('token', token);
      return url.toString();
    }
    return video.video_url ?? null;
  }

  function resolveNoteVideoUrl(note: Note): string | null {
    if (note.video_source_type === 'local') {
      if (!note.video_url || !token) {
        return null;
      }
      const url = new URL(note.video_url);
      url.searchParams.set('token', token);
      return url.toString();
    }
    return note.video_url ?? null;
  }

  function formatDuration(seconds?: number | null) {
    if (!seconds && seconds !== 0) {
      return '—';
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  $: notesSorted = [...notes].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  $: linkedVideoIds = new Set(
    notes.map((note) => note.video_id).filter((videoId): videoId is string => Boolean(videoId)),
  );
  $: unlinkedVideos = videos.filter((video) => !linkedVideoIds.has(video.id));
  $: timelineItems = [
    ...notesSorted.map((note) => ({ type: 'note' as const, note, date: note.created_at })),
    ...unlinkedVideos.map((video) => ({
      type: 'video' as const,
      video,
      date: video.original_created_at ?? video.created_at,
    })),
  ].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  $: availableNotes = allNotes.filter((note) => !notes.find((item) => item.id === note.id));
  $: availableVideos = allVideos.filter((video) => !videos.find((item) => item.id === video.id));
</script>

<svelte:head>
  <title>{lesson ? `${formatLessonTitle()} · Lessons` : 'Lesson · Ibis'}</title>
</svelte:head>

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div class="space-y-2">
      <input
        class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-2 text-xl font-semibold shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-4 focus:ring-orange-100"
        type="text"
        bind:value={lessonTitle}
        placeholder={lesson ? formatLessonTitle() : 'Lesson title'}
        on:blur={saveTitle}
      />
      {#if lesson}
        <div class="text-xs text-slate-500">
          {new Date(lesson.created_at).toLocaleString()}
          {#if savingTitle}
            <span class="ml-2 text-slate-400">Saving...</span>
          {/if}
        </div>
      {/if}
    </div>
    <a
      href="/lessons"
      class="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
    >
      Back to lessons
    </a>
  </div>

  <div class="flex flex-wrap gap-2">
    <button
      type="button"
      class={`rounded-full px-4 py-2 text-xs transition ${
        tab === 'timeline' ? 'bg-slate-900 text-white' : 'border border-slate-200 text-slate-600'
      }`}
      on:click={() => (tab = 'timeline')}
    >
      Timeline
    </button>
    <button
      type="button"
      class={`rounded-full px-4 py-2 text-xs transition ${
        tab === 'tasks' ? 'bg-slate-900 text-white' : 'border border-slate-200 text-slate-600'
      }`}
      on:click={() => (tab = 'tasks')}
    >
      Tasks
    </button>
    <button
      type="button"
      class={`rounded-full px-4 py-2 text-xs transition ${
        tab === 'library' ? 'bg-slate-900 text-white' : 'border border-slate-200 text-slate-600'
      }`}
      on:click={() => (tab = 'library')}
    >
      Lesson library
    </button>
  </div>

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="rounded-2xl border border-slate-200 bg-white/70 px-6 py-8 text-sm text-slate-500">
      Loading lesson...
    </div>
  {:else if lesson}
    {#if tab === 'timeline'}
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="text-sm text-slate-500">{notes.length} notes</div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            class={`rounded-full px-4 py-2 text-xs transition ${
              viewMode === 'full'
                ? 'bg-slate-900 text-white'
                : 'border border-slate-200 text-slate-600'
            }`}
            on:click={() => (viewMode = 'full')}
          >
            Full view
          </button>
          <button
            type="button"
            class={`rounded-full px-4 py-2 text-xs transition ${
              viewMode === 'birdseye'
                ? 'bg-slate-900 text-white'
                : 'border border-slate-200 text-slate-600'
            }`}
            on:click={() => (viewMode = 'birdseye')}
          >
            Birdseye
          </button>
        </div>
      </div>

      {#if timelineItems.length === 0}
        <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          No notes yet for this lesson.
        </div>
      {:else if viewMode === 'full'}
        <div class="space-y-6">
          {#each timelineItems as item}
            {#if item.type === 'note'}
              <NoteDetailView noteId={item.note.id} showHead={false} />
            {:else}
              <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
                <div class="grid gap-6 lg:grid-cols-[1fr_1fr]">
                  <div>
                    <div class="text-xs text-slate-500">
                      {formatVideoCreatedAt(item.video)}
                    </div>
                    <div class="mt-3 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                      {#if getYouTubeId(item.video.video_url)}
                        <iframe
                          class="aspect-video w-full"
                          src={`https://www.youtube.com/embed/${getYouTubeId(item.video.video_url)}`}
                          title={item.video.title ?? 'YouTube video'}
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                          allowfullscreen
                        ></iframe>
                      {:else if resolveVideoUrl(item.video)}
                        <video class="aspect-video w-full" src={resolveVideoUrl(item.video)} controls></video>
                      {:else}
                        <div class="flex h-44 items-center justify-center text-xs text-slate-400">
                          Video unavailable
                        </div>
                      {/if}
                    </div>
                  </div>
                  <div class="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
                    <div class="space-y-2">
                      <input
                        class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100"
                        type="text"
                        value={videoTitleDrafts[item.video.id] ?? item.video.title ?? ''}
                        placeholder="Video title"
                        on:input={(event) => handleVideoTitleInput(item.video.id, event)}
                        on:blur={() => saveVideoTitle(item.video)}
                      />
                      {#if savingVideos[item.video.id]}
                        <div class="text-[11px] text-slate-400">Saving...</div>
                      {/if}
                      <div class="text-xs text-slate-500">
                        No notes yet for this video.
                      </div>
                    </div>
                    <button
                      type="button"
                      class="mt-4 rounded-full bg-orange-500 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-orange-400 disabled:opacity-60"
                      on:click={() => createNoteForVideo(item.video)}
                      disabled={creatingNoteForVideo[item.video.id]}
                    >
                      {creatingNoteForVideo[item.video.id]
                        ? 'Creating...'
                        : 'Create note for this video'}
                    </button>
                  </div>
                </div>
              </div>
            {/if}
          {/each}
        </div>
      {:else}
        <div class="relative">
          <div class="absolute left-1/2 top-0 h-full w-px bg-slate-200"></div>
          <div class="space-y-6">
            {#each timelineItems as item}
              <div class="grid gap-6 lg:grid-cols-[1fr_1fr]">
                <div class="relative">
                  <div class="absolute right-0 top-6 h-3 w-3 -translate-y-1/2 rounded-full border border-slate-300 bg-white"></div>
                  <div class="rounded-3xl border border-slate-200 bg-white/90 p-4 shadow-sm">
                    {#if item.type === 'note'}
                      {#if item.note.video_url}
                        {#if getYouTubeId(item.note.video_url)}
                          <iframe
                            class="aspect-video w-full"
                            src={`https://www.youtube.com/embed/${getYouTubeId(item.note.video_url)}`}
                            title={item.note.video_title ?? 'YouTube video'}
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowfullscreen
                          ></iframe>
                        {:else if resolveNoteVideoUrl(item.note)}
                          <video class="aspect-video w-full" src={resolveNoteVideoUrl(item.note)} controls></video>
                        {:else}
                          <div class="flex h-40 items-center justify-center text-xs text-slate-400">
                            Video unavailable
                          </div>
                        {/if}
                      {:else}
                        <div class="flex h-40 items-center justify-center text-xs text-slate-400">
                          No video
                        </div>
                      {/if}
                    {:else}
                      {#if getYouTubeId(item.video.video_url)}
                        <iframe
                          class="aspect-video w-full"
                          src={`https://www.youtube.com/embed/${getYouTubeId(item.video.video_url)}`}
                          title={item.video.title ?? 'YouTube video'}
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                          allowfullscreen
                        ></iframe>
                      {:else if resolveVideoUrl(item.video)}
                        <video class="aspect-video w-full" src={resolveVideoUrl(item.video)} controls></video>
                      {:else}
                        <div class="flex h-40 items-center justify-center text-xs text-slate-400">
                          Video unavailable
                        </div>
                      {/if}
                    {/if}
                  </div>
                </div>
                {#if item.type === 'note'}
                  <div class="rounded-3xl border border-slate-200 bg-white/90 p-4 shadow-sm">
                    <div class="flex items-center justify-between text-xs text-slate-500">
                      <span>{new Date(item.note.created_at).toLocaleString()}</span>
                      <button
                        type="button"
                        class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                        on:click={() => removeNote(item.note.id)}
                      >
                        Remove
                      </button>
                    </div>
                    <div class="mt-2 text-base font-semibold text-slate-900">{item.note.title}</div>
                    <div class="mt-3 ibis-markdown text-sm text-slate-700">
                      {@html renderMarkdown(item.note.body)}
                    </div>
                    <a class="mt-3 inline-block text-xs text-orange-600 hover:underline" href={`/notes/${item.note.id}`}>
                      Open note →
                    </a>
                  </div>
                {:else}
                  <div class="rounded-3xl border border-slate-200 bg-white/90 p-4 shadow-sm">
                    <div class="flex items-center justify-between text-xs text-slate-500">
                      <span>{formatVideoCreatedAt(item.video)}</span>
                      <a
                        href={`/library/${item.video.id}`}
                        class="text-[11px] text-slate-400 hover:text-orange-600 hover:underline"
                      >
                        Open video
                      </a>
                    </div>
                    <div class="mt-2 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                      {#if getYouTubeId(item.video.video_url)}
                        <iframe
                          class="aspect-video w-full"
                          src={`https://www.youtube.com/embed/${getYouTubeId(item.video.video_url)}`}
                          title={item.video.title ?? 'YouTube video'}
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                          allowfullscreen
                        ></iframe>
                      {:else if resolveVideoUrl(item.video)}
                        <video class="aspect-video w-full" src={resolveVideoUrl(item.video)} controls></video>
                      {:else}
                        <div class="flex h-32 items-center justify-center text-xs text-slate-400">
                          Video unavailable
                        </div>
                      {/if}
                    </div>
                    <input
                      class="mt-3 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-900 shadow-sm transition focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100"
                      type="text"
                      value={videoTitleDrafts[item.video.id] ?? item.video.title ?? ''}
                      placeholder="Video title"
                      on:input={(event) => handleVideoTitleInput(item.video.id, event)}
                      on:blur={() => saveVideoTitle(item.video)}
                    />
                    {#if savingVideos[item.video.id]}
                      <div class="mt-1 text-[11px] text-slate-400">Saving...</div>
                    {/if}
                    <div class="mt-3 text-xs text-slate-500">
                      This video has no notes yet.
                    </div>
                    <button
                      type="button"
                      class="mt-4 w-full rounded-full bg-orange-500 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-orange-400 disabled:opacity-60"
                      on:click={() => createNoteForVideo(item.video)}
                      disabled={creatingNoteForVideo[item.video.id]}
                    >
                      {creatingNoteForVideo[item.video.id]
                        ? 'Creating...'
                        : 'Create note for this video'}
                    </button>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {:else if tab === 'tasks'}
      <div class="space-y-3">
        {#if tasks.length === 0}
          <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
            No tasks for this lesson yet.
          </div>
        {:else}
          {#each tasks as task}
            <div class="rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 text-xs text-slate-600">
              <div class="flex items-center justify-between">
                <label class="flex items-center gap-2">
                  <input
                    type="checkbox"
                    class="h-4 w-4 accent-orange-500"
                    checked={task.completed}
                    on:change={() => toggleTask(task)}
                  />
                  <span class={task.completed ? 'line-through text-slate-400' : ''}>{task.text}</span>
                </label>
                <a href={`/notes/${task.note_id}`} class="text-[11px] text-orange-600 hover:underline">
                  {task.note_title}
                </a>
              </div>
              <div class="mt-1 text-[11px] text-slate-400">
                {new Date(task.created_at).toLocaleString()}
              </div>
            </div>
          {/each}
        {/if}
      </div>
    {:else}
      <div class="space-y-8">
        <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-900">Notes</h2>
            <div class="flex items-center gap-2">
              <select
                class="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm"
                bind:value={selectedNoteId}
              >
                <option value="">Add a note…</option>
                {#each availableNotes as note}
                  <option value={note.id}>{note.title}</option>
                {/each}
              </select>
              <button
                type="button"
                class="rounded-full border border-slate-200 px-3 py-2 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                on:click={addNoteToLesson}
                disabled={!selectedNoteId}
              >
                Add
              </button>
            </div>
          </div>
          <div class="mt-4 space-y-3">
            {#if notes.length === 0}
              <div class="text-xs text-slate-500">No notes linked yet.</div>
            {:else}
              {#each notesSorted as note}
                <div class="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
                  <a href={`/notes/${note.id}`} class="font-semibold text-slate-900 hover:underline">
                    {note.title}
                  </a>
                  <button
                    type="button"
                    class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                    on:click={() => removeNote(note.id)}
                  >
                    Remove
                  </button>
                </div>
              {/each}
            {/if}
          </div>
        </div>

        <div class="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-xl">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-900">Videos</h2>
            <div class="flex items-center gap-2">
              <select
                class="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm"
                bind:value={selectedVideoId}
              >
                <option value="">Add a video…</option>
                {#each availableVideos as video}
                  <option value={video.id}>{video.title ?? 'Untitled video'}</option>
                {/each}
              </select>
              <button
                type="button"
                class="rounded-full border border-slate-200 px-3 py-2 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                on:click={addVideoToLesson}
                disabled={!selectedVideoId}
              >
                Add
              </button>
            </div>
          </div>
          <div class="mt-4 space-y-3">
            {#if videos.length === 0}
              <div class="text-xs text-slate-500">No videos linked yet.</div>
            {:else}
              {#each videos as video}
                <div class="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
                  <a href={`/library/${video.id}`} class="font-semibold text-slate-900 hover:underline">
                    {video.title ?? 'Untitled video'}
                  </a>
                  <div class="flex items-center gap-2 text-xs text-slate-500">
                    <span>{formatDuration(video.duration_seconds)}</span>
                    <button
                      type="button"
                      class="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                      on:click={() => removeVideo(video.id)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    {/if}
  {/if}
</section>
