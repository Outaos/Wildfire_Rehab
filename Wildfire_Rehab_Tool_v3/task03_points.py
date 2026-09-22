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
SOURCE_UNKNOWN = "0"
SOURCE_NON_CORRECTED_GROUND_GPS = "2"

NRS_DISTRICT_CODES = {
    "DCC": 1,
    "DCK": 2,
    "DCR": 3,
    "DCS": 4,
    "DFN": 5,
    "DKA": 6,
    "DKM": 7,
    "DMH": 8,
    "DMK": 9,
    "DND": 10,
    "DNI": 11,
    "DOS": 12,
    "DPC": 13,
    "DPG": 14,
    "DQC": 15,
    "DQU": 16,
    "DRM": 17,
    "DSC": 18,
    "DSE": 19,
    "DSI": 20,
    "DSQ": 21,
    "DSS": 22,
    "DVA": 23
}

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

#def _ds_path(dataset_or_layer) -> str:
#    """Get catalog path from either a layer object or a dataset path string."""
#    return dataset_or_layer.dataSource if hasattr(dataset_or_layer, "dataSource") else str(dataset_or_layer)
def _ds_path(dataset_or_layer) -> str:
    """
    Return the underlying catalog path for a layer or dataset.
    """
    try:
        desc = arcpy.Describe(dataset_or_layer)
        if hasattr(desc, "catalogPath") and desc.catalogPath:
            return desc.catalogPath
    except Exception:
        pass
    if hasattr(dataset_or_layer, "dataSource"):
        return dataset_or_layer.dataSource
    return str(dataset_or_layer)

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
            msg = f"Truncating '{target_field_name}' at {key_for_msg}: value length {len(value)} > {max_len}"
            arcpy.AddWarning(msg)

            value = value[:max_len] 

    if row[idx] == value:
        return False
    row[idx] = value
    return True

#############################################################################################
# 3.0 RETIRE NULL GEOMETRY RECORDS
#############################################################################################

def retire_null_geometry_points(points_to_update):
    """
    Find target point records with null/empty geometry and set Status = 'Retired'.
    """
    tgt = points_to_update  #_ds_path(points_to_update)
    arcpy.AddMessage(f"3.0 Target dataset: {tgt}")
    if not arcpy.Exists(tgt):
        raise ValueError(f"3.0 Target dataset could not be resolved: {tgt}")
    workspace = _workspace_from_dataset(points_to_update)

    tgt_fields = [f.name for f in arcpy.ListFields(tgt)]

    if "Status" not in tgt_fields:
        raise ValueError(
            "3.0 Target does not contain a Status field. "
            "Cannot retire null geometry records."
        )

    null_count = 0
    retired_count = 0
    already_retired = 0

    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(tgt, ["SHAPE@", "Status"]) as cur:
            for row in cur:
                geom = row[0]

                if geom is None or geom.pointCount == 0:
                    null_count += 1

                    if row[1] != "Retired":
                        row[1] = "Retired"
                        cur.updateRow(row)
                        retired_count += 1
                    else:
                        already_retired += 1

    arcpy.AddMessage(
        f"3.0 Identified {null_count} target point(s) with null/empty geometry."
    )
    arcpy.AddMessage(
        f"3.0 Retired {retired_count} null-geometry point(s)."
    )

    if already_retired:
        arcpy.AddMessage(
            f"3.0 {already_retired} null-geometry point(s) were already Retired."
        )

    return null_count, retired_count

#############################################################################################
# 3.1 COPY SPATIAL DATA - POINTS
#############################################################################################

def copy_points(points_to_copy, points_to_update):
    """
    Copy only new source points into target.
    Respects source selections and skips points already present in target.
    """

    src = points_to_copy
    tgt = _ds_path(points_to_update)

    source_count = int(arcpy.management.GetCount(src)[0])
    arcpy.AddMessage(f"3.1 Processing {source_count} incoming point(s).")

    if _shape_type(src) != "Point" or _shape_type(tgt) != "Point":
        raise ValueError("3.1 Both inputs must be Point feature classes/layers.")

    workspace = _workspace_from_dataset(points_to_update)
    tgt_sr = arcpy.Describe(tgt).spatialReference

    # Existing target locations
    existing_keys = set()

    with arcpy.da.SearchCursor(tgt, ["SHAPE@"]) as cur:
        for (geom,) in cur:
            if geom is None or geom.pointCount == 0:
                continue

            geom = geom.projectAs(tgt_sr)

            existing_keys.add(
                _pt_key(geom, decimals=3)
            )


    copied_count = 0
    skipped_existing = 0
    skipped_null = 0

    tgt_fields = [f.name for f in arcpy.ListFields(tgt)]

    with arcpy.da.Editor(workspace):
        with arcpy.da.SearchCursor(src, ["SHAPE@"]) as s_cur:
            if "Fire_Num" in tgt_fields:
                insert_fields = ["SHAPE@", "Fire_Num"]
            else:
                insert_fields = ["SHAPE@"]
            with arcpy.da.InsertCursor(tgt, insert_fields) as i_cur:
                for (geom,) in s_cur:
                    if geom is None or geom.pointCount == 0:
                        skipped_null += 1
                        continue
                    projected_geom = geom.projectAs(tgt_sr)
                    key = _pt_key(projected_geom, decimals=3)

                    if key in existing_keys:
                        skipped_existing += 1
                        continue

                    if "Fire_Num" in tgt_fields:
                        i_cur.insertRow((projected_geom, ""))
                    else:
                        i_cur.insertRow((projected_geom,))

                    copied_count += 1
                    existing_keys.add(key)

    arcpy.AddMessage(f"3.1 Copied {copied_count} new point(s) into target.")
    arcpy.AddMessage(f"3.1 Skipped {skipped_existing} point(s) already present in target.")
    if skipped_null:
        arcpy.AddWarning(f"3.1 Skipped {skipped_null} incoming point(s) with null/empty geometry.")

    return copied_count


