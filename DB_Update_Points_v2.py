
import arcpy
import os
import re


############################
# 1. BACKUP GDB
############################
def backup_gdb(fire_year, fire_number, backup_output_folder):
    # Derive fire_code from fire_number
    fire_code = fire_number[:2]  # Take the first two characters of fire_number
    # Define input and output paths
    #input_gdb = fr"W:\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\Cariboo\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"   # F
    input_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\Cariboo\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    output_gdb = os.path.join(backup_output_folder, f"{fire_number}_Rehab_BU.gdb")

    # Create output directory if it doesn't exist
    if not os.path.exists(backup_output_folder):
        os.makedirs(backup_output_folder)

    # Perform the copy operation
    arcpy.Copy_management(input_gdb, output_gdb)

    print("1. Backup completed successfully.")

############################

############################
############################
# 2. IMPORT AND GROUP LAYERS
############################

# Define a function
def add_layers_to_group(fire_year, fire_number):
    # Set the Project and Map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap


    # Derive fire_code from fire_number
    fire_code = fire_number[:2]  

    # Define the path to the GeoDatabase  and feature dataset
    #if fire_year == '2021':
    #    gdb_path = fr"Y:\FireSeasonWork\{fire_year}\Cariboo\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    #else:
    #gdb_path = fr"W:\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\Cariboo\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"   # F
    gdb_path = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\Cariboo\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"

    feature_dataset = "wildfireBC_Rehab"


    # Check if the GeoDatabase exists:
    if not arcpy.Exists(gdb_path):
        arcpy.AddError(f"The GeoDatabase '{gdb_path}' does not exist.")
        return
    
    # Define the feature classes
    fc_points = os.path.join(gdb_path, feature_dataset, "wildfireBC_Rehab_Point")
    fc_lines = os.path.join(gdb_path, feature_dataset, "wildfireBC_Rehab_Line")

    # Check if the feature classes exist:
    if not arcpy.Exists(fc_points):
        arcpy.AddError(f"The feature class '{fc_points}' does not exist.")
        return
    if not arcpy.Exists(fc_lines):
        arcpy.AddError(f"The feature class '{fc_lines}' does not exist.")
        return
    
    # Define the names of the layers to be grouped
    layer_names_to_group = ["wildfireBC_Rehab_Point", "wildfireBC_Rehab_Line"]

    # Check if the group layer already exists
    group_layer_name = f"{fire_number}_Original"
    group_layer_exists = any(lyr.name == group_layer_name for lyr in map_obj.listLayers() if lyr.isGroupLayer)

    # If the group layer does not exist, create it and add layers
    if not group_layer_exists:
        # Create a new group layer
        group_layer = map_obj.createGroupLayer(group_layer_name)

        # Function to add layers to the group
        def add_layer_to_group(fc_path, layer_name, group_layer):
            # Check if the layer is already in the group layer
            if not any(lyr.name == layer_name for lyr in group_layer.listLayers()):
                # Add the layer from the path to the map
                new_layer = map_obj.addDataFromPath(fc_path)
                # Add layer to the group
                map_obj.addLayerToGroup(group_layer, new_layer, "BOTTOM")
                # Remove the original layer from the map
                map_obj.removeLayer(new_layer)

        # Execute the Group Function
        # Add the point and line feature classes directly to the group layer
        add_layer_to_group(fc_points, "wildfireBC_Rehab_Point", group_layer)
        add_layer_to_group(fc_lines, "wildfireBC_Rehab_Line", group_layer)

        # Save the project
        aprx.save()

        arcpy.AddMessage(f"2. Layers added directly to '{group_layer_name}' group, standalone layers avoided.")
    else:
        arcpy.AddWarning(f"'2. {group_layer_name}' group already exists. No layers were added.\nPlease update: 'FIRE_NUMBER'")

    return fc_points


