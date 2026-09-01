import unittest
from sap_visualizer.models import LogFrame, ResolvedFrameInfo
from sap_visualizer.constants import EventType


class TestModels(unittest.TestCase):
    def test_log_frame_from_dict_full(self):
        raw = {
            "index": 10,
            "episode": 2,
            "step": 5,
            "event_type": "ACTIVATION",
            "A": [0.1, 0.8, 0.3],
            "weight": [[0.0, 0.5, 0.0], [0.5, 0.0, 0.2], [0.0, 0.2, 0.0]],
            "plan": 1,
            "selectplans": [0, 1, 0],
            "threshold": 0.25,
            "policyvalue": [0.1, 0.9, 0.2],
            "reused_action": 3,
            "custom_metadata": "test_value"
        }
        frame = LogFrame.from_dict(raw)
        self.assertEqual(frame.index, 10)
        self.assertEqual(frame.episode, 2)
        self.assertEqual(frame.step, 5)
        self.assertEqual(frame.event_type, EventType.ACTIVATION)
        self.assertEqual(frame.activations, [0.1, 0.8, 0.3])
        self.assertEqual(len(frame.weight_matrix), 3)
        self.assertEqual(frame.plan, 1)
        self.assertEqual(frame.selectplans, [0, 1, 0])
        self.assertEqual(frame.threshold, 0.25)
        self.assertEqual(frame.policyvalue, [0.1, 0.9, 0.2])
        self.assertEqual(frame.reused_action, 3)
        self.assertEqual(frame.extra_fields.get("custom_metadata"), "test_value")

    def test_log_frame_from_dict_minimal(self):
        raw = {
            "episode": 1,
            "step": 1,
            "A": [0.5, 0.2]
        }
        frame = LogFrame.from_dict(raw)
        self.assertEqual(frame.episode, 1)
        self.assertEqual(frame.step, 1)
        self.assertEqual(frame.activations, [0.5, 0.2])
        self.assertEqual(frame.weight_matrix, [])
        self.assertEqual(frame.plan, None)
        self.assertEqual(frame.threshold, 0.18)
        self.assertEqual(frame.event_type, EventType.STEP)

    def test_resolved_frame_info(self):
        info = ResolvedFrameInfo(
            plan=2,
            selectplans=[0, 0, 1],
            activations=[0.1, 0.2, 0.9],
            weight_matrix=[[0.0, 0.1, 0.2], [0.1, 0.0, 0.3], [0.2, 0.3, 0.0]],
            episode=3,
            step=12,
            event_type="STEP",
            threshold=0.18
        )
        self.assertEqual(info.plan, 2)
        self.assertEqual(info.activations[2], 0.9)
        self.assertEqual(info.episode, 3)


if __name__ == "__main__":
    unittest.main()
