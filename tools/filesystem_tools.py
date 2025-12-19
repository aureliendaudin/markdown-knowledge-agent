"""Filesystem tools for Obsidian vault navigation."""
import logging
from pathlib import Path
from langchain_core.tools import tool
from config import settings

logger = logging.getLogger(__name__)


@tool
def list_folder(folder: str = "") -> str:
    """List files and subfolders in the vault."""
    logger.info(f"[TOOL] list_folder('{folder}')")
    
    target = settings.vault.path / folder if folder else settings.vault.path
    
    if not target.exists():
        return f"Folder '{folder}' not found"
    
    folders = sorted([
        d.name + "/" 
        for d in target.iterdir() 
        if d.is_dir() and not d.name.startswith('.')
    ])
    
    files = sorted([
        f.name 
        for f in target.iterdir() 
        if f.suffix == '.md'
    ])
    
    items = folders + files
    max_items = settings.tools.filesystem.max_folder_items
    result = "\n".join(items[:max_items]) if items else "Empty folder"
    
    logger.debug(f"  Found: {len(folders)} folders, {len(files)} files")
    return result


@tool
def search_notes(keyword: str) -> str:
    """Search for notes by filename or path."""
    logger.info(f"[TOOL] search_notes('{keyword}')")
    
    keyword_lower = keyword.lower()
    matches = []
    
    for md_file in settings.vault.path.rglob("*.md"):
        rel_path = str(md_file.relative_to(settings.vault.path))
        if keyword_lower in rel_path.lower():
            matches.append(rel_path)
    
    if not matches:
        return f"No notes found with '{keyword}'"
    
    max_results = settings.tools.filesystem.max_search_results
    logger.debug(f"  Found {len(matches)} matches")
    return "\n".join(matches[:max_results])


@tool
def read_note(file_path: str, max_lines: int | None = None) -> str:
    """Read content of a markdown note."""
    if max_lines is None:
        max_lines = settings.modules.retrieval.max_file_lines
    
    logger.info(f"[TOOL] read_note('{file_path}', max_lines={max_lines})")
    
    full_path = settings.vault.path / file_path
    
    if not full_path.exists():
        return f"File not found: {file_path}"
    
    try:
        lines = full_path.read_text(encoding='utf-8').split('\n')
        content = '\n'.join(lines[:max_lines])
        
        if len(lines) > max_lines:
            content += f"\n\n[{len(lines) - max_lines} more lines...]"
        
        logger.debug(f"  Read {len(lines)} lines (showing {min(len(lines), max_lines)})")
        return content
    except Exception as e:
        logger.error(f"  Error reading file: {e}")
        return f"Error reading file: {e}"


@tool
def grep_content(search_term: str, folder: str = "") -> str:
    """Search for text inside markdown files."""
    logger.info(f"[TOOL] grep_content('{search_term}', folder='{folder}')")
    
    target = settings.vault.path / folder if folder else settings.vault.path
    results = []
    
    for md_file in target.rglob("*.md"):
        try:
            content = md_file.read_text(encoding='utf-8')
            if search_term.lower() in content.lower():
                rel_path = md_file.relative_to(settings.vault.path)
                
                matching_lines = [
                    line for line in content.split('\n') 
                    if search_term.lower() in line.lower()
                ]
                snippet = matching_lines[0][:100] if matching_lines else ""
                results.append(f"{rel_path}: ...{snippet}...")
        except Exception:
            continue
    
    if not results:
        return f"No content found matching '{search_term}'"
    
    max_results = settings.tools.filesystem.max_grep_results
    logger.debug(f"  Found in {len(results)} files")
    return "\n".join(results[:max_results])


def get_all_tools() -> list:
    """Return list of all available tools."""
    return [list_folder, search_notes, read_note, grep_content]
