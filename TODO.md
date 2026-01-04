# TODO

## Roadmap

-   [x] Define database schema and run initial migrations (users, classes, memberships, videos, notes, tags, transcripts, history)
-   [x] Add auth (email/password + JWT)
-   [x] Scope notes to authenticated users
-   [x] Build upload pipeline (local filesystem only) with 100MB per-file client-side limit
-   [x] Add video library (videos reusable across notes) with naming at upload or note creation
-   [x] Update note creation flow to choose YouTube link or uploaded video library item
-   [x] Add /me page with logout + storage usage gauge (5GB free, show total uploaded bytes)
-   [x] Add /library video catalog with filters + detail view to play video and create notes
-   [x] support notating start and end times for a video in the metadata (maybe under tags editor?); if specified, start playing at Start and end at End and auto repeat the video when it ends or gets to endpt; hide youtube video suggestions; don't auto-play
-   [x] recognize ==|:mm:ss - mm:ss:|== timestamp ranges, support segment-based repeats. do just |:mm:ss - mm:ss:| (i.e., no ==) ideally, if you can figure out how to do that in the editor without requiring ==-wrap....
    -   [x] if you click one of these, jump to the start time and start playing the video from there to the end time, and then auto loop.
    -   [x] to escape the loop, click a "stop looping" button that appears while looping is active.
    -   [x] add directly underneath the video a list of all the segments and loops defined in the note, as clickable links that jump to that segment and start playing it. include the timestamps and any text on the same line as them for context / name, max 4 words before, 4 words after.
-   [x] on video page, show the title (editable) large above video instead of "Lesson Video". show small video link underneath the video. remove title editor from right pane (where tags are also listed), just do tags there.
-   [x] "history" should use date as header, not title. and show just the last 3 snapshots, with a "view all" link to see the full history page for that note at /notes/{id}/history
-   [x] on the "tasks" page include the date of creation on the task list row.
-   [x] change "create new note" from a card on the notes page to a button in the top right that opens a modal dialog to enter info. then make the notes page more elegant, searchable, filterable, orderable...
-   [x] Build FastAPI core (notes CRUD, note history, videos, tags, search)
-   [x] when you check off a todo item on the tasks page, it should animate a strikethrough effect on the text, and then fade out after like 1 second, rather than just instantly disappearing.
-   [ ] Add realtime collaboration (Yjs over WebSocket, storage of updates, presence)
-   [ ] Implement upload pipeline (local filesystem + S3) with background processing
-   [ ] Add transcription pipeline (Whisper worker, searchable transcript index, auto-tags) for yt and uploaded videos
-   [x] "your notes" /notes page should not be full-width like this. just the actual note/{x} page should be full width.
-   [ ] Build video segmenter (timeline UI, save segments, FFmpeg clip worker)
-   [x] Build auth UI (login/register) and notes list/detail screens
-   [x] Build SvelteKit UI (editor, video viewer controls, tags, history)
-   [x] Add tasks view and search filter in notes UI
-   [x] Persist tasks with creation timestamps + toggle from editor/tasks page
-   [x] Add tags navigation page and tag deep-links
-   [x] Add markdown editor preview with timestamp tokens
-   [x] Add delete action for videos (block if notes are attached)
-   [ ] Add tests coverage for API, workers, and frontend
-   [ ] Add deployment configs for Fly.io and k8s (containers, env, migrations)
-   [ ] Transcription + transcoding pipeline (Whisper + FFmpeg)
    -   [ ] Add background job queue for media processing (local, optional Redis)
    -   [ ] Implement transcoding worker (max 1080p, filesize reduction, configurable)
    -   [ ] Implement transcription worker (Whisper CLI/Docker), store caption chunks with timestamps
    -   [x] Add bulk upload dropzone with queue/progress + auto title
    -   [x] Render captions under video with karaoke-style highlight + click-to-seek
    -   [ ] Add graceful fallbacks when processing services are disabled
    -   [ ] Support running workers via CLI or Docker/K8s

## Bugs

## Feature Backlog

-   Add optional video transcoding to reduce file sizes after upload (auto or manual).
-   Revisit stable task IDs that do not render in the editor.
