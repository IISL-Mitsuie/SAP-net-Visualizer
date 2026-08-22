"""
SAP-net Visualizer Full-Auto Clean Build Script
Creates a clean temporary virtual environment, installs minimal dependencies,
builds the PyInstaller binary, compiles the Inno Setup installer,
and cleans up all temporary build environments.
"""
import os
import sys
import shutil
import subprocess
import time
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)

    print("=" * 60)
    print("  SAP-net Visualizer Full-Auto Clean Build Script")
    print("=" * 60)

    venv_dir = root_dir / ".venv_build"
    build_dir = root_dir / "build"
    dist_dir = root_dir / "dist"
    installer_output_dir = root_dir / "dist_installer"
    requirements_file = root_dir / "requirements.txt"
    spec_file = root_dir / "packaging" / "SAP-net-Visualizer.spec"
    iss_file = root_dir / "packaging" / "installer.iss"

    # 1. Clean previous build virtual environment
    print("[1/5] Creating clean temporary virtual environment (.venv_build)...")
    if venv_dir.exists():
        shutil.rmtree(venv_dir, ignore_errors=True)
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    except Exception as e:
        print(f"[ERROR] Failed to create virtual environment: {e}")
        return 1

    venv_python = venv_dir / "Scripts" / "python.exe"
    venv_pip = venv_dir / "Scripts" / "pip.exe"
    venv_pyinstaller = venv_dir / "Scripts" / "pyinstaller.exe"

    # 2. Install dependencies
    print("[2/5] Installing minimal dependencies from requirements.txt...")
    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=False)
        subprocess.run([str(venv_pip), "install", "-r", str(requirements_file)], check=True)
    except Exception as e:
        print(f"[ERROR] Failed to install dependencies: {e}")
        shutil.rmtree(venv_dir, ignore_errors=True)
        return 1

    # 3. Build standalone binary with PyInstaller
    print("[3/5] Building standalone binary with PyInstaller...")
    try:
        subprocess.run([str(venv_pyinstaller), "--noconfirm", str(spec_file)], check=True)
        print("[INFO] PyInstaller standalone binary created successfully.")
    except Exception as e:
        print(f"[ERROR] PyInstaller build failed: {e}")
        shutil.rmtree(venv_dir, ignore_errors=True)
        return 1

    # 4. Search Inno Setup and compile installer
    print("[4/5] Compiling Windows Setup Installer with Inno Setup...")
    iscc_candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    iscc_path = None
    for cand in iscc_candidates:
        if cand.exists():
            iscc_path = cand
            break

    if iscc_path and iss_file.exists():
        print(f"[INFO] Running Inno Setup compiler: {iscc_path}")
        res = subprocess.run([str(iscc_path), str(iss_file)])
        if res.returncode == 0:
            print("[INFO] Inno Setup installer compiled successfully!")
        else:
            print("[ERROR] Inno Setup compilation failed.")
    else:
        if not iscc_path:
            print("[WARNING] Inno Setup compiler (ISCC.exe) not found.")
            print("[INFO] To create installer, install Inno Setup 6 from: https://jrsoftware.org/isdl.php")
        if not iss_file.exists():
            print(f"[ERROR] Inno Setup script not found: {iss_file}")

    # 5. Clean up temporary virtual environment and build cache
    print("[5/5] Cleaning up temporary build environment (.venv_build and build/)...")
    time.sleep(1)
    if venv_dir.exists():
        shutil.rmtree(venv_dir, ignore_errors=True)
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    print("=" * 60)
    print("  BUILD PROCESS FINISHED!")
    
    # installer.iss からバージョン番号を動的抽出
    app_version = "1.0.1"
    if iss_file.exists():
        try:
            with open(iss_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "MyAppVersion" in line and '"' in line:
                        app_version = line.split('"')[1]
                        break
        except Exception:
            pass

    setup_exe = installer_output_dir / f"SAP_net_Visualizer_Setup_v{app_version}.exe"
    if setup_exe.exists():
        print(f"  [SUCCESS] Windows Installer: {setup_exe}")
    standalone_exe = dist_dir / "SAP-net-Visualizer" / "SAP-net-Visualizer.exe"
    if standalone_exe.exists():
        print(f"  [SUCCESS] Standalone Binary: {standalone_exe}")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
