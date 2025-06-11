import arcpy
import os

#################################################################################
# 10. Update Basic Fields - Lines
#################################################################################

# Main function to update fields in the feature class
def update_wildfire_lines(wildfire_lines, fire_number, fire_name, status):

    """
    Updates wildfire rehab point attributes in the provided layer.
    Only fills empty or default values in 'Fire_Num', 'Fire_Name', and 'Status'.
    """

    if not wildfire_lines.isFeatureLayer:
        arcpy.AddError(f"Step 10. Layer '{wildfire_lines.name}' is not a feature layer.")
        return

    # Determine workspace path
    conn_props = wildfire_lines.connectionProperties
    if 'connection_info' in conn_props and 'database' in conn_props['connection_info']:
        workspace = conn_props['connection_info']['database']
        arcpy.AddMessage(f"Step 10. Workspace (SDE): {workspace}")
    else:
        workspace = os.path.dirname(wildfire_lines.dataSource)
        arcpy.AddMessage(f"Step 10. Workspace (FileGDB): {workspace}")

    if not workspace:
        arcpy.AddError("Step 10. Could not determine the workspace.")
        return

    wildfire_fc_lines = wildfire_lines.dataSource

    try:
        with arcpy.da.Editor(workspace):
            with arcpy.da.UpdateCursor(wildfire_fc_lines, ["Fire_Num", "Fire_Name", "Status"]) as cursor:
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


        arcpy.AddMessage("Step 10. Wildfire rehab points updated successfully.")
    except Exception as e:
        arcpy.AddError(f"Step 10. Error during update: {e}")