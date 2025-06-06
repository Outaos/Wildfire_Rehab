# 7. COPY ATTRIBUTES BASED ON LOCATION 

import arcpy 
import os
import re

# Function to copy attributes based on spatial location
def copy_attributes_based_on_location(fc_to_copy, fc_to_update):
    arcpy.AddMessage("🔄 Starting attribute copy process...")
    print("🔄 Starting attribute copy process...")
    # Access the current project and active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap

    # Try to get the layer objects for fc_to_update and fc_to_copy
    layer_update = None
    layer_copy = None
    for lyr in map_obj.listLayers():
        if lyr.name == fc_to_update or lyr.longName == fc_to_update:
            layer_update = lyr
        if lyr.name == fc_to_copy or lyr.longName == fc_to_copy:
            layer_copy = lyr

    if layer_update is None:
        arcpy.AddError(f"Layer '{fc_to_update}' not found in the current map.")
        return
    if layer_copy is None:
        arcpy.AddError(f"Layer '{fc_to_copy}' not found in the current map.")
        return

    # Get the workspace from the layer's connection properties for fc_to_update
    conn_props_update = layer_update.connectionProperties

    # Initialize workspace variable
    workspace_update = None

    if 'connection_info' in conn_props_update:
        conn_info_update = conn_props_update['connection_info']
        if 'database' in conn_info_update:
            workspace_update = conn_info_update['database']
            arcpy.AddMessage(f"Workspace from connection_info (fc_to_update): {workspace_update}")
            print(f"🗂 Workspace: {workspace_update}")
        else:
            arcpy.AddError("Could not retrieve 'database' from connection_info for fc_to_update.")
            return
    else:
        # For file geodatabases or shapefiles, use the data source path
        workspace_update = os.path.dirname(layer_update.dataSource)
        arcpy.AddMessage(f"Workspace from dataSource (fc_to_update): {workspace_update}")

    # Ensure workspace was obtained
    if not workspace_update:
        arcpy.AddError("Failed to determine the workspace for fc_to_update.")
        return

    # Get data source paths
    fc_to_update_path = layer_update.dataSource
    fc_to_copy_path = layer_copy.dataSource
    arcpy.AddMessage(f"📍 fc_to_update_path: {fc_to_update_path}")
    arcpy.AddMessage(f"📍 fc_to_copy_path: {fc_to_copy_path}")
    print(f"📍 fc_to_update_path: {fc_to_update_path}")
    print(f"📍 fc_to_copy_path: {fc_to_copy_path}")

    # For debugging, output the data source paths
    arcpy.AddMessage(f"fc_to_update_path: {fc_to_update_path}")
    arcpy.AddMessage(f"fc_to_copy_path: {fc_to_copy_path}")

    ###############################################################################
    # Dynamically define the field mapping between fc_to_update and fc_to_copy
    # Get the list of existing fields in fc_to_copy
    existing_fields = [f.name for f in arcpy.ListFields(fc_to_copy_path)]
    arcpy.AddMessage(f"🔍 Fields in source: {existing_fields}")
    print(f"🔍 Fields in source: {existing_fields}")

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



    # If no matching fields are found, inform the user and exit
    if not field_mapping:
        arcpy.AddError("No matching fields found between the feature classes.")
        print("No matching fields found between the feature classes.")
        return

    # For debugging, output the field mapping
    arcpy.AddMessage(f"Field Mapping: {field_mapping}")
    print(f"🧭 Field Mapping: {field_mapping}")
    ###############################################################################

    # Get the spatial reference of fc_to_update
    spatial_ref_fc_to_update = arcpy.Describe(fc_to_update_path).spatialReference

    # Get the fields for the cursors
    fields_to_update = ["SHAPE@"] + list(field_mapping.keys())
    fields_to_copy = ["SHAPE@"] + list(field_mapping.values())

    # Create a dictionary to store the coordinates and field values from fc_to_copy
    field_to_copy_dict = {}

    # Populate the dictionary with points from fc_to_copy
    with arcpy.da.SearchCursor(fc_to_copy_path, fields_to_copy) as cursor:
        for row in cursor:
            # Project the geometry to match fc_to_update
            projected_point = row[0].projectAs(spatial_ref_fc_to_update)
            coords = (round(projected_point.centroid.X, 3), round(projected_point.centroid.Y, 3))
            # Store the corresponding field values
            field_values = row[1:]  # All fields except SHAPE@
            field_to_copy_dict[coords] = field_values

    arcpy.AddMessage(f"📌 {len(field_to_copy_dict)} source features indexed by coordinates.")
    print(f"📌 {len(field_to_copy_dict)} source features indexed by coordinates.")
    
    # Initialize a list to keep track of skipped rows
    skipped_rows = []
    updated_count = 0
    unmatched_count = 0

    # Now, update fc_to_update based on the matching coordinates within an edit session
    try:
        with arcpy.da.Editor(workspace_update) as edit:
            with arcpy.da.UpdateCursor(fc_to_update_path, fields_to_update) as cursor:
                for row in cursor:
                    coords = (round(row[0].centroid.X, 3), round(row[0].centroid.Y, 3))
                    if coords in field_to_copy_dict:
                        values_to_assign = field_to_copy_dict[coords]
                        row_changed = False
                        for i, value in enumerate(values_to_assign):
                            field_name = fields_to_update[i + 1]  # Skip SHAPE@
                            # Check if the value exceeds field length
                            field_length = [f.length for f in arcpy.ListFields(fc_to_update_path, field_name) if f.name == field_name][0]
                            if isinstance(value, str) and len(value) > field_length:
                                arcpy.AddWarning(f"Skipping row at {coords} due to '{field_name}' field length exceeded.")
                                print(f"⚠️ Skipping field '{field_name}' at {coords}: value too long.")
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

        arcpy.AddMessage(f"✅ {updated_count} features updated.")
        arcpy.AddMessage(f"❌ {unmatched_count} features not matched by coordinates.")
        print(f"✅ {updated_count} features updated.")
        print(f"❌ {unmatched_count} features not matched by coordinates.")
        
        # After processing, report skipped rows
        if skipped_rows:
            arcpy.AddWarning("\nSkipped rows due to field length exceeded:")
            print("\n⚠️ Skipped rows due to field length exceeded:")
            for coords, field_name, value in skipped_rows:
                arcpy.AddWarning(f"Coordinates: {coords}, Field: {field_name}, Value: {value}")
                print(f"Coordinates: {coords}, Field: {field_name}, Value: {value}")

        arcpy.AddMessage("\nField values copied from fc_to_copy to fc_to_update based on matching point locations.")
        print("\nField values copied from fc_to_copy to fc_to_update based on matching point locations.")

    except Exception as e:
        arcpy.AddError(f"An error occurred during the edit session: {e}")
        print(f"💥 An error occurred: {e}")
        return

# User inputs from ArcGIS Pro tool
fc_to_copy = arcpy.GetParameterAsText(0)  
fc_to_update = arcpy.GetParameterAsText(1)  
 

# Run the function with the provided parameters
copy_attributes_based_on_location(fc_to_copy, fc_to_update)
