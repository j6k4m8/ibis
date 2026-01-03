# TODO

## Roadmap

-   [x] Define database schema and run initial migrations (users, classes, memberships, videos, notes, tags, transcripts, history)
-   [x] Add auth (email/password + JWT)
-   [x] Scope notes to authenticated users
-   [ ] support notating start and end times for a video in the metadata (maybe under tags editor?); if specified, start playing at Start and end at End and auto repeat the video when it ends or gets to endpt; hide youtube video suggestions; don't auto-play
-   [ ] recognize ==|:mm:ss - mm:ss:|== timestamp ranges, support segment-based repeats. do just |:mm:ss - mm:ss:| (i.e., no ==) ideally, if you can figure out how to do that in the editor without requiring ==-wrap
-   [ ] on video page, show the title (editable) large above video instead of "Lesson Video". show small video link underneath the video. remove title editor from right pane (where tags are also listed), just do tags there.
-   [ ] "history" should use date as header, not title. and show just the last 3 snapshots, with a "view all" link to see the full history page for that note at /notes/{id}/history
-   [ ] Build FastAPI core (notes CRUD, note history, videos, tags, search)
-   [ ] Add realtime collaboration (Yjs over WebSocket, storage of updates, presence)
-   [ ] Implement upload pipeline (local filesystem + S3) with background processing
-   [ ] Add transcription pipeline (Whisper worker, searchable transcript index, auto-tags) for yt and uploaded videos
-   [ ] Build video segmenter (timeline UI, save segments, FFmpeg clip worker)
-   [x] Build auth UI (login/register) and notes list/detail screens
-   [ ] Build SvelteKit UI (editor, video viewer controls, tags, history)
-   [x] Add tasks view and search filter in notes UI
-   [x] Persist tasks with creation timestamps + toggle from editor/tasks page
-   [x] Add tags navigation page and tag deep-links
-   [x] Add markdown editor preview with timestamp tokens
-   [ ] Add tests coverage for API, workers, and frontend
-   [ ] Add deployment configs for Fly.io and k8s (containers, env, migrations)

## Bugs

## Feature Backlog
