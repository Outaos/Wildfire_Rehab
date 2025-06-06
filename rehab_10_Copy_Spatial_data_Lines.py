import arcpy

####################################################################
# Function to copy lines from one feature class to another
def copy_lines(lines_to_copy, wildfire_lines):

    # Create a search cursor to iterate over the selected lines in lines_to_copy
    with arcpy.da.SearchCursor(lines_to_copy, ["SHAPE@"]) as cursor:
        # Create an insert cursor to add lines to wildfire_lines
        with arcpy.da.InsertCursor(wildfire_lines, ["SHAPE@", "Fire_Num"]) as insert_cursor:
            for row in cursor:
                insert_cursor.insertRow((row[0], ''))

    arcpy.AddMessage("New lines created in wildfire_lines at the selected locations.")

# Parameters from ArcGIS Pro tool
lines_to_copy = arcpy.GetParameterAsText(0)  # First parameter: feature class with lines to copy
wildfire_lines = arcpy.GetParameterAsText(1)  # Second parameter: feature class where lines will be copied

# Run the function with the provided parameters
copy_lines(lines_to_copy, wildfire_lines)
