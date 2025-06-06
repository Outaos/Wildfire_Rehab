# 3. IMPORT COLLECTED DATA

import arcpy
import os

def add_shapefiles_to_group(fire_number, input_folder):
    # Check if the input folder exists
    if not os.path.exists(input_folder):
        arcpy.AddError(f"The input folder '{input_folder}' does not exist.")
        return

    # Access the current project and active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap

    # Create a new group layer for the shapefiles
    group_layer_name = f"{fire_number}_Input"
    group_layer_exists = any(
        lyr.name == group_layer_name for lyr in map_obj.listLayers() if lyr.isGroupLayer
    )

    if not group_layer_exists:
        group_layer = map_obj.createGroupLayer(group_layer_name)
    else:
        # If the group layer exists, get it
        group_layer = next(
            lyr for lyr in map_obj.listLayers() if lyr.isGroupLayer and lyr.name == group_layer_name
        )

    # Function to add layers directly to the group if they are not already present
    def add_layer_to_group(shapefile_path, group_layer):
        shapefile_name = os.path.basename(shapefile_path)
        layer_name = os.path.splitext(shapefile_name)[0]  # Remove the .shp extension

        # Check if the layer is already in the group
        if not any(lyr.name == layer_name for lyr in group_layer.listLayers()):
            # Add the layer from the path to the map
            new_layer = map_obj.addDataFromPath(shapefile_path)
            # Add the layer to the group layer
            map_obj.addLayerToGroup(group_layer, new_layer)
            # Remove the original layer from the map
            map_obj.removeLayer(new_layer)
            arcpy.AddMessage(f"Added shapefile: {shapefile_name}")
        else:
            arcpy.AddMessage(f"Layer '{layer_name}' already exists in the group layer.")

    # Loop through all shapefiles in the input folder
    shapefiles_added = False
    for file in os.listdir(input_folder):
        if file.lower().endswith(".shp"):
            # Full path to the shapefile
            shapefile_path = os.path.join(input_folder, file)
            
            # Add the shapefile to the group layer
            add_layer_to_group(shapefile_path, group_layer)
            shapefiles_added = True

    if not shapefiles_added:
        arcpy.AddWarning(f"No shapefiles found in the input folder '{input_folder}'.")

    # Save the project to retain changes
    aprx.save()

    arcpy.AddMessage(f"All shapefiles have been added to the '{group_layer_name}' group and project saved.")

if __name__ == "__main__":
    # Get parameters from user
    fire_number = arcpy.GetParameterAsText(0)
    input_folder = arcpy.GetParameterAsText(1)

    # Call the function
    add_shapefiles_to_group(fire_number, input_folder)
