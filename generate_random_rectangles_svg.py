#!/usr/bin/env python3
"""Generate an SVG sheet filled with random non-overlapping rectangles."""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rectangle:
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    def overlaps(self, other: "Rectangle", gap: float = 0.0) -> bool:
        return not (
            self.x + self.width + gap <= other.x
            or other.x + other.width + gap <= self.x
            or self.y + self.height + gap <= other.y
            or other.y + other.height + gap <= self.y
        )


@dataclass(frozen=True)
class GeneratorConfig:
    sheet_width_mm: float
    sheet_height_mm: float
    border_margin_mm: float
    min_rect_width_mm: float
    max_rect_width_mm: float
    min_rect_height_mm: float
    max_rect_height_mm: float
    fill_ratio: float
    placement_attempts: int
    max_consecutive_failures: int
    inner_gap_mm: float | None
    stroke_width_mm: float
    seed: int | None
    output: Path


@dataclass(frozen=True)
class LayoutResult:
    rectangles: list[Rectangle]
    total_area_mm2: float
    target_area_mm2: float

    @property
    def achieved_ratio(self) -> float:
        if self.target_area_mm2 <= 0:
            return 0.0
        return self.total_area_mm2 / self.target_area_mm2

    @property
    def target_reached(self) -> bool:
        return self.total_area_mm2 + 1e-9 >= self.target_area_mm2


def parse_ratio(raw_value: str) -> float:
    value = raw_value.strip()
    if value.endswith("%"):
        return float(value[:-1]) / 100.0

    ratio = float(value)
    if ratio > 1.0:
        return ratio / 100.0
    return ratio


def parse_args() -> GeneratorConfig:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an SVG sheet with random non-overlapping rectangles sized in millimeters."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--sheet-width-mm", type=float, required=True, help="Sheet width in mm.")
    parser.add_argument("--sheet-height-mm", type=float, required=True, help="Sheet height in mm.")
    parser.add_argument(
        "--border-margin-mm",
        type=float,
        default=5.0,
        help="Empty margin between the sheet border and the random rectangles.",
    )
    parser.add_argument(
        "--min-rect-width-mm",
        type=float,
        default=3.0,
        help="Minimum rectangle width in mm.",
    )
    parser.add_argument(
        "--max-rect-width-mm",
        type=float,
        default=10.0,
        help="Maximum rectangle width in mm.",
    )
    parser.add_argument(
        "--min-rect-height-mm",
        type=float,
        default=100.0,
        help="Minimum rectangle height in mm.",
    )
    parser.add_argument(
        "--max-rect-height-mm",
        type=float,
        default=400.0,
        help="Maximum rectangle height in mm.",
    )
    parser.add_argument(
        "--fill-ratio",
        type=parse_ratio,
        default=0.02,
        help="Target rectangle area as decimal or percent, for example 0.02 or 2%%.",
    )
    parser.add_argument(
        "--placement-attempts",
        type=int,
        default=750,
        help="Random placement attempts for each rectangle before retrying with a new size.",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=2500,
        help="Stop after this many failed rectangle placement attempts in a row.",
    )
    parser.add_argument(
        "--inner-gap-mm",
        type=float,
        default=None,
        help="Minimum gap to preserve between rectangles in mm. Defaults to 3 x min rectangle width.",
    )
    parser.add_argument(
        "--stroke-width-mm",
        type=float,
        default=0.2,
        help="Stroke width used when drawing the SVG rectangles.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible output.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("random_rectangles.svg"),
        help="Path of the generated SVG file.",
    )

    args = parser.parse_args()
    return GeneratorConfig(
        sheet_width_mm=args.sheet_width_mm,
        sheet_height_mm=args.sheet_height_mm,
        border_margin_mm=args.border_margin_mm,
        min_rect_width_mm=args.min_rect_width_mm,
        max_rect_width_mm=args.max_rect_width_mm,
        min_rect_height_mm=args.min_rect_height_mm,
        max_rect_height_mm=args.max_rect_height_mm,
        fill_ratio=args.fill_ratio,
        placement_attempts=args.placement_attempts,
        max_consecutive_failures=args.max_consecutive_failures,
        inner_gap_mm=args.inner_gap_mm,
        stroke_width_mm=args.stroke_width_mm,
        seed=args.seed,
        output=args.output,
    )


