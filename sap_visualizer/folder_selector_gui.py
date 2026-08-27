import os
import sys
import json
import glob
import datetime
from typing import List, Dict, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False


class FolderHistoryManager:
    """
    SAP-netシミュレーションログフォルダの選択履歴を管理・永続化するクラス。
    ユーザー設定ディレクトリ（例: ~/.sap_visualizer/folder_history.json）にJSON形式で保存します。
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
                    if isinstance(item, str):
                        self.history.append({
                            "path": os.path.abspath(item),
                            "last_opened": "",
                            "note": ""
                        })
                    elif isinstance(item, dict) and "path" in item:
                        item["path"] = os.path.abspath(item["path"])
                        self.history.append(item)
        except Exception as e:
            print(f"[WARNING] Failed to load folder history: {e}")
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
            print(f"[WARNING] Failed to save folder history: {e}")
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
    # 統一カラーパレット定義
    BG_MAIN = "#f0f3f6"         # メインウィンドウ背景色
    BG_CARD = "#ffffff"         # カード・入力コンテナ背景色
    BG_HEADER = "#e4ebf3"       # テーブルヘッダー背景色
    BORDER_COLOR = "#becde1"    # 枠線色
    BORDER_FOCUS = "#2864b4"    # フォーカス時枠線色
    
    TEXT_TITLE = "#14284b"      # タイトル文字色（濃紺）
    TEXT_BODY = "#1e3250"       # 本文文字色
    TEXT_MUTED = "#5a738e"      # 補足・注釈文字色
    TEXT_PLACEHOLDER = "#8c9ba5"# プレースホルダー色
    
    ACCENT_BLUE = "#1e50a2"     # プライマリボタン背景（深青）
    ACCENT_BLUE_HOVER = "#143c7d"
    ACCENT_BORDER = "#3c78c8"
    
    STATUS_OK_FG = "#146428"     # 正常テキスト（緑）
    STATUS_WARN_FG = "#a05a00"   # 警告テキスト（琥珀）
    STATUS_ERR_FG = "#888888"    # 不存在テキスト（灰）

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
            print("[WARNING] Tkinter is not available.")
            return None

        self.root = tk.Tk()
        self.root.title("SAP-net シミュレーションフォルダ選択")
        self.root.geometry("820x620")
        self.root.minsize(700, 480)
        self.root.configure(bg=self.BG_MAIN)

        # アイコンの設定
        icon_paths = [
            os.path.join(os.path.dirname(__file__), "..", "packaging", "app_icon.ico"),
            os.path.join(os.path.dirname(__file__), "packaging", "app_icon.ico"),
            os.path.join(os.getcwd(), "packaging", "app_icon.ico"),
        ]
        for ip in icon_paths:
            if os.path.exists(ip):
                try:
                    self.root.iconbitmap(ip)
                    break
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

        # 全体共通フォント設定
        font_family = "Meiryo UI"
        style.configure(".", font=(font_family, 9), background=self.BG_MAIN, foreground=self.TEXT_BODY)
        
        # Frame
        style.configure("Main.TFrame", background=self.BG_MAIN)
        style.configure("Card.TFrame", background=self.BG_CARD, relief="solid", borderwidth=1)
        
        # Treeview (履歴テーブル)
        style.configure(
            "Custom.Treeview.Heading",
            font=(font_family, 9, "bold"),
            background=self.BG_HEADER,
            foreground=self.TEXT_TITLE,
            relief="flat",
            padding=5
        )
        style.map("Custom.Treeview.Heading", background=[("active", "#d5e2f0")])
        style.configure(
            "Custom.Treeview",
            font=(font_family, 9),
            background=self.BG_CARD,
            fieldbackground=self.BG_CARD,
            foreground=self.TEXT_BODY,
            rowheight=25,
            relief="solid",
            borderwidth=1
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", "#d2e4f8")],
            foreground=[("selected", "#0a2850")]
        )

        # ボタンのスタイル定義
        style.configure(
            "Primary.TButton",
            font=(font_family, 9, "bold"),
            background=self.ACCENT_BLUE,
            foreground="#ffffff",
            borderwidth=0,
            padding=(16, 6)
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.ACCENT_BLUE_HOVER), ("pressed", "#0f2d5e")],
            foreground=[("active", "#ffffff")]
        )

        style.configure(
            "Secondary.TButton",
            font=(font_family, 9),
            background="#ffffff",
            foreground=self.ACCENT_BLUE,
            relief="solid",
            borderwidth=1,
            padding=(12, 5)
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#e8f0fe"), ("pressed", "#d2e3fc")],
            foreground=[("active", "#103875")]
        )

        style.configure(
            "Danger.TButton",
            font=(font_family, 9),
            background="#ffffff",
            foreground="#b91c1c",
            relief="solid",
            borderwidth=1,
            padding=(10, 5)
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#fee2e2"), ("pressed", "#fecaca")],
            foreground=[("active", "#991b1b")]
        )

        # メインフレーム
        main_frame = ttk.Frame(self.root, style="Main.TFrame", padding="16 12 16 12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------
        # 1. ヘッダーエリア（タイトル ＆ サブテキスト）
        # ----------------------------------------------------
        header_frame = tk.Frame(main_frame, bg=self.BG_MAIN)
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))

        title_label = tk.Label(
            header_frame,
            text="SAP-net 実験ログフォルダ選択",
            font=(font_family, 12, "bold"),
            bg=self.BG_MAIN,
            fg=self.TEXT_TITLE
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = tk.Label(
            header_frame,
            text="可視化対象のシミュレーションログ（*.jsonl.gz / *.jsonl）が格納されたフォルダを指定してください。",
            font=(font_family, 9),
            bg=self.BG_MAIN,
            fg=self.TEXT_MUTED
        )
        subtitle_label.pack(anchor=tk.W, pady=(2, 0))

        # 区切りライン
        sep_line = tk.Frame(main_frame, height=2, bg=self.BORDER_COLOR)
        sep_line.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        # ----------------------------------------------------
        # 2. フォルダ指定入力カード
        # ----------------------------------------------------
        input_card = tk.Frame(main_frame, bg=self.BG_CARD, highlightbackground=self.BORDER_COLOR, highlightthickness=1, padx=12, pady=8)
        input_card.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        lbl_folder_title = tk.Label(
            input_card,
            text="フォルダパス指定",
            font=(font_family, 9, "bold"),
            bg=self.BG_CARD,
            fg=self.TEXT_TITLE
        )
        lbl_folder_title.pack(anchor=tk.W, pady=(0, 4))

        entry_row = tk.Frame(input_card, bg=self.BG_CARD)
        entry_row.pack(fill=tk.X)

        self.path_var = tk.StringVar(value="")
        self.entry_path = tk.Entry(
            entry_row,
            textvariable=self.path_var,
            font=(font_family, 9),
            bg="#fdfefe",
            fg=self.TEXT_PLACEHOLDER,
            relief=tk.SOLID,
            bd=1,
            highlightthickness=1,
            highlightcolor=self.BORDER_FOCUS,
            highlightbackground="#d0dbe8"
        )
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)

        self.entry_path.bind("<FocusIn>", self._on_entry_focus_in)
        self.entry_path.bind("<FocusOut>", self._on_entry_focus_out)

        btn_browse = ttk.Button(entry_row, text="参照 (Browse)...", style="Secondary.TButton", command=self._on_browse)
        btn_browse.pack(side=tk.RIGHT)

        # 初期プレースホルダー適用
        self._apply_placeholder()

        # ----------------------------------------------------
        # 3. フッター・アクションボタンエリア（※下部に固定配置）
        # ----------------------------------------------------
        bottom_frame = tk.Frame(main_frame, bg=self.BG_MAIN)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))

        # 左側ボタン（履歴管理）
        btn_delete = ttk.Button(bottom_frame, text="履歴から削除", style="Secondary.TButton", command=self._on_delete_selected)
        btn_delete.pack(side=tk.LEFT, padx=(0, 6))

        btn_clear = ttk.Button(bottom_frame, text="全履歴クリア", style="Danger.TButton", command=self._on_clear_all)
        btn_clear.pack(side=tk.LEFT)

        # 右側ボタン（アクション）
        btn_cancel = ttk.Button(bottom_frame, text="キャンセル (Esc)", style="Secondary.TButton", command=self._on_cancel)
        btn_cancel.pack(side=tk.RIGHT, padx=(8, 0))

        btn_open = ttk.Button(bottom_frame, text="開く (Open)", style="Primary.TButton", command=self._on_confirm)
        btn_open.pack(side=tk.RIGHT)

        # ----------------------------------------------------
        # 4. 最近選択したフォルダ履歴カード（中央領域を可変拡張）
        # ----------------------------------------------------
        history_card = tk.Frame(main_frame, bg=self.BG_CARD, highlightbackground=self.BORDER_COLOR, highlightthickness=1, padx=12, pady=8)
        history_card.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        history_title_row = tk.Frame(history_card, bg=self.BG_CARD)
        history_title_row.pack(fill=tk.X, pady=(0, 4))

        lbl_history_title = tk.Label(
            history_title_row,
            text="最近選択した実験ログフォルダの履歴 (Recent Folders)",
            font=(font_family, 9, "bold"),
            bg=self.BG_CARD,
            fg=self.TEXT_TITLE
        )
        lbl_history_title.pack(side=tk.LEFT)

        lbl_history_hint = tk.Label(
            history_title_row,
            text="※ ダブルクリックまたは Enter で即座に開きます",
            font=(font_family, 8),
            bg=self.BG_CARD,
            fg=self.TEXT_MUTED
        )
        lbl_history_hint.pack(side=tk.RIGHT)

        # Treeview + Scrollbars コンテナ
        tree_container = tk.Frame(history_card, bg=self.BG_CARD)
        tree_container.pack(fill=tk.BOTH, expand=True)

        columns = ("folder_name", "last_opened", "status", "path")
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Custom.Treeview",
            height=8
        )

        self.tree.heading("folder_name", text="フォルダ名", anchor=tk.W)
        self.tree.heading("last_opened", text="最終アクセス日時", anchor=tk.W)
        self.tree.heading("status", text="状態", anchor=tk.CENTER)
        self.tree.heading("path", text="フルパス", anchor=tk.W)

        self.tree.column("folder_name", width=180, minwidth=110, anchor=tk.W)
        self.tree.column("last_opened", width=140, minwidth=120, anchor=tk.W)
        self.tree.column("status", width=120, minwidth=90, anchor=tk.CENTER)
        self.tree.column("path", width=340, minwidth=180, anchor=tk.W)

        vsb = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)

        # イベントバインド
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Return>", lambda e: self._on_confirm())
        self.tree.bind("<Delete>", lambda e: self._on_delete_selected())
        self.root.bind("<Escape>", lambda e: self._on_cancel())

        # 履歴データの読み込み・描画
        self._refresh_tree()

        # 初期フォーカス設定
        self.tree.focus_set()

        # ウィンドウ終了ハンドラ
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.root.mainloop()

        return self.selected_folder

    def _apply_placeholder(self):
        """プレースホルダー（半透明・グレー文字）を適用"""
        self.placeholder_active = True
        if self.path_var is not None:
            self.path_var.set(self.placeholder_text)
        if self.entry_path is not None:
            self.entry_path.config(fg=self.TEXT_PLACEHOLDER)

    def _clear_placeholder(self):
        """プレースホルダーを解除して通常編集状態にする"""
        if self.placeholder_active:
            self.placeholder_active = False
            if self.path_var is not None:
                self.path_var.set("")
            if self.entry_path is not None:
                self.entry_path.config(fg=self.TEXT_BODY)

    def _set_entry_path(self, path_str: str):
        """パス文字列を入力欄に確実に設定（通常文字色）"""
        self.placeholder_active = False
        if self.path_var is not None:
            self.path_var.set(path_str)
        if self.entry_path is not None:
            self.entry_path.config(fg=self.TEXT_BODY)

    def _get_entry_path(self) -> str:
        """入力欄から有効なパスを取得（プレースホルダー表示時は空文字を返す）"""
        if self.placeholder_active:
            return ""
        if self.path_var is None:
            return ""
        return self.path_var.get().strip()

    def _on_entry_focus_in(self, event):
        """入力欄フォーカス取得時"""
        if self.placeholder_active:
            self._clear_placeholder()

    def _on_entry_focus_out(self, event):
        """入力欄フォーカス喪失時"""
        if not self.path_var.get().strip():
            self._apply_placeholder()

    def _refresh_tree(self):
        """Treeviewの表示を更新"""
        if not self.tree:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        items = self.history_mgr.get_detailed_history()
        for idx, it in enumerate(items):
            tags = ()
            if not it["exists"]:
                tags = ("missing",)
            elif not it["log_found"]:
                tags = ("no_log",)
            else:
                tags = ("ok",)

            self.tree.insert(
                "",
                tk.END,
                values=(it["folder_name"], it["last_opened"], it["status"], it["path"]),
                tags=tags
            )

        self.tree.tag_configure("missing", foreground=self.STATUS_ERR_FG)
        self.tree.tag_configure("no_log", foreground=self.STATUS_WARN_FG)
        self.tree.tag_configure("ok", foreground=self.STATUS_OK_FG)

    def _on_browse(self):
        """OS標準のフォルダ選択ダイアログを開く（選択中フォルダの親階層を初期表示）"""
        current_input = self._get_entry_path()
        init_dir = None

        if current_input:
            abs_input = os.path.abspath(current_input)
            parent_dir = os.path.dirname(abs_input)
            # 親ディレクトリが存在し、かつ元のパスと異なる（ルート直下等でない）場合は親を優先
            if parent_dir and parent_dir != abs_input and os.path.exists(parent_dir) and os.path.isdir(parent_dir):
                init_dir = parent_dir
            elif os.path.exists(abs_input) and os.path.isdir(abs_input):
                init_dir = abs_input

        if not init_dir or not os.path.exists(init_dir):
            if self.initial_dir and os.path.exists(self.initial_dir):
                abs_init = os.path.abspath(self.initial_dir)
                parent_init = os.path.dirname(abs_init)
                if parent_init and parent_init != abs_init and os.path.exists(parent_init) and os.path.isdir(parent_init):
                    init_dir = parent_init
                else:
                    init_dir = abs_init
            else:
                init_dir = os.getcwd()

        selected = filedialog.askdirectory(
            title="SAP-net 実験ログフォルダの選択",
            initialdir=init_dir,
            parent=self.root
        )
        if selected:
            norm_path = os.path.abspath(selected)
            self._set_entry_path(norm_path)
            if self.entry_path:
                self.entry_path.icursor(tk.END)
                self.entry_path.focus_set()

    def _on_tree_select(self, event):
        """履歴リスト選択時にパス入力欄を更新"""
        if not self.tree:
            return
        selected_items = self.tree.selection()
        if selected_items:
            vals = self.tree.item(selected_items[0], "values")
            if vals and len(vals) >= 4:
                selected_path = vals[3]
                self._set_entry_path(selected_path)

    def _on_tree_double_click(self, event):
        """ダブルクリックで即座に決定"""
        self._on_confirm()

    def _on_delete_selected(self):
        """選択された履歴行を削除"""
        if not self.tree:
            return
        selected_items = self.tree.selection()
        if not selected_items:
            return
        vals = self.tree.item(selected_items[0], "values")
        if vals and len(vals) >= 4:
            target_path = vals[3]
            self.history_mgr.remove_folder(target_path)
            self._refresh_tree()
            if self._get_entry_path() == target_path:
                self._apply_placeholder()

    def _on_clear_all(self):
        """すべての履歴をクリア"""
        if not self.tree or not self.tree.get_children():
            return
        confirm = messagebox.askyesno(
            "履歴の全消去",
            "シミュレーションフォルダの選択履歴をすべて消去しますか？",
            parent=self.root
        )
        if confirm:
            self.history_mgr.clear_history()
            self._refresh_tree()
            self._apply_placeholder()

    def _on_confirm(self):
        """「開く」決定処理"""
        target_path = self._get_entry_path()
        if not target_path and self.tree:
            selected_items = self.tree.selection()
            if selected_items:
                vals = self.tree.item(selected_items[0], "values")
                if vals and len(vals) >= 4:
                    target_path = vals[3]

        if not target_path:
            messagebox.showwarning(
                "フォルダ未選択",
                "対象の実験ログフォルダが指定されていません。\nフォルダを選択するか、パスを入力してください。",
                parent=self.root
            )
            return

        abs_path = os.path.abspath(target_path)
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            messagebox.showerror(
                "フォルダ検出エラー",
                f"指定されたフォルダが存在しません:\n{abs_path}",
                parent=self.root
            )
            return

        self.selected_folder = abs_path
        if self.root:
            self.root.destroy()
            self.root = None

    def _on_cancel(self):
        """キャンセル処理"""
        self.selected_folder = None
        if self.root:
            self.root.destroy()
            self.root = None


def select_simulation_folder(initial_dir: Optional[str] = None, parent=None) -> Optional[str]:
    """
    シミュレーションログフォルダ選択ダイアログを表示し、選択されたパスを返す便利関数。
    """
    dialog = FolderSelectorDialog(initial_dir=initial_dir)
    return dialog.show()


if __name__ == "__main__":
    print("[TEST] Launching styled FolderSelectorDialog...")
    folder = select_simulation_folder()
    print(f"[TEST] Result: {folder}")
