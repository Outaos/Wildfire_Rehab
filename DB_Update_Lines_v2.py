
import arcpy
import os
import re

#################################################################################
# 10. Copy Spatial Data - Lines
#################################################################################

####################################################################
# Function to copy lines from one feature class to another
def copy_lines(lines_to_copy, wildfire_lines):

    count = 0

    # Create a search cursor to iterate over the selected lines in lines_to_copy
    with arcpy.da.SearchCursor(lines_to_copy, ["SHAPE@"]) as cursor:
        # Create an insert cursor to add lines to wildfire_lines
        with arcpy.da.InsertCursor(wildfire_lines, ["SHAPE@", "Fire_Num"]) as insert_cursor:
            for row in cursor:
                insert_cursor.insertRow((row[0], ''))
                #insert_cursor.insertRow(row)
                count += 1
        
    arcpy.AddMessage(f"{count} lines copied into wildfire_lines.")





#################################################################################
# 11. Update Basic Fields - Lines
#################################################################################

# Function to normalize status input
def normalize_status(user_status):
    if user_status == 'Field Verified':
        return 'RehabFieldVerified'
    elif user_status in ['Completed', 'Complete', 'Rehab Completed', 'Rehab Complete']:
        return 'RehabCompleted'
    elif user_status == 'Obligations Transferred':
        return 'RehabObligationsTransferred'
    return user_status  # Return original if no match

# Main function to update fields in the feature class
def update_wildfire_lines(wildfire_lines, fire_number, fire_name, status):
    # Set the workspace environment
    fgdb = arcpy.env.workspace


    # Normalize the status based on user input
    normalized_status = normalize_status(status)

    # Use an UpdateCursor to iterate through the rows and update the fields
    with arcpy.da.UpdateCursor(wildfire_lines, ["Fire_Num", "Fire_Name", "Status"]) as cursor:
        for row in cursor:
            # Safely update each field with default values if None or empty
            if row[0] is None or row[0] == '':
                row[0] = f"{fire_number}"

            if row[1] is None or row[1] == '':
                row[1] = f"{fire_name}"

            if row[2] is None or row[2] == '' or row[2] == 'RehabRequiresFieldVerification':
                row[2] = normalized_status

            # Update the row
            cursor.updateRow(row)

    arcpy.AddMessage("Field update process completed.")




#################################################################################
# 12. Copy Attributes Based On Location - Lines
#################################################################################


# Function to copy attributes based on spatial location
def copy_attributes_based_on_location(lines_to_copy, wildfire_lines):
    arcpy.AddMessage(" Starting attribute copy process...")
    print(" Starting attribute copy process...")
    # Access the current project and active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap

    # Try to get the layer objects for wildfire_lines and lines_to_copy
    layer_update = None
    layer_copy = None
    for lyr in map_obj.listLayers():
        if lyr.name == wildfire_lines or lyr.longName == wildfire_lines:
            layer_update = lyr
        if lyr.name == lines_to_copy or lyr.longName == lines_to_copy:
            layer_copy = lyr

    if layer_update is None:
        arcpy.AddError(f"Layer '{wildfire_lines}' not found in the current map.")
        return
    if layer_copy is None:
        arcpy.AddError(f"Layer '{lines_to_copy}' not found in the current map.")
        return

    # Get the workspace from the layer's connection properties for wildfire_lines
    conn_props_update = layer_update.connectionProperties

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
        workspace_update = os.path.dirname(layer_update.dataSource)
        arcpy.AddMessage(f"Workspace from dataSource (wildfire_lines): {workspace_update}")

    # Ensure workspace was obtained
    if not workspace_update:
        arcpy.AddError("Failed to determine the workspace for wildfire_lines.")
        return

    # Get data source paths
    wildfire_lines_path = layer_update.dataSource
    lines_to_copy_path = layer_copy.dataSource
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







#################################################################################
# 13. Copy Domains Based On Location - Lines
#################################################################################


def normalize_label(label):
    """Normalize label by removing punctuation, spaces, and lowering case."""
    return re.sub(r'[^a-zA-Z0-9]', '', label).lower()

