"""
Copies attribute values from source points to target points based on identical XY location (rounded to 3 decimals).

The function:
- Validates that both layers are feature layers.
- Determines the workspace from the target layer for editing.
- Dynamically maps fields from the source to the target based on common names.
- Projects source geometries to match the target's spatial reference.
- Matches points by centroid coordinates and copies attribute values via UpdateCursor.

Args:
    source_lyr (arcpy.mp.Layer): The layer containing the data to be copied.
    target_lyr (arcpy.mp.Layer): The layer to which data will be written.

Returns:
    None
"""

import arcpy
import os


############################
# 6. COPY ATTRIBUTES BASED ON LOCATION
############################


def copy_attributes_based_on_location(source_lyr, target_lyr):

    # Both must be feature layers
    if not target_lyr.isFeatureLayer:
        arcpy.AddError(f"Step 6. Target layer '{target_lyr.name}' is not a feature layer. Cannot copy attributes.")
        return

    if not source_lyr.isFeatureLayer:
        arcpy.AddError(f"Step 6. Source layer '{source_lyr.name}' is not a feature layer. Cannot copy attributes.")
        return

    # --- Determine the workspace of the TARGET (like copy_points) ---
    conn_props_update = target_lyr.connectionProperties
    workspace_update = None

    if 'connection_info' in conn_props_update:
        # Probably enterprise GDB (SDE)
        conn_info_update = conn_props_update['connection_info']
        if 'database' in conn_info_update:
            workspace_update = conn_info_update['database']
            arcpy.AddMessage(f"Step 6. Workspace (SDE) from target: {workspace_update}")
        else:
            arcpy.AddError("Step 6. Could not retrieve 'database' from target layer's connection_info.")
            return
    else:
        # Likely a file GDB / shapefile
        workspace_update = os.path.dirname(target_lyr.dataSource)
        arcpy.AddMessage(f"Step 6. Workspace (file GDB/shapefile) from target: {workspace_update}")

    if not workspace_update:
        arcpy.AddError("Step 6. Failed to determine the workspace for the edit session.")
        return

    # Data source paths
    target_path = target_lyr.dataSource
    source_path = source_lyr.dataSource

    arcpy.AddMessage(f"Step 6. target_path (update): {target_path}")
    arcpy.AddMessage(f"Step 6. source_path (copy): {source_path}")

    # -----------------------------------------------------------------------
    # Example of "dynamic field mapping" logic from your snippet:
    #    This looks for fields like 'TimeStamp' / 'TimeWhen' => 'CaptureDate', etc.
    # -----------------------------------------------------------------------
    existing_fields = [f.name for f in arcpy.ListFields(source_path)]
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



    if not field_mapping:
        arcpy.AddError("Step 6. No matching fields found between the feature classes.")
        return

    arcpy.AddMessage(f"Step 6. Field Mapping: {field_mapping}")

    # --- Reproject source geometry to match target’s spatial reference ---
    target_sr = arcpy.Describe(target_path).spatialReference

    # Build a dictionary of { (X, Y): [mapped field values] } from the source
    fields_to_copy = ["SHAPE@"] + list(field_mapping.values())
    source_dict = {}

    with arcpy.da.SearchCursor(source_path, fields_to_copy) as s_cursor:
        for row in s_cursor:
            source_geom = row[0]
            # Project geometry
            projected_geom = source_geom.projectAs(target_sr)

            coords = (round(projected_geom.centroid.X, 3),
                      round(projected_geom.centroid.Y, 3))

            # All attribute values except SHAPE@
            attr_values = row[1:]
            source_dict[coords] = attr_values

    # Now update the target features based on these coords
    fields_to_update = ["SHAPE@"] + list(field_mapping.keys())

    try:
        with arcpy.da.Editor(workspace_update):
            with arcpy.da.UpdateCursor(target_path, fields_to_update) as u_cursor:
                for row in u_cursor:
                    geom = row[0]
                    tgt_coords = (round(geom.centroid.X, 3),
                                  round(geom.centroid.Y, 3))

                    if tgt_coords in source_dict:
                        source_vals = source_dict[tgt_coords]
                        # Merge source attribute values into row
                        # row[1..] correspond to field_mapping keys
                        row_changed = False
                        for i, val in enumerate(source_vals, start=1):
                            if val is None:
                                continue
                            field_name = fields_to_update[i]  # ignoring SHAPE@
                            # Optional: check field length etc.

                            row[i] = val
                            row_changed = True

                        if row_changed:
                            u_cursor.updateRow(row)

        arcpy.AddMessage("Step 6. Field values copied successfully based on matching point locations.")
    except Exception as e:
        arcpy.AddError(f"Step 6. Error during the edit session: {e}")
        return