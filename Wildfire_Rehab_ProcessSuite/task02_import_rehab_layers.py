"""
Adds point and line rehab feature classes to a group layer in the current ArcGIS Pro map.

Constructs the geodatabase path based on fire year and number, verifies dataset existence,
and adds the relevant layers to a group named '{FIRE_NUMBER}_Master'. If the group already
exists, a warning is issued and no layers are added.

Returns:
    str: Path to the wildfireBC_Rehab_Point feature class if successful.
"""
import arcpy
import os

def add_layers_to_group(fire_year, fire_number):
    # Set the Project and Map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap

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
        raise ValueError(f"Step 2. Unknown district code '{district_code}' in fire_number '{fire_number}'")

    # Define the path to the GeoDatabase and feature dataset
    gdb_path = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    #gdb_path = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Scripts\Rehab\Wildfire_Rehab_GitHub\Wildfire_Rehab_ProcessSuite\FireSeasonWork_Test\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    feature_dataset = "wildfireBC_Rehab"

    # Check if the GeoDatabase exists
    if not arcpy.Exists(gdb_path):
        arcpy.AddError(f"Step 2. The GeoDatabase '{gdb_path}' does not exist.")
        return

    # Use appropriate naming based on fire year
    try:
        fire_year_int = int(fire_year)
    except ValueError:
        arcpy.AddError("Step 2. Fire year must be a valid integer.")
        return

    # Try lowercase version first
    fc_points = os.path.join(gdb_path, feature_dataset, "wildfireBC_rehabPoint")
    fc_lines = os.path.join(gdb_path, feature_dataset, "wildfireBC_rehabLine")

    if not arcpy.Exists(fc_points) or not arcpy.Exists(fc_lines):
        # Try 2025-style naming
        fc_points_alt = os.path.join(gdb_path, feature_dataset, "wildfireBC_Rehab_Point")
        fc_lines_alt = os.path.join(gdb_path, feature_dataset, "wildfireBC_Rehab_Line")

        if arcpy.Exists(fc_points_alt) and arcpy.Exists(fc_lines_alt):
            fc_points = fc_points_alt
            fc_lines = fc_lines_alt
        else:
            if not arcpy.Exists(fc_points):
                arcpy.AddError(f"Step 2. Neither 'wildfireBC_rehabPoint' nor 'wildfireBC_Rehab_Point' exist in: {gdb_path}")
            if not arcpy.Exists(fc_lines):
                arcpy.AddError(f"Step 2. Neither 'wildfireBC_rehabLine' nor 'wildfireBC_Rehab_Line' exist in: {gdb_path}")
            return

    group_layer_name = f"{fire_number}_Master"
    group_layer_exists = any(lyr.name == group_layer_name for lyr in map_obj.listLayers() if lyr.isGroupLayer)

    if not group_layer_exists:
        group_layer = map_obj.createGroupLayer(group_layer_name)

        def add_layer_to_group(fc_path, layer_name, group_layer):
            if not any(lyr.name == layer_name for lyr in group_layer.listLayers()):
                new_layer = map_obj.addDataFromPath(fc_path)
                map_obj.addLayerToGroup(group_layer, new_layer, "BOTTOM")
                map_obj.removeLayer(new_layer)

        add_layer_to_group(fc_points, "wildfireBC_Rehab_Point", group_layer)
        add_layer_to_group(fc_lines, "wildfireBC_Rehab_Line", group_layer)

        aprx.save()
        arcpy.AddMessage(f"Step 2. Layers added directly to '{group_layer_name}' group, standalone layers avoided.")
    else:
        arcpy.AddWarning(f"'Step 2. {group_layer_name}' group already exists. No layers were added.\nPlease update: 'FIRE_NUMBER'")

    return fc_points

# Execute the Main Function
if __name__ == "__main__":
    fire_year = arcpy.GetParameterAsText(0)
    fire_number = arcpy.GetParameterAsText(1)

    add_layers_to_group(fire_year, fire_number)
