#!/usr/bin/env python3
"""
Windows executable builder for Response Report Generator.

Usage:
    python scripts/build_windows.py
    
Requirements:
    - PyInstaller (pip install pyinstaller)
    
Output:
    - dist/ResponseReportGenerator/  (folder with executable)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def main():
    """Build Windows executable using PyInstaller."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("=" * 60)
    print("  Building Response Report Generator for Windows")
    print("=" * 60)
    
    try:
        import PyInstaller
        print(f"\n  PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("\n  PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
    
    for folder in ['build', 'dist']:
        folder_path = project_root / folder
        if folder_path.exists():
            print(f"  Cleaning {folder}/...")
            shutil.rmtree(folder_path)
    
    for folder in ['data', 'logs', 'exports']:
        folder_path = project_root / folder
        folder_path.mkdir(exist_ok=True)
        gitkeep = folder_path / '.gitkeep'
        gitkeep.touch(exist_ok=True)
    
    print("\n  Running PyInstaller...")
    spec_file = project_root / 'ResponseReportGenerator.spec'
    
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        str(spec_file),
        '--noconfirm'
    ], cwd=project_root)
    
    if result.returncode != 0:
        print("\n  ERROR: Build failed!")
        sys.exit(1)
    
    dist_folder = project_root / 'dist' / 'ResponseReportGenerator'
    if dist_folder.exists():
        print("\n" + "=" * 60)
        print("  BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"\n  Output: {dist_folder}")
        print("\n  To run the application:")
        print("    1. Navigate to dist/ResponseReportGenerator/")
        print("    2. Double-click ResponseReportGenerator.exe")
        print("\n  To distribute:")
        print("    1. Zip the entire dist/ResponseReportGenerator/ folder")
        print("    2. Users extract and run the .exe")
        
        env_example = project_root / '.env.example'
        if env_example.exists():
            shutil.copy(env_example, dist_folder / '.env.example')
            print("\n  Copied .env.example to distribution folder")
    else:
        print("\n  ERROR: dist folder not found after build!")
        sys.exit(1)


if __name__ == '__main__':
    main()
