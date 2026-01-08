"""LLM-based pattern analysis for extracted user prompts."""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

try:
    import anthropic
except ImportError:
    anthropic = None

# Predefined categories for pattern organization
PREDEFINED_CATEGORIES = {
    "coding_style": "Naming conventions, formatting, code style preferences",
    "architecture": "File structure, design patterns, project organization",
    "testing": "Testing approaches, coverage expectations, test patterns",
    "documentation": "Comments, README, JSDoc, docstrings preferences",
    "workflow": "Git practices, PR conventions, commit style",
    "tools": "Preferred libraries, frameworks, dependencies",
    "communication": "How you prefer Claude to respond, verbosity, explanations",
    "error_handling": "Exception handling, validation, error messages",
    "performance": "Optimization preferences, caching, efficiency",
    "ui_ux": "User interface patterns, design choices, accessibility",
}

# System prompt for pattern discovery
DISCOVERY_SYSTEM_PROMPT = """You are an expert at analyzing user behavior patterns from coding assistant conversations.

Your task is to identify recurring patterns, preferences, and stylistic choices from a collection of user prompts given to a coding assistant.

Focus on:
1. EXPLICIT INSTRUCTIONS - Things the user directly asks for (e.g., "always use TypeScript")
2. CORRECTIONS - Things the user corrects, which reveal implicit preferences (e.g., "no, use camelCase")
3. REPEATED REQUESTS - Similar requests made across different sessions
4. STYLE PREFERENCES - Coding style, naming conventions, file organization
5. WORKFLOW PATTERNS - How the user likes to work, what they prioritize

For each pattern you identify:
- Summarize it in one clear sentence
- Quote 2-3 example prompts that demonstrate it
- Rate your confidence: high (appears 3+ times explicitly), medium (appears 2 times or implicitly), low (inferred from single occurrence)
- Suggest a category from: coding_style, architecture, testing, documentation, workflow, tools, communication, error_handling, performance, ui_ux, or suggest a custom category

Output your analysis as valid JSON with this structure:
{
    "patterns": [
        {
            "summary": "One sentence describing the pattern",
            "examples": ["quote1", "quote2"],
            "confidence": "high|medium|low",
            "category": "category_name"
        }
    ],
    "custom_categories": [
        {
            "name": "category_name",
            "description": "What this category covers"
        }
    ]
}"""


@dataclass
class Pattern:
    """A discovered preference pattern."""
    summary: str
    examples: list[str]
    confidence: str  # high, medium, low
    category: str
    approved: Optional[bool] = None  # None = not reviewed, True/False = user decision
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        return cls(**data)


