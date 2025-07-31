import arcpy
import os
import re


def normalize_label(label):
    """Normalize label by removing punctuation, spaces, and lowering case."""
    return re.sub(r'[^a-zA-Z0-9]', '', label).lower()

def copy_attributes_with_domains(source_lyr, target_lyr):
    """
    Copies domain-related attributes from source_lyr to target_lyr
    by matching point geometries and using a normalized domain mapping.
    """

    if not source_lyr.isFeatureLayer or not target_lyr.isFeatureLayer:
        arcpy.AddError("7. Both source and target must be feature layers.")
        return

    # Determine workspace for edit session
    conn_props = target_lyr.connectionProperties
    if 'connection_info' in conn_props and 'database' in conn_props['connection_info']:
        workspace = conn_props['connection_info']['database']  # SDE
        arcpy.AddMessage(f"7. Workspace (SDE): {workspace}")
    else:
        workspace = os.path.dirname(target_lyr.dataSource)  # FileGDB
        arcpy.AddMessage(f"7. Workspace (FileGDB): {workspace}")

    if not workspace:
        arcpy.AddError("7. Could not determine workspace path.")
        return

    source_path = source_lyr.dataSource
    target_path = target_lyr.dataSource
    target_sr = arcpy.Describe(target_path).spatialReference

    # Domain mapping (raw, unnormalized)
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
        ##########################
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
    domain_mapping = {normalize_label(k): v for k, v in domain_mapping_raw.items()}

    # Fields to map: {target_field: source_field}
    full_field_map = {
        "RPtType": "sym_name",
        "RPtType2": "RPtType2",
        "RPtType3": "RPtType3"
    }

    # Detect which source fields are present
    source_fields = [f.name for f in arcpy.ListFields(source_path)]
    target_fields = [f.name for f in arcpy.ListFields(target_path)]

    field_map = {}
    for target_field, source_field in full_field_map.items():
        if source_field not in source_fields:
            arcpy.AddWarning(f"7. Optional source field '{source_field}' not found. Skipping updates for '{target_field}'.")
            field_map[target_field] = None
        elif target_field not in target_fields:
            arcpy.AddWarning(f"7. Target field '{target_field}' not found. Skipping.")
            field_map[target_field] = None
        else:
            field_map[target_field] = source_field

    arcpy.AddMessage("7. Indexing source features...")
    source_data = {}

    # Only request valid (non-None) fields in SearchCursor
    valid_source_fields = [v for v in field_map.values() if v is not None]
    source_cursor_fields = ["SHAPE@"] + valid_source_fields

    with arcpy.da.SearchCursor(source_path, source_cursor_fields) as cursor:
        for row in cursor:
            geom = row[0].projectAs(target_sr)
            coords = (round(geom.centroid.X, 3), round(geom.centroid.Y, 3))
            source_data[coords] = dict(zip(valid_source_fields, row[1:]))

    arcpy.AddMessage(f"7. {len(source_data)} source points indexed.")

    arcpy.AddMessage("7. Updating target features...")
    updated, skipped = 0, 0

    valid_target_fields = [k for k, v in field_map.items() if v is not None]
    target_cursor_fields = ["SHAPE@"] + valid_target_fields

    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(target_path, target_cursor_fields) as cursor:
            for row in cursor:
                coords = (round(row[0].centroid.X, 3), round(row[0].centroid.Y, 3))
                if coords not in source_data:
                    skipped += 1
                    continue

                updated_this_row = False
                for i, (target_field, source_field) in enumerate(field_map.items(), start=1):
                    if source_field is None or target_field not in valid_target_fields:
                        continue  # skip invalid fields

                    val = source_data[coords].get(source_field)
                    if not val:
                        continue
                    normalized = normalize_label(val)
                    domain_val = domain_mapping.get(normalized)
                    if domain_val:
                        row[i] = domain_val
                        updated_this_row = True
                        arcpy.AddMessage(f"7. {target_field} <- '{val}' -> '{domain_val}'")
                    else:
                        arcpy.AddWarning(f"7. No match for {source_field}: '{val}'")

                if updated_this_row:
                    cursor.updateRow(row)
                    updated += 1

