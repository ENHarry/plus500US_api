#!/usr/bin/env python3
"""
Build and Release Script for Plus500US SDK
Handles versioning, testing, building, and publishing to PyPI and GitHub.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Any
import re

class ReleaseManager:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.version_file = self.root_dir / "plus500us_client" / "__version__.py"
        
    def get_current_version(self) -> str:
        """Get current version from __version__.py"""
        if not self.version_file.exists():
            return "0.1.0"
            
        with open(self.version_file, 'r') as f:
            content = f.read()
            match = re.search(r'__version__ = [\'"]([^\'"]+)[\'"]', content)
            return match.group(1) if match else "0.1.0"
    
    def update_version(self, new_version: str):
        """Update version in __version__.py and pyproject.toml"""
        # Update __version__.py
        version_content = f'"""Version information for Plus500US SDK."""\n\n__version__ = "{new_version}"\n'
        with open(self.version_file, 'w') as f:
            f.write(version_content)
        
        # Update pyproject.toml
        pyproject_file = self.root_dir / "pyproject.toml"
        if pyproject_file.exists():
            with open(pyproject_file, 'r') as f:
                content = f.read()
            
            content = re.sub(
                r'version = "[^"]*"',
                f'version = "{new_version}"',
                content
            )
            
            with open(pyproject_file, 'w') as f:
                f.write(content)
        
        print(f"✅ Updated version to {new_version}")
    
    def run_tests(self) -> bool:
        """Run test suite"""
        print("🧪 Running test suite...")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/", "-v", "--tb=short",
                "-m", "unit or integration"
            ], cwd=self.root_dir, check=True, capture_output=True, text=True)
            
            print("✅ All tests passed!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Tests failed!")
            print(e.stdout)
            print(e.stderr)
            return False
    
    def build_package(self) -> bool:
        """Build wheel and sdist packages"""
        print("📦 Building package...")
        try:
            # Clean previous builds
            subprocess.run([sys.executable, "-m", "pip", "install", "build"], 
                         check=True, capture_output=True)
            
            # Remove old dist
            dist_dir = self.root_dir / "dist"
            if dist_dir.exists():
                import shutil
                shutil.rmtree(dist_dir)
            
            # Build
            subprocess.run([sys.executable, "-m", "build"], 
                         cwd=self.root_dir, check=True)
            
            print("✅ Package built successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            return False
    
    def create_git_tag(self, version: str):
        """Create git tag for release"""
        try:
            subprocess.run(["git", "add", "."], cwd=self.root_dir, check=True)
            subprocess.run(["git", "commit", "-m", f"Release v{version}"], 
                         cwd=self.root_dir, check=True)
            subprocess.run(["git", "tag", f"v{version}"], 
                         cwd=self.root_dir, check=True)
            
            print(f"✅ Created git tag v{version}")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Git operations failed: {e}")
    
    def publish_to_pypi(self, test: bool = True):
        """Publish package to PyPI"""
        repo = "--repository testpypi" if test else ""
        
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "twine"], 
                         check=True, capture_output=True)
            
            cmd = f"{sys.executable} -m twine upload {repo} dist/*"
            subprocess.run(cmd.split(), cwd=self.root_dir, check=True)
            
            target = "TestPyPI" if test else "PyPI"
            print(f"✅ Published to {target}!")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Publishing failed: {e}")
    
    def push_to_github(self):
        """Push commits and tags to GitHub"""
        try:
            subprocess.run(["git", "push"], cwd=self.root_dir, check=True)
            subprocess.run(["git", "push", "--tags"], cwd=self.root_dir, check=True)
            
            print("✅ Pushed to GitHub!")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ GitHub push failed: {e}")

def main():
    """Main release workflow"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Plus500US SDK Release Manager")
    parser.add_argument("action", choices=["build", "test", "release", "publish"], 
                       help="Action to perform")
    parser.add_argument("--version", help="New version number (for release)")
    parser.add_argument("--test-pypi", action="store_true", 
                       help="Use TestPyPI instead of PyPI")
    parser.add_argument("--skip-tests", action="store_true", 
                       help="Skip running tests")
    
    args = parser.parse_args()
    manager = ReleaseManager()
    
    if args.action == "test":
        success = manager.run_tests()
        sys.exit(0 if success else 1)
        
    elif args.action == "build":
        if not args.skip_tests:
            if not manager.run_tests():
                sys.exit(1)
        
        success = manager.build_package()
        sys.exit(0 if success else 1)
        
    elif args.action == "release":
        if not args.version:
            current = manager.get_current_version()
            print(f"Current version: {current}")
            print("Please specify --version for new release")
            sys.exit(1)
        
        # Full release workflow
        print(f"🚀 Starting release workflow for v{args.version}")
        
        # Update version
        manager.update_version(args.version)
        
        # Run tests
        if not args.skip_tests:
            if not manager.run_tests():
                sys.exit(1)
        
        # Build package
        if not manager.build_package():
            sys.exit(1)
        
        # Git operations
        manager.create_git_tag(args.version)
        
        print(f"✅ Release v{args.version} ready!")
        print("Next steps:")
        print("1. Review the changes")
        print("2. Run: python build_release.py publish")
        print("3. Push to GitHub: python build_release.py push")
        
    elif args.action == "publish":
        manager.publish_to_pypi(test=args.test_pypi)
        
    elif args.action == "push":
        manager.push_to_github()

if __name__ == "__main__":
    main()