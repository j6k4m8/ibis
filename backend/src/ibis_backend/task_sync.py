"""Task parsing and synchronization helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from sqlalchemy.orm import Session

from ibis_backend.models import Note, Task, utcnow

TASK_LINE_REGEX = re.compile(
    r"^(?P<indent>\s*)(?P<bullet>[-*+])\s*\[(?P<checked>[ xX])\](?P<space>\s*)(?P<text>.*)$"
)


@dataclass(frozen=True)
class ParsedTask:
    """Parsed task line details."""

    text: str
    completed: bool
    line_index: int
    raw_line: str
    key: str


def normalize_task_text(text: str) -> str:
    """Normalize task text to a stable key.

    Args:
        text: Raw task text.

    Returns:
        str: Normalized task key.
    """

    return " ".join(text.strip().split())


def parse_task_lines(body: str) -> list[ParsedTask]:
    """Parse task lines from markdown.

    Args:
        body: Markdown text.

    Returns:
        list[ParsedTask]: Parsed task lines.
    """

    tasks: list[ParsedTask] = []
    lines = body.splitlines()
    for index, line in enumerate(lines):
        match = TASK_LINE_REGEX.match(line)
        if not match:
            continue
        text = match.group("text")
        tasks.append(
            ParsedTask(
                text=text,
                completed=match.group("checked").lower() == "x",
                line_index=index,
                raw_line=line,
                key=normalize_task_text(text),
            )
        )
    return tasks


def update_task_line(line: str, completed: bool) -> str:
    """Update a markdown task line with a new completion state.

    Args:
        line: Raw markdown line.
        completed: Desired completion state.

    Returns:
        str: Updated markdown line.
    """

    match = TASK_LINE_REGEX.match(line)
    if not match:
        return line
    indent = match.group("indent")
    bullet = match.group("bullet")
    space = match.group("space") or " "
    text = match.group("text")
    check = "x" if completed else " "
    return f"{indent}{bullet} [{check}]{space}{text}"


def sync_tasks_for_note(note: Note, db: Session) -> None:
    """Sync task rows for a note based on its markdown body.

    Args:
        note: Note ORM instance.
        db: Database session.
    """

    parsed = parse_task_lines(note.body or "")
    existing = (
        db.query(Task)
        .filter(Task.note_id == note.id)
        .order_by(Task.created_at.asc())
        .all()
    )

    existing_by_key: dict[str, list[Task]] = defaultdict(list)
    for task in existing:
        existing_by_key[normalize_task_text(task.text)].append(task)

    now = utcnow()
    occurrence_counts: dict[str, int] = defaultdict(int)

    for parsed_task in parsed:
        key = parsed_task.key
        occurrence = occurrence_counts[key]
        occurrence_counts[key] += 1

        if existing_by_key[key]:
            task = existing_by_key[key].pop(0)
            task.text = parsed_task.text
            task.completed = parsed_task.completed
            task.occurrence = occurrence
            task.updated_at = now
        else:
            task = Task(
                note_id=note.id,
                text=parsed_task.text,
                completed=parsed_task.completed,
                occurrence=occurrence,
                created_at=now,
                updated_at=now,
            )
            db.add(task)

    for tasks in existing_by_key.values():
        for task in tasks:
            db.delete(task)


def apply_task_completion(note: Note, task: Task, completed: bool) -> bool:
    """Apply a completion toggle to the matching task line in a note.

    Args:
        note: Note ORM instance.
        task: Task row to update.
        completed: Desired completion state.

    Returns:
        bool: True if a line was updated.
    """

    lines = note.body.splitlines()
    parsed = parse_task_lines(note.body or "")
    occurrence_counts: dict[str, int] = defaultdict(int)
    target_key = normalize_task_text(task.text)

    for parsed_task in parsed:
        key = parsed_task.key
        occurrence = occurrence_counts[key]
        occurrence_counts[key] += 1
        if key == target_key and occurrence == task.occurrence:
            lines[parsed_task.line_index] = update_task_line(parsed_task.raw_line, completed)
            note.body = "\n".join(lines)
            return True

    return False
