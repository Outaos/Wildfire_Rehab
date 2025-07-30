"""
Copies geometry from the feature class (layer object) 'points_to_copy'
into the layer object 'target_lyr'.

- 'points_to_copy' is an arcpy.mp.Layer object discovered in the "{fire_number}_Input" group
    matching the pattern ^[A-Za-z_]+_BC$.
- 'target_lyr' is the arcpy.mp.Layer object for "wildfireBC_rehabPoint" inside "{fire_number}_Master".
- Determines each layer's workspace and starts an edit session in the target's workspace.
- Inserts all geometry from 'points_to_copy' into 'target_lyr'.
"""

import arcpy
import os
import re


# Access the current project and active map
aprx = arcpy.mp.ArcGISProject("CURRENT")
map_obj = aprx.activeMap

def copy_points(points_to_copy, target_lyr):

    if not target_lyr.isFeatureLayer:
        arcpy.AddError(f"Step 5. Target layer '{target_lyr.name}' is not a feature layer. Cannot copy points.")
        return

    if not points_to_copy.isFeatureLayer:
        arcpy.AddError(f"Step 5. Source layer '{points_to_copy.name}' is not a feature layer. Cannot copy points.")
        return

    # --- Determine the workspace of the target (where we need to edit) ---
    conn_props = target_lyr.connectionProperties
    workspace = None

    # Enterprise GDB (SDE) scenario
    if 'connection_info' in conn_props:
        conn_info = conn_props['connection_info']
        if 'database' in conn_info:
            workspace = conn_info['database']
            arcpy.AddMessage(f"Step 5. Workspace (SDE) from target: {workspace}")
        else:
            arcpy.AddError("Step 5. Could not retrieve 'database' from the target layer's connection_info.")
            return
    else:
        # File GDB / Shapefile scenario
        workspace = os.path.dirname(target_lyr.dataSource)
        arcpy.AddMessage(f"Step 5. Workspace (file GDB/shapefile) from target: {workspace}")

    if not workspace:
        arcpy.AddError("Step 5. Failed to determine the workspace for the edit session.")
        return

    # --- Perform the insert in an edit session on the target's workspace ---
    try:
        with arcpy.da.Editor(workspace):
            # Search the source feature class
            with arcpy.da.SearchCursor(points_to_copy, ["SHAPE@"]) as s_cursor:
                # Insert into the target layer
                with arcpy.da.InsertCursor(target_lyr, ["SHAPE@", "Fire_Num"]) as i_cursor:
                    for row in s_cursor:
                        i_cursor.insertRow((row[0], ''))
                        #i_cursor.insertRow(row)

        arcpy.AddMessage(f"Step 5. Successfully copied points from '{points_to_copy.name}' into '{target_lyr.name}'.")
    except Exception as e:
        arcpy.AddError(f"Step 5. Error during editing/copy: {e}")


##################################
##################################

#fire_number = 'G70229'                             # <--------------------------------------!!!
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


#target_lyr = None
#for lyr in target_group_lyr.listLayers():
#    if lyr.name == source_layer_name_pts:
#        target_lyr = lyr
#        break

target_lyr = None
source_layer_names_pts = ["wildfireBC_Rehab_Point", "wildfireBC_rehabPoint"]

for lyr in target_group_lyr.listLayers():
    if lyr.name in source_layer_names_pts:
        target_lyr = lyr
        break

if not target_lyr:
    arcpy.AddError(f"Step 5. Could not find point layer in group '{group_target_layer_name}' with any of the names: {source_layer_names_pts}")
    raise RuntimeError("Step 5. Target point layer not found.")



# --------------------------------------------------------------------
# 5. For each matched input layer, copy its features into the target layer.
# --------------------------------------------------------------------
for pts_layer in matched_layers_pts:
    copy_points(pts_layer, target_lyr)




