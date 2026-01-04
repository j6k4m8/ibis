# Ibis

Music note management and annotation app, with support for realtime collaboration with your teacher.

## Features

- Annotate and tag your videos, with versioned note history
- Supports uploaded videos and YouTube hosted videos
- Markdown editor with preview and timestamp tokens
- Notate tasks and keep track of them all in one place, to help you organize your practicing and learning
- Video playback "crop" ranges
- Repeat loops from `|:start - end:|` notation, with a clickable list
- Go to specific timepoints with `==1:23==` highlighted tags
- Lessons group related notes and videos into timelines with tasks and library tabs

## Screenshots 

|                                                                                                                                                                                                                                              |                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Lesson page                                                                                                                                                                                                                                 | ![](https://github.com/user-attachments/assets/e0a0abc6-c869-4a44-8099-1faa9157de08) |
| Use `==00:23==` to tag timestamps; clicking timestamps scans the video to that moment.                                                                                                                                                      | ![](https://github.com/user-attachments/assets/ec6eb247-2306-4b45-9713-9c50a8d51f19) |
| You can also use `\|:1:23 - 2:34:\|` to create a "repeat" segment. Clicking this segment opens a "loop" which will replay until you hit the "Stop Loop". This can help you practice segments without having to keep reaching for the mouse. | ![](https://github.com/user-attachments/assets/52427324-753d-4f4f-8827-360c33105c47) |
| Tasks, marked with the `- [ ] do this` syntax, are centralized on a tasks page:                                                                                                                                                             | ![](https://github.com/user-attachments/assets/63c8cae5-9ef7-45f4-b16a-751292187910) |
| Tags are centralized on a tags page, with deep-link filtering:                                                                                                                                                                              | ![](https://github.com/user-attachments/assets/33e01d31-3f1e-4d0c-992d-167b6ba899f3) |
| Notes library page with uploaded or linked videos:                                                                                                                                                                                          | ![](https://github.com/user-attachments/assets/6315c717-f663-4a14-896f-1913a699e943) |
| User profile page with storage usage meter                                                                                                                                                                                                  | ![](https://github.com/user-attachments/assets/5f474126-63b5-4a28-86cb-93264f52a518) |



## Roadmap 

Help welcome :) Please reach out or file an Issue to "claim" a task before contributing to avoid duplicating work!

- [ ] video speed manipulation
- [ ] optional [multilingual]-transcription of videos
- [ ] video transcoding to reduce file sizes
- [ ] realtime multiuser notes collaboration
- [ ] k8s packaging
- [ ] (free) public deployment

## Workflow

- Update `TODO.md` as features land.
- Add major features to `## Features` here.
- Add tests/docs when they make sense.
- Commit at meaningful checkpoints with clear messages.

## Dev servers

All-in-one:

```bash
./scripts/dev.sh
```

The script loads a root `.env` file if present and exports variables for both services.

Background worker (media processing):

```bash
./scripts/worker.sh
```

Enable processing with:

```bash
IBIS_PROCESSING_ENABLED=true IBIS_TRANSCODE_ENABLED=true IBIS_TRANSCRIPTION_ENABLED=true
```

Raw uploads are stored under `uploads/raw/{user_id}`. After a successful transcode, the raw file
is deleted unless you set:

```bash
IBIS_KEEP_RAW_UPLOADS=true
```

Upload/storage limits (bytes):

```bash
IBIS_UPLOAD_MAX_BYTES=104857600
IBIS_STORAGE_LIMIT_BYTES=5368709120
```

Backend:

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
uv run uvicorn ibis_backend.app:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Tests

Backend:

```bash
cd backend
uv run pytest
```

Frontend:

```bash
cd frontend
npm run test
```
