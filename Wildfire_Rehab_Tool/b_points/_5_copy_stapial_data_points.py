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


############################
# 5. COPY STAPIAL DATA POINTS
############################


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