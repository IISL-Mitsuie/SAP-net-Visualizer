"""
SAP-net Visualizer リソースファイル探索・パス解決モジュール
"""
import os
import sys


def get_resource_path(relative_path: str) -> str:
    """
    開発時・インストール時・PyInstallerバンドル時を問わず、
    アセット（アイコン、画像等）の絶対パスを確実に解決して返す。
    """
    # 1. PyInstaller 一時展開ディレクトリのチェック
    if hasattr(sys, "_MEIPASS"):
        meipass_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(meipass_path):
            return meipass_path

    # 2. パッケージ親ディレクトリ（リポジトリルート）からの探索
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(package_dir)
    candidate_paths = [
        os.path.join(root_dir, relative_path),
        os.path.join(package_dir, relative_path),
        os.path.join(os.getcwd(), relative_path),
    ]

    for p in candidate_paths:
        if os.path.exists(p):
            return os.path.abspath(p)

    # 見つからない場合はプロジェクトルート基準の絶対パスをデフォルト返却
    return os.path.abspath(os.path.join(root_dir, relative_path))
