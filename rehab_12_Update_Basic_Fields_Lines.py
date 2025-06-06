import arcpy


# Function to normalize status input
def normalize_status(user_status):
    if user_status in ['RehabFieldVerified','Field Verified']:
        return 'RehabFieldVerified'
    elif user_status in ['RehabCompleted','Completed', 'Complete', 'Rehab Completed', 'Rehab Complete']:
        return 'RehabCompleted'
    elif user_status in ['RehabObligationsTransferred','Obligations Transferred']:
        return 'RehabObligationsTransferred'
    return user_status  # Return original if no match

# Main function to update fields in the feature class
def update_wildfire_lines(fire_number, fire_name,  status):
    # Set the workspace environment
    fgdb = arcpy.env.workspace

    ######################################################################
    # Define the feature class
    wildfire_lines = f"{fire_number}_Original\\wildfireBC_Rehab_Line"
    ######################################################################


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

# User inputs from ArcGIS Pro tool
fire_number = arcpy.GetParameterAsText(0)  # Fire number for dynamic naming
fire_name = arcpy.GetParameterAsText(1)  # Fire name
status = arcpy.GetParameterAsText(2)  # Status (should be text)

# Run the function with the provided parameters
update_wildfire_lines(fire_number, fire_name, status)