############################
# 3. IMPORT COLLECTED DATA
############################
def add_shapefiles_to_group(fire_number, collected_data_folder):
    # Check if the input folder exists
    if not os.path.exists(collected_data_folder):
        arcpy.AddError(f"3. The input folder '{collected_data_folder}' does not exist.")
        return

    # Access the current project and active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap

    # Create a new group layer for the shapefiles
    group_layer_name = f"{fire_number}_Input"
    group_layer_exists = any(
        lyr.name == group_layer_name for lyr in map_obj.listLayers() if lyr.isGroupLayer
    )

    if not group_layer_exists:
        group_layer = map_obj.createGroupLayer(group_layer_name)
    else:
        # If the group layer exists, get it
        group_layer = next(
            lyr for lyr in map_obj.listLayers() if lyr.isGroupLayer and lyr.name == group_layer_name
        )

    # Function to add layers directly to the group if they are not already present
    def add_layer_to_group(shapefile_path, group_layer):
        shapefile_name = os.path.basename(shapefile_path)
        layer_name = os.path.splitext(shapefile_name)[0]  # Remove the .shp extension

        # Check if the layer is already in the group
        if not any(lyr.name == layer_name for lyr in group_layer.listLayers()):
            # Add the layer from the path to the map
            new_layer = map_obj.addDataFromPath(shapefile_path)
            # Add the layer to the group layer
            map_obj.addLayerToGroup(group_layer, new_layer)
            # Remove the original layer from the map
            map_obj.removeLayer(new_layer)
            arcpy.AddMessage(f"Added shapefile: {shapefile_name}")
        else:
            arcpy.AddMessage(f"Layer '{layer_name}' already exists in the group layer.")

    # Loop through all shapefiles in the input folder
    shapefiles_added = False
    for file in os.listdir(collected_data_folder):
        if file.lower().endswith(".shp"):
            # Full path to the shapefile
            shapefile_path = os.path.join(collected_data_folder, file)
            
            # Add the shapefile to the group layer
            add_layer_to_group(shapefile_path, group_layer)
            shapefiles_added = True

    if not shapefiles_added:
        arcpy.AddWarning(f"3. No shapefiles found in the input folder '{collected_data_folder}'.")

    # Save the project to retain changes
    aprx.save()

    arcpy.AddMessage(f"3. All shapefiles have been added to the '{group_layer_name}' group and project saved.")


############################
# 4. RE-PROJECT INPUT FC
############################
# Function to sanitize layer names for file output
def sanitize_name(name):
    # Replace invalid characters, including '.', with underscores
    sanitized = re.sub(r'[^\w]+', '_', name)  # '\w' matches [A-Za-z0-9_]
    sanitized = sanitized.replace('.', '_')  # Explicitly replace '.' with '_'
    # Ensure the name starts with a letter or underscore
    if not re.match(r'^[A-Za-z_]', sanitized):
        sanitized = f"_{sanitized}"
    return sanitized

