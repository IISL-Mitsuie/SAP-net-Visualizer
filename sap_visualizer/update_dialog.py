"""
SAP-net Visualizer アップデート通知・ダウンロードGUIダイアログモジュール
"""
from __future__ import annotations

import os
import sys
import logging
import webbrowser
import threading
import subprocess
from typing import Optional, Tuple, Any

from .constants import APP_VERSION
from .updater import (
    UpdateInfo,
    download_installer,
    launch_installer_and_exit,
)
from .theme import (
    TK_BG_MAIN,
    TK_BG_CARD,
    TK_BG_PANEL,
    TK_BORDER_COLOR,
    TK_TEXT_TITLE,
    TK_TEXT_BODY,
    TK_TEXT_MUTED,
    TK_ACCENT_BLUE,
    TK_ACCENT_BLUE_HOVER,
    TK_BTN_SECONDARY_BG,
    TK_BTN_SECONDARY_HOVER,
    TK_BTN_SECONDARY_BORDER,
    TK_BTN_SECONDARY_TEXT,
)

logger = logging.getLogger(__name__)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False


class UpdateDialog:
    """
    新バージョン案内・インストーラーダウンロード・更新適用ダイアログ
    """
    def __init__(self, parent: tk.Widget, update_info: UpdateInfo, font_family: str = "Meiryo UI"):
        if not HAS_TKINTER:
            raise RuntimeError("tkinter is required to display UpdateDialog")
        self.parent = parent
        self.update_info = update_info
        self.font_family = font_family
        self.cancel_event = threading.Event()
        self.download_thread: Optional[threading.Thread] = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("SAP-net Visualizer アップデート")
        self.dialog.geometry("680x580")
        self.dialog.minsize(580, 480)
        self.dialog.configure(bg=TK_BG_MAIN)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 中央配置
        self.dialog.update_idletasks()
        w, h = 680, 580
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.dialog.geometry(f"{w}x{h}+{max(0, px)}+{max(0, py)}")

        self._build_ui()
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_styled_button(
        self,
        parent: tk.Widget,
        text: str,
        command: Any,
        bg: str,
        fg: str,
        hover_bg: str,
        hover_fg: Optional[str] = None,
        border_color: Optional[str] = None,
        font: Optional[Tuple[str, int, str]] = None,
        padx: int = 14,
        pady: int = 6,
        cursor: str = "hand2"
    ) -> tk.Button:
        has_border = border_color is not None
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover_bg,
            activeforeground=hover_fg if hover_fg else fg,
            relief="solid" if has_border else "flat",
            bd=1 if has_border else 0,
            highlightthickness=0,
            cursor=cursor,
            padx=padx,
            pady=pady,
            font=font or (self.font_family, 9)
        )

        def _on_enter(e):
            if btn.cget("state") != "disabled":
                btn.configure(bg=hover_bg)
                if hover_fg:
                    btn.configure(fg=hover_fg)

        def _on_leave(e):
            if btn.cget("state") != "disabled":
                btn.configure(bg=bg)
                if hover_fg:
                    btn.configure(fg=fg)

        btn.bind("<Enter>", _on_enter)
        btn.bind("<Leave>", _on_leave)
        return btn

    def _build_ui(self) -> None:
        # 1. 最下部アクションボタングループ（確実に最下部に固定表示）
        btn_bar = tk.Frame(self.dialog, bg=TK_BG_MAIN)
        btn_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=22, pady=(0, 18))

        self.browser_btn = self._create_styled_button(
            btn_bar,
            text="GitHubで確認",
            command=self._open_in_browser,
            bg=TK_BTN_SECONDARY_BG,
            fg=TK_BTN_SECONDARY_TEXT,
            hover_bg=TK_BTN_SECONDARY_HOVER,
            border_color=TK_BTN_SECONDARY_BORDER,
            font=(self.font_family, 9),
            padx=14
        )
        self.browser_btn.pack(side=tk.LEFT)

        self.close_btn = self._create_styled_button(
            btn_bar,
            text="閉じる",
            command=self._on_close,
            bg=TK_BTN_SECONDARY_BG,
            fg=TK_BTN_SECONDARY_TEXT,
            hover_bg=TK_BTN_SECONDARY_HOVER,
            border_color=TK_BTN_SECONDARY_BORDER,
            font=(self.font_family, 9),
            padx=16
        )
        self.close_btn.pack(side=tk.RIGHT, padx=(8, 0))

        if self.update_info.installer_download_url:
            self.update_now_btn = self._create_styled_button(
                btn_bar,
                text="今すぐアップデート (自動インストール)",
                command=self._start_download,
                bg=TK_ACCENT_BLUE,
                fg="#ffffff",
                hover_bg=TK_ACCENT_BLUE_HOVER,
                hover_fg="#ffffff",
                border_color=None,
                font=(self.font_family, 9, "bold"),
                padx=18
            )
            self.update_now_btn.pack(side=tk.RIGHT)
        else:
            self.browser_btn.configure(text="ブラウザからダウンロード")
            self.browser_btn.pack_forget()
            self.browser_btn.pack(side=tk.RIGHT)

        # 2. ダウンロード進捗領域（ボトムバーの直上に固定）
        self.progress_frame = tk.Frame(self.dialog, bg=TK_BG_MAIN)
        self.progress_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=22, pady=(0, 10))

        self.progress_lbl = tk.Label(
            self.progress_frame,
            text="",
            font=(self.font_family, 9),
            bg=TK_BG_MAIN,
            fg=TK_TEXT_MUTED
        )
        self.progress_lbl.pack(anchor="w", pady=(0, 2))

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            orient="horizontal",
            mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X)
        self.progress_frame.pack_forget()  # ダウンロード開始まで非表示

        # 3. メインコンテンツ領域（残りの上部・中央を伸縮配置）
        container = tk.Frame(self.dialog, bg=TK_BG_MAIN)
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=22, pady=(18, 12))

        # 3-1. ヘッダーカード
        header_card = tk.Frame(
            container,
            bg=TK_BG_CARD,
            relief="solid",
            borderwidth=1,
            highlightbackground=TK_BORDER_COLOR
        )
        header_card.pack(fill=tk.X, pady=(0, 12))

        header_inner = tk.Frame(header_card, bg=TK_BG_CARD)
        header_inner.pack(fill=tk.X, padx=16, pady=12)

        title_lbl = tk.Label(
            header_inner,
            text="🚀 新バージョンが利用可能です！",
            font=(self.font_family, 13, "bold"),
            bg=TK_BG_CARD,
            fg=TK_TEXT_TITLE
        )
        title_lbl.pack(anchor="w")

        info_text = f"現在のバージョン: v{APP_VERSION}   ➔   最新バージョン: v{self.update_info.version}"
        if self.update_info.installer_size > 0:
            size_mb = self.update_info.installer_size / (1024 * 1024)
            info_text += f" ({size_mb:.1f} MB)"

        info_lbl = tk.Label(
            header_inner,
            text=info_text,
            font=(self.font_family, 10),
            bg=TK_BG_CARD,
            fg=TK_ACCENT_BLUE
        )
        info_lbl.pack(anchor="w", pady=(4, 0))

        # 3-2. リリースノート領域
        notes_label = tk.Label(
            container,
            text="リリースノート (更新内容):",
            font=(self.font_family, 9, "bold"),
            bg=TK_BG_MAIN,
            fg=TK_TEXT_TITLE
        )
        notes_label.pack(anchor="w", pady=(0, 4))

        notes_frame = tk.Frame(
            container,
            bg=TK_BG_CARD,
            relief="solid",
            borderwidth=1,
            highlightbackground=TK_BORDER_COLOR
        )
        notes_frame.pack(fill=tk.BOTH, expand=True)

        notes_scroll = ttk.Scrollbar(notes_frame, orient="vertical")
        notes_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.notes_text = tk.Text(
            notes_frame,
            wrap="word",
            bg=TK_BG_PANEL,
            fg=TK_TEXT_BODY,
            font=(self.font_family, 9),
            relief="flat",
            padx=10,
            pady=10,
            height=8,
            yscrollcommand=notes_scroll.set
        )
        self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        notes_scroll.config(command=self.notes_text.yview)

        # リリースノート本文の挿入
        notes_content = self.update_info.release_notes.strip() or "更新内容の詳細はGitHub Releasesページをご確認ください。"
        self.notes_text.insert("1.0", notes_content)
        self.notes_text.configure(state="disabled")

    def _open_in_browser(self) -> None:
        """GitHub Releases Webページを既定のブラウザで開く"""
        if self.update_info.release_url:
            webbrowser.open(self.update_info.release_url)

    def _start_download(self) -> None:
        """インストーラーのダウンロードを開始"""
        if not self.update_info.installer_download_url:
            return

        self.update_now_btn.configure(state="disabled", text="ダウンロード中...")
        self.close_btn.configure(text="キャンセル")
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        self.progress_bar["value"] = 0
        self.progress_lbl.configure(text="インストーラーをダウンロード中...")

        def _download_worker():
            try:
                def _on_progress(downloaded: int, total: int):
                    if total > 0:
                        pct = (downloaded / total) * 100
                        d_mb = downloaded / (1024 * 1024)
                        t_mb = total / (1024 * 1024)
                        msg = f"ダウンロード中: {d_mb:.1f} MB / {t_mb:.1f} MB ({pct:.1f}%)"
                        self.dialog.after(0, lambda: self._update_progress_ui(pct, msg))

                installer_path = download_installer(
                    self.update_info.installer_download_url,
                    target_filename=self.update_info.installer_name,
                    progress_callback=_on_progress,
                    cancel_event=self.cancel_event
                )

                self.dialog.after(0, lambda: self._on_download_complete(installer_path))

            except InterruptedError:
                self.dialog.after(0, lambda: self._on_download_cancelled())
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Download failed: {err_msg}")
                self.dialog.after(0, lambda msg=err_msg: self._on_download_failed(msg))

        self.download_thread = threading.Thread(target=_download_worker, daemon=True)
        self.download_thread.start()

    def _update_progress_ui(self, pct: float, msg: str) -> None:
        self.progress_bar["value"] = pct
        self.progress_lbl.configure(text=msg)

    def _on_download_complete(self, installer_path: str) -> None:
        self.downloaded_installer_path = installer_path
        file_name = os.path.basename(installer_path)
        self.progress_lbl.configure(text=f"✓ ダウンロード完了: {file_name}")
        self.progress_bar["value"] = 100

        # ダウンロード完了後のボタンスタイル・機能に更新
        self._update_buttons_to_installed_state(installer_path)

        # ユーザーに今すぐインストーラーを起動するか確認
        if messagebox.askyesno(
            "ダウンロード完了",
            f"インストーラーのダウンロードが完了しました。\n\n"
            f"ファイル: {file_name}\n\n"
            "今すぐアプリを終了してインストーラーを起動しますか？\n\n"
            "・「はい」: アプリを終了し、インストーラーを起動します\n"
            "・「いいえ」: 起動せず、後で手動またはダイアログから実行します",
            parent=self.dialog
        ):
            self._launch_installer(installer_path)

    def _update_buttons_to_installed_state(self, installer_path: str) -> None:
        """ダウンロード完了時のボタン表示・動作に切り替え"""
        self.close_btn.configure(text="後で (閉じる)")
        if hasattr(self, "update_now_btn"):
            self.update_now_btn.configure(
                state="normal",
                text="今すぐインストール",
                command=lambda: self._launch_installer(installer_path)
            )
        self.browser_btn.configure(
            text="保存先フォルダを開く",
            command=lambda: self._open_installer_folder(installer_path)
        )

    def _open_installer_folder(self, file_path: str) -> None:
        """インストーラーが保存されたフォルダをエクスプローラーで開く"""
        try:
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{os.path.abspath(file_path)}"')
            else:
                webbrowser.open(os.path.dirname(file_path))
        except Exception as e:
            logger.warning(f"Failed to open folder: {e}")

    def _launch_installer(self, installer_path: str) -> None:
        """インストーラーを起動してアプリを終了"""
        try:
            launch_installer_and_exit(installer_path)
        except Exception as e:
            messagebox.showerror("起動エラー", f"インストーラーの起動に失敗しました:\n{e}", parent=self.dialog)

    def _on_download_failed(self, error_msg: str) -> None:
        messagebox.showerror(
            "ダウンロード失敗",
            f"インストーラーのダウンロード中にエラーが発生しました:\n{error_msg}\n\nブラウザから手動でダウンロードをお試しください。",
            parent=self.dialog
        )
        self._reset_buttons()

    def _on_download_cancelled(self) -> None:
        self.progress_lbl.configure(text="ダウンロードがキャンセルされました。")
        self._reset_buttons()

    def _reset_buttons(self) -> None:
        if hasattr(self, "update_now_btn"):
            self.update_now_btn.configure(state="normal", text="今すぐアップデート")
        self.close_btn.configure(text="閉じる")
        self.progress_frame.pack_forget()

    def _on_close(self) -> None:
        if self.download_thread and self.download_thread.is_alive():
            if messagebox.askyesno("キャンセル確認", "ダウンロードを中止して閉じますか？", parent=self.dialog):
                self.cancel_event.set()
                self.dialog.destroy()
        else:
            self.dialog.destroy()
