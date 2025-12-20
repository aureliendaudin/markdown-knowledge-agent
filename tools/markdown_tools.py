"""Advanced markdown parsing tools."""
import logging
import re
from pathlib import Path
from typing import Literal
from langchain_core.tools import tool
from config import settings

logger = logging.getLogger(__name__)


@tool
def get_document_structure(file_path: str) -> str:
    """
    Extract the outline/structure of a markdown document.
    Shows all headers (H1, H2, H3) with line numbers.
    
    Args:
        file_path: Relative path to markdown file
    
    Returns:
        Document outline with headers and line numbers
    
    Example:
        get_document_structure("School/Notes/AI/Machine Learning.md")
        → Returns:
        # Machine Learning (line 1)
        ## Supervised Learning (line 10)
        ### Linear Regression (line 15)
        ### Decision Trees (line 45)
        ## Unsupervised Learning (line 80)
    """
    logger.info(f"[TOOL] get_document_structure('{file_path}')")
    
    full_path = settings.vault.path / file_path
    
    if not full_path.exists():
        return f"File not found: {file_path}"
    
    try:
        lines = full_path.read_text(encoding='utf-8').split('\n')
        structure = []
        
        for i, line in enumerate(lines, 1):
            # Match H1, H2, H3 headers
            if re.match(r'^#{1,3}\s+.+', line):
                # Extract header level and text
                match = re.match(r'^(#{1,3})\s+(.+)', line)
                if match:
                    hashes, title = match.groups()
                    # Clean title (remove trailing #, links, etc.)
                    title = title.strip().rstrip('#').strip()
                    structure.append(f"{hashes} {title} (line {i})")
        
        if not structure:
            return "No headers found in document"
        
        result = f"Structure of {file_path}:\n" + "\n".join(structure)
        logger.debug(f"  Found {len(structure)} headers")
        return result
        
    except Exception as e:
        logger.error(f"  Error reading file: {e}")
        return f"Error reading file: {e}"


@tool
def read_section(file_path: str, section_title: str, max_lines: int = 50) -> str:
    """
    Read a specific section of a markdown document by header title.
    Returns content from the matching header until the next header of same/higher level.
    
    Args:
        file_path: Relative path to markdown file
        section_title: Title of the section to read (case-insensitive, partial match OK)
        max_lines: Maximum lines to return (default: 50)
    
    Returns:
        Content of the specified section
    
    Example:
        read_section("AI/ML.md", "Linear Regression", 50)
        → Returns content of "Linear Regression" section
    """
    logger.info(f"[TOOL] read_section('{file_path}', '{section_title}', {max_lines})")
    
    full_path = settings.vault.path / file_path
    
    if not full_path.exists():
        return f"File not found: {file_path}"
    
    try:
        lines = full_path.read_text(encoding='utf-8').split('\n')
        section_title_lower = section_title.lower()
        
        # Find the section
        section_start = None
        section_level = None
        
        for i, line in enumerate(lines):
            header_match = re.match(r'^(#{1,6})\s+(.+)', line)
            if header_match:
                hashes, title = header_match.groups()
                title_clean = title.strip().rstrip('#').strip().lower()
                
                # Check if this is the section we're looking for
                if section_title_lower in title_clean or title_clean in section_title_lower:
                    section_start = i
                    section_level = len(hashes)
                    break
        
        if section_start is None:
            return f"Section '{section_title}' not found in {file_path}"
        
        # Extract content until next header of same/higher level
        content_lines = [lines[section_start]]
        
        for i in range(section_start + 1, len(lines)):
            line = lines[i]
            header_match = re.match(r'^(#{1,6})\s+', line)
            
            if header_match:
                # Stop if we hit a header of same or higher level
                if len(header_match.group(1)) <= section_level:
                    break
            
            content_lines.append(line)
            
            # Respect max_lines limit
            if len(content_lines) >= max_lines:
                content_lines.append(f"\n[Section continues... {len(lines) - i - 1} more lines]")
                break
        
        result = '\n'.join(content_lines)
        logger.debug(f"  Extracted {len(content_lines)} lines from section")
        return result
        
    except Exception as e:
        logger.error(f"  Error reading section: {e}")
        return f"Error reading section: {e}"


@tool
def get_headers_with_preview(file_path: str, preview_lines: int = 2) -> str:
    """
    Get all headers with a preview of content below each header.
    Useful for quick overview of document content.
    
    Args:
        file_path: Relative path to markdown file
        preview_lines: Number of lines to show after each header (default: 2)
    
    Returns:
        Headers with content preview
    
    Example:
        get_headers_with_preview("AI/ML.md", 2)
        → Returns:
        # Machine Learning
        Machine learning is a subset of AI...
        It uses statistical techniques...
        
        ## Supervised Learning
        In supervised learning, we have labeled data...
        Common algorithms include...
    """
    logger.info(f"[TOOL] get_headers_with_preview('{file_path}', {preview_lines})")
    
    full_path = settings.vault.path / file_path
    
    if not full_path.exists():
        return f"File not found: {file_path}"
    
    try:
        lines = full_path.read_text(encoding='utf-8').split('\n')
        result_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this is a header (H1-H3 only)
            if re.match(r'^#{1,3}\s+.+', line):
                result_lines.append(line)
                
                # Add preview lines after header
                for j in range(1, preview_lines + 1):
                    if i + j < len(lines):
                        preview_line = lines[i + j].strip()
                        # Skip empty lines
                        if preview_line:
                            result_lines.append(preview_line)
                
                result_lines.append("")  # Empty line for readability
            
            i += 1
        
        if not result_lines:
            return "No headers found in document"
        
        result = f"Overview of {file_path}:\n\n" + "\n".join(result_lines)
        logger.debug(f"  Generated overview with {len(result_lines)} lines")
        return result
        
    except Exception as e:
        logger.error(f"  Error generating overview: {e}")
        return f"Error: {e}"


@tool
def search_in_headers(keyword: str, folder: str = "") -> str:
    """
    Search for keyword in document headers (H1-H3) across the vault.
    Faster than grep_content as it only searches headers.
    
    Args:
        keyword: Search term (case-insensitive)
        folder: Limit search to this folder (empty for entire vault)
    
    Returns:
        List of files and matching headers
    
    Example:
        search_in_headers("regression")
        → Returns:
        School/Notes/AI/ML.md:
          ## Linear Regression (line 15)
          ## Logistic Regression (line 45)
    """
    logger.info(f"[TOOL] search_in_headers('{keyword}', folder='{folder}')")
    
    target = settings.vault.path / folder if folder else settings.vault.path
    keyword_lower = keyword.lower()
    results = {}
    
    for md_file in target.rglob("*.md"):
        try:
            lines = md_file.read_text(encoding='utf-8').split('\n')
            matching_headers = []
            
            for i, line in enumerate(lines, 1):
                if re.match(r'^#{1,3}\s+.+', line):
                    if keyword_lower in line.lower():
                        matching_headers.append(f"  {line} (line {i})")
            
            if matching_headers:
                rel_path = md_file.relative_to(settings.vault.path)
                results[str(rel_path)] = matching_headers
                
        except Exception:
            continue
    
    if not results:
        return f"No headers found matching '{keyword}'"
    
    # Format results
    output = []
    for file_path, headers in list(results.items())[:10]:  # Limit to 10 files
        output.append(f"{file_path}:")
        output.extend(headers)
        output.append("")
    
    logger.debug(f"  Found matches in {len(results)} files")
    return "\n".join(output)
