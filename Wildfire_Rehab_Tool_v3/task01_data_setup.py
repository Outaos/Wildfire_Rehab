import arcpy
import os
import re

"""
Workflow
1.1 Creates a backup of the Rehab geodatabase for a given fire number and year.
1.2 Adds point and line rehab feature classes to a group layer in the current ArcGIS Pro map.
1.3 Re-projects and imports all shapefiles from a specified folder into a group layer in the current ArcGIS Pro map.

"""
#############################################################################################
# 1.0 HELPERS
#############################################################################################
def _get_fire_context(fire_year, fire_number, step_label):
    """
    Shared: derive fire_code + district, and validate district code.
    step_label should be like 'Step 1.1' or 'Step 1.2' for clean errors.
    """
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
        raise ValueError(f"{step_label} Unknown district code '{district_code}' in fire_number '{fire_number}'")

    return fire_code, district_code, fire_district


def _get_rehab_gdb_paths(fire_year, fire_number, fire_district, fire_code):
    """
    Shared: build input/output gdb paths.
    TEST vs PROD switching is handled here (single place).
    """

    # Set this ONCE here (flip to False when going live)
    use_test_paths = False

    # Define input and output paths
    if use_test_paths:
        # TEST locations
        input_gdb = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Rehab\TEST_for_script\C59999\Data\{fire_number}_Rehab.gdb"
        output_gdb = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Rehab\TEST_for_script\C59999\Data\{fire_number}_Rehab_Backup.gdb"
        gdb_path  = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Rehab\TEST_for_script\C59999\Data\{fire_number}_Rehab.gdb"
        return input_gdb, output_gdb, gdb_path

    #input_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    #output_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\Outgoing\{fire_number}_Rehab_Backup.gdb"

    #input_gdb = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Scripts\Rehab\Wildfire_Rehab_GitHub\Wildfire_Rehab_ProcessSuite\FireSeasonWork_Test\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    #output_gdb = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Scripts\Rehab\Wildfire_Rehab_GitHub\Wildfire_Rehab_ProcessSuite\FireSeasonWork_Test\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\Outgoing\{fire_number}_Rehab_Backup.gdb"

    input_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    output_gdb = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\Outgoing\{fire_number}_Rehab_Backup.gdb"
    gdb_path = input_gdb
    return input_gdb, output_gdb, gdb_path


#############################################################################################
# 1.1 CREATE A BACKUP
#############################################################################################
# --> fire_year & fire_code are temporarily inactive because of the test run
def backup_gdb(fire_year, fire_number):
    # Check if GDB has a fire_number
    if "FIRENUMBER" in fire_number.upper():
        msg = "Step 1.1 Please update the geodatabase name, as it is currently set to FIRENUMBER_Rehab.gdb and the fire number has not been specified."
        arcpy.AddError(msg)
        print(msg)
        return

    fire_code, district_code, fire_district = _get_fire_context(fire_year, fire_number, "Step 1.1")
    input_gdb, output_gdb, _ = _get_rehab_gdb_paths(fire_year, fire_number, fire_district, fire_code)

    # Perform the copy operation
    arcpy.Copy_management(input_gdb, output_gdb)

    print("Step 1.1 Backup completed successfully.")





