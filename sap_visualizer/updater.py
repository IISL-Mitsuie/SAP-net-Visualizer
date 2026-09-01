"""
SAP-net Visualizer アップデータモジュール (Updater Module)
GitHub Releases API から最新バージョン情報を取得し、
アップデート通知、インストーラーダウンロード、自動起動を提供します。
"""
import os
import sys
import re
import json
import logging
import threading
import tempfile
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, Tuple

from .constants import APP_VERSION

logger = logging.getLogger(__name__)

DEFAULT_REPO = "IISL-Mitsuie/SAP-net-Visualizer"
GITHUB_API_LATEST_RELEASE = "https://api.github.com/repos/{repo}/releases/latest"
DEFAULT_TIMEOUT_SEC = 3.0


@dataclass
class UpdateInfo:
    """最新バージョン情報を保持するデータクラス"""
    version: str                      # 例: "1.1.0"
    tag_name: str                     # 例: "v1.1.0"
    title: str                        # リリースタイトル
    release_notes: str                # リリースノート (Markdown / テキスト)
    release_url: str                  # リリースWebページURL (GitHub Releases)
    published_at: str                 # リリース日時 (ISO形式文字列)
    installer_download_url: Optional[str] = None  # Setup.exe のダウンロードURL
    installer_name: Optional[str] = None          # 例: "SAP_net_Visualizer_Setup_v1.1.0.exe"
    installer_size: int = 0                       # バイト数
    is_update_available: bool = False             # 現在のバージョンより新しいか


def parse_version_tuple(version_str: str) -> Tuple[int, ...]:
    """
    バージョン文字列（例: "v1.2.3", "1.0.1", "2.0.0-rc1"）を比較可能な数値タプルに変換する。
    """
    if not version_str:
        return (0,)
    # 'v' や 'V' プレフィックスを除去
    clean_str = version_str.strip().lstrip("vV")
    # 数値の並びを抽出 (例: "1.2.3" -> [1, 2, 3])
    parts = re.split(r"[-_+.]", clean_str)
    num_parts = []
    for part in parts:
        digits = re.match(r"^\d+", part)
        if digits:
            num_parts.append(int(digits.group(0)))
        else:
            # 数値以外の修飾子（alpha, beta, rc等）
            break
    return tuple(num_parts) if num_parts else (0,)


def compare_versions(v1: str, v2: str) -> int:
    """
    2つのバージョン文字列を比較する。
    戻り値:
        v1 > v2  -> 1
        v1 == v2 -> 0
        v1 < v2  -> -1
    """
    t1 = parse_version_tuple(v1)
    t2 = parse_version_tuple(v2)

    # 桁数を揃える (例: (1, 0) と (1, 0, 1) -> (1, 0, 0) と (1, 0, 1))
    max_len = max(len(t1), len(t2))
    padded_t1 = t1 + (0,) * (max_len - len(t1))
    padded_t2 = t2 + (0,) * (max_len - len(t2))

    if padded_t1 > padded_t2:
        return 1
    elif padded_t1 < padded_t2:
        return -1
    return 0


def is_newer_version(current_version: str, latest_version: str) -> bool:
    """最新バージョンが現在のバージョンより新しいかどうかを判定"""
    return compare_versions(latest_version, current_version) > 0


