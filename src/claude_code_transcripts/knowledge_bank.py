"""Generate structured Markdown knowledge bank from analyzed patterns."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .pattern_analyzer import AnalysisResult, Pattern, PREDEFINED_CATEGORIES


def generate_knowledge_bank(
    result: AnalysisResult,
    output_path: Optional[Path] = None,
) -> str:
    """Generate a Markdown knowledge bank from analysis results.
    
    Args:
        result: AnalysisResult with patterns
        output_path: Optional path to write the file
        
    Returns:
        Generated Markdown content
    """
    lines = []
    
    # Header
    lines.append("# My Claude Patterns")
    lines.append("")
    lines.append(f"> Auto-generated from {result.sessions_analyzed} sessions")
    lines.append(f"> {result.total_prompts_analyzed} prompts analyzed")
    lines.append(f"> Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    # Get approved patterns only (or all if not reviewed)
    approved_patterns = [
        p for p in result.patterns 
        if p.approved is None or p.approved is True
    ]
    
    if not approved_patterns:
        lines.append("*No patterns discovered yet. Run more sessions to build your knowledge bank.*")
        content = "\n".join(lines)
        if output_path:
            output_path.write_text(content, encoding="utf-8")
        return content
    
    # Group patterns by category
    patterns_by_category: dict[str, list[Pattern]] = {}
    for p in approved_patterns:
        cat = p.category
        if cat not in patterns_by_category:
            patterns_by_category[cat] = []
        patterns_by_category[cat].append(p)
    
    # All categories (predefined + custom)
    all_categories = {**PREDEFINED_CATEGORIES, **result.custom_categories}
    
    # Sort categories: predefined first, then custom
    predefined_order = list(PREDEFINED_CATEGORIES.keys())
    custom_cats = [c for c in patterns_by_category.keys() if c not in predefined_order]
    ordered_cats = [c for c in predefined_order if c in patterns_by_category] + sorted(custom_cats)
    
    # Generate sections for each category
    for category in ordered_cats:
        patterns = patterns_by_category.get(category, [])
        if not patterns:
            continue
        
        # Section header
        category_title = category.replace("_", " ").title()
        category_desc = all_categories.get(category, "")
        
        lines.append(f"## {category_title}")
        if category_desc:
            lines.append(f"*{category_desc}*")
        lines.append("")
        
        # Sort patterns by confidence (high > medium > low)
        confidence_order = {"high": 0, "medium": 1, "low": 2}
        patterns.sort(key=lambda p: confidence_order.get(p.confidence, 3))
        
        for pattern in patterns:
            # Pattern summary with confidence badge
            confidence_emoji = {
                "high": "🟢",
                "medium": "🟡", 
                "low": "⚪"
            }.get(pattern.confidence, "⚪")
            
            lines.append(f"- **{pattern.summary}** {confidence_emoji}")
            
            # Examples as sub-bullets
            for example in pattern.examples[:3]:  # Max 3 examples
                # Truncate long examples
                if len(example) > 100:
                    example = example[:97] + "..."
                lines.append(f'  - _"{example}"_')
            
            lines.append("")
    
    # Legend
    lines.append("---")
    lines.append("")
    lines.append("**Confidence:** 🟢 High (3+ occurrences) | 🟡 Medium (2 occurrences) | ⚪ Low (inferred)")
    
    content = "\n".join(lines)
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    
    return content


def generate_claude_md(
    result: AnalysisResult,
    output_path: Optional[Path] = None,
) -> str:
    """Generate a CLAUDE.md style file for use with Claude Code.
    
    This creates a more compact format suitable for including in project roots.
    
    Args:
        result: AnalysisResult with patterns
        output_path: Optional path to write the file
        
    Returns:
        Generated Markdown content
    """
    lines = []
    
    lines.append("# Project Preferences")
    lines.append("")
    lines.append("<!-- Auto-generated from Claude Code session analysis -->")
    lines.append("")
    
    # Get high-confidence approved patterns only
    high_confidence = [
        p for p in result.patterns
        if (p.approved is None or p.approved is True) and p.confidence == "high"
    ]
    
    if not high_confidence:
        lines.append("*No high-confidence patterns discovered yet.*")
        content = "\n".join(lines)
        if output_path:
            output_path.write_text(content, encoding="utf-8")
        return content
    
    # Group by category
    patterns_by_category: dict[str, list[Pattern]] = {}
    for p in high_confidence:
        if p.category not in patterns_by_category:
            patterns_by_category[p.category] = []
        patterns_by_category[p.category].append(p)
    
    for category, patterns in patterns_by_category.items():
        category_title = category.replace("_", " ").title()
        lines.append(f"## {category_title}")
        lines.append("")
        
        for pattern in patterns:
            lines.append(f"- {pattern.summary}")
        
        lines.append("")
    
    content = "\n".join(lines)
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    
    return content