def copy_attributes_with_domains(lines_to_copy, wildfire_lines):
    print(" Starting attribute copy with domain mapping...")
    arcpy.AddMessage(" Starting attribute copy with domain mapping...")

    # DOMAIN MAPPING
    domain_mapping_raw = {
        # RLType1 or RLType2
        'Ditch Clean Repair (DCR)': '1',
        'Dry Seed (DS)': '2',
        'Grade Road (GR)': '5',
        'Pull Back (PB)': '6',
        'Recontour (RC)': '7',
        'Steep Slopes (SS)': '10',
        'No Treatment (NT)': '11',
        'Fire Hazard Treatment (FHT)': '13',
        'Other Rehab Treatment Type (ORT)': '16',
        'Infrastructure Repair (IR)': '20',
        'Infrastructure No Treatment (INT)': '21',
        'No Work Zone (NWZ)': '22',
        'No Treatment - Line (NA)': '11',
        
        # FLType1
        'Unknown': '0',
        'Active Burnout': '1',
        'Aerial Foam Drop': '2',
        'Aerial Hazard': '3',
        'Aerial Ignition': '4',
        'Aerial Retardant Drop': '5',
        'Aerial Water Drop': '6',
        'Branch Break': '7',
        'Completed Burnout': '8',
        'Completed Machine Line': '9',
        'Completed Handline': '10',
        'Completed Line': '11',
        'Division Break': '12',
        'Danger Tree Assessed': '13',
        'Danger Tree Assessed/Felled': '14',
        'Escape Route': '15',
        'Fire Break Planned or Incomplete': '16',
        'Fire Spread Prediction': '17',
        'Highlighted Geographic Feature': '18',
        'Highlighted Manmade Feature': '19',
        'Line Break Complete': '20',
        'Planned Fire Line': '21',
        'Planned Secondary Line': '22',
        'Proposed Burnout': '23',
        'Proposed Machine Line': '24',
        'Trigger Point': '25',
        'Uncontrolled Fire Edge': '26',
        'Other': '27',
        'Contingency Line': '28',
        'No Work Zone': '29',
        'Completed Fuel Free Line': '30',
        'Road - Modified Existing': '32',
        'Trail': '34',
        'Road': '31',
        'Road - Heavily Used': '33',
        'Pipeline': '35',
        'Completed Hoselay': '36',
        'Containment / Control Line': '37',
        # Line Width
        # '1m': '0',   <--------------------------- this will need to be added later
        '5m': '0',
        '10m': '1',
        '15m': '2',
        '20m and wider': '3',
        # AvgSlope
        '0 to 15': '0',
        '16 to 25': '1',
        '26 to 35': '2',
        'above 35': '3'
    }

    domain_mapping = {normalize_label(k): v for k, v in domain_mapping_raw.items()}

    spatial_ref_wildfire_lines = arcpy.Describe(wildfire_lines).spatialReference
    print(f" Spatial reference: {spatial_ref_wildfire_lines.name}")
    arcpy.AddMessage(f" Spatial reference: {spatial_ref_wildfire_lines.name}")

    print(" Reading source features...")
    arcpy.AddMessage(" Reading source features...")

    # Build dict: (X,Y) -> {"RPtType1": val1, "RPtType2": val2, "RPtType3": val3}
    source_data = {}
    with arcpy.da.SearchCursor(lines_to_copy, ["SHAPE@", "RLType1", "RLType2","RLType3", "FLType1", "FLType2", "LineWidth", "Slope"]) as cursor:
        for row in cursor:
            #point_geom = row[0].projectAs(spatial_ref_wildfire_lines)
            #coords = (round(point_geom.centroid.X, 3), round(point_geom.centroid.Y, 3))
            projected_line = row[0].projectAs(spatial_ref_wildfire_lines)
            first_vertex = (round(projected_line.firstPoint.X, 3), round(projected_line.firstPoint.Y, 3))
            last_vertex = (round(projected_line.lastPoint.X, 3), round(projected_line.lastPoint.Y, 3))
            coords = (first_vertex, last_vertex)
            source_data[coords] = {
                "RLType": row[1],
                "RLType2": row[2],
                "RLType3": row[3],
                "FLType": row[4],
                "FLType2": row[5],
                "LineWidth": row[6],
                "AvgSlope": row[7]
            }

    print(f" {len(source_data)} source points indexed.")
    arcpy.AddMessage(f" {len(source_data)} source points indexed.")

    print(" Updating target features...")
    arcpy.AddMessage(" Updating target features...")

    updated = 0
    skipped = 0
    fields_to_update = ["RLType1", "RLType2","RLType3", "FLType1", "FLType2", "LineWidth", "AvgSlope"]

    with arcpy.da.UpdateCursor(wildfire_lines, ["SHAPE@"] + fields_to_update) as cursor:
        for row in cursor:
            #coords = (round(row[0].centroid.X, 3), round(row[0].centroid.Y, 3))
            first_vertex = (round(row[0].firstPoint.X, 3), round(row[0].firstPoint.Y, 3))
            last_vertex = (round(row[0].lastPoint.X, 3), round(row[0].lastPoint.Y, 3))
            coords = (first_vertex, last_vertex)
            if coords in source_data:
                changed = False
                for i, field in enumerate(fields_to_update):
                    source_val = source_data[coords].get(field)
                    if source_val:
                        normalized = normalize_label(source_val)
                        mapped_val = domain_mapping.get(normalized)
                        if mapped_val:
                            row[i + 1] = mapped_val
                            changed = True
                            print(f" {field} updated from '{source_val}' -> '{mapped_val}'")
                            arcpy.AddMessage(f" {field} updated from '{source_val}' -> '{mapped_val}'")
                        else:
                            print(f" No domain match for {field}: '{source_val}'")
                            arcpy.AddWarning(f" No domain match for {field}: '{source_val}'")
                            skipped += 1
                if changed:
                    cursor.updateRow(row)
                    updated += 1
            else:
                skipped += 1

    print(f" {updated} rows updated.")
    print(f" {skipped} rows skipped.")
    arcpy.AddMessage(f" {updated} rows updated.")
    arcpy.AddWarning(f" {skipped} rows skipped.")
    print(" Done.")
    arcpy.AddMessage(" Done.")