#############################################################################################
# 3.2 COPY ATTRIBUTES BASED ON LOCATION - POINTS
#############################################################################################

def copy_attributes_based_on_location_points(points_to_copy, points_to_update):
    """
    Copies NON-DOMAIN attributes by matching centroid XY.
    Domain fields (RPtType*) are handled in 3.3 only.
    """
    src = points_to_copy
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

    # Comments mapping (target can be Comments OR Description)

    tgt_fields = [f.name for f in arcpy.ListFields(tgt)]

    # Determine which target field to use
    target_comment_field = None
    if "Comments" in tgt_fields:
        target_comment_field = "Comments"
    elif "Description" in tgt_fields:
        target_comment_field = "Description"

    # Map source → target
    if target_comment_field:
        for candidate in ["desc", "Desc", "description", "Description", "Descriptio", "comments", "Comments", "notes", "Notes"]:
            if candidate in src_fields:
                field_mapping[target_comment_field] = candidate
                arcpy.AddMessage(f"2.2 Using '{candidate}' as source for '{target_comment_field}'")
                break

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
            geom = row[0]
            if geom is None or geom.pointCount == 0:
                continue
            geom = geom.projectAs(tgt_sr)
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
                geom = row[0]
                if geom is None or geom.pointCount == 0:
                    continue
                key = _pt_key(geom, decimals=3)
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
    src = points_to_copy
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
        'Point of Commencement / Termination (PTC)': '49',

        # Source
        'Unknown': '0',
        'Non-corrected ground GPS': '2',
        'Non-corrected airborne GPS': '3',
        'Hand sketch of any type': '1',
        'Digitized other': '99',
        'Derived from satellite imagery': '9'
    }
    domain_mapping = {_norm(k): v for k, v in domain_mapping_raw.items()}

    tgt_sr = arcpy.Describe(tgt).spatialReference

    src_all = [f.name for f in arcpy.ListFields(src)]
    tgt_all = [f.name for f in arcpy.ListFields(tgt)]


    # Determine primary label field (sym_name OR RPtType)
    primary_label_field = None
    if "sym_name" in src_all:
        primary_label_field = "sym_name"
    elif "RPtType" in src_all:
        primary_label_field = "RPtType"
        arcpy.AddMessage("3.3 Using 'RPtType' as fallback for 'sym_name'")
    else:
        arcpy.AddWarning("3.3 Source missing both 'sym_name' and 'RPtType'. Mapping may fail.")

    # Build read fields
    #read_candidates = ["RPtType2", "RPtType3"]
    read_candidates = ["RPtType2", "RPtType3", "Source"]
    read_fields = ["SHAPE@"]

    if primary_label_field:
        read_fields.append(primary_label_field)

    read_fields += [f for f in read_candidates if f in src_all]

    # Determine what we can update on target
    update_candidates = ["RPtType", "RPtType2", "RPtType3", "Source", "CritWork", "ProtValue"]
    update_fields = [f for f in update_candidates if f in tgt_all]

    if not update_fields:
        arcpy.AddWarning("3.3 Target has none of RPtType/RPtType2/RPtType3. Skipping 3.3.")
        return 0, 0

    # Build source index by XY
    idx = {f: i for i, f in enumerate(read_fields)}
    source_data = {}

    with arcpy.da.SearchCursor(src, read_fields) as cur:
        for row in cur:
            geom = row[idx["SHAPE@"]]
            if geom is None or geom.pointCount == 0:
                continue
            geom = geom.projectAs(tgt_sr)
            key = _pt_key(geom, decimals=3)

            sym = row[idx[primary_label_field]] if primary_label_field in idx else None

            def get_label(field, allow_fallback=False):
                if field in idx:
                    v = row[idx[field]]
                    if v is not None and str(v).strip():
                        return str(v).strip()

                if allow_fallback:
                    return sym

                return None


            source_data[key] = {
                "RPtType": get_label("RPtType", allow_fallback=True),
                "RPtType2": get_label("RPtType2"),
                "RPtType3": get_label("RPtType3"),
                "Source": row[idx["Source"]] if "Source" in idx else None,
            }

    arcpy.AddMessage(f"3.3 Indexed {len(source_data)} source feature(s) for domain mapping.")

    workspace = _workspace_from_dataset(points_to_update)

    updated = 0
    skipped = 0

    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(tgt, ["SHAPE@"] + update_fields) as cur:
            for row in cur:
                geom = row[0]
                if geom is None or geom.pointCount == 0:
                    continue
                key = _pt_key(row[0], decimals=3)
                if key not in source_data:
                    skipped += 1
                    continue

                changed = False
                for i, field in enumerate(update_fields):
                    # Force CritWork to null
                    if field == "CritWork":
                        if row[i + 1] is not None:
                            row[i + 1] = None
                            changed = True
                        continue

                    if field == "ProtValue":
                        if row[i + 1] is not None:
                            row[i + 1] = None
                            changed = True
                        continue

                    label = source_data[key].get(field)

                    # Default Source if missing
                    if field == "Source" and not label:
                        if row[i + 1] != SOURCE_NON_CORRECTED_GROUND_GPS:
                            row[i + 1] = SOURCE_NON_CORRECTED_GROUND_GPS
                            changed = True
                        continue

                    if not label:
                        continue

                    mapped = domain_mapping.get(_norm(label))

                    # Source field stores TEXT domain codes
                    if field == "Source" and mapped is not None:
                        mapped = str(mapped)

                    if mapped is None:
                        skipped += 1
                        continue

                    if row[i + 1] != mapped:
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

