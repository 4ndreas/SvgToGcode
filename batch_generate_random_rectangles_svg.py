#!/usr/bin/env python3
"""Generate a batch of random-rectangle SVG files by editing the job list below."""

from __future__ import annotations

from pathlib import Path

from generate_random_rectangles_svg import GeneratorConfig, generate_svg_file


OUTPUT_DIR = Path("batch_output")

# Shared defaults for every file in the batch.
BASE_SETTINGS = {
    "border_margin_mm": 5.0,
    "min_rect_width_mm": 3.0,
    "max_rect_width_mm": 10.0,
    "min_rect_height_mm": 100.0,
    "max_rect_height_mm": 400.0,
    "fill_ratio": 0.02,
    "placement_attempts": 750,
    "max_consecutive_failures": 2500,
    "inner_gap_mm": None,
    "stroke_width_mm": 0.2,
}

# Add one entry per SVG file you want to generate.
# You can override any value from BASE_SETTINGS inside a single job if needed.
BATCH_JOBS = [
    {
        "output_name": "sheet_970x1430_a.svg",
        "sheet_width_mm": 970,
        "sheet_height_mm": 1430.0,
        "seed": 101,
        "variations": 6,
    },
    {
        "output_name": "sheet_900x1330_b.svg",
        "sheet_width_mm": 900.0,
        "sheet_height_mm": 1330.0,
        "seed": 102,
        "variations": 6,        
    },
    {
        "output_name": "sheet_1180x1430.svg",
        "sheet_width_mm": 1180.0,
        "sheet_height_mm": 1430.0,
        "fill_ratio": 0.03,
        "seed": 103,
        "variations": 6,           
    },
]


def make_variation_output_name(output_name: str, variation_index: int, variation_count: int) -> str:
    if variation_count <= 1:
        return output_name

    output_path = Path(output_name)
    return f"{output_path.stem}_v{variation_index:02d}{output_path.suffix}"


def build_config(
    job: dict[str, float | int | None | str],
    variation_index: int = 1,
    variation_count: int = 1,
) -> GeneratorConfig:
    data = {**BASE_SETTINGS, **job}
    output_name = make_variation_output_name(
        output_name=str(data.pop("output_name")),
        variation_index=variation_index,
        variation_count=variation_count,
    )
    seed = data.get("seed")
    if seed is not None:
        seed = int(seed) + variation_index - 1

    return GeneratorConfig(
        sheet_width_mm=float(data["sheet_width_mm"]),
        sheet_height_mm=float(data["sheet_height_mm"]),
        border_margin_mm=float(data["border_margin_mm"]),
        min_rect_width_mm=float(data["min_rect_width_mm"]),
        max_rect_width_mm=float(data["max_rect_width_mm"]),
        min_rect_height_mm=float(data["min_rect_height_mm"]),
        max_rect_height_mm=float(data["max_rect_height_mm"]),
        fill_ratio=float(data["fill_ratio"]),
        placement_attempts=int(data["placement_attempts"]),
        max_consecutive_failures=int(data["max_consecutive_failures"]),
        inner_gap_mm=None if data["inner_gap_mm"] is None else float(data["inner_gap_mm"]),
        stroke_width_mm=float(data["stroke_width_mm"]),
        seed=seed,
        output=OUTPUT_DIR / output_name,
    )


def main() -> int:
    if not BATCH_JOBS:
        print("No batch jobs configured. Add entries to BATCH_JOBS first.")
        return 1

    configs: list[GeneratorConfig] = []
    for job in BATCH_JOBS:
        variation_count = int(job.get("variations", 1))
        if variation_count <= 0:
            raise ValueError("Every batch job must have at least one variation.")

        for variation_index in range(1, variation_count + 1):
            configs.append(build_config(job, variation_index, variation_count))

    for index, config in enumerate(configs, start=1):
        validated_config, layout = generate_svg_file(config)
        achieved_ratio = layout.total_area_mm2 / (
            validated_config.sheet_width_mm * validated_config.sheet_height_mm
        )

        print(
            f"[{index}/{len(configs)}] {validated_config.output} "
            f"- rectangles={len(layout.rectangles)} "
            f"- fill={achieved_ratio:.2%}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
