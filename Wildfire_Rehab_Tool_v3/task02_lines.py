import arcpy
import os
import re

"""
Workflow
2.1 Copies spatial data lines
2.2 Copies attribute values from input lines
2.3 Copies domain values from input lines
2.4 Updates basic fields

"""

#############################################################################################
# 2.0 HELPERS
#############################################################################################

def _workspace_from_dataset(dataset_or_layer) -> str:
    """
    Return the edit workspace for a target dataset/layer.
    Works for enterprise FGDB/SDE and file GDB.
    """
    try:
        # Layer object case
        conn_props = dataset_or_layer.connectionProperties
        if isinstance(conn_props, dict) and 'connection_info' in conn_props:
            db = conn_props['connection_info'].get('database')
            if db:
                return db
        # Fallback
        ds = dataset_or_layer.dataSource
        return os.path.dirname(ds)
    except Exception:
        # dataset path case
        return os.path.dirname(str(dataset_or_layer))

def _ds_path(dataset_or_layer) -> str:
    """Get catalog path from either a layer object or a dataset path string."""
    return dataset_or_layer.dataSource if hasattr(dataset_or_layer, "dataSource") else str(dataset_or_layer)

def _shape_type(dataset_path: str) -> str:
    return arcpy.Describe(dataset_path).shapeType

