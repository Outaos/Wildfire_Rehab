import arcpy
import re
import os

# Function to copy lines from one feature class to another
def copy_lines(lines_to_copy, wildfire_lines):

    # --- Determine the workspace of the target (where we need to edit) ---
    conn_props = wildfire_lines.connectionProperties
    workspace = None

    # Enterprise GDB (SDE) scenario
    if 'connection_info' in conn_props:
        conn_info = conn_props['connection_info']
        if 'database' in conn_info:
            workspace = conn_info['database']
            print(f"Step 5. Workspace (SDE) from target: {workspace}")
    else:
        # File GDB / Shapefile scenario
        workspace = os.path.dirname(wildfire_lines.dataSource)
        print(f"Step 9. Workspace (file GDB/shapefile) from target: {workspace}")

    if not workspace:
        print("Step 9. Failed to determine the workspace for the edit session.")

    try:
        count = 0
        with arcpy.da.Editor(workspace):
            # Search the source feature class
            with arcpy.da.SearchCursor(lines_to_copy, ["SHAPE@"]) as s_cursor:
                # Insert into the target layer
                with arcpy.da.InsertCursor(wildfire_lines, ["SHAPE@", "Fire_Num"]) as insert_cursor:
                    for row in s_cursor:
                        insert_cursor.insertRow((row[0], ''))
                        #i_cursor.insertRow(row)
                        count += 1

        print(f"Step 9. Successfully copied {count} lines from '{lines_to_copy.name}' into '{wildfire_lines.name}'.")
    except Exception as e:
        print(f"Step 9. Error during editing/copy: {e}")




# --------------------------------------------------------------------------------------------------------------------------------------
# Finds matching lines 
# --------------------------------------------------------------------
# --------------------------------------------------------------------
# LOCATE AND RETRIVE POINTS AND LINES TO COPY AND POINTS AND LINES TO UPDATE
# --------------------------------------------------------------------
"""
1. Find the input group layer named '{fire_number}_Input'.
   - For each sublayer matching pattern ^[A-Za-z_]+_BC$ AND geometry == Point, gather them as 'points_to_copy'.
2. Find the target group layer '{fire_number}_Master' -> sublayer 'wildfireBC_rehabPoint'.
3. For EACH matched 'points_to_copy' layer, call copy_points(points_to_copy, target_lyr).
"""

fire_number = arcpy.GetParameterAsText(0)
group_input_layer_name = f"{fire_number}_Input"
pattern = r'^[A-Za-z0-9_]+_BC$'

# We also want the target group and sublayer
group_target_layer_name = f"{fire_number}_Master"
#source_layer_name_lines = "wildfireBC_Rehab_Line"

# Get the current project and active map
aprx = arcpy.mp.ArcGISProject("CURRENT")
active_map = aprx.activeMap

if not active_map:
   print("No active map found. Open a map in ArcGIS Pro before running.")
    

# --------------------------------------------------------------------
# 1. Locate the INPUT group layer ("C50903_Input") and gather sublayers
#    that match ^[A-Za-z_]+_BC$ AND have shapeType == "Point".
# --------------------------------------------------------------------
input_group_lyr = None
for lyr in active_map.listLayers():
    if lyr.isGroupLayer and lyr.name == group_input_layer_name:
        input_group_lyr = lyr
        break

if not input_group_lyr:
    print(f"Group layer '{group_input_layer_name}' (Input) not found.")
    

# 4. LINES -> get lines to copy
# --------------------------------------------------------------------
matched_layers_lines = []
for lyr in input_group_lyr.listLayers():
    if re.match(pattern, lyr.name):
        # Check geometry type to ensure it's a Point layer
        desc = arcpy.Describe(lyr.dataSource)
        if desc.shapeType == "Polyline":    # 'Line'
            matched_layers_lines.append(lyr)
        else:
            print(f"Skipping '{lyr.name}' (shapeType = {desc.shapeType}).")

if not matched_layers_lines:
    print(
        f"No line sublayers in '{group_input_layer_name}' match pattern '{pattern}'."
    )
    
else:
    print(
        f"Found {len(matched_layers_lines)} line layer(s) matching '{pattern}' in '{group_input_layer_name}'."
    )

# --------------------------------------------------------------------
# 5. LINES -> get lines to update (TARGET group layer)
# --------------------------------------------------------------------

target_group_lyr = None
for lyr in active_map.listLayers():
    if lyr.isGroupLayer and lyr.name == group_target_layer_name:
        target_group_lyr = lyr
        break






target_lyr = None
source_layer_names_line = ["wildfireBC_Rehab_Line", "wildfireBC_rehabLine"]

for lyr in target_group_lyr.listLayers():
    if lyr.name in source_layer_names_line:
        target_lyr = lyr
        break

if not target_lyr:
    arcpy.AddError(f"Step 5. Could not find point layer in group '{group_target_layer_name}' with any of the names: {source_layer_names_line}")
    raise RuntimeError("Step 5. Target point layer not found.")



# --------------------------------------------------------------------
# 5. For each matched input layer, copy its features into the target layer.
# --------------------------------------------------------------------
for line_layer in matched_layers_lines:
    copy_lines(line_layer, target_lyr)