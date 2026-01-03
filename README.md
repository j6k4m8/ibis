# Ibis

Music lesson management and annotation app, with support for realtime collaboration with your music teacher.

## Features

- Notes list + detail editing with history snapshot preview.
- Video link preview with YouTube embed support.
- Local video uploads with a reusable library and storage usage meter.
- Video library page with filters and per-video detail view to spawn new notes.
- Markdown editor with preview and timestamp tokens.
- Tags page with deep-linked filters.
- Tasks page that aggregates checklist items from notes.
- Persistent tasks with creation timestamps and completion toggles.
- Video playback ranges with looping start/end controls.
- Segment loops from inline `|start - end|` notation with a clickable list.

## Screenshots 

### Lesson page

<img width="1504" height="870" alt="image" src="https://github.com/user-attachments/assets/5d875734-0ead-4122-ae7d-848756cf94d8" />

### Notes

Use `==00:23==` to tag timestamps; clicking timestamps scans the video to that moment. 

<img width="514" height="477" alt="image" src="https://github.com/user-attachments/assets/ec6eb247-2306-4b45-9713-9c50a8d51f19" />


You can also use `|:1:23 - 2:34:|` to create a "repeat" segment:

<img width="984" height="625" alt="image" src="https://github.com/user-attachments/assets/52427324-753d-4f4f-8827-360c33105c47" />

Clicking this segment opens a "loop" which will replay until you hit the "Stop Loop". This can help you practice segments without having to keep reaching for the mouse.

### Tasks

Tasks, marked with the `- [ ] do this` syntax, are centralized on a tasks page:

<img width="1500" height="602" alt="image" src="https://github.com/user-attachments/assets/63c8cae5-9ef7-45f4-b16a-751292187910" />

### Library Page

#### Tags

<img width="1160" height="679" alt="image" src="https://github.com/user-attachments/assets/33e01d31-3f1e-4d0c-992d-167b6ba899f3" />

#### Notes

<img width="1164" height="685" alt="image" src="https://github.com/user-attachments/assets/6315c717-f663-4a14-896f-1913a699e943" />



## Dev servers

All-in-one:

```bash
./scripts/dev.sh
```

The script loads a root `.env` file if present and exports variables for both services.

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

