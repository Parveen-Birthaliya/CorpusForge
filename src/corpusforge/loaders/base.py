from abc import ABC, abstractmethod
from pathlib import Path

from src.corpusforge.models import Document


class BaseLoader(ABC):
    """
    Contract: every loader converts a file on disk into a Document.
    """

    @abstractmethod
    def load(self, file_path: Path) -> Document:
        """
        Load a single file and return a Document.
       """
        ...

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """
        Return True if this loader handles the given file's extension.
        """
        ...

    def load_many(self, paths: list[Path]) -> list[Document]:
        """
        Load all compatible files from a list of paths.
        """
        docs = []
        for path in paths:
            if self.can_handle(path):
                docs.append(self.load(path))
        return docs