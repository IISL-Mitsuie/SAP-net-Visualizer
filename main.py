import os
import sys

# windowed (GUI) モード起動時に stdout/stderr が None の場合の安全対策
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# 自身のディレクトリをモジュール検索パスの先頭に追加
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import pygame
from sap_visualizer import SAPVisualLogger, SAPVisualizerGUI, FolderHistoryManager, select_simulation_folder

def main():
    print("=" * 60)
    print("      SAP-net Visualizer")
    print("=" * 60)
    
    logger = SAPVisualLogger(enabled=True)
    history_mgr = FolderHistoryManager()
    
    # コマンドライン引数のチェック
    target_path = None
    if len(sys.argv) > 1:
        target_path = sys.argv[1]

    if target_path and os.path.exists(target_path):
        # シミュレーション連動起動やパス直接指定時
        if os.path.isdir(target_path):
            if logger.load_from_folder(target_path):
                history_mgr.add_folder(target_path)
        else:
            logger.load_from_file(target_path)
            history_mgr.add_folder(os.path.dirname(target_path))
    else:
        # 直接起動時: フォルダ選択＆履歴ダイアログを表示
        print("[INFO] Launching simulation folder selector dialog...")
        selected_folder = select_simulation_folder()
        if not selected_folder:
            print("[INFO] Folder selection cancelled. Exiting SAP-net Visualizer.")
            return

        if logger.load_from_folder(selected_folder):
            history_mgr.add_folder(selected_folder)
        else:
            print(f"[ERROR] Failed to load selected folder: {selected_folder}")

    gui = SAPVisualizerGUI(logger)
    gui.live_follow = False  # 保存ログ閲覧ビューアー起動時は手動再生・精査モードを標準とする


    print("\n--- 操作方法・キーボードショートカット ---")
    print("  G キー       : 画面表示モード切替（ステップ表示 ⇄ 活性値推移グラフ）")
    print("  左矢印 (←)  : 1ステップ コマ戻し")
    print("  右矢印 (→)  : 1ステップ コマ送り")
    print("  Space キー   : 再生 / 一時停止")
    print("  E / Shift+E : 次 / 直前 のエピソードへジャンプ")
    print("  P / Shift+P : 次 / 直前 の知識選択へジャンプ")
    print("  A / Shift+A : 次 / 直前 の活性化へジャンプ")
    print("  W / Shift+W : 次 / 直前 の重み更新へジャンプ")
    print("  S キー       : 折れ線グラフ画面で高精細グラフ画像を保存")
    print("  O キー       : 実験ログフォルダ選択ダイアログを開く")
    print("  C キー       : ハイパーパラメータ設定一覧の表示 / 非表示")
    print("  L キー       : リアルタイム追従モードの切り替え")
    print("  H キー       : 画面の見方・ヘルプの表示/非表示")
    print("  マウス       : タイムラインスライダーのドラッグ / ボタン操作")
    print("-" * 60)

    print("[INFO] Starting Standalone SAP-net Visualizer...")
    while gui.is_active:
        if not gui.handle_events():
            break
        gui.draw()

    # 終了処理
    try:
        pygame.quit()
    except Exception:
        pass
    print("[INFO] SAP-net Visualizer terminated cleanly.")

if __name__ == "__main__":
    main()
