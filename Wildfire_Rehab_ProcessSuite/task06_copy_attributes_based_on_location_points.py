"""
Copies attribute values from source points to target points based on identical XY location (rounded to 3 decimals).

The function:
- Validates that both layers are feature layers.
- Determines the workspace from the target layer for editing.
- Dynamically maps fields from the source to the target based on common names.
- Projects source geometries to match the target's spatial reference.
- Matches points by centroid coordinates and copies attribute values via UpdateCursor.

Args:
    source_lyr (arcpy.mp.Layer): The layer containing the data to be copied.
    target_lyr (arcpy.mp.Layer): The layer to which data will be written.

Returns:
    None
"""

import arcpy
import os
import re


def copy_attributes_based_on_location(source_lyr, target_lyr):


    # --- Determine the workspace of the TARGET (like copy_points) ---
    conn_props_update = target_lyr.connectionProperties
    workspace_update = None

    if 'connection_info' in conn_props_update:
        # Probably enterprise GDB (SDE)
        conn_info_update = conn_props_update['connection_info']
        if 'database' in conn_info_update:
            workspace_update = conn_info_update['database']
            arcpy.AddMessage(f"6. Workspace (SDE) from target: {workspace_update}")
    else:
        # Likely a file GDB / shapefile
        workspace_update = os.path.dirname(target_lyr.dataSource)
        arcpy.AddMessage(f"6. Workspace (file GDB/shapefile) from target: {workspace_update}")



    # Data source paths
    target_path = target_lyr.dataSource
    source_path = source_lyr.dataSource

    arcpy.AddMessage(f"6. target_path (update): {target_path}")
    arcpy.AddMessage(f"6. source_path (copy): {source_path}")

    # -----------------------------------------------------------------------
    # Example of "dynamic field mapping" logic from your snippet:
    #    This looks for fields like 'TimeStamp' / 'TimeWhen' => 'CaptureDate', etc.
    # -----------------------------------------------------------------------
    existing_fields = [f.name for f in arcpy.ListFields(source_path)]
    field_mapping = {}

    # Check for "CaptureDate" field
    if "TimeStamp" in existing_fields:
        field_mapping["CaptureDate"] = "TimeStamp"
    elif "TimeWhen" in existing_fields:
        field_mapping["CaptureDate"] = "TimeWhen"

    # Check for "Comments" field
    if "desc" in existing_fields:
        field_mapping["Comments"] = "desc"
    elif "Descr" in existing_fields:
        field_mapping["Comments"] = "Descr"

    # Check for "Label" field
    if "name" in existing_fields:
        field_mapping["Label"] = "name"
    elif "Name" in existing_fields:
        field_mapping["Label"] = "Name"

    # Check for "CritWork" field
    if "CritWork" in existing_fields:
        field_mapping["CritWork"] = "CritWork"

    # Check for "ProtValue" field
    if "ProtValue" in existing_fields:
        field_mapping["ProtValue"] = "ProtValue"



    print(f"6. Field Mapping: {field_mapping}")

    # --- Reproject source geometry to match target’s spatial reference ---
    target_sr = arcpy.Describe(target_path).spatialReference

    # Build a dictionary of { (X, Y): [mapped field values] } from the source
    fields_to_copy = ["SHAPE@"] + list(field_mapping.values())
    source_dict = {}

    with arcpy.da.SearchCursor(source_path, fields_to_copy) as s_cursor:
        for row in s_cursor:
            source_geom = row[0]
            # Project geometry
            projected_geom = source_geom.projectAs(target_sr)

            coords = (round(projected_geom.centroid.X, 3),
                      round(projected_geom.centroid.Y, 3))

            # All attribute values except SHAPE@
            attr_values = row[1:]
            source_dict[coords] = attr_values

    # Now update the target features based on these coords
    fields_to_update = ["SHAPE@"] + list(field_mapping.keys())


    with arcpy.da.Editor(workspace_update):
        with arcpy.da.UpdateCursor(target_path, fields_to_update) as u_cursor:
            for row in u_cursor:
                geom = row[0]
                tgt_coords = (round(geom.centroid.X, 3),
                              round(geom.centroid.Y, 3))

                if tgt_coords in source_dict:
                    source_vals = source_dict[tgt_coords]
                    # Merge source attribute values into row
                    # row[1..] correspond to field_mapping keys
                    row_changed = False
                    for i, val in enumerate(source_vals, start=1):
                        if val is None:
                            continue
                        field_name = fields_to_update[i]  # ignoring SHAPE@
                        # Optional: check field length etc.

                        row[i] = val
                        row_changed = True

                    if row_changed:
                        u_cursor.updateRow(row)


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
            arcpy.AddMessage(f"Step 5. Skipping '{lyr.name}' (shapeType = {desc.shapeType}).")



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
    arcpy.AddError(f"Step 5. Could not find point layer in group '{group_target_layer_name}' with any of the names: {source_layer_names_pts}")
    raise RuntimeError("Step 5. Target point layer not found.")



# 6. Copy Attributes Based on Location
for pts_layer in matched_layers_pts:
    copy_attributes_based_on_location(pts_layer, target_lyr)