"""Tests for filesystem tools."""
import pytest
from pathlib import Path
from tools import list_folder, search_notes, read_note, grep_content


def test_list_folder():
    """Test folder listing."""
    result = list_folder.invoke({"folder": ""})
    assert isinstance(result, str)
    assert len(result) > 0


def test_search_notes():
    """Test note search."""
    result = search_notes.invoke({"keyword": "AI"})
    assert isinstance(result, str)


def test_read_note_not_found():
    """Test reading non-existent file."""
    result = read_note.invoke({"file_path": "nonexistent.md"})
    assert "not found" in result.lower()


def test_grep_content():
    """Test content search."""
    result = grep_content.invoke({"search_term": "test", "folder": ""})
    assert isinstance(result, str)
