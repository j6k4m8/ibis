# TODO

## Roadmap
- [ ] Define database schema and run initial migrations (users, classes, memberships, videos, notes, tags, transcripts, history)
- [x] Add auth (email/password + JWT)
- [ ] Build FastAPI core (notes CRUD, note history, videos, tags, search)
- [ ] Add realtime collaboration (Yjs over WebSocket, storage of updates, presence)
- [ ] Implement upload pipeline (local filesystem + S3) with background processing
- [ ] Build video segmenter (timeline UI, save segments, FFmpeg clip worker)
- [ ] Add transcription pipeline (Whisper worker, searchable transcript index, auto-tags)
- [ ] Build SvelteKit UI (notes list, editor, video viewer, tasks, search, tags, history)
- [ ] Add tests coverage for API, workers, and frontend
- [ ] Add deployment configs for Fly.io and k8s (containers, env, migrations)

## Bugs

## Feature Backlog
