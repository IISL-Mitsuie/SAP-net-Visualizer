"""
SAP-net Visualizer フォルダ選択GUIダイアログ ＆ フォルダ履歴管理モジュール
"""
import os
import sys
import json
import glob
import datetime
import logging
from typing import List, Dict, Optional, Tuple

from .theme import (
    TK_BG_MAIN,
    TK_BG_CARD,
    TK_BG_HEADER,
    TK_BORDER_COLOR,
    TK_TEXT_TITLE,
    TK_TEXT_BODY,
    TK_TEXT_MUTED,
    TK_TEXT_PLACEHOLDER,
    TK_ACCENT_BLUE,
    TK_ACCENT_BLUE_HOVER,
    TK_STATUS_OK_FG,
    TK_STATUS_WARN_FG,
    TK_STATUS_ERR_FG,
)
from .utils.resource_utils import get_resource_path

logger = logging.getLogger(__name__)

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False


class FolderHistoryManager:
    """
    SAP-netシミュレーションログフォルダの選択履歴を管理・永続化するクラス。
    ユーザー設定ディレクトリ（~/.sap_visualizer/folder_history.json）にJSON形式で保存。
    """
    def __init__(self, history_file: Optional[str] = None, max_history: int = 30):
        self.max_history = max_history
        if history_file:
            self.history_file = history_file
        else:
            user_dir = os.path.expanduser("~")
            config_dir = os.path.join(user_dir, ".sap_visualizer")
            try:
                os.makedirs(config_dir, exist_ok=True)
                self.history_file = os.path.join(config_dir, "folder_history.json")
            except Exception:
                self.history_file = os.path.abspath("folder_history.json")
        
        self.history: List[Dict[str, str]] = []
        self.load_history()

    def load_history(self) -> List[Dict[str, str]]:
        """JSONファイルから履歴を読み込む"""
        self.history = []
        if not os.path.exists(self.history_file):
            return self.history

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "recent_folders" in data:
                    raw_list = data["recent_folders"]
                elif isinstance(data, list):
                    raw_list = data
                else:
                    raw_list = []

                for item in raw_list:
                    if isinstance(item, dict) and "path" in item:
                        item["path"] = os.path.abspath(item["path"])
                        self.history.append(item)
        except Exception as e:
            logger.warning(f"Failed to load folder history: {e}")
            self.history = []

        return self.history

    def save_history(self) -> bool:
        """現在の履歴リストをJSONファイルに保存する"""
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            data = {
                "version": "1.0",
                "max_history": self.max_history,
                "recent_folders": self.history[:self.max_history]
            }
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.warning(f"Failed to save folder history: {e}")
            return False

    def add_folder(self, folder_path: str, note: str = "") -> None:
        """フォルダを履歴の先頭に追加（既存にある場合は最新タイムスタンプで先頭に移動）"""
        if not folder_path:
            return

        abs_path = os.path.abspath(folder_path)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.history = [item for item in self.history if os.path.abspath(item.get("path", "")) != abs_path]

        new_entry = {
            "path": abs_path,
            "last_opened": now_str,
            "note": note
        }
        self.history.insert(0, new_entry)

        if len(self.history) > self.max_history:
            self.history = self.history[:self.max_history]

        self.save_history()

    def remove_folder(self, folder_path: str) -> None:
        """指定したパスを履歴から削除"""
        abs_path = os.path.abspath(folder_path)
        self.history = [item for item in self.history if os.path.abspath(item.get("path", "")) != abs_path]
        self.save_history()

    def clear_history(self) -> None:
        """すべての履歴をクリア"""
        self.history = []
        self.save_history()

    def get_detailed_history(self) -> List[Dict[str, str]]:
        """UI表示用に各履歴フォルダの存在確認・ログ状態を付与した詳細リストを返す"""
        detailed = []
        for item in self.history:
            path = item.get("path", "")
            last_opened = item.get("last_opened", "")
            
            exists = os.path.exists(path) and os.path.isdir(path)
            status_text = ""
            log_found = False

            if not exists:
                status_text = "※ フォルダ未検出"
            else:
                log_files = glob.glob(os.path.join(path, "sap_dynamic_log_*.jsonl*"))
                if not log_files:
                    log_files = glob.glob(os.path.join(path, "*.jsonl*"))
                if not log_files:
                    log_files = glob.glob(os.path.join(path, "**", "sap_dynamic_log_*.jsonl*"), recursive=True)

                if log_files:
                    status_text = "正常 (ログ検出)"
                    log_found = True
                else:
                    status_text = "△ ログ未検出"

            folder_name = os.path.basename(path) if path else ""
            if not folder_name and path:
                folder_name = path

            detailed.append({
                "folder_name": folder_name,
                "path": path,
                "last_opened": last_opened,
                "status": status_text,
                "exists": exists,
                "log_found": log_found
            })
        return detailed


