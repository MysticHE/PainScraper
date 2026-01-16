"""
Generate static HTML dashboard from pain point data.
"""
import json
from datetime import datetime
from pathlib import Path

from database import (
    get_pain_points,
    get_all_posts,
    get_category_stats,
    get_automation_opportunities,
    get_total_stats,
)
from config import REPORTS_DIR


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
    all_posts = get_all_posts(limit=100)  # Get all posts for the table
    pain_points = get_pain_points(min_intensity=1, limit=50)  # For charts/stats
    automation_ops = get_automation_opportunities(min_intensity=5, limit=10)

    # Extract unique sources for filter dropdown
    unique_sources = sorted(set(pp.get('source', 'unknown') for pp in all_posts if pp.get('source')))

    # Prepare all posts data for JavaScript (includes is_pain_point flag)
    pain_points_json_data = []
    for pp in all_posts:
        scraped_at = pp.get('scraped_at', '')
        date_str = scraped_at[:10] if scraped_at else ''
        pain_points_json_data.append({
            'title': (pp.get('title') or 'No title')[:60],
            'url': pp.get('url', '#'),
            'category': pp.get('category', 'N/A') or 'N/A',
            'intensity': pp.get('intensity', 0) or 0,
            'audience': pp.get('audience', 'N/A') or 'N/A',
            'source': pp.get('source', 'N/A'),
            'date': date_str,
            'is_pain_point': bool(pp.get('is_pain_point', False)),
        })

    # Build pain point rows
    rows = []
    for pp in pain_points[:15]:
        intensity = pp.get('intensity', 0) or 0
        intensity_class = get_intensity_class(intensity)
        title = (pp.get('title') or 'No title')[:60]
        url = pp.get('url', '#')

        rows.append(f'''
        <tr class="table-row border-b border-gray-800/30">
            <td class="py-4 pr-4">
                <a href="{url}" target="_blank" class="hover:text-primary-400 transition-colors font-medium">{title}...</a>
            </td>
            <td class="py-4">
                <span class="badge px-3 py-1 bg-primary-500/15 text-primary-300 rounded-full text-xs font-medium">{pp.get('category', 'N/A')}</span>
            </td>
            <td class="py-4">
                <span class="{intensity_class} font-bold tabular-nums">{intensity}/10</span>
            </td>
            <td class="py-4 text-gray-300 hidden md:table-cell">{pp.get('audience', 'N/A')}</td>
            <td class="py-4 text-gray-500 hidden md:table-cell">{pp.get('source', 'N/A')}</td>
        </tr>
        ''')

    # Build automation cards
    auto_cards = []
    for op in automation_ops[:6]:
        title = (op.get('title') or 'No title')[:50]
        solution = op.get('suggested_solution') or 'No suggestion'
        auto_cards.append(f'''
        <div class="group bg-gradient-to-br from-accent-500/5 to-primary-500/5 rounded-xl p-5 border border-accent-500/10 hover:border-accent-500/30 transition-all hover:shadow-lg hover:shadow-accent-500/5">
            <div class="flex items-start gap-3 mb-3">
                <div class="p-2 rounded-lg bg-accent-500/20 group-hover:bg-accent-500/30 transition-colors">
                    <svg class="w-4 h-4 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
                </div>
                <h3 class="font-semibold text-white group-hover:text-accent-300 transition-colors flex-1">{title}...</h3>
            </div>
            <p class="text-gray-400 text-sm leading-relaxed mb-4">{solution}</p>
            <div class="flex items-center gap-3 text-xs">
                <span class="px-2 py-1 bg-gray-800/50 rounded-md text-gray-400">{op.get('category', 'N/A')}</span>
                <span class="text-gray-600">|</span>
                <span class="text-orange-400 font-medium">Intensity: {op.get('intensity', 'N/A')}/10</span>
            </div>
        </div>
        ''')

    if not auto_cards:
        auto_cards = ['''
        <div class="empty-state col-span-full rounded-xl p-8 text-center">
            <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gray-800/50 mb-4">
                <svg class="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/></svg>
            </div>
            <p class="text-gray-400 mb-1">No high-potential opportunities yet</p>
            <p class="text-gray-600 text-sm">Keep collecting data to identify automation opportunities</p>
        </div>
        ''']

    # Category data for chart
    category_labels = list(category_stats.keys())[:10] if category_stats else ['No data']
    category_data = [category_stats[c]['count'] for c in category_labels] if category_stats else [0]

    # Intensity distribution
    low = sum(1 for pp in pain_points if (pp.get('intensity') or 0) <= 3)
    med = sum(1 for pp in pain_points if 4 <= (pp.get('intensity') or 0) <= 6)
    high = sum(1 for pp in pain_points if (pp.get('intensity') or 0) >= 7)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_posts = stats['total_posts']
    total_pain_points = stats['total_pain_points']
    total_sources = stats['total_sources']
    automation_opps = len(automation_ops)
    pain_point_rows = ''.join(rows) if rows else '<tr><td colspan="5" class="text-center py-4 text-gray-400">No data yet</td></tr>'
    automation_cards_html = ''.join(auto_cards)
    category_labels_json = json.dumps(category_labels)
    category_data_json = json.dumps(category_data)
    intensity_data_json = json.dumps([low, med, high])
    pain_points_data_json = json.dumps(pain_points_json_data)
    sources_json = json.dumps(unique_sources)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SG Pain Point Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{ sans: ['Manrope', 'system-ui', 'sans-serif'] }},
                    colors: {{
                        primary: {{ 50: '#eef2ff', 100: '#e0e7ff', 400: '#818cf8', 500: '#6366f1', 600: '#4f46e5' }},
                        accent: {{ 400: '#34d399', 500: '#10b981', 600: '#059669' }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{ font-family: 'Manrope', system-ui, sans-serif; }}
        .gradient-bg {{ background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); }}
        .card {{
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.08);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .card:hover {{
            background: rgba(255,255,255,0.06);
            border-color: rgba(99, 102, 241, 0.3);
            transform: translateY(-2px);
        }}
        .stat-card {{ position: relative; overflow: hidden; }}
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: var(--accent-color);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        .stat-card:hover::before {{ opacity: 1; }}
        .stat-card-blue {{ --accent-color: #6366f1; }}
        .stat-card-purple {{ --accent-color: #a855f7; }}
        .stat-card-green {{ --accent-color: #10b981; }}
        .stat-card-orange {{ --accent-color: #f97316; }}
        .intensity-high {{ color: #f87171; text-shadow: 0 0 20px rgba(248, 113, 113, 0.3); }}
        .intensity-med {{ color: #fbbf24; }}
        .intensity-low {{ color: #34d399; }}
        .fade-in {{ animation: fadeIn 0.6s ease-out forwards; opacity: 0; }}
        .fade-in-delay-1 {{ animation-delay: 0.1s; }}
        .fade-in-delay-2 {{ animation-delay: 0.2s; }}
        .fade-in-delay-3 {{ animation-delay: 0.3s; }}
        .fade-in-delay-4 {{ animation-delay: 0.4s; }}
        @keyframes fadeIn {{ to {{ opacity: 1; transform: translateY(0); }} from {{ opacity: 0; transform: translateY(10px); }} }}
        .pulse-dot {{ animation: pulse 2s infinite; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
        .search-input {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.2s ease;
        }}
        .search-input:focus {{
            background: rgba(255,255,255,0.08);
            border-color: rgba(99, 102, 241, 0.5);
            outline: none;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }}
        .table-row {{ transition: background 0.15s ease; }}
        .table-row:hover {{ background: rgba(99, 102, 241, 0.08); }}
        .badge {{ transition: transform 0.2s ease; }}
        .badge:hover {{ transform: scale(1.05); }}
        .empty-state {{
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(16, 185, 129, 0.05) 100%);
            border: 2px dashed rgba(255,255,255,0.1);
        }}
        .tabular-nums {{ font-variant-numeric: tabular-nums; }}
        /* Modal styles */
        .modal-overlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(4px);
            z-index: 50;
            justify-content: center;
            align-items: center;
        }}
        .modal-overlay.active {{ display: flex; }}
        .modal-content {{
            background: #1e1b4b;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 1rem;
            max-width: 600px;
            max-height: 85vh;
            width: 90%;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        .modal-header {{
            padding: 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-body {{
            padding: 1.5rem;
            overflow-y: auto;
            flex: 1;
        }}
        .modal-body h3 {{ font-weight: 500; margin-bottom: 0.5rem; }}
        .modal-body p, .modal-body ul {{ color: #9ca3af; font-size: 0.75rem; line-height: 1.6; }}
        .modal-body ul {{ list-style: disc; padding-left: 1.25rem; }}
        .modal-body section {{ margin-bottom: 1.25rem; }}
        .modal-close {{
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 0.5rem;
            padding: 0.5rem;
            cursor: pointer;
            color: #9ca3af;
            transition: all 0.2s;
        }}
        .modal-close:hover {{ background: rgba(255,255,255,0.2); color: white; }}
        .footer-link {{
            color: #9ca3af;
            text-decoration: none;
            transition: color 0.2s;
            cursor: pointer;
        }}
        .footer-link:hover {{ color: #818cf8; text-decoration: underline; }}
    </style>
</head>
<body class="gradient-bg min-h-screen text-white antialiased">
    <div class="container mx-auto px-4 py-8 max-w-7xl">
        <!-- Header -->
        <header class="text-center mb-12 fade-in">
            <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-500/10 border border-primary-500/20 mb-6">
                <span class="w-2 h-2 rounded-full bg-accent-500 pulse-dot"></span>
                <span class="text-sm text-gray-300">Live Data Pipeline</span>
            </div>
            <h1 class="text-4xl md:text-5xl font-bold mb-3 bg-gradient-to-r from-white via-primary-100 to-primary-400 bg-clip-text text-transparent">
                Singapore Pain Point Dashboard
            </h1>
            <p class="text-gray-400 flex items-center justify-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                Updated {generated_at}
            </p>
        </header>

        <!-- Stats Grid -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 mb-12">
            <div class="card stat-card stat-card-blue rounded-2xl p-6 fade-in fade-in-delay-1">
                <div class="flex items-start justify-between mb-3">
                    <div class="p-2 rounded-lg bg-primary-500/20">
                        <svg class="w-5 h-5 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                    </div>
                </div>
                <div class="text-3xl md:text-4xl font-bold text-primary-400 tabular-nums">{total_posts:,}</div>
                <div class="text-gray-400 text-sm mt-1">Posts Analyzed</div>
            </div>
            <div class="card stat-card stat-card-purple rounded-2xl p-6 fade-in fade-in-delay-2">
                <div class="flex items-start justify-between mb-3">
                    <div class="p-2 rounded-lg bg-purple-500/20">
                        <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                    </div>
                </div>
                <div class="text-3xl md:text-4xl font-bold text-purple-400 tabular-nums">{total_pain_points:,}</div>
                <div class="text-gray-400 text-sm mt-1">Pain Points Found</div>
            </div>
            <div class="card stat-card stat-card-green rounded-2xl p-6 fade-in fade-in-delay-3">
                <div class="flex items-start justify-between mb-3">
                    <div class="p-2 rounded-lg bg-accent-500/20">
                        <svg class="w-5 h-5 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
                    </div>
                </div>
                <div class="text-3xl md:text-4xl font-bold text-accent-400 tabular-nums">{total_sources}</div>
                <div class="text-gray-400 text-sm mt-1">Sources Tracked</div>
            </div>
            <div class="card stat-card stat-card-orange rounded-2xl p-6 fade-in fade-in-delay-4">
                <div class="flex items-start justify-between mb-3">
                    <div class="p-2 rounded-lg bg-orange-500/20">
                        <svg class="w-5 h-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                    </div>
                </div>
                <div class="text-3xl md:text-4xl font-bold text-orange-400 tabular-nums">{automation_opps}</div>
                <div class="text-gray-400 text-sm mt-1">Automation Opportunities</div>
            </div>
        </div>

        <!-- Charts Section -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
            <div class="card rounded-2xl p-6">
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-lg font-semibold flex items-center gap-2">
                        <svg class="w-5 h-5 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"/></svg>
                        Pain Points by Category
                    </h2>
                </div>
                <div class="relative" style="height: 280px;">
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>
            <div class="card rounded-2xl p-6">
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-lg font-semibold flex items-center gap-2">
                        <svg class="w-5 h-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                        Intensity Distribution
                    </h2>
                </div>
                <div class="relative" style="height: 280px;">
                    <canvas id="intensityChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Pain Points Table -->
        <div class="card rounded-2xl p-6 mb-12">
            <div class="flex flex-col gap-4 mb-6">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <h2 class="text-lg font-semibold flex items-center gap-2">
                        <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z"/></svg>
                        Top Pain Points
                        <span id="resultCount" class="text-sm font-normal text-gray-400 ml-2"></span>
                    </h2>
                    <div class="relative">
                        <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                        <input type="text" id="searchInput" placeholder="Search pain points..." class="search-input pl-10 pr-4 py-2 rounded-lg text-sm text-white w-full md:w-64">
                    </div>
                </div>
                <!-- Filters Row -->
                <div class="flex flex-wrap items-center gap-3">
                    <!-- Pain Points Toggle -->
                    <div class="flex items-center gap-2 bg-gray-800/50 rounded-lg p-1">
                        <button id="btnAllPosts" onclick="setViewMode('all')" class="px-3 py-1.5 rounded-md text-sm transition-colors bg-primary-500 text-white">
                            All Posts
                        </button>
                        <button id="btnPainPoints" onclick="setViewMode('pain')" class="px-3 py-1.5 rounded-md text-sm transition-colors text-gray-400 hover:text-white">
                            Pain Points Only
                        </button>
                    </div>
                    <div class="h-6 w-px bg-gray-700 hidden md:block"></div>
                    <div class="flex items-center gap-2">
                        <label class="text-sm text-gray-400">Source:</label>
                        <select id="sourceFilter" class="search-input px-3 py-1.5 rounded-lg text-sm text-white bg-transparent">
                            <option value="">All Sources</option>
                        </select>
                    </div>
                    <div class="flex items-center gap-2">
                        <label class="text-sm text-gray-400">Date:</label>
                        <select id="dateFilter" class="search-input px-3 py-1.5 rounded-lg text-sm text-white bg-transparent">
                            <option value="">All Dates</option>
                        </select>
                    </div>
                    <button onclick="clearFilters()" class="text-sm text-primary-400 hover:text-primary-300 transition-colors">
                        Clear Filters
                    </button>
                </div>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full" id="painPointsTable">
                    <thead>
                        <tr class="text-left text-gray-400 border-b border-gray-700/50">
                            <th class="pb-4 font-medium text-sm">Title</th>
                            <th class="pb-4 font-medium text-sm">Type</th>
                            <th class="pb-4 font-medium text-sm">Category</th>
                            <th class="pb-4 font-medium text-sm">Intensity</th>
                            <th class="pb-4 font-medium text-sm hidden md:table-cell">Source</th>
                            <th class="pb-4 font-medium text-sm hidden md:table-cell">Date</th>
                        </tr>
                    </thead>
                    <tbody id="painPointsBody">
                        <!-- Dynamically populated -->
                    </tbody>
                </table>
            </div>
            <!-- Pagination -->
            <div class="flex flex-col md:flex-row items-center justify-between gap-4 mt-6 pt-4 border-t border-gray-700/50">
                <div class="text-sm text-gray-400">
                    Showing <span id="showingStart">1</span>-<span id="showingEnd">10</span> of <span id="totalFiltered">0</span> results
                </div>
                <div class="flex items-center gap-2">
                    <button id="prevBtn" onclick="changePage(-1)" class="px-3 py-1.5 rounded-lg text-sm bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                        Previous
                    </button>
                    <div id="pageNumbers" class="flex items-center gap-1">
                        <!-- Page numbers dynamically populated -->
                    </div>
                    <button id="nextBtn" onclick="changePage(1)" class="px-3 py-1.5 rounded-lg text-sm bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                        Next
                    </button>
                </div>
            </div>
        </div>

        <!-- Automation Opportunities -->
        <div class="card rounded-2xl p-6 mb-12">
            <div class="flex items-center gap-2 mb-6">
                <div class="p-2 rounded-lg bg-accent-500/20">
                    <svg class="w-5 h-5 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                </div>
                <h2 class="text-lg font-semibold">Automation Opportunities</h2>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {automation_cards_html}
            </div>
        </div>

        <!-- Footer -->
        <footer class="border-t border-gray-800/50 pt-8 pb-4">
            <div class="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-gray-500">
                <div class="flex items-center gap-6">
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-accent-500"></span>
                        <span>Reddit</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-primary-500"></span>
                        <span>HardwareZone</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-purple-500"></span>
                        <span>Mothership</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-orange-500"></span>
                        <span>STOMP</span>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <span class="footer-link" onclick="openModal('privacyModal')">Privacy Notice</span>
                    <span class="text-gray-700">|</span>
                    <span class="footer-link" onclick="openModal('termsModal')">Terms of Use</span>
                    <span class="text-gray-700">|</span>
                    <a href="https://github.com/MysticHE/PainScraper" class="text-primary-400 hover:text-primary-300 transition-colors flex items-center gap-1">
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"/></svg>
                        GitHub
                    </a>
                </div>
            </div>
        </footer>
    </div>

    <!-- Terms of Use Modal -->
    <div id="termsModal" class="modal-overlay" onclick="closeModalOnOverlay(event, 'termsModal')">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <h2 class="text-xl font-semibold">Terms of Use</h2>
                    <p class="text-gray-400 text-sm">Last Updated: January 2026</p>
                </div>
                <button class="modal-close" onclick="closeModal('termsModal')">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            </div>
            <div class="modal-body">
                <section>
                    <h3>About This Service</h3>
                    <p>SG Pain Point Dashboard aggregates and analyzes public content from Singapore news sources and forums to identify common pain points and frustrations.</p>
                </section>
                <section>
                    <h3>Data Sources</h3>
                    <ul>
                        <li>Mothership.sg (RSS feed)</li>
                        <li>STOMP (web scraping)</li>
                        <li>HardwareZone EDMW (web scraping)</li>
                    </ul>
                </section>
                <section>
                    <h3>Service Availability</h3>
                    <p>This is a personal project provided as-is. We do not guarantee uptime or availability. Data is refreshed daily via automated workflows.</p>
                </section>
                <section>
                    <h3>Acceptable Use</h3>
                    <p>This dashboard is for informational purposes only. Do not use the data for spam, harassment, or any illegal purpose.</p>
                </section>
                <section>
                    <h3>Limitation of Liability</h3>
                    <p>This service is provided "as is" without warranties of any kind. We are not liable for any damages arising from your use of this service or reliance on the data presented.</p>
                </section>
                <section>
                    <h3>Changes</h3>
                    <p>We may update these terms at any time. Continued use after changes constitutes acceptance.</p>
                </section>
            </div>
        </div>
    </div>

    <!-- Privacy Notice Modal -->
    <div id="privacyModal" class="modal-overlay" onclick="closeModalOnOverlay(event, 'privacyModal')">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <h2 class="text-xl font-semibold">Privacy Notice</h2>
                    <p class="text-gray-400 text-sm">Last Updated: January 2026</p>
                </div>
                <button class="modal-close" onclick="closeModal('privacyModal')">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            </div>
            <div class="modal-body">
                <section>
                    <h3>What We Collect</h3>
                    <ul>
                        <li>No personal information is collected from visitors</li>
                        <li>No cookies or tracking scripts are used</li>
                        <li>No user accounts or login required</li>
                    </ul>
                </section>
                <section>
                    <h3>Data Displayed</h3>
                    <p>This dashboard displays publicly available content from news sites and forums. All content is sourced from public pages and RSS feeds.</p>
                </section>
                <section>
                    <h3>Third-Party Services</h3>
                    <ul>
                        <li>GitHub Pages (hosting)</li>
                        <li>Groq API (content classification)</li>
                        <li>Chart.js and Tailwind CSS (frontend libraries via CDN)</li>
                    </ul>
                </section>
                <section>
                    <h3>Questions</h3>
                    <p>For privacy questions, please open an issue on the <a href="https://github.com/MysticHE/PainScraper" class="text-primary-400 hover:underline">GitHub repository</a>.</p>
                </section>
            </div>
        </div>
    </div>

    <script>
        // Modal functions
        function openModal(modalId) {{
            document.getElementById(modalId).classList.add('active');
            document.body.style.overflow = 'hidden';
        }}
        function closeModal(modalId) {{
            document.getElementById(modalId).classList.remove('active');
            document.body.style.overflow = '';
        }}
        function closeModalOnOverlay(event, modalId) {{
            if (event.target.classList.contains('modal-overlay')) {{
                closeModal(modalId);
            }}
        }}
        // Close modal on Escape key
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                document.querySelectorAll('.modal-overlay.active').forEach(m => {{
                    m.classList.remove('active');
                    document.body.style.overflow = '';
                }});
            }}
        }});

        // Pain Points Data and Pagination
        const allPainPoints = {pain_points_data_json};
        const sources = {sources_json};
        const ITEMS_PER_PAGE = 10;
        const MAX_PAGES = 5;
        let currentPage = 1;
        let filteredData = [...allPainPoints];
        let viewMode = 'all'; // 'all' or 'pain'

        // Initialize filters
        function initFilters() {{
            const sourceFilter = document.getElementById('sourceFilter');
            const dateFilter = document.getElementById('dateFilter');

            // Populate source filter
            sources.forEach(source => {{
                const option = document.createElement('option');
                option.value = source;
                option.textContent = source;
                sourceFilter.appendChild(option);
            }});

            // Extract unique dates and populate date filter
            const dates = [...new Set(allPainPoints.map(pp => pp.date).filter(d => d))].sort().reverse();
            dates.forEach(date => {{
                const option = document.createElement('option');
                option.value = date;
                option.textContent = date;
                dateFilter.appendChild(option);
            }});

            // Add event listeners
            document.getElementById('searchInput').addEventListener('input', applyFilters);
            sourceFilter.addEventListener('change', applyFilters);
            dateFilter.addEventListener('change', applyFilters);
        }}

        function getIntensityClass(intensity) {{
            if (intensity >= 7) return 'intensity-high';
            if (intensity >= 4) return 'intensity-med';
            return 'intensity-low';
        }}

        function setViewMode(mode) {{
            viewMode = mode;
            // Update button styles
            const btnAll = document.getElementById('btnAllPosts');
            const btnPain = document.getElementById('btnPainPoints');
            if (mode === 'all') {{
                btnAll.className = 'px-3 py-1.5 rounded-md text-sm transition-colors bg-primary-500 text-white';
                btnPain.className = 'px-3 py-1.5 rounded-md text-sm transition-colors text-gray-400 hover:text-white';
            }} else {{
                btnAll.className = 'px-3 py-1.5 rounded-md text-sm transition-colors text-gray-400 hover:text-white';
                btnPain.className = 'px-3 py-1.5 rounded-md text-sm transition-colors bg-primary-500 text-white';
            }}
            applyFilters();
        }}

        function applyFilters() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const sourceValue = document.getElementById('sourceFilter').value;
            const dateValue = document.getElementById('dateFilter').value;

            filteredData = allPainPoints.filter(pp => {{
                // Filter by view mode
                if (viewMode === 'pain' && !pp.is_pain_point) return false;

                const matchesSearch = !searchTerm ||
                    pp.title.toLowerCase().includes(searchTerm) ||
                    pp.category.toLowerCase().includes(searchTerm) ||
                    pp.source.toLowerCase().includes(searchTerm);
                const matchesSource = !sourceValue || pp.source === sourceValue;
                const matchesDate = !dateValue || pp.date === dateValue;
                return matchesSearch && matchesSource && matchesDate;
            }});

            currentPage = 1;
            renderTable();
        }}

        function clearFilters() {{
            document.getElementById('searchInput').value = '';
            document.getElementById('sourceFilter').value = '';
            document.getElementById('dateFilter').value = '';
            applyFilters();
        }}

        function renderTable() {{
            const tbody = document.getElementById('painPointsBody');
            const totalPages = Math.min(Math.ceil(filteredData.length / ITEMS_PER_PAGE), MAX_PAGES);
            const maxItems = MAX_PAGES * ITEMS_PER_PAGE;
            const displayData = filteredData.slice(0, maxItems);

            const startIdx = (currentPage - 1) * ITEMS_PER_PAGE;
            const endIdx = Math.min(startIdx + ITEMS_PER_PAGE, displayData.length);
            const pageData = displayData.slice(startIdx, endIdx);

            if (pageData.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-gray-400">No posts match your filters</td></tr>';
            }} else {{
                tbody.innerHTML = pageData.map(pp => `
                    <tr class="table-row border-b border-gray-800/30">
                        <td class="py-4 pr-4">
                            <a href="${{pp.url}}" target="_blank" class="hover:text-primary-400 transition-colors font-medium">${{pp.title}}...</a>
                        </td>
                        <td class="py-4">
                            ${{pp.is_pain_point
                                ? '<span class="px-2 py-1 bg-red-500/20 text-red-300 rounded-full text-xs font-medium">Pain Point</span>'
                                : '<span class="px-2 py-1 bg-gray-500/20 text-gray-400 rounded-full text-xs font-medium">General</span>'
                            }}
                        </td>
                        <td class="py-4">
                            <span class="badge px-3 py-1 bg-primary-500/15 text-primary-300 rounded-full text-xs font-medium">${{pp.category}}</span>
                        </td>
                        <td class="py-4">
                            <span class="${{getIntensityClass(pp.intensity)}} font-bold tabular-nums">${{pp.intensity || '-'}}/10</span>
                        </td>
                        <td class="py-4 text-gray-500 hidden md:table-cell">${{pp.source}}</td>
                        <td class="py-4 text-gray-500 hidden md:table-cell">${{pp.date || 'N/A'}}</td>
                    </tr>
                `).join('');
            }}

            // Update pagination info
            document.getElementById('showingStart').textContent = displayData.length > 0 ? startIdx + 1 : 0;
            document.getElementById('showingEnd').textContent = endIdx;
            document.getElementById('totalFiltered').textContent = Math.min(filteredData.length, maxItems);

            // Update pagination buttons
            document.getElementById('prevBtn').disabled = currentPage === 1;
            document.getElementById('nextBtn').disabled = currentPage >= totalPages || totalPages === 0;

            // Render page numbers
            const pageNumbersDiv = document.getElementById('pageNumbers');
            pageNumbersDiv.innerHTML = '';
            for (let i = 1; i <= totalPages; i++) {{
                const btn = document.createElement('button');
                btn.textContent = i;
                btn.className = `px-3 py-1.5 rounded-lg text-sm transition-colors ${{
                    i === currentPage
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 hover:text-white'
                }}`;
                btn.onclick = () => goToPage(i);
                pageNumbersDiv.appendChild(btn);
            }}
        }}

        function changePage(delta) {{
            const totalPages = Math.min(Math.ceil(filteredData.length / ITEMS_PER_PAGE), MAX_PAGES);
            const newPage = currentPage + delta;
            if (newPage >= 1 && newPage <= totalPages) {{
                currentPage = newPage;
                renderTable();
            }}
        }}

        function goToPage(page) {{
            currentPage = page;
            renderTable();
        }}

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', () => {{
            initFilters();
            renderTable();
        }});

        // Chart.js global defaults
        Chart.defaults.font.family = "'Manrope', system-ui, sans-serif";
        Chart.defaults.color = '#9ca3af';

        // Category Doughnut Chart
        const categoryCtx = document.getElementById('categoryChart').getContext('2d');
        new Chart(categoryCtx, {{
            type: 'doughnut',
            data: {{
                labels: {category_labels_json},
                datasets: [{{
                    data: {category_data_json},
                    backgroundColor: [
                        'rgba(99, 102, 241, 0.8)',
                        'rgba(168, 85, 247, 0.8)',
                        'rgba(236, 72, 153, 0.8)',
                        'rgba(245, 158, 11, 0.8)',
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(6, 182, 212, 0.8)',
                        'rgba(249, 115, 22, 0.8)',
                        'rgba(132, 204, 22, 0.8)',
                        'rgba(139, 92, 246, 0.8)',
                        'rgba(20, 184, 166, 0.8)'
                    ],
                    borderColor: 'rgba(15, 23, 42, 0.8)',
                    borderWidth: 2,
                    hoverOffset: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{
                            color: '#9ca3af',
                            padding: 12,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: {{ size: 11 }}
                        }}
                    }},
                    tooltip: {{
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#fff',
                        bodyColor: '#9ca3af',
                        borderColor: 'rgba(99, 102, 241, 0.3)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }}
                }}
            }}
        }});

        // Intensity Bar Chart
        const intensityCtx = document.getElementById('intensityChart').getContext('2d');
        new Chart(intensityCtx, {{
            type: 'bar',
            data: {{
                labels: ['Low (1-3)', 'Medium (4-6)', 'High (7-10)'],
                datasets: [{{
                    label: 'Pain Points',
                    data: {intensity_data_json},
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.7)',
                        'rgba(245, 158, 11, 0.7)',
                        'rgba(239, 68, 68, 0.7)'
                    ],
                    borderColor: [
                        'rgba(16, 185, 129, 1)',
                        'rgba(245, 158, 11, 1)',
                        'rgba(239, 68, 68, 1)'
                    ],
                    borderWidth: 1,
                    borderRadius: 8,
                    borderSkipped: false
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#fff',
                        bodyColor: '#9ca3af',
                        borderColor: 'rgba(99, 102, 241, 0.3)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            color: '#6b7280',
                            font: {{ size: 11 }}
                        }},
                        grid: {{
                            color: 'rgba(255, 255, 255, 0.05)',
                            drawBorder: false
                        }}
                    }},
                    x: {{
                        ticks: {{
                            color: '#9ca3af',
                            font: {{ size: 11 }}
                        }},
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});

        // Fade-in animation on scroll
        const observerOptions = {{
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        }};

        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }}
            }});
        }}, observerOptions);

        document.querySelectorAll('.card').forEach(card => {{
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            observer.observe(card);
        }});
    </script>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Dashboard generated: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    generate_dashboard()
