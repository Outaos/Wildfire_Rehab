import arcpy
import os
import re


############################
# 7. COPY ATTRIBUTES WITH DOMAINS - POINTS
############################



def normalize_label(label):
    """Normalize label by removing punctuation, spaces, and lowering case."""
    return re.sub(r'[^a-zA-Z0-9]', '', label).lower()

def copy_attributes_with_domains(source_lyr, target_lyr):
    """
    Copies domain-related attributes from source_lyr to target_lyr
    by matching point geometries and using a normalized domain mapping.
    """

    if not source_lyr.isFeatureLayer or not target_lyr.isFeatureLayer:
        arcpy.AddError("Step 7. Both source and target must be feature layers.")
        return

    # Determine workspace for edit session
    conn_props = target_lyr.connectionProperties
    if 'connection_info' in conn_props and 'database' in conn_props['connection_info']:
        workspace = conn_props['connection_info']['database']  # SDE
        arcpy.AddMessage(f"Step 7. Workspace (SDE): {workspace}")
    else:
        workspace = os.path.dirname(target_lyr.dataSource)  # FileGDB
        arcpy.AddMessage(f"Step 7. Workspace (FileGDB): {workspace}")

    if not workspace:
        arcpy.AddError("Step 7. Could not determine workspace path.")
        return

    source_path = source_lyr.dataSource
    target_path = target_lyr.dataSource
    target_sr = arcpy.Describe(target_path).spatialReference

    # Domain mapping (raw, unnormalized)
    domain_mapping_raw = {
        'Berm Breach BB': '2',
        'Cross Ditch Install CDI': '6',
        'Cross Ditch Repair CDR': '7',
        'Culvert Clean Repair CC': '8',
        'Culvert Insert CI': '9',
        'Wood Decked DW': '13',
        'Ditch Clean Repair DCR': '14',
        'Ditch Install DI': '15',
        'Domestic Water Supply W': '18',
        'Dry Seed DS': '19',
        'Existing Deactivation ED': '20',
        'Hazard H': '27',
        'Pull Back PB': '30',
        'Recontour RC': '31',
        'Restore Draw RD': '32',
        'Wood Burn Pile BPW': '34',
        'Steep Slope SS': '36',
        'Stream Crossing Non Classified SCN': '37',
        'Sump SP': '38',
        'Water Bar WB': '39',
        'Unique Point UP': '40',
        'No Treatment NT': '41',
        'Cleared Area CA': '42',
        'Berm High BH': '43',
        'Other Rehab Treatment Type ORT': '44',
        'Wood Bunched BW': '47',
        'Seepage SG': '48',
        'Point of Commencement Termination PCT': '49',
        'Cross Ditch Culvert Backup CDB': '50',
        'Culvert No Damage CND': '51',
        'Culvert Remove and Dispose CRD': '52',
        'Infrastructure No Treatment INT': '53',
        'Infrastructure Repair IR': '54',
        'Lowbed Turnaround LBT': '55',
        'No Work Zone NWZ': '56',
        'Stream Crossing Classified SCC': '60',
        'Unassigned UN': '99'
    }
    domain_mapping = {normalize_label(k): v for k, v in domain_mapping_raw.items()}

    # Fields to map: {target_field: source_field}
    field_map = {
        "RPtType": "sym_name",
        "RPtType2": "RPtType2",
        "RPtType3": "RPtType3"
    }

    arcpy.AddMessage("Step 7. Indexing source features...")
    source_data = {}

    with arcpy.da.SearchCursor(source_path, ["SHAPE@"] + list(field_map.values())) as cursor:
        for row in cursor:
            geom = row[0].projectAs(target_sr)
            coords = (round(geom.centroid.X, 3), round(geom.centroid.Y, 3))
            source_data[coords] = dict(zip(field_map.values(), row[1:]))

    arcpy.AddMessage(f"Step 7. {len(source_data)} source points indexed.")

    arcpy.AddMessage("Step 7. Updating target features...")
    updated, skipped = 0, 0

    try:
        with arcpy.da.Editor(workspace):
            with arcpy.da.UpdateCursor(target_path, ["SHAPE@"] + list(field_map.keys())) as cursor:
                for row in cursor:
                    coords = (round(row[0].centroid.X, 3), round(row[0].centroid.Y, 3))
                    if coords not in source_data:
                        skipped += 1
                        continue

                    updated_this_row = False
                    for i, (target_field, source_field) in enumerate(field_map.items(), start=1):
                        val = source_data[coords].get(source_field)
                        if not val:
                            continue
                        normalized = normalize_label(val)
                        domain_val = domain_mapping.get(normalized)
                        if domain_val:
                            row[i] = domain_val
                            updated_this_row = True
                            arcpy.AddMessage(f"7. {target_field} <- '{val}' -> '{domain_val}'")
                        else:
                            arcpy.AddWarning(f"7. No match for {source_field}: '{val}'")

                    if updated_this_row:
                        cursor.updateRow(row)
                        updated += 1

        arcpy.AddMessage(f"Step 7. {updated} features updated.")
        arcpy.AddWarning(f"Step 7. {skipped} features skipped (no match).")
    except Exception as e:
        arcpy.AddError(f"Step 7. Error during editing session: {e}")