#!/usr/bin/env python3
"""
Development Artifacts Cleanup Script (Conservative)
===================================================

Removes temporary files and development artifacts while preserving:
- scraped_data/ (network capture data for endpoint verification)
- screenshots/ (debugging reference for WebDriver automation)
- session_backup/ (session analysis data)
- endpoint_analysis_and_extraction.md (API documentation)

This conservative cleanup keeps data needed for live testing validation.
After successful live testing, run with --aggressive flag for full cleanup.
"""

import os
import shutil
from pathlib import Path

def cleanup_artifacts():
    """Clean up development artifacts and temporary files"""
    
    base_dir = Path(__file__).parent
    
    # Directories to remove completely
    dirs_to_remove = [
        "__pycache__",
        ".pytest_cache", 
        # "scraped_data",  # Keep for live test verification
        # "screenshots",   # Keep for debugging reference
        # "session_backup", # Keep for session analysis
        ".trees",
        "plus500us_client.egg-info"
    ]
    
    # File patterns to remove (conservative cleanup - keep network/endpoint data)
    files_to_remove = [
        "*.pyc",
        "*.pyo", 
        "*.pyd",
        "*.so",
        "*.egg",
        ".DS_Store",
        "Thumbs.db",
        "*.log",
        "*.tmp",
        "*.backup",
        "*.bak",
        "*.orig",
        "PHASE*.md",
        "IMPLEMENTATION*.md", 
        "AUTHENTICATION*.md",
        "ITERATION*.md",
        "CLAUDE.*.md",
        "consolidation_plan.md",
        # "endpoint_analysis_and_extraction.md",  # Keep for endpoint verification
        "implementation_status.md",
        "phase3_completion_summary.py",
        "PRODUCTION_ADJUSTMENTS.py",
        "merge_validation.py",
        "*_todo.md",
        "*_github_issues.md",
        "*_enhancement*.md"
    ]
    
    print("🧹 Cleaning up development artifacts...")
    
    removed_dirs = 0
    removed_files = 0
    
    # Remove directories
    for dir_pattern in dirs_to_remove:
        for dir_path in base_dir.rglob(dir_pattern):
            if dir_path.is_dir():
                print(f"📁 Removing directory: {dir_path.relative_to(base_dir)}")
                shutil.rmtree(dir_path)
                removed_dirs += 1
    
    # Remove files
    for file_pattern in files_to_remove:
        for file_path in base_dir.rglob(file_pattern):
            if file_path.is_file():
                print(f"🗑️  Removing file: {file_path.relative_to(base_dir)}")
                file_path.unlink()
                removed_files += 1
    
    print(f"\n✅ Cleanup complete!")
    print(f"   Directories removed: {removed_dirs}")
    print(f"   Files removed: {removed_files}")
    
    # Show final clean structure
    print("\n📊 Clean project structure:")
    for item in sorted(base_dir.iterdir()):
        if not item.name.startswith('.'):
            if item.is_dir():
                print(f"   📁 {item.name}/")
            else:
                print(f"   📄 {item.name}")

if __name__ == "__main__":
    cleanup_artifacts()