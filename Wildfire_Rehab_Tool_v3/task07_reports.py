# -*- coding: utf-8 -*-
import os
import csv
import arcpy
from datetime import datetime


# ---------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------
FIELD_SYNONYMS = {
    "RLType": ["RLType1"],
    "FLType": ["FLType1"],
    "Comments": ["Description"],
}


def get_bool_param(i: int, default: bool = False) -> bool:
    v = arcpy.GetParameterAsText(i)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip().lower() in ("true", "t", "1", "yes", "y")

def resolve_field_map(fc: str, canonical_fields: list, synonyms: dict) -> dict:
    """
    Returns a mapping: canonical_field -> actual_field_in_fc (or None if not found)

    synonyms example:
      {"RLType": ["RLType1"], "Comments": ["Description"]}
    """
    existing = {f.name for f in arcpy.ListFields(fc)}
    out = {}

    for canon in canonical_fields:
        if canon in existing:
            out[canon] = canon
            continue

        # try alternates
        found = None
        for alt in synonyms.get(canon, []):
            if alt in existing:
                found = alt
                break
        out[canon] = found  # can be None

    return out


def district_to_region(fire_number: str) -> str:
    district_map = {
        "C": "Cariboo",
        "V": "Coastal",
        "K": "Kamloops",
        "R": "NorthWest",
        "G": "PrinceGeorge",
        "N": "SouthEast"
    }
    code = fire_number[0].upper()
    region = district_map.get(code)
    if not region:
        raise ValueError(f"Unknown district code '{code}' in fire_number '{fire_number}'")
    return region


def default_reports_folder(fire_year: str, fire_number: str) -> str:
    region = district_to_region(fire_number)
    fire_code = fire_number[:2]
    return fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{region}\{fire_code}\{fire_number}\Outputs\Reports"


