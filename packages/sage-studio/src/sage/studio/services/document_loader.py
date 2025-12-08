"""
Document Loader for SAGE Studio Knowledge Manager

This module provides document loading and chunking functionality for the
SAGE Studio Multi-Agent architecture.

Layer: L6 (sage-studio)
Dependencies: sage-libs (rag module)

Design: Thin wrapper around sage.libs.rag components to provide a Studio-specific
interface with additional metadata handling for knowledge sources.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from sage.libs.rag import CharacterSplitter, LoaderFactory

# Reuse DocumentChunk from vector_store to avoid duplication
from sage.studio.services.vector_store import DocumentChunk

if TYPE_CHECKING:
    from sage.studio.services.knowledge_manager import SourceType

logger = logging.getLogger(__name__)

# Re-export DocumentChunk for convenient imports
__all__ = ["DocumentChunk", "DocumentLoader", "load_documents"]


class DocumentLoader:
    """Document loader and chunker for SAGE Studio knowledge sources.

    This class wraps sage.libs.rag components to provide:
    - Unified interface for loading directories and files
    - Smart chunking based on document type (Markdown by headers, Python by AST)
    - Rich metadata extraction

    Example:
        >>> loader = DocumentLoader(chunk_size=1000, chunk_overlap=200)
        >>> for chunk in loader.load_directory(Path("docs/"), ["**/*.md"], SourceType.MARKDOWN):
        ...     print(chunk.content[:100], chunk.metadata)
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """Initialize the document loader.

        Args:
            chunk_size: Target size for each chunk in characters.
            chunk_overlap: Number of overlapping characters between chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._splitter = CharacterSplitter(
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )

    def load_directory(
        self,
        path: Path,
        patterns: list[str],
        source_type: SourceType,
    ) -> Iterator[DocumentChunk]:
        """Load all matching files from a directory.

        Args:
            path: Root directory path.
            patterns: Glob patterns to match files (e.g., ["**/*.md", "**/*.py"]).
            source_type: Type of source for metadata.

        Yields:
            DocumentChunk for each chunk of each file.
        """
        path = Path(path).expanduser().resolve()

        if not path.exists():
            logger.warning(f"Directory does not exist: {path}")
            return

        for pattern in patterns:
            for file_path in path.glob(pattern):
                if file_path.is_file():
                    try:
                        yield from self.load_file(file_path, source_type)
                    except Exception as e:
                        logger.warning(f"Failed to load {file_path}: {e}")
                        continue

    def load_file(self, path: Path, source_type: SourceType) -> list[DocumentChunk]:
        """Load and chunk a single file.

        Args:
            path: Path to the file.
            source_type: Type of source for specialized processing.

        Returns:
            List of DocumentChunks.
        """
        # Import here to avoid circular dependency
        from sage.studio.services.knowledge_manager import SourceType

        path = Path(path).expanduser().resolve()

        # Use specialized loaders for certain types
        if source_type == SourceType.MARKDOWN:
            return self._load_markdown(path)
        elif source_type == SourceType.PYTHON_CODE:
            return self._load_python(path)
        elif source_type == SourceType.PDF:
            return self._load_pdf(path)
        else:
            return self._load_generic(path, source_type)

    def _load_markdown(self, path: Path) -> list[DocumentChunk]:
        """Load and chunk a Markdown file by headers.

        Splits by ## headers to preserve semantic structure.
        """
        try:
            content = self._read_file_with_encoding(path)
        except Exception as e:
            logger.error(f"Failed to read markdown file {path}: {e}")
            return []

        chunks = []
        # Split by ## headers (level 2), keeping the header with content
        sections = re.split(r"\n(?=##\s)", content)

        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            # Extract title from header
            title_match = re.match(r"^##\s+(.+?)(?:\n|$)", section)
            title = title_match.group(1).strip() if title_match else f"Section {i}"

            # If section is too long, split further
            if len(section) > self.chunk_size:
                sub_chunks = self._splitter.split(section)
                for j, sub_chunk in enumerate(sub_chunks):
                    chunks.append(
                        DocumentChunk(
                            content=sub_chunk,
                            source_file=str(path),
                            chunk_index=len(chunks),
                            metadata={
                                "title": title,
                                "type": "markdown",
                                "section_index": i,
                                "sub_chunk_index": j,
                            },
                        )
                    )
            else:
                chunks.append(
                    DocumentChunk(
                        content=section,
                        source_file=str(path),
                        chunk_index=len(chunks),
                        metadata={
                            "title": title,
                            "type": "markdown",
                            "section_index": i,
                        },
                    )
                )

        return chunks

    def _load_python(self, path: Path) -> list[DocumentChunk]:
        """Load and chunk a Python file by AST nodes.

        Extracts classes, functions, and their docstrings as separate chunks.
        """
        try:
            content = self._read_file_with_encoding(path)
        except Exception as e:
            logger.error(f"Failed to read Python file {path}: {e}")
            return []

        chunks = []

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {path}: {e}, falling back to text split")
            return self._load_generic_content(content, str(path), "python_code")

        # Extract module docstring
        module_docstring = ast.get_docstring(tree)
        if module_docstring:
            chunks.append(
                DocumentChunk(
                    content=f"# Module: {path.stem}\n\n{module_docstring}",
                    source_file=str(path),
                    chunk_index=len(chunks),
                    metadata={
                        "type": "python_code",
                        "node_type": "module",
                        "name": path.stem,
                        "language": "python",
                    },
                )
            )

        # Process top-level definitions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                chunks.extend(self._extract_class_chunks(node, content, path))
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                chunk = self._extract_function_chunk(node, content, path, len(chunks))
                if chunk:
                    chunks.append(chunk)

        # If no chunks extracted, fall back to generic split
        if not chunks:
            return self._load_generic_content(content, str(path), "python_code")

        return chunks

    def _extract_class_chunks(
        self, node: ast.ClassDef, source: str, path: Path
    ) -> list[DocumentChunk]:
        """Extract chunks from a class definition."""
        chunks = []
        class_name = node.name

        # Class docstring
        docstring = ast.get_docstring(node)
        if docstring:
            # Get class signature
            lines = source.split("\n")
            class_line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""

            chunks.append(
                DocumentChunk(
                    content=f'{class_line}\n"""{docstring}"""',
                    source_file=str(path),
                    chunk_index=len(chunks),
                    metadata={
                        "type": "python_code",
                        "node_type": "class",
                        "name": class_name,
                        "language": "python",
                        "line_number": node.lineno,
                    },
                )
            )

        # Extract methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                chunk = self._extract_function_chunk(
                    item, source, path, len(chunks), class_name=class_name
                )
                if chunk:
                    chunks.append(chunk)

        return chunks

    def _extract_function_chunk(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
        path: Path,
        chunk_index: int,
        class_name: str | None = None,
    ) -> DocumentChunk | None:
        """Extract a chunk from a function definition."""
        func_name = node.name

        # Skip private methods without docstrings
        docstring = ast.get_docstring(node)
        if func_name.startswith("_") and not docstring:
            return None

        # Get function source
        lines = source.split("\n")
        start_line = node.lineno - 1
        end_line = node.end_lineno if node.end_lineno else start_line + 1
        func_source = "\n".join(lines[start_line:end_line])

        # Truncate if too long (keep signature + docstring)
        if len(func_source) > self.chunk_size:
            # Try to keep at least signature and docstring
            if docstring:
                func_source = f'{lines[start_line]}\n    """{docstring}"""\n    ...'
            else:
                func_source = func_source[: self.chunk_size] + "\n    # ... (truncated)"

        full_name = f"{class_name}.{func_name}" if class_name else func_name

        return DocumentChunk(
            content=func_source,
            source_file=str(path),
            chunk_index=chunk_index,
            metadata={
                "type": "python_code",
                "node_type": "method" if class_name else "function",
                "name": full_name,
                "class_name": class_name,
                "language": "python",
                "line_number": node.lineno,
                "has_docstring": docstring is not None,
            },
        )

    def _load_pdf(self, path: Path) -> list[DocumentChunk]:
        """Load and chunk a PDF file.

        Uses sage.libs.rag.PDFLoader and splits by pages or paragraphs.
        """
        try:
            doc = LoaderFactory.load(str(path))
            content = doc["content"]
            metadata = doc.get("metadata", {})
        except ImportError:
            logger.error("PDF loading requires PyPDF2. Install with: pip install PyPDF2")
            return []
        except Exception as e:
            logger.error(f"Failed to load PDF {path}: {e}")
            return []

        # Split content into chunks
        chunks = []
        text_chunks = self._splitter.split(content)

        for i, chunk_text in enumerate(text_chunks):
            chunks.append(
                DocumentChunk(
                    content=chunk_text,
                    source_file=str(path),
                    chunk_index=i,
                    metadata={
                        "type": "pdf",
                        "total_pages": metadata.get("pages"),
                    },
                )
            )

        return chunks

    def _load_generic(self, path: Path, source_type: SourceType) -> list[DocumentChunk]:
        """Load and chunk a generic file using LoaderFactory."""
        try:
            doc = LoaderFactory.load(str(path))
            content = doc["content"]
            file_type = doc.get("metadata", {}).get("type", source_type.value)
        except ValueError:
            # Unsupported extension, try as text
            try:
                content = self._read_file_with_encoding(path)
                file_type = source_type.value
            except Exception as e:
                logger.error(f"Failed to load {path}: {e}")
                return []
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return []

        return self._load_generic_content(content, str(path), file_type)

    def _load_generic_content(
        self, content: str, source_file: str, file_type: str
    ) -> list[DocumentChunk]:
        """Split generic content into chunks."""
        chunks = []
        text_chunks = self._splitter.split(content)

        for i, chunk_text in enumerate(text_chunks):
            chunks.append(
                DocumentChunk(
                    content=chunk_text,
                    source_file=source_file,
                    chunk_index=i,
                    metadata={"type": file_type},
                )
            )

        return chunks

    def _read_file_with_encoding(self, path: Path) -> str:
        """Read file with automatic encoding detection.

        Tries UTF-8 first, then falls back to other common encodings.
        """
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]

        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        # Last resort: read as binary and decode with errors='replace'
        return path.read_bytes().decode("utf-8", errors="replace")


# Convenience function for simple usage
def load_documents(
    path: str | Path,
    patterns: list[str] | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[DocumentChunk]:
    """Load documents from a path with automatic type detection.

    Args:
        path: File or directory path.
        patterns: Glob patterns (only for directories). Defaults to common doc patterns.
        chunk_size: Target chunk size.
        chunk_overlap: Overlap between chunks.

    Returns:
        List of DocumentChunks.
    """
    from sage.studio.services.knowledge_manager import SourceType

    path = Path(path).expanduser().resolve()
    loader = DocumentLoader(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if path.is_file():
        # Detect type from extension
        ext = path.suffix.lower()
        type_map = {
            ".md": SourceType.MARKDOWN,
            ".markdown": SourceType.MARKDOWN,
            ".py": SourceType.PYTHON_CODE,
            ".pdf": SourceType.PDF,
            ".json": SourceType.JSON,
            ".yaml": SourceType.YAML,
            ".yml": SourceType.YAML,
        }
        source_type = type_map.get(ext, SourceType.USER_UPLOAD)
        return loader.load_file(path, source_type)

    elif path.is_dir():
        if patterns is None:
            patterns = ["**/*.md", "**/*.py", "**/*.txt"]

        # Use MARKDOWN as default, actual type detected per-file
        chunks = []
        for pattern in patterns:
            for file_path in path.glob(pattern):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in {".md", ".markdown"}:
                        source_type = SourceType.MARKDOWN
                    elif ext == ".py":
                        source_type = SourceType.PYTHON_CODE
                    elif ext == ".pdf":
                        source_type = SourceType.PDF
                    else:
                        source_type = SourceType.USER_UPLOAD
                    try:
                        chunks.extend(loader.load_file(file_path, source_type))
                    except Exception as e:
                        logger.warning(f"Failed to load {file_path}: {e}")
        return chunks

    else:
        raise FileNotFoundError(f"Path does not exist: {path}")
