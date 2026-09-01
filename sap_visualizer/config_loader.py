"""
SAP-net Visualizer ハイパーパラメータ設定ファイル（YAML）動的読み込みモジュール
特定のシミュレーション環境に依存しない汎用的なYAML解析と値の抽出を提供します。
"""
import os
import logging
from typing import List, Tuple, Optional, Any, Dict

logger = logging.getLogger(__name__)


def load_raw_config(log_file_path: Optional[str] = None) -> Optional[dict]:
    """
    ログファイルのあるディレクトリから config_used_*.yaml を探索し、生の dict として読み込んで返す。
    """
    if not log_file_path or not os.path.exists(log_file_path):
        return None

    log_dir = os.path.dirname(os.path.abspath(log_file_path))
    yaml_files = [
        os.path.join(log_dir, f)
        for f in os.listdir(log_dir)
        if f.startswith("config_used") and f.endswith(".yaml")
    ]

    if not yaml_files:
        return None

    try:
        import yaml
        with open(yaml_files[0], mode="r", encoding="utf-8") as f:
            raw_yaml = yaml.safe_load(f)
            if isinstance(raw_yaml, dict):
                return raw_yaml
    except (ImportError, ModuleNotFoundError):
        logger.warning("PyYAML is not installed. Run 'pip install pyyaml' to enable config viewer.")
    except Exception as e:
        logger.warning(f"Failed to load raw YAML config file ({yaml_files[0]}): {e}")

    return None


def get_config_threshold(log_file_path: Optional[str] = None) -> Optional[float]:
    """
    config_used_*.yaml の階層から SAP.THRESHOLD (または THRESHOLD) を再帰探索して float で取得。
    見つからない場合は None を返す。
    """
    config = load_raw_config(log_file_path)
    if not config or not isinstance(config, dict):
        return None

    def search_threshold(data: Any, parent_key: str = "") -> Optional[float]:
        if isinstance(data, dict):
            # SAPセクションを最優先で確認
            for k, v in data.items():
                k_str = str(k).upper()
                if "THRESHOLD" in k_str:
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        pass
                if isinstance(v, (dict, list)):
                    res = search_threshold(v, f"{parent_key}.{k}" if parent_key else str(k))
                    if res is not None:
                        return res
        elif isinstance(data, list):
            for item in data:
                res = search_threshold(item, parent_key)
                if res is not None:
                    return res
        return None

    # 1. まず 'SAP' セクション内を優先探索
    for k, v in config.items():
        if isinstance(k, str) and k.upper() == "SAP" and isinstance(v, dict):
            thresh = search_threshold(v, "SAP")
            if thresh is not None:
                return thresh

    # 2. 全体から探索
    return search_threshold(config)


def _format_yaml_value(val: Any) -> Tuple[str, str]:
    """
    YAMLの値を表示用文字列と型種別（'bool', 'number', 'list', 'str', 'none'）に整形
    """
    if val is None:
        return "-", "none"
    if isinstance(val, bool):
        return ("True" if val else "False"), "bool"
    if isinstance(val, (int, float)):
        return str(val), "number"
    if isinstance(val, list):
        items_str = ", ".join(str(x) for x in val)
        return f"[{items_str}]", "list"
    if isinstance(val, dict):
        return f"{{ {len(val)} items }}", "dict"
    v_str = str(val).strip().replace("\n", " ")
    if not v_str or v_str.lower() in ("none", "null", "nan", "empty"):
        return "-", "none"
    return v_str, "str"


def _flatten_section_items(data: Any, prefix: str = "") -> List[Tuple[str, str, str]]:
    """
    セクション内部の辞書・リストを再帰的に (表示キー名, 整形値, 型種別) のリストに平坦化
    """
    items: List[Tuple[str, str, str]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            current_key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                items.extend(_flatten_section_items(v, current_key))
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                for idx, sub_elem in enumerate(v):
                    items.extend(_flatten_section_items(sub_elem, f"{current_key}[{idx}]"))
            else:
                formatted_val, val_type = _format_yaml_value(v)
                items.append((current_key, formatted_val, val_type))
    else:
        formatted_val, val_type = _format_yaml_value(data)
        items.append((prefix or "VALUE", formatted_val, val_type))
    return items


def load_config_data(log_file_path: Optional[str] = None) -> Tuple[List[Dict[str, Any]], bool]:
    """
    ログファイルのあるディレクトリから config_used_*.yaml を探索し、
    セクション分割された汎用設定項目リストを動的生成して返す。
    
    戻り値:
        Tuple[List[Dict[str, Any]], yaml_loaded(bool)]
        各アイテム辞書:
            - is_section: bool (セクション見出し帯かどうか)
            - section: str (セクション名)
            - key: str (パラメータキー名)
            - value: str (整形された設定値文字列)
            - val_type: str ('number', 'bool', 'list', 'str', 'none')
    """
    raw_yaml = load_raw_config(log_file_path)
    if raw_yaml is None:
        if not log_file_path or not os.path.exists(log_file_path):
            return [
                {
                    "is_section": False,
                    "section": "STATUS",
                    "key": "CONFIG_STATUS",
                    "value": "未読み込み（ログフォルダに config_used_*.yaml が存在しません）",
                    "val_type": "none"
                }
            ], False
        log_dir = os.path.dirname(os.path.abspath(log_file_path))
        yaml_files = [
            os.path.join(log_dir, f)
            for f in os.listdir(log_dir)
            if f.startswith("config_used") and f.endswith(".yaml")
        ]
        if not yaml_files:
            return [
                {
                    "is_section": False,
                    "section": "STATUS",
                    "key": "CONFIG_STATUS",
                    "value": "フォルダ内に config_used_*.yaml が存在しません",
                    "val_type": "none"
                }
            ], False

        # PyYAML ライブラリの有無を確認
        try:
            import yaml  # noqa: F401
        except (ImportError, ModuleNotFoundError):
            return [
                {
                    "is_section": False,
                    "section": "STATUS",
                    "key": "CONFIG_STATUS",
                    "value": "PyYAML が未インストールです（'pip install pyyaml' を実行してください）",
                    "val_type": "none"
                }
            ], False

        return [
            {
                "is_section": False,
                "section": "STATUS",
                "key": "CONFIG_STATUS",
                "value": f"設定ファイル ({os.path.basename(yaml_files[0])}) の解析に失敗しました",
                "val_type": "none"
            }
        ], False

    config_entries: List[Dict[str, Any]] = []

    # 最上位キーごとにセクション分割して走査
    for section_name, section_content in raw_yaml.items():
        s_title = str(section_name).upper()
        # 1. セクション見出しヘッダーを追加
        config_entries.append({
            "is_section": True,
            "section": s_title,
            "key": s_title,
            "value": "",
            "val_type": "section"
        })

        # 2. セクション内の全パラメータを展開
        section_items = _flatten_section_items(section_content)
        for key_path, val_str, val_type in section_items:
            config_entries.append({
                "is_section": False,
                "section": s_title,
                "key": key_path,
                "value": val_str,
                "val_type": val_type
            })

    if config_entries:
        return config_entries, True

    return [
        {
            "is_section": False,
            "section": "STATUS",
            "key": "CONFIG_STATUS",
            "value": "設定ファイルが空または有効な項目がありません",
            "val_type": "none"
        }
    ], False
