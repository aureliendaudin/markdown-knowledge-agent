"""Tests for markdown tools."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from tools.markdown_tools import (
    get_document_structure,
    read_section,
    get_headers_with_preview,
    search_in_headers,
)
from config import settings

@pytest.fixture
def mock_vault_path(tmp_path):
    """Mock the vault path with a temporary directory."""
    original_path = settings.vault.path
    settings.vault.path = tmp_path
    
    # Create a test file
    test_file = tmp_path / "test_notes.md"
    test_file.write_text("""# Main Title
Introduction text.

## Section 1
Content of section 1.
More content.

### Subsection 1.1
Detail 1.

## Section 2
Content of section 2.
""")
    
    yield tmp_path
    settings.vault.path = original_path

def test_get_document_structure(mock_vault_path):
    """Test extracting document structure."""
    result = get_document_structure.invoke("test_notes.md")
    assert "# Main Title" in result
    assert "## Section 1" in result
    assert "### Subsection 1.1" in result
    assert "(line 1)" in result

def test_read_section(mock_vault_path):
    """Test reading a specific section."""
    # Test reading Section 1
    result = read_section.invoke({"file_path": "test_notes.md", "section_title": "Section 1", "max_lines": 10})
    assert "Content of section 1" in result
    assert "## Section 1" in result
    # Should not include Section 2
    assert "## Section 2" not in result

def test_read_section_nested(mock_vault_path):
    """Test reading a nested section."""
    result = read_section.invoke({"file_path": "test_notes.md", "section_title": "Subsection 1.1", "max_lines": 10})
    assert "Detail 1" in result
    assert "### Subsection 1.1" in result

def test_get_headers_with_preview(mock_vault_path):
    """Test extracting headers with preview."""
    result = get_headers_with_preview.invoke({"file_path": "test_notes.md", "preview_lines": 1})
    assert "# Main Title" in result
    assert "Introduction text." in result
    assert "## Section 1" in result
    assert "Content of section 1." in result

def test_search_in_headers(mock_vault_path):
    """Test searching in headers."""
    result = search_in_headers.invoke({"keyword": "Section", "folder": ""})
    assert "test_notes.md" in result
    assert "## Section 1" in result
    assert "## Section 2" in result