# Main function to reproject shapefiles in a group layer
def reproject_shapefiles_in_group(fire_number):
    # Set the environment workspace to the default geodatabase
    default_gdb = arcpy.env.workspace

    # Define the spatial reference for WGS 1984 and BC Albers
    wgs1984 = arcpy.SpatialReference(4326)  # WGS 1984
    bc_albers = arcpy.SpatialReference(3005)  # NAD 1983 BC Environment Albers

    # Access the current project and map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map = aprx.activeMap

    # Generate the group layer name based on the fire number
    group_layer_name = f"{fire_number}_Input"

    # Find the group layer where the input shapefiles are located
    group_layer = next((lyr for lyr in map.listLayers() if lyr.isGroupLayer and lyr.name == group_layer_name), None)

    if not group_layer:
        arcpy.AddError(f"4. Group layer '{group_layer_name}' not found.")
        return

    # Loop through each layer in the group
    for lyr in group_layer.listLayers():
        # Check if the layer is a shapefile and if it's in WGS 1984
        if lyr.dataSource.endswith(".shp"):
            desc = arcpy.Describe(lyr)

            # Only reproject if the spatial reference is WGS 1984
            if desc.spatialReference.factoryCode == 4326:
                # Sanitize the layer name and create output shapefile name with 'BC' at the end
                sanitized_name = sanitize_name(lyr.name)
                output_name = f"{sanitized_name}_BC"
                output_fc = os.path.join(default_gdb, output_name)

                # Check if the output name is valid
                if arcpy.ValidateTableName(output_name, default_gdb) != output_name:
                    arcpy.AddWarning(f"4. Adjusted output name '{output_name}' is invalid in the geodatabase.")
                    continue  # Skip this layer or handle accordingly

                # Reproject the shapefile to BC Albers
                arcpy.management.Project(lyr.dataSource, output_fc, bc_albers)

                # Add the reprojected shapefile to the same group layer
                new_layer = map.addDataFromPath(output_fc)
                map.addLayerToGroup(group_layer, new_layer)

                # Remove the original layer from the map  <<<<
                map.removeLayer(new_layer)               #<<<<

                arcpy.AddMessage(f"4. Reprojected and added '{output_name}' to group '{group_layer_name}'.")
            else:
                arcpy.AddMessage(f"'4. {lyr.name}' is not in WGS 1984, skipping.")
    
    # Save the project to retain changes
    aprx.save()

    arcpy.AddMessage("4. Reprojection completed for all eligible shapefiles.")


    # RETURN POINT SHAPEFILES
    # Initialize a list to store reprojected point shapefiles
    reprojected_points = []

    # Loop through each layer in the group
    for lyr in group_layer.listLayers():
        # Check if the layer is a shapefile and if it's a point feature class
        if lyr.dataSource.endswith(".shp"):
            desc = arcpy.Describe(lyr)

            if desc.shapeType == "Point" and desc.spatialReference.factoryCode == 4326:
                # Sanitize the layer name and create output shapefile name
                sanitized_name = sanitize_name(lyr.name)
                output_name = f"{sanitized_name}_BC"
                output_fc = os.path.join("in_memory", output_name)

                # Reproject the shapefile to BC Albers
                arcpy.management.Project(lyr.dataSource, output_fc, bc_albers)
                reprojected_points.append(output_fc)

    # If multiple point shapefiles are reprojected, merge them
    if len(reprojected_points) > 1:
        merged_points = os.path.join("in_memory", f"{fire_number}_reprojected_points")
        arcpy.management.Merge(reprojected_points, merged_points)
        arcpy.AddMessage(f"4. Merged {len(reprojected_points)} reprojected point shapefiles into a single feature class.")
        return merged_points

    # If only one point shapefile, return it directly
    elif reprojected_points:
        return reprojected_points[0]

    # If no point shapefiles were reprojected, return None
    arcpy.AddError("4. No point shapefiles were reprojected.")
    return None

############################
# 5. COPY STAPIAL DATA POINTS
############################


def copy_points(points_to_copy, target_lyr):
    """
    Copies geometry from the feature class (layer object) 'points_to_copy'
    into the layer object 'target_lyr'.
    
    - 'points_to_copy' is an arcpy.mp.Layer object discovered in the "{fire_number}_Input" group
      matching the pattern ^[A-Za-z_]+_BC$.
    - 'target_lyr' is the arcpy.mp.Layer object for "wildfireBC_rehabPoint" inside "{fire_number}_Original".
    - Determines each layer's workspace and starts an edit session in the target's workspace.
    - Inserts all geometry from 'points_to_copy' into 'target_lyr'.
    """

    if not target_lyr.isFeatureLayer:
        arcpy.AddError(f"5. Target layer '{target_lyr.name}' is not a feature layer. Cannot copy points.")
        return

    if not points_to_copy.isFeatureLayer:
        arcpy.AddError(f"5. Source layer '{points_to_copy.name}' is not a feature layer. Cannot copy points.")
        return

    # --- Determine the workspace of the target (where we need to edit) ---
    conn_props = target_lyr.connectionProperties
    workspace = None

    # Enterprise GDB (SDE) scenario
    if 'connection_info' in conn_props:
        conn_info = conn_props['connection_info']
        if 'database' in conn_info:
            workspace = conn_info['database']
            arcpy.AddMessage(f"5. Workspace (SDE) from target: {workspace}")
        else:
            arcpy.AddError("5. Could not retrieve 'database' from the target layer's connection_info.")
            return
    else:
        # File GDB / Shapefile scenario
        workspace = os.path.dirname(target_lyr.dataSource)
        arcpy.AddMessage(f"5. Workspace (file GDB/shapefile) from target: {workspace}")

    if not workspace:
        arcpy.AddError("5. Failed to determine the workspace for the edit session.")
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

        arcpy.AddMessage(f"5. Successfully copied points from '{points_to_copy.name}' into '{target_lyr.name}'.")
    except Exception as e:
        arcpy.AddError(f"5. Error during editing/copy: {e}")