def ensure_folder(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def list_fields(fc: str) -> set:
    return {f.name for f in arcpy.ListFields(fc)}


def invert_domain_map_label_to_code(domain_mapping_raw: dict) -> dict:
    """
    Input: {label: "2", ...}
    Output: {2: label, ...}
    Keeps first label encountered for each code.
    """
    code_to_label = {}
    for label, code in domain_mapping_raw.items():
        try:
            code_int = int(code)
        except Exception:
            continue
        if code_int not in code_to_label:
            code_to_label[code_int] = label
    return code_to_label


def safe_int(v):
    try:
        return int(v)
    except Exception:
        return v


def write_csv(path: str, header: list, rows_iter):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows_iter:
            w.writerow(r)


# ---------------------------------------------------------------------
# Width extraction for lines (from Comments)
# ---------------------------------------------------------------------
def extract_width_from_comments(comments):
    """
    Extract token immediately preceding first 'm'. If range like '5-10', returns average.
    Returns float or None.
    """
    if not comments or "m" not in comments:
        return None
    try:
        token = comments.split("m")[0].split()[-1]
        if "-" in token:
            a, b = token.split("-", 1)
            return (float(a) + float(b)) / 2.0
        return float(token)
    except Exception:
        return None


# ---------------------------------------------------------------------
# Domain dictionaries (as provided)
# ---------------------------------------------------------------------
def get_points_rpttype_domain_raw() -> dict:
    return {
        'Berm Breach BB': '2',
        'Berm High BH': '43',
        'Cleared Area CA': '42',
        'Cross Ditch Culvert Backup CDB': '50',
        'Cross Ditch Install CDI': '6',
        'Cross Ditch Repair CDR': '7',
        'Culvert Clean Repair CC': '8',
        'Culvert Insert CI': '9',
        'Culvert No Damage CND': '51',
        'Culvert Remove and Dispose CRD': '52',
        'Ditch Clean Repair DCR': '14',
        'Ditch Install DI': '15',
        'Domestic Water Supply W': '18',
        'Dry Seed DS': '19',
        'Existing Deactivation ED': '20',
        'Hazard H': '27',
        'Infrastructure No Treatment INT': '53',
        'Infrastructure Repair IR': '54',
        'Lowbed Turnaround LBT': '55',
        'No Treatment Point NT': '41',
        'No Work Zone NWZ': '56',
        'Other Rehab Treatment Type ORT': '46',
        'Point of Commencement Termination PCT': '49',
        'Pull Back PB': '30',
        'Recontour RC': '31',
        'Restore Draw RD': '32',
        'Seepage SG': '48',
        'Steep Slope SS': '36',
        'Stream Crossing Classified SCC': '60',
        'Stream Crossing Non Classified SCN': '37',
        'Sump SP': '38',
        'Unassigned UN': '99',
        'Unique Point UP': '40',
        'Water Bar WB': '39',
        'Wood Bunched BW': '47',
        'Wood Burn Pile BPW': '34',
        'Wood Decked DW': '13',

        # 2024 gdb
        'Steep Slope gt 35% (SS)': '36',
        'Breach Berm (BB)': '2',
        'Cattle Guard Damage (CGD)': '3',
        'Cattle Guard No Damage (CGND)': '4',
        'Cleared Area (CA)': '42',
        'Cross Ditch - Install (CDI)': '6',
        'Cross Ditch - Repair (CDR)': '7',
        'Culvert - Clean/Repair Culvert (CC)': '8',
        'Culvert - Insert Metal (MC)': '9',
        'Culvert - Insert Wood (WC)': '10',
        'Culvert - Remove and Dispose (RC)': '11',
        'Culvert - Rock Ford / Squamish (SO)': '12',
        'Decked Wood (DW)': '13',
        'Ditch - Clean/Repair (CD)': '14',
        'Ditch - Install (ID)': '15',
        'Ditch - Install French Drain (FD)': '16',
        'Ditch - Install Rock Check Dam (ID)': '17',
        'Domestic Water Supply (W)': '18',
        'Dry Seed (DS)': '19',
        'Existing Deactivation (ED)': '20',
        'Fence Damage - Point (FD)': '21',
        'Fence No Damaged - Point (FND)': '22',
        'Ford - Install (FI)': '23',
        'Ford - Removal (FR)': '24',
        'Gate Damage (GD)': '25',
        'Gate No Damage (GND)': '26',
        'Hazard (H)': '27',
        'High Berm (HB)': '43',
        'Point of Commencement (POC)': '28',
        'Point of Termination (POT)': '29',
        'Pull Back (PB)': '30',
        'Recontour (RC)': '31',
        'Restore Draw (RD)': '32',
        'Safety Zone (SZ)': '33',
        'Slash / Burn Pile / Hazard (SBP)': '34',
        'Staging Area (SA)': '35',
        'Steep Slope >35% (SS)': '36',
        'Stream Crossing (SC)': '37',
        'Sump (SP)': '38',
        'Water Bar (WB)': '39',
        'Unique Point (UP)': '40',
        'No Treatment - Point (NA)': '41',
        'Unassigned': '99',
        'Division Label': '98',
        'Straw Bales (SB)': '44',
        'Danger Tree Treatment Required (DTA)': '45',
        'Armouring / Coco Matting / Rip Rap (ACR)': '1',
        'Other Rehab Treatment Type': '46',
        'Bunched Wood (BW)': '47',
        'Seepage (SG)': '48',
        'Point of Commencement / Termination (PTC)': '49'
    }


def get_lines_rltype_domain_raw() -> dict:
    return {
        'Clean Ditch (CD)': '1',
        'Dry Seed (DS)': '2',
        'Fence - Damaged (FD)': '3',
        'Fence - Undamaged (FND)': '4',
        'Danger Tree Treatment Required (DTA)': '14',
        'Grade Road (GR)': '5',
        'Pull Back (PB)': '6',
        'Recontour (RC)': '7',
        'Steep Slopes >35% (SS)': '10',
        'No Treatment - Line (NA)': '11',
        'Hazard (H)': '13',
        'Unassigned': '99',
        'Fuel Hazard Treatment Required (FHT)': '15',
        'Division Break': '89',
        'Other Rehab Treatment Type': '16',
        'Road Damage - Requires Repair (RR)': '9',

        'Ditch Clean Repair DCR': '1',
        'Dry Seed DS': '2',
        'Fire Hazard Treatment FHT': '13',
        'Grade Road GR': '5',
        'Infrastructure No Treatment INT': '21',
        'Infrastructure Repair IR': '20',
        'No Treatment NT': '11',
        'No Work Zone NWZ': '22',
        'Other Rehab Treatment Type ORT': '16',
        'Pull Back PB': '6',
        'Recontour RC': '7',
        'Steep Slopes SS': '10'
    }


def get_lines_fltype_domain_raw() -> dict:
    return {
        'Unknown': '0',
        'Active Burnout': '1',
        'Aerial Foam Drop': '2',
        'Aerial Hazard': '3',
        'Aerial Ignition': '4',
        'Aerial Retardant Drop': '5',
        'Aerial Water Drop': '6',
        'Branch Break': '7',
        'Completed Burnout': '8',
        'Completed Machine Line': '9',
        'Completed Handline': '10',
        'Completed Line': '11',
        'Division Break': '12',
        'Danger Tree Assessed': '13',
        'Danger Tree Assessed/Felled': '14',
        'Escape Route': '15',
        'Fire Break Planned or Incomplete': '16',
        'Fire Spread Prediction': '17',
        'Highlighted Geographic Feature': '18',
        'Highlighted Manmade Feature': '19',
        'Line Break Complete': '20',
        'Planned Fire Line': '21',
        'Planned Secondary Line': '22',
        'Proposed Burnout': '23',
        'Proposed Machine Line': '24',
        'Trigger Point': '25',
        'Uncontrolled Fire Edge': '26',
        'Other': '27',
        'Contingency Line': '28',
        'No Work Zone': '29',
        'Completed Fuel Free Line': '30',
        'Road - Modified Existing': '32',
        'Trail': '34',
        'Road': '31',
        'Road - Heavily Used': '33',
        'Pipeline': '35',
        'Completed Hoselay': '36',
        'Containment / Control Line': '37',

        # duplicates / alt labels
        'Containment Control Line': '37',
        'Completed Fuel Free Line FF': '30',
        'Completed Handline HL': '10',
        'Completed Machine Line MG': '9',
        'Road Heavily Used RHU': '33',
        'Road Modified Existing REM': '32',
        'Trail TR': '34'
    }


# ---------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------
def export_point_stats(points_fc: str, out_csv: str, scratch_gdb: str, fire_number: str):
    case_field = "RPtType"
    stats_table = os.path.join(scratch_gdb, f"{fire_number}_Point_Stats")
    statistics_fields = [["OBJECTID", "COUNT"]]

    domain_code_to_label = invert_domain_map_label_to_code(get_points_rpttype_domain_raw())

    arcpy.Statistics_analysis(points_fc, stats_table, statistics_fields, case_field)

    def rows():
        with arcpy.da.SearchCursor(stats_table, [case_field, "COUNT_OBJECTID"]) as cur:
            for code_val, cnt in cur:
                key = safe_int(code_val)
                label = domain_code_to_label.get(key, f"Unknown ({code_val})")
                yield [label, cnt]

    write_csv(out_csv, ["RPtType", "COUNT_OBJECTID"], rows())


def export_line_stats(lines_fc: str, out_csv: str, scratch_gdb: str, fire_number: str):
    """
    Line stats grouped by RLType + FLType (no Label).
    Also supports alternate field names:
      RLType1 -> RLType
      FLType1 -> FLType
      Description -> Comments (for width extraction)
    """

    # Canonical fields we need for this report
    canonical_needed = ["RLType", "FLType", "Comments"]

    # Resolve canonical -> actual field name present in FC (or None)
    field_map = resolve_field_map(lines_fc, canonical_needed, FIELD_SYNONYMS)

    rl_field = field_map.get("RLType")      # could be "RLType" or "RLType1"
    fl_field = field_map.get("FLType")      # could be "FLType" or "FLType1"
    cmt_field = field_map.get("Comments")   # could be "Comments" or "Description"

    if rl_field is None or fl_field is None:
        raise RuntimeError(
            "Line stats: could not find required grouping fields. "
            f"Resolved RLType -> {rl_field}, FLType -> {fl_field}"
        )

    stats_table = os.path.join(scratch_gdb, f"{fire_number}_Line_Stats")

    # Run statistics grouped by the ACTUAL fields (rl_field/fl_field)
    statistics_fields = [["OBJECTID", "COUNT"], ["Shape_Length", "SUM"]]
    case_fields_actual = [rl_field, fl_field]
    arcpy.Statistics_analysis(lines_fc, stats_table, statistics_fields, case_fields_actual)

    # Domain decode dicts (code -> label)
    rl_code_to_label = invert_domain_map_label_to_code(get_lines_rltype_domain_raw())
    fl_code_to_label = invert_domain_map_label_to_code(get_lines_fltype_domain_raw())

    # Average width grouped by (RLType, FLType) using Comments/Description if available
    avg_width = {}
    if cmt_field is not None:
        width_vals = {}
        with arcpy.da.SearchCursor(lines_fc, [rl_field, fl_field, cmt_field]) as cur:
            for rl, fl, comments in cur:
                w = extract_width_from_comments(comments)
                if w is None:
                    continue
                key = (rl, fl)
                width_vals.setdefault(key, []).append(w)
        avg_width = {k: (sum(v) / len(v)) for k, v in width_vals.items()}
    else:
        arcpy.AddWarning("Line stats: no Comments/Description field found; Width column will be empty.")

    # Write CSV using CANONICAL headers
    header = ["RLType", "FLType", "COUNT_OBJECTID", "SUM_Shape_Length", "Width"]

    def rows():
        # stats table fields are the ACTUAL grouping fields
        fields = case_fields_actual + ["COUNT_OBJECTID", "SUM_Shape_Length"]
        with arcpy.da.SearchCursor(stats_table, fields) as cur:
            for rl, fl, cnt, sum_len in cur:
                rl_txt = rl_code_to_label.get(safe_int(rl), f"Unknown ({rl})")
                fl_txt = fl_code_to_label.get(safe_int(fl), f"Unknown ({fl})")

                w = avg_width.get((rl, fl), None)
                if w is not None:
                    w = round(w, 1)

                yield [rl_txt, fl_txt, cnt, sum_len, w]

    write_csv(out_csv, header, rows())




def export_point_feature_report(points_fc: str, out_csv: str):
    fields_to_export = ["Label", "CaptureDate", "RPtType", "Comments", "Status"]
    existing = list_fields(points_fc)

    export_fields = [f for f in fields_to_export if f in existing]
    missing = [f for f in fields_to_export if f not in existing]
    if missing:
        arcpy.AddWarning(f"Points report: skipping missing fields: {', '.join(missing)}")

    if not export_fields:
        raise RuntimeError("Points report: no fields available to export.")

    domain_code_to_label = invert_domain_map_label_to_code(get_points_rpttype_domain_raw())

    rpt_idx = export_fields.index("RPtType") if "RPtType" in export_fields else None
    label_idx = export_fields.index("Label") if "Label" in export_fields else None

    def rows():
        with arcpy.da.SearchCursor(points_fc, export_fields) as cur:
            for row in cur:
                row = list(row)

                # decode domain
                if rpt_idx is not None:
                    v = row[rpt_idx]
                    if v is None:
                        row[rpt_idx] = ""
                    else:
                        row[rpt_idx] = domain_code_to_label.get(safe_int(v), f"Unknown ({v})")

                # Excel-safe label (force text)
                if label_idx is not None and row[label_idx] is not None:
                    row[label_idx] = "'" + str(row[label_idx])

                yield row

    write_csv(out_csv, export_fields, rows())


def export_line_feature_report(lines_fc: str, out_csv: str):
    # Canonical fields we WANT in output (always)
    canonical_fields = [
        "Label", "CaptureDate",
        "RLType", "FLType",
        "FLType2", "RLType_2", "RLType_3",
        "LineWidth", "Comments", "Status"
    ]

    # Resolve canonical -> actual field in this FC (may be synonyms like RLType1)
    field_map = resolve_field_map(lines_fc, canonical_fields, FIELD_SYNONYMS)

    # Build list of fields we can actually read in a cursor
    cursor_fields = [actual for actual in field_map.values() if actual is not None]

    missing = [k for k, v in field_map.items() if v is None]
    if missing:
        arcpy.AddWarning(
            f"Lines report: these fields not found (will be empty in CSV): {', '.join(missing)}"
        )

    rl_code_to_label = invert_domain_map_label_to_code(get_lines_rltype_domain_raw())
    fl_code_to_label = invert_domain_map_label_to_code(get_lines_fltype_domain_raw())

    # Domain-decoded fields (canonical names)
    rl_fields = {"RLType", "RLType_2", "RLType_3"}
    fl_fields = {"FLType", "FLType2"}

    def decode(canon_field, val):
        if val is None:
            return ""
        key = safe_int(val)
        if canon_field in rl_fields:
            return rl_code_to_label.get(key, f"Unknown ({val})")
        if canon_field in fl_fields:
            return fl_code_to_label.get(key, f"Unknown ({val})")
        return val

    # Build quick lookup: actual_field -> index in cursor row
    idx = {f: i for i, f in enumerate(cursor_fields)}

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(canonical_fields)  # ✅ always canonical header

        with arcpy.da.SearchCursor(lines_fc, cursor_fields) as cur:
            for row in cur:
                out_row = []
                for canon in canonical_fields:
                    actual = field_map.get(canon)
                    if actual is None:
                        out_row.append("")  # field missing entirely
                    else:
                        out_row.append(decode(canon, row[idx[actual]]))
                w.writerow(out_row)



# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    fire_year = arcpy.GetParameterAsText(0)
    fire_number = arcpy.GetParameterAsText(1)
    points_fc = arcpy.GetParameterAsText(2)
    lines_fc = arcpy.GetParameterAsText(3)
    out_folder = arcpy.GetParameterAsText(4)
    overwrite = get_bool_param(5, True)

    if not fire_year or not fire_number or not points_fc or not lines_fc:
        raise ValueError("Fire Year, Fire Number, Points FC, and Lines FC are required.")

    if not out_folder:
        out_folder = default_reports_folder(fire_year, fire_number)

    ensure_folder(out_folder)

    arcpy.env.overwriteOutput = overwrite

    # Use Scratch GDB for temp stats tables
    scratch_gdb = arcpy.env.scratchGDB
    if not scratch_gdb or not arcpy.Exists(scratch_gdb):
        raise RuntimeError("scratchGDB is not available. Check ArcGIS Pro environment settings.")

    # Output paths
    out_point_stats = os.path.join(out_folder, f"{fire_number}_Point_Stats.csv")
    out_line_stats = os.path.join(out_folder, f"{fire_number}_Line_Stats.csv")
    out_point_report = os.path.join(out_folder, f"{fire_number}_Point_Feature_Report.csv")
    out_line_report = os.path.join(out_folder, f"{fire_number}_Line_Feature_Report.csv")

    arcpy.AddMessage(f"Reports folder: {out_folder}")
    arcpy.AddMessage("Generating 4 CSV reports...")

    export_point_stats(points_fc, out_point_stats, scratch_gdb, fire_number)
    arcpy.AddMessage(f"✅ Points stats: {out_point_stats}")

    export_line_stats(lines_fc, out_line_stats, scratch_gdb, fire_number)
    arcpy.AddMessage(f"✅ Lines stats: {out_line_stats}")

    export_point_feature_report(points_fc, out_point_report)
    arcpy.AddMessage(f"✅ Points feature report: {out_point_report}")

    export_line_feature_report(lines_fc, out_line_report)
    arcpy.AddMessage(f"✅ Lines feature report: {out_line_report}")

    arcpy.AddMessage("✅ All reports created successfully.")


if __name__ == "__main__":
    main()
