"""
Generate static HTML dashboard from pain point data.
"""
import json
from datetime import datetime
from pathlib import Path

from database import (
    get_pain_points,
    get_category_stats,
    get_automation_opportunities,
    get_total_stats,
)
from config import REPORTS_DIR

DASHBOARD_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SG Pain Point Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .gradient-bg { background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%); }
        .card { background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
        .intensity-high { color: #ef4444; }
        .intensity-med { color: #f59e0b; }
        .intensity-low { color: #22c55e; }
    </style>
</head>
<body class="gradient-bg min-h-screen text-white">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="text-center mb-10">
            <h1 class="text-4xl font-bold mb-2">🇸🇬 Singapore Pain Point Dashboard</h1>
            <p class="text-gray-400">Last updated: {generated_at}</p>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
            <div class="card rounded-xl p-6 text-center">
                <div class="text-4xl font-bold text-blue-400">{total_posts}</div>
                <div class="text-gray-400 mt-2">Posts Analyzed</div>
            </div>
            <div class="card rounded-xl p-6 text-center">
                <div class="text-4xl font-bold text-purple-400">{total_pain_points}</div>
                <div class="text-gray-400 mt-2">Pain Points Found</div>
            </div>
            <div class="card rounded-xl p-6 text-center">
                <div class="text-4xl font-bold text-green-400">{total_sources}</div>
                <div class="text-gray-400 mt-2">Sources Tracked</div>
            </div>
            <div class="card rounded-xl p-6 text-center">
                <div class="text-4xl font-bold text-orange-400">{automation_opps}</div>
                <div class="text-gray-400 mt-2">Automation Opportunities</div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
            <!-- Category Chart -->
            <div class="card rounded-xl p-6">
                <h2 class="text-xl font-semibold mb-4">Pain Points by Category</h2>
                <canvas id="categoryChart" height="300"></canvas>
            </div>
            <!-- Intensity Distribution -->
            <div class="card rounded-xl p-6">
                <h2 class="text-xl font-semibold mb-4">Intensity Distribution</h2>
                <canvas id="intensityChart" height="300"></canvas>
            </div>
        </div>

        <!-- Top Pain Points -->
        <div class="card rounded-xl p-6 mb-10">
            <h2 class="text-xl font-semibold mb-4">🔥 Top Pain Points (High Intensity)</h2>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="text-left text-gray-400 border-b border-gray-700">
                            <th class="pb-3">Title</th>
                            <th class="pb-3">Category</th>
                            <th class="pb-3">Intensity</th>
                            <th class="pb-3">Audience</th>
                            <th class="pb-3">Source</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pain_point_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Automation Opportunities -->
        <div class="card rounded-xl p-6 mb-10">
            <h2 class="text-xl font-semibold mb-4">🤖 Best Automation Opportunities</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {automation_cards}
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center text-gray-500 mt-10">
            <p>Data scraped from Reddit, HardwareZone, Mothership.sg, STOMP</p>
            <p class="mt-2">Powered by Llama 3.1 | <a href="https://github.com/MysticHE/PainScraper" class="text-blue-400 hover:underline">GitHub</a></p>
        </div>
    </div>

    <script>
        // Category Chart
        const categoryCtx = document.getElementById('categoryChart').getContext('2d');
        new Chart(categoryCtx, {
            type: 'doughnut',
            data: {
                labels: {category_labels},
                datasets: [{
                    data: {category_data},
                    backgroundColor: [
                        '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#22c55e',
                        '#06b6d4', '#f97316', '#84cc16', '#a855f7', '#14b8a6'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#9ca3af' }
                    }
                }
            }
        });

        // Intensity Chart
        const intensityCtx = document.getElementById('intensityChart').getContext('2d');
        new Chart(intensityCtx, {
            type: 'bar',
            data: {
                labels: ['1-3 (Low)', '4-6 (Medium)', '7-10 (High)'],
                datasets: [{
                    label: 'Pain Points',
                    data: {intensity_data},
                    backgroundColor: ['#22c55e', '#f59e0b', '#ef4444']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        ticks: { color: '#9ca3af' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    },
                    x: {
                        ticks: { color: '#9ca3af' },
                        grid: { display: false }
                    }
                }
            }
        });
    </script>
</body>
</html>
'''


def get_intensity_class(intensity):
    if intensity >= 7:
        return "intensity-high"
    elif intensity >= 4:
        return "intensity-med"
    return "intensity-low"


def generate_dashboard(output_path=None):
    """Generate HTML dashboard."""
    if output_path is None:
        output_path = Path("docs/index.html")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Gather data
    stats = get_total_stats()
    category_stats = get_category_stats()
    pain_points = get_pain_points(min_intensity=1, limit=50)
    automation_ops = get_automation_opportunities(min_intensity=5, limit=10)

    # Build pain point rows
    rows = []
    for pp in pain_points[:15]:
        intensity = pp.get('intensity', 0) or 0
        intensity_class = get_intensity_class(intensity)
        title = (pp.get('title') or 'No title')[:60]
        url = pp.get('url', '#')

        rows.append(f'''
        <tr class="border-b border-gray-800 hover:bg-white/5">
            <td class="py-3"><a href="{url}" target="_blank" class="hover:text-blue-400">{title}...</a></td>
            <td class="py-3"><span class="px-2 py-1 bg-blue-500/20 rounded text-sm">{pp.get('category', 'N/A')}</span></td>
            <td class="py-3 {intensity_class} font-bold">{intensity}/10</td>
            <td class="py-3">{pp.get('audience', 'N/A')}</td>
            <td class="py-3 text-gray-400">{pp.get('source', 'N/A')}</td>
        </tr>
        ''')

    # Build automation cards
    auto_cards = []
    for op in automation_ops[:6]:
        title = (op.get('title') or 'No title')[:50]
        solution = op.get('suggested_solution') or 'No suggestion'
        auto_cards.append(f'''
        <div class="bg-gradient-to-r from-green-500/10 to-blue-500/10 rounded-lg p-4 border border-green-500/20">
            <h3 class="font-semibold text-green-400 mb-2">{title}...</h3>
            <p class="text-gray-300 text-sm">{solution}</p>
            <div class="mt-2 text-xs text-gray-500">Category: {op.get('category', 'N/A')} | Intensity: {op.get('intensity', 'N/A')}/10</div>
        </div>
        ''')

    if not auto_cards:
        auto_cards = ['<p class="text-gray-400 col-span-2">No high-potential opportunities identified yet. Keep collecting data!</p>']

    # Category data for chart
    category_labels = list(category_stats.keys())[:10]
    category_data = [category_stats[c]['count'] for c in category_labels]

    # Intensity distribution
    low = sum(1 for pp in pain_points if (pp.get('intensity') or 0) <= 3)
    med = sum(1 for pp in pain_points if 4 <= (pp.get('intensity') or 0) <= 6)
    high = sum(1 for pp in pain_points if (pp.get('intensity') or 0) >= 7)

    # Generate HTML
    html = DASHBOARD_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_posts=stats['total_posts'],
        total_pain_points=stats['total_pain_points'],
        total_sources=stats['total_sources'],
        automation_opps=len(automation_ops),
        pain_point_rows=''.join(rows) if rows else '<tr><td colspan="5" class="text-center py-4 text-gray-400">No data yet</td></tr>',
        automation_cards=''.join(auto_cards),
        category_labels=json.dumps(category_labels),
        category_data=json.dumps(category_data),
        intensity_data=json.dumps([low, med, high]),
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Dashboard generated: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    generate_dashboard()
