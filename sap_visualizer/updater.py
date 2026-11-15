"""
SAP-net Visualizer アップデータモジュール (Updater Module)
GitHub Releases API から最新バージョン情報を取得し、
アップデート通知、インストーラーダウンロード、自動起動を提供します。
"""
import os
import sys
import re
import json
import shutil
import hashlib
import logging
import threading
import tempfile
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional, Callable, Tuple

from .constants import APP_VERSION

logger = logging.getLogger(__name__)

DEFAULT_REPO = "IISL-Mitsuie/SAP-net-Visualizer"
GITHUB_API_LATEST_RELEASE = "https://api.github.com/repos/{repo}/releases/latest"
DEFAULT_TIMEOUT_SEC = 3.0
_SHA256_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")


class UpdateVerificationError(Exception):
    """ダウンロードしたインストーラーの検証（サイズ・SHA-256等）に失敗した場合の例外"""


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
    expected_sha256: Optional[str] = None         # 期待される SHA-256 (hex lowercase)
    is_update_available: bool = False             # 現在のバージョンより新しいか


def _extract_sha256_digest(digest_value: Optional[str]) -> Optional[str]:
    """GitHub API asset.digest ('sha256:<hex>') 等から正規化済み SHA-256 を抽出"""
    if not digest_value or not isinstance(digest_value, str):
        return None
    cleaned = digest_value.strip()
    if cleaned.lower().startswith("sha256:"):
        cleaned = cleaned[7:].strip()
    m = _SHA256_RE.fullmatch(cleaned)
    return m.group(1).lower() if m else None


def _parse_sha256_text(text: str, target_filename: Optional[str] = None) -> Optional[str]:
    """sha256sum / certutil 形式のテキストから期待 SHA-256 ハッシュを抽出する"""
    if not text:
        return None
    first_match = None
    for line in text.splitlines():
        m = _SHA256_RE.search(line)
        if not m:
            continue
        digest = m.group(1).lower()
        if target_filename and target_filename in line:
            return digest
        if first_match is None:
            first_match = digest
    return first_match


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

        # アセット一覧からインストーラー (.exe) と SHA-256 チェックサムアセットを探索
        installer_url = None
        installer_name = None
        installer_size = 0
        expected_sha256 = None

        assets = data.get("assets", [])
        for asset in assets:
            name = asset.get("name", "")
            # Setup または exe を優先探索
            if name.lower().endswith(".exe"):
                installer_url = asset.get("browser_download_url")
                installer_name = name
                installer_size = asset.get("size", 0)
                expected_sha256 = _extract_sha256_digest(asset.get("digest"))
                if "setup" in name.lower():
                    # Setup を含むものを最優先
                    break

        if not expected_sha256:
            sha_asset = None
            if installer_name:
                exact_sha_name = f"{installer_name}.sha256".lower()
                for asset in assets:
                    if asset.get("name", "").lower() == exact_sha_name:
                        sha_asset = asset
                        break
            if sha_asset is None:
                for asset in assets:
                    if asset.get("name", "").lower().endswith(".sha256"):
                        sha_asset = asset
                        break

            if sha_asset and sha_asset.get("browser_download_url"):
                try:
                    sha_req = urllib.request.Request(
                        sha_asset["browser_download_url"],
                        headers={"User-Agent": f"SAP-net-Visualizer/{current_version}"},
                        method="GET",
                    )
                    with urllib.request.urlopen(sha_req, timeout=timeout) as sha_resp:
                        if sha_resp.status == 200:
                            sha_text = sha_resp.read().decode("utf-8", errors="replace")
                            expected_sha256 = _parse_sha256_text(sha_text, target_filename=installer_name)
                except Exception as e:
                    logger.debug(f"Failed to fetch .sha256 asset: {e}")

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
            expected_sha256=expected_sha256,
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
    expected_size: Optional[int] = None,
    expected_sha256: Optional[str] = None,
) -> str:
    """
    指定されたURLから専用一時フォルダに .part ファイルとしてダウンロードし、
    サイズおよび SHA-256 検証に成功した場合のみ正規ファイルへ昇格してパスを返す。
    """
    work_dir = tempfile.mkdtemp(prefix="sap_vis_update_")
    raw_name = target_filename or os.path.basename(download_url.split("?")[0])
    safe_name = os.path.basename(raw_name) if raw_name else ""
    if not safe_name:
        safe_name = "SAP_net_Visualizer_Setup.exe"

    part_path = os.path.join(work_dir, f"{safe_name}.part")
    dest_path = os.path.join(work_dir, safe_name)

    headers = {
        "User-Agent": f"SAP-net-Visualizer/{APP_VERSION}",
    }
    req = urllib.request.Request(download_url, headers=headers)

    hasher = hashlib.sha256()
    downloaded = 0
    header_total_size = 0

    try:
        with urllib.request.urlopen(req, timeout=30.0) as response, open(part_path, "wb") as out_file:
            raw_len = response.headers.get("Content-Length") if response.headers else None
            header_total_size = int(raw_len) if raw_len and str(raw_len).isdigit() else 0
            progress_total = expected_size if (expected_size and expected_size > 0) else header_total_size

            while True:
                if cancel_event and cancel_event.is_set():
                    raise InterruptedError("Download was cancelled by user.")

                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                hasher.update(chunk)
                downloaded += len(chunk)

                if progress_callback:
                    progress_callback(downloaded, progress_total)

        if expected_size is not None and expected_size > 0 and downloaded != expected_size:
            raise UpdateVerificationError(
                f"Downloaded size mismatch: expected {expected_size} bytes, got {downloaded} bytes."
            )
        if (expected_size is None or expected_size <= 0) and header_total_size > 0 and downloaded != header_total_size:
            raise UpdateVerificationError(
                f"Downloaded size mismatch against Content-Length: expected {header_total_size} bytes, got {downloaded} bytes."
            )

        if expected_sha256:
            normalized_expected = _extract_sha256_digest(expected_sha256)
            actual_sha256 = hasher.hexdigest().lower()
            if not normalized_expected or actual_sha256 != normalized_expected:
                raise UpdateVerificationError(
                    f"SHA-256 verification failed: expected {expected_sha256}, got {actual_sha256}."
                )

        os.replace(part_path, dest_path)
        return dest_path
    except Exception:
        if os.path.exists(part_path):
            try:
                os.remove(part_path)
            except OSError:
                pass
        shutil.rmtree(work_dir, ignore_errors=True)
        raise


def launch_installer(installer_path: str, silent: bool = False) -> None:
    """
    ダウンロードしたインストーラーをバックグラウンドプロセスとして起動する。
    呼び出し元のイベントループやプロセス終了は行わない。
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


def launch_installer_and_exit(installer_path: str, silent: bool = False) -> None:
    """
    後方互換ラッパー: インストーラーを起動し、現在のプロセスを終了する。
    """
    launch_installer(installer_path, silent=silent)
    sys.exit(0)
