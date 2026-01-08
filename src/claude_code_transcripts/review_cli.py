"""Interactive CLI for reviewing and approving discovered patterns."""

import questionary
from pathlib import Path
from typing import Optional

from .pattern_analyzer import AnalysisResult, Pattern, PREDEFINED_CATEGORIES


def review_patterns_interactive(
    result: AnalysisResult,
    state_path: Optional[Path] = None,
) -> AnalysisResult:
    """Interactively review patterns and get user approval.
    
    Args:
        result: AnalysisResult with patterns to review
        state_path: Optional path to save progress (for resuming)
        
    Returns:
        Updated AnalysisResult with approval decisions
    """
    # Count patterns to review
    to_review = [p for p in result.patterns if p.approved is None]
    total = len(to_review)
    
    if total == 0:
        print("✓ All patterns have been reviewed!")
        return result
    
    print(f"\n🔍 {total} patterns to review\n")
    print("For each pattern, choose:")
    print("  ✅ Accept - include in knowledge bank")
    print("  ❌ Reject - exclude from knowledge bank")
    print("  ✏️  Edit  - modify the pattern")
    print("  ⏭️  Skip  - review later")
    print("  💾 Save  - save progress and exit")
    print()
    
    all_categories = list(PREDEFINED_CATEGORIES.keys()) + list(result.custom_categories.keys())
    
    reviewed_count = 0
    for i, pattern in enumerate(result.patterns):
        if pattern.approved is not None:
            continue
        
        reviewed_count += 1
        print(f"\n─── Pattern {reviewed_count}/{total} ───")
        print(f"\n📌 {pattern.summary}")
        print(f"   Category: {pattern.category.replace('_', ' ').title()}")
        print(f"   Confidence: {pattern.confidence}")
        print("\n   Examples:")
        for ex in pattern.examples[:3]:
            if len(ex) > 80:
                ex = ex[:77] + "..."
            print(f'     • "{ex}"')
        print()
        
        action = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("✅ Accept", value="accept"),
                questionary.Choice("❌ Reject", value="reject"),
                questionary.Choice("✏️  Edit summary", value="edit"),
                questionary.Choice("🏷️  Change category", value="category"),
                questionary.Choice("⏭️  Skip (review later)", value="skip"),
                questionary.Choice("💾 Save & exit", value="save"),
            ],
        ).ask()
        
        if action is None or action == "save":
            # Save progress and exit
            if state_path:
                result.save(state_path)
                print(f"\n💾 Progress saved to {state_path}")
            break
        elif action == "accept":
            pattern.approved = True
            print("   ✓ Accepted")
        elif action == "reject":
            pattern.approved = False
            print("   ✗ Rejected")
        elif action == "edit":
            new_summary = questionary.text(
                "New summary:",
                default=pattern.summary,
            ).ask()
            if new_summary:
                pattern.summary = new_summary
                print(f"   ✓ Updated: {new_summary}")
            # Don't mark as approved yet, just updated
        elif action == "category":
            new_cat = questionary.select(
                "Select category:",
                choices=all_categories + ["(custom)"],
            ).ask()
            if new_cat == "(custom)":
                new_cat = questionary.text("Enter custom category name:").ask()
                if new_cat:
                    # Add description
                    desc = questionary.text(
                        f"Description for '{new_cat}':",
                        default=""
                    ).ask()
                    if desc:
                        result.custom_categories[new_cat] = desc
            if new_cat:
                pattern.category = new_cat
                print(f"   ✓ Category changed to: {new_cat}")
        # skip does nothing, just moves to next
    
    # Final save
    if state_path:
        result.save(state_path)
    
    # Summary
    accepted = sum(1 for p in result.patterns if p.approved is True)
    rejected = sum(1 for p in result.patterns if p.approved is False)
    pending = sum(1 for p in result.patterns if p.approved is None)
    
    print(f"\n📊 Review Summary:")
    print(f"   ✅ Accepted: {accepted}")
    print(f"   ❌ Rejected: {rejected}")
    print(f"   ⏳ Pending:  {pending}")
    
    return result


def quick_approve_all(result: AnalysisResult) -> AnalysisResult:
    """Accept all patterns without review (for batch processing).
    
    Args:
        result: AnalysisResult with patterns
        
    Returns:
        Updated AnalysisResult with all patterns approved
    """
    for pattern in result.patterns:
        if pattern.approved is None:
            pattern.approved = True
    return result


def quick_approve_high_confidence(result: AnalysisResult) -> AnalysisResult:
    """Accept only high-confidence patterns automatically.
    
    Args:
        result: AnalysisResult with patterns
        
    Returns:
        Updated AnalysisResult with high-confidence patterns approved
    """
    for pattern in result.patterns:
        if pattern.approved is None and pattern.confidence == "high":
            pattern.approved = True
    return result
