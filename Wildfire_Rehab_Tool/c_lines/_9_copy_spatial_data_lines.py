import arcpy
import os

#################################################################################
# 9. Copy Spatial Data - Lines
#################################################################################

####################################################################
# Function to copy lines from one feature class to another
def copy_lines(lines_to_copy, wildfire_lines):

    """
    Copies geometry from the feature class 'lines_to_copy'
    into the layer object 'wildfire_lines'.
    """

    if not wildfire_lines.isFeatureLayer:
        arcpy.AddError(f"Step 9. Target layer '{wildfire_lines.name}' is not a feature layer. Cannot copy points.")
        return

    if not lines_to_copy.isFeatureLayer:
        arcpy.AddError(f"Step 9. Source layer '{lines_to_copy.name}' is not a feature layer. Cannot copy points.")
        return

    # --- Determine the workspace of the target (where we need to edit) ---
    conn_props = wildfire_lines.connectionProperties
    workspace = None

    # Enterprise GDB (SDE) scenario
    if 'connection_info' in conn_props:
        conn_info = conn_props['connection_info']
        if 'database' in conn_info:
            workspace = conn_info['database']
            arcpy.AddMessage(f"Step 9. Workspace (SDE) from target: {workspace}")
        else:
            arcpy.AddError("Step 9. Could not retrieve 'database' from the target layer's connection_info.")
            return
    else:
        # File GDB / Shapefile scenario
        workspace = os.path.dirname(wildfire_lines.dataSource)
        arcpy.AddMessage(f"Step 9. Workspace (file GDB/shapefile) from target: {workspace}")

    if not workspace:
        arcpy.AddError("Step 9. Failed to determine the workspace for the edit session.")
        return

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

        arcpy.AddMessage(f"Step 9. Successfully copied {count} lines from '{lines_to_copy.name}' into '{wildfire_lines.name}'.")
    except Exception as e:
        arcpy.AddError(f"Step 9. Error during editing/copy: {e}")
