import arcpy
import os

def copy_points(points_to_copy, wildfire_points):
    # Access the current project and active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap

    # Try to get the layer object for wildfire_points
    layer = None
    for lyr in map_obj.listLayers():
        if lyr.name == wildfire_points or lyr.longName == wildfire_points:
            layer = lyr
            break

    if layer is None:
        arcpy.AddError(f"Layer '{wildfire_points}' not found in the current map.")
        return

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

    # Start an edit session
    try:
        with arcpy.da.Editor(workspace) as edit:
            # Create a search cursor to iterate over the points in points_to_copy
            with arcpy.da.SearchCursor(points_to_copy, ["SHAPE@"]) as cursor:
                # Create an insert cursor to add points to wildfire_points
                with arcpy.da.InsertCursor(wildfire_points, ["SHAPE@", "Fire_Num"]) as insert_cursor:
                    for row in cursor:
                        insert_cursor.insertRow((row[0], ''))
                        #insert_cursor.insertRow(row)

        arcpy.AddMessage("New points created in wildfire_points at the selected locations.")

    except Exception as e:
        arcpy.AddError(f"An error occurred during the edit session: {e}")

# Parameters from ArcGIS Pro tool
points_to_copy = arcpy.GetParameterAsText(0)
wildfire_points = arcpy.GetParameterAsText(1)

# Run the function with the provided parameters
copy_points(points_to_copy, wildfire_points)
