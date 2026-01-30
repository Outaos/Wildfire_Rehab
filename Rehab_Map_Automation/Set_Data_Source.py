import os
import arcpy


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def get_fire_district(fire_number: str) -> str:
    """Derive district name from the first character of fire_number."""
    if not fire_number or len(fire_number) < 1:
        raise ValueError("fire_number is empty.")

    district_code = fire_number[0].upper()

    district_map = {
        "C": "Cariboo",
        "V": "Coastal",
        "K": "Kamloops",
        "R": "NorthWest",
        "G": "PrinceGeorge",
        "N": "SouthEast"
    }

    fire_district = district_map.get(district_code)
    if not fire_district:
        raise ValueError(f"Unknown district code '{district_code}' in fire_number '{fire_number}'")

    return fire_district


def build_rehab_gdb_path(fire_year: str, fire_number: str) -> str:
    """Build the standard Rehab.gdb path from year + fire number."""
    fire_code = fire_number[:2]
    fire_district = get_fire_district(fire_number)

    return fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{fire_district}\{fire_code}\{fire_number}\Data\{fire_number}_Rehab.gdb"


def pick_map(aprx: "arcpy.mp.ArcGISProject", map_choice: str) -> "arcpy.mp.Map":
    """
    map_choice can be:
      - "Template_Rehab"
      - "Export_KML_SHP"
    """
    name = (map_choice or "").strip()

    if name not in ("Template_Rehab", "Export_KML_SHP"):
        raise ValueError("Map choice must be either 'Template_Rehab' or 'Export_KML_SHP'.")

    maps = aprx.listMaps(name)
    if not maps:
        raise RuntimeError(f"Map '{name}' not found in the current project.")
    return maps[0]


def update_layer_workspace(layer: "arcpy.mp.Layer", new_gdb: str) -> bool:
    """
    Update a layer to point at a new file geodatabase by modifying connectionProperties.
    Returns True if updated, False if skipped (e.g., unsupported layer type).
    """
    if not layer.supports("CONNECTIONPROPERTIES"):
        return False

    old_props = layer.connectionProperties
    if not isinstance(old_props, dict):
        return False

    # Make a deep-ish copy (nested dicts)
    new_props = dict(old_props)
    new_props["connection_info"] = dict(old_props.get("connection_info", {}))

    # For FGDB connections, the workspace path lives here:
    # new_props["connection_info"]["database"] = r"...\something.gdb"
    if "database" not in new_props["connection_info"]:
        # Some layer types (services, etc.) may not have this
        return False

    new_props["connection_info"]["database"] = new_gdb

    # Apply update
    layer.updateConnectionProperties(old_props, new_props, validate=True)
    return True


def update_fire_perimeter_definition_queries(aprx, fire_number: str):
    """
    Update definition queries for two fire perimeter layers across the project.
    Only touches layers named exactly:
      - Fire Perimeter
      - Fire Perimeter Historic
    """
    target_layers = {"Fire Perimeter", "Fire Perimeter Historic"}
    updated = 0

    # Basic SQL string (file gdb + enterprise gdb both accept single quotes for text)
    where = f"FIRE_NUMBER = '{fire_number}'"

    for m in aprx.listMaps():
        for lyr in m.listLayers():
            if lyr.isFeatureLayer and lyr.name in target_layers:
                lyr.definitionQuery = where
                arcpy.AddMessage(f"Definition query updated for '{lyr.name}' in map '{m.name}': {where}")
                updated += 1

    if updated == 0:
        arcpy.AddWarning("No 'Fire Perimeter' / 'Fire Perimeter Historic' layers found to update.")


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------
def main():
    # Script tool parameters:
    # 0 = Fire Year (e.g., "2025")
    # 1 = Fire Number (e.g., "C51672")
    # 2 = Map Choice ("Template_Rehab" or "Export_KML_SHP")
    # 3 = Optional: semicolon-separated list of layer names (leave blank to use defaults)
    fire_year = arcpy.GetParameterAsText(0)
    fire_number = arcpy.GetParameterAsText(1)
    map_choice = arcpy.GetParameterAsText(2)
    layers_param = arcpy.GetParameterAsText(3)

    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = pick_map(aprx, map_choice)
    # Only do perimeter layer definition queries if Template_Rehab was chosen
    if map_choice == "Template_Rehab":
        update_fire_perimeter_definition_queries(aprx, fire_number)

    if not fire_year or not fire_number:
        raise ValueError("Fire Year and Fire Number are required.")

    # Default layers (your original list)
    default_layer_names = [
        "2 Fireline Point [PTType]",
        "Rehab Point Treatment [RPtType]",
        "Rehab Point Treatment [RPtType2]",
        "Rehab Point Treatment [RPtType3]",
        "Rehab Line Treatment [RLType]",
        "Rehab Line Treatment [RLType2]",
        "Rehab Line Treatment [RLType3]",
        "Fireline OPS Type [FLType]",
        "Fireline OPS Type [FLType2]",
        "Rehab Point [Status]",
        "Rehab Line [Status]"
    ]

    if layers_param and layers_param.strip():
        # Accept either semicolon-separated (common in GP tools) or newline-separated
        raw = layers_param.replace("\n", ";")
        layer_names = [x.strip() for x in raw.split(";") if x.strip()]
    else:
        layer_names = default_layer_names

    # Build new gdb path
    new_gdb = build_rehab_gdb_path(fire_year, fire_number)
    arcpy.AddMessage(f"New data source (GDB): {new_gdb}")

    if not os.path.exists(new_gdb):
        arcpy.AddWarning("The geodatabase path does not exist on disk (yet). "
                         "Update may fail validation depending on your environment.")

    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = pick_map(aprx, map_choice)

    updated = 0
    missing = 0
    skipped = 0

    for layer_name in layer_names:
        layers = m.listLayers(layer_name)
        if not layers:
            arcpy.AddWarning(f"Layer not found in map '{m.name}': {layer_name}")
            missing += 1
            continue

        layer = layers[0]
        try:
            did = update_layer_workspace(layer, new_gdb)
            if did:
                arcpy.AddMessage(f"Updated: {layer_name}")
                updated += 1
            else:
                arcpy.AddWarning(f"Skipped (unsupported or unexpected connectionProperties): {layer_name}")
                skipped += 1
        except Exception as ex:
            arcpy.AddWarning(f"Failed to update '{layer_name}': {ex}")
            skipped += 1

    aprx.save()

    arcpy.AddMessage("--------------------------------------------------")
    arcpy.AddMessage(f"Done. Updated: {updated}, Missing: {missing}, Skipped/Failed: {skipped}")
    arcpy.AddMessage("All data sources update attempt complete.")


if __name__ == "__main__":
    main()