@dataclass
class AnalysisResult:
    """Result of pattern analysis."""
    patterns: list[Pattern] = field(default_factory=list)
    custom_categories: dict[str, str] = field(default_factory=dict)  # name -> description
    total_prompts_analyzed: int = 0
    sessions_analyzed: int = 0
    
    def to_dict(self) -> dict:
        return {
            "patterns": [p.to_dict() for p in self.patterns],
            "custom_categories": self.custom_categories,
            "total_prompts_analyzed": self.total_prompts_analyzed,
            "sessions_analyzed": self.sessions_analyzed,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        patterns = [Pattern.from_dict(p) for p in data.get("patterns", [])]
        return cls(
            patterns=patterns,
            custom_categories=data.get("custom_categories", {}),
            total_prompts_analyzed=data.get("total_prompts_analyzed", 0),
            sessions_analyzed=data.get("sessions_analyzed", 0),
        )
    
    def save(self, path: Path):
        """Save analysis result to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "AnalysisResult":
        """Load analysis result from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


def get_api_key() -> str:
    """Get Anthropic API key from environment."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Please set it or use --api-key option."
        )
    return key


def batch_prompts(prompts: list[dict], batch_size: int = 100) -> list[list[dict]]:
    """Split prompts into batches for efficient API usage.
    
    Args:
        prompts: List of prompt dicts
        batch_size: Max prompts per batch
        
    Returns:
        List of prompt batches
    """
    batches = []
    for i in range(0, len(prompts), batch_size):
        batches.append(prompts[i:i + batch_size])
    return batches


def format_prompts_for_analysis(prompts: list[dict]) -> str:
    """Format prompts for LLM analysis.
    
    Args:
        prompts: List of prompt dicts with text, type, project
        
    Returns:
        Formatted string for LLM input
    """
    lines = []
    for i, p in enumerate(prompts, 1):
        prompt_type = p.get("type", "general")
        project = p.get("project", "unknown")
        text = p.get("text", "")
        lines.append(f"[{i}] ({prompt_type}, {project}) {text}")
    return "\n".join(lines)


def analyze_prompts_batch(
    prompts: list[dict],
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> dict:
    """Analyze a batch of prompts using Claude API.
    
    Args:
        prompts: List of prompt dicts
        api_key: Anthropic API key
        model: Model to use for analysis
        
    Returns:
        Raw JSON response from Claude
    """
    if anthropic is None:
        raise ImportError(
            "anthropic package not installed. "
            "Please install it with: pip install anthropic"
        )
    
    client = anthropic.Anthropic(api_key=api_key)
    
    formatted_prompts = format_prompts_for_analysis(prompts)
    
    user_message = f"""Analyze these {len(prompts)} user prompts from coding assistant sessions and identify recurring patterns:

{formatted_prompts}

Remember to output valid JSON with patterns and any custom categories."""

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=DISCOVERY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    
    # Extract JSON from response
    text = response.content[0].text
    
    # Try to parse JSON from the response
    try:
        # Handle case where response is wrapped in markdown code block
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Return raw text if JSON parsing fails
        return {"raw_response": text, "parse_error": str(e)}


def merge_pattern_results(results: list[dict]) -> AnalysisResult:
    """Merge multiple batch analysis results into a single result.
    
    Args:
        results: List of raw JSON responses from analyze_prompts_batch
        
    Returns:
        Merged AnalysisResult
    """
    all_patterns = []
    all_custom_categories = {}
    
    for result in results:
        if "parse_error" in result:
            continue
            
        # Extract patterns
        for p in result.get("patterns", []):
            pattern = Pattern(
                summary=p.get("summary", ""),
                examples=p.get("examples", []),
                confidence=p.get("confidence", "low"),
                category=p.get("category", "general"),
            )
            all_patterns.append(pattern)
        
        # Extract custom categories
        for cat in result.get("custom_categories", []):
            if isinstance(cat, dict):
                name = cat.get("name", "")
                desc = cat.get("description", "")
                if name:
                    all_custom_categories[name] = desc
    
    # Deduplicate similar patterns (by summary similarity)
    # For now, just return all patterns - deduplication can be added later
    
    return AnalysisResult(
        patterns=all_patterns,
        custom_categories=all_custom_categories,
    )


def analyze_all_prompts(
    prompts: list[dict],
    api_key: Optional[str] = None,
    batch_size: int = 100,
    model: str = "claude-sonnet-4-20250514",
    progress_callback=None,
) -> AnalysisResult:
    """Analyze all prompts and extract patterns.
    
    Args:
        prompts: List of prompt dicts from collect_prompts_for_analysis
        api_key: Anthropic API key (uses env if not provided)
        batch_size: Prompts per API call
        model: Claude model to use
        progress_callback: Optional callback(current_batch, total_batches)
        
    Returns:
        AnalysisResult with discovered patterns
    """
    if not api_key:
        api_key = get_api_key()
    
    batches = batch_prompts(prompts, batch_size)
    results = []
    
    for i, batch in enumerate(batches):
        if progress_callback:
            progress_callback(i + 1, len(batches))
        
        result = analyze_prompts_batch(batch, api_key, model)
        results.append(result)
    
    merged = merge_pattern_results(results)
    merged.total_prompts_analyzed = len(prompts)
    merged.sessions_analyzed = len(set(p.get("session_id", "") for p in prompts))
    
    return merged
