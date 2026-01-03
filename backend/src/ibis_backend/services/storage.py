"""Storage backends for uploaded videos."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StoredObject:
    """Descriptor for a stored object."""

    key: str
    url: str


class StorageBackend:
    """Abstract storage backend interface."""

    def store(self, *, filename: str, content_type: str) -> StoredObject:
        """Return a signed upload URL or storage destination.

        Args:
            filename: Original filename.
            content_type: MIME type.

        Returns:
            StoredObject: Storage descriptor.
        """

        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str) -> None:
        """Initialize the backend.

        Args:
            base_path: Base directory for uploads.
        """

        self.base_path = base_path

    def store(self, *, filename: str, content_type: str) -> StoredObject:
        """Create a placeholder descriptor for local storage.

        Args:
            filename: Original filename.
            content_type: MIME type.

        Returns:
            StoredObject: Storage descriptor.
        """

        key = f"{self.base_path}/{filename}"
        return StoredObject(key=key, url=key)