def validate_config(config: GeneratorConfig) -> GeneratorConfig:
    if config.sheet_width_mm <= 0 or config.sheet_height_mm <= 0:
        raise ValueError("Sheet width and height must be positive.")
    if config.border_margin_mm < 0:
        raise ValueError("Border margin must be zero or positive.")
    if config.fill_ratio <= 0 or config.fill_ratio > 1:
        raise ValueError("Fill ratio must be greater than 0 and at most 1.")
    if config.inner_gap_mm is not None and config.inner_gap_mm < 0:
        raise ValueError("Inner gap must be zero or positive.")
    if config.stroke_width_mm <= 0:
        raise ValueError("Stroke width must be positive.")
    if config.placement_attempts <= 0 or config.max_consecutive_failures <= 0:
        raise ValueError("Placement attempt limits must be positive integers.")

    if config.min_rect_width_mm <= 0 or config.min_rect_height_mm <= 0:
        raise ValueError("Minimum rectangle size must be positive.")
    if config.min_rect_width_mm > config.max_rect_width_mm:
        raise ValueError("Minimum rectangle width cannot exceed maximum rectangle width.")
    if config.min_rect_height_mm > config.max_rect_height_mm:
        raise ValueError("Minimum rectangle height cannot exceed maximum rectangle height.")

    usable_width = config.sheet_width_mm - (2.0 * config.border_margin_mm)
    usable_height = config.sheet_height_mm - (2.0 * config.border_margin_mm)

    if usable_width <= 0 or usable_height <= 0:
        raise ValueError("Border margin is too large for the selected sheet size.")

    effective_max_width = min(config.max_rect_width_mm, usable_width)
    effective_max_height = min(config.max_rect_height_mm, usable_height)

    if config.min_rect_width_mm > effective_max_width:
        raise ValueError("Rectangle width range does not fit inside the sheet.")
    if config.min_rect_height_mm > effective_max_height:
        raise ValueError("Rectangle height range does not fit inside the sheet.")

    resolved_inner_gap_mm = (
        config.inner_gap_mm
        if config.inner_gap_mm is not None
        else 3.0 * config.min_rect_width_mm
    )

    return GeneratorConfig(
        sheet_width_mm=config.sheet_width_mm,
        sheet_height_mm=config.sheet_height_mm,
        border_margin_mm=config.border_margin_mm,
        min_rect_width_mm=config.min_rect_width_mm,
        max_rect_width_mm=effective_max_width,
        min_rect_height_mm=config.min_rect_height_mm,
        max_rect_height_mm=effective_max_height,
        fill_ratio=config.fill_ratio,
        placement_attempts=config.placement_attempts,
        max_consecutive_failures=config.max_consecutive_failures,
        inner_gap_mm=resolved_inner_gap_mm,
        stroke_width_mm=config.stroke_width_mm,
        seed=config.seed,
        output=config.output,
    )


def sample_rectangle_size(rng: random.Random, config: GeneratorConfig, remaining_area: float) -> tuple[float, float] | None:
    for _ in range(50):
        width = rng.uniform(config.min_rect_width_mm, config.max_rect_width_mm)
        height = rng.uniform(config.min_rect_height_mm, config.max_rect_height_mm)
        if width * height <= remaining_area:
            return width, height

    for _ in range(50):
        width = rng.uniform(config.min_rect_width_mm, config.max_rect_width_mm)
        max_height = min(config.max_rect_height_mm, remaining_area / width)
        if max_height >= config.min_rect_height_mm:
            height = rng.uniform(config.min_rect_height_mm, max_height)
            return width, height

    for _ in range(50):
        height = rng.uniform(config.min_rect_height_mm, config.max_rect_height_mm)
        max_width = min(config.max_rect_width_mm, remaining_area / height)
        if max_width >= config.min_rect_width_mm:
            width = rng.uniform(config.min_rect_width_mm, max_width)
            return width, height

    return None


def try_place_rectangle(
    rng: random.Random,
    rectangles: list[Rectangle],
    origin_x_mm: float,
    origin_y_mm: float,
    area_width_mm: float,
    area_height_mm: float,
    width_mm: float,
    height_mm: float,
    gap_mm: float,
    attempts: int,
) -> Rectangle | None:
    max_x = origin_x_mm + area_width_mm - width_mm
    max_y = origin_y_mm + area_height_mm - height_mm
    if max_x < 0 or max_y < 0:
        return None

    for _ in range(attempts):
        candidate = Rectangle(
            x=rng.uniform(origin_x_mm, max_x),
            y=rng.uniform(origin_y_mm, max_y),
            width=width_mm,
            height=height_mm,
        )
        if all(not candidate.overlaps(existing, gap_mm) for existing in rectangles):
            return candidate

    return None


