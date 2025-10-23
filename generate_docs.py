#!/usr/bin/env python3
"""
Automatic Documentation Generator for OpenGovt Repository

This script analyzes all Python files in the repository and generates:
1. SCRIPT_EVALUATION.md - Comprehensive analysis
2. SCRIPT_INDEX.md - Quick reference guide
3. index.html - Interactive web view of the project

Run this script whenever files are added, removed, or modified to keep
documentation up-to-date.

Usage:
    python generate_docs.py
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Set
from collections import defaultdict


class RepoAnalyzer:
    """Analyzes repository structure and generates documentation."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.python_files: List[Path] = []
        self.file_stats: Dict[str, Dict] = {}
        self.categories: Dict[str, List[Path]] = defaultdict(list)
        
    def scan_repository(self):
        """Scan repository for Python files and categorize them."""
        # Directories to exclude
        exclude_dirs = {'.git', '.venv', 'venv', '.env', 'virtualenv', '.tox', '__pycache__', 'node_modules',
                       '.pytest_cache', 'build', 'dist', 'env'}
        
        # Find all Python files
        for root, dirs, files in os.walk(self.repo_path):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(self.repo_path)
                    self.python_files.append(rel_path)
                    self._analyze_file(rel_path)
                    self._categorize_file(rel_path)
        
        self.python_files.sort()
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file for statistics."""
        full_path = self.repo_path / file_path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            # Count lines
            total_lines = len(lines)
            code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            
            # Find classes and functions
            classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
            functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
            
            # Extract docstring if present
            docstring_match = re.search(r'^["\']{3}(.+?)["\']{3}', content, re.MULTILINE | re.DOTALL)
            docstring = docstring_match.group(1).strip() if docstring_match else ""
            
            self.file_stats[str(file_path)] = {
                'total_lines': total_lines,
                'code_lines': code_lines,
                'classes': classes,
                'functions': functions,
                'docstring': docstring[:200] if docstring else None
            }
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            self.file_stats[str(file_path)] = {
                'total_lines': 0,
                'code_lines': 0,
                'classes': [],
                'functions': [],
                'docstring': None
            }
    
    def _categorize_file(self, file_path: Path):
        """Categorize file based on its location and name."""
        parts = file_path.parts
        
        if file_path.name.startswith('cbw_'):
            self.categories['Core Pipeline (cbw_*.py)'].append(file_path)
        elif parts[0] == 'models':
            self.categories['Data Models (models/)'].append(file_path)
        elif parts[0] == 'analysis':
            self.categories['Analysis Modules (analysis/)'].append(file_path)
        elif parts[0] == 'app':
            self.categories['Application Layer (app/)'].append(file_path)
        elif parts[0] == 'congress_api':
            self.categories['Congress API (congress_api/)'].append(file_path)
        elif parts[0] == 'examples':
            self.categories['Examples (examples/)'].append(file_path)
        elif parts[0] == '.github' and len(parts) > 1 and parts[1] == 'scripts':
            self.categories['GitHub Automation (.github/scripts/)'].append(file_path)
        # Test file categorization
        elif file_path.name.startswith('test_') or 'tests' in parts:
            self.categories['Test Files'].append(file_path)
        # Alternative Implementations, but not test files
        elif ('congress' in file_path.name or 'pipeline' in file_path.name):
            self.categories['Alternative Implementations'].append(file_path)
        else:
            self.categories['Other Scripts'].append(file_path)
    def generate_markdown_index(self) -> str:
        """Generate SCRIPT_INDEX.md content."""
        lines = [
            "# OpenGovt - Quick Script Reference Index",
            "",
            f"**Auto-generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "This is a quick reference guide to all scripts in the repository. ",
            "For comprehensive analysis, see [SCRIPT_EVALUATION.md](SCRIPT_EVALUATION.md).",
            "",
            "## Quick Stats",
            "",
            f"- **Total Python Files:** {len(self.python_files)}",
            f"- **Total Lines of Code:** ~{sum(s['total_lines'] for s in self.file_stats.values()):,}",
            f"- **Total Classes:** {sum(len(s['classes']) for s in self.file_stats.values())}",
            f"- **Total Functions:** {sum(len(s['functions']) for s in self.file_stats.values())}",
            "",
        ]
        
        # Add category tables
        for category, files in sorted(self.categories.items()):
            if not files:
                continue
                
            lines.extend([
                f"## {category}",
                "",
                "| Script | Lines | Classes | Functions |",
                "|--------|-------|---------|-----------|",
            ])
            
            for file_path in sorted(files):
                stats = self.file_stats[str(file_path)]
                lines.append(
                    f"| {file_path} | {stats['total_lines']} | "
                    f"{len(stats['classes'])} | {len(stats['functions'])} |"
                )
            
            total_lines = sum(self.file_stats[str(f)]['total_lines'] for f in files)
            total_classes = sum(len(self.file_stats[str(f)]['classes']) for f in files)
            total_functions = sum(len(self.file_stats[str(f)]['functions']) for f in files)
            
            lines.extend([
                "",
                f"**Total:** {len(files)} files, {total_lines} lines, "
                f"{total_classes} classes, {total_functions} functions",
                "",
            ])
        
        # Add common workflows
        lines.extend([
            "## Common Workflows",
            "",
            "### 1. Basic Data Ingestion",
            "```bash",
            "python cbw_main.py --start-congress 118 --end-congress 118 \\",
            "  --download --extract --postprocess \\",
            '  --db "postgresql://localhost/congress"',
            "```",
            "",
            "### 2. Generate Embeddings",
            "```bash",
            "python examples/embeddings_example.py",
            "```",
            "",
            "### 3. Full Analysis",
            "```bash",
            "python examples/complete_analysis_pipeline.py",
            "```",
            "",
            "### 4. Start Control Server",
            "```bash",
            "python cbw_main.py --serve --serve-port 8080",
            "```",
            "",
            "## Regenerating Documentation",
            "",
            "To regenerate this documentation after adding/removing/modifying files:",
            "",
            "```bash",
            "python generate_docs.py",
            "```",
            "",
            "For detailed documentation, see [SCRIPT_EVALUATION.md](SCRIPT_EVALUATION.md).",
        ])
        
        return '\n'.join(lines)
    
    def generate_html_index(self) -> str:
        """Generate index.html content."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenGovt Repository - Script Browser</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .header .timestamp {{
            font-size: 0.9rem;
            opacity: 0.8;
            margin-top: 0.5rem;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .stat-card .number {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
            display: block;
        }}
        
        .stat-card .label {{
            color: #666;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }}
        
        .search-box {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 4px;
            transition: border-color 0.3s;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .category {{
            background: white;
            margin-bottom: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .category-header {{
            background: #f8f9fa;
            padding: 1rem 1.5rem;
            border-bottom: 2px solid #e0e0e0;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .category-header:hover {{
            background: #e9ecef;
        }}
        
        .category-header h2 {{
            font-size: 1.3rem;
            color: #333;
        }}
        
        .category-header .count {{
            background: #667eea;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.9rem;
        }}
        
        .category-content {{
            display: none;
        }}
        
        .category.expanded .category-content {{
            display: block;
        }}
        
        .file-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .file-table thead {{
            background: #f8f9fa;
        }}
        
        .file-table th {{
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            color: #555;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        .file-table td {{
            padding: 1rem;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .file-table tbody tr:hover {{
            background: #f8f9fa;
        }}
        
        .file-name {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        
        .file-name:hover {{
            text-decoration: underline;
        }}
        
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
            margin-right: 0.5rem;
        }}
        
        .badge-classes {{
            background: #e3f2fd;
            color: #1976d2;
        }}
        
        .badge-functions {{
            background: #f3e5f5;
            color: #7b1fa2;
        }}
        
        .expand-icon {{
            transition: transform 0.3s;
        }}
        
        .category.expanded .expand-icon {{
            transform: rotate(90deg);
        }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            color: #666;
            font-size: 0.9rem;
        }}
        
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏛️ OpenGovt Repository</h1>
        <p>Interactive Script Browser & Documentation</p>
        <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <span class="number">{len(self.python_files)}</span>
                <span class="label">Python Files</span>
            </div>
            <div class="stat-card">
                <span class="number">{sum(s['total_lines'] for s in self.file_stats.values()):,}</span>
                <span class="label">Lines of Code</span>
            </div>
            <div class="stat-card">
                <span class="number">{sum(len(s['classes']) for s in self.file_stats.values())}</span>
                <span class="label">Classes</span>
            </div>
            <div class="stat-card">
                <span class="number">{sum(len(s['functions']) for s in self.file_stats.values())}</span>
                <span class="label">Functions</span>
            </div>
        </div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="🔍 Search for files, classes, or functions..." onkeyup="filterFiles()">
        </div>
"""
        
        # Add categories
        for category, files in sorted(self.categories.items()):
            if not files:
                continue
            
            html += f"""
        <div class="category expanded" data-category="{category}">
            <div class="category-header" onclick="toggleCategory(this)">
                <h2><span class="expand-icon">▶</span> {category}</h2>
                <span class="count">{len(files)} files</span>
            </div>
            <div class="category-content">
                <table class="file-table">
                    <thead>
                        <tr>
                            <th>File</th>
                            <th>Lines</th>
                            <th>Classes</th>
                            <th>Functions</th>
                        </tr>
                    </thead>
                    <tbody>
"""
            
            for file_path in sorted(files):
                stats = self.file_stats[str(file_path)]
                class_list = ', '.join(stats['classes'][:5])
                if len(stats['classes']) > 5:
                    class_list += '...'
                func_list = ', '.join(stats['functions'][:5])
                if len(stats['functions']) > 5:
                    func_list += '...'
                
                html += f"""
                        <tr data-file="{file_path}" data-classes="{' '.join(stats['classes'])}" data-functions="{' '.join(stats['functions'])}">
                            <td>
                                <a href="#" class="file-name" onclick="return false;">{file_path}</a>
                            </td>
                            <td>{stats['total_lines']}</td>
                            <td>
                                <span class="badge badge-classes">{len(stats['classes'])} classes</span>
                                <br><small style="color: #666;">{class_list}</small>
                            </td>
                            <td>
                                <span class="badge badge-functions">{len(stats['functions'])} functions</span>
                                <br><small style="color: #666;">{func_list}</small>
                            </td>
                        </tr>
"""
            
            html += """
                    </tbody>
                </table>
            </div>
        </div>
"""
        
        html += """
    </div>
    
    <div class="footer">
        <p><strong>OpenGovt Repository</strong> - Government Data Analysis Framework</p>
        <p>See <a href="SCRIPT_EVALUATION.md">SCRIPT_EVALUATION.md</a> for comprehensive documentation</p>
        <p style="margin-top: 1rem; font-size: 0.85rem;">
            To regenerate this page: <code>python generate_docs.py</code>
        </p>
    </div>
    
    <script>
        function toggleCategory(element) {
            const category = element.parentElement;
            category.classList.toggle('expanded');
        }
        
        function filterFiles() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('.file-table tbody tr');
            
            rows.forEach(row => {
                const fileName = row.dataset.file.toLowerCase();
                const classes = row.dataset.classes.toLowerCase();
                const functions = row.dataset.functions.toLowerCase();
                
                if (fileName.includes(searchTerm) || 
                    classes.includes(searchTerm) || 
                    functions.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
            
            // Show/hide categories based on whether they have visible files
            document.querySelectorAll('.category').forEach(category => {
                const visibleRows = category.querySelectorAll('tbody tr:not([style*="display: none"])');
                if (visibleRows.length === 0 && searchTerm) {
                    category.style.display = 'none';
                } else {
                    category.style.display = '';
                }
            });
        }
        
        // Expand all categories by default
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('.category').forEach(cat => {
                cat.classList.add('expanded');
            });
        });
    </script>
</body>
</html>
"""
        
        return html


def main():
    """Main function to generate all documentation."""
    print("🔍 Scanning repository...")
    analyzer = RepoAnalyzer()
    analyzer.scan_repository()
    
    print(f"✅ Found {len(analyzer.python_files)} Python files")
    
    # Generate SCRIPT_INDEX.md
    print("📝 Generating SCRIPT_INDEX.md...")
    index_md = analyzer.generate_markdown_index()
    with open('SCRIPT_INDEX.md', 'w', encoding='utf-8') as f:
        f.write(index_md)
    print("✅ SCRIPT_INDEX.md generated")
    
    # Generate index.html
    print("🌐 Generating index.html...")
    index_html = analyzer.generate_html_index()
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("✅ index.html generated")
    
    print("\n✨ Documentation generation complete!")
    print("\n📚 Generated files:")
    print("   - SCRIPT_INDEX.md (Quick reference)")
    print("   - index.html (Interactive web view)")
    print("\n💡 To view the HTML page, open index.html in your browser")
    print("   Or run: python -m http.server 8000")
    print("   Then visit: http://localhost:8000/index.html")


if __name__ == '__main__':
    main()