#############################################################################################
# 1.2 ADD EXISTING POINTS AND LINES FROM REHAB GDB
#############################################################################################
def add_layers_to_group(fire_year, fire_number):
    # Set the Project and Map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap

    fire_code, _, fire_district = _get_fire_context(fire_year, fire_number, "Step 1.2")
    _, _, gdb_path = _get_rehab_gdb_paths(fire_year, fire_number, fire_district, fire_code)

    # Define the path to the GeoDatabase and feature dataset
    #gdb_path = fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    # TEST locations
    #gdb_path = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Rehab\TEST_for_script\C59999\Data\{fire_number}_Rehab.gdb"
    #gdb_path = fr"\\spatialfiles.bcgov\work\srm\wml\Workarea\ofedyshy\Scripts\Rehab\Wildfire_Rehab_GitHub\Wildfire_Rehab_ProcessSuite\FireSeasonWork_Test\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"
    feature_dataset = "wildfireBC_Rehab"

    # Check if the GeoDatabase exists
    if not arcpy.Exists(gdb_path):
        arcpy.AddError(f"Step 1.2 The GeoDatabase '{gdb_path}' does not exist.")
        return

    # Try lowercase version first
    fc_points = os.path.join(gdb_path, feature_dataset, "wildfireBC_rehabPoint")
    fc_lines = os.path.join(gdb_path, feature_dataset, "wildfireBC_rehabLine")

    # If not found, try 2025-style naming
    if not arcpy.Exists(fc_points) or not arcpy.Exists(fc_lines):
        fc_points_alt = os.path.join(gdb_path, feature_dataset, "wildfireBC_Rehab_Point")
        fc_lines_alt = os.path.join(gdb_path, feature_dataset, "wildfireBC_Rehab_Line")

        if arcpy.Exists(fc_points_alt) and arcpy.Exists(fc_lines_alt):
            fc_points, fc_lines = fc_points_alt, fc_lines_alt
        else:
            if not arcpy.Exists(fc_points) and not arcpy.Exists(fc_points_alt):
                arcpy.AddError(f"Step 1.2 Neither 'wildfireBC_rehabPoint' nor 'wildfireBC_Rehab_Point' exist in: {gdb_path}")
            if not arcpy.Exists(fc_lines) and not arcpy.Exists(fc_lines_alt):
                arcpy.AddError(f"Step 1.2 Neither 'wildfireBC_rehabLine' nor 'wildfireBC_Rehab_Line' exist in: {gdb_path}")
            return

    group_layer_name = f"{fire_number}_Master"
    group_layer = next((lyr for lyr in map_obj.listLayers() if lyr.isGroupLayer and lyr.name == group_layer_name), None)

    if group_layer is None:
        group_layer = map_obj.createGroupLayer(group_layer_name)

        def add_layer_to_group(fc_path, layer_name):
            if not any(lyr.name == layer_name for lyr in group_layer.listLayers()):
                tmp = map_obj.addDataFromPath(fc_path)
                map_obj.addLayerToGroup(group_layer, tmp, "BOTTOM")
                map_obj.removeLayer(tmp)

        add_layer_to_group(fc_points, "wildfireBC_Rehab_Point")
        add_layer_to_group(fc_lines, "wildfireBC_Rehab_Line")

        aprx.save()
        arcpy.AddMessage(f"Step 1.2 Layers added directly to '{group_layer_name}' group, standalone layers avoided.")
    else:
        arcpy.AddWarning(f"'Step 1.2 {group_layer_name}' group already exists. No layers were added.\nPlease update: 'FIRE_NUMBER' if needed")

    return




#############################################################################################
# 1.3 RE-PROJECT LAYERS INTO BC ALBERS AND IMPOPRT COLLECTED DATA
#############################################################################################

def sanitize_name(name):
    sanitized = re.sub(r"[^\w]+", "_", name)
    if not re.match(r"^[A-Za-z_]", sanitized):
        sanitized = f"_{sanitized}"
    return sanitized

def ensure_group(map_obj, group_layer_name):
    grp = next((l for l in map_obj.listLayers() if l.isGroupLayer and l.name == group_layer_name), None)
    if grp is None:
        grp = map_obj.createGroupLayer(group_layer_name)
    return grp