def generate_layout(config: GeneratorConfig) -> LayoutResult:
    rng = random.Random(config.seed)
    sheet_area = config.sheet_width_mm * config.sheet_height_mm
    target_area = sheet_area * config.fill_ratio
    min_area = config.min_rect_width_mm * config.min_rect_height_mm
    usable_width = config.sheet_width_mm - (2.0 * config.border_margin_mm)
    usable_height = config.sheet_height_mm - (2.0 * config.border_margin_mm)

    rectangles: list[Rectangle] = []
    total_area = 0.0
    consecutive_failures = 0

    while total_area < target_area and consecutive_failures < config.max_consecutive_failures:
        remaining_area = target_area - total_area
        if remaining_area < min_area:
            break

        size = sample_rectangle_size(rng, config, remaining_area)
        if size is None:
            break

        rectangle = try_place_rectangle(
            rng=rng,
            rectangles=rectangles,
            origin_x_mm=config.border_margin_mm,
            origin_y_mm=config.border_margin_mm,
            area_width_mm=usable_width,
            area_height_mm=usable_height,
            width_mm=size[0],
            height_mm=size[1],
            gap_mm=config.inner_gap_mm,
            attempts=config.placement_attempts,
        )
        if rectangle is None:
            consecutive_failures += 1
            continue

        rectangles.append(rectangle)
        total_area += rectangle.area
        consecutive_failures = 0

    return LayoutResult(
        rectangles=rectangles,
        total_area_mm2=total_area,
        target_area_mm2=target_area,
    )


def fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def rectangle_path(rectangle: Rectangle) -> str:
    x1 = fmt(rectangle.x)
    y1 = fmt(rectangle.y)
    x2 = fmt(rectangle.x + rectangle.width)
    y2 = fmt(rectangle.y + rectangle.height)
    return f"M {x1} {y1} H {x2} V {y2} H {x1} Z"


def build_svg(config: GeneratorConfig, layout: LayoutResult) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(config.sheet_width_mm)}mm" '
            f'height="{fmt(config.sheet_height_mm)}mm" '
            f'viewBox="0 0 {fmt(config.sheet_width_mm)} {fmt(config.sheet_height_mm)}">'
        ),
        (
            f'  <!-- seed={config.seed} rectangles={len(layout.rectangles)} '
            f'target_ratio={config.fill_ratio:.6f} achieved_area_mm2={layout.total_area_mm2:.3f} -->'
        ),
        (
            f'  <path d="{rectangle_path(Rectangle(0.0, 0.0, config.sheet_width_mm, config.sheet_height_mm))}" '
            f'fill="none" stroke="black" stroke-width="{fmt(config.stroke_width_mm)}" />'
        ),
    ]

    for rectangle in layout.rectangles:
        lines.append(
            f'  <path d="{rectangle_path(rectangle)}" '
            f'fill="none" stroke="black" stroke-width="{fmt(config.stroke_width_mm)}" />'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def write_svg(output_path: Path, svg_content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding="utf-8")


def generate_svg_file(config: GeneratorConfig) -> tuple[GeneratorConfig, LayoutResult]:
    validated_config = validate_config(config)
    layout = generate_layout(validated_config)
    svg_content = build_svg(validated_config, layout)
    write_svg(validated_config.output, svg_content)
    return validated_config, layout


def main() -> int:
    try:
        config, layout = generate_svg_file(parse_args())
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    sheet_area = config.sheet_width_mm * config.sheet_height_mm
    achieved_ratio = layout.total_area_mm2 / sheet_area if sheet_area else 0.0

    print(f"Saved SVG to: {config.output}")
    print(f"Rectangles placed: {len(layout.rectangles)}")
    print(f"Target fill ratio: {config.fill_ratio:.2%}")
    print(f"Achieved fill ratio: {achieved_ratio:.2%}")

    smallest_rect_area = config.min_rect_width_mm * config.min_rect_height_mm
    shortfall_area = max(layout.target_area_mm2 - layout.total_area_mm2, 0.0)

    if shortfall_area > smallest_rect_area + 1e-9:
        print(
            "Warning: target fill ratio was not fully reached with the current size range and placement limits.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
