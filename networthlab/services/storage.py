"""JSON-based storage for persisting app data."""

import json
from pathlib import Path
from typing import Any


class Storage:
    """Simple JSON file storage for app data."""

    def __init__(self, storage_dir: str = ".networthlab"):
        """
        Initialize storage with a directory path.

        Args:
            storage_dir: Directory name for storing data files
        """
        self.storage_path = Path.home() / storage_dir
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a storage key."""
        return self.storage_path / f"{key}.json"

    def save(self, key: str, data: Any) -> bool:
        """
        Save data to a JSON file.

        Args:
            key: Storage key (becomes filename)
            data: Data to save (must be JSON-serializable)

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_file_path(key)
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except (OSError, TypeError) as e:
            print(f"Error saving {key}: {e}")
            return False

    def load(self, key: str, default: Any = None) -> Any:
        """
        Load data from a JSON file.

        Args:
            key: Storage key
            default: Default value if key doesn't exist

        Returns:
            Loaded data or default value
        """
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return default

        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error loading {key}: {e}")
            return default

    def delete(self, key: str) -> bool:
        """
        Delete a stored key.

        Args:
            key: Storage key to delete

        Returns:
            True if deleted, False otherwise
        """
        file_path = self._get_file_path(key)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except OSError as e:
                print(f"Error deleting {key}: {e}")
                return False
        return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in storage.

        Args:
            key: Storage key to check

        Returns:
            True if exists, False otherwise
        """
        return self._get_file_path(key).exists()

    def list_keys(self) -> list[str]:
        """
        List all stored keys.

        Returns:
            List of storage keys
        """
        return [f.stem for f in self.storage_path.glob("*.json")]


# Global storage instance
storage = Storage()