############################
# 6. UPDATE BASIC FIELDS
############################


def copy_attributes_based_on_location(source_lyr, target_lyr):
    """
    Copy attributes from 'source_lyr' into 'target_lyr' based on matching point locations.
    - 'source_lyr' is the layer from which we copy attributes (formerly 'points_to_copy').
    - 'target_lyr' is the layer to be updated (formerly 'wildfire_points').
    """

    # Both must be feature layers
    if not target_lyr.isFeatureLayer:
        arcpy.AddError(f"6. Target layer '{target_lyr.name}' is not a feature layer. Cannot copy attributes.")
        return

    if not source_lyr.isFeatureLayer:
        arcpy.AddError(f"6. Source layer '{source_lyr.name}' is not a feature layer. Cannot copy attributes.")
        return

    # --- Determine the workspace of the TARGET (like copy_points) ---
    conn_props_update = target_lyr.connectionProperties
    workspace_update = None

    if 'connection_info' in conn_props_update:
        # Probably enterprise GDB (SDE)
        conn_info_update = conn_props_update['connection_info']
        if 'database' in conn_info_update:
            workspace_update = conn_info_update['database']
            arcpy.AddMessage(f"6. Workspace (SDE) from target: {workspace_update}")
        else:
            arcpy.AddError("6. Could not retrieve 'database' from target layer's connection_info.")
            return
    else:
        # Likely a file GDB / shapefile
        workspace_update = os.path.dirname(target_lyr.dataSource)
        arcpy.AddMessage(f"6. Workspace (file GDB/shapefile) from target: {workspace_update}")

    if not workspace_update:
        arcpy.AddError("6. Failed to determine the workspace for the edit session.")
        return

    # Data source paths
    target_path = target_lyr.dataSource
    source_path = source_lyr.dataSource

    arcpy.AddMessage(f"6. target_path (update): {target_path}")
    arcpy.AddMessage(f"6. source_path (copy): {source_path}")

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
        arcpy.AddError("6. No matching fields found between the feature classes.")
        return

    arcpy.AddMessage(f"6. Field Mapping: {field_mapping}")

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

        arcpy.AddMessage("6. Field values copied successfully based on matching point locations.")
    except Exception as e:
        arcpy.AddError(f"6. Error during the edit session: {e}")
        return


############################
# 7. UPDATE BASIC FIELDS - DOMAINS
############################



def normalize_label(label):
    """Normalize label by removing punctuation, spaces, and lowering case."""
    return re.sub(r'[^a-zA-Z0-9]', '', label).lower()

