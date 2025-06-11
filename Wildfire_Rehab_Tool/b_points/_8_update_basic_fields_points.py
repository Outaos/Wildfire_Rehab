import arcpy
import os

############################
# 8. UPDATE BASIC FIELDS  - POINTS
############################


def update_wildfire_points(target_lyr, fire_number, fire_name, status):
    """
    Updates wildfire rehab point attributes in the provided layer.
    Only fills empty or default values in 'Fire_Num', 'Fire_Name', and 'Status'.
    """

    if not target_lyr.isFeatureLayer:
        arcpy.AddError(f"Step 8. Layer '{target_lyr.name}' is not a feature layer.")
        return

    # Determine workspace path
    conn_props = target_lyr.connectionProperties
    if 'connection_info' in conn_props and 'database' in conn_props['connection_info']:
        workspace = conn_props['connection_info']['database']
        arcpy.AddMessage(f"Step 8. Workspace (SDE): {workspace}")
    else:
        workspace = os.path.dirname(target_lyr.dataSource)
        arcpy.AddMessage(f"Step 8. Workspace (FileGDB): {workspace}")

    if not workspace:
        arcpy.AddError("Step 8. Could not determine the workspace.")
        return

    wildfire_fc = target_lyr.dataSource

    try:
        with arcpy.da.Editor(workspace):
            with arcpy.da.UpdateCursor(wildfire_fc, ["Fire_Num", "Fire_Name", "Status"]) as cursor:
                for row in cursor:
                    # Safely update each field with default values if None or empty
                    if row[0] is None or row[0] == '':
                        row[0] = f"{fire_number}"

                    if row[1] is None or row[1] == '':
                        row[1] = f"{fire_name}"

                    if row[2] is None or row[2] == '' or row[2] == 'RehabRequiresFieldVerification':
                        row[2] = status

                    # Update the row
                    cursor.updateRow(row)


        arcpy.AddMessage("Step 8. Wildfire rehab points updated successfully.")
    except Exception as e:
        arcpy.AddError(f"Step 8. Error during update: {e}")