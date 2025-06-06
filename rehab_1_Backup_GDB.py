# 1. BACKUP GDB

import arcpy
import os

def backup_gdb(new_fire_year, new_fire_number, output_folder):
    # Derive fire_code from fire_number
    new_fire_code = new_fire_number[:2]  # Take the first two characters of fire_number
    # Define input and output paths
    #input_gdb = fr"F:\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{new_fire_year}\Cariboo\{new_fire_code}\{new_fire_number}\Data\{new_fire_number}_Rehab.gdb"
    input_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{new_fire_year}\Cariboo\{new_fire_code}\{new_fire_number}\Data\{new_fire_number}_Rehab.gdb"
    output_gdb = os.path.join(output_folder, f"{new_fire_number}_Rehab_BU.gdb")

    # Create output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Perform the copy operation
    arcpy.Copy_management(input_gdb, output_gdb)

    print("Backup completed successfully.")

if __name__ == "__main__":
    # Get parameters from user
    new_fire_year = arcpy.GetParameterAsText(0)
    #new_fire_code = arcpy.GetParameterAsText(1)
    new_fire_number = arcpy.GetParameterAsText(1)
    output_folder = arcpy.GetParameterAsText(2)

    # Call the backup function
    backup_gdb(new_fire_year, new_fire_number, output_folder)