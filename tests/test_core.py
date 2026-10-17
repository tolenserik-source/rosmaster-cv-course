"""Проверки численного результата и диагностик, без камеры или ROS."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
from rosmaster_cv.common import read_image, red_mask, save_image
from rosmaster_cv import lesson01_intro, lesson02_geometry, lesson03_drawing, lesson04_enhancement
from rosmaster_cv.lesson05_applications import detect_red_objects


class CoreVisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.source = self.directory / "scene.png"
        self.image = np.full((120, 160, 3), 35, dtype=np.uint8)
        cv2.rectangle(self.image, (15, 20), (54, 59), (0, 0, 255), -1)
        save_image(self.source, self.image)

    def tearDown(self):
        self.temp.cleanup()

    def test_red_mask_covers_both_hue_ends_but_rejects_green_and_gray(self):
        hsv = np.uint8([[[2, 255, 255], [178, 255, 255], [60, 255, 255], [0, 0, 180], [0, 255, 20]]])
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        np.testing.assert_array_equal(red_mask(bgr), np.uint8([[255, 255, 0, 0, 0]]))

    def test_missing_image_has_actionable_diagnostic(self):
        with self.assertRaisesRegex(FileNotFoundError, "Не найдено изображение.*--input"):
            read_image(self.directory / "missing.png")

    def test_intro_pixel_values_and_grayscale_dimensions(self):
        images, report = lesson01_intro.process(self.image, 20, 25)
        self.assertEqual(report["pixel_bgr"], [0, 0, 255])
        self.assertEqual((report["width"], report["height"]), (160, 120))
        self.assertEqual(images["grayscale"].shape, (120, 160))
        self.assertEqual(int(images["grayscale"][25, 20]), 76)

    def test_pixel_outside_image_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "вне изображения"):
            lesson01_intro.process(self.image, 160, 0)

    def test_geometry_cli_dimensions_and_horizontal_reflection(self):
        output = self.directory / "geometry"
        with contextlib.redirect_stdout(io.StringIO()):
            lesson02_geometry.main(["--input", str(self.source), "--out", str(output), "--scale", "0.5", "--crop", "10", "20", "50", "40", "--warp-size", "80", "60"])
        self.assertEqual(read_image(output / "resized.png").shape, (60, 80, 3))
        self.assertEqual(read_image(output / "cropped.png").shape, (40, 50, 3))
        self.assertEqual(read_image(output / "perspective.png").shape, (60, 80, 3))
        np.testing.assert_array_equal(read_image(output / "flipped.png"), self.image[:, ::-1])

    def test_threshold_result_has_only_two_values(self):
        output = self.directory / "drawing"
        with contextlib.redirect_stdout(io.StringIO()):
            lesson03_drawing.main(["--input", str(self.source), "--out", str(output), "--threshold", "50"])
        result = read_image(output / "threshold.png")
        self.assertEqual(set(np.unique(result)), {0, 255})
        self.assertEqual(int(result[25, 20, 0]), 255)
        self.assertEqual(int(result[5, 5, 0]), 0)

    def test_contour_center_area_and_small_noise_rejection(self):
        cv2.circle(self.image, (110, 80), 2, (0, 0, 255), -1)
        _, _, objects = detect_red_objects(self.image, min_area=100, kernel=1)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["bbox_xywh"], [15, 20, 40, 40])
        self.assertEqual(objects[0]["center_px"], [34.5, 39.5])
        self.assertEqual(objects[0]["area_px2"], 1521.0)

    def test_brightness_clips_without_unsigned_wraparound_or_absolute_value(self):
        image = np.uint8([[[10, 100, 250]]])
        np.testing.assert_array_equal(lesson04_enhancement.adjust_brightness(image, 1, -20), np.uint8([[[0, 80, 230]]]))
        np.testing.assert_array_equal(lesson04_enhancement.adjust_brightness(image, 2, 0), np.uint8([[[20, 200, 255]]]))

    def test_inpaint_creates_nonempty_mask_and_restores_uniform_region(self):
        output = self.directory / "enhancement"
        uniform = np.full((120, 160, 3), 150, dtype=np.uint8)
        save_image(self.source, uniform)
        with contextlib.redirect_stdout(io.StringIO()):
            lesson04_enhancement.main(["--input", str(self.source), "--out", str(output)])
        mask = read_image(output / "damage_mask.png")[:, :, 0] > 0
        damaged = read_image(output / "damaged.png")
        inpainted = read_image(output / "inpainted.png")
        self.assertTrue(mask.any())
        self.assertEqual(float(damaged[mask].mean()), 0)
        self.assertGreater(float(inpainted[mask].mean()), 140)

    def test_cli_missing_file_exits_with_two_and_no_traceback(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            with self.assertRaises(SystemExit) as raised:
                lesson01_intro.main(["--input", str(self.directory / "missing.png"), "--out", str(self.directory / "unused")])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("Не найдено изображение", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
