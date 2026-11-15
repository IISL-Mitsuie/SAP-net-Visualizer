"""
SAP-net Visualizer Full-Auto Clean Build Script
Creates a clean temporary virtual environment, installs minimal dependencies,
builds the PyInstaller binary, compiles the Inno Setup installer,
and cleans up all temporary build environments.
"""
import argparse
import os
import re
import shutil
import stat
import string
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

APP_VERSION_PATTERN = re.compile(r'^APP_VERSION\s*=\s*["\'](\d+\.\d+\.\d+)["\']', re.MULTILINE)


def read_app_version(constants_path: Optional[Path] = None) -> str:
    """sap_visualizer/constants.py から APP_VERSION (MAJOR.MINOR.PATCH) を取得する"""
    if constants_path is None:
        constants_path = Path(__file__).resolve().parent.parent / "sap_visualizer" / "constants.py"
    text = Path(constants_path).read_text(encoding="utf-8")
    match = APP_VERSION_PATTERN.search(text)
    if not match:
        raise ValueError(f"Could not extract APP_VERSION from {constants_path}")
    return match.group(1)


def render_version_info(
    version: str,
    output_path: Path,
    template_path: Optional[Path] = None,
) -> Path:
    """version_info.template.txt にバージョン情報を展開して出力する"""
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid semantic version format: {version!r}")
    major, minor, patch = parts

    if template_path is None:
        template_path = Path(__file__).resolve().parent / "version_info.template.txt"

    template_text = Path(template_path).read_text(encoding="utf-8")
    rendered = string.Template(template_text).substitute(
        MAJOR=major,
        MINOR=minor,
        PATCH=patch,
        VERSION=version,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def run_prebuild_tests(root_dir: Path) -> bool:
    """ビルド前に pytest を実行し、全テスト通過時のみ True を返す"""
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    env.setdefault("PYTHONUTF8", "1")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(root_dir),
        env=env,
        check=False,
    )
    return result.returncode == 0


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SAP-net Visualizer Clean Build Script")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pre-build pytest execution",
    )
    return parser.parse_args(argv)


def remove_readonly(func, path, excinfo):
    """Windowsの読み取り専用属性を強制解除して削除を再試行するハンドラ"""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def safe_rmtree(path, retries=5, delay=0.5):
    """
    Windows環境のファイルロックや読み取り専用属性に対応した堅牢なディレクトリ削除
    """
    p = Path(path)
    if not p.exists():
        return

    for attempt in range(retries):
        try:
            if sys.version_info >= (3, 12):
                def _onexc(func, filepath, err):
                    try:
                        os.chmod(filepath, stat.S_IWRITE)
                        func(filepath)
                    except Exception:
                        pass
                shutil.rmtree(p, onexc=_onexc)
            else:
                shutil.rmtree(p, onerror=remove_readonly)

            if not p.exists():
                return
        except Exception:
            pass
        time.sleep(delay)

    if p.exists():
        try:
            shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass


def kill_existing_process():
    """実行中の SAP-net-Visualizer.exe プロセスがあれば安全に終了"""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "SAP-net-Visualizer.exe", "/T"],
            capture_output=True,
            check=False
        )
    except Exception:
        pass


