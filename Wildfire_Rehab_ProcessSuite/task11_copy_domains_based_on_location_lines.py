import arcpy
import re

def normalize_label(label):
    """Normalize label by removing punctuation, spaces, and lowering case."""
    return re.sub(r'[^a-zA-Z0-9]', '', label).lower()

def copy_attributes_with_domains(fc_to_copy, fc_to_update):
    print("Step 11. Starting attribute copy with domain mapping...")
    arcpy.AddMessage("Step 11. Starting attribute copy with domain mapping...")

    # DOMAIN MAPPING
    domain_mapping_raw = {
        # RLType
        'Clean Ditch (CD)': '1',
        'Dry Seed (DS)': '2',
        'Fence - Damaged (FD)': '3',
        'Fence - Undamaged (FND)': '4',
        'Danger Tree Treatment Required (DTA)': '14',
        'Grade Road (GR)': '5',
        'Pull Back (PB)': '6',
        'Recontour (RC)': '7',
        'Steep Slopes >35% (SS)': '10',
        'No Treatment - Line (NA)': '11',
        'Hazard (H)': '13',
        'Unassigned': '99',
        'Fuel Hazard Treatment Required (FHT)': '15',
        'Division Break': '89',
        'Other Rehab Treatment Type': '16',
        'Road Damage - Requires Repair (RR)': '9',
        'Ditch Clean Repair DCR': '1',
        'Dry Seed DS': '2',
        'Fire Hazard Treatment FHT': '13',
        'Grade Road GR': '5',
        'Infrastructure No Treatment INT': '21',
        'Infrastructure Repair IR': '20',
        'No Treatment NT': '11',
        'No Work Zone NWZ': '22',
        'Other Rehab Treatment Type ORT': '16',
        'Pull Back PB': '6',
        'Recontour RC': '7',
        'Steep Slopes SS': '10',

        # FLType
        'Unknown': '0',
        'Active Burnout': '1',
        'Aerial Foam Drop': '2',
        'Aerial Hazard': '3',
        'Aerial Ignition': '4',
        'Aerial Retardant Drop': '5',
        'Aerial Water Drop': '6',
        'Branch Break': '7',
        'Completed Burnout': '8',
        'Completed Machine Line': '9',
        'Completed Handline': '10',
        'Completed Line': '11',
        'Division Break': '12',
        'Danger Tree Assessed': '13',
        'Danger Tree Assessed/Felled': '14',
        'Escape Route': '15',
        'Fire Break Planned or Incomplete': '16',
        'Fire Spread Prediction': '17',
        'Highlighted Geographic Feature': '18',
        'Highlighted Manmade Feature': '19',
        'Line Break Complete': '20',
        'Planned Fire Line': '21',
        'Planned Secondary Line': '22',
        'Proposed Burnout': '23',
        'Proposed Machine Line': '24',
        'Trigger Point': '25',
        'Uncontrolled Fire Edge': '26',
        'Other': '27',
        'Contingency Line': '28',
        'No Work Zone': '29',
        'Completed Fuel Free Line': '30',
        'Road - Modified Existing': '32',
        'Trail': '34',
        'Road': '31',
        'Road - Heavily Used': '33',
        'Pipeline': '35',
        'Completed Hoselay': '36',
        'Containment / Control Line': '37',
        'Containment Control Line': '37',
        'Completed Line': '11',
        'Completed Fuel Free Line FF': '30',
        'Completed Handline HL': '10',
        'Completed Machine Line MG': '9',
        'Road Heavily Used RHU': '33',
        'Road Modified Existing REM': '32',
        'Trail TR': '34',

        # Line Width
        '5m': '0',
        '10m': '1',
        '15m': '2',
        '20m and wider': '3',

        # AvgSlope
        '0 to 15': '0',
        '16 to 25': '1',
        '26 to 35': '2',
        'above 35': '3'
    }

    domain_mapping = {normalize_label(k): v for k, v in domain_mapping_raw.items()}

    spatial_ref_fc_to_update = arcpy.Describe(fc_to_update).spatialReference
    print(f"Step 11. Spatial reference: {spatial_ref_fc_to_update.name}")
    arcpy.AddMessage(f"Step 11. Spatial reference: {spatial_ref_fc_to_update.name}")

    print("Step 11. Reading source features...")
    arcpy.AddMessage("Step 11. Reading source features...")

    # Step 1: Check which fields exist in fc_to_copy
    all_fields = [f.name for f in arcpy.ListFields(fc_to_copy)]
    print("Step 11. Available fields:", all_fields)
    arcpy.AddMessage(f"Step 11. Available fields: {all_fields}")

    # Always required fields
    optional_fields = ["RLType", "RLType2", "RLType_2", "RLType3", "RLType_3", "FLType", "FLType2", "LineWidth", "AvgSlope"]
    fields = ["SHAPE@"] + [f for f in optional_fields if f in all_fields] + ["sym_name"]
    field_indices = {f: i for i, f in enumerate(fields)}

    # Step 2: Build source_data
    source_data = {}
    with arcpy.da.SearchCursor(fc_to_copy, fields) as cursor:
        for row in cursor:
            geom = row[field_indices["SHAPE@"]].projectAs(spatial_ref_fc_to_update)
            first_vertex = (round(geom.firstPoint.X, 3), round(geom.firstPoint.Y, 3))
            last_vertex = (round(geom.lastPoint.X, 3), round(geom.lastPoint.Y, 3))
            coords = (first_vertex, last_vertex)

            sym_name = row[field_indices["sym_name"]]

            def get_val(field):
                if field in field_indices:
                    val = row[field_indices[field]]
                    return val if val and str(val).strip() else sym_name
                else:
                    return sym_name if field in ["RLType", "FLType"] else None

            source_data[coords] = {
                "RLType": get_val("RLType"),
                "RLType2": get_val("RLType2") or get_val("RLType_2"),
                "RLType3": get_val("RLType3") or get_val("RLType_3"),
                "FLType": get_val("FLType"),
                "FLType2": get_val("FLType2"),
                "LineWidth": get_val("LineWidth"),
                "AvgSlope": get_val("AvgSlope"),
            }

    print(f"Step 11. {len(source_data)} source points indexed.")
    arcpy.AddMessage(f"Step 11. {len(source_data)} source points indexed.")

    print("Step 11. Updating target features...")
    arcpy.AddMessage("Step 11. Updating target features...")

    # Step 3: Handle update cursor with dynamic field detection
    update_fields_all = [f.name for f in arcpy.ListFields(fc_to_update)]
    preferred_field_names = [
        "RLType",
        "RLType2" if "RLType2" in update_fields_all else "RLType_2",
        "RLType3" if "RLType3" in update_fields_all else "RLType_3",
        "FLType",
        "FLType2",
        "LineWidth",
        "AvgSlope"
    ]
    fields_to_update = [f for f in preferred_field_names if f in update_fields_all]

    print(f"Step 11. Target fields to update: {fields_to_update}")
    arcpy.AddMessage(f"Step 11. Target fields to update: {fields_to_update}")

    updated = 0
    skipped = 0

    with arcpy.da.UpdateCursor(fc_to_update, ["SHAPE@"] + fields_to_update) as cursor:
        for row in cursor:
            first_vertex = (round(row[0].firstPoint.X, 3), round(row[0].firstPoint.Y, 3))
            last_vertex = (round(row[0].lastPoint.X, 3), round(row[0].lastPoint.Y, 3))
            coords = (first_vertex, last_vertex)

            if coords in source_data:
                changed = False
                for i, field in enumerate(fields_to_update):
                    source_val = source_data[coords].get(field)
                    if source_val:
                        source_val_str = str(source_val).strip()
                        normalized = normalize_label(source_val_str)
                        print(f"------DEBUG: Normalized '{source_val_str}' → '{normalized}'")
                        mapped_val = domain_mapping.get(normalized)
                        if mapped_val:
                            row[i + 1] = mapped_val
                            changed = True
                            print(f"Step 11. {field} updated from '{source_val}' → '{mapped_val}'")
                            arcpy.AddMessage(f"Step 11. {field} updated from '{source_val}' → '{mapped_val}'")
                        else:
                            print(f"Step 11. No domain match for {field}: '{source_val}'")
                            arcpy.AddWarning(f"Step 11. No domain match for {field}: '{source_val}'")
                            skipped += 1
                if changed:
                    cursor.updateRow(row)
                    updated += 1
            else:
                skipped += 1

    print(f"Step 11. {updated} rows updated.")
    print(f"Step 11. {skipped} rows skipped.")
    arcpy.AddMessage(f"Step 11. {updated} rows updated.")
    arcpy.AddWarning(f"Step 11. {skipped} rows skipped.")
    print("Step 11. Done.")
    arcpy.AddMessage("Step 11. Done.")

# Example call
fc_to_copy = arcpy.GetParameterAsText(0)
fc_to_update = arcpy.GetParameterAsText(1)

copy_attributes_with_domains(fc_to_copy, fc_to_update)
