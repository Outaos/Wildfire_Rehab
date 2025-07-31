import arcpy
import os


# Main function to update fields in the feature class
def update_wildfire_points(fire_number, fire_name, status):
    # Access the current project and active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap

    # Build the expected layer name based on the fire number
    # Set the expected group layer name (e.g., "C50987_Original")
    group_layer_name = f"{fire_number}_Master"

    # List of possible layer names under the group
    possible_names = ["wildfireBC_rehabPoint", "wildfireBC_Rehab_Point"]

    # Try to find the group layer
    group_layer = None
    for lyr in map_obj.listLayers():
        if lyr.name == group_layer_name and lyr.isGroupLayer:
            group_layer = lyr
            break

    if not group_layer:
        arcpy.AddError(f"Group layer '{group_layer_name}' not found in the current map.")
        return

    # Now search for the expected feature class inside the group
    layer = None
    for name in possible_names:
        for sub_lyr in group_layer.listLayers():
            if sub_lyr.name.lower() == name.lower():
                layer = sub_lyr
                break
        if layer:
            break

    if not layer:
        arcpy.AddError(f"Feature class not found under group layer '{group_layer_name}'.")

    # Get the workspace from the layer's connection properties
    conn_props = layer.connectionProperties

    # For debugging, output the connection properties
    arcpy.AddMessage(f"Connection Properties: {conn_props}")

    # Initialize workspace variable
    workspace = None

    if 'connection_info' in conn_props:
        conn_info = conn_props['connection_info']
        if 'database' in conn_info:
            workspace = conn_info['database']
            arcpy.AddMessage(f"Workspace from connection_info: {workspace}")
        else:
            arcpy.AddError("Could not retrieve 'database' from connection_info.")
            return
    else:
        # For file geodatabases or shapefiles, use the data source path
        workspace = os.path.dirname(layer.dataSource)
        arcpy.AddMessage(f"Workspace from dataSource: {workspace}")

    # Ensure workspace was obtained
    if not workspace:
        arcpy.AddError("Failed to determine the workspace.")
        return

    # Get the full path to the feature class
    wildfire_points = layer.dataSource

    # For debugging, output the feature class path
    arcpy.AddMessage(f"Feature Class Path: {wildfire_points}")


    # Start an edit session
    try:
        with arcpy.da.Editor(workspace) as edit:
            # Use an UpdateCursor to iterate through the rows and update the fields
            with arcpy.da.UpdateCursor(wildfire_points, ["Fire_Num", "Fire_Name", "Status"]) as cursor:
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

        arcpy.AddMessage("Field update process completed.")

    except Exception as e:
        arcpy.AddError(f"An error occurred during the edit session: {e}")
        return




# User inputs from ArcGIS Pro tool
fire_number = arcpy.GetParameterAsText(0)  # Fire number for dynamic naming
fire_name = arcpy.GetParameterAsText(1)    # Fire name
status = arcpy.GetParameterAsText(2)       # Status (should be text)



'''
Current
RehabCompleted
RehabFieldVerified
RehabObligationsTransferred
RehabPFR/ArchCompleted
RehabRequiresFieldVerification
Retired
'''

# Run the function with the provided parameters
update_wildfire_points(fire_number, fire_name, status)