class FolderSelectorDialog:
    """
    SAP-netシミュレーションログフォルダの選択・履歴参照を行うGUIダイアログ
    （SAP-net Visualizer のダークブルー＆ソフトグレーの統一モダンデザイン）
    """
    BG_MAIN = TK_BG_MAIN
    BG_CARD = TK_BG_CARD
    BG_HEADER = TK_BG_HEADER
    BORDER_COLOR = TK_BORDER_COLOR
    BORDER_FOCUS = "#2864b4"
    
    TEXT_TITLE = TK_TEXT_TITLE
    TEXT_BODY = TK_TEXT_BODY
    TEXT_MUTED = TK_TEXT_MUTED
    TEXT_PLACEHOLDER = TK_TEXT_PLACEHOLDER
    
    ACCENT_BLUE = TK_ACCENT_BLUE
    ACCENT_BLUE_HOVER = TK_ACCENT_BLUE_HOVER
    ACCENT_BORDER = "#3c78c8"
    
    STATUS_OK_FG = TK_STATUS_OK_FG
    STATUS_WARN_FG = TK_STATUS_WARN_FG
    STATUS_ERR_FG = TK_STATUS_ERR_FG

    def __init__(self, initial_dir: Optional[str] = None, history_manager: Optional[FolderHistoryManager] = None):
        self.selected_folder: Optional[str] = None
        self.initial_dir = initial_dir or os.getcwd()
        self.history_mgr = history_manager or FolderHistoryManager()
        self.root: Optional[tk.Tk] = None
        self.entry_path: Optional[tk.Entry] = None
        self.path_var: Optional[tk.StringVar] = None
        self.tree: Optional[ttk.Treeview] = None
        
        self.placeholder_text = "フォルダパスを直接入力、または右の「参照...」ボタン・下の履歴一覧から選択..."
        self.placeholder_active = True

    def show(self) -> Optional[str]:
        """
        GUIダイアログを表示し、ユーザーが選択したフォルダパスを返す。
        キャンセルされた場合は None を返す。
        """
        if not HAS_TKINTER:
            logger.warning("Tkinter is not available.")
            return None

        self.root = tk.Tk()
        self.root.title("SAP-net シミュレーションフォルダ選択")
        self.root.geometry("820x620")
        self.root.minsize(700, 480)
        self.root.configure(bg=self.BG_MAIN)

        # アイコンの設定
        icon_path = get_resource_path(os.path.join("packaging", "app_icon.ico"))
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # 画面中央に配置
        self.root.update_idletasks()
        w = 820
        h = 620
        x = max(0, (self.root.winfo_screenwidth() - w) // 2)
        y = max(0, (self.root.winfo_screenheight() - h) // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.attributes("-topmost", True)

        # ttk スタイル設定（統一デザインシステム）
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        font_family = "Meiryo UI"
        style.configure(".", font=(font_family, 9), background=self.BG_MAIN, foreground=self.TEXT_BODY)
        
        style.configure("Main.TFrame", background=self.BG_MAIN)
        style.configure("Card.TFrame", background=self.BG_CARD, relief="solid", borderwidth=1)
        
        style.configure(
            "Treeview.Heading",
            font=(font_family, 9, "bold"),
            background=self.BG_HEADER,
            foreground=self.TEXT_TITLE,
            relief="flat",
            padding=6
        )
        style.map("Treeview.Heading", background=[("active", "#d2e0f0")])
        
        style.configure(
            "Treeview",
            font=(font_family, 9),
            background=self.BG_CARD,
            foreground=self.TEXT_BODY,
            fieldbackground=self.BG_CARD,
            rowheight=26,
            borderwidth=0
        )
        style.map(
            "Treeview",
            background=[("selected", "#d5e5f8")],
            foreground=[("selected", self.TEXT_TITLE)]
        )

        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=self.BG_MAIN,
            background=self.ACCENT_BLUE,
            bordercolor=self.BORDER_COLOR,
            lightcolor=self.ACCENT_BLUE,
            darkcolor=self.ACCENT_BLUE
        )

        self._build_ui(font_family)

        self.root.bind("<Return>", lambda e: self._on_select())
        self.root.bind("<Escape>", lambda e: self._on_cancel())

        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.root.mainloop()

        return self.selected_folder

    def _build_ui(self, font_family: str) -> None:
        """UIコンポーネントの構築"""
        container = tk.Frame(self.root, bg=self.BG_MAIN, padx=20, pady=16)
        container.pack(fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(container, bg=self.BG_MAIN)
        header_frame.pack(fill=tk.X, pady=(0, 14))

        title_lbl = tk.Label(
            header_frame,
            text="SAP-net 実験ログフォルダの選択",
            font=(font_family, 14, "bold"),
            bg=self.BG_MAIN,
            fg=self.TEXT_TITLE
        )
        title_lbl.pack(anchor="w")

        desc_lbl = tk.Label(
            header_frame,
            text="可視化するSAP動的ログファイル (*.jsonl.gz / *.jsonl) が格納されている実験ディレクトリを選択してください。",
            font=(font_family, 9),
            bg=self.BG_MAIN,
            fg=self.TEXT_MUTED
        )
        desc_lbl.pack(anchor="w", pady=(2, 0))

        # フォルダ選択コンテナ
        sel_card = tk.Frame(
            container,
            bg=self.BG_CARD,
            bd=1,
            relief="solid",
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
            padx=14,
            pady=12
        )
        sel_card.pack(fill=tk.X, pady=(0, 14))

        sel_label = tk.Label(
            sel_card,
            text="対象フォルダパス:",
            font=(font_family, 9, "bold"),
            bg=self.BG_CARD,
            fg=self.TEXT_TITLE
        )
        sel_label.pack(anchor="w", pady=(0, 6))

        input_row = tk.Frame(sel_card, bg=self.BG_CARD)
        input_row.pack(fill=tk.X)

        self.path_var = tk.StringVar()
        self.entry_path = tk.Entry(
            input_row,
            textvariable=self.path_var,
            font=(font_family, 9),
            bg="#fdfefe",
            fg=self.TEXT_PLACEHOLDER,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightcolor=self.BORDER_FOCUS,
            highlightbackground=self.BORDER_COLOR
        )
        self.entry_path.insert(0, self.placeholder_text)
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))

        self.entry_path.bind("<FocusIn>", self._on_entry_focus_in)
        self.entry_path.bind("<FocusOut>", self._on_entry_focus_out)
        self.path_var.trace_add("write", self._on_path_changed)

        browse_btn = tk.Button(
            input_row,
            text="参照 (Browse)...",
            font=(font_family, 9),
            bg="#eef3f8",
            fg=self.TEXT_TITLE,
            activebackground="#dbe7f4",
            relief="groove",
            bd=1,
            padx=12,
            pady=3,
            cursor="hand2",
            command=self._on_browse
        )
        browse_btn.pack(side=tk.RIGHT)

        self.status_bar_card = tk.Label(
            sel_card,
            text="",
            font=(font_family, 8),
            bg=self.BG_CARD,
            fg=self.TEXT_MUTED
        )
        self.status_bar_card.pack(anchor="w", pady=(6, 0))

        # 履歴テーブルコンテナ
        hist_card = tk.Frame(
            container,
            bg=self.BG_CARD,
            bd=1,
            relief="solid",
            highlightbackground=self.BORDER_COLOR,
            highlightthickness=1,
            padx=14,
            pady=12
        )
        hist_card.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

        hist_header = tk.Frame(hist_card, bg=self.BG_CARD)
        hist_header.pack(fill=tk.X, pady=(0, 8))

        hist_title = tk.Label(
            hist_header,
            text="最近開いた実験ログフォルダ (履歴一覧)",
            font=(font_family, 9, "bold"),
            bg=self.BG_CARD,
            fg=self.TEXT_TITLE
        )
        hist_title.pack(side=tk.LEFT)

        del_btn = tk.Button(
            hist_header,
            text="選択項目を履歴から削除",
            font=(font_family, 8),
            bg="#fdf0f0",
            fg="#a02020",
            activebackground="#fadcdc",
            relief="groove",
            bd=1,
            padx=8,
            pady=1,
            cursor="hand2",
            command=self._on_delete_history
        )
        del_btn.pack(side=tk.RIGHT, padx=(4, 0))

        clear_btn = tk.Button(
            hist_header,
            text="全履歴クリア",
            font=(font_family, 8),
            bg="#fdf0f0",
            fg="#a02020",
            activebackground="#fadcdc",
            relief="groove",
            bd=1,
            padx=8,
            pady=1,
            cursor="hand2",
            command=self._on_clear_history
        )
        clear_btn.pack(side=tk.RIGHT)

        tree_frame = tk.Frame(hist_card, bg=self.BG_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("folder_name", "status", "last_opened", "full_path")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        self.tree.heading("folder_name", text="フォルダ名", anchor="w")
        self.tree.heading("status", text="状態 (ログ有無)", anchor="w")
        self.tree.heading("last_opened", text="最終参照日時", anchor="center")
        self.tree.heading("full_path", text="絶対パス", anchor="w")

        self.tree.column("folder_name", width=180, minwidth=120, stretch=False)
        self.tree.column("status", width=110, minwidth=90, stretch=False)
        self.tree.column("last_opened", width=140, minwidth=120, stretch=False)
        self.tree.column("full_path", width=300, minwidth=180, stretch=True)

        self.tree.tag_configure("ok", foreground=self.STATUS_OK_FG)
        self.tree.tag_configure("warn", foreground=self.STATUS_WARN_FG)
        self.tree.tag_configure("err", foreground=self.STATUS_ERR_FG)

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self._on_select())

        self._refresh_history_tree()

        # 下部ボタングループ
        btn_frame = tk.Frame(container, bg=self.BG_MAIN)
        btn_frame.pack(fill=tk.X)

        cancel_btn = tk.Button(
            btn_frame,
            text="キャンセル (Esc)",
            font=(font_family, 9),
            bg="#e4ebf3",
            fg=self.TEXT_TITLE,
            activebackground="#d2e0f0",
            relief="groove",
            bd=1,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))

        self.select_btn = tk.Button(
            btn_frame,
            text="このフォルダを開いて可視化 (Enter)",
            font=(font_family, 9, "bold"),
            bg=self.ACCENT_BLUE,
            fg="#ffffff",
            activebackground=self.ACCENT_BLUE_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=20,
            pady=6,
            cursor="hand2",
            command=self._on_select
        )
        self.select_btn.pack(side=tk.RIGHT)

    def _refresh_history_tree(self) -> None:
        """履歴テーブルを最新状態に再描画"""
        if not self.tree:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        history_items = self.history_mgr.get_detailed_history()
        for h in history_items:
            tag = "ok" if h["log_found"] else ("warn" if h["exists"] else "err")
            self.tree.insert(
                "",
                tk.END,
                values=(h["folder_name"], h["status"], h["last_opened"], h["path"]),
                tags=(tag,)
            )

    def _on_entry_focus_in(self, event=None) -> None:
        if self.placeholder_active:
            self.entry_path.delete(0, tk.END)
            self.entry_path.config(fg=self.TEXT_BODY)
            self.placeholder_active = False

    def _on_entry_focus_out(self, event=None) -> None:
        if not self.entry_path.get().strip():
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, self.placeholder_text)
            self.entry_path.config(fg=self.TEXT_PLACEHOLDER)
            self.placeholder_active = True

    def _on_path_changed(self, *args) -> None:
        if self.placeholder_active:
            return
        path = self.path_var.get().strip()
        self._update_status_preview(path)

    def _update_status_preview(self, path: str) -> None:
        if not path:
            self.status_bar_card.config(text="")
            return

        if not os.path.exists(path):
            self.status_bar_card.config(text="※ 指定されたパスが存在しません", fg=self.STATUS_ERR_FG)
            return

        if not os.path.isdir(path):
            self.status_bar_card.config(text="※ ディレクトリ（フォルダ）を指定してください", fg=self.STATUS_WARN_FG)
            return

        log_files = glob.glob(os.path.join(path, "sap_dynamic_log_*.jsonl*"))
        if not log_files:
            log_files = glob.glob(os.path.join(path, "*.jsonl*"))
        if not log_files:
            log_files = glob.glob(os.path.join(path, "**", "sap_dynamic_log_*.jsonl*"), recursive=True)

        if log_files:
            target = max(log_files, key=os.path.getmtime)
            f_name = os.path.basename(target)
            self.status_bar_card.config(text=f"✓ SAP動的ログファイルを検出しました: {f_name}", fg=self.STATUS_OK_FG)
        else:
            self.status_bar_card.config(text="△ フォルダ内に SAP動的ログファイル (*.jsonl.gz / *.jsonl) が見つかりません", fg=self.STATUS_WARN_FG)

    def _get_entry_path(self) -> str:
        """現在の入力欄パスを取得（プレースホルダー時は空文字）"""
        if self.placeholder_active:
            return ""
        return self.path_var.get().strip() if self.path_var else ""

    def _set_entry_path(self, path: str) -> None:
        """入力欄にパスを設定"""
        if not path:
            self._apply_placeholder()
            return
        self.placeholder_active = False
        if self.entry_path:
            self.entry_path.config(fg=self.TEXT_BODY)
        if self.path_var:
            self.path_var.set(os.path.abspath(path))

    def _apply_placeholder(self) -> None:
        """プレースホルダー状態を適用"""
        self.placeholder_active = True
        if self.entry_path:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, self.placeholder_text)
            self.entry_path.config(fg=self.TEXT_PLACEHOLDER)
        if self.path_var:
            self.path_var.set("")

    def _on_browse(self) -> None:
        current_val = self._get_entry_path()
        if current_val and os.path.exists(current_val):
            initial = os.path.dirname(os.path.abspath(current_val)) if os.path.isfile(current_val) or os.path.isdir(current_val) else current_val
        else:
            initial = self.initial_dir

        folder = filedialog.askdirectory(
            parent=self.root,
            title="SAP動的ログファイルがある実験フォルダを選択",
            initialdir=initial
        )
        if folder:
            self._set_entry_path(folder)

    def _on_tree_select(self, event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return

        values = self.tree.item(selected[0], "values")
        if values and len(values) >= 4:
            path = values[3]
            self._set_entry_path(path)

    def _on_delete_history(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("お知らせ", "削除する履歴項目を一覧から選択してください。", parent=self.root)
            return

        values = self.tree.item(selected[0], "values")
        if values and len(values) >= 4:
            path = values[3]
            self.history_mgr.remove_folder(path)
            self._refresh_history_tree()

    def _on_clear_history(self) -> None:
        if not self.history_mgr.history:
            return

        if messagebox.askyesno("履歴クリアの確認", "すべてのフォルダ選択履歴を削除しますか？", parent=self.root):
            self.history_mgr.clear_history()
            self._refresh_history_tree()

    def _on_confirm(self) -> None:
        """決定ボタン処理（入力欄またはTreeview選択行の採用）"""
        raw_path = self._get_entry_path()
        if not raw_path and self.tree:
            selected = self.tree.selection()
            if selected:
                values = self.tree.item(selected[0], "values")
                if values and len(values) >= 4:
                    raw_path = values[3]

        if not raw_path:
            messagebox.showwarning("入力確認", "フォルダパスを選択または入力してください。", parent=self.root)
            return

        abs_path = os.path.abspath(raw_path)
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            messagebox.showerror("エラー", f"指定されたフォルダが存在しません:\n{abs_path}", parent=self.root)
            return

        self.history_mgr.add_folder(abs_path)
        self.selected_folder = abs_path
        if self.root:
            self.root.destroy()

    def _on_select(self) -> None:
        self._on_confirm()

    def _on_cancel(self) -> None:
        self.selected_folder = None
        if self.root:
            self.root.destroy()



def select_simulation_folder(initial_dir: Optional[str] = None) -> Optional[str]:
    """
    フォルダ選択ダイアログを開き、ユーザーが選択したフォルダパスを返すヘルパー関数。
    """
    dialog = FolderSelectorDialog(initial_dir=initial_dir)
    return dialog.show()

