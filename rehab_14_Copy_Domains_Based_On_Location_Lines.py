import arcpy
import re

def normalize_label(label):
    """Normalize label by removing punctuation, spaces, and lowering case."""
    return re.sub(r'[^a-zA-Z0-9]', '', label).lower()

def copy_attributes_with_domains(fc_to_copy, fc_to_update):
    print("Starting attribute copy with domain mapping...")
    arcpy.AddMessage("Starting attribute copy with domain mapping...")

    # DOMAIN MAPPING
    domain_mapping_raw = {
        # RLType1 or RLType2
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
        # FLType1
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
        # Line Width
        # '1m': '0',   <--------------------------- this will need to be added later
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
    print(f"Spatial reference: {spatial_ref_fc_to_update.name}")
    arcpy.AddMessage(f"Spatial reference: {spatial_ref_fc_to_update.name}")

    print("Reading source features...")
    arcpy.AddMessage("Reading source features...")

    # Build dict: (X,Y) -> {"RPtType1": val1, "RPtType2": val2, "RPtType3": val3}
    source_data = {}
    with arcpy.da.SearchCursor(fc_to_copy, ["SHAPE@", "RLType1", "RLType2","RLType3", "FLType1", "FLType2", "LineWidth", "Slope"]) as cursor:
        for row in cursor:
            #point_geom = row[0].projectAs(spatial_ref_fc_to_update)
            #coords = (round(point_geom.centroid.X, 3), round(point_geom.centroid.Y, 3))
            projected_line = row[0].projectAs(spatial_ref_fc_to_update)
            first_vertex = (round(projected_line.firstPoint.X, 3), round(projected_line.firstPoint.Y, 3))
            last_vertex = (round(projected_line.lastPoint.X, 3), round(projected_line.lastPoint.Y, 3))
            coords = (first_vertex, last_vertex)
            source_data[coords] = {
                "RLType1": row[1],
                "RLType2": row[2],
                "RLType3": row[3],
                "FLType1": row[4],
                "FLType2": row[5],
                "LineWidth": row[6],
                "AvgSlope": row[7]
            }

    print(f"{len(source_data)} source points indexed.")
    arcpy.AddMessage(f"{len(source_data)} source points indexed.")

    print(" Updating target features...")
    arcpy.AddMessage(" Updating target features...")

    updated = 0
    skipped = 0
    fields_to_update = ["RLType1", "RLType2","RLType3", "FLType1", "FLType2", "LineWidth", "AvgSlope"]

    with arcpy.da.UpdateCursor(fc_to_update, ["SHAPE@"] + fields_to_update) as cursor:
        for row in cursor:
            #coords = (round(row[0].centroid.X, 3), round(row[0].centroid.Y, 3))
            first_vertex = (round(row[0].firstPoint.X, 3), round(row[0].firstPoint.Y, 3))
            last_vertex = (round(row[0].lastPoint.X, 3), round(row[0].lastPoint.Y, 3))
            coords = (first_vertex, last_vertex)
            if coords in source_data:
                changed = False
                for i, field in enumerate(fields_to_update):
                    source_val = source_data[coords].get(field)
                    if source_val:
                        normalized = normalize_label(source_val)
                        mapped_val = domain_mapping.get(normalized)
                        if mapped_val:
                            row[i + 1] = mapped_val
                            changed = True
                            print(f" {field} updated from '{source_val}' -> '{mapped_val}'")
                            arcpy.AddMessage(f" {field} updated from '{source_val}' -> '{mapped_val}'")
                        else:
                            print(f" No domain match for {field}: '{source_val}'")
                            arcpy.AddWarning(f" No domain match for {field}: '{source_val}'")
                            skipped += 1
                if changed:
                    cursor.updateRow(row)
                    updated += 1
            else:
                skipped += 1

    print(f"{updated} rows updated.")
    print(f" {skipped} rows skipped.")
    arcpy.AddMessage(f"{updated} rows updated.")
    arcpy.AddWarning(f" {skipped} rows skipped.")
    print("Done.")
    arcpy.AddMessage("Done.")

# Local test paths
#fc_to_copy = "C90999_Input\\Rehab_Avenza_Picklist_1__BC"
#fc_to_update = "C90999_Original\\wildfireBC_Rehab_Line"

# Uncomment for tool mode
fc_to_copy = arcpy.GetParameterAsText(0)
fc_to_update = arcpy.GetParameterAsText(1)

copy_attributes_with_domains(fc_to_copy, fc_to_update)
