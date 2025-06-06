import arcpy

# Function to update Status field based on user selection
def update_status(fc, new_status):
    with arcpy.da.UpdateCursor(fc, ["Status"]) as cursor:
        for row in cursor:
            row[0] = new_status
            cursor.updateRow(row)
    arcpy.AddMessage(f"All features updated to Status = '{new_status}'.")

# Get user inputs from tool
fc = arcpy.GetParameterAsText(0)  # Input feature class
new_status = arcpy.GetParameterAsText(1)  # Status to apply (from value list)

# Run the update
update_status(fc, new_status)