def _norm(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', str(s)).lower().strip()

def _line_key(geom, decimals=3):
    """
    Produce a stable key for a polyline based on its endpoints.
    IMPORTANT: direction matters (A->B != B->A). If you want directionless matching,
    we can sort the endpoints.
    """
    fp = (round(geom.firstPoint.X, decimals), round(geom.firstPoint.Y, decimals))
    lp = (round(geom.lastPoint.X, decimals), round(geom.lastPoint.Y, decimals))
    return (fp, lp)

def _get_field_length(table, field_name) -> int | None:
    for f in arcpy.ListFields(table, field_name):
        if f.name.lower() == field_name.lower():
            return f.length
    return None

def _safe_set(row, idx, value, target_table, target_field_name, skipped_rows, key_for_msg):
    """
    Assign value into row[idx], but skip if string is too long for target field.
    """
    if value is None:
        return False

    if isinstance(value, str):
        max_len = _get_field_length(target_table, target_field_name)
        if max_len and len(value) > max_len:
            msg = f"Skipping '{target_field_name}' at {key_for_msg}: value length {len(value)} > {max_len}"
            arcpy.AddWarning(msg)
            skipped_rows.append((key_for_msg, target_field_name, value))
            return False

    row[idx] = value
    return True


#############################################################################################
# 2.1 COPY SPATIAL DATA - LINES
#############################################################################################

def copy_lines(lines_to_copy, lines_to_update):
    """
    Copy geometries from source into target. Inserts blank Fire_Num ('') like your original.
    """
    src = _ds_path(lines_to_copy)
    tgt = _ds_path(lines_to_update)

    if _shape_type(src) != "Polyline" or _shape_type(tgt) != "Polyline":
        raise ValueError("2.1 Both inputs must be Polyline feature classes/layers.")

    workspace = _workspace_from_dataset(lines_to_update)

    count = 0
    with arcpy.da.Editor(workspace):
        with arcpy.da.SearchCursor(src, ["SHAPE@"]) as s_cur:
            # Keep your Fire_Num behavior; if field doesn't exist, just insert geometry
            tgt_fields = [f.name for f in arcpy.ListFields(tgt)]
            if "Fire_Num" in tgt_fields:
                with arcpy.da.InsertCursor(tgt, ["SHAPE@", "Fire_Num"]) as i_cur:
                    for (geom,) in s_cur:
                        i_cur.insertRow((geom, ""))
                        count += 1
            else:
                with arcpy.da.InsertCursor(tgt, ["SHAPE@"]) as i_cur:
                    for (geom,) in s_cur:
                        i_cur.insertRow((geom,))
                        count += 1

    arcpy.AddMessage(f"2.1 Copied {count} line(s) from source into target.")
    return count


#############################################################################################
# 2.2 COPY ATTRIBUTES BASED ON LOCATION - LINES
#############################################################################################

def copy_attributes_based_on_location_lines(lines_to_copy, lines_to_update):
    """
    Copies attribute values by matching line endpoint keys.
    Matches endpoints after projecting source geometry into target spatial reference.
    """
    src = _ds_path(lines_to_copy)
    tgt = _ds_path(lines_to_update)

    arcpy.AddMessage("2.2 Starting attribute copy process...")

    # Build mapping from target_field -> source_field (dynamic based on source fields)
    src_fields = [f.name for f in arcpy.ListFields(src)]
    field_mapping = {}

    # CaptureDate mapping (target may have CaptureDate)
    if "CaptureDate" in [f.name for f in arcpy.ListFields(tgt)]:
        if "TimeStamp" in src_fields:
            field_mapping["CaptureDate"] = "TimeStamp"
        elif "TimeWhen" in src_fields:
            field_mapping["CaptureDate"] = "TimeWhen"

    # Comments mapping (target has Comments)
    if "Comments" in [f.name for f in arcpy.ListFields(tgt)]:
        if "desc" in src_fields:
            field_mapping["Comments"] = "desc"

    # Label mapping
    if "Label" in [f.name for f in arcpy.ListFields(tgt)]:
        if "name" in src_fields:
            field_mapping["Label"] = "name"
        elif "Name" in src_fields:
            field_mapping["Label"] = "Name"

    # Same-name fields if present in BOTH
    for f in ["CritWork", "ProtValue"]:
        if f in src_fields and f in [x.name for x in arcpy.ListFields(tgt)]:
            field_mapping[f] = f

    if not field_mapping:
        arcpy.AddWarning("2.2 No matching attribute fields found to copy. Skipping 2.2.")
        return 0, 0

    arcpy.AddMessage(f"2.2 Field mapping: {field_mapping}")

    # Spatial ref of target
    tgt_sr = arcpy.Describe(tgt).spatialReference

    # Build source index
    fields_to_copy = ["SHAPE@"] + list(field_mapping.values())
    source_index = {}

    with arcpy.da.SearchCursor(src, fields_to_copy) as cur:
        for row in cur:
            geom = row[0].projectAs(tgt_sr)
            key = _line_key(geom, decimals=3)
            source_index[key] = row[1:]  # attribute values in source-field order

    arcpy.AddMessage(f"2.2 Indexed {len(source_index)} source feature(s) by endpoints.")

    # Update target
    workspace = _workspace_from_dataset(lines_to_update)
    fields_to_update = ["SHAPE@"] + list(field_mapping.keys())

    skipped_rows = []
    updated_count = 0
    unmatched_count = 0

    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(tgt, fields_to_update) as cur:
            for row in cur:
                key = _line_key(row[0], decimals=3)
                if key not in source_index:
                    unmatched_count += 1
                    continue

                values = source_index[key]
                changed = False
                for i, val in enumerate(values):
                    tgt_field = fields_to_update[i + 1]
                    if _safe_set(row, i + 1, val, tgt, tgt_field, skipped_rows, key):
                        changed = True

                if changed:
                    cur.updateRow(row)
                    updated_count += 1

    arcpy.AddMessage(f"2.2 Updated {updated_count} feature(s). Unmatched: {unmatched_count}.")
    if skipped_rows:
        arcpy.AddWarning(f"2.2 Skipped {len(skipped_rows)} field assignment(s) due to length constraints.")
    return updated_count, unmatched_count


#############################################################################################
# 2.3 COPY DOMAIN VALUES BASED ON LOCATION - LINES
#############################################################################################

def copy_domain_values_based_on_location_lines(lines_to_copy, lines_to_update):
    """
    Copies coded domain values (RLType/FLType/etc) by mapping the source label -> code,
    matched by endpoint key. Uses 'sym_name' fallback logic similar to your original.
    """
    src = _ds_path(lines_to_copy)
    tgt = _ds_path(lines_to_update)

    arcpy.AddMessage("2.3 Starting domain copy process...")

    # ---- Domain mapping (same as your original, just normalized) ----
    domain_mapping_raw = {
        # RLType
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
        'Steep Slopes SS': '10',

        # FLType
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
        'Containment Control Line': '37',
        'Completed Fuel Free Line FF': '30',
        'Completed Handline HL': '10',
        'Completed Machine Line MG': '9',
        'Road Heavily Used RHU': '33',
        'Road Modified Existing REM': '32',
        'Trail TR': '34',

        # LineWidth
        '1m': '0',
        '5m': '1',
        '10m': '2',
        '15m': '3',
        '20m and wider': '4',

        # AvgSlope
        '0 to 15': '0',
        '16 to 25': '1',
        '26 to 35': '2',
        'above 35': '3'
    }
    domain_mapping = {_norm(k): v for k, v in domain_mapping_raw.items()}

    tgt_sr = arcpy.Describe(tgt).spatialReference

    # Determine available fields
    src_all = [f.name for f in arcpy.ListFields(src)]
    tgt_all = [f.name for f in arcpy.ListFields(tgt)]

    # We will read these if present; sym_name is used as fallback label
    optional_fields = ["RLType", "RLType2", "RLType_2", "RLType3", "RLType_3", "FLType", "FLType2", "LineWidth", "AvgSlope", "sym_name"]
    read_fields = ["SHAPE@"] + [f for f in optional_fields if f in src_all]
    if "sym_name" not in read_fields:
        arcpy.AddWarning("2.3 Source does not have 'sym_name'. Fallbacks may be less accurate.")

    # Build source_data dict
    idx = {f: i for i, f in enumerate(read_fields)}
    source_data = {}

    with arcpy.da.SearchCursor(src, read_fields) as cur:
        for row in cur:
            geom = row[idx["SHAPE@"]].projectAs(tgt_sr)
            key = _line_key(geom, decimals=3)

            sym = row[idx["sym_name"]] if "sym_name" in idx else None

            def get_label(field):
                if field in idx:
                    v = row[idx[field]]
                    if v is not None and str(v).strip():
                        return str(v).strip()
                return sym  # fallback

            source_data[key] = {
                "RLType": get_label("RLType"),
                "RLType2": get_label("RLType2") or get_label("RLType_2"),
                "RLType3": get_label("RLType3") or get_label("RLType_3"),
                "FLType": get_label("FLType"),
                "FLType2": get_label("FLType2"),
                "LineWidth": get_label("LineWidth"),
                "AvgSlope": get_label("AvgSlope"),
            }

    arcpy.AddMessage(f"2.3 Indexed {len(source_data)} source feature(s) for domain mapping.")

    # Choose target field names (handle _2 / _3 variants)
    preferred = [
        "RLType",
        "RLType2" if "RLType2" in tgt_all else "RLType_2",
        "RLType3" if "RLType3" in tgt_all else "RLType_3",
        "FLType",
        "FLType2",
        "LineWidth",
        "AvgSlope"
    ]
    fields_to_update = [f for f in preferred if f in tgt_all]
    if not fields_to_update:
        arcpy.AddWarning("2.3 Target has none of the expected domain fields. Skipping 2.3.")
        return 0, 0

    workspace = _workspace_from_dataset(lines_to_update)

    updated = 0
    skipped = 0

    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(tgt, ["SHAPE@"] + fields_to_update) as cur:
            for row in cur:
                key = _line_key(row[0], decimals=3)
                if key not in source_data:
                    skipped += 1
                    continue

                changed = False
                for i, field in enumerate(fields_to_update):
                    label = source_data[key].get(field)
                    if not label:
                        continue

                    mapped = domain_mapping.get(_norm(label))
                    if mapped is None:
                        skipped += 1
                        continue

                    row[i + 1] = mapped
                    changed = True

                if changed:
                    cur.updateRow(row)
                    updated += 1

    arcpy.AddMessage(f"2.3 Updated {updated} feature(s). Skipped/unmatched: {skipped}.")
    return updated, skipped


#############################################################################################
# 2.4 UPDATE BASIC FIELDS - LINES
#############################################################################################

def update_basic_fields_lines(lines_to_update, fire_number, fire_name, status):
    """
    Update Fire_Num / Fire_Name / Status on target lines.
    Only fills blanks (and treats RehabRequiresFieldVerification as blank for Status).
    """
    tgt = _ds_path(lines_to_update)
    workspace = _workspace_from_dataset(lines_to_update)

    tgt_fields = [f.name for f in arcpy.ListFields(tgt)]
    required = ["Fire_Num", "Fire_Name", "Status"]
    missing = [f for f in required if f not in tgt_fields]
    if missing:
        arcpy.AddWarning(f"2.4 Target missing fields {missing}. Skipping 2.4.")
        return 0

    updated = 0
    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(tgt, ["Fire_Num", "Fire_Name", "Status"]) as cur:
            for row in cur:
                changed = False

                if row[0] is None or row[0] == "":
                    row[0] = str(fire_number)
                    changed = True

                if row[1] is None or row[1] == "":
                    row[1] = str(fire_name)
                    changed = True

                if row[2] is None or row[2] == "" or row[2] == "RehabRequiresFieldVerification":
                    row[2] = str(status)
                    changed = True

                if changed:
                    cur.updateRow(row)
                    updated += 1

    arcpy.AddMessage(f"2.4 Updated basic fields on {updated} feature(s).")
    return updated


#############################################################################################
# EXECUTION
#############################################################################################

if __name__ == "__main__":
    # Required inputs (simplified)
    lines_to_copy = arcpy.GetParameter(0)      
    lines_to_update = arcpy.GetParameter(1)    
    # Basic fields (optional, but provided as parameters for the tool)
    fire_number = arcpy.GetParameterAsText(2)
    fire_name = arcpy.GetParameterAsText(3)
    status = arcpy.GetParameterAsText(4)

    copy_lines(lines_to_copy, lines_to_update)
    copy_attributes_based_on_location_lines(lines_to_copy, lines_to_update)
    copy_domain_values_based_on_location_lines(lines_to_copy, lines_to_update)
    update_basic_fields_lines(lines_to_update, fire_number, fire_name, status)

