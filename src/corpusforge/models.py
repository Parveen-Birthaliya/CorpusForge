from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Document:
    """
    A single document loaded from disk.
    """

    doc_id:      str
    text:        str
    source_path: Path
    format_type: str
    char_count:  int  = 0
    metadata:    dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Auto-set char_count if not provided."""
        if self.char_count == 0 and self.text:
            self.char_count = len(self.text)