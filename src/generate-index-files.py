#!/usr/bin/env python3
"""
Generate index.html files for a directory tree of PDFs using metadata from SQLite.

This script recursively walks through a directory structure, creates an index.html
file in each directory that lists PDFs with their metadata (title, authors) from
a SQLite database, and adds navigation links to parent and child directories.

Uses Jinja2 for HTML templating and Bootstrap for responsive, attractive styling.
"""

import os
import sqlite3
import argparse
from pathlib import Path
import html
from jinja2 import Environment, FileSystemLoader, Template


# Jinja2 template for index.html with Bootstrap styling
INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Index of {{ directory_name }}</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        .directory-icon { color: #ffc107; }
        .pdf-icon { color: #dc3545; }
        .card { transition: transform .2s; }
        .card:hover { transform: scale(1.02); }
        .breadcrumb-item+.breadcrumb-item::before {
            content: ">";
        }
    </style>
</head>
<body>
    <div class="container my-4">
        <!-- Header -->
        <div class="row mb-4">
            <div class="col">
                <h1 class="display-4">
                    {% if is_root %}
                        <i class="fas fa-home me-2"></i> PDF Document Root
                    {% else %}
                        <i class="fas fa-folder-open me-2"></i> {{ directory_name }}
                    {% endif %}
                </h1>
                
                <!-- Breadcrumb navigation -->
                <nav aria-label="breadcrumb">
                    <ol class="breadcrumb">
                        <li class="breadcrumb-item"><a href="{{ server_url }}"><i class="fas fa-home"></i> Home</a></li>
                        {% if not is_root %}
                            {% set path_parts = directory_name.split('/') %}
                            {% set current_path = '' %}
                            {% for part in path_parts %}
                                {% set current_path = current_path + '/' + part if current_path else part %}
                                {% if loop.last %}
                                    <li class="breadcrumb-item active" aria-current="page">{{ part }}</li>
                                {% else %}
                                    <li class="breadcrumb-item"><a href="{{ server_url }}/{{ current_path }}">{{ part }}</a></li>
                                {% endif %}
                            {% endfor %}
                        {% endif %}
                    </ol>
                </nav>
            </div>
        </div>
        
        <!-- Parent directory link -->
        {% if parent_url %}
        <div class="row mb-4">
            <div class="col">
                <a href="{{ parent_url }}" class="btn btn-outline-secondary">
                    <i class="fas fa-arrow-left"></i> Parent Directory
                </a>
            </div>
        </div>
        {% endif %}
        
        <!-- Directories section -->
        {% if directories %}
        <div class="row mb-4">
            <div class="col">
                <h2><i class="fas fa-folder me-2"></i> Directories</h2>
                <div class="row row-cols-1 row-cols-md-3 g-4">
                    {% for dir in directories %}
                    <div class="col">
                        <div class="card h-100 shadow-sm">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="fas fa-folder directory-icon me-2"></i>
                                    <a href="{{ dir.url }}" class="text-decoration-none">{{ dir.name }}/</a>
                                </h5>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endif %}
        
        <!-- PDF files section -->
        {% if pdf_files %}
        <div class="row">
            <div class="col">
                <h2><i class="fas fa-file-pdf me-2"></i> PDF Files</h2>
                <div class="table-responsive">
                    <table class="table table-hover">
                        <colgroup>
                            <col style="width: 15%;">
                            <col style="width: 50%;">
                            <col style="width: 30%;">
                            <col style="width: 5%;">
                        </colgroup>
                        <thead class="table-light">
                            <tr>
                                <th>File Name</th>
                                <th>Title</th>
                                <th>Authors</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for pdf in pdf_files %}
                            <tr>
                                <td class="text-truncate" style="max-width: 150px;">
                                    <i class="fas fa-file-pdf pdf-icon me-2"></i>
                                    <a href="{{ pdf.url }}" class="text-decoration-none" title="{{ pdf.filename }}">{{ pdf.filename }}</a>
                                </td>
                                <td>{{ pdf.title }}</td>
                                <td>{{ pdf.authors }}</td>
                                <td class="text-center">
                                    <a href="{{ pdf.url }}" class="btn btn-sm btn-primary" title="Download">
                                        <i class="fas fa-download"></i>
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% else %}
        <div class="row">
            <div class="col">
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i> No PDF files in this directory.
                </div>
            </div>
        </div>
        {% endif %}
        
        <!-- Footer -->
        <footer class="mt-5 mb-3 text-center text-muted">
            <small>Generated on {{ generation_date }}</small>
        </footer>
    </div>
    
    <!-- Bootstrap JS Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


def create_index_files(root_dir, db_path, server_url_prefix, original_path_prefix=None):
    """
    Create index.html files for each directory in the tree.
    
    Args:
        root_dir: The root directory of the PDF collection
        db_path: Path to the SQLite database
        server_url_prefix: URL prefix for accessing files (e.g., 'http://raspberrypi.local/')
        original_path_prefix: Prefix in the database paths that should be replaced with root_dir
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all PDF entries from the database
    cursor.execute("SELECT path, title, authors FROM pdf_info")
    pdf_entries = cursor.fetchall()
    
    # Create a dictionary to store metadata by path
    pdf_metadata = {}
    for path, title, authors in pdf_entries:
        if original_path_prefix and path.startswith(original_path_prefix):
            # Convert original path to local path
            relative_path = path[len(original_path_prefix):].lstrip('/')
            local_path = os.path.join(root_dir, relative_path)
            pdf_metadata[local_path] = {
                'title': title if title else "No Title",
                'authors': authors if authors else "Unknown"
            }
        else:
            # If no prefix mapping, use path as is
            pdf_metadata[path] = {
                'title': title if title else "No Title",
                'authors': authors if authors else "Unknown"
            }
    
    # Close the database connection
    conn.close()
    
    # Create Jinja2 template
    template = Template(INDEX_TEMPLATE)
    
    # Walk the directory tree and create index files
    for dirpath, dirnames, filenames in os.walk(root_dir):
        create_index_for_directory(
            dirpath, dirnames, filenames,
            pdf_metadata, root_dir, server_url_prefix, template
        )


def create_index_for_directory(dirpath, dirnames, filenames, pdf_metadata, root_dir, server_url_prefix, template):
    """Create an index.html file for a single directory using Jinja2 template with Bootstrap styling."""
    import datetime
    
    index_path = os.path.join(dirpath, "index.html")
    
    # Get relative path from root for navigation
    rel_path = os.path.relpath(dirpath, root_dir)
    is_root = (rel_path == '.')
    directory_name = "Root" if is_root else rel_path
    
    parent_path = os.path.dirname(rel_path) if rel_path != '.' else None
    parent_url = f'{server_url_prefix}/{parent_path}' if parent_path else None
    
    # Filter for PDF files and prepare data for template
    pdf_files = []
    for filename in sorted([f for f in filenames if f.lower().endswith('.pdf')]):
        pdf_path = os.path.join(dirpath, filename)
        metadata = pdf_metadata.get(pdf_path, {'title': 'No Title', 'authors': 'Unknown'})
        
        # Create file URL
        if is_root:
            file_url = f'{server_url_prefix}/{filename}'
        else:
            file_url = f'{server_url_prefix}/{rel_path}/{filename}'
        
        pdf_files.append({
            'filename': html.escape(filename),
            'url': file_url,
            'title': html.escape(metadata['title']),
            'authors': html.escape(metadata['authors'])
        })
    
    # Prepare directory data
    directories = []
    for dirname in sorted(dirnames):
        # Skip hidden directories
        if dirname.startswith('.'):
            continue
            
        # Create subdirectory URL
        if is_root:
            subdir_url = f'{server_url_prefix}/{dirname}'
        else:
            subdir_url = f'{server_url_prefix}/{rel_path}/{dirname}'
        
        directories.append({
            'name': html.escape(dirname),
            'url': subdir_url
        })
    
    # Get current date/time for footer
    generation_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Render the template
    html_content = template.render(
        is_root=is_root,
        directory_name=directory_name,
        server_url=server_url_prefix,
        parent_url=parent_url,
        directories=directories,
        pdf_files=pdf_files,
        generation_date=generation_date
    )
    
    # Write the index.html file
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Created index.html in {dirpath}")


def main():
    parser = argparse.ArgumentParser(description='Generate index.html files for a PDF directory tree')
    parser.add_argument('--root', required=True, help='Root directory of the PDF collection')
    parser.add_argument('--db', required=True, help='Path to the SQLite database')
    parser.add_argument('--url', required=True, help='URL prefix for accessing files (e.g., "http://raspberrypi.local")')
    parser.add_argument('--original-prefix', help='Original path prefix in the database to be replaced')
    parser.add_argument('--template', help='Path to custom Jinja2 template file (optional)')
    
    args = parser.parse_args()
    
    # If a custom template file is provided, use it instead of the default
    global INDEX_TEMPLATE
    if args.template:
        with open(args.template, 'r', encoding='utf-8') as f:
            INDEX_TEMPLATE = f.read()
    
    create_index_files(
        args.root, 
        args.db,
        args.url,
        args.original_prefix
    )
    
    print("Index generation complete!")


if __name__ == "__main__":
    main()