# ####################################################################################################################################################
####################################################################################################################################################
####################################################################################################################################################



def main():

    # Get parameters from user
    lines_to_copy = arcpy.GetParameterAsText(0)
    wildfire_lines = arcpy.GetParameterAsText(1)
    fire_number = arcpy.GetParameterAsText(2)
    fire_name = arcpy.GetParameterAsText(3)
    status = arcpy.GetParameterAsText(4)


    # Handle missing parameters
    if not lines_to_copy:
        arcpy.AddError("Parameter 'lines_to_copy' is missing or invalid.")
        exit()

    if not wildfire_lines:
        arcpy.AddError("Parameter 'wildfire_lines' is missing or invalid.")
        exit()

    if not fire_number:
        arcpy.AddError("Parameter 'fire_number' is missing or invalid.")
        exit()

    if not fire_name:
        arcpy.AddError("Parameter 'fire_name' is missing or invalid.")
        exit()

    if not status:
        arcpy.AddError("Parameter 'status' is missing or invalid.")
        exit()


#################################
    # CALL FUNCTIONS
#################################
    # 10. Copy Spatial Data - Lines    
    try:
        copy_lines(lines_to_copy, wildfire_lines)
        arcpy.AddMessage("10. Copy Spatial Data - Lines completed successfully.")
    except Exception as e:
        arcpy.AddError(f"Error during 10. Copy Spatial Data - Lines: {e}")
        exit()


    # 11. Update Basic Fields - Lines    
    try:
        update_wildfire_lines(wildfire_lines, fire_number, fire_name, status)
        arcpy.AddMessage("11. Update Basic Fields - Lines  completed successfully.")
    except Exception as e:
        arcpy.AddError(f"Error during 11. Update Basic Fields - Lines: {e}")
        exit()


    # 12. Copy Attributes Based On Location - Lines
    try:
        copy_attributes_based_on_location(lines_to_copy, wildfire_lines)
        arcpy.AddMessage("12. Copy Attributes Based On Location - Lines  completed successfully.")
    except Exception as e:
        arcpy.AddError(f"Error during 12. Copy Attributes Based On Location - Lines: {e}")
        exit()

    # 13. Copy Domains Based On Location - Lines
    try:
        copy_attributes_with_domains(lines_to_copy, wildfire_lines)
        arcpy.AddMessage("13. Copy Domains Based On Location - Lines  completed successfully.")
    except Exception as e:
        arcpy.AddError(f"Error during 13. Copy Domains Based On Location - Lines: {e}")
        exit()

# Standard way to run main() if this file is executed in standalone mode
if __name__ == "__main__":

    main()

    '''
        'Clean Ditch (CD)': '1',
        'Dry Seed (DS)': '2',
        'Fence - Damaged (FD)': '3',
        'Fence - Undamaged (FND)': '4',
        'Danger Tree Treatment Required (DTA)': '14',
        'Grade Road (GR)': '5',
        'Pull Back (PB)': '6',
        'Recontour (RC)': '7',
        'Steep Slopes >35% (SS)': '10',
        'No Treatment - Line (NA)': '11',
        'Hazard (H)': '13',
        'Unassigned': '99',
        'Fuel Hazard Treatment Required (FHT)': '15',
        'Division Break': '89',
        'Other Rehab Treatment Type ORT': '16',
        'Road Damage - Requires Repair (RR)': '9',
    '''

    