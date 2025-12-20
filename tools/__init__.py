"""Tools package."""
from .filesystem_tools import (
    list_folder,
    search_notes,
    read_note,
    grep_content,
)
from .markdown_tools import (
    get_document_structure,
    read_section,
    get_headers_with_preview,
    search_in_headers,
)

def get_all_tools() -> list:
    """Return list of all available tools."""
    return [
        # Filesystem tools
        list_folder,
        search_notes,
        read_note,
        grep_content,
        # Markdown structure tools
        get_document_structure,
        read_section,
        get_headers_with_preview,
        search_in_headers,
    ]

__all__ = [
    "list_folder",
    "search_notes",
    "read_note",
    "grep_content",
    "get_document_structure",
    "read_section",
    "get_headers_with_preview",
    "search_in_headers",
    "get_all_tools"
]
