import unittest
from sap_visualizer.utils.geometry_utils import (
    calculate_circular_node_positions,
    calculate_edge_badge_position,
    calculate_downsampled_indices,
    calculate_legend_layout,
    wrap_text_to_lines,
)


class TestGeometryUtils(unittest.TestCase):
    def test_calculate_circular_node_positions(self):
        # 0ノード
        self.assertEqual(calculate_circular_node_positions(0, 200, 200, 100), [])
        
        # 4ノード (12時, 3時, 6時, 9時)
        pos = calculate_circular_node_positions(4, 200, 200, 100)
        self.assertEqual(len(pos), 4)
        # 12時方向 (x=200, y=100)
        self.assertEqual(pos[0], (200, 100))
        # 3時方向 (x=300, y=200)
        self.assertEqual(pos[1], (300, 200))
        # 6時方向 (x=200, y=300)
        self.assertEqual(pos[2], (200, 300))
        # 9時方向 (x=100, y=200)
        self.assertEqual(pos[3], (100, 200))

    def test_calculate_edge_badge_position(self):
        # 中心から離れたエッジ -> 正確に中点
        p1 = (100, 100)
        p2 = (300, 100)
        bx, by = calculate_edge_badge_position(p1, p2, 200, 300, center_avoidance_dist=30.0)
        self.assertEqual((bx, by), (200, 100))

        # 中心を通る対角エッジ -> 35%位置へシフト
        p1 = (100, 100)
        p2 = (300, 300)
        bx, by = calculate_edge_badge_position(p1, p2, 200, 200, center_avoidance_dist=30.0)
        self.assertNotEqual((bx, by), (200, 200))
        self.assertEqual(bx, 170)
        self.assertEqual(by, 170)

    def test_calculate_downsampled_indices(self):
        # 0件, 1件
        self.assertEqual(calculate_downsampled_indices(0, 500), [])
        self.assertEqual(calculate_downsampled_indices(1, 500), [0])

        # 5000件のデータを幅500pxに対してサンプリング
        indices = calculate_downsampled_indices(5000, 500)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 4999)
        self.assertLess(len(indices), 1500)

    def test_wrap_text_to_lines(self):
        # 1文字あたり10pxのダミー幅関数
        dummy_get_width = lambda s: len(s) * 10
        
        text = "ABCDEFGHIJ" # 10文字 = 100px
        # max_width = 40px -> 4文字ずつ分割
        lines = wrap_text_to_lines(text, dummy_get_width, 40)
        self.assertEqual(lines, ["ABCD", "EFGH", "IJ"])

    def test_calculate_legend_layout(self):
        dummy_get_width = lambda s: len(s) * 8
        vis_nodes = [0, 1, 2, 3, 4]
        items, end_y = calculate_legend_layout(
            vis_nodes, dummy_get_width, gx=50, gy=50, gw=300, gh=200
        )
        self.assertEqual(len(items), 5)
        self.assertGreater(end_y, 250)


if __name__ == "__main__":
    unittest.main()
