import arcpy
import os
import re

"""
Workflow
4.1 Re-projects and imports additional shapefiles from a specified folder into the
    existing {FIRE_NUMBER}_Input group layer in the current ArcGIS Pro map.

Rules
- Do NOT delete anything already in the Input group.
- If an output name already exists in the default GDB, create a new name by suffixing _1, _2, ...
- Do NOT leave standalone layers outside the Input group (remove them after adding to group).
- Supports inputs in EPSG:4326 (WGS84) and EPSG:3005 (BC Albers).
"""

#############################################################################################
# HELPERS
#############################################################################################

def sanitize_name(name: str) -> str:
    sanitized = re.sub(r"[^\w]+", "_", name)
    if not re.match(r"^[A-Za-z_]", sanitized):
        sanitized = f"_{sanitized}"
    return sanitized

def ensure_group(map_obj, group_layer_name):
    grp = next((l for l in map_obj.listLayers() if l.isGroupLayer and l.name == group_layer_name), None)
    if grp is None:
        grp = map_obj.createGroupLayer(group_layer_name)
    return grp

def group_sources(group_layer):
    """Return a set of normalized dataSource paths already present in the group."""
    sources = set()
    for lyr in group_layer.listLayers():
        try:
            sources.add(os.path.normcase(lyr.dataSource))
        except Exception:
            pass
    return sources

def unique_fc_name(gdb: str, base_name: str) -> str:
    """
    Return a unique feature class name inside gdb:
    base, base_1, base_2, ...
    """
    base = arcpy.ValidateTableName(sanitize_name(base_name), gdb)
    candidate = base
    i = 1
    while arcpy.Exists(os.path.join(gdb, candidate)):
        candidate = arcpy.ValidateTableName(f"{base}_{i}", gdb)
        i += 1
    return candidate

def add_fc_to_group(map_obj, group_layer, fc_path, existing_sources):
    """
    Add fc to map, move into group, remove standalone copy.
    Avoid duplicate dataSources already in group.
    """
    norm = os.path.normcase(fc_path)
    if norm in existing_sources:
        return False

    lyr = map_obj.addDataFromPath(fc_path)              # creates standalone layer
    map_obj.addLayerToGroup(group_layer, lyr, "BOTTOM") # move into group

    # remove standalone layer so it doesn't appear twice
    try:
        map_obj.removeLayer(lyr)
    except Exception:
        pass

    existing_sources.add(norm)
    return True

#############################################################################################
# 4.1 MAIN
#############################################################################################

def add_additional_shapefiles(fire_number, input_folder):
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap
    if not map_obj:
        arcpy.AddError("Step 4.1 No active map found. Open a map and try again.")
        return

    if not os.path.isdir(input_folder):
        arcpy.AddError(f"Step 4.1 Folder does not exist: {input_folder}")
        return

    default_gdb = aprx.defaultGeodatabase
    arcpy.env.workspace = default_gdb

    bc_albers = arcpy.SpatialReference(3005)

    group_layer_name = f"{fire_number}_Input"
    group_layer = ensure_group(map_obj, group_layer_name)
    existing_sources = group_sources(group_layer)

    added = 0
    skipped = 0
    processed = 0

    for fn in os.listdir(input_folder):
        if not fn.lower().endswith(".shp"):
            continue

        shp = os.path.join(input_folder, fn)
        processed += 1

        # Read SR
        try:
            sr = arcpy.Describe(shp).spatialReference
            code = getattr(sr, "factoryCode", None)
        except Exception:
            arcpy.AddWarning(f"Step 4.1 Could not read spatial reference: {fn} (skipping).")
            skipped += 1
            continue

        base = os.path.splitext(fn)[0]

        # Choose unique output name in default GDB (suffix if needed)
        out_name = unique_fc_name(default_gdb, base)
        out_fc = os.path.join(default_gdb, out_name)

        try:
            if code == 4326:
                # Project WGS84 -> BC Albers
                arcpy.AddMessage(f"Step 4.1 Projecting (4326→3005): {fn} → {out_name}")
                arcpy.management.Project(shp, out_fc, bc_albers)

            elif code == 3005:
                # Copy (already BC Albers) into default GDB with unique name
                arcpy.AddMessage(f"Step 4.1 Copying (already 3005): {fn} → {out_name}")
                arcpy.conversion.FeatureClassToFeatureClass(shp, default_gdb, out_name)

            elif code in (None, 0):
                arcpy.AddWarning(f"Step 4.1 {fn} has Unknown spatial reference (skipping).")
                skipped += 1
                continue

            else:
                arcpy.AddMessage(f"Step 4.1 {fn} is EPSG:{code} (skipping; only 4326 or 3005 supported).")
                skipped += 1
                continue

        except Exception as e:
            arcpy.AddWarning(f"Step 4.1 Failed to import {fn}: {e}")
            skipped += 1
            continue

        # Add to Input group and remove standalone copy
        if arcpy.Exists(out_fc):
            if add_fc_to_group(map_obj, group_layer, out_fc, existing_sources):
                added += 1

    aprx.save()
    arcpy.AddMessage(f"Step 4.1 Done. Processed: {processed}. Added to '{group_layer_name}': {added}. Skipped: {skipped}.")

#############################################################################################
# EXECUTION
#############################################################################################

if __name__ == "__main__":
    fire_number = arcpy.GetParameterAsText(0)  
    input_folder = arcpy.GetParameterAsText(1) 

    add_additional_shapefiles(fire_number, input_folder)
