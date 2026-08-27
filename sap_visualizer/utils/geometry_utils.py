"""
SAP-net Visualizer 幾何計算・レイアウト計算純粋関数モジュール
"""
import math
from typing import List, Tuple, Callable


def calculate_circular_node_positions(
    num_nodes: int,
    center_x: int,
    center_y: int,
    radius: int
) -> List[Tuple[int, int]]:
    """
    指定されたノード数に基づき、円周上に均等配置された各ノードの中心座標 (x, y) リストを算出する。
    12時方向（上端）から時計回りに配置。
    """
    if num_nodes <= 0:
        return []

    positions = []
    for i in range(num_nodes):
        angle = 2 * math.pi * i / max(1, num_nodes) - math.pi / 2
        nx = center_x + int(radius * math.cos(angle))
        ny = center_y + int(radius * math.sin(angle))
        positions.append((nx, ny))
    return positions


def calculate_edge_badge_position(
    p1: Tuple[int, int],
    p2: Tuple[int, int],
    center_x: int,
    center_y: int,
    center_avoidance_dist: float = 30.0
) -> Tuple[int, int]:
    """
    ノード p1, p2 間のエッジ中央に配置する数値バッジの座標 (badge_x, badge_y) を算出する。
    中心部に近すぎる場合は交差文字の重複を防ぐため 35% 位置にシフトする。
    """
    mid_x = (p1[0] + p2[0]) / 2.0
    mid_y = (p1[1] + p2[1]) / 2.0

    dist_to_center = math.hypot(mid_x - center_x, mid_y - center_y)
    if dist_to_center < center_avoidance_dist:
        badge_x = int(p1[0] + 0.35 * (p2[0] - p1[0]))
        badge_y = int(p1[1] + 0.35 * (p2[1] - p1[1]))
    else:
        badge_x = int(mid_x)
        badge_y = int(mid_y)

    return badge_x, badge_y


def calculate_downsampled_indices(total_frames: int, chart_width: int) -> List[int]:
    """
    大規模ログ描画時の高速化のため、表示幅に応じた適切な間引きインデックスリストを算出する。
    先頭フレームと末尾フレームは必ず含む。
    """
    if total_frames <= 0:
        return []
    if total_frames == 1:
        return [0]

    stride = max(1, total_frames // max(1, chart_width * 2))
    indices = list(range(0, total_frames, stride))
    if indices[-1] != total_frames - 1:
        indices.append(total_frames - 1)
    return indices


def calculate_legend_layout(
    vis_node_indices: List[int],
    get_text_width_func: Callable[[str], int],
    gx: int,
    gy: int,
    gw: int,
    gh: int,
    item_gap: int = 18,
    icon_w: int = 16,
    row_h: int = 24
) -> Tuple[List[Tuple[int, int, int, str]], int]:
    """
    画像保存用などの凡例アイテムを行ごとに中央揃え（Center Alignment）で配置計算する。
    
    戻り値:
        Tuple[List[Tuple[node_idx, item_x, item_y, label_str]], final_bottom_y]
    """
    if not vis_node_indices:
        return [], gy + gh + 58

    legend_start_y = gy + gh + 58
    rows = []
    current_row = []
    current_row_w = 0

    for i in vis_node_indices:
        label_str = f"知識 {i}"
        lbl_w = get_text_width_func(label_str)
        item_w = icon_w + lbl_w + item_gap

        if current_row and (current_row_w + item_w > gw):
            rows.append((current_row, current_row_w))
            current_row = [(i, item_w, label_str)]
            current_row_w = item_w
        else:
            current_row.append((i, item_w, label_str))
            current_row_w += item_w

    if current_row:
        rows.append((current_row, current_row_w))

    legend_items = []
    cur_y = legend_start_y
    for r_items, r_width in rows:
        actual_w = max(0, r_width - item_gap)
        start_x = gx + (gw - actual_w) // 2

        cur_x = start_x
        for i, item_w, label_str in r_items:
            legend_items.append((i, cur_x, cur_y, label_str))
            cur_x += item_w
        cur_y += row_h

    return legend_items, cur_y


def wrap_text_to_lines(
    text: str,
    get_width_func: Callable[[str], int],
    max_width: int
) -> List[str]:
    """
    指定した最大ピクセル幅(max_width)に合わせてテキストを自動改行（行分割）する。
    """
    if not text:
        return []

    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        if get_width_func(test_line) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)

    return lines