def main(argv=None):
    args = parse_args(argv)
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)

    print("=" * 60)
    print("  SAP-net Visualizer Full-Auto Clean Build Script")
    print("=" * 60)

    try:
        app_version = read_app_version(root_dir / "sap_visualizer" / "constants.py")
    except Exception as e:
        print(f"[ERROR] Failed to read APP_VERSION: {e}")
        return 1
    print(f"[INFO] Target version: {app_version}")

    if not args.skip_tests:
        print("[0/5] Running pre-build unit tests (pytest -q)...")
        if not run_prebuild_tests(root_dir):
            print("[ERROR] Pre-build tests failed. Aborting build.")
            return 1
        print("[INFO] Pre-build tests passed.")
    else:
        print("[0/5] Skipping pre-build tests (--skip-tests specified).")

    # Google Driveのファイルロックやクラウド同期遅延を回避するため、
    # 一時的なビルド用仮想環境および中間ビルドディレクトリはローカルTemp内に配置
    temp_base = Path(tempfile.gettempdir())
    venv_dir = temp_base / "sap_net_visualizer_build_venv"
    build_dir = temp_base / "sap_net_visualizer_build_work"
    legacy_venv = root_dir / ".venv_build"
    legacy_build = root_dir / "build"

    dist_dir = root_dir / "dist"
    installer_output_dir = root_dir / "dist_installer"
    requirements_file = root_dir / "requirements-build.txt"
    spec_file = root_dir / "packaging" / "SAP-net-Visualizer.spec"
    iss_file = root_dir / "packaging" / "installer.iss"
    version_template = root_dir / "packaging" / "version_info.template.txt"

    # 1. Clean previous build virtual environment and output directories
    print("[1/5] Cleaning previous build artifacts and creating clean virtual environment...")
    kill_existing_process()
    safe_rmtree(venv_dir)
    safe_rmtree(build_dir)
    safe_rmtree(legacy_venv)
    safe_rmtree(legacy_build)
    safe_rmtree(dist_dir)

    venv_created = False
    for attempt in range(3):
        try:
            subprocess.run([sys.executable, "-m", "venv", "--clear", str(venv_dir)], check=True)
            venv_created = True
            break
        except Exception as e:
            print(f"[WARNING] Virtualenv creation attempt {attempt + 1} failed: {e}. Retrying...")
            safe_rmtree(venv_dir)
            time.sleep(1)

    if not venv_created:
        print("[ERROR] Failed to create virtual environment.")
        return 1

    venv_python = venv_dir / "Scripts" / "python.exe"
    venv_pip = venv_dir / "Scripts" / "pip.exe"
    venv_pyinstaller = venv_dir / "Scripts" / "pyinstaller.exe"

    # 2. Install dependencies
    print("[2/5] Installing build dependencies from requirements-build.txt...")
    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=False)
        subprocess.run([str(venv_pip), "install", "-r", str(requirements_file)], check=True)
    except Exception as e:
        print(f"[ERROR] Failed to install dependencies: {e}")
        safe_rmtree(venv_dir)
        safe_rmtree(build_dir)
        return 1

    # 3. Build standalone binary with PyInstaller
    print("[3/5] Building standalone binary with PyInstaller...")
    try:
        generated_version_info = render_version_info(
            app_version,
            build_dir / "version_info.txt",
            template_path=version_template,
        )
        pyinstaller_env = os.environ.copy()
        pyinstaller_env["SAP_VERSION_INFO_PATH"] = str(generated_version_info)

        subprocess.run(
            [
                str(venv_pyinstaller),
                "--noconfirm",
                "--workpath", str(build_dir),
                "--distpath", str(dist_dir),
                str(spec_file)
            ],
            env=pyinstaller_env,
            check=True,
        )
        print("[INFO] PyInstaller standalone binary created successfully.")
    except Exception as e:
        print(f"[ERROR] PyInstaller build failed: {e}")
        safe_rmtree(venv_dir)
        safe_rmtree(build_dir)
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
        res = subprocess.run([str(iscc_path), f"/DMyAppVersion={app_version}", str(iss_file)])
        if res.returncode == 0:
            print("[INFO] Inno Setup installer compiled successfully!")
        else:
            print(f"[ERROR] Inno Setup compilation failed with exit code {res.returncode}.")
            safe_rmtree(venv_dir)
            safe_rmtree(build_dir)
            return 1
    else:
        if not iscc_path:
            print("[WARNING] Inno Setup compiler (ISCC.exe) not found.")
            print("[INFO] To create installer, install Inno Setup 6 from: https://jrsoftware.org/isdl.php")
        if not iss_file.exists():
            print(f"[ERROR] Inno Setup script not found: {iss_file}")
            safe_rmtree(venv_dir)
            safe_rmtree(build_dir)
            return 1

    # 5. Clean up temporary virtual environment and build cache
    print("[5/5] Cleaning up temporary build environment...")
    safe_rmtree(venv_dir)
    safe_rmtree(build_dir)

    print("=" * 60)
    print("  BUILD PROCESS FINISHED!")

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
