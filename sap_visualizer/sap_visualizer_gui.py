import sys
import math
import os
import datetime
import re
import numpy as np

# PygameまたはTkinter/MatplotlibのUI構築
try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

# ファイル選択ダイアログ用
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

try:
    from .folder_selector_gui import select_simulation_folder, FolderHistoryManager
except ImportError:
    from folder_selector_gui import select_simulation_folder, FolderHistoryManager


class SAPVisualizerGUI:
    """
    SAP-netの動的パラメータをグラフィカルに表示し、
    コマ送り、コマ戻し、各種イベントスキップ、巻き戻し再生操作およびログファイル選択操作を提供するGUIクラス。
    """
    def __init__(self, logger, window_width=920, window_height=690):
        self.logger = logger
        self.width = window_width
        self.height = window_height
        self.current_index = 0
        self.is_playing = False
        self.live_follow = True  # シミュレーション進行中の最新フレームリアルタイム自動追従フラグ
        self.is_active = True    # 可視化ウィンドウの表示状態フラグ（閉じられた場合は False）
        self.show_help = False   # ヘルプ・操作ガイドオーバーレイ表示フラグ
        self.show_config = False # ハイパーパラメータ表示フラグ
        self.config_scroll_y = 0  # ハイパーパラメータ確認画面の垂直スクロール位置
        self.max_config_scroll = 0 # スクロール最大可能量
        self.header_scroll_offset = 0.0 # サブヘッダー情報の動的水平スクロールオフセット
        self.header_scroll_dir = 1.0    # スクロール移動方向 (1.0: 左へ, -1.0: 右へ)
        self.header_scroll_pause_timer = 0 # スクロール端での一時停止タイマー
        self.play_speed = 1.0  # 再生速度 (1.0 = 標準)
        self.view_mode = "STEP"  # 表示モード: "STEP" (ネットワーク/棒グラフ) または "LINE_CHART" (折れ線グラフ)
        self.visible_nodes = {}  # 知識別折れ線グラフの表示・非表示フラグ辞書 {node_index: bool}
        
        # 知識別折れ線グラフ用マルチカラーパレット (視認性の高い20色)
        self.node_colors = [
            (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189),
            (140, 86, 75), (227, 119, 194), (127, 127, 127), (188, 189, 34), (23, 190, 207),
            (255, 152, 150), (174, 199, 232), (152, 223, 138), (197, 176, 213), (196, 156, 148),
            (247, 182, 210), (199, 199, 199), (219, 219, 141), (158, 218, 229), (255, 187, 120)
        ]
        
        self.has_pygame = HAS_PYGAME
        if not self.has_pygame:
            print("[WARNING] Pygame is not installed. Graphical GUI window will run in text/console mode.")
            return

        pygame.init()
        pygame.display.set_caption("SAP-net Visualizer")
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        
        # 日本語表示対応フォントのリスト (Windows: meiryo, msgothic / Mac: hiragino / Linux: takao)
        font_names = ["meiryo", "msgothic", "yugothic", "hiragino sans", "takao gothic", "arial"]
        self.font_tiny = pygame.font.SysFont(font_names, 11, bold=True)
        self.font_small = pygame.font.SysFont(font_names, 13)
        self.font_medium = pygame.font.SysFont(font_names, 15, bold=True)
        self.font_title = pygame.font.SysFont(font_names, 18, bold=True)
        
        # ボタン定義をウィンドウ幅に合わせて動的均等計算して初期化
        self._setup_buttons()
        
        # ヘッダー領域ボタン (画面切り替えボタン ＆ 実験ログフォルダ選択ボタン)
        self.view_btn_rect = pygame.Rect(560, 10, 130, 30)
        self.header_btn_rect = pygame.Rect(700, 10, 200, 30)

        # 活性値推移折れ線グラフおよびトグル凡例領域
        self.chart_rect = pygame.Rect(50, 80, 680, 435)
        self.btn_all_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_none_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_save_chart_rect = pygame.Rect(0, 0, 0, 0)
        self.node_toggle_rects = []

        # トースト通知用メッセージ＆タイマー
        self.toast_msg = ""
        self.toast_timer = 0

        # スライダー領域 (左右マージン 20px)
        self.slider_rect = pygame.Rect(20, 550, self.width - 40, 15)
        self.is_dragging_slider = False

    def get_resolved_frame_info(self, frame_index):
        """
        指定したフレームインデックスにおける動的パラメータ情報を取得する。
        A や weight, plan, selectplans が空・None（イベント行等）の場合は直前の有効フレームからフォールバック復元する。
        戻り値:
            plan (int or None): 選択中の知識番号
            selectplans (list[int]): 転移候補知識フラグ (0/1配列)
            A (list[float]): 活性値リスト
            weight (list[list[float]]): 重み行列
            episode (int): エピソード番号
            step (int): ステップ番号
            event_type (str): イベント種別
        """
        if not self.logger.history or not (0 <= frame_index < len(self.logger.history)):
            return None, [], [], [], 0, 0, ""

        frame = self.logger.history[frame_index]
        plan = frame.get("plan")
        selectplans = frame.get("selectplans", [])
        A_raw = frame.get("A", [])
        weight_raw = frame.get("weight", [])
        episode = frame.get("episode", 0)
        step = frame.get("step", 0)
        event_type = frame.get("event_type", "STEP")

        # 未設定フィールドを過去フレームに遡って探索
        if plan is None or not A_raw or not weight_raw or not selectplans:
            for p_idx in range(frame_index - 1, -1, -1):
                p_fr = self.logger.history[p_idx]
                if plan is None and p_fr.get("plan") is not None:
                    plan = p_fr.get("plan")
                if not A_raw and p_fr.get("A"):
                    A_raw = p_fr.get("A")
                if not selectplans and p_fr.get("selectplans"):
                    selectplans = p_fr.get("selectplans", [])
                if not weight_raw and p_fr.get("weight"):
                    weight_raw = p_fr.get("weight", [])
                
                # すべて取得できたら早期終了
                if plan is not None and len(A_raw) > 0 and len(weight_raw) > 0 and len(selectplans) > 0:
                    break

        return plan, selectplans, A_raw, weight_raw, episode, step, event_type

    def _setup_buttons(self):
        """ウィンドウ幅に合わせて2段のボタンレイアウト（上段8個・下段7個）を動的に均等計算して構築"""
        margin_left = 20
        margin_right = 20
        avail_w = self.width - margin_left - margin_right

        # 上段: イベントジャンプ 8個 (すべて日本語表記へ統一)
        row1_items = [
            ("|< エピソード", "prev_ep"),
            ("エピソード >|", "next_ep"),
            ("|< 知識選択", "prev_plan"),
            ("知識選択 >|", "next_plan"),
            ("|< 活性化", "prev_act"),
            ("活性化 >|", "next_act"),
            ("|< 重み更新", "prev_weight"),
            ("重み更新 >|", "next_weight"),
        ]
        gap1 = 8
        n1 = len(row1_items)
        w1 = (avail_w - (n1 - 1) * gap1) // n1
        y1 = 578
        h1 = 30

        # 下段: 再生 ＆ システム 7個 (テキスト長に応じた可変カスタム幅設定)
        row2_items = [
            ("<< コマ戻し", "step_back", 110),
            ("再生/一時停止", "toggle_play", 115),
            ("コマ送り >>", "step_forward", 110),
            ("リアルタイム追従", "toggle_live", 125),
            ("ハイパーパラメータ", "toggle_config", 145),
            ("ヘルプ", "toggle_help", 105),
            ("リセット", "reset_index", 110),
        ]
        gap2 = 10
        y2 = 622
        h2 = 35

        self.buttons = []

        # 上段ボタンの登録
        for i, (label, action) in enumerate(row1_items):
            bx = margin_left + i * (w1 + gap1)
            self.buttons.append(((bx, y1, w1, h1), label, action))

        # 下段ボタンの登録
        curr_x2 = margin_left
        for label, action, bw in row2_items:
            self.buttons.append(((curr_x2, y2, bw, h2), label, action))
            curr_x2 += bw + gap2

    def open_folder_dialog(self):
        """GUIのシミュレーションフォルダ選択画面（履歴一覧・ファイルダイアログ）を開き、指定された実験ログフォルダから各種ファイルを一括読み込む"""
        if not HAS_TKINTER:
            print("[WARNING] Tkinter is not available for folder dialog.")
            return

        log_filepath = getattr(self.logger, 'log_file_path', None)
        init_dir = os.path.dirname(log_filepath) if (log_filepath and os.path.exists(log_filepath)) else os.getcwd()

        try:
            folder_path = select_simulation_folder(initial_dir=init_dir)

            if folder_path:
                if self.logger.load_from_folder(folder_path):
                    self.current_index = 0
                    self.is_playing = False
                    self.live_follow = False  # フォルダ読み込み時は手動閲覧モードに
                    print(f"[INFO] Successfully loaded experiment folder: {folder_path}")

                    # 選択履歴マネージャーへ保存
                    try:
                        history_mgr = FolderHistoryManager()
                        history_mgr.add_folder(folder_path)
                    except Exception as h_err:
                        print(f"[WARNING] Could not save folder to history: {h_err}")

                    # ハイパーパラメータ設定ファイル (config_used_*.yaml) の存在・読み込みチェック
                    _, yaml_loaded = self.load_config_data(return_status=True)
                    if not yaml_loaded:
                        w_root = tk.Tk()
                        w_root.withdraw()
                        w_root.attributes('-topmost', True)
                        messagebox.showwarning(
                            "設定ファイル読み込み通知",
                            f"動的パラメータログの読み込みは成功しましたが、以下のファイルを開くことができませんでした。\n\n"
                            f"■ 開けなかったファイル種別:\n"
                            f"  【ハイパーパラメータ設定ファイル (config_used_*.yaml)】\n\n"
                            f"■ 詳細:\n"
                            f"  フォルダ内に該当するYAML設定ファイルが存在しないか、パースエラーが発生しました。\n"
                            f"  ※可視化表示はデフォルト/動的フォールバック表示で継続します。\n\n"
                            f"対象フォルダ:\n{folder_path}"
                        )
                        w_root.destroy()
                else:
                    # ログファイル自体の読み込み失敗（メッセージボックスを表示してエラー通知）
                    err_msg = getattr(self.logger, "last_error_msg", "ファイルが開けませんでした。")
                    file_type = getattr(self.logger, "last_missing_file_type", "SAP動的パラメータログファイル (*.jsonl.gz / *.jsonl)")

                    e_root = tk.Tk()
                    e_root.withdraw()
                    e_root.attributes('-topmost', True)
                    messagebox.showerror(
                        "ログフォルダ読み込みエラー",
                        f"選択されたフォルダから必要なファイルを開くことができませんでした。\n\n"
                        f"■ 開けなかったファイル種別:\n"
                        f"  【{file_type}】\n\n"
                        f"■ エラー詳細:\n"
                        f"  {err_msg}\n\n"
                        f"対象フォルダ:\n{folder_path}"
                    )
                    e_root.destroy()
        except Exception as e:
            print(f"[ERROR] Failed to open folder dialog: {e}")

    def save_chart_image(self):
        """学術・報告用途に適した独立キャンバス（グラフ ＋ 凡例）を高精細PNGとしてファイル選択ダイアログ経由で保存"""
        if self.view_mode != "LINE_CHART":
            return

        total_frames = len(self.logger.history)
        if total_frames <= 1:
            print("[WARNING] Cannot export chart image: Insufficient log frames.")
            self.toast_msg = "ログデータが不足しています"
            self.toast_timer = 150
            return

        # 1. 読み込み中のログファイルからタイムスタンプを抽出
        log_filepath = getattr(self.logger, 'log_file_path', None) or getattr(self.logger, 'log_file', None)
        log_filename = os.path.basename(log_filepath) if log_filepath else ""
        save_dir = os.path.dirname(log_filepath) if (log_filepath and os.path.exists(log_filepath)) else os.getcwd()

        log_timestamp = None
        if log_filename:
            match = re.search(r'(\d{8}_\d{6})', log_filename)
            if match:
                log_timestamp = match.group(1)
        
        if not log_timestamp:
            log_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        default_filename = f"sap_chart_{log_timestamp}.png"

        # 2. 保存場所選択ウィンドウ（ファイルダイアログ）の表示
        save_path = None
        if HAS_TKINTER:
            try:
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                save_path = filedialog.asksaveasfilename(
                    title="Save Chart Image",
                    initialdir=save_dir,
                    initialfile=default_filename,
                    defaultextension=".png",
                    filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
                )
                root.destroy()
            except Exception as e:
                print(f"[WARNING] File dialog failed: {e}")

        if not save_path:
            return  # キャンセル時

        # 3. 独立した描画キャンバスの準備 & 凡例領域のレイアウト計算
        export_w = 900
        gx, gy, gw, gh = 70, 25, 800, 420

        # データから総ノード数の計算および表示ノードのリストアップ
        num_nodes = 0
        if total_frames > 0:
            for f in self.logger.history:
                if f.get("A"):
                    num_nodes = max(num_nodes, len(f["A"]))

        vis_node_indices = [i for i in range(num_nodes) if self.visible_nodes.get(i, True)]

        # 下部凡例レイアウトの事前面積・高さ計算 (各行中央揃え)
        legend_start_y = gy + gh + 58
        row_h = 24
        
        # 1. アイテムを行ごとにグループ化
        rows = []
        current_row = []
        current_row_w = 0

        for i in vis_node_indices:
            label_str = f"知識 {i}"
            lbl_w, _ = self.font_small.size(label_str)
            item_w = 16 + lbl_w + 18  # 色丸(16px) + ラベル幅 + 項目間余白(18px)

            if current_row and (current_row_w + item_w > gw):
                rows.append((current_row, current_row_w))
                current_row = [(i, item_w, label_str)]
                current_row_w = item_w
            else:
                current_row.append((i, item_w, label_str))
                current_row_w += item_w

        if current_row:
            rows.append((current_row, current_row_w))

        # 2. 各行ごとに中央揃え (Center Alignment) 座標を計算
        legend_items = []
        cur_y = legend_start_y
        for r_items, r_width in rows:
            actual_w = max(0, r_width - 18)
            start_x = gx + (gw - actual_w) // 2
            
            cur_x = start_x
            for i, item_w, label_str in r_items:
                legend_items.append((i, cur_x, cur_y, label_str))
                cur_x += item_w
            cur_y += row_h

        export_h = max(520, cur_y + 12)
        surf = pygame.Surface((export_w, export_h))
        surf.fill((255, 255, 255))  # 純白背景

        # 4. グラフ領域背景 ＆ 枠線
        pygame.draw.rect(surf, (255, 255, 255), (gx, gy, gw, gh))
        pygame.draw.rect(surf, (150, 160, 175), (gx, gy, gw, gh), 2)

        # Y軸グリッド & 目盛り (0.0 〜 1.0)
        for y_val in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            cy = gy + gh - int(y_val * gh)
            pygame.draw.line(surf, (230, 235, 240), (gx, cy), (gx + gw, cy), 1)
            lbl = self.font_small.render(f"{y_val:.1f}", True, (80, 90, 100))
            surf.blit(lbl, (gx - 35, cy - 7))

        # Y軸ラベル (反時計回りに90度回転)
        y_axis_lbl = self.font_small.render("活性度 A", True, (60, 70, 80))
        y_axis_lbl_rot = pygame.transform.rotate(y_axis_lbl, 90)
        surf.blit(y_axis_lbl_rot, (gx - 48, gy + (gh - y_axis_lbl_rot.get_height()) // 2))

        # X軸グリッド & 目盛り (フレームインデックス)
        num_x_ticks = min(10, total_frames)
        for t in range(num_x_ticks):
            idx = int(t * (total_frames - 1) / max(1, num_x_ticks - 1))
            cx = gx + int((idx / max(1, total_frames - 1)) * gw)
            pygame.draw.line(surf, (235, 238, 242), (cx, gy), (cx, gy + gh), 1)
            lbl = self.font_small.render(str(idx), True, (80, 90, 100))
            surf.blit(lbl, (cx - lbl.get_width() // 2, gy + gh + 6))

        # X軸ラベル
        x_axis_lbl = self.font_small.render("フレーム数 (Step)", True, (60, 70, 80))
        surf.blit(x_axis_lbl, (gx + (gw - x_axis_lbl.get_width()) // 2, gy + gh + 28))

        # 5. 各ノードの折れ線描画 (表示オンのノードのみ ＆ 高速化ストライド)
        stride = max(1, total_frames // (gw * 2))
        indices = list(range(0, total_frames, stride))
        if indices[-1] != total_frames - 1:
            indices.append(total_frames - 1)

        for i in vis_node_indices:
            points = []
            c_color = self.node_colors[i % len(self.node_colors)]
            for frame_idx in indices:
                f = self.logger.history[frame_idx]
                A = f.get("A", [])
                if i < len(A):
                    val = max(0.0, min(1.0, float(A[i])))
                    px = gx + int((frame_idx / max(1, total_frames - 1)) * gw)
                    py = gy + gh - int(val * gh)
                    points.append((px, py))
            
            if len(points) >= 2:
                pygame.draw.lines(surf, c_color, False, points, 2)

        # 6. 下部横並び凡例 (Legend) のプロット
        for i, ix, iy, label_str in legend_items:
            c_color = self.node_colors[i % len(self.node_colors)]
            pygame.draw.circle(surf, c_color, (ix + 6, iy + 10), 5)
            k_txt = self.font_small.render(label_str, True, (30, 40, 55))
            surf.blit(k_txt, (ix + 16, iy + 2))

        # 7. 画像ファイルの書き出し
        try:
            pygame.image.save(surf, save_path)
            out_filename = os.path.basename(save_path)
            print(f"[INFO] Exported standalone chart image successfully: {save_path}")
            if HAS_TKINTER:
                try:
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    messagebox.showinfo("保存完了", f"グラフ画像を保存しました。\n\nファイル名: {out_filename}")
                    root.destroy()
                except Exception:
                    pass
        except Exception as e:
            print(f"[ERROR] Failed to export chart image: {e}")
            if HAS_TKINTER:
                try:
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    messagebox.showerror("保存エラー", f"画像の保存に失敗しました:\n{e}")
                    root.destroy()
                except Exception:
                    pass

    def handle_events(self):
        """ユーザー入力イベント（キーボード・マウス操作）の処理"""
        if not self.has_pygame or not self.is_active:
            return True

        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_active = False
                    try:
                        pygame.quit()
                    except Exception:
                        pass
                    print("[INFO] SAP-net Visualizer window closed.")
                    return True

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button in (4, 5):  # マウスホイール操作によるスクロール
                        if self.show_config:
                            scroll_step = 40
                            if event.button == 4:  # 上スクロール
                                self.config_scroll_y = max(0, self.config_scroll_y - scroll_step)
                            elif event.button == 5:  # 下スクロール
                                self.config_scroll_y = min(getattr(self, "max_config_scroll", 0), self.config_scroll_y + scroll_step)
                            continue

                    elif event.button == 1:
                        pos = event.pos

                        # ヘルプ画面表示中かつダイアログ外側の黒い背景をクリックした場合に閉じる
                        if self.show_help:
                            help_dlg_rect = pygame.Rect(30, 25, 860, 635)
                            help_btn_rect = None
                            for rect_tuple, label, action in self.buttons:
                                if action == "toggle_help":
                                    help_btn_rect = pygame.Rect(*rect_tuple)
                                    break
                            
                            if not help_dlg_rect.collidepoint(pos):
                                if help_btn_rect and help_btn_rect.collidepoint(pos):
                                    self.execute_action("toggle_help")
                                else:
                                    self.show_help = False
                                continue

                        # ハイパーパラメータ画面表示中かつダイアログ外側の黒い背景をクリックした場合に閉じる
                        if self.show_config:
                            cfg_dlg_rect = pygame.Rect(30, 25, 860, 635)
                            cfg_btn_rect = None
                            for rect_tuple, label, action in self.buttons:
                                if action == "toggle_config":
                                    cfg_btn_rect = pygame.Rect(*rect_tuple)
                                    break
                            
                            if not cfg_dlg_rect.collidepoint(pos):
                                if cfg_btn_rect and cfg_btn_rect.collidepoint(pos):
                                    self.execute_action("toggle_config")
                                else:
                                    self.show_config = False
                                continue

                        # ヘッダー領域「ビュー切替」ボタンクリック判定
                        if self.view_btn_rect.collidepoint(pos):
                            self.toggle_view()
                            continue

                        # ヘッダー右側「実験ログフォルダを開く」ボタンクリック判定
                        if self.header_btn_rect.collidepoint(pos):
                            self.open_folder_dialog()
                            continue

                        # 活性値推移（折れ線グラフ）画面でのインタラクティブクリック判定
                        if self.view_mode == "LINE_CHART":
                            # 折れ線グラフエリアのクリック（クリック位置へのステップジャンプ）
                            if self.chart_rect.collidepoint(pos):
                                total_frames = len(self.logger.history)
                                if total_frames > 0:
                                    rel_x = max(0, min(pos[0] - self.chart_rect.x, self.chart_rect.width))
                                    ratio = rel_x / float(self.chart_rect.width)
                                    self.current_index = int(ratio * (total_frames - 1))
                                    self.live_follow = False
                                continue

                            # トグル凡例パネル「全選択」ボタンクリック
                            if self.btn_all_rect.collidepoint(pos):
                                self.toggle_all_nodes_visibility(True)
                                continue

                            # トグル凡例パネル「全解除」ボタンクリック
                            if self.btn_none_rect.collidepoint(pos):
                                self.toggle_all_nodes_visibility(False)
                                continue

                            # トグル凡例パネル「グラフ保存」ボタンクリック
                            if self.btn_save_chart_rect.collidepoint(pos):
                                self.save_chart_image()
                                continue

                            # 各知識の表示/非表示トグルボタンクリック
                            clicked_node = False
                            for node_idx, node_r in self.node_toggle_rects:
                                if node_r.collidepoint(pos):
                                    self.visible_nodes[node_idx] = not self.visible_nodes.get(node_idx, True)
                                    clicked_node = True
                                    break
                            if clicked_node:
                                continue

                        # 通常のボタンクリック判定
                        for rect_tuple, label, action in self.buttons:
                            r = pygame.Rect(*rect_tuple)
                            if r.collidepoint(pos):
                                self.execute_action(action)
                                break
                        # スライダークリック
                        if self.slider_rect.collidepoint(pos):
                            self.is_dragging_slider = True
                            self.update_slider_position(pos[0])

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.is_dragging_slider = False

                elif event.type == pygame.MOUSEMOTION:
                    if self.is_dragging_slider:
                        self.update_slider_position(event.pos[0])

                elif event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    is_shift = bool(mods & pygame.KMOD_SHIFT)

                    if event.key == pygame.K_g:
                        self.toggle_view()
                    elif event.key == pygame.K_s:
                        if self.view_mode == "LINE_CHART":
                            self.save_chart_image()
                    elif event.key == pygame.K_LEFT:
                        self.step_back()
                    elif event.key == pygame.K_RIGHT:
                        self.step_forward()
                    elif event.key == pygame.K_SPACE:
                        self.toggle_play()
                    elif event.key == pygame.K_e:
                        if is_shift:
                            self.prev_event("NEW_EPISODE")
                        else:
                            self.next_event("NEW_EPISODE")
                    elif event.key == pygame.K_p:
                        if is_shift:
                            self.prev_event("SELECT_PLAN")
                        else:
                            self.next_event("SELECT_PLAN")
                    elif event.key == pygame.K_a:
                        if is_shift:
                            self.prev_event("ACTIVATION")
                        else:
                            self.next_event("ACTIVATION")
                    elif event.key == pygame.K_w:
                        if is_shift:
                            self.prev_event("WEIGHT_UPDATE")
                        else:
                            self.next_event("WEIGHT_UPDATE")
                    elif event.key == pygame.K_o:
                        self.open_folder_dialog()
                    elif event.key == pygame.K_l:
                        self.toggle_live()
                    elif event.key == pygame.K_c:
                        self.toggle_config()
                    elif event.key == pygame.K_h or event.key == pygame.K_SLASH or event.key == pygame.K_ESCAPE:
                        if self.show_config:
                            self.show_config = False
                        else:
                            self.toggle_help()
        except Exception as e:
            self.is_active = False
            return True

        return True

    def execute_action(self, action):
        if action == "step_back":
            self.step_back()
        elif action == "step_forward":
            self.step_forward()
        elif action == "toggle_play":
            self.toggle_play()
        elif action == "prev_ep":
            self.prev_event("NEW_EPISODE")
        elif action == "next_ep":
            self.next_event("NEW_EPISODE")
        elif action == "prev_plan":
            self.prev_event("SELECT_PLAN")
        elif action == "next_plan":
            self.next_event("SELECT_PLAN")
        elif action == "prev_act":
            self.prev_event("ACTIVATION")
        elif action == "next_act":
            self.next_event("ACTIVATION")
        elif action == "prev_weight":
            self.prev_event("WEIGHT_UPDATE")
        elif action == "next_weight":
            self.next_event("WEIGHT_UPDATE")
        elif action == "open_file" or action == "open_folder":
            self.open_folder_dialog()
        elif action == "toggle_live":
            self.toggle_live()
        elif action == "toggle_config":
            self.toggle_config()
        elif action == "toggle_help":
            self.toggle_help()
        elif action == "toggle_view":
            self.toggle_view()
        elif action == "reset_index":
            self.live_follow = False
            self.current_index = 0

    def toggle_view(self):
        """ステップ表示画面と活性値推移グラフ画面の切替"""
        if self.view_mode == "STEP":
            self.view_mode = "LINE_CHART"
        else:
            self.view_mode = "STEP"

    def toggle_all_nodes_visibility(self, visible=True):
        """全知識の表示/非表示一括切り替え"""
        total_frames = len(self.logger.history)
        num_nodes = 0
        if total_frames > 0:
            for f in self.logger.history:
                if f.get("A"):
                    num_nodes = max(num_nodes, len(f["A"]))
        for i in range(max(10, num_nodes)):
            self.visible_nodes[i] = visible

    def toggle_config(self):
        """ハイパーパラメータ表示ダイアログのON/OFF切替"""
        self.show_config = not self.show_config
        if self.show_config:
            self.config_scroll_y = 0

    def toggle_help(self):
        """ヘルプ・操作ガイドオーバーレイのON/OFF切替"""
        self.show_help = not self.show_help

    def toggle_live(self):
        """最新ステップ自動追従 (Live Follow) のON/OFF切替"""
        self.live_follow = not self.live_follow
        if self.live_follow:
            self.is_playing = False
            total_frames = len(self.logger.history)
            if total_frames > 0:
                self.current_index = total_frames - 1

    def next_event(self, event_type):
        self.live_follow = False  # 手動操作時はLive追従をオフに
        self.current_index = self.logger.find_next_event_index(self.current_index, event_type)

    def prev_event(self, event_type):
        self.live_follow = False  # 手動操作時はLive追従をオフに
        self.current_index = self.logger.find_prev_event_index(self.current_index, event_type)

    def update_slider_position(self, mouse_x):
        self.live_follow = False  # 手動操作時はLive追従をオフに
        total_frames = len(self.logger.history)
        if total_frames <= 1:
            return
        rel_x = max(0, min(mouse_x - self.slider_rect.x, self.slider_rect.width))
        ratio = rel_x / float(self.slider_rect.width)
        self.current_index = int(ratio * (total_frames - 1))

    def step_forward(self):
        self.live_follow = False  # 手動操作時はLive追従をオフに
        if self.current_index < len(self.logger.history) - 1:
            self.current_index += 1

    def step_back(self):
        self.live_follow = False  # 手動操作時はLive追従をオフに
        if self.current_index > 0:
            self.current_index -= 1

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.live_follow = False

    def draw(self):
        """可視化画面のレンダリング"""
        if not self.has_pygame or not self.is_active:
            return

        try:
            self.screen.fill((240, 243, 246))
            total_frames = len(self.logger.history)
            
            # ライブ自動追従処理
            if self.live_follow and total_frames > 0:
                self.current_index = total_frames - 1

            # 進行処理（再生中）
            if self.is_playing and total_frames > 0:
                if self.current_index < total_frames - 1:
                    self.current_index += 1
                else:
                    self.is_playing = False

            frame = self.logger.get_frame(self.current_index) if total_frames > 0 else None
            
            # 1. タイトル ＆ ヘッダー情報 (すべて日本語表記へ統一)
            title_txt = self.font_title.render("SAP-net 動的パラメータ可視化ビューアー", True, (20, 30, 50))
            self.screen.blit(title_txt, (20, 12))

            # ヘッダー右側「ビュー切替」ボタンの描画
            v_btn_color = (255, 235, 180) if self.view_mode == "LINE_CHART" else (230, 240, 255)
            v_btn_border = (220, 140, 30) if self.view_mode == "LINE_CHART" else (60, 120, 200)
            pygame.draw.rect(self.screen, v_btn_color, self.view_btn_rect, border_radius=5)
            pygame.draw.rect(self.screen, v_btn_border, self.view_btn_rect, 2, border_radius=5)
            v_label = "活性値推移 (G)" if self.view_mode == "STEP" else "ステップ表示 (G)"
            v_txt = self.font_small.render(v_label, True, (30, 50, 90))
            v_rect = v_txt.get_rect(center=self.view_btn_rect.center)
            self.screen.blit(v_txt, v_rect)

            # ヘッダー右側「実験ログフォルダを開く」ボタンの描画
            h_btn_color = (255, 255, 255)
            h_btn_border = (60, 120, 200)
            pygame.draw.rect(self.screen, h_btn_color, self.header_btn_rect, border_radius=5)
            pygame.draw.rect(self.screen, h_btn_border, self.header_btn_rect, 2, border_radius=5)
            h_txt = self.font_small.render("実験ログフォルダを開く (O)", True, (30, 70, 140))
            h_rect = h_txt.get_rect(center=self.header_btn_rect.center)
            self.screen.blit(h_txt, h_rect)

            # リアルタイム追従 / マニュアル操作 インジケーター (「SAP動的ログを開く」ボタン直下に配置)
            mode_label = "● リアルタイム追従中" if self.live_follow else "■ マニュアル操作中"
            bg_color = (225, 245, 230) if self.live_follow else (255, 243, 220)
            border_color = (40, 160, 60) if self.live_follow else (210, 140, 20)
            text_color = (20, 100, 40) if self.live_follow else (140, 80, 10)

            tag_w, tag_h = self.header_btn_rect.width, 22
            tag_x = self.header_btn_rect.x
            tag_y = self.header_btn_rect.y + self.header_btn_rect.height + 4
            tag_rect = pygame.Rect(tag_x, tag_y, tag_w, tag_h)

            pygame.draw.rect(self.screen, bg_color, tag_rect, border_radius=4)
            pygame.draw.rect(self.screen, border_color, tag_rect, 1, border_radius=4)

            mode_txt = self.font_small.render(mode_label, True, text_color)
            m_r = mode_txt.get_rect(center=tag_rect.center)
            self.screen.blit(mode_txt, m_r)

            if self.view_mode == "LINE_CHART":
                # --- 活性値変動推移の重ね合わせ折れ線グラフ画面 ---
                self.draw_line_chart_screen()
            else:
                # --- 従来のステップ表示画面 (ネットワーク構造 ＋ 活性値棒グラフ) ---
                if frame:
                    plan, selectplans, A_raw, weight_raw, ep, st, ev = self.get_resolved_frame_info(self.current_index)
                    plan_disp = f"知識 {plan}" if plan is not None else "なし"
                    info_str = f"フレーム: {self.current_index}/{max(0, total_frames-1)} | エピソード: {ep} | ステップ: {st} | イベント: {ev} | 選択知識: {plan_disp}"
                    self._draw_subheader_info(info_str, y_pos=46, max_width=660)

                    # --- 2. ネットワーク構造の描画 (左側 400x450) ---
                    net_center_x, net_center_y = 230, 290
                    net_radius = 150

                    # ノード数の決定 (Aの長さ、weightのサイズ、または全ログからの推測)
                    num_nodes = len(A_raw) if len(A_raw) > 0 else (len(weight_raw) if len(weight_raw) > 0 else 0)
                    A = np.array(A_raw, dtype=float) if len(A_raw) > 0 else np.zeros(num_nodes, dtype=float)
                    weight = np.array(weight_raw, dtype=float) if len(weight_raw) > 0 else np.zeros((num_nodes, num_nodes), dtype=float)

                    if num_nodes == 0 and len(weight) > 0:
                        num_nodes = len(weight)

                    # ノード位置の計算
                    node_positions = []
                    for i in range(num_nodes):
                        angle = 2 * math.pi * i / max(1, num_nodes) - math.pi / 2
                        nx = net_center_x + int(net_radius * math.cos(angle))
                        ny = net_center_y + int(net_radius * math.sin(angle))
                        node_positions.append((nx, ny))

                    # エッジ（重み weight）の描画 ＆ 数値ラベルバッジ用データの収集
                    edge_draw_list = []
                    if len(weight) == num_nodes and num_nodes > 0:
                        non_zero_w = weight[weight > 0]
                        min_w = float(np.min(non_zero_w)) if len(non_zero_w) > 0 else 0.0
                        max_w = float(np.max(non_zero_w)) if len(non_zero_w) > 0 else 0.0

                        for i in range(num_nodes):
                            for j in range(i + 1, num_nodes):
                                w_val = float(weight[i][j])
                                if w_val > 0:
                                    if max_w > min_w:
                                        # 重みの強弱に応じたスケーリング (0.0 〜 1.0)
                                        ratio = (w_val - min_w) / (max_w - min_w)
                                        thickness = 2 + int(ratio * 4)  # 2px 〜 6px
                                        # 強化された重みは鮮やかなロイヤルブルー (35, 95, 215) 〜 濃紺 (10, 45, 175)
                                        r_c = int(160 - ratio * 125)  # 160 -> 35
                                        g_c = int(175 - ratio * 80)   # 175 -> 95
                                        b_c = int(195 + ratio * 20)   # 195 -> 215
                                        color = (max(0, min(255, r_c)), max(0, min(255, g_c)), max(0, min(255, b_c)))
                                        is_enhanced = (ratio > 0.05)
                                    else:
                                        thickness = 2
                                        color = (160, 175, 195)
                                        is_enhanced = False

                                    pygame.draw.line(self.screen, color, node_positions[i], node_positions[j], thickness)
                                    edge_draw_list.append((i, j, w_val, is_enhanced))

                    # エッジ中央への重み数値ラベル（バッジ）の描画
                    for (i, j, w_val, is_enhanced) in edge_draw_list:
                        p1 = node_positions[i]
                        p2 = node_positions[j]

                        mid_x = (p1[0] + p2[0]) / 2.0
                        mid_y = (p1[1] + p2[1]) / 2.0

                        # 中心 (net_center_x, net_center_y) に近い交差エッジ（対角線等）は中点からずらして文字重複を防止
                        dist_to_center = math.hypot(mid_x - net_center_x, mid_y - net_center_y)
                        if dist_to_center < 30:
                            badge_x = int(p1[0] + 0.35 * (p2[0] - p1[0]))
                            badge_y = int(p1[1] + 0.35 * (p2[1] - p1[1]))
                        else:
                            badge_x = int(mid_x)
                            badge_y = int(mid_y)

                        # ラベル文字列（例: 5.0, 6.7）
                        val_str = f"{w_val:.2f}".rstrip('0').rstrip('.') if '.' in f"{w_val:.2f}" else f"{w_val:.1f}"
                        if "." not in val_str:
                            val_str = f"{w_val:.1f}"

                        t_surf = self.font_tiny.render(val_str, True, (15, 55, 140) if is_enhanced else (70, 80, 95))
                        tw, th = t_surf.get_width(), t_surf.get_height()

                        pad_x, pad_y = 4, 2
                        badge_rect = pygame.Rect(badge_x - tw // 2 - pad_x, badge_y - th // 2 - pad_y, tw + pad_x * 2, th + pad_y * 2)

                        bg_color = (235, 245, 255) if is_enhanced else (255, 255, 255)
                        border_color = (35, 105, 215) if is_enhanced else (180, 190, 205)
                        border_w = 2 if is_enhanced else 1

                        pygame.draw.rect(self.screen, bg_color, badge_rect, border_radius=3)
                        pygame.draw.rect(self.screen, border_color, badge_rect, border_w, border_radius=3)
                        self.screen.blit(t_surf, (badge_x - tw // 2, badge_y - th // 2))

                    # ノードの描画
                    for i, (nx, ny) in enumerate(node_positions):
                        act_val = A[i] if i < len(A) else 0.0
                        norm_act = min(1.0, max(0.0, act_val / 0.5))
                        r_c = int(255 * norm_act)
                        b_c = int(255 * (1.0 - norm_act))
                        node_color = (r_c, 80, b_c)

                        is_selected = (plan == i)
                        is_candidate = (i < len(selectplans) and selectplans[i] == 1)

                        if is_selected:
                            pygame.draw.circle(self.screen, (255, 215, 0), (nx, ny), 26)
                        elif is_candidate:
                            pygame.draw.circle(self.screen, (50, 205, 50), (nx, ny), 24)

                        pygame.draw.circle(self.screen, node_color, (nx, ny), 20)

                        n_txt = self.font_medium.render(str(i), True, (255, 255, 255))
                        n_rect = n_txt.get_rect(center=(nx, ny))
                        self.screen.blit(n_txt, n_rect)

                    # --- 3. 活性値 A のリアルタイムバーチャート (右側 420x450) ---
                    bar_start_x = 480
                    bar_start_y = 90
                    bar_width = 360
                    bar_height = 420
                    
                    pygame.draw.rect(self.screen, (255, 255, 255), (bar_start_x, bar_start_y, bar_width, bar_height))
                    pygame.draw.rect(self.screen, (180, 190, 200), (bar_start_x, bar_start_y, bar_width, bar_height), 2)
                    
                    b_title = self.font_medium.render("知識活性値 (A)", True, (30, 40, 60))
                    self.screen.blit(b_title, (bar_start_x + 10, bar_start_y + 10))

                    thresh_val = frame.get("threshold", 0.18) if frame else 0.18
                    thresh_y = bar_start_y + bar_height - 30 - int((thresh_val / 0.6) * (bar_height - 60))
                    pygame.draw.line(self.screen, (220, 50, 50), (bar_start_x + 30, thresh_y), (bar_start_x + bar_width - 10, thresh_y), 2)
                    t_txt = self.font_small.render(f"活性化閾値 ({thresh_val:.2f})", True, (200, 40, 40))
                    self.screen.blit(t_txt, (bar_start_x + bar_width - 130, thresh_y - 18))

                    if num_nodes > 0:
                        bw = (bar_width - 50) // num_nodes
                        for i in range(num_nodes):
                            act_val = A[i] if i < len(A) else 0.0
                            bh = int((min(0.6, act_val) / 0.6) * (bar_height - 60))
                            bx = bar_start_x + 40 + i * bw
                            by = bar_start_y + bar_height - 30 - bh
                            
                            b_color = (70, 130, 180) if i != plan else (230, 160, 30)
                            pygame.draw.rect(self.screen, b_color, (bx, by, bw - 6, bh))
                            
                            lbl = self.font_small.render(str(i), True, (50, 50, 50))
                            self.screen.blit(lbl, (bx + (bw - 6)//4, bar_start_y + bar_height - 25))

                # コンパクト凡例バー（ステップ表示画面時のみ常時表示）
                self.draw_legend_bar()

            # --- 4. スライダー ＆ ボタン操作GUI ---
            pygame.draw.rect(self.screen, (200, 210, 220), self.slider_rect)
            if total_frames > 1:
                handle_x = self.slider_rect.x + int((self.current_index / float(total_frames - 1)) * self.slider_rect.width)
                pygame.draw.circle(self.screen, (40, 100, 220), (handle_x, self.slider_rect.centery), 10)

            # ボタン描画
            for (x, y, w, h), label, action in self.buttons:
                btn_rect = pygame.Rect(x, y, w, h)
                btn_color = (220, 230, 240)
                if action == "toggle_play" and self.is_playing:
                    btn_color = (180, 220, 180)
                elif action == "toggle_config" and self.show_config:
                    btn_color = (255, 220, 150)
                elif action == "toggle_help" and self.show_help:
                    btn_color = (255, 220, 150)
                elif action == "toggle_live" and self.live_follow:
                    btn_color = (180, 230, 200)

                pygame.draw.rect(self.screen, btn_color, btn_rect, border_radius=5)
                pygame.draw.rect(self.screen, (120, 140, 160), btn_rect, 2, border_radius=5)
                
                txt = self.font_small.render(label, True, (20, 30, 50))
                t_r = txt.get_rect(center=btn_rect.center)
                self.screen.blit(txt, t_r)

            # ハイパーパラメータモーダル (show_config == True 時)
            if self.show_config:
                self.draw_config_overlay()

            # ヘルプ詳細解説オーバーレイ (show_help == True 時)
            if self.show_help:
                self.draw_help_overlay()

            # 保存成功等のトースト通知表示
            if self.toast_timer > 0:
                self.toast_timer -= 1
                t_surf = self.font_small.render(self.toast_msg, True, (255, 255, 255))
                tw, th = t_surf.get_width() + 24, t_surf.get_height() + 12
                tx = (self.width - tw) // 2
                ty = 520
                t_rect = pygame.Rect(tx, ty, tw, th)
                pygame.draw.rect(self.screen, (30, 40, 55), t_rect, border_radius=6)
                pygame.draw.rect(self.screen, (80, 160, 240), t_rect, 1, border_radius=6)
                self.screen.blit(t_surf, t_surf.get_rect(center=t_rect.center))

            pygame.display.flip()
            self.clock.tick(30)
        except Exception as e:
            self.is_active = False
            try:
                pygame.quit()
            except Exception:
                pass
            print(f"[INFO] SAP-net Visualizer window closed: {e}")

    def _draw_subheader_info(self, info_str, y_pos=46, max_width=660):
        """サブヘッダー情報（フレーム・エピソード・ステップ等）をクリッピング＆長文時に水平動的自動スクロール描画"""
        info_surf = self.font_medium.render(info_str, True, (40, 60, 90))
        txt_w = info_surf.get_width()

        if txt_w <= max_width:
            self.screen.blit(info_surf, (20, y_pos))
        else:
            old_clip = self.screen.get_clip()
            clip_rect = pygame.Rect(20, y_pos - 2, max_width, info_surf.get_height() + 4)
            self.screen.set_clip(clip_rect)

            max_scroll = float(txt_w - max_width)
            speed = 0.8  # スクロールスピード

            if self.header_scroll_pause_timer > 0:
                self.header_scroll_pause_timer -= 1
            else:
                self.header_scroll_offset += self.header_scroll_dir * speed
                if self.header_scroll_offset >= max_scroll:
                    self.header_scroll_offset = max_scroll
                    self.header_scroll_dir = -1.0
                    self.header_scroll_pause_timer = 35  # 端で一定フレーム一時停止
                elif self.header_scroll_offset <= 0.0:
                    self.header_scroll_offset = 0.0
                    self.header_scroll_dir = 1.0
                    self.header_scroll_pause_timer = 35

            render_x = 20 - int(self.header_scroll_offset)
            self.screen.blit(info_surf, (render_x, y_pos))
            self.screen.set_clip(old_clip)

    def draw_line_chart_screen(self):
        """活性値変動推移の重ね合わせ折れ線グラフ画面の描画"""
        total_frames = len(self.logger.history)
        
        # 現在選択中フレームの解決済みパラメータを取得
        c_plan, c_selectplans, c_A, _, c_ep, c_st, _ = (
            self.get_resolved_frame_info(self.current_index)
            if (total_frames > 0 and 0 <= self.current_index < total_frames)
            else (None, [], [], [], 0, 0, "")
        )

        # サブヘッダーフレーム情報
        if total_frames > 0 and 0 <= self.current_index < total_frames:
            plan_str = f"知識 {c_plan}" if c_plan is not None else "なし"
            info_str = f"活性値変動推移ビュー | 現在選択: フレーム {self.current_index}/{total_frames-1} | エピソード: {c_ep} | ステップ: {c_st} | 選択知識: {plan_str}"
        else:
            info_str = "活性値変動推移ビュー | ログ未読み込み"
        self._draw_subheader_info(info_str, y_pos=46, max_width=660)

        chart_x, chart_y = self.chart_rect.x, self.chart_rect.y
        chart_w, chart_h = self.chart_rect.width, self.chart_rect.height

        panel_x, panel_y = 745, 80
        panel_w, panel_h = 155, 435

        # 1. グラフ領域背景 ＆ 枠
        pygame.draw.rect(self.screen, (255, 255, 255), (chart_x, chart_y, chart_w, chart_h))
        pygame.draw.rect(self.screen, (180, 190, 200), (chart_x, chart_y, chart_w, chart_h), 2)

        # 2. 凡例トグル操作パネル背景 ＆ 枠
        pygame.draw.rect(self.screen, (248, 250, 253), (panel_x, panel_y, panel_w, panel_h), border_radius=6)
        pygame.draw.rect(self.screen, (200, 210, 225), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=6)

        p_title = self.font_medium.render("知識表示フィルター", True, (30, 50, 80))
        self.screen.blit(p_title, (panel_x + 12, panel_y + 8))

        # 全選択・全解除ボタン
        self.btn_all_rect = pygame.Rect(panel_x + 10, panel_y + 32, 63, 24)
        self.btn_none_rect = pygame.Rect(panel_x + 80, panel_y + 32, 63, 24)

        pygame.draw.rect(self.screen, (225, 235, 245), self.btn_all_rect, border_radius=4)
        pygame.draw.rect(self.screen, (140, 160, 180), self.btn_all_rect, 1, border_radius=4)
        t_all = self.font_small.render("全選択", True, (20, 40, 70))
        self.screen.blit(t_all, t_all.get_rect(center=self.btn_all_rect.center))

        pygame.draw.rect(self.screen, (225, 235, 245), self.btn_none_rect, border_radius=4)
        pygame.draw.rect(self.screen, (140, 160, 180), self.btn_none_rect, 1, border_radius=4)
        t_none = self.font_small.render("全解除", True, (20, 40, 70))
        self.screen.blit(t_none, t_none.get_rect(center=self.btn_none_rect.center))

        # グラフ画像保存ボタン (パネル最下部に配置)
        self.btn_save_chart_rect = pygame.Rect(panel_x + 10, panel_y + panel_h - 34, panel_w - 20, 26)
        pygame.draw.rect(self.screen, (215, 235, 255), self.btn_save_chart_rect, border_radius=4)
        pygame.draw.rect(self.screen, (50, 110, 190), self.btn_save_chart_rect, 1, border_radius=4)
        t_save = self.font_small.render("グラフ保存 (S)", True, (15, 45, 90))
        self.screen.blit(t_save, t_save.get_rect(center=self.btn_save_chart_rect.center))

        # データから総ノード数の計算
        num_nodes = 0
        if total_frames > 0:
            for f in self.logger.history:
                if f.get("A"):
                    num_nodes = max(num_nodes, len(f["A"]))

        # 3. 知識表示/非表示トグルボタンの描画・生成（選択中知識のハイライト付き）
        self.node_toggle_rects = []
        for i in range(num_nodes):
            if i not in self.visible_nodes:
                self.visible_nodes[i] = True
            
            by = panel_y + 64 + i * 26
            if by + 24 > panel_y + panel_h - 40:
                break  # 最下部「グラフ保存」ボタンとの被り防止
            
            btn_rect = pygame.Rect(panel_x + 8, by, panel_w - 16, 23)
            self.node_toggle_rects.append((i, btn_rect))

            is_vis = self.visible_nodes[i]
            is_plan = (c_plan == i)
            c_color = self.node_colors[i % len(self.node_colors)]

            if is_plan:
                bg_col = (255, 246, 220) if is_vis else (245, 238, 220)
                border_col = (230, 160, 20)
                border_w = 2
            else:
                bg_col = (235, 243, 255) if is_vis else (240, 240, 240)
                border_col = c_color if is_vis else (180, 180, 180)
                border_w = 2 if is_vis else 1

            pygame.draw.rect(self.screen, bg_col, btn_rect, border_radius=4)
            pygame.draw.rect(self.screen, border_col, btn_rect, border_w, border_radius=4)

            # 色丸マーク
            pygame.draw.circle(self.screen, c_color, (btn_rect.x + 14, btn_rect.centery), 6)
            if not is_vis:
                pygame.draw.line(self.screen, (150, 150, 150), (btn_rect.x + 8, btn_rect.centery - 6), (btn_rect.x + 20, btn_rect.centery + 6), 2)

            chk_str = f"知識 {i}" + (" [✓]" if is_vis else " [  ]")
            if is_plan:
                chk_str += " ★選択"
            txt_color = (190, 110, 0) if (is_plan and is_vis) else ((20, 30, 50) if is_vis else (130, 130, 130))
            n_txt = self.font_small.render(chk_str, True, txt_color)
            self.screen.blit(n_txt, (btn_rect.x + 26, btn_rect.centery - n_txt.get_height() // 2))

        if total_frames <= 1:
            msg = self.font_medium.render("ログデータが読み込まれていません（'O' キーで実験ログフォルダを選択してください）", True, (120, 130, 140))
            self.screen.blit(msg, msg.get_rect(center=(chart_x + chart_w // 2, chart_y + chart_h // 2)))
            return

        # 4. Y軸グリッド ＆ 目盛り（0.0 〜 1.0）
        for y_val in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            cy = chart_y + chart_h - int(y_val * chart_h)
            pygame.draw.line(self.screen, (230, 235, 240), (chart_x, cy), (chart_x + chart_w, cy), 1)
            lbl = self.font_small.render(f"{y_val:.1f}", True, (100, 110, 120))
            self.screen.blit(lbl, (chart_x - 30, cy - 7))

        # 5. X軸グリッド ＆ 目盛り（フレームインデックス）
        num_x_ticks = min(10, total_frames)
        for t in range(num_x_ticks):
            idx = int(t * (total_frames - 1) / max(1, num_x_ticks - 1))
            cx = chart_x + int((idx / float(total_frames - 1)) * chart_w)
            pygame.draw.line(self.screen, (230, 235, 240), (cx, chart_y), (cx, chart_y + chart_h), 1)
            lbl = self.font_small.render(str(idx), True, (100, 110, 120))
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, chart_y + chart_h + 5))

        # 6. 活性化閾値線の描画
        curr_frame = self.logger.get_frame(self.current_index) or self.logger.get_frame(total_frames - 1)
        thresh_val = curr_frame.get("threshold", 0.18) if curr_frame else 0.18
        thresh_y = chart_y + chart_h - int(thresh_val * chart_h)
        
        dash_len = 8
        for dash_x in range(chart_x, chart_x + chart_w, dash_len * 2):
            pygame.draw.line(self.screen, (220, 50, 50), (dash_x, thresh_y), (min(chart_x + chart_w, dash_x + dash_len), thresh_y), 2)
        t_lbl = self.font_small.render(f"活性化閾値 ({thresh_val:.2f})", True, (200, 40, 40))
        self.screen.blit(t_lbl, (chart_x + chart_w - 120, thresh_y - 18))

        # 7. 各知識の時系列折れ線描画 (マルチライン ＆ 高速化ストライド)
        stride = max(1, total_frames // (chart_w * 2))
        indices = list(range(0, total_frames, stride))
        if indices[-1] != total_frames - 1:
            indices.append(total_frames - 1)

        for i in range(num_nodes):
            if not self.visible_nodes.get(i, True):
                continue
            
            c_color = self.node_colors[i % len(self.node_colors)]
            points = []
            for idx in indices:
                px = chart_x + int((idx / float(total_frames - 1)) * chart_w)
                frame_data = self.logger.history[idx]
                act_list = frame_data.get("A", [])
                act_val = act_list[i] if i < len(act_list) else 0.0
                act_val = min(1.0, max(0.0, float(act_val)))
                py = chart_y + chart_h - int(act_val * chart_h)
                points.append((px, py))

            if len(points) >= 2:
                pygame.draw.lines(self.screen, c_color, False, points, 2)

        # 8. 現在選択中フレームの垂直カーソル線 ＆ 選択知識マーカー描画
        if 0 <= self.current_index < total_frames:
            cur_x = chart_x + int((self.current_index / float(total_frames - 1)) * chart_w)
            # 垂直カーソル線
            pygame.draw.line(self.screen, (30, 90, 220), (cur_x, chart_y), (cur_x, chart_y + chart_h), 2)
            
            # 選択されている知識（plan）の折れ線上の現在ポイントを二重丸＋バッジで強調
            if c_plan is not None and self.visible_nodes.get(c_plan, True):
                p_act = c_A[c_plan] if c_plan < len(c_A) else 0.0
                p_act = min(1.0, max(0.0, float(p_act)))
                py = chart_y + chart_h - int(p_act * chart_h)
                p_color = self.node_colors[c_plan % len(self.node_colors)]

                # 外側リング（金色・発光風）＋中心ドット
                pygame.draw.circle(self.screen, (240, 190, 30), (cur_x, py), 9, 3)
                pygame.draw.circle(self.screen, (255, 255, 255), (cur_x, py), 6)
                pygame.draw.circle(self.screen, p_color, (cur_x, py), 4)

                # 活性値バッジ（ポイント近傍の吹き出し）
                act_badge_txt = f"知識{c_plan}: {p_act:.2f}"
                act_surf = self.font_tiny.render(act_badge_txt, True, (30, 40, 60))
                bw = act_surf.get_width() + 8
                bh = 16
                bx = cur_x + 10
                if bx + bw > chart_x + chart_w - 4:
                    bx = cur_x - bw - 10
                by = max(chart_y + 4, min(py - 8, chart_y + chart_h - bh - 4))
                
                b_rect = pygame.Rect(bx, by, bw, bh)
                pygame.draw.rect(self.screen, (255, 248, 220), b_rect, border_radius=3)
                pygame.draw.rect(self.screen, (220, 160, 20), b_rect, 1, border_radius=3)
                self.screen.blit(act_surf, (bx + 4, by + 1))

            # カーソル上部情報バッジ
            plan_label = f"選択知識: 知識 {c_plan}" if c_plan is not None else "選択知識: なし"
            cur_txt = f"フレーム {self.current_index} (Ep:{c_ep}, Step:{c_st}) | {plan_label}"
            c_surf = self.font_small.render(cur_txt, True, (255, 255, 255))
            
            c_w = c_surf.get_width() + 16
            c_left = min(max(cur_x - c_w // 2, chart_x + 4), chart_x + chart_w - c_w - 4)
            c_bg = pygame.Rect(c_left, chart_y + 8, c_w, 22)
            
            bg_col = (20, 50, 110) if c_plan is not None else (40, 60, 90)
            border_col = (240, 200, 40) if c_plan is not None else (100, 140, 200)
            pygame.draw.rect(self.screen, bg_col, c_bg, border_radius=4)
            pygame.draw.rect(self.screen, border_col, c_bg, 2 if c_plan is not None else 1, border_radius=4)
            self.screen.blit(c_surf, (c_bg.x + 8, c_bg.y + 4))

    def load_config_data(self, return_status=False):
        """ログファイルに付随する config_used_*.yaml を読み込む。存在しない場合はフォールバック情報を生成して返す"""
        config_items = []
        yaml_loaded = False

        PARAM_DESCRIPTIONS = {
            # Meta
            "META.TARGET_SCRIPT": "実行対象スクリプトファイル名",
            "META.DESCRIPTION": "実験・制御設定の概要メモ",
            # Mode
            "MODE.NAME": "学習モード (RL / S-SAP / Q-SAP)",
            "MODE.USE_SHIELD": "安全性保証シールド機構の有効化",
            # Experiment
            "EXPERIMENT.ENABLE_SAP_VISUALIZER": "SAP動的パラメータ可視化GUIの自動起動",
            "EXPERIMENT.MAX_EPISODES": "最大総エピソード数",
            "EXPERIMENT.MAX_STEPS": "1エピソードあたりの最大ステップ数",
            "EXPERIMENT.GOAL_POSITION": "目標（ゴール）の3次元座標 [X, Y, Z] (m)",
            "EXPERIMENT.INITIAL_POSITION": "ロボット初期配置座標 [X, Y, Z] (m)",
            # Reward
            "REWARD.REWARD_GOAL": "目標到達時のプラス報酬",
            "REWARD.REWARD_COLLISION": "壁衝突時のペナルティ報酬",
            "REWARD.REWARD_STEP": "1ステップごとのタイムペナルティ",
            "REWARD.REWARD_NEAR_WALL": "壁接近時 (<=0.5m) の回避ペナルティ",
            "REWARD.REWARD_SHAPING_COEFF": "距離変化に基づくポテンシャル報酬 (Shaping) 係数",
            "REWARD.REWARD_SHIELD_PENALTY": "シールド介入時のペナルティ",
            # Q-learning
            "QLEARNING.ALPHA": "強化学習の学習率 (alpha)",
            "QLEARNING.GAMMA": "将来報酬の時間割引率 (gamma)",
            "QLEARNING.TAU": "ボルツマン行動選択の温度パラメータ (tau)",
            "QLEARNING.LOAD_Q_TABLE": "既存Qテーブルのロード有効化",
            "QLEARNING.LOAD_Q_TABLE_NAME": "ロード対象Qテーブルファイル名",
            # SAP
            "SAP.ACTIVATION": "知識ノード初期活性値 (Activation)",
            "SAP.THRESHOLD": "知識活性化・転移判断の評価閾値 (Threshold)",
            "SAP.ATTENUATION": "1ステップごとの活性度減衰率 (Attenuation)",
            "SAP.FREQ_ACT": "知識活性化・選択の実行頻度 (ステップ数)",
            "SAP.FREQ_WEIGHT": "知識間重み行列の更新実行頻度 (ステップ数)",
            "SAP.FIRST_WEIGHT": "知識間重み行列の初期値 (Firstweight)",
            "SAP.POSITIVE_ADJUSTMENT": "正の転移発生時の重み増強補正量",
            "SAP.NEGATIVE_ADJUSTMENT": "負の転移発生時の重み抑制補正量",
            "SAP.COLLISION": "負の転移・衝突発生時の活性度ペナルティ",
            "SAP.T_RATE": "他タスク知識の転移適用率 (T_RATE)",
            # Policy
            "POLICY.ALL_POLICY": "登録・管理されている再利用ポリシー（Qテーブル）総数",
            "POLICY.REUSE_POLICY_DIR": "再利用ポリシーファイルの保存ディレクトリ",
            "POLICY.REUSE_POLICY_PREFIX": "ポリシーファイルの接頭辞",
            # Control
            "CONTROL.MOVE_SPEED": "ロボット目標移動速度 (m/s)",
            "CONTROL.STRAFE_VX_CORRECTION": "左右移動時の直進軸補正速度 (m/s)",
            "CONTROL.YAW_KP": "機体姿勢・方角補正のPゲイン",
            "CONTROL.MOVE_DISTANCE": "1行動あたりの移動距離 (m)",
            # Environment
            "ENVIRONMENT.NUM_ACTIONS": "離散行動空間の総行動数",
            "ENVIRONMENT.MIN_DX": "状態空間: X方向相対座標の最小範囲 (m)",
            "ENVIRONMENT.MAX_DX": "状態空間: X方向相対座標の最大範囲 (m)",
            "ENVIRONMENT.MIN_DY": "状態空間: Y方向相対座標の最小範囲 (m)",
            "ENVIRONMENT.MAX_DY": "状態空間: Y方向相対座標の最大範囲 (m)",
            # Dynamic Fallback items
            "SYSTEM.LOG_FRAMES": "現在記録されている総ログフレーム数",
            "SYSTEM.GUI_FPS": "GUI描画目標フレームレート",
            "CONFIG_STATUS": "YAML未検出時の動的フォールバック表示",
        }

        def get_japanese_desc(sec, k):
            full_key = f"{sec}.{k}".upper()
            return PARAM_DESCRIPTIONS.get(full_key, "詳細不明（未定義パラメータ）")

        try:
            log_path = getattr(self.logger, "log_file_path", None)
            if log_path and os.path.exists(log_path):
                log_dir = os.path.dirname(log_path)
                yaml_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.startswith("config_used") and f.endswith(".yaml")]
                
                if yaml_files:
                    import yaml
                    with open(yaml_files[0], mode="r", encoding="utf-8") as f:
                        raw_yaml = yaml.safe_load(f)
                        if isinstance(raw_yaml, dict):
                            for section, params in raw_yaml.items():
                                if isinstance(params, dict):
                                    for key, val in params.items():
                                        v_str = str(val).strip().replace("\n", "") if val is not None else ""
                                        if not v_str or v_str.lower() in ("none", "null", "nan", "empty", "[]", "{}"):
                                            v_str = "-"
                                        desc = get_japanese_desc(section, key)
                                        config_items.append((f"{section}.{key}".upper(), v_str, desc))
                            if config_items:
                                yaml_loaded = True
        except Exception as ye:
            print(f"[WARNING] Failed to load/parse YAML config: {ye}")

        # YAMLが読めなかった場合の代替・デフォルト・動的設定項目
        if not yaml_loaded:
            # 現在のフレームからの活性化閾値等の取得
            frame = self.logger.get_frame(self.current_index) if hasattr(self.logger, "get_frame") and len(getattr(self.logger, "history", [])) > 0 else None
            thresh_val = frame.get("threshold", 0.18) if frame else 0.18
            total_frames = len(getattr(self.logger, "history", []))

            config_items = [
                ("CONFIG_STATUS", "DEFAULT / DYNAMIC", "YAML未検出時の動的フォールバック表示"),
                ("SAP.THRESHOLD", f"{thresh_val:.2f}", "知識活性化の評価閾値"),
                ("SAP.SPREAD_RATE", "0.60", "活性化エネルギー拡散係数"),
                ("SAP.DECAY_RATE", "0.05", "1ステップ毎の活性値減衰率"),
                ("SAP.INITIAL_ACT", "0.00", "知識ノード初期活性度"),
                ("RL.LEARNING_RATE", "0.01", "Q学習・価値関数更新率 (alpha)"),
                ("RL.DISCOUNT_FACTOR", "0.95", "時間割引率 (gamma)"),
                ("RL.EPSILON_START", "1.00", "初期探索率 (epsilon_start)"),
                ("RL.EPSILON_MIN", "0.05", "最小探索率 (epsilon_min)"),
                ("RL.REWARD_SCALE", "1.00", "報酬関数のスケール係数"),
                ("ENV.ROBOT", "Robotino 3-Omni", "使用ロボットモデル"),
                ("ENV.MAX_STEPS", "1000", "1エピソードあたりの最大ステップ数"),
                ("SYSTEM.LOG_FRAMES", f"{total_frames}", "現在記録されている総ログフレーム数"),
                ("SYSTEM.GUI_FPS", "30", "GUI描画目標フレームレート"),
            ]

        if return_status:
            return config_items, yaml_loaded
        return config_items

    def _render_wrapped_text(self, text, font, color, max_width):
        """指定した最大ピクセル幅(max_width)に合わせてテキストを自動改行してレンダリングする"""
        if not text:
            return []

        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)

        surfaces = [font.render(line, True, color) for line in lines]
        return surfaces

    def draw_config_overlay(self):
        """ハイパーパラメータ・学習設定一覧ダイアログの描画 (1列高視認性・文字自動改行＆スクロール対応)"""
        try:
            # 1. 暗色半透明バックドロップ
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((10, 20, 30, 215))
            self.screen.blit(overlay, (0, 0))

            # 2. メインモーダルウィンドウ枠 (860 x 635 px)
            dlg_x, dlg_y = 30, 25
            dlg_w, dlg_h = 860, 635
            pygame.draw.rect(self.screen, (250, 252, 255), (dlg_x, dlg_y, dlg_w, dlg_h), border_radius=10)
            pygame.draw.rect(self.screen, (40, 100, 180), (dlg_x, dlg_y, dlg_w, dlg_h), 3, border_radius=10)

            # 3. タイトルヘッダー (固定)
            cfg_title = self.font_title.render("ハイパーパラメータ ＆ システム学習設定一覧", True, (20, 45, 90))
            self.screen.blit(cfg_title, (dlg_x + 25, dlg_y + 16))
            pygame.draw.line(self.screen, (190, 205, 225), (dlg_x + 20, dlg_y + 50), (dlg_x + dlg_w - 20, dlg_y + 50), 2)

            # 4. データ読み込み
            config_items = self.load_config_data()

            # 5. 1列テーブルの固定カラムヘッダー描画
            head_y = dlg_y + 58
            th_param = self.font_medium.render("パラメータ名", True, (70, 90, 120))
            th_val = self.font_medium.render("設定値", True, (70, 90, 120))
            th_desc = self.font_medium.render("概要・説明", True, (70, 90, 120))
            
            # 各列の X 座標 (全幅 810px)
            col_param_x = dlg_x + 25    # 230px 幅
            col_val_x = dlg_x + 265      # 150px 幅
            col_desc_x = dlg_x + 425     # 400px 幅

            self.screen.blit(th_param, (col_param_x, head_y))
            self.screen.blit(th_val, (col_val_x, head_y))
            self.screen.blit(th_desc, (col_desc_x, head_y))
            
            pygame.draw.line(self.screen, (200, 212, 230), (dlg_x + 20, head_y + 24), (dlg_x + dlg_w - 20, head_y + 24), 2)

            # 6. テーブルコンテンツのクリッピング可視領域定義 (フッター領域と被らない高さ 485px)
            content_top = head_y + 28
            content_h = dlg_h - 145  # 約 490px (底面 y = dlg_y + head_y + 28 + 490 = 601)
            content_rect = pygame.Rect(dlg_x + 15, content_top, dlg_w - 30, content_h)

            # Pygameの描画クリッピングを設定
            old_clip = self.screen.get_clip()
            self.screen.set_clip(content_rect)

            y_curr = content_top - self.config_scroll_y

            for idx, item in enumerate(config_items):
                name_str = str(item[0]).strip().replace("\n", "")
                val_str = str(item[1]).strip().replace("\n", "") if item[1] is not None else ""
                if not val_str or val_str.lower() in ("none", "null", "nan", "empty", "[]", "{}"):
                    val_str = "-"
                desc_str = str(item[2]).strip().replace("\n", "") if len(item) > 2 else ""

                # 各カラムの文字自動改行レンダリング
                name_surfs = self._render_wrapped_text(name_str, self.font_small, (25, 55, 115), 230)
                val_color = (200, 35, 35) if ("SAP" in name_str or "REWARD" in name_str) else (25, 115, 45)
                val_surfs = self._render_wrapped_text(val_str, self.font_medium, val_color, 150)
                desc_surfs = self._render_wrapped_text(desc_str, self.font_small, (80, 90, 110), 400)

                # 行数の最大値からこのアイテムの高さを計算
                max_lines = max(len(name_surfs), len(val_surfs), len(desc_surfs), 1)
                line_h = 19
                row_padding = 8
                item_h = max(30, max_lines * line_h + row_padding)

                # 画面範囲内にある場合のみ描画
                if y_curr + item_h >= content_top and y_curr <= content_top + content_h:
                    # ゼブラパターン背景
                    if idx % 2 == 1:
                        pygame.draw.rect(self.screen, (242, 246, 252), (dlg_x + 20, y_curr, dlg_w - 40, item_h - 2), border_radius=4)

                    # パラメータ名レンダリング
                    for i, srf in enumerate(name_surfs):
                        self.screen.blit(srf, (col_param_x, y_curr + 4 + i * line_h))

                    # 設定値レンダリング
                    for i, srf in enumerate(val_surfs):
                        self.screen.blit(srf, (col_val_x, y_curr + 4 + i * line_h))

                    # 概要・説明レンダリング
                    for i, srf in enumerate(desc_surfs):
                        self.screen.blit(srf, (col_desc_x, y_curr + 4 + i * line_h))

                    # 下部区切り線
                    pygame.draw.line(self.screen, (230, 236, 244), (dlg_x + 20, y_curr + item_h - 1), (dlg_x + dlg_w - 20, y_curr + item_h - 1), 1)

                y_curr += item_h

            # クリッピング解除
            self.screen.set_clip(old_clip)

            # 7. スクロール領域・スクロールバー計算
            total_content_height = y_curr + self.config_scroll_y - content_top
            self.max_config_scroll = max(0, total_content_height - content_h)

            if self.max_config_scroll > 0:
                # 右端スクロールバーの描画
                sb_x = dlg_x + dlg_w - 18
                sb_y = content_top
                sb_w = 6
                sb_h = content_h
                pygame.draw.rect(self.screen, (220, 225, 235), (sb_x, sb_y, sb_w, sb_h), border_radius=3)

                handle_h = max(25, int(content_h * (content_h / float(total_content_height))))
                handle_y = sb_y + int((self.config_scroll_y / float(self.max_config_scroll)) * (sb_h - handle_h))
                pygame.draw.rect(self.screen, (100, 140, 200), (sb_x, handle_y, sb_w, handle_h), border_radius=3)

            # 8. フッターメッセージ案内 (テーブルと被らない独立白帯背景)
            footer_y = dlg_y + dlg_h - 45
            footer_h = 40
            pygame.draw.rect(self.screen, (245, 248, 252), (dlg_x + 3, footer_y, dlg_w - 6, footer_h), border_bottom_left_radius=8, border_bottom_right_radius=8)
            pygame.draw.line(self.screen, (200, 212, 230), (dlg_x + 20, footer_y), (dlg_x + dlg_w - 20, footer_y), 2)

            close_txt = self.font_medium.render("'C' / 'Esc' キー（またはマウスホイールでスクロール） | 閉じる", True, (80, 105, 140))
            c_rect = close_txt.get_rect(center=(dlg_x + dlg_w // 2, footer_y + 20))
            self.screen.blit(close_txt, c_rect)

        except Exception as err:
            print(f"[ERROR] Critical failure in draw_config_overlay: {err}")

    def draw_legend_bar(self):
        """ネットワークグラフ下部にコンパクト凡例 (Legend Bar) を背景枠に対して均等に描画"""
        lg_x, lg_y = 20, 515
        lg_w, lg_h = 470, 30
        pygame.draw.rect(self.screen, (255, 255, 255), (lg_x, lg_y, lg_w, lg_h), border_radius=4)
        pygame.draw.rect(self.screen, (200, 210, 220), (lg_x, lg_y, lg_w, lg_h), 1, border_radius=4)

        # 4つの凡例アイテム定義
        legend_items = [
            ("gold_ring", "選択中の知識"),
            ("green_ring", "転移候補知識"),
            ("red_dot", "活性値の高い知識"),
            ("weight_line", "強い知識間重み"),
        ]

        # 各アイテムの幅（アイコン幅 + テキスト幅）を実測計算
        item_widths = []
        rendered_texts = []
        for item_type, text_str in legend_items:
            txt_surf = self.font_small.render(text_str, True, (40, 50, 60))
            rendered_texts.append(txt_surf)
            w_txt = txt_surf.get_width()
            
            if item_type in ("gold_ring", "green_ring"):
                icon_w = 16 + 5  # 直径16 + テキスト隙間5
            elif item_type == "red_dot":
                icon_w = 12 + 5  # 直径12 + テキスト隙間5
            elif item_type == "weight_line":
                icon_w = 16 + 5  # 線長16 + テキスト隙間5
            else:
                icon_w = 0
                
            item_widths.append(icon_w + w_txt)

        total_items_w = sum(item_widths)
        num_items = len(legend_items)
        
        # 均等間隔の計算 (左右端余白 15px, アイテム間 gap)
        margin = 15
        avail_space = lg_w - 2 * margin
        gap = (avail_space - total_items_w) / max(1, num_items - 1) if num_items > 1 else 0

        curr_x = lg_x + margin
        cy = lg_y + 15
        
        for i, (item_type, text_str) in enumerate(legend_items):
            txt_surf = rendered_texts[i]
            
            if item_type == "gold_ring":
                pygame.draw.circle(self.screen, (255, 215, 0), (int(curr_x + 8), cy), 8)
                pygame.draw.circle(self.screen, (220, 50, 50), (int(curr_x + 8), cy), 5)
                self.screen.blit(txt_surf, (int(curr_x + 21), lg_y + 7))
            elif item_type == "green_ring":
                pygame.draw.circle(self.screen, (50, 205, 50), (int(curr_x + 8), cy), 8)
                pygame.draw.circle(self.screen, (50, 80, 200), (int(curr_x + 8), cy), 5)
                self.screen.blit(txt_surf, (int(curr_x + 21), lg_y + 7))
            elif item_type == "red_dot":
                pygame.draw.circle(self.screen, (220, 40, 40), (int(curr_x + 6), cy), 6)
                self.screen.blit(txt_surf, (int(curr_x + 17), lg_y + 7))
            elif item_type == "weight_line":
                pygame.draw.line(self.screen, (35, 95, 215), (int(curr_x), cy), (int(curr_x + 16), cy), 4)
                self.screen.blit(txt_surf, (int(curr_x + 21), lg_y + 7))
                
            curr_x += item_widths[i] + gap

    def draw_help_overlay(self):
        """詳細操作ガイド ＆ ヘルプオーバーレイパネルの描画"""
        # 暗色半透明のオーバーレイ背景
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((10, 20, 30, 210))  # 黒透明
        self.screen.blit(overlay, (0, 0))

        # ダイアログ枠 (860 x 635 px)
        dlg_x, dlg_y = 30, 25
        dlg_w, dlg_h = 860, 635
        pygame.draw.rect(self.screen, (252, 254, 255), (dlg_x, dlg_y, dlg_w, dlg_h), border_radius=10)
        pygame.draw.rect(self.screen, (50, 90, 150), (dlg_x, dlg_y, dlg_w, dlg_h), 3, border_radius=10)

        # ヘッダー
        h_title = self.font_title.render("画面の見方・操作ガイド", True, (20, 40, 80))
        self.screen.blit(h_title, (dlg_x + 25, dlg_y + 18))
        pygame.draw.line(self.screen, (200, 210, 225), (dlg_x + 20, dlg_y + 52), (dlg_x + dlg_w - 20, dlg_y + 52), 2)

        # ガイド本文 (左カラム: 画面の見方 / 右カラム: キーボード・ボタン操作)
        col1_x = dlg_x + 25
        col2_x = dlg_x + 440
        y_curr = dlg_y + 65

        # 現在のフレームの閾値を取得
        frame = self.logger.get_frame(self.current_index) if len(self.logger.history) > 0 else None
        thresh_val = frame.get("threshold", 0.18) if frame else 0.18

        # --- Section 1: 画面エレメントの見方 ---
        sec1_title = self.font_medium.render("【画面エレメントの見方】", True, (30, 60, 120))
        self.screen.blit(sec1_title, (col1_x, y_curr))
        
        items_sec1 = [
            ("icon_gold", "選択中の知識 (金色二重枠/マーカー)", "実行中知識（グラフ上でも金色サークル＆バッジで強調）"),
            ("icon_green", "転移候補知識 (緑色二重枠)", f"活性化基準(閾値 {thresh_val:.2f})を超えた転移候補知識"),
            ("icon_color", "ノードの色 (活性度 A)", "赤: 活性値の高い知識 A>=0.5 / 青: 非活性 A=0"),
            ("icon_weight", "強い知識間重みの線", "太く濃い青色の線ほど結合が強固（数値バッジ付き）"),
            ("icon_barchart", "活性値バーグラフ (右側)", "各知識の活性値 A のリアルタイムバーチャート"),
            ("icon_linechart", "活性値変動推移グラフ (Gキー)", "全知識の活性値の時系列変化（選択中の知識を金色強調）"),
            ("icon_threshold", f"活性化閾値線 ({thresh_val:.2f})", f"活性化閾値 ({thresh_val:.2f}) の赤色線"),
            ("icon_live", "リアルタイム追従モード", "シミュレーションの最新ステップにリアルタイム自動追従"),
        ]

        y_p = y_curr + 28
        for icon_type, title_str, desc_str in items_sec1:
            icon_cx = col1_x + 16
            icon_cy = y_p + 10

            # アイコンタイプ別のグラフィック直接描写
            if icon_type == "icon_gold":
                pygame.draw.circle(self.screen, (255, 215, 0), (icon_cx, icon_cy), 8)
                pygame.draw.circle(self.screen, (50, 80, 200), (icon_cx, icon_cy), 5)
            elif icon_type == "icon_green":
                pygame.draw.circle(self.screen, (50, 205, 50), (icon_cx, icon_cy), 7)
                pygame.draw.circle(self.screen, (50, 80, 200), (icon_cx, icon_cy), 4)
            elif icon_type == "icon_color":
                pygame.draw.circle(self.screen, (220, 40, 40), (icon_cx - 5, icon_cy), 5)
                pygame.draw.circle(self.screen, (40, 80, 200), (icon_cx + 5, icon_cy), 5)
            elif icon_type == "icon_weight":
                pygame.draw.line(self.screen, (35, 95, 215), (icon_cx - 8, icon_cy), (icon_cx + 8, icon_cy), 4)
            elif icon_type == "icon_barchart":
                pygame.draw.rect(self.screen, (70, 130, 220), (icon_cx - 8, icon_cy - 4, 4, 10))
                pygame.draw.rect(self.screen, (70, 130, 220), (icon_cx - 2, icon_cy - 8, 4, 14))
                pygame.draw.rect(self.screen, (70, 130, 220), (icon_cx + 4, icon_cy - 2, 4, 8))
            elif icon_type == "icon_linechart":
                pygame.draw.line(self.screen, (220, 120, 30), (icon_cx - 8, icon_cy + 4), (icon_cx - 2, icon_cy - 6), 2)
                pygame.draw.line(self.screen, (220, 120, 30), (icon_cx - 2, icon_cy - 6), (icon_cx + 4, icon_cy + 2), 2)
                pygame.draw.line(self.screen, (220, 120, 30), (icon_cx + 4, icon_cy + 2), (icon_cx + 8, icon_cy - 6), 2)
            elif icon_type == "icon_threshold":
                pygame.draw.line(self.screen, (220, 50, 50), (icon_cx - 8, icon_cy), (icon_cx + 8, icon_cy), 2)
            elif icon_type == "icon_live":
                pygame.draw.circle(self.screen, (40, 160, 60), (icon_cx, icon_cy), 6)
            elif icon_type == "icon_manual":
                pygame.draw.circle(self.screen, (210, 140, 20), (icon_cx, icon_cy), 6)

            t_title = self.font_medium.render(title_str, True, (30, 50, 80))
            t_desc = self.font_small.render(desc_str, True, (80, 90, 110))
            self.screen.blit(t_title, (col1_x + 34, y_p))
            self.screen.blit(t_desc, (col1_x + 34, y_p + 20))
            y_p += 54

        # --- Section 2: 操作方法・ショートカットキー ---
        sec2_title = self.font_medium.render("【キーボード ＆ ボタン操作】", True, (30, 60, 120))
        self.screen.blit(sec2_title, (col2_x, y_curr))

        items_sec2 = [
            ("G キー", "画面表示モード切替（ステップ表示 ⇄ 折れ線グラフ）"),
            ("Space キー", "再生 / 一時停止"),
            ("← / → 矢印キー", "1ステップ コマ戻し / コマ送り"),
            ("E / Shift+E キー", "次 / 直前 のエピソードへジャンプ"),
            ("P / Shift+P キー", "次 / 直前 の知識選択へジャンプ"),
            ("A / Shift+A キー", "次 / 直前 の活性化へジャンプ"),
            ("W / Shift+W キー", "次 / 直前 の重み更新へジャンプ"),
            ("L キー", "リアルタイム追従モードのON/OFF切替"),
            ("C キー", "ハイパーパラメータ設定一覧の表示 / 非表示"),
            ("O キー", "実験ログフォルダ選択ダイアログを開く"),
            ("H / ? / Esc キー", "ヘルプ画面の表示 / 非表示"),
        ]

        y_p2 = y_curr + 28
        for key_str, desc_str in items_sec2:
            t_k = self.font_medium.render(key_str, True, (20, 80, 160))
            t_d = self.font_small.render(desc_str, True, (60, 70, 90))
            self.screen.blit(t_k, (col2_x + 10, y_p2))
            self.screen.blit(t_d, (col2_x + 10, y_p2 + 18))
            y_p2 += 44

        # フッター閉じる案内
        close_txt = self.font_medium.render("'H' キーまたは 'Esc' キー（または 'ヘルプ' ボタン）で閉じる", True, (100, 120, 150))
        c_rect = close_txt.get_rect(center=(dlg_x + dlg_w // 2, dlg_y + dlg_h - 22))
        self.screen.blit(close_txt, c_rect)
