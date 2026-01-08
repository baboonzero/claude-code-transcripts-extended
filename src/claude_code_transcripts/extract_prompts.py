"""Extract user prompts from Claude Code transcripts for pattern analysis."""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Iterator

from . import (
    find_all_sessions,
    parse_session_file,
    extract_text_from_content,
    get_project_display_name,
)

# Patterns that indicate a correction/change of mind
CORRECTION_PATTERNS = [
    re.compile(r"^no[,\s]", re.IGNORECASE),
    re.compile(r"^actually[,\s]", re.IGNORECASE),
    re.compile(r"^wait[,\s]", re.IGNORECASE),
    re.compile(r"^sorry[,\s]", re.IGNORECASE),
    re.compile(r"change (this|that|it) to", re.IGNORECASE),
    re.compile(r"instead[,\s]", re.IGNORECASE),
    re.compile(r"^not? like that", re.IGNORECASE),
    re.compile(r"i meant", re.IGNORECASE),
    re.compile(r"that's not (right|correct|what i)", re.IGNORECASE),
    re.compile(r"^undo", re.IGNORECASE),
    re.compile(r"^revert", re.IGNORECASE),
    re.compile(r"go back to", re.IGNORECASE),
]

# Patterns that indicate an instruction/preference
INSTRUCTION_PATTERNS = [
    re.compile(r"always\s", re.IGNORECASE),
    re.compile(r"never\s", re.IGNORECASE),
    re.compile(r"make sure (to|you)", re.IGNORECASE),
    re.compile(r"don't forget", re.IGNORECASE),
    re.compile(r"remember to", re.IGNORECASE),
    re.compile(r"prefer\s", re.IGNORECASE),
    re.compile(r"use\s+\w+\s+instead of", re.IGNORECASE),
    re.compile(r"i (like|want|prefer)", re.IGNORECASE),
    re.compile(r"(should|must) (be|have|use)", re.IGNORECASE),
]


def classify_prompt(text: str) -> str:
    """Classify a user prompt as instruction, correction, or general.
    
    Args:
        text: The user prompt text
        
    Returns:
        One of: 'correction', 'instruction', 'general'
    """
    if not text:
        return "general"
    
    # Check for correction patterns first (higher priority)
    for pattern in CORRECTION_PATTERNS:
        if pattern.search(text):
            return "correction"
    
    # Check for instruction patterns
    for pattern in INSTRUCTION_PATTERNS:
        if pattern.search(text):
            return "instruction"
    
    return "general"


def extract_user_prompts(session_path: Path) -> list[dict]:
    """Extract all user prompts from a single session.
    
    Args:
        session_path: Path to the session file (JSON or JSONL)
        
    Returns:
        List of prompt dicts with keys: text, type, timestamp
    """
    session_path = Path(session_path)
    prompts = []
    
    try:
        data = parse_session_file(session_path)
        loglines = data.get("loglines", [])
        
        for entry in loglines:
            if entry.get("type") != "user":
                continue
                
            # Skip tool results (not actual user prompts)
            message = entry.get("message", {})
            content = message.get("content", "")
            
            # Skip if content is a tool result
            if isinstance(content, list):
                is_tool_result = all(
                    isinstance(b, dict) and b.get("type") == "tool_result"
                    for b in content
                )
                if is_tool_result:
                    continue
            
            # Extract text from content
            text = extract_text_from_content(content)
            
            # Skip empty or very short prompts (likely just confirmations)
            if not text or len(text) < 5:
                continue
            
            # Skip XML-like content (system messages)
            if text.strip().startswith("<"):
                continue
            
            prompt_type = classify_prompt(text)
            timestamp = entry.get("timestamp", "")
            
            prompts.append({
                "text": text,
                "type": prompt_type,
                "timestamp": timestamp,
            })
            
    except Exception as e:
        # Log but don't fail on individual session errors
        pass
    
    return prompts


def extract_all_prompts(
    projects_folder: Path | str,
    limit: int | None = None,
    include_agents: bool = False,
) -> Iterator[dict]:
    """Extract prompts from all sessions in a Claude projects folder.
    
    Args:
        projects_folder: Path to ~/.claude/projects or similar
        limit: Maximum number of sessions to process (None for all)
        include_agents: Whether to include agent-* session files
        
    Yields:
        Session dicts with keys:
        - session_id: Unique session identifier
        - project: Project display name
        - session_path: Full path to session file
        - mtime: Session modification time
        - prompts: List of prompt dicts
    """
    projects_folder = Path(projects_folder)
    
    # Find all sessions
    projects = find_all_sessions(projects_folder, include_agents=include_agents)
    
    session_count = 0
    
    for project in projects:
        project_name = project["name"]
        
        for session in project["sessions"]:
            if limit and session_count >= limit:
                return
            
            session_path = session["path"]
            session_id = session_path.stem
            
            prompts = extract_user_prompts(session_path)
            
            # Skip sessions with no meaningful prompts
            if not prompts:
                continue
            
            yield {
                "session_id": session_id,
                "project": project_name,
                "session_path": str(session_path),
                "mtime": session["mtime"],
                "prompts": prompts,
            }
            
            session_count += 1


def get_prompt_stats(projects_folder: Path | str) -> dict:
    """Get statistics about prompts across all sessions.
    
    Args:
        projects_folder: Path to ~/.claude/projects
        
    Returns:
        Dict with stats: total_sessions, total_prompts, by_type, projects
    """
    stats = {
        "total_sessions": 0,
        "total_prompts": 0,
        "by_type": {"instruction": 0, "correction": 0, "general": 0},
        "projects": set(),
    }
    
    for session in extract_all_prompts(projects_folder):
        stats["total_sessions"] += 1
        stats["projects"].add(session["project"])
        
        for prompt in session["prompts"]:
            stats["total_prompts"] += 1
            prompt_type = prompt.get("type", "general")
            stats["by_type"][prompt_type] = stats["by_type"].get(prompt_type, 0) + 1
    
    stats["projects"] = list(stats["projects"])
    return stats


def collect_prompts_for_analysis(
    projects_folder: Path | str,
    limit: int | None = None,
    min_length: int = 10,
) -> list[dict]:
    """Collect prompts suitable for pattern analysis.
    
    Filters out very short prompts and aggregates into batches suitable
    for LLM analysis.
    
    Args:
        projects_folder: Path to ~/.claude/projects
        limit: Max sessions to process
        min_length: Minimum prompt length to include
        
    Returns:
        List of prompt dicts with: text, type, project, session_id
    """
    all_prompts = []
    
    for session in extract_all_prompts(projects_folder, limit=limit):
        for prompt in session["prompts"]:
            if len(prompt["text"]) >= min_length:
                all_prompts.append({
                    "text": prompt["text"],
                    "type": prompt["type"],
                    "project": session["project"],
                    "session_id": session["session_id"],
                })
    
    return all_prompts
