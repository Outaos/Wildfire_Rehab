import arcpy
import os


#################################################################################
# 11. Copy Attributes Based On Location - Lines
#################################################################################


# Function to copy attributes based on spatial location
def copy_attributes_based_on_location_lines(lines_to_copy, wildfire_lines):
    """
    Copies attributes from 'lines_to_copy' into 'wildfire_lines' based on matching line endpoints.
    """
    arcpy.AddMessage(" Starting attribute copy process...")
    print(" Starting attribute copy process...")
    # Access the current project and active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap


    # Get the workspace from the layer's connection properties for wildfire_lines
    conn_props_update = wildfire_lines.connectionProperties

    # Initialize workspace variable
    workspace_update = None

    if 'connection_info' in conn_props_update:
        conn_info_update = conn_props_update['connection_info']
        if 'database' in conn_info_update:
            workspace_update = conn_info_update['database']
            arcpy.AddMessage(f"Workspace from connection_info (wildfire_lines): {workspace_update}")
            print(f" Workspace: {workspace_update}")
        else:
            arcpy.AddError("Could not retrieve 'database' from connection_info for wildfire_lines.")
            return
    else:
        # For file geodatabases or shapefiles, use the data source path
        workspace_update = os.path.dirname(wildfire_lines.dataSource)
        arcpy.AddMessage(f"Workspace from dataSource (wildfire_lines): {workspace_update}")

    # Ensure workspace was obtained
    if not workspace_update:
        arcpy.AddError("Failed to determine the workspace for wildfire_lines.")
        return

    # Get data source paths
    wildfire_lines_path = wildfire_lines.dataSource
    lines_to_copy_path = lines_to_copy.dataSource
    arcpy.AddMessage(f" wildfire_lines_path: {wildfire_lines_path}")
    arcpy.AddMessage(f" lines_to_copy_path: {lines_to_copy_path}")
    print(f" wildfire_lines_path: {wildfire_lines_path}")
    print(f" lines_to_copy_path: {lines_to_copy_path}")

    # For debugging, output the data source paths
    arcpy.AddMessage(f"wildfire_lines_path: {wildfire_lines_path}")
    arcpy.AddMessage(f"lines_to_copy_path: {lines_to_copy_path}")

    ###############################################################################
    # Dynamically define the field mapping between wildfire_lines and lines_to_copy
    # Get the list of existing fields in lines_to_copy
    existing_fields = [f.name for f in arcpy.ListFields(lines_to_copy_path)]
    arcpy.AddMessage(f" Fields in source: {existing_fields}")
    print(f" Fields in source: {existing_fields}")

    # Initialize field mapping
    field_mapping = {}

    # Check for "CaptureDate" field
    if "TimeStamp" in existing_fields:
        field_mapping["CaptureDate"] = "TimeStamp"
    elif "TimeWhen" in existing_fields:
        field_mapping["CaptureDate"] = "TimeWhen"

    # Check for "Comments" field
    if "desc" in existing_fields:
        field_mapping["Description"] = "desc"
    elif "desc" in existing_fields:
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

    # Check for "CritWork" field
    if "LineWidth" in existing_fields:
        field_mapping["LineWidth"] = "LineWidth"

    # Check for "ProtValue" field
    if "AvgSlope" in existing_fields:
        field_mapping["AvgSlope"] = "AvgSlope"

    

    # If no matching fields are found, inform the user and exit
    if not field_mapping:
        arcpy.AddError("No matching fields found between the feature classes.")
        print("No matching fields found between the feature classes.")
        return

    # For debugging, output the field mapping
    arcpy.AddMessage(f"Field Mapping: {field_mapping}")
    print(f" Field Mapping: {field_mapping}")
    ###############################################################################

    # Get the spatial reference of wildfire_lines
    spatial_ref_wildfire_lines = arcpy.Describe(wildfire_lines_path).spatialReference

    # Get the fields for the cursors
    fields_to_update = ["SHAPE@"] + list(field_mapping.keys())
    fields_to_copy = ["SHAPE@"] + list(field_mapping.values())

    # Create a dictionary to store the coordinates and field values from lines_to_copy
    field_to_copy_dict = {}

    # Populate the dictionary with points from lines_to_copy
    with arcpy.da.SearchCursor(lines_to_copy_path, fields_to_copy) as cursor:
        for row in cursor:
            # Project the geometry to match wildfire_lines
            #projected_point = row[0].projectAs(spatial_ref_wildfire_lines)
            #coords = (round(projected_point.centroid.X, 3), round(projected_point.centroid.Y, 3))
            projected_line = row[0].projectAs(spatial_ref_wildfire_lines)
            first_vertex = (round(projected_line.firstPoint.X, 3), round(projected_line.firstPoint.Y, 3))
            last_vertex = (round(projected_line.lastPoint.X, 3), round(projected_line.lastPoint.Y, 3))
            coords = (first_vertex, last_vertex)
            # Store the corresponding field values
            field_values = row[1:]  # All fields except SHAPE@
            field_to_copy_dict[coords] = field_values

    arcpy.AddMessage(f" {len(field_to_copy_dict)} source features indexed by coordinates.")
    print(f" {len(field_to_copy_dict)} source features indexed by coordinates.")
    
    # Initialize a list to keep track of skipped rows
    skipped_rows = []
    updated_count = 0
    unmatched_count = 0

    # Now, update wildfire_lines based on the matching coordinates within an edit session
    try:
        with arcpy.da.Editor(workspace_update) as edit:
            with arcpy.da.UpdateCursor(wildfire_lines_path, fields_to_update) as cursor:
                for row in cursor:
                    #coords = (round(row[0].centroid.X, 3), round(row[0].centroid.Y, 3))
                    first_vertex = (round(row[0].firstPoint.X, 3), round(row[0].firstPoint.Y, 3))
                    last_vertex = (round(row[0].lastPoint.X, 3), round(row[0].lastPoint.Y, 3))
                    coords = (first_vertex, last_vertex)
                    if coords in field_to_copy_dict:
                        values_to_assign = field_to_copy_dict[coords]
                        row_changed = False
                        for i, value in enumerate(values_to_assign):
                            field_name = fields_to_update[i + 1]  # Skip SHAPE@
                            # Check if the value exceeds field length
                            field_length = [f.length for f in arcpy.ListFields(wildfire_lines_path, field_name) if f.name == field_name][0]
                            if isinstance(value, str) and len(value) > field_length:
                                arcpy.AddWarning(f"Skipping row at {coords} due to '{field_name}' field length exceeded.")
                                print(f" Skipping field '{field_name}' at {coords}: value too long.")
                                skipped_rows.append((coords, field_name, value))
                                continue
                            else:
                                row[i + 1] = value  # Assign the value to the row
                                row_changed = True
                        if row_changed:
                            cursor.updateRow(row)
                            updated_count += 1
                    else:
                        unmatched_count += 1

        arcpy.AddMessage(f" {updated_count} features updated.")
        arcpy.AddMessage(f" {unmatched_count} features not matched by coordinates.")
        print(f" {updated_count} features updated.")
        print(f" {unmatched_count} features not matched by coordinates.")
        
        # After processing, report skipped rows
        if skipped_rows:
            arcpy.AddWarning("\nSkipped rows due to field length exceeded:")
            print("\n Skipped rows due to field length exceeded:")
            for coords, field_name, value in skipped_rows:
                arcpy.AddWarning(f"Coordinates: {coords}, Field: {field_name}, Value: {value}")
                print(f"Coordinates: {coords}, Field: {field_name}, Value: {value}")

        arcpy.AddMessage("\nField values copied from lines_to_copy to wildfire_lines based on matching line vertices.")
        print("\nField values copied from lines_to_copy to wildfire_lines based on matching line vertices.")

    except Exception as e:
        arcpy.AddError(f"An error occurred during the edit session: {e}")
        print(f" An error occurred: {e}")
        return