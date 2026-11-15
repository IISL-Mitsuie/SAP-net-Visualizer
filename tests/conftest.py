"""
pytest 共通フィクスチャ設定。
実画面のポップアップ、本番履歴ファイル(~/.sap_visualizer/)への書き込み、
およびテスト中の外部ネットワーク通信を防止する。
"""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def isolate_test_session(tmp_path_factory):
    """セッション全体で本番設定ディレクトリの保護とフォント生成キャッシュ・終了処理を行う"""
    config_dir = tmp_path_factory.mktemp("sap_visualizer_config")
    old_config_dir = os.environ.get("SAP_VISUALIZER_CONFIG_DIR")
    os.environ["SAP_VISUALIZER_CONFIG_DIR"] = str(config_dir)

    orig_sysfont = pygame.font.SysFont
    font_cache = {}

    def _cached_sysfont(name, size, bold=False, italic=False):
        cache_name = tuple(name) if isinstance(name, (list, tuple)) else name
        key = (cache_name, size, bold, italic)
        if key not in font_cache:
            font_cache[key] = orig_sysfont(name, size, bold=bold, italic=italic)
        return font_cache[key]

    pygame.font.SysFont = _cached_sysfont

    try:
        yield
    finally:
        pygame.font.SysFont = orig_sysfont
        font_cache.clear()
        if old_config_dir is None:
            os.environ.pop("SAP_VISUALIZER_CONFIG_DIR", None)
        else:
            os.environ["SAP_VISUALIZER_CONFIG_DIR"] = old_config_dir
        if pygame.get_init():
            pygame.quit()


@pytest.fixture(autouse=True)
def block_network_update_checks(monkeypatch):
    """GUI初期化時にバックグラウンドでGitHub API通信が発火するのを遮断する"""
    monkeypatch.setattr(
        "sap_visualizer.folder_selector_gui.check_for_updates_async",
        lambda *args, **kwargs: None,
    )
