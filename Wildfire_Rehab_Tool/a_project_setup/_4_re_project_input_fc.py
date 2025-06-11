"""
Reprojects shapefiles in the '{FIRE_NUMBER}_Input' group layer from WGS 1984 to BC Albers 
and optionally merges reprojected point shapefiles into a single feature class.

For each shapefile in the group:
- If it is in WGS 1984, it is reprojected and added back into the group.
- If it is a point shapefile, it is additionally collected for merging.
- All changes are saved to the current ArcGIS Pro project.

Args:
    fire_number (str): The fire number used to identify the group layer and output naming.

Returns:
    str or None: Path to a merged point feature class (in_memory) if multiple were reprojected,
                    a single path if only one point shapefile was found, or None if none were eligible.
"""

import arcpy
import os
import re

############################
# 4. RE-PROJECT INPUT FC
############################
# Function to sanitize layer names for file output
def sanitize_name(name):
    # Replace invalid characters, including '.', with underscores
    sanitized = re.sub(r'[^\w]+', '_', name)  # '\w' matches [A-Za-z0-9_]
    sanitized = sanitized.replace('.', '_')  # Explicitly replace '.' with '_'
    # Ensure the name starts with a letter or underscore
    if not re.match(r'^[A-Za-z_]', sanitized):
        sanitized = f"_{sanitized}"
    return sanitized

# Main function to reproject shapefiles in a group layer
def reproject_shapefiles_in_group(fire_number):
    # Set the environment workspace to the default geodatabase
    default_gdb = arcpy.env.workspace

    # Define the spatial reference for WGS 1984 and BC Albers
    wgs1984 = arcpy.SpatialReference(4326)  # WGS 1984
    bc_albers = arcpy.SpatialReference(3005)  # NAD 1983 BC Environment Albers

    # Access the current project and map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map = aprx.activeMap

    # Generate the group layer name based on the fire number
    group_layer_name = f"{fire_number}_Input"

    # Find the group layer where the input shapefiles are located
    group_layer = next((lyr for lyr in map.listLayers() if lyr.isGroupLayer and lyr.name == group_layer_name), None)

    if not group_layer:
        arcpy.AddError(f"Step 4. Group layer '{group_layer_name}' not found.")
        return

    # Loop through each layer in the group
    for lyr in group_layer.listLayers():
        # Check if the layer is a shapefile and if it's in WGS 1984
        if lyr.dataSource.endswith(".shp"):
            desc = arcpy.Describe(lyr)

            # Only reproject if the spatial reference is WGS 1984
            if desc.spatialReference.factoryCode == 4326:
                # Sanitize the layer name and create output shapefile name with 'BC' at the end
                sanitized_name = sanitize_name(lyr.name)
                output_name = f"{sanitized_name}_BC"
                output_fc = os.path.join(default_gdb, output_name)

                # Check if the output name is valid
                if arcpy.ValidateTableName(output_name, default_gdb) != output_name:
                    arcpy.AddWarning(f"Step 4. Adjusted output name '{output_name}' is invalid in the geodatabase.")
                    continue  # Skip this layer or handle accordingly

                # Reproject the shapefile to BC Albers
                arcpy.management.Project(lyr.dataSource, output_fc, bc_albers)

                # Add the reprojected shapefile to the same group layer
                new_layer = map.addDataFromPath(output_fc)
                map.addLayerToGroup(group_layer, new_layer)

                # Remove the original layer from the map  <<<<
                map.removeLayer(new_layer)               #<<<<

                arcpy.AddMessage(f"Step 4. Reprojected and added '{output_name}' to group '{group_layer_name}'.")
            else:
                arcpy.AddMessage(f"'Step 4. {lyr.name}' is not in WGS 1984, skipping.")
    
    # Save the project to retain changes
    aprx.save()

    arcpy.AddMessage("Step 4. Reprojection completed for all eligible shapefiles.")


    # RETURN POINT SHAPEFILES
    # Initialize a list to store reprojected point shapefiles
    reprojected_points = []

    # Loop through each layer in the group
    for lyr in group_layer.listLayers():
        # Check if the layer is a shapefile and if it's a point feature class
        if lyr.dataSource.endswith(".shp"):
            desc = arcpy.Describe(lyr)

            if desc.shapeType == "Point" and desc.spatialReference.factoryCode == 4326:
                # Sanitize the layer name and create output shapefile name
                sanitized_name = sanitize_name(lyr.name)
                output_name = f"{sanitized_name}_BC"
                output_fc = os.path.join("in_memory", output_name)

                # Reproject the shapefile to BC Albers
                arcpy.management.Project(lyr.dataSource, output_fc, bc_albers)
                reprojected_points.append(output_fc)

    # If multiple point shapefiles are reprojected, merge them
    if len(reprojected_points) > 1:
        merged_points = os.path.join("in_memory", f"{fire_number}_reprojected_points")
        arcpy.management.Merge(reprojected_points, merged_points)
        arcpy.AddMessage(f"Step 4. Merged {len(reprojected_points)} reprojected point shapefiles into a single feature class.")
        return merged_points

    # If only one point shapefile, return it directly
    elif reprojected_points:
        return reprojected_points[0]

    # If no point shapefiles were reprojected, return None
    arcpy.AddError("Step 4. No point shapefiles were reprojected.")
    return None