"""
    # Fields to map: {target_field: source_field}
    field_map = {
        "RPtType": "sym_name",
        "RPtType2": "RPtType2",
        "RPtType3": "RPtType3"
    }

    arcpy.AddMessage("7. Indexing source features...")
    source_data = {}

    with arcpy.da.SearchCursor(source_path, ["SHAPE@"] + list(field_map.values())) as cursor:
        for row in cursor:
            geom = row[0].projectAs(target_sr)
            coords = (round(geom.centroid.X, 3), round(geom.centroid.Y, 3))
            source_data[coords] = dict(zip(field_map.values(), row[1:]))

    arcpy.AddMessage(f"7. {len(source_data)} source points indexed.")

    arcpy.AddMessage("7. Updating target features...")
    updated, skipped = 0, 0


    with arcpy.da.Editor(workspace):
        with arcpy.da.UpdateCursor(target_path, ["SHAPE@"] + list(field_map.keys())) as cursor:
            for row in cursor:
                coords = (round(row[0].centroid.X, 3), round(row[0].centroid.Y, 3))
                if coords not in source_data:
                    skipped += 1
                    continue

                updated_this_row = False
                for i, (target_field, source_field) in enumerate(field_map.items(), start=1):
                    val = source_data[coords].get(source_field)
                    if not val:
                        continue
                    normalized = normalize_label(val)
                    domain_val = domain_mapping.get(normalized)
                    if domain_val:
                        row[i] = domain_val
                        updated_this_row = True
                        arcpy.AddMessage(f"7. {target_field} <- '{val}' -> '{domain_val}'")
                    else:
                        arcpy.AddWarning(f"7. No match for {source_field}: '{val}'")

                if updated_this_row:
                    cursor.updateRow(row)
                    updated += 1
"""

##################################
##################################

# User provides only the fire number as a parameter
fire_number = arcpy.GetParameterAsText(0)
group_input_layer_name = f"{fire_number}_Input"
pattern = r'^[A-Za-z0-9_]+_BC$'

# We also want the target group and sublayer
group_target_layer_name = f"{fire_number}_Master"
#source_layer_name_pts = "wildfireBC_Rehab_Point"  #"wildfireBC_rehabPoint"

# Get the current project and active map
aprx = arcpy.mp.ArcGISProject("CURRENT")
active_map = aprx.activeMap


# --------------------------------------------------------------------
# 1. Locate the INPUT group layer ("C50903_Input") and gather sublayers
#    that match ^[A-Za-z_]+_BC$ AND have shapeType == "Point".
# --------------------------------------------------------------------
input_group_lyr = None
for lyr in active_map.listLayers():
    if lyr.isGroupLayer and lyr.name == group_input_layer_name:
        input_group_lyr = lyr
        break



# --------------------------------------------------------------------
# 2. POINTS -> get points to copy
# --------------------------------------------------------------------
matched_layers_pts = []
for lyr in input_group_lyr.listLayers():
    if re.match(pattern, lyr.name):
        # Check geometry type to ensure it's a Point layer
        desc = arcpy.Describe(lyr.dataSource)
        if desc.shapeType == "Point":
            matched_layers_pts.append(lyr)
        else:
            arcpy.AddMessage(f"Step 7. Skipping '{lyr.name}' (shapeType = {desc.shapeType}).")



# --------------------------------------------------------------------
# 3. POINTS -> get points to update (TARGET group layer)
# --------------------------------------------------------------------

target_group_lyr = None
for lyr in active_map.listLayers():
    if lyr.isGroupLayer and lyr.name == group_target_layer_name:
        target_group_lyr = lyr
        break



target_lyr = None
source_layer_names_pts = ["wildfireBC_Rehab_Point", "wildfireBC_rehabPoint"]

for lyr in target_group_lyr.listLayers():
    if lyr.name in source_layer_names_pts:
        target_lyr = lyr
        break

if not target_lyr:
    arcpy.AddError(f"Step 7. Could not find point layer in group '{group_target_layer_name}' with any of the names: {source_layer_names_pts}")
    raise RuntimeError("Step 7. Target point layer not found.")


# 7. Copy Domains (Optional)
for pts_layer in matched_layers_pts:
    copy_attributes_with_domains(pts_layer, target_lyr)