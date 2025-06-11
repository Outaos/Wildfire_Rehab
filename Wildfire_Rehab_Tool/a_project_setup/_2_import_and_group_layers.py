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



############################
# 2. IMPORT AND GROUP LAYERS
############################

# Define a function
def add_layers_to_group(fire_year, fire_number):
    # Set the Project and Map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap


    # Derive codes
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

    # Define the path to the GeoDatabase  and feature dataset
    gdb_path = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"

    feature_dataset = "wildfireBC_Rehab"


    # Check if the GeoDatabase exists:
    if not arcpy.Exists(gdb_path):
        arcpy.AddError(f"Step 2. The GeoDatabase '{gdb_path}' does not exist.")
        return
    
    # Define the feature classes
    fc_points = os.path.join(gdb_path, feature_dataset, "wildfireBC_Rehab_Point")
    fc_lines = os.path.join(gdb_path, feature_dataset, "wildfireBC_Rehab_Line")

    # Check if the feature classes exist:
    if not arcpy.Exists(fc_points):
        arcpy.AddError(f"Step 2. The feature class '{fc_points}' does not exist.")
        return
    if not arcpy.Exists(fc_lines):
        arcpy.AddError(f"Step 2. The feature class '{fc_lines}' does not exist.")
        return
    
    # Define the names of the layers to be grouped
    #layer_names_to_group = ["wildfireBC_Rehab_Point", "wildfireBC_Rehab_Line"]

    # Check if the group layer already exists
    group_layer_name = f"{fire_number}_Master"
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

        arcpy.AddMessage(f"Step 2. Layers added directly to '{group_layer_name}' group, standalone layers avoided.")
    else:
        arcpy.AddWarning(f"'Step 2. {group_layer_name}' group already exists. No layers were added.\nPlease update: 'FIRE_NUMBER'")

    return fc_points