def reproject_shapefiles_batch(fire_number, collected_data_folder, add_outputs_to_group=True):
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    map_obj = aprx.activeMap

    # use project's default GDB
    default_gdb = aprx.defaultGeodatabase
    arcpy.env.workspace = default_gdb

    bc_albers = arcpy.SpatialReference(3005)

    # Collect shapefiles that are actually WGS84
    shp_paths = []
    out_names = []

    for fn in os.listdir(collected_data_folder):
        if not fn.lower().endswith(".shp"):
            continue

        shp = os.path.join(collected_data_folder, fn)

        try:
            sr = arcpy.Describe(shp).spatialReference
            if getattr(sr, "factoryCode", None) != 4326:
                arcpy.AddMessage(f"Step 1.3 {fn} not WGS84, skipping.")
                continue
        except Exception:
            arcpy.AddWarning(f"Step 1.3 Could not read spatial reference: {fn}")
            continue

        base = os.path.splitext(fn)[0]
        out_name = arcpy.ValidateTableName(f"{sanitize_name(base)}_BC", default_gdb)

        shp_paths.append(shp)
        out_names.append(out_name)

    if not shp_paths:
        arcpy.AddWarning("Step 1.3 No WGS84 shapefiles found.")
        return

    # Remove existing outputs to avoid collisions
    for out_name in out_names:
        out_fc = os.path.join(default_gdb, out_name)
        if arcpy.Exists(out_fc):
            arcpy.Delete_management(out_fc)

    # 🚀 One GP call instead of many
    arcpy.AddMessage(
        f"Step 1.3 BatchProject: {len(shp_paths)} shapefiles → {os.path.basename(default_gdb)}"
    )

    try:
        # Most robust across ArcGIS Pro versions
        arcpy.management.BatchProject(shp_paths, default_gdb, bc_albers)
    except TypeError:
        # Fallback: some installs use different keyword names
        arcpy.management.BatchProject(
            shp_paths,
            default_gdb,
            bc_albers
        )

    # Optional: add outputs to map/group
    if add_outputs_to_group:
        group_layer_name = f"{fire_number}_Input"
        group_layer = next(
            (l for l in map_obj.listLayers() if l.isGroupLayer and l.name == group_layer_name),
            None
        ) or map_obj.createGroupLayer(group_layer_name)

        # Build list of actual/expected outputs from inputs (dedup)
        expected_out_fcs = []
        seen = set()

        for shp in shp_paths:
            base = os.path.splitext(os.path.basename(shp))[0]

            # BatchProject usually keeps the base name
            name1 = arcpy.ValidateTableName(base, default_gdb)
            fc1 = os.path.join(default_gdb, name1)

            # Your preferred naming (base_BC) - fallback
            name2 = arcpy.ValidateTableName(f"{sanitize_name(base)}_BC", default_gdb)
            fc2 = os.path.join(default_gdb, name2)

            for fc in (fc1, fc2):
                if fc not in seen:
                    expected_out_fcs.append(fc)
                    seen.add(fc)

        # Existing layer sources in group (avoid duplicates)
        existing_sources = set()
        for lyr in group_layer.listLayers():
            try:
                existing_sources.add(os.path.normcase(lyr.dataSource))
            except Exception:
                pass

        added = 0
        for out_fc in expected_out_fcs:
            if arcpy.Exists(out_fc):
                if os.path.normcase(out_fc) in existing_sources:
                    continue

                lyr = map_obj.addDataFromPath(out_fc)
                # Add to group
                map_obj.addLayerToGroup(group_layer, lyr, "BOTTOM")
                # Remove the standalone layer that addDataFromPath created
                try:
                    map_obj.removeLayer(lyr)
                except Exception:
                    pass
                added += 1

        if added == 0:
            arcpy.AddWarning(
                "Step 1.3 No new projected outputs were added to the group. "
                "Either outputs weren't found, or they were already present."
            )
        else:
            arcpy.AddMessage(f"Step 1.3 Added {added} projected layer(s) to '{group_layer_name}'.")



    aprx.save()
    arcpy.AddMessage("Step 1.3 Reprojection complete.")

    





#############################################################################################
# EXECUTION
#############################################################################################
if __name__ == "__main__":
    fire_year = arcpy.GetParameterAsText(0)
    fire_number = arcpy.GetParameterAsText(1)
    collected_data_folder = arcpy.GetParameterAsText(2)
    create_backup = arcpy.GetParameter(3)

    # Call the backup function
    if create_backup:
        backup_gdb(fire_year, fire_number)
    else:
        arcpy.AddMessage("Step 1.1 Backup skipped.")
    add_layers_to_group(fire_year, fire_number)
    reproject_shapefiles_batch(fire_number, collected_data_folder, add_outputs_to_group=True)



    

