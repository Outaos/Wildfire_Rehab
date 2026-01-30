# -*- coding: utf-8 -*-
import os
import arcpy


def get_bool_param(i: int, default: bool) -> bool:
    v = arcpy.GetParameterAsText(i)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip().lower() in ("true", "t", "1", "yes", "y")


def district_to_region(fire_number: str) -> str:
    district_map = {
        "C": "Cariboo",
        "V": "Coastal",
        "K": "Kamloops",
        "R": "NorthWest",
        "G": "PrinceGeorge",
        "N": "SouthEast"
    }
    code = fire_number[0].upper()
    region = district_map.get(code)
    if not region:
        raise ValueError(f"Unknown district code '{code}' in fire_number '{fire_number}'")
    return region


def default_kml_folder(fire_year: str, fire_number: str) -> str:
    region = district_to_region(fire_number)
    fire_code = fire_number[:2]
    return fr"\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{fire_year}\{region}\{fire_code}\{fire_number}\Outputs\KML"


def ensure_folder(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def get_map(aprx, map_name: str):
    matches = aprx.listMaps(map_name)
    if not matches:
        available = [m.name for m in aprx.listMaps()]
        raise RuntimeError(
            f"Map '{map_name}' not found in CURRENT project.\n"
            f"Available maps:\n- " + "\n- ".join(available)
        )
    return matches[0]


def get_layer_by_name(m, layer_name: str):
    layers = m.listLayers(layer_name)
    if not layers:
        raise RuntimeError(f"Layer '{layer_name}' not found in map '{m.name}'.")
    return layers[0]


def blank_comments_in_fc(fc_path: str):
    """Blank Comments in OUTPUT only (safe)."""
    fields = {f.name for f in arcpy.ListFields(fc_path)}
    if "Comments" not in fields:
        return
    with arcpy.da.UpdateCursor(fc_path, ["Comments"]) as cur:
        for row in cur:
            row[0] = None
            cur.updateRow(row)


def export_layer_selected(layer, out_shp: str, where_clause: str, blank_comments: bool):
    tmp = arcpy.management.MakeFeatureLayer(layer, "tmp_export_layer", where_clause).getOutput(0)
    arcpy.management.CopyFeatures(tmp, out_shp)
    arcpy.management.Delete(tmp)

    if blank_comments:
        blank_comments_in_fc(out_shp)


def main():
    arcpy.env.addOutputsToMap = False

    # --------------------------
    # Parameters
    # --------------------------
    fire_year = arcpy.GetParameterAsText(0)
    fire_number = arcpy.GetParameterAsText(1)
    map_choice = arcpy.GetParameterAsText(2)

    do_shp = get_bool_param(3, True)
    do_kmz = get_bool_param(4, True)

    if not fire_year or not fire_number or not map_choice:
        raise ValueError("Fire Year, Fire Number, and Map Choice are required.")

    if not do_shp and not do_kmz:
        raise ValueError("At least one of Export Shapefile / Export KMZ must be True.")

    # --------------------------
    # Workspace = CURRENT project's default gdb
    # --------------------------
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    default_gdb = aprx.defaultGeodatabase
    if not default_gdb or not arcpy.Exists(default_gdb):
        raise RuntimeError("Could not resolve the CURRENT project's default geodatabase.")
    arcpy.env.workspace = default_gdb

    # --------------------------
    # Output folder
    # --------------------------
    output_folder = default_kml_folder(fire_year, fire_number)
    ensure_folder(output_folder)

    # Exclude retired features
    where_clause = "\"Status\" <> 'Retired'"

    # --------------------------
    # What to export (layer names must exist in the chosen map)
    # --------------------------
    exports = {
        "Rehab Point Treatment [RPtType]": f"{fire_number}_Points",
        "Fireline OPS Type [FLType]": f"{fire_number}_Lines_FLType",
        "Rehab Line Treatment [RLType]": f"{fire_number}_Lines_RLType1",
    }

    # You previously blanked comments; keep that behaviour but ONLY on outputs.
    blank_comments = True

    # --------------------------
    # Resolve map + export
    # --------------------------
    m = get_map(aprx, map_choice)

    arcpy.AddMessage(f"Default GDB: {default_gdb}")
    arcpy.AddMessage(f"Map: {m.name}")
    arcpy.AddMessage(f"Output folder: {output_folder}")

    for layer_name, out_base in exports.items():
        try:
            lyr = get_layer_by_name(m, layer_name)

            shp_path = os.path.join(output_folder, out_base + ".shp")
            kmz_path = os.path.join(output_folder, out_base + ".kmz")

            # 1) Export SHP (optional)
            if do_shp:
                export_layer_selected(lyr, shp_path, where_clause, blank_comments)
                arcpy.AddMessage(f"✅ SHP: {shp_path}")

            # 2) Export KMZ (optional)
            if do_kmz:
                # If SHP was made, use it for KMZ (so Comments are blank there too)
                if do_shp and arcpy.Exists(shp_path):
                    kml_layer = arcpy.management.MakeFeatureLayer(shp_path, "tmp_kml_layer").getOutput(0)
                else:
                    kml_layer = arcpy.management.MakeFeatureLayer(lyr, "tmp_kml_layer", where_clause).getOutput(0)

                arcpy.conversion.LayerToKML(kml_layer, kmz_path)
                arcpy.management.Delete(kml_layer)
                arcpy.AddMessage(f"✅ KMZ: {kmz_path}")

        except arcpy.ExecuteError:
            arcpy.AddWarning(f"ArcPy error for '{layer_name}':\n{arcpy.GetMessages(2)}")
        except Exception as e:
            arcpy.AddWarning(f"Error for '{layer_name}': {e}")

    arcpy.AddMessage("✅ Export complete!")


if __name__ == "__main__":
    main()
