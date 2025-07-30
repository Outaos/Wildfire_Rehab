"""
Creates a backup of the Rehab geodatabase for a given fire number and year.

Determines the appropriate district based on the fire number, constructs the input
and output paths, and copies the backup geodatabase to the Outgoing folder.
"""

import arcpy


def backup_gdb(fire_year, fire_number):
    # Check if GDB has a fire_number
    if "FIRENUMBER" in fire_number.upper():
        msg = "Step 1. Please update the geodatabase name, as it is currently set to FIRENUMBER_Rehab.gdb and the fire number has not been specified."
        arcpy.AddError(msg)
        print(msg)
        return
    
    # Derive fire_code from fire_number
    fire_code = fire_number[:2]  
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
    #input_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    input_gdb = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Scripts\Rehab\Wildfire_Rehab_GitHub\Wildfire_Rehab_ProcessSuite\FireSeasonWork_Test\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    #output_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\Outgoing\{fire_number}_Rehab_Backup.gdb"
    output_gdb = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Scripts\Rehab\Wildfire_Rehab_GitHub\Wildfire_Rehab_ProcessSuite\FireSeasonWork_Test\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\Outgoing\{fire_number}_Rehab_Backup.gdb"


    # Perform the copy operation
    arcpy.Copy_management(input_gdb, output_gdb)

    print("Step 1. Backup completed successfully.")

if __name__ == "__main__":
    #fire_year = '2024'
    #fire_number = 'C41440' 
    # Get parameters from user
    fire_year = arcpy.GetParameterAsText(0)
    fire_number = arcpy.GetParameterAsText(1)
    
    # Call the backup function
    backup_gdb(fire_year, fire_number)





