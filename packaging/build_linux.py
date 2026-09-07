"""
SAP-net Visualizer Full-Auto Clean Build Script for Linux / WSL2
Creates a clean temporary virtual environment, installs minimal dependencies,
builds the standalone Linux binary using PyInstaller, generates desktop integration files,
and bundles everything into a portable tar.gz archive.
"""
import os
import sys
import shutil
import stat
import subprocess
import time
import tempfile
import tarfile
from pathlib import Path


def safe_rmtree(path, retries=5, delay=0.5):
    """堅牢なディレクトリ削除ハンドラ"""
    p = Path(path)
    if not p.exists():
        return

    for attempt in range(retries):
        try:
            shutil.rmtree(p, ignore_errors=True)
            if not p.exists():
                return
        except Exception:
            pass
        time.sleep(delay)


def get_app_version(root_dir: Path) -> str:
    """sap_visualizer/__init__.py または constants.py からバージョン番号を動的抽出"""
    init_file = root_dir / "sap_visualizer" / "__init__.py"
    if init_file.exists():
        try:
            with open(init_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "__version__" in line and '"' in line:
                        return line.split('"')[1]
                    elif "__version__" in line and "'" in line:
                        return line.split("'")[1]
        except Exception:
            pass

    constants_file = root_dir / "sap_visualizer" / "constants.py"
    if constants_file.exists():
        try:
            with open(constants_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "APP_VERSION" in line and '"' in line:
                        return line.split('"')[1]
                    elif "APP_VERSION" in line and "'" in line:
                        return line.split("'")[1]
        except Exception:
            pass

    return "1.0.0"


def create_desktop_entry(target_dir: Path):
    """デスクトップエントリーファイル (.desktop) を生成"""
    desktop_content = """[Desktop Entry]
Type=Application
Name=SAP-net Visualizer
GenericName=SAP-net Simulation Visualizer
Comment=Interactive dynamic parameter visualizer for SAP-net reinforcement learning
Exec=sh -c '"$(dirname "$0")/SAP-net-Visualizer"'
Icon=packaging/app_icon.ico
Terminal=false
Categories=Science;Education;Development;
"""
    desktop_file = target_dir / "SAP-net-Visualizer.desktop"
    with open(desktop_file, "w", encoding="utf-8") as f:
        f.write(desktop_content)
    try:
        desktop_file.chmod(desktop_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def create_launcher_script(target_dir: Path):
    """ポータブル起動用シェルスクリプト (run.sh) を生成"""
    launcher_content = """#!/usr/bin/env bash
# SAP-net Visualizer ポータブル起動ランチャー
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 音声デバイス未検出環境（WSL/サーバー等）での警告抑制
if [ -z "$SDL_AUDIODRIVER" ]; then
    export SDL_AUDIODRIVER=dummy
fi

# アプリケーションバイナリの実行
exec "$SCRIPT_DIR/SAP-net-Visualizer" "$@"
"""
    launcher_file = target_dir / "run.sh"
    with open(launcher_file, "w", encoding="utf-8") as f:
        f.write(launcher_content)
    try:
        launcher_file.chmod(launcher_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def main():
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)

    print("=" * 60)
    print("  SAP-net Visualizer Linux Standalone Build Script")
    print("=" * 60)

    app_version = get_app_version(root_dir)
    print(f"[INFO] Target Application Version: v{app_version}")

    temp_base = Path(tempfile.gettempdir())
    venv_dir = temp_base / "sap_visualizer_linux_build_venv"
    build_dir = temp_base / "sap_visualizer_linux_build_work"

    dist_dir = root_dir / "dist"
    target_output_dir = dist_dir / "SAP-net-Visualizer-linux"
    requirements_file = root_dir / "requirements.txt"
    spec_file = root_dir / "packaging" / "SAP-net-Visualizer-linux.spec"

    # 1. Clean previous build virtual environment and output directories
    print("[1/4] Cleaning previous build artifacts and creating clean virtual environment...")
    safe_rmtree(venv_dir)
    safe_rmtree(build_dir)
    safe_rmtree(target_output_dir)

    try:
        subprocess.run([sys.executable, "-m", "venv", "--clear", str(venv_dir)], check=True)
    except Exception as e:
        print(f"[ERROR] Failed to create virtual environment: {e}")
        return 1

    venv_python = venv_dir / "bin" / "python3"
    venv_pip = venv_dir / "bin" / "pip"
    venv_pyinstaller = venv_dir / "bin" / "pyinstaller"

    if not venv_python.exists():
        # Windows上の仮想環境互換（Scripts/）
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
        venv_pyinstaller = venv_dir / "Scripts" / "pyinstaller.exe"

    # 2. Install dependencies
    print("[2/4] Installing minimal dependencies from requirements.txt...")
    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=False)
        subprocess.run([str(venv_pip), "install", "-r", str(requirements_file)], check=True)
    except Exception as e:
        print(f"[ERROR] Failed to install dependencies: {e}")
        safe_rmtree(venv_dir)
        return 1

    # 3. Build standalone binary with PyInstaller
    print("[3/4] Building standalone binary with PyInstaller...")
    try:
        subprocess.run(
            [
                str(venv_pyinstaller),
                "--noconfirm",
                "--workpath", str(build_dir),
                "--distpath", str(dist_dir),
                str(spec_file)
            ],
            check=True
        )
        print("[INFO] PyInstaller standalone binary created successfully.")
    except Exception as e:
        print(f"[ERROR] PyInstaller build failed: {e}")
        safe_rmtree(venv_dir)
        safe_rmtree(build_dir)
        return 1

    # dist/SAP-net-Visualizer を dist/SAP-net-Visualizer-linux にリネームまたは整理
    source_dir = dist_dir / "SAP-net-Visualizer"
    if source_dir.exists() and source_dir != target_output_dir:
        safe_rmtree(target_output_dir)
        source_dir.rename(target_output_dir)

    # 4. Generate integration files and tar.gz archive
    print("[4/4] Creating launcher script, desktop entry, and distribution tar.gz...")
    if target_output_dir.exists():
        create_launcher_script(target_output_dir)
        create_desktop_entry(target_output_dir)

        # 実行権限を付与
        binary_path = target_output_dir / "SAP-net-Visualizer"
        if binary_path.exists():
            try:
                binary_path.chmod(binary_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception:
                pass

        # tar.gz アーカイブ作成
        archive_name = f"SAP-net-Visualizer-linux-v{app_version}.tar.gz"
        archive_path = dist_dir / archive_name
        print(f"[INFO] Compressing standalone bundle into: {archive_path}")
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(target_output_dir, arcname="SAP-net-Visualizer")

    # Clean up build cache
    safe_rmtree(venv_dir)
    safe_rmtree(build_dir)

    print("=" * 60)
    print("  LINUX BUILD PROCESS FINISHED!")
    if target_output_dir.exists():
        print(f"  [SUCCESS] Standalone Directory : {target_output_dir}")
    if (dist_dir / f"SAP-net-Visualizer-linux-v{app_version}.tar.gz").exists():
        print(f"  [SUCCESS] Portable Archive    : {dist_dir / f'SAP-net-Visualizer-linux-v{app_version}.tar.gz'}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
