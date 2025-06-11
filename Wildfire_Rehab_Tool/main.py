# Step 1
"""
This is the entry point of the Wildfire Rehab Tool.
It collects user input parameters from the ArcGIS Pro tool interface,
initializes the RehabJob controller with those parameters,
and triggers the full rehab processing pipeline.
"""

# Wildfire_Rehab_Tool/main.py

# Project setup
from a_project_setup._1_backup_gdb import *
from a_project_setup._2_import_and_group_layers import *
from a_project_setup._3_import_collected_data import *
from a_project_setup._4_re_project_input_fc import *

# Point processing
from b_points._5_copy_stapial_data_points import *
from b_points._6_copy_attributes_based_on_location_points import *
from b_points._7_copy_attributes_with_domains_points import *
from b_points._8_update_basic_fields_points import *

# Line processing
from c_lines._9_copy_spatial_data_lines import *
from c_lines._10_update_basic_fields_lines import *
from c_lines._11_copy_attributes_based_on_location_lines import *
from c_lines._12_copy_domains_based_on_location_lines import *

# Runner
from d_runner._13_locate_and_retrive_data_from_map import locate_and_retrieve
import arcpy

def main():

    # Get parameters from user
    fire_year = arcpy.GetParameterAsText(0)
    fire_number = arcpy.GetParameterAsText(1)
    collected_data_folder = arcpy.GetParameterAsText(2)
    fire_name = arcpy.GetParameterAsText(3)
    status = arcpy.GetParameterAsText(4)


#################################
    # Handle missing parameters
#################################
    if not fire_year:
        arcpy.AddError("Parameter 'fire_year' is missing or invalid.")
        exit()

    if not fire_number:
        arcpy.AddError("Parameter 'fire_number' is missing or invalid.")
        exit()

    if not collected_data_folder:
        arcpy.AddError("Parameter 'collected_data_folder' is missing or invalid.")
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
    # 1. Backup
    try:
        backup_gdb(fire_year, fire_number)
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


    # Step 4.5 - Locate relevant layers
    layers = locate_and_retrieve(fire_number)
    if not layers:
        arcpy.AddError("One or more required layers could not be located. Exiting.")
        return

    matched_pts, target_pts, matched_lines, target_lines = layers

    # Step 5 - Copy Spatial Points
    for layer in matched_pts:
        try:
            copy_points(layer, target_pts)
        except Exception as e:
            arcpy.AddError(f"Error in Step 5 (copy_points): {e}")
            return

    # Step 6 - Copy Attributes from Points
    for layer in matched_pts:
        try:
            copy_attributes_based_on_location(layer, target_pts)
        except Exception as e:
            arcpy.AddError(f"Error in Step 6 (copy_attributes_based_on_location): {e}")
            return

    # Step 7 - Copy Domains from Points
    for layer in matched_pts:
        try:
            copy_attributes_with_domains(layer, target_pts)
        except Exception as e:
            arcpy.AddError(f"Error in Step 7 (copy_attributes_with_domains): {e}")
            return

    # Step 8 - Update Point Fields
    try:
        update_wildfire_points(target_pts, fire_number, fire_name, status)
        arcpy.AddMessage("Step 8. Point fields updated successfully.")
    except Exception as e:
        arcpy.AddError(f"Error in Step 8 (update_wildfire_points): {e}")
        return

    # Step 9 - Copy Spatial Lines
    for layer in matched_lines:
        try:
            copy_lines(layer, target_lines)
            arcpy.AddMessage("Step 9. Spatial data (lines) copied successfully.")
        except Exception as e:
            arcpy.AddError(f"Error in Step 9 (copy_lines): {e}")
            return

    # Step 10 - Update Line Fields
    try:
        update_wildfire_lines(target_lines, fire_number, fire_name, status)
        arcpy.AddMessage("Step 10. Line fields updated successfully.")
    except Exception as e:
        arcpy.AddError(f"Error in Step 10 (update_wildfire_lines): {e}")
        return

    # Step 11 - Copy Attributes from Lines
    for layer in matched_lines:
        try:
            copy_attributes_based_on_location_lines(layer, target_lines)
            arcpy.AddMessage("Step 11. Attributes from lines copied successfully.")
        except Exception as e:
            arcpy.AddError(f"Error in Step 11 (copy_attributes_based_on_location_lines): {e}")
            return

    # Step 12 - Copy Domains from Lines
    for layer in matched_lines:
        try:
            copy_attributes_with_domains_lines(layer, target_lines)
            arcpy.AddMessage("Step 12. Domains from lines copied successfully.")
        except Exception as e:
            arcpy.AddError(f"Error in Step 12 (copy_attributes_with_domains_lines): {e}")
            return


####################################################################################################################################################


# Standard way to run main() if this file is executed in standalone mode
if __name__ == "__main__":

    main()
