import arcpy
import re

#################################################################################
# 12. Copy Domains Based On Location - Lines
#################################################################################


def normalize_label(label):
    """Normalize label by removing punctuation, spaces, and lowering case."""
    return re.sub(r'[^a-zA-Z0-9]', '', label).lower()

def copy_attributes_with_domains_lines(lines_to_copy, wildfire_lines):
    print("Step 12. Starting attribute copy with domain mapping...")
    arcpy.AddMessage("Step 12. Starting attribute copy with domain mapping...")

    # DOMAIN MAPPING
    domain_mapping_raw = {
        # RLType1 or RLType2
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

        'No Treatment Line NT': '11',
        
        # FLType1
        'Completed Line': '11',
        'Containment Control Line': '37',
        'Contingency Line': '28',
        'Fire Break Planned or Incomplete': '16',
        'Line Break Complete': '20',
        'No Work Zone': '29',
        'Planned Fire Line': '21',
        'Planned Secondary Line': '22',
        'Proposed Machine Line': '24',
        'Completed Fuel Free Line FF': '30',
        'Completed Handline HL': '10',
        'Completed Machine Line MG': '9',
        'Road Heavily Used RHU': '33',
        'Road Modified Existing REM': '32',
        'Trail TR': '34',

        'Completed Line': '11',
        'Containment Control Line': '37',
        'Contingency Line': '28',
        'Fire Break Planned or Incomplete': '16',
        'Line Break Complete': '20',
        'No Work Zone': '29',
        'Planned Fire Line': '21',
        'Planned Secondary Line': '22',
        'Proposed Machine Line': '24',
        'Completed Fuel Free Line': '30',
        'Completed Handline': '10',
        'Completed Machine Line': '9',
        'Road Heavily Used': '33',
        'Road Modified Existing': '32',
        'Trail': '34',

        # Line Width
        '1m': '0',   
        '5m': '1',
        '10m': '2',
        '15m': '3',
        '20m and wider': '4',

        # AvgSlope
        '0 to 15': '0',
        '16 to 25': '1',
        '26 to 35': '2',
        'above 35': '3'
    }

    domain_mapping = {normalize_label(k): v for k, v in domain_mapping_raw.items()}

    spatial_ref_wildfire_lines = arcpy.Describe(wildfire_lines).spatialReference
    print(f"Step 12. Spatial reference: {spatial_ref_wildfire_lines.name}")
    arcpy.AddMessage(f"Step 12. Spatial reference: {spatial_ref_wildfire_lines.name}")

    print("Step 12. Reading source features...")
    arcpy.AddMessage("Step 12. Reading source features...")

    # Build dict: (X,Y) -> {"RPtType1": val1, "RPtType2": val2, "RPtType3": val3}
    source_data = {}
    with arcpy.da.SearchCursor(lines_to_copy, ["SHAPE@", "RLType1", "RLType2","RLType3", "FLType1", "FLType2", "LineWidth", "AvgSlope"]) as cursor:
        for row in cursor:
            #point_geom = row[0].projectAs(spatial_ref_wildfire_lines)
            #coords = (round(point_geom.centroid.X, 3), round(point_geom.centroid.Y, 3))
            projected_line = row[0].projectAs(spatial_ref_wildfire_lines)
            first_vertex = (round(projected_line.firstPoint.X, 3), round(projected_line.firstPoint.Y, 3))
            last_vertex = (round(projected_line.lastPoint.X, 3), round(projected_line.lastPoint.Y, 3))
            coords = (first_vertex, last_vertex)
            source_data[coords] = {
                "RLType": row[1],
                "RLType2": row[2],
                "RLType3": row[3],
                "FLType": row[4],
                "FLType2": row[5],
                "LineWidth": row[6],
                "AvgSlope": row[7]
            }

    print(f"Step 12. {len(source_data)} source points indexed.")
    arcpy.AddMessage(f"Step 12. {len(source_data)} source points indexed.")

    print("Step 12. Updating target features...")
    arcpy.AddMessage("Step 12. Updating target features...")

    updated = 0
    skipped = 0
    fields_to_update = ["RLType", "RLType2","RLType3", "FLType", "FLType2", "LineWidth", "AvgSlope"]

    with arcpy.da.UpdateCursor(wildfire_lines, ["SHAPE@"] + fields_to_update) as cursor:
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
                            print(f"Step 12. {field} updated from '{source_val}' -> '{mapped_val}'")
                            arcpy.AddMessage(f"Step 12. {field} updated from '{source_val}' -> '{mapped_val}'")
                        else:
                            print(f"Step 12. No domain match for {field}: '{source_val}'")
                            arcpy.AddWarning(f"Step 12. No domain match for {field}: '{source_val}'")
                            skipped += 1
                if changed:
                    cursor.updateRow(row)
                    updated += 1
            else:
                skipped += 1

    print(f"Step 12. {updated} rows updated.")
    print(f"Step 12. {skipped} rows skipped.")
    arcpy.AddMessage(f"Step 12. {updated} rows updated.")
    arcpy.AddWarning(f"Step 12. {skipped} rows skipped.")
    print("Step 12. Done.")
    arcpy.AddMessage("Step 12. Done.")