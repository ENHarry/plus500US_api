#!/usr/bin/env python3
"""
Plus500US SDK - Publication Readiness Validator
Checks all components are ready for GitHub publication and PyPI release.
"""

import os
import sys
from pathlib import Path
import subprocess
import json
from typing import List, Dict, Tuple

class PublicationValidator:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.success: List[str] = []
        
    def check_file_structure(self) -> bool:
        """Validate essential file structure"""
        required_files = [
            "README.md",
            "pyproject.toml", 
            "LICENSE",
            "plus500us_client/__init__.py",
            "plus500us_client/__version__.py",
            "docs/README.md",
            "docs/guides/installation.md",
            "docs/guides/quickstart.md",
            "examples/README.md",
            "tests/test_complete_workflow.py",
            ".github/workflows/ci-cd.yml",
            "build_release.py",
            "Dockerfile"
        ]
        
        required_dirs = [
            "plus500us_client/",
            "docs/guides/", 
            "examples/",
            "tests/",
            ".github/workflows/"
        ]
        
        missing_files = []
        missing_dirs = []
        
        for file_path in required_files:
            if not (self.root_dir / file_path).exists():
                missing_files.append(file_path)
                
        for dir_path in required_dirs:
            if not (self.root_dir / dir_path).exists():
                missing_dirs.append(dir_path)
        
        if missing_files:
            self.issues.extend([f"Missing file: {f}" for f in missing_files])
            
        if missing_dirs:
            self.issues.extend([f"Missing directory: {d}" for d in missing_dirs])
            
        if not missing_files and not missing_dirs:
            self.success.append("✅ File structure complete")
            return True
            
        return False
    
    def check_version_consistency(self) -> bool:
        """Check version numbers are consistent"""
        try:
            # Get version from __version__.py
            version_file = self.root_dir / "plus500us_client" / "__version__.py"
            if not version_file.exists():
                self.issues.append("Missing __version__.py")
                return False
                
            with open(version_file) as f:
                content = f.read()
                
            import re
            match = re.search(r'__version__ = [\'"]([^\'"]+)[\'"]', content)
            if not match:
                self.issues.append("Invalid version format in __version__.py")
                return False
                
            py_version = match.group(1)
            
            # Check pyproject.toml version
            pyproject_file = self.root_dir / "pyproject.toml"
            if not pyproject_file.exists():
                self.issues.append("Missing pyproject.toml")
                return False
                
            with open(pyproject_file) as f:
                content = f.read()
                
            match = re.search(r'version = "([^"]+)"', content)
            if not match:
                self.issues.append("Invalid version format in pyproject.toml")
                return False
                
            toml_version = match.group(1)
            
            if py_version != toml_version:
                self.issues.append(f"Version mismatch: __version__.py={py_version}, pyproject.toml={toml_version}")
                return False
                
            self.success.append(f"✅ Version consistency: v{py_version}")
            return True
            
        except Exception as e:
            self.issues.append(f"Version check error: {e}")
            return False
    
    def check_documentation(self) -> bool:
        """Validate documentation completeness"""
        docs_files = [
            ("README.md", ["installation", "quickstart", "examples", "architecture"]),
            ("docs/guides/installation.md", ["prerequisites", "webdriver", "environment"]),
            ("docs/guides/quickstart.md", ["first", "trade", "configuration"]),
            ("examples/README.md", ["webdriver_login", "webdriver_trading", "complete_workflow"])
        ]
        
        all_good = True
        
        for file_path, required_content in docs_files:
            full_path = self.root_dir / file_path
            
            if not full_path.exists():
                self.issues.append(f"Missing documentation: {file_path}")
                all_good = False
                continue
                
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                
            missing_content = [item for item in required_content if item.lower() not in content]
            
            if missing_content:
                self.warnings.append(f"Missing content in {file_path}: {missing_content}")
            else:
                self.success.append(f"✅ Documentation complete: {file_path}")
        
        return all_good
    
    def check_test_structure(self) -> bool:
        """Validate test organization"""
        test_files = [
            "tests/test_complete_workflow.py",
            "tests/test_authentication_complete.py", 
            "tests/test_browser_verification.py",
            "tests/test_core_functions.py"
        ]
        
        missing_tests = []
        for test_file in test_files:
            if not (self.root_dir / test_file).exists():
                missing_tests.append(test_file)
        
        if missing_tests:
            self.warnings.extend([f"Missing test file: {t}" for t in missing_tests])
        
        # Check for old scattered test files (should be cleaned up)
        root_test_files = list(self.root_dir.glob("test_*.py"))
        if root_test_files:
            self.warnings.append(f"Found {len(root_test_files)} test files in root (should be in tests/)")
        
        self.success.append(f"✅ Test structure organized")
        return True
    
    def check_dependencies(self) -> bool:
        """Check if all dependencies are properly specified"""
        try:
            pyproject = self.root_dir / "pyproject.toml"
            with open(pyproject) as f:
                content = f.read()
            
            required_deps = [
                "requests", "pydantic", "tenacity", "selenium", 
                "webdriver-manager", "undetected-chromedriver"
            ]
            
            missing_deps = []
            for dep in required_deps:
                if dep not in content:
                    missing_deps.append(dep)
            
            if missing_deps:
                self.issues.extend([f"Missing dependency: {dep}" for dep in missing_deps])
                return False
            
            self.success.append("✅ Dependencies complete")
            return True
            
        except Exception as e:
            self.issues.append(f"Dependency check error: {e}")
            return False
    
    def check_git_readiness(self) -> bool:
        """Check git configuration"""
        try:
            # Check if git is initialized
            if not (self.root_dir / ".git").exists():
                self.warnings.append("Git not initialized (run: git init)")
                return False
            
            # Check for gitignore
            gitignore = self.root_dir / ".gitignore"
            if not gitignore.exists():
                self.warnings.append("Missing .gitignore file")
            else:
                with open(gitignore) as f:
                    content = f.read()
                if "__pycache__" not in content:
                    self.warnings.append(".gitignore missing __pycache__")
            
            # Check if there are uncommitted changes
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True, cwd=self.root_dir)
            
            if result.stdout.strip():
                self.warnings.append("Uncommitted changes detected")
            
            self.success.append("✅ Git repository ready")
            return True
            
        except Exception as e:
            self.warnings.append(f"Git check failed: {e}")
            return False
    
    def check_build_readiness(self) -> bool:
        """Test package build"""
        try:
            # Check if build module is available
            subprocess.run([sys.executable, "-c", "import build"], 
                         check=True, capture_output=True)
            
            self.success.append("✅ Build tools available")
            return True
            
        except subprocess.CalledProcessError:
            self.warnings.append("Build module not installed (pip install build)")
            return False
        except Exception as e:
            self.issues.append(f"Build check error: {e}")
            return False
    
    def generate_report(self) -> Dict:
        """Generate comprehensive readiness report"""
        checks = [
            ("File Structure", self.check_file_structure),
            ("Version Consistency", self.check_version_consistency), 
            ("Documentation", self.check_documentation),
            ("Test Structure", self.check_test_structure),
            ("Dependencies", self.check_dependencies),
            ("Git Readiness", self.check_git_readiness),
            ("Build Readiness", self.check_build_readiness)
        ]
        
        results = {}
        all_passed = True
        
        print("🔍 Plus500US SDK Publication Readiness Check\n")
        print("=" * 50)
        
        for check_name, check_func in checks:
            print(f"\n📋 {check_name}...")
            try:
                passed = check_func()
                results[check_name] = "PASS" if passed else "FAIL"
                if not passed:
                    all_passed = False
            except Exception as e:
                results[check_name] = "ERROR"
                self.issues.append(f"{check_name} check failed: {e}")
                all_passed = False
        
        # Print results
        print("\n" + "=" * 50)
        print("\n📊 RESULTS SUMMARY:")
        
        if self.success:
            print(f"\n✅ SUCCESS ({len(self.success)} items):")
            for item in self.success:
                print(f"  {item}")
        
        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)} items):")
            for item in self.warnings:
                print(f"  {item}")
        
        if self.issues:
            print(f"\n❌ ISSUES ({len(self.issues)} items):")
            for item in self.issues:
                print(f"  {item}")
        
        print("\n" + "=" * 50)
        
        if all_passed and not self.issues:
            print("🎉 PUBLICATION READY!")
            print("\nNext steps:")
            print("1. Create GitHub repository")
            print("2. Update URLs in pyproject.toml")
            print("3. Set up GitHub secrets (PYPI_TOKEN, etc.)")
            print("4. Run: git push origin main --tags")
            print("5. Create first release on GitHub")
        else:
            print("🔧 FIX ISSUES BEFORE PUBLICATION")
            print("\nRun this script again after fixes.")
        
        return {
            "ready": all_passed and not self.issues,
            "results": results,
            "issues": self.issues,
            "warnings": self.warnings,
            "success": self.success
        }

def main():
    """Main validation workflow"""
    validator = PublicationValidator()
    report = validator.generate_report()
    
    # Save report
    report_file = Path(__file__).parent / "publication_readiness_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Report saved: {report_file}")
    
    # Exit code
    sys.exit(0 if report["ready"] else 1)

if __name__ == "__main__":
    main()