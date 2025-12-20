from tools.markdown_tools import (
    get_document_structure,
    read_section,
    get_headers_with_preview,
    search_in_headers
)

"""Tests for filesystem tools."""
import pytest
from pathlib import Path
from tools import list_folder, search_notes, read_note, grep_content


def test_list_folder():
    """Test folder listing."""
    result = list_folder.invoke("")
    assert isinstance(result, str)
    assert len(result) > 0


def test_search_notes():
    """Test note search."""
    result = search_notes.invoke("AI")
    assert isinstance(result, str)


def test_read_note_not_found():
    """Test reading non-existent file."""
    result = read_note.invoke("nonexistent.md")
    assert "not found" in result.lower()


def test_grep_content():
    """Test content search."""
    result = grep_content.invoke("test", "")
    assert isinstance(result, str)

# Test 4: Search in headers
result = search_in_headers.invoke("regression")
print(result)
