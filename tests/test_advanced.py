"""Deterministic geometry/data checks; no ROS master, camera or MediaPipe needed."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest

import cv2
import numpy as np

from rosmaster_cv import lesson06_ar as ar
from rosmaster_cv import lesson07_markers as markers
from rosmaster_cv import lesson08_ros_image as ros_image
from rosmaster_cv import lesson09_ros_processing as ros_processing
from rosmaster_cv import lesson10_data as spatial
from rosmaster_cv import lesson11_mediapipe as mp_lesson
from rosmaster_cv.ros_deadline import run_with_deadline


class AdvancedGeometryTests(unittest.TestCase):
    def test_checkerboard_detection_and_planar_mapping(self):
        image = ar.make_checkerboard(7, 5)
        corners = ar.find_board(image, 7, 5)
        result, homography = ar.planar_overlay(image, corners, 7, 5)
        self.assertEqual(len(corners), 35)
        self.assertEqual(result.shape, image.shape)
        source = np.float32([[[0, 0], [299, 0], [299, 199], [0, 199]]])
        actual = cv2.perspectiveTransform(source, homography)[0]
        expected = corners.reshape(-1, 2)[[0, 6, 34, 28]]
        np.testing.assert_allclose(actual, expected, atol=1e-3)
        self.assertGreater(np.count_nonzero(result != image), 1000)

    def test_known_pinhole_pose_recovery(self):
        camera = np.float64([[600, 0, 320], [0, 600, 240], [0, 0, 1]])
        objects = ar.board_object_points(7, 5, 0.02)
        expected_t = np.float64([0.03, -0.04, 0.8]).reshape(3, 1)
        expected_r = np.float64([0.15, -0.20, 0.03]).reshape(3, 1)
        corners, _ = cv2.projectPoints(objects, expected_r, expected_t, camera, np.zeros(5))
        image = np.full((480, 640, 3), 255, np.uint8)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test_calibration.json"
            path.write_text(json.dumps({"camera_matrix": camera.tolist(),
                                        "distortion_coefficients": [0] * 5,
                                        "image_size": [640, 480]}), encoding="utf-8")
            _, data = ar.calibrated_pose(image, corners, 7, 5, 0.02, path)
            np.testing.assert_allclose(data["tvec_m"], expected_t.ravel(), atol=2e-5)
            self.assertLess(data["reprojection_rms_px"], 0.001)
            with self.assertRaisesRegex(ValueError, "resolution"):
                ar.load_calibration(path, (320, 240))

    def test_manual_quad_has_area_and_no_decoded_id(self):
        data = markers.quadrilateral_geometry([[10, 10], [110, 10], [110, 60], [10, 60]])
        self.assertEqual(data["area_px2"], 5000)
        np.testing.assert_allclose(data["centroid_px"], [60, 35])
        self.assertIsNone(data["decoded_marker_id"])
        with self.assertRaises(ValueError):
            markers.quadrilateral_geometry([[10, 10], [110, 60], [110, 10], [10, 60]])

    def test_scan_filters_invalid_ranges_and_respects_angles(self):
        points = spatial.scan_to_points([2, 2, np.nan, np.inf, 0, -1, 20],
                                         0, np.pi / 2, 0.1, 5)
        np.testing.assert_allclose(points, [[2, 0, 0], [0, 2, 0]], atol=1e-12)
        with self.assertRaises(ValueError):
            spatial.scan_to_points([1], 0, 0, 0.1, 5)

    def test_rigid_transform_and_invalid_scale(self):
        transform = np.float64([[0, -1, 0, 1], [1, 0, 0, 2], [0, 0, 1, 3], [0, 0, 0, 1]])
        result = spatial.transform_points([[1, 0, 0], [0, 1, 0]], transform)
        np.testing.assert_allclose(result, [[1, 3, 3], [0, 2, 3]])
        with self.assertRaisesRegex(ValueError, "orthonormal"):
            spatial.transform_points([[1, 0, 0]], np.diag([2, 1, 1, 1]))

    def test_raster_reports_points_outside_view(self):
        image, clipped = spatial.rasterize(np.float64([[1, 0, 0], [0, 2, 1], [100, 0, 0]]),
                                          extent=5, size=200)
        self.assertEqual(image.shape, (200, 200, 3))
        self.assertEqual(clipped, 1)


class AdvancedDataTests(unittest.TestCase):
    def test_ros_deadline_bounds_startup_and_returns_completed_result(self):
        self.assertEqual(run_with_deadline(pow, (2, 3), 5), 8)
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, "including startup"):
            run_with_deadline(time.sleep, (10,), 0.2)
        self.assertLess(time.monotonic() - started, 3)

    def test_depth_preserves_original_values_and_header(self):
        depth = np.float32([[0, 1.2, 4.5], [np.nan, 2.0, np.inf]])
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "depth.png"
            metadata = ros_image.save_converted_image(depth, output, "32FC1", passthrough=True,
                                                        header={"frame_id": "test_depth"})
            stored = np.load(str(output.with_suffix(".npy")), allow_pickle=False)
            np.testing.assert_equal(stored, depth)
            self.assertEqual(metadata["header"]["frame_id"], "test_depth")
            self.assertEqual(cv2.imread(str(output), cv2.IMREAD_GRAYSCALE).dtype, np.uint8)
            with self.assertRaisesRegex(ValueError, "depth"):
                ros_image.save_converted_image(depth, Path(temp) / "bad.png", "32FC1", True, True)

    def test_red_mask_covers_both_ends_of_hue_scale(self):
        hsv = np.zeros((10, 30, 3), np.uint8)
        hsv[:, :10] = [2, 255, 255]
        hsv[:, 10:20] = [175, 255, 255]
        hsv[:, 20:] = [100, 255, 255]
        mask = ros_processing.red_mask(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR))
        self.assertEqual(np.count_nonzero(mask), 200)
        self.assertTrue(np.all(mask[:, 20:] == 0))
        with self.assertRaises(ValueError):
            ros_processing.red_mask(np.zeros((10, 10), np.uint8))

    def test_ascii_pcd_roundtrip_and_binary_rejection(self):
        points = np.float64([[0.1, 0.2, 0.3], [-2, 1, 4]])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cloud.pcd"
            spatial.write_ascii_pcd(path, points)
            np.testing.assert_allclose(spatial.read_ascii_pcd(path), points, atol=1e-7)
            path.write_text("FIELDS x y z\nDATA binary\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "ascii"):
                spatial.read_ascii_pcd(path)

    def test_landmark_normalization_needs_no_mediapipe_import(self):
        landmark = SimpleNamespace(x=0.2, y=0.3, z=-0.1, visibility=0.9)
        result = SimpleNamespace(hand_landmarks=[[landmark]])
        groups = mp_lesson.landmarks_from_result(result, "tasks", "hands")
        self.assertEqual(groups[0][0]["x"], 0.2)
        self.assertEqual(groups[0][0]["visibility"], 0.9)
        with self.assertRaisesRegex(ValueError, "model"):
            mp_lesson.make_detector("tasks", "hands", None)

    def test_cli_rejects_unsafe_or_incomplete_parameters_before_optional_imports(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ar.main(["--synthetic", "--square-size", "0.02"]), 2)
            self.assertEqual(ros_image.main(["--topic", "/image", "--timeout", "0"]), 2)
            self.assertEqual(ros_processing.main(["--topic", "/image", "--output-topic", "/image"]), 2)
            self.assertEqual(spatial.main(["--pcd", "missing.pcd"]), 2)


if __name__ == "__main__":
    unittest.main()