def fetch_latest_release_info(
    repo: str = DEFAULT_REPO,
    current_version: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[UpdateInfo]:
    """
    GitHub Releases API から最新のリリース情報を同期的に取得する。
    オフライン時やエラー時は例外を出さず None を返す。
    """
    if current_version is None:
        current_version = APP_VERSION

    url = GITHUB_API_LATEST_RELEASE.format(repo=repo)
    headers = {
        "User-Agent": f"SAP-net-Visualizer/{current_version}",
        "Accept": "application/vnd.github.v3+json",
    }

    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                logger.warning(f"GitHub Releases API returned status {resp.status}")
                return None
            body_bytes = resp.read()
            data = json.loads(body_bytes.decode("utf-8"))

        tag_name = data.get("tag_name", "")
        # tag_name からバージョン番号を抽出
        latest_version = tag_name.lstrip("vV") if tag_name else ""
        if not latest_version:
            return None

        title = data.get("name") or tag_name
        release_notes = data.get("body") or ""
        release_url = data.get("html_url") or f"https://github.com/{repo}/releases"
        published_at = data.get("published_at", "")

        # アセット一覧からインストーラー (.exe) を探索
        installer_url = None
        installer_name = None
        installer_size = 0

        assets = data.get("assets", [])
        for asset in assets:
            name = asset.get("name", "")
            # Setup または exe を優先探索
            if name.lower().endswith(".exe"):
                installer_url = asset.get("browser_download_url")
                installer_name = name
                installer_size = asset.get("size", 0)
                if "setup" in name.lower():
                    # Setup を含むものを最優先
                    break

        update_available = is_newer_version(current_version, latest_version)

        return UpdateInfo(
            version=latest_version,
            tag_name=tag_name,
            title=title,
            release_notes=release_notes,
            release_url=release_url,
            published_at=published_at,
            installer_download_url=installer_url,
            installer_name=installer_name,
            installer_size=installer_size,
            is_update_available=update_available,
        )

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        logger.debug(f"Update check skipped (network error/offline): {e}")
        return None
    except Exception as e:
        logger.debug(f"Failed to check for updates: {e}")
        return None


def check_for_updates_async(
    callback: Callable[[Optional[UpdateInfo]], None],
    repo: str = DEFAULT_REPO,
    current_version: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> threading.Thread:
    """
    バックグラウンドスレッドで更新チェックを実行し、完了時に callback を呼び出す。
    """
    def _worker():
        info = fetch_latest_release_info(
            repo=repo,
            current_version=current_version,
            timeout=timeout
        )
        try:
            callback(info)
        except Exception as e:
            logger.debug(f"Error in update callback: {e}")

    thread = threading.Thread(target=_worker, name="UpdateCheckThread", daemon=True)
    thread.start()
    return thread


def download_installer(
    download_url: str,
    target_filename: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    chunk_size: int = 64 * 1024,
) -> str:
    """
    指定されたURLからインストーラーを %TEMP% フォルダにダウンロードする。
    戻り値: ダウンロードされたファイルの絶対パス
    """
    temp_dir = tempfile.gettempdir()
    if not target_filename:
        target_filename = os.path.basename(download_url.split("?")[0]) or "SAP_net_Visualizer_Setup.exe"

    dest_path = os.path.join(temp_dir, target_filename)

    headers = {
        "User-Agent": f"SAP-net-Visualizer/{APP_VERSION}",
    }
    req = urllib.request.Request(download_url, headers=headers)

    with urllib.request.urlopen(req, timeout=30.0) as response, open(dest_path, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0

        while True:
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Download was cancelled by user.")

            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)

            if progress_callback:
                progress_callback(downloaded, total_size)

    return dest_path


def launch_installer_and_exit(installer_path: str, silent: bool = False) -> None:
    """
    ダウンロードしたインストーラーをバックグラウンドで起動し、現在のプロセスを安全に終了する。
    """
    if not os.path.exists(installer_path):
        raise FileNotFoundError(f"Installer not found: {installer_path}")

    args = [installer_path]
    if silent:
        # Inno Setup のサイレントインストール引数
        args.extend(["/VERYSILENT", "/NORESTART"])

    logger.info(f"Launching installer: {args}")
    
    # 新しい独立したプロセスとして起動（Windows環境で親プロセス終了後も独立実行）
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(args, creationflags=flags, close_fds=True)
    else:
        subprocess.Popen(args, close_fds=True)

    # アプリケーションプロセスを正常終了
    sys.exit(0)
