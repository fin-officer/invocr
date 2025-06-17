"""
Document structure models for PDF processing.

This module defines the data models used to represent the hierarchical
structure of PDF documents, including pages, blocks, lines, and words.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict, Any


@dataclass
class BBox:
    """Bounding box coordinates (x0, y0, x1, y1)"""
    x0: float  # left
    y0: float  # top
    x1: float  # right
    y1: float  # bottom
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return asdict(self)
    
    @property
    def width(self) -> float:
        """Calculate width of the bounding box"""
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        """Calculate height of the bounding box"""
        return self.y1 - self.y0
    
    def __str__(self) -> str:
        return f"BBox(x0={self.x0}, y0={self.y0}, x1={self.x1}, y1={self.y1})"


@dataclass
class Word:
    """Represents a single word in a document"""
    text: str
    bbox: BBox
    fontname: str = ""
    size: float = 0.0
    color: Optional[Tuple[float, float, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['bbox'] = self.bbox.to_dict()
        return result


@dataclass
class Line:
    """Represents a line of text in a document"""
    words: List[Word] = field(default_factory=list)
    bbox: Optional[BBox] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'words': [word.to_dict() for word in self.words],
        }
        if self.bbox:
            result['bbox'] = self.bbox.to_dict()
        return result
    
    @property
    def text(self) -> str:
        """Get the full text of the line"""
        return " ".join(word.text for word in self.words)


@dataclass
class Block:
    """Represents a block of text in a document (e.g., paragraph)"""
    lines: List[Line] = field(default_factory=list)
    bbox: Optional[BBox] = None
    type: str = "text"  # text, image, table, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'type': self.type,
            'lines': [line.to_dict() for line in self.lines],
        }
        if self.bbox:
            result['bbox'] = self.bbox.to_dict()
        return result
    
    @property
    def text(self) -> str:
        """Get the full text of the block"""
        return "\n".join(line.text for line in self.lines)


@dataclass
class Page:
    """Represents a single page in a document"""
    blocks: List[Block] = field(default_factory=list)
    bbox: Optional[BBox] = None
    page_number: int = 0
    width: float = 0.0
    height: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'page_number': self.page_number,
            'width': self.width,
            'height': self.height,
            'blocks': [block.to_dict() for block in self.blocks],
        }
        if self.bbox:
            result['bbox'] = self.bbox.to_dict()
        return result


@dataclass
class Document:
    """Represents a complete document with multiple pages"""
    pages: List[Page] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'metadata': self.metadata,
            'pages': [page.to_dict() for page in self.pages],
        }
