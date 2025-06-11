import arcpy
import re

def locate_and_retrieve(fire_number):
    """
    Locates point and line layers to copy and their respective target layers for update,
    based on group naming and geometry pattern.

    Args:
        fire_number (str): The fire number used to identify relevant input and target layers.

    Returns:
        tuple: (matched_layers_pts, target_lyr, matched_layers_lines, target_lyr_lines)
               or None if any required layer is not found.
    """

    group_input_layer_name = f"{fire_number}_Input"
    pattern = r'^[A-Za-z0-9_]+_BC$'

    group_target_layer_name = f"{fire_number}_Master"
    source_layer_name_pts = "wildfireBC_Rehab_Point"
    source_layer_name_lines = "wildfireBC_Rehab_Line"

    # Get the current project and active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap

    if not active_map:
        arcpy.AddError("No active map found. Open a map in ArcGIS Pro before running.")
        return None

    # --- Locate the INPUT group layer ---
    input_group_lyr = next(
        (lyr for lyr in active_map.listLayers()
         if lyr.isGroupLayer and lyr.name == group_input_layer_name),
        None
    )

    if not input_group_lyr:
        arcpy.AddError(f"Group layer '{group_input_layer_name}' (Input) not found.")
        return None

    # --- POINTS to COPY ---
    matched_layers_pts = []
    for lyr in input_group_lyr.listLayers():
        if re.match(pattern, lyr.name):
            desc = arcpy.Describe(lyr.dataSource)
            if desc.shapeType == "Point":
                matched_layers_pts.append(lyr)
            else:
                arcpy.AddMessage(f"Skipping '{lyr.name}' (shapeType = {desc.shapeType}).")

    if not matched_layers_pts:
        arcpy.AddError(f"No point sublayers in '{group_input_layer_name}' match pattern '{pattern}'.")
        return None
    else:
        arcpy.AddMessage(f"Found {len(matched_layers_pts)} point layer(s) in '{group_input_layer_name}'.")

    # --- POINTS to UPDATE ---
    target_group_lyr = next(
        (lyr for lyr in active_map.listLayers()
         if lyr.isGroupLayer and lyr.name == group_target_layer_name),
        None
    )

    if not target_group_lyr:
        arcpy.AddError(f"Group layer '{group_target_layer_name}' (Target) not found.")
        return None

    target_lyr = next(
        (lyr for lyr in target_group_lyr.listLayers()
         if lyr.name == source_layer_name_pts),
        None
    )

    if not target_lyr:
        arcpy.AddError(f"Sublayer '{source_layer_name_pts}' not found in group '{group_target_layer_name}'.")
        return None

    if not target_lyr.isFeatureLayer:
        arcpy.AddError(f"'{source_layer_name_pts}' is not a feature layer.")
        return None

    # --- LINES to COPY ---
    matched_layers_lines = []
    for lyr in input_group_lyr.listLayers():
        if re.match(pattern, lyr.name):
            desc = arcpy.Describe(lyr.dataSource)
            if desc.shapeType == "Polyline":
                matched_layers_lines.append(lyr)
            else:
                arcpy.AddMessage(f"Skipping '{lyr.name}' (shapeType = {desc.shapeType}).")

    if not matched_layers_lines:
        arcpy.AddError(f"No line sublayers in '{group_input_layer_name}' match pattern '{pattern}'.")
        return None
    else:
        arcpy.AddMessage(f"Found {len(matched_layers_lines)} line layer(s) in '{group_input_layer_name}'.")

    # --- LINES to UPDATE ---
    target_lyr_lines = next(
        (lyr for lyr in target_group_lyr.listLayers()
         if lyr.name == source_layer_name_lines),
        None
    )

    if not target_lyr_lines:
        arcpy.AddError(f"Sublayer '{source_layer_name_lines}' not found in group '{group_target_layer_name}'.")
        return None

    if not target_lyr_lines.isFeatureLayer:
        arcpy.AddError(f"'{source_layer_name_lines}' is not a feature layer.")
        return None

    # --- Return located layers ---
    return matched_layers_pts, target_lyr, matched_layers_lines, target_lyr_lines
