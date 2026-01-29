import arcpy
import os
import re

"""
Workflow
3.1 Copies spatial data points
3.2 Copies attribute values from input points
3.3 Copies domain values from input points
3.4 Updates basic fields
"""

#############################################################################################
# 1.0 HELPERS
#############################################################################################

def _workspace_from_dataset(dataset_or_layer) -> str:
    """
    Return the edit workspace for a target dataset/layer.
    Works for enterprise FGDB/SDE and file GDB.
    """
    try:
        conn_props = dataset_or_layer.connectionProperties
        if isinstance(conn_props, dict) and "connection_info" in conn_props:
            db = conn_props["connection_info"].get("database")
            if db:
                return db
        ds = dataset_or_layer.dataSource
        return os.path.dirname(ds)
    except Exception:
        return os.path.dirname(str(dataset_or_layer))

def _ds_path(dataset_or_layer) -> str:
    """Get catalog path from either a layer object or a dataset path string."""
    return dataset_or_layer.dataSource if hasattr(dataset_or_layer, "dataSource") else str(dataset_or_layer)

def _shape_type(dataset_path: str) -> str:
    return arcpy.Describe(dataset_path).shapeType

def _norm(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", str(s)).lower().strip()

def _pt_key(geom, decimals=3):
    """Stable key for a point by centroid."""
    c = geom.centroid
    return (round(c.X, decimals), round(c.Y, decimals))

def _get_field_length(table, field_name):
    for f in arcpy.ListFields(table, field_name):
        if f.name.lower() == field_name.lower():
            return f.length
    return None

def _safe_set_text(row, idx, value, target_table, target_field_name, skipped, key_for_msg):
    """
    Only does length checks if the target field is TEXT and the incoming value is a string.
    """
    if value is None:
        return False

    # Find target field def
    fld = next((f for f in arcpy.ListFields(target_table, target_field_name)
                if f.name.lower() == target_field_name.lower()), None)

    if fld and fld.type == "String" and isinstance(value, str):
        max_len = fld.length
        if max_len and len(value) > max_len:
            msg = f"Skipping '{target_field_name}' at {key_for_msg}: value length {len(value)} > {max_len}"
            arcpy.AddWarning(msg)
            skipped.append((key_for_msg, target_field_name, value))
            return False

    row[idx] = value
    return True


#############################################################################################
# 3.1 COPY SPATIAL DATA - POINTS
#############################################################################################

def copy_points(points_to_copy, points_to_update):
    """
    Copy geometries from source into target. Inserts blank Fire_Num ('') if field exists.
    """
    src = _ds_path(points_to_copy)
    tgt = _ds_path(points_to_update)

    if _shape_type(src) != "Point" or _shape_type(tgt) != "Point":
        raise ValueError("3.1 Both inputs must be Point feature classes/layers.")

    workspace = _workspace_from_dataset(points_to_update)

    count = 0
    with arcpy.da.Editor(workspace):
        with arcpy.da.SearchCursor(src, ["SHAPE@"]) as s_cur:
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

    arcpy.AddMessage(f"3.1 Copied {count} point(s) from source into target.")
    return count


#############################################################################################
# 3.2 COPY ATTRIBUTES BASED ON LOCATION - POINTS
#############################################################################################

def copy_attributes_based_on_location_points(points_to_copy, points_to_update):
    """
    Copies NON-DOMAIN attributes by matching centroid XY.
    Domain fields (RPtType*) are handled in 3.3 only.
    """
    src = _ds_path(points_to_copy)
    tgt = _ds_path(points_to_update)

    arcpy.AddMessage("3.2 Starting attribute copy process...")

    src_fields = [f.name for f in arcpy.ListFields(src)]
    tgt_fields = [f.name for f in arcpy.ListFields(tgt)]

    field_mapping = {}

    # CaptureDate mapping (only if target has CaptureDate)
    if "CaptureDate" in tgt_fields:
        if "TimeStamp" in src_fields:
            field_mapping["CaptureDate"] = "TimeStamp"
        elif "TimeWhen" in src_fields:
            field_mapping["CaptureDate"] = "TimeWhen"

    # Comments mapping
    if "Comments" in tgt_fields:
        if "desc" in src_fields:
            field_mapping["Comments"] = "desc"
        elif "Descr" in src_fields:
            field_mapping["Comments"] = "Descr"

    # Label mapping
    if "Label" in tgt_fields:
        if "name" in src_fields:
            field_mapping["Label"] = "name"
        elif "Name" in src_fields:
            field_mapping["Label"] = "Name"

    # Same-name “normal” fields (exclude domain-managed fields here!)
    for f in ["CritWork", "ProtValue"]:
        if f in src_fields and f in tgt_fields:
            field_mapping[f] = f

    if not field_mapping:
        arcpy.AddWarning("3.2 No matching attribute fields found to copy. Skipping 3.2.")
        return 0, 0

    arcpy.AddMessage(f"3.2 Field mapping: {field_mapping}")

    tgt_sr = arcpy.Describe(tgt).spatialReference

    # Build source index
    fields_to_copy = ["SHAPE@"] + list(field_mapping.values())
    source_index = {}

    with arcpy.da.SearchCursor(src, fields_to_copy) as cur:
        for row in cur:
            geom = row[0].projectAs(tgt_sr)
            key = _pt_key(geom, decimals=3)
            source_index[key] = row[1:]

    arcpy.AddMessage(f"3.2 Indexed {len(source_index)} source feature(s) by centroid XY.")

    # Update target
    workspace = _workspace_from_dataset(points_to_update)
    fields_to_update = ["SHAPE@"] + list(field_mapping.keys())

    skipped = []
    updated_count = 0
    unmatched_count = 0

    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(tgt, fields_to_update) as cur:
            for row in cur:
                key = _pt_key(row[0], decimals=3)
                if key not in source_index:
                    unmatched_count += 1
                    continue

                values = source_index[key]
                changed = False
                for i, val in enumerate(values):
                    tgt_field = fields_to_update[i + 1]
                    if _safe_set_text(row, i + 1, val, tgt, tgt_field, skipped, key):
                        changed = True

                if changed:
                    cur.updateRow(row)
                    updated_count += 1

    arcpy.AddMessage(f"3.2 Updated {updated_count} feature(s). Unmatched: {unmatched_count}.")
    if skipped:
        arcpy.AddWarning(f"3.2 Skipped {len(skipped)} field assignment(s) due to length constraints.")
    return updated_count, unmatched_count


#############################################################################################
# 3.3 COPY DOMAIN VALUES BASED ON LOCATION - POINTS
#############################################################################################

def copy_domain_values_based_on_location_points(points_to_copy, points_to_update):
    """
    Copies coded domain values (RPtType/RPtType2/RPtType3) by mapping source label -> code,
    matched by centroid XY. Uses sym_name as the primary label for RPtType (like your original).
    """
    src = _ds_path(points_to_copy)
    tgt = _ds_path(points_to_update)

    arcpy.AddMessage("3.3 Starting domain copy process...")

    # Your domain mapping (normalized)
    domain_mapping_raw = {
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

        # 2024 gdb variants
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
    domain_mapping = {_norm(k): v for k, v in domain_mapping_raw.items()}

    tgt_sr = arcpy.Describe(tgt).spatialReference

    src_all = [f.name for f in arcpy.ListFields(src)]
    tgt_all = [f.name for f in arcpy.ListFields(tgt)]

    # Determine what we can read from source
    read_candidates = ["sym_name", "RPtType2", "RPtType3"]
    read_fields = ["SHAPE@"] + [f for f in read_candidates if f in src_all]

    if "sym_name" not in read_fields:
        arcpy.AddWarning("3.3 Source is missing 'sym_name'. RPtType mapping may not work.")

    # Determine what we can update on target
    update_candidates = ["RPtType", "RPtType2", "RPtType3"]
    update_fields = [f for f in update_candidates if f in tgt_all]

    if not update_fields:
        arcpy.AddWarning("3.3 Target has none of RPtType/RPtType2/RPtType3. Skipping 3.3.")
        return 0, 0

    # Build source index by XY
    idx = {f: i for i, f in enumerate(read_fields)}
    source_data = {}

    with arcpy.da.SearchCursor(src, read_fields) as cur:
        for row in cur:
            geom = row[idx["SHAPE@"]].projectAs(tgt_sr)
            key = _pt_key(geom, decimals=3)

            sym = row[idx["sym_name"]] if "sym_name" in idx else None

            def get_label(field):
                if field in idx:
                    v = row[idx[field]]
                    if v is not None and str(v).strip():
                        return str(v).strip()
                return sym  # fallback

            source_data[key] = {
                "RPtType": sym,
                "RPtType2": get_label("RPtType2"),
                "RPtType3": get_label("RPtType3"),
            }

    arcpy.AddMessage(f"3.3 Indexed {len(source_data)} source feature(s) for domain mapping.")

    workspace = _workspace_from_dataset(points_to_update)

    updated = 0
    skipped = 0

    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(tgt, ["SHAPE@"] + update_fields) as cur:
            for row in cur:
                key = _pt_key(row[0], decimals=3)
                if key not in source_data:
                    skipped += 1
                    continue

                changed = False
                for i, field in enumerate(update_fields):
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

    arcpy.AddMessage(f"3.3 Updated {updated} feature(s). Skipped/unmatched: {skipped}.")
    return updated, skipped


#############################################################################################
# 3.4 UPDATE BASIC FIELDS - POINTS
#############################################################################################

def update_basic_fields_points(points_to_update, fire_number, fire_name, status):
    """
    Update Fire_Num / Fire_Name / Status on target points.
    Only fills blanks (and treats RehabRequiresFieldVerification as blank for Status).
    """
    tgt = _ds_path(points_to_update)
    workspace = _workspace_from_dataset(points_to_update)

    tgt_fields = [f.name for f in arcpy.ListFields(tgt)]
    required = ["Fire_Num", "Fire_Name", "Status"]
    missing = [f for f in required if f not in tgt_fields]
    if missing:
        arcpy.AddWarning(f"3.4 Target missing fields {missing}. Skipping 3.4.")
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

    arcpy.AddMessage(f"3.4 Updated basic fields on {updated} feature(s).")
    return updated


#############################################################################################
# EXECUTION
#############################################################################################

if __name__ == "__main__":
    # Required inputs (simplified)
    points_to_copy = arcpy.GetParameter(0)       
    points_to_update = arcpy.GetParameter(1)      
    fire_number = arcpy.GetParameterAsText(2)
    fire_name = arcpy.GetParameterAsText(3)
    status = arcpy.GetParameterAsText(4)

    copy_points(points_to_copy, points_to_update)
    copy_attributes_based_on_location_points(points_to_copy, points_to_update)
    copy_domain_values_based_on_location_points(points_to_copy, points_to_update)
    update_basic_fields_points(points_to_update, fire_number, fire_name, status)
