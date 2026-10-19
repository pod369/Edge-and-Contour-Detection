"""Compare Sobel and Canny edges and display contours longer than a point threshold."""

import argparse
import json
from pathlib import Path
import time

import cv2 as cv
import numpy as np


PROJECT_DIR = Path(__file__).resolve().parent
ASSET_DIR = PROJECT_DIR / "assets"


def recorded_path(path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_DIR).as_posix()
    except ValueError:
        return str(resolved)


def write_image(path, image):
    if not cv.imwrite(str(path), image):
        raise OSError(f"Could not save image: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=ASSET_DIR / "river.jpg")
    parser.add_argument("--min-contour-points", type=int, default=100,
                        help="Keep contours with strictly more than this many sampled boundary points.")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_DIR / "outputs")
    parser.add_argument("--show", action="store_true", help="Display images; requires a GUI-enabled OpenCV build.")
    args = parser.parse_args()
    if args.min_contour_points < 0:
        parser.error("--min-contour-points must be nonnegative.")
    image = cv.imread(str(args.image), cv.IMREAD_COLOR)
    if image is None:
        parser.error(f"Could not read image: {args.image}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    gradient_x = cv.Sobel(gray, cv.CV_32F, 1, 0, ksize=3)
    gradient_y = cv.Sobel(gray, cv.CV_32F, 0, 1, ksize=3)
    sobel_x, sobel_y = cv.convertScaleAbs(gradient_x), cv.convertScaleAbs(gradient_y)
    # This is the original weighted absolute-gradient visualization, not Euclidean magnitude.
    strength = cv.addWeighted(sobel_x, 0.5, sobel_y, 0.5, 0)
    canny_50_150 = cv.Canny(gray, 50, 150)
    canny_100_200 = cv.Canny(gray, 100, 200)
    contours, _ = cv.findContours(canny_100_200, cv.RETR_LIST, cv.CHAIN_APPROX_NONE)
    selected = [contour for contour in contours if len(contour) > args.min_contour_points]
    overlay = image.copy()
    cv.drawContours(overlay, selected, -1, (0, 255, 0), 2)
    elapsed = time.perf_counter() - started
    results = {
        "original.png": image, "grayscale.png": gray,
        "sobel_x.png": sobel_x, "sobel_y.png": sobel_y,
        "sobel_weighted_strength.png": strength,
        "canny_50_150.png": canny_50_150, "canny_100_200.png": canny_100_200,
        "contours_overlay.png": overlay,
    }
    for name, result in results.items():
        write_image(args.output_dir / name, result)
    metrics = {
        "input": recorded_path(args.image), "shape_hwc": list(image.shape),
        "opencv_version": cv.__version__, "processing_seconds": elapsed,
        "sobel_kernel_size": 3, "canny": {},
        "contour_source_thresholds": [100, 200], "retrieval_mode": "RETR_LIST",
        "approximation_mode": "CHAIN_APPROX_NONE", "minimum_contour_points_exclusive": args.min_contour_points,
        "all_contours": len(contours), "selected_contours": len(selected),
        "selected_contour_point_counts": [len(contour) for contour in selected],
        "selected_contour_arc_lengths_pixels": [float(cv.arcLength(contour, True)) for contour in selected],
    }
    for name, edge, thresholds in (("50_150", canny_50_150, [50, 150]), ("100_200", canny_100_200, [100, 200])):
        count = int(np.count_nonzero(edge))
        metrics["canny"][name] = {"thresholds": thresholds, "edge_pixels": count,
                                   "edge_pixel_fraction": count / edge.size}
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {key: value for key, value in metrics.items() if key not in
               ("selected_contour_point_counts", "selected_contour_arc_lengths_pixels")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved results to {args.output_dir.resolve()}")
    if args.show:
        for name, result in results.items():
            cv.imshow(name, result)
        cv.waitKey(0)
        cv.destroyAllWindows()


if __name__ == "__main__":
    main()