def update_basic_fields_points(points_to_copy, points_to_update, fire_number, fire_name, status, nrs_district):
    """
    Update Fire_Num / Fire_Name / Status on target points.
    Only fills blanks (and treats RehabRequiresFieldVerification as blank for Status).
    """
    src = points_to_copy
    tgt = _ds_path(points_to_update)
    workspace = _workspace_from_dataset(points_to_update)
    tgt_sr = arcpy.Describe(tgt).spatialReference

    tgt_fields = [f.name for f in arcpy.ListFields(tgt)]
    required = [
    "Fire_Num",
    "Fire_Name",
    "Status",
    "NaturalResourceDistrict"
    ]                           #["Fire_Num", "Fire_Name", "Status", "Source", "CritWork", "ProtValue", "NaturalResourceDistrict"]
    missing = [f for f in required if f not in tgt_fields]
    if missing:
        arcpy.AddWarning(f"3.4 Target missing fields {missing}. Skipping 3.4.")
        return 0

    source_keys = set()

    with arcpy.da.SearchCursor(src, ["SHAPE@"]) as cur:
        for (geom,) in cur:
            if geom is None or geom.pointCount == 0:
                continue
            geom = geom.projectAs(tgt_sr)
            source_keys.add(_pt_key(geom, decimals=3))

    updated = 0
    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(tgt, ["SHAPE@", "Fire_Num", "Fire_Name", "Status", "NaturalResourceDistrict"]) as cur:
            for row in cur:
                geom = row[0]
                if geom is None or geom.pointCount == 0:
                    continue
                key = _pt_key(geom, decimals=3)
                if key not in source_keys:
                    continue
                changed = False

                # Fire Number
                if row[1] is None or row[1] == "":
                    row[1] = str(fire_number)
                    changed = True

                # Fire Name
                if row[2] is None or row[2] == "":
                    row[2] = str(fire_name)
                    changed = True

                # Status
                if (
                    row[3] is None
                    or row[3] == ""
                    or row[3] == "RehabRequiresFieldVerification"
                ):
                    row[3] = str(status)
                    changed = True

                # Natural Resource District
                if nrs_district and (row[4] is None or row[4] == ""):
                    mapped_district = NRS_DISTRICT_CODES.get(
                        nrs_district.upper()
                    )

                    if mapped_district is not None:
                        row[4] = mapped_district
                        changed = True
                    else:
                        arcpy.AddWarning(
                            f"Unknown NRS district code: {nrs_district}"
                        )

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
    nrs_district = arcpy.GetParameterAsText(5)

    retire_null_geometry_points(points_to_update)
    copy_points(points_to_copy, points_to_update)
    copy_attributes_based_on_location_points(points_to_copy, points_to_update)
    copy_domain_values_based_on_location_points(points_to_copy, points_to_update)
    update_basic_fields_points(points_to_copy, points_to_update, fire_number, fire_name, status, nrs_district)
