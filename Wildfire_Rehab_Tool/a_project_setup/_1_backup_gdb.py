"""
Creates a backup of the Rehab geodatabase for a given fire number and year.

Determines the appropriate district based on the fire number, constructs the input
and output paths, and uses ArcPy to copy the geodatabase to the Outgoing folder.
"""

import arcpy


############################
# 1. BACKUP GDB
############################
def backup_gdb(fire_year, fire_number):
    
    # Derive the codes
    fire_code = fire_number[:2]  # Take the first two characters of fire_number
    district_code = fire_number[0].upper()

    # Map district codes to district names
    district_map = {
            "C": "Cariboo",
            "V": "Coastal",
            "K": "Kamloops",
            "R": "NorthWest",
            "G": "PrinceGeorge",
            "N": "SouthEast"
    }

    # Get the district name, or raise an error if not found
    fire_district = district_map.get(district_code)
    if not fire_district:
        raise ValueError(f"Step 1. Unknown district code '{district_code}' in fire_number '{fire_number}'")
    
    # Define input and output paths
    input_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    output_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\Outgoing\{fire_number}_Rehab_Backup.gdb"

    # Perform the copy operation
    arcpy.Copy_management(input_gdb, output_gdb)

    print("Step 1. Backup completed successfully.")