def copy_attributes_with_domains(source_lyr, target_lyr):
    """
    Copies domain-related attributes from source_lyr to target_lyr
    by matching point geometries and using a normalized domain mapping.
    """

    if not source_lyr.isFeatureLayer or not target_lyr.isFeatureLayer:
        arcpy.AddError("7. Both source and target must be feature layers.")
        return

    # Determine workspace for edit session
    conn_props = target_lyr.connectionProperties
    if 'connection_info' in conn_props and 'database' in conn_props['connection_info']:
        workspace = conn_props['connection_info']['database']  # SDE
        arcpy.AddMessage(f"7. Workspace (SDE): {workspace}")
    else:
        workspace = os.path.dirname(target_lyr.dataSource)  # FileGDB
        arcpy.AddMessage(f"7. Workspace (FileGDB): {workspace}")

    if not workspace:
        arcpy.AddError("7. Could not determine workspace path.")
        return

    source_path = source_lyr.dataSource
    target_path = target_lyr.dataSource
    target_sr = arcpy.Describe(target_path).spatialReference

    # Domain mapping (raw, unnormalized)
    domain_mapping_raw = {
        'Berm Breach (BB)': '2',
        'Berm High (BH)': '43',
        'Cleared Area (CA)': '42',
        'Cross Ditch Culvert Backup (CDB)': '50',
        'Cross Ditch Install (CDI)': '6',
        'Cross Ditch Repair (CDR)': '7',
        'Culvert Clean Repair (CC)': '8',
        'Culvert Insert (CI)': '9',
        'Culvert No Damage (CND)': '51',
        'Culvert Remove and Dispose (CRD)': '52',
        'Ditch Clean Repair (DCR)': '14',
        'Ditch Install (DI)': '15',
        'Domestic Water Supply (W)': '18',
        'Dry Seed (DS)': '19',
        'Existing Deactivation (ED)': '20',
        'Hazard (H)': '27',
        'Infrastructure No Treatment (INT)': '53',
        'Infrastructure Repair (IR)': '54',
        'Lowbed Turnaround (LBT)': '55',
        'No Treatment Point (NT)': '41',
        'No Work Zone (NWZ)': '56',
        'Other Rehab Treatment Type (ORT)': '46',
        'Point of Commencement Termination (PCT)': '49',
        'Pull Back (PB)': '30',
        'Recontour (RC)': '31',
        'Restore Draw (RD)': '32',
        'Seepage (SG)': '48',
        'Steep Slope (SS)': '36',
        'Stream Crossing Classified (SCC)': '60',
        'Stream Crossing Non Classified (SCN)': '37',
        'Sump (SP)': '38',
        'Unassigned (UN)': '99',
        'Unique Point (UP)': '40',
        'Water Bar (WB)': '39',
        'Wood Bunched (BW)': '47',
        'Wood Burn Pile (BPW)': '34',
        'Wood Decked (DW)': '13'
    }
    domain_mapping = {normalize_label(k): v for k, v in domain_mapping_raw.items()}

    # Fields to map: {target_field: source_field}
    field_map = {
        "RPtType1": "sym_name",
        "RPtType2": "RPtType2",
        "RPtType3": "RPtType3"
    }

    arcpy.AddMessage("7. Indexing source features...")
    source_data = {}

    with arcpy.da.SearchCursor(source_path, ["SHAPE@"] + list(field_map.values())) as cursor:
        for row in cursor:
            geom = row[0].projectAs(target_sr)
            coords = (round(geom.centroid.X, 3), round(geom.centroid.Y, 3))
            source_data[coords] = dict(zip(field_map.values(), row[1:]))

    arcpy.AddMessage(f"7. {len(source_data)} source points indexed.")

    arcpy.AddMessage("7. Updating target features...")
    updated, skipped = 0, 0

    try:
        with arcpy.da.Editor(workspace):
            with arcpy.da.UpdateCursor(target_path, ["SHAPE@"] + list(field_map.keys())) as cursor:
                for row in cursor:
                    coords = (round(row[0].centroid.X, 3), round(row[0].centroid.Y, 3))
                    if coords not in source_data:
                        skipped += 1
                        continue

                    updated_this_row = False
                    for i, (target_field, source_field) in enumerate(field_map.items(), start=1):
                        val = source_data[coords].get(source_field)
                        if not val:
                            continue
                        normalized = normalize_label(val)
                        domain_val = domain_mapping.get(normalized)
                        if domain_val:
                            row[i] = domain_val
                            updated_this_row = True
                            arcpy.AddMessage(f"7. {target_field} <- '{val}' -> '{domain_val}'")
                        else:
                            arcpy.AddWarning(f"7. No match for {source_field}: '{val}'")

                    if updated_this_row:
                        cursor.updateRow(row)
                        updated += 1

        arcpy.AddMessage(f"7. {updated} features updated.")
        arcpy.AddWarning(f"7. {skipped} features skipped (no match).")
    except Exception as e:
        arcpy.AddError(f"7. Error during editing session: {e}")




############################
# 8. UPDATE BASIC FIELDS
############################


def update_wildfire_points(target_lyr, fire_number, fire_name, status):
    """
    Updates wildfire rehab point attributes in the provided layer.
    Only fills empty or default values in 'Fire_Num', 'Fire_Name', and 'Status'.
    """

    if not target_lyr.isFeatureLayer:
        arcpy.AddError(f"Layer '{target_lyr.name}' is not a feature layer.")
        return

    # Determine workspace path
    conn_props = target_lyr.connectionProperties
    if 'connection_info' in conn_props and 'database' in conn_props['connection_info']:
        workspace = conn_props['connection_info']['database']
        arcpy.AddMessage(f"Workspace (SDE): {workspace}")
    else:
        workspace = os.path.dirname(target_lyr.dataSource)
        arcpy.AddMessage(f"Workspace (FileGDB): {workspace}")

    if not workspace:
        arcpy.AddError("Could not determine the workspace.")
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

                #for row in cursor:
                #    if not row[0]:
                #        row[0] = fire_number
                #    if not row[1]:
                #        row[1] = fire_name
                #    if not row[2] or row[2] == 'RehabRequiresFieldVerification':
                #        row[2] = status
                #    cursor.updateRow(row)

        arcpy.AddMessage("8. Wildfire rehab points updated successfully.")
    except Exception as e:
        arcpy.AddError(f"8. Error during update: {e}")




# ####################################################################################################################################################
####################################################################################################################################################
####################################################################################################################################################


def main():

    # Get parameters from user
    fire_year = arcpy.GetParameterAsText(0)
    fire_number = arcpy.GetParameterAsText(1)
    backup_output_folder = arcpy.GetParameterAsText(2)
    collected_data_folder = arcpy.GetParameterAsText(3)
    fire_name = arcpy.GetParameterAsText(4)
    status = arcpy.GetParameterAsText(5)


#################################
    # Handle missing parameters
#################################
    if not fire_year:
        arcpy.AddError("Parameter 'fire_year' is missing or invalid.")
        exit()

    if not fire_number:
        arcpy.AddError("Parameter 'fire_number' is missing or invalid.")
        exit()

    if not backup_output_folder:
        arcpy.AddError("Parameter 'backup_output_folder' is missing or invalid.")
        exit()

    if not collected_data_folder:
        arcpy.AddError("Parameter 'collected_data_folder' is missing or invalid.")
        exit()

    if not fire_name:
        arcpy.AddError("Parameter 'fire_name' is missing or invalid.")
        exit()

    #if not contact_person:
    #    arcpy.AddError("Parameter 'contact_person' is missing or invalid.")
    #    exit()

    if not status:
        arcpy.AddError("Parameter 'status' is missing or invalid.")
        exit()




#################################
    # CALL FUNCTIONS
