"""
Export a chosen Layout (by NAME) to PDF for Wildfire Rehab maps.

Script Tool parameters (recommended):
0  Fire Year (String)              e.g., 2025
1  Fire Number (String)            e.g., C51672
2  Layout Name (String)            EXACT layout name in the CURRENT aprx
3  Map Size (Long)                 22 or 34
4  Suffix (String, optional)       e.g., West (default), leave blank for none
5  Output Folder (Folder, optional)leave blank to use standard Outputs\\Maps path
6  Resolution (Long, optional)     default 800
7  Image Quality (String, optional)BEST | BETTER | NORMAL | FASTEST
8  Compress Vector (Boolean, opt)  default True
9  Embed Fonts (Boolean, opt)      default True
10 Output Filename Override (String, optional) if provided, used as filename (no folder)
"""

import os
import arcpy
import arcpy.mp as mp
from datetime import datetime


def get_bool_param(i: int, default: bool = False) -> bool:
    """ArcGIS passes booleans as 'true'/'false' strings sometimes."""
    v = arcpy.GetParameterAsText(i)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip().lower() in ("true", "t", "1", "yes", "y")


def get_int_param(i: int, default: int) -> int:
    v = arcpy.GetParameterAsText(i)
    if v is None or str(v).strip() == "":
        return default
    return int(v)


def get_text_param(i: int, default: str = "") -> str:
    v = arcpy.GetParameterAsText(i)
    if v is None:
        return default
    v = str(v).strip()
    return v if v else default


def district_to_region(fire_number: str) -> str:
    district_map = {
        "C": "Cariboo",
        "V": "Coastal",
        "K": "Kamloops",
        "R": "NorthWest",
        "G": "PrinceGeorge",
        "N": "SouthEast"
    }
    if not fire_number:
        raise ValueError("Fire Number is empty.")
    district_code = fire_number[0].upper()
    region = district_map.get(district_code)
    if not region:
        raise ValueError(f"Unknown district code '{district_code}' in fire_number '{fire_number}'")
    return region


def find_layout_by_name(aprx, layout_name: str):
    layouts = aprx.listLayouts(layout_name)
    if layouts:
        return layouts[0]

    # If no exact match, provide a helpful message listing names
    all_names = [l.name for l in aprx.listLayouts()]
    raise RuntimeError(
        f"Layout '{layout_name}' not found. Available layouts:\n- " + "\n- ".join(all_names)
    )


def build_default_output_folder(fire_year: str, fire_number: str) -> str:
    region = district_to_region(fire_number)
    fire_code = fire_number[:2]
    return fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{region}\{fire_code}\{fire_number}\Outputs\Maps"


def build_default_filename(fire_year: str, fire_number: str, map_size: int, suffix: str) -> str:
    year_short = fire_year[-2:]
    size_labels = {34: "34 x 44", 22: "22 x 17"}
    size_label = size_labels.get(map_size)
    if size_label is None:
        raise ValueError("Map Size must be 22 or 34.")

    date_str = datetime.today().date()  # YYYY-MM-DD
    suffix_part = f"_{suffix}" if suffix else ""
    return f"{year_short} {fire_number} REHAB MAP {size_label} {date_str}{suffix_part}.pdf"


def export_layout_to_pdf(
    layout,
    out_pdf: str,
    resolution: int,
    image_quality: str,
    compress_vector: bool,
    embed_fonts: bool
) -> None:
    # Note: exportToPDF supports many optional args; keep the important ones consistent.
    layout.exportToPDF(
        out_pdf,
        resolution=resolution,
        image_quality=image_quality,
        compress_vector_graphics=compress_vector,
        embed_fonts=embed_fonts
    )


def main():
    # --- Parameters ---
    fire_year = get_text_param(0)
    fire_number = get_text_param(1)
    layout_name = get_text_param(2)

    map_size = get_int_param(3, 34)
    suffix = get_text_param(4, "")  # default matches your example
    out_folder = get_text_param(5, "")  # optional override

    resolution = get_int_param(6, 800)
    image_quality = get_text_param(7, "BEST").upper()
    compress_vector = get_bool_param(8, True)
    embed_fonts = get_bool_param(9, True)

    filename_override = get_text_param(10, "")

    if not fire_year or not fire_number or not layout_name:
        raise ValueError("Fire Year, Fire Number, and Layout Name are required.")

    valid_qualities = {"BEST", "BETTER", "NORMAL", "FASTEST"}
    if image_quality not in valid_qualities:
        raise ValueError(f"Image Quality must be one of: {', '.join(sorted(valid_qualities))}")

    # --- Project + Layout ---
    aprx = mp.ArcGISProject("CURRENT")
    layout = find_layout_by_name(aprx, layout_name)

    # --- Output folder ---
    if not out_folder:
        out_folder = build_default_output_folder(fire_year, fire_number)

    os.makedirs(out_folder, exist_ok=True)

    # --- Output filename ---
    if filename_override:
        # If user provides "something.pdf" we use it, otherwise append .pdf
        base = filename_override
        if not base.lower().endswith(".pdf"):
            base += ".pdf"
        out_pdf = os.path.join(out_folder, base)
    else:
        out_pdf = os.path.join(out_folder, build_default_filename(fire_year, fire_number, map_size, suffix))

    arcpy.AddMessage(f"Layout: {layout.name}")
    arcpy.AddMessage(f"Exporting to: {out_pdf}")
    arcpy.AddMessage(f"Resolution: {resolution}, Image quality: {image_quality}, Compress vector: {compress_vector}, Embed fonts: {embed_fonts}")

    export_layout_to_pdf(
        layout=layout,
        out_pdf=out_pdf,
        resolution=resolution,
        image_quality=image_quality,
        compress_vector=compress_vector,
        embed_fonts=embed_fonts
    )

    arcpy.AddMessage("✅ Happy days! PDF exported successfully.")
    arcpy.SetParameterAsText(11, out_pdf) if False else None  # optional if you add an output param


if __name__ == "__main__":
    main()
