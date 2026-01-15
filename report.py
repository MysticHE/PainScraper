"""
Report generator for Singapore Pain Point analysis.
Exports findings to markdown format.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from database import (
    get_pain_points,
    get_category_stats,
    get_automation_opportunities,
    get_recent_vs_previous,
    get_total_stats,
)
from config import REPORTS_DIR


def generate_report(output_path: Optional[str] = None) -> str:
    """
    Generate a comprehensive markdown report.

    Args:
        output_path: Optional custom output path

    Returns:
        Path to generated report
    """
    # Generate default filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    if output_path is None:
        output_path = REPORTS_DIR / f"{date_str}.md"
    else:
        output_path = Path(output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Gather data
    total_stats = get_total_stats()
    category_stats = get_category_stats()
    top_pain_points = get_pain_points(min_intensity=6, limit=10)
    automation_ops = get_automation_opportunities(min_intensity=6, limit=20)
    trending = get_recent_vs_previous(days_recent=7, days_previous=14)

    # Build report
    report_lines = []

    # Header
    report_lines.extend([
        f"# Singapore Pain Point Analysis Report",
        f"",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"---",
        f"",
    ])

    # Executive Summary
    report_lines.extend([
        f"## Executive Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Posts Analyzed | {total_stats['total_posts']} |",
        f"| Pain Points Identified | {total_stats['total_pain_points']} |",
        f"| Sources Tracked | {total_stats['total_sources']} |",
        f"| High-Potential Automation Opportunities | {len(automation_ops)} |",
        f"",
    ])

    # Posts by Source
    if total_stats['posts_by_source']:
        report_lines.extend([
            f"### Posts by Source",
            f"",
        ])
        for source, count in sorted(
            total_stats['posts_by_source'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            report_lines.append(f"- **{source}**: {count} posts")
        report_lines.append("")

    # Top 10 Pain Points by Intensity
    report_lines.extend([
        f"---",
        f"",
        f"## Top 10 Pain Points by Intensity",
        f"",
    ])

    if top_pain_points:
        for i, pp in enumerate(top_pain_points[:10], 1):
            title = pp.get('title', 'No title')[:80]
            report_lines.extend([
                f"### {i}. {title}",
                f"",
                f"- **Intensity:** {pp.get('intensity', 'N/A')}/10",
                f"- **Category:** {pp.get('category', 'N/A')}",
                f"- **Audience:** {pp.get('audience', 'N/A')}",
                f"- **Automation Potential:** {pp.get('automation_potential', 'N/A')}",
                f"- **Source:** {pp.get('source', 'N/A')}",
                f"",
            ])
            if pp.get('summary'):
                report_lines.append(f"> {pp['summary']}")
                report_lines.append("")
            if pp.get('suggested_solution'):
                report_lines.append(f"**Suggested Solution:** {pp['suggested_solution']}")
                report_lines.append("")
            if pp.get('url'):
                report_lines.append(f"[View Original]({pp['url']})")
                report_lines.append("")
    else:
        report_lines.append("*No high-intensity pain points found yet.*")
        report_lines.append("")

    # Pain Points by Category
    report_lines.extend([
        f"---",
        f"",
        f"## Pain Points by Category",
        f"",
    ])

    if category_stats:
        report_lines.extend([
            f"| Category | Count | Avg Intensity |",
            f"|----------|-------|---------------|",
        ])
        for category, stats in sorted(
            category_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        ):
            report_lines.append(
                f"| {category.replace('_', ' ').title()} | {stats['count']} | {stats['avg_intensity']}/10 |"
            )
        report_lines.append("")

        # Category breakdown chart (ASCII)
        report_lines.extend([
            f"### Category Distribution",
            f"",
            f"```",
        ])
        max_count = max(s['count'] for s in category_stats.values()) if category_stats else 1
        for category, stats in sorted(
            category_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:10]:
            bar_length = int((stats['count'] / max_count) * 30)
            bar = "█" * bar_length
            report_lines.append(f"{category[:15]:<15} {bar} ({stats['count']})")
        report_lines.extend([
            f"```",
            f"",
        ])
    else:
        report_lines.append("*No categorized pain points yet.*")
        report_lines.append("")

    # Best Automation Opportunities
    report_lines.extend([
        f"---",
        f"",
        f"## Best Automation Opportunities",
        f"",
        f"*High automation potential + High intensity = Best opportunities for AI solutions*",
        f"",
    ])

    if automation_ops:
        for i, op in enumerate(automation_ops[:10], 1):
            title = op.get('title', 'No title')[:60]
            report_lines.extend([
                f"### {i}. {title}...",
                f"",
                f"- **Category:** {op.get('category', 'N/A')}",
                f"- **Intensity:** {op.get('intensity', 'N/A')}/10",
                f"- **Source:** {op.get('source', 'N/A')}",
                f"",
            ])
            if op.get('summary'):
                report_lines.append(f"> {op['summary']}")
                report_lines.append("")
            if op.get('suggested_solution'):
                report_lines.extend([
                    f"**AI Solution Idea:**",
                    f"{op['suggested_solution']}",
                    f"",
                ])
    else:
        report_lines.append("*No high-potential automation opportunities identified yet.*")
        report_lines.append("")

    # Trending Analysis
    report_lines.extend([
        f"---",
        f"",
        f"## Trending Topics",
        f"",
        f"*Comparing last 7 days vs previous 7 days*",
        f"",
    ])

    recent = trending.get('recent', {})
    previous = trending.get('previous', {})

    if recent or previous:
        all_categories = set(recent.keys()) | set(previous.keys())

        trending_up = []
        trending_down = []

        for cat in all_categories:
            recent_count = recent.get(cat, 0)
            prev_count = previous.get(cat, 0)

            if prev_count == 0 and recent_count > 0:
                trending_up.append((cat, recent_count, "NEW"))
            elif recent_count > prev_count:
                change = ((recent_count - prev_count) / max(prev_count, 1)) * 100
                trending_up.append((cat, recent_count, f"+{change:.0f}%"))
            elif recent_count < prev_count:
                change = ((prev_count - recent_count) / max(prev_count, 1)) * 100
                trending_down.append((cat, recent_count, f"-{change:.0f}%"))

        if trending_up:
            report_lines.extend([
                f"### Trending Up 📈",
                f"",
            ])
            for cat, count, change in sorted(trending_up, key=lambda x: x[1], reverse=True)[:5]:
                report_lines.append(f"- **{cat.replace('_', ' ').title()}**: {count} mentions ({change})")
            report_lines.append("")

        if trending_down:
            report_lines.extend([
                f"### Trending Down 📉",
                f"",
            ])
            for cat, count, change in sorted(trending_down, key=lambda x: x[1])[:5]:
                report_lines.append(f"- **{cat.replace('_', ' ').title()}**: {count} mentions ({change})")
            report_lines.append("")
    else:
        report_lines.append("*Not enough data for trending analysis yet.*")
        report_lines.append("")

    # Footer
    report_lines.extend([
        f"---",
        f"",
        f"## Methodology",
        f"",
        f"This report was generated by the Singapore Pain Point Scraper system:",
        f"",
        f"1. **Data Collection**: Posts scraped from Reddit (r/singapore, r/askSingapore, etc.), HardwareZone EDMW, Mothership.sg, and STOMP",
        f"2. **Classification**: Each post analyzed by Llama 3.1 8B via Ollama for pain point identification",
        f"3. **Scoring**: Pain points rated on intensity (1-10) and automation potential (low/medium/high)",
        f"",
        f"---",
        f"",
        f"*Report generated by [SG Pain Point Scraper](https://github.com/your-repo)*",
    ])

    # Write report
    report_content = "\n".join(report_lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\nReport saved to: {output_path}")
    return str(output_path)


def generate_json_export(output_path: Optional[str] = None) -> str:
    """
    Export pain point data as JSON.

    Args:
        output_path: Optional custom output path

    Returns:
        Path to generated JSON
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    if output_path is None:
        output_path = REPORTS_DIR / f"{date_str}.json"
    else:
        output_path = Path(output_path)

    # Gather all data
    data = {
        "generated_at": datetime.now().isoformat(),
        "total_stats": get_total_stats(),
        "category_stats": get_category_stats(),
        "pain_points": get_pain_points(limit=500),
        "automation_opportunities": get_automation_opportunities(limit=100),
        "trending": get_recent_vs_previous(),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"JSON export saved to: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate pain point reports")
    parser.add_argument("--json", action="store_true", help="Also export as JSON")
    parser.add_argument("--output", type=str, help="Custom output path")

    args = parser.parse_args()

    print("Generating Pain Point Report...")

    report_path = generate_report(args.output)

    if args.json:
        json_path = generate_json_export()

    print("\nDone!")