#################################
    # 1. Backup
    try:
        backup_gdb(fire_year, fire_number, backup_output_folder)
        arcpy.AddMessage("1. Backup completed successfully.")
    except Exception as e:
        arcpy.AddError(f"Error during 1. backup: {e}")
        exit()

    # 2. Import layers and get wildfire_points
    try:
        wildfire_points = add_layers_to_group(fire_year, fire_number)
        if wildfire_points is None:
            arcpy.AddError("2. Failed to retrieve wildfire_points.")
            exit()
        arcpy.AddMessage("2. Wildfire points imported successfully.")
    except Exception as e:
        arcpy.AddError(f"Error during 2. importing wildfire points: {e}")
        exit()

    # 3. Collected data
    try:
        add_shapefiles_to_group(fire_number, collected_data_folder)
        arcpy.AddMessage("3. Collected data copied successfully.")
    except Exception as e:
        arcpy.AddError(f"Error during copying 3. Collected data: {e}")
        exit()

    # 4. Re-Project and get points_to_copy
    points_to_copy = reproject_shapefiles_in_group(fire_number)
    if points_to_copy is None:
        arcpy.AddError("Failed to retrieve points_to_copy. 4. Re-Project.")
        exit()

    """
    1. Find the input group layer named '{fire_number}_Input'.
       - For each sublayer matching pattern ^[A-Za-z_]+_BC$ AND geometry == Point, gather them as 'points_to_copy'.
    2. Find the target group layer '{fire_number}_Original' -> sublayer 'wildfireBC_rehabPoint'.
    3. For EACH matched 'points_to_copy' layer, call copy_points(points_to_copy, target_lyr).
    """

    fire_number = fire_number
    group_input_layer_name = f"{fire_number}_Input"
    pattern = r'^[A-Za-z0-9_]+_BC$'

    # We also want the target group and sublayer
    group_target_layer_name = f"{fire_number}_Original"
    source_layer_name = "wildfireBC_Rehab_Point"  #"wildfireBC_rehabPoint"

    # Get the current project and active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap

    if not active_map:
        arcpy.AddError("No active map found. Open a map in ArcGIS Pro before running.")
        return

    # --------------------------------------------------------------------
    # 1. Locate the INPUT group layer ("C50903_Input") and gather sublayers
    #    that match ^[A-Za-z_]+_BC$ AND have shapeType == "Point".
    # --------------------------------------------------------------------
    input_group_lyr = None
    for lyr in active_map.listLayers():
        if lyr.isGroupLayer and lyr.name == group_input_layer_name:
            input_group_lyr = lyr
            break

    if not input_group_lyr:
        arcpy.AddError(f"Group layer '{group_input_layer_name}' (Input) not found.")
        return

    matched_layers = []
    for lyr in input_group_lyr.listLayers():
        if re.match(pattern, lyr.name):
            # Check geometry type to ensure it's a Point layer
            desc = arcpy.Describe(lyr.dataSource)
            if desc.shapeType == "Point":
                matched_layers.append(lyr)
            else:
                arcpy.AddMessage(f"Skipping '{lyr.name}' (shapeType = {desc.shapeType}).")
    
    if not matched_layers:
        arcpy.AddError(
            f"No point sublayers in '{group_input_layer_name}' match pattern '{pattern}'."
        )
        return
    else:
        arcpy.AddMessage(
            f"Found {len(matched_layers)} point layer(s) matching '{pattern}' in '{group_input_layer_name}'."
        )

    # --------------------------------------------------------------------
    # 2. Locate the TARGET group layer ("C50903_Original") -> sublayer "wildfireBC_rehabPoint".
    # --------------------------------------------------------------------
    target_group_lyr = None
    for lyr in active_map.listLayers():
        if lyr.isGroupLayer and lyr.name == group_target_layer_name:
            target_group_lyr = lyr
            break

    if not target_group_lyr:
        arcpy.AddError(f"Group layer '{group_target_layer_name}' (Target) not found.")
        return

    target_lyr = None
    for lyr in target_group_lyr.listLayers():
        if lyr.name == source_layer_name:
            target_lyr = lyr
            break

    if not target_lyr:
        arcpy.AddError(f"Sublayer '{source_layer_name}' not found in group '{group_target_layer_name}'.")
        return

    if not target_lyr.isFeatureLayer:
        arcpy.AddError(f"'{source_layer_name}' is not a feature layer and cannot receive new points.")
        return

    # --------------------------------------------------------------------
    # 5. For each matched input layer, copy its features into the target layer.
    # --------------------------------------------------------------------
    for pts_layer in matched_layers:
        # Optional selection if you want to see them highlighted:
        # arcpy.management.SelectLayerByAttribute(pts_layer, "CLEAR_SELECTION")
        # arcpy.management.SelectLayerByAttribute(pts_layer, "NEW_SELECTION", "1=1")

        copy_points(pts_layer, target_lyr)


    # 6. Copy Attributes Based on Location
    for pts_layer in matched_layers:
        copy_attributes_based_on_location(pts_layer, target_lyr)

    # 7. Copy Domains (Optional)
    for pts_layer in matched_layers:
        copy_attributes_with_domains(pts_layer, target_lyr)

    # 8. Update Basic Fields
    try:
        # Pass the same target_lyr you used in steps 5–7
        update_wildfire_points(target_lyr, fire_number, fire_name, status)
        arcpy.AddMessage("8. Basic fields updated successfully.")
    except Exception as e:
        arcpy.AddError(f"Error during 8. updating basic fields: {e}")
        exit()
####################################################################################################################################################


# Standard way to run main() if this file is executed in standalone mode
if __name__ == "__main__":

    main()






    