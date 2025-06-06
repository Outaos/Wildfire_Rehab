# 8. COPY DOMAINS BASED ON LOCATION

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
        'Berm Breach (BB)': '2',
        'Berm High (BH)': '43',
        'Cleared Area (CA)': '42',
        'Cross Ditch Culvert Backup (CDB)': '50',
        'Cross Ditch Install (CDI)': '6',
        'Cross Ditch Repair (CDR)': '7',
        'Culvert Clean Repair (CC)': '8',
        'Culvert Insert (CI)': '9',
        'Culvert No Damage (CND)': '51',
        'Culvert Remove and Dispose (CRD)': '52',
        'Ditch Clean Repair (DCR)': '14',
        'Ditch Install (DI)': '15',
        'Domestic Water Supply (W)': '18',
        'Dry Seed (DS)': '19',
        'Existing Deactivation (ED)': '20',
        'Hazard (H)': '27',
        'Infrastructure No Treatment (INT)': '53',
        'Infrastructure Repair (IR)': '54',
        'Lowbed Turnaround (LBT)': '55',
        'No Treatment Point (NT)': '41',
        'No Work Zone (NWZ)': '56',
        'Other Rehab Treatment Type (ORT)': '46',
        'Point of Commencement Termination (PCT)': '49',
        'Pull Back (PB)': '30',
        'Recontour (RC)': '31',
        'Restore Draw (RD)': '32',
        'Seepage (SG)': '48',
        'Steep Slope (SS)': '36',
        'Stream Crossing Classified (SCC)': '60',
        'Stream Crossing Non Classified (SCN)': '37',
        'Sump (SP)': '38',
        'Unassigned (UN)': '99',
        'Unique Point (UP)': '40',
        'Water Bar (WB)': '39',
        'Wood Bunched (BW)': '47',
        'Wood Burn Pile (BPW)': '34',
        'Wood Decked (DW)': '13'
    }
    domain_mapping = {normalize_label(k): v for k, v in domain_mapping_raw.items()}

    spatial_ref_fc_to_update = arcpy.Describe(fc_to_update).spatialReference
    print(f"Spatial reference: {spatial_ref_fc_to_update.name}")
    arcpy.AddMessage(f"Spatial reference: {spatial_ref_fc_to_update.name}")

    print("Reading source features...")
    arcpy.AddMessage("Reading source features...")

    # Build dict: (X,Y) → {"RPtType1": val1, "RPtType2": val2, "RPtType3": val3}
    source_data = {}
    with arcpy.da.SearchCursor(fc_to_copy, ["SHAPE@", "sym_name", "RPtType2", "RPtType3"]) as cursor:
        for row in cursor:
            point_geom = row[0].projectAs(spatial_ref_fc_to_update)
            coords = (round(point_geom.centroid.X, 3), round(point_geom.centroid.Y, 3))
            source_data[coords] = {
                "RPtType1": row[1],
                "RPtType2": row[2],
                "RPtType3": row[3]
            }

    print(f"{len(source_data)} source points indexed.")
    arcpy.AddMessage(f"{len(source_data)} source points indexed.")

    print("Updating target features...")
    arcpy.AddMessage("Updating target features...")

    updated = 0
    skipped = 0
    fields_to_update = ["RPtType1", "RPtType2", "RPtType3"]

    with arcpy.da.UpdateCursor(fc_to_update, ["SHAPE@"] + fields_to_update) as cursor:
        for row in cursor:
            coords = (round(row[0].centroid.X, 3), round(row[0].centroid.Y, 3))
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
                            print(f"{field} updated from '{source_val}' → '{mapped_val}'")
                            arcpy.AddMessage(f"{field} updated from '{source_val}' → '{mapped_val}'")
                        else:
                            print(f"No domain match for {field}: '{source_val}'")
                            arcpy.AddWarning(f"No domain match for {field}: '{source_val}'")
                            skipped += 1
                if changed:
                    cursor.updateRow(row)
                    updated += 1
            else:
                skipped += 1

    print(f"{updated} rows updated.")
    print(f"{skipped} rows skipped.")
    arcpy.AddMessage(f"{updated} rows updated.")
    arcpy.AddWarning(f"{skipped} rows skipped.")
    print("Done.")
    arcpy.AddMessage("Done.")

# Local test paths
#fc_to_copy = "C90999_Input\\Rehab_Avenza_Picklist_2__BC"
#fc_to_update = "C90999_Original\\wildfireBC_Rehab_Point"


# User inputs from ArcGIS Pro tool
fc_to_copy = arcpy.GetParameterAsText(0) 
fc_to_update = arcpy.GetParameterAsText(1)  
 

# Run the function with the provided parameters
copy_attributes_with_domains(fc_to_copy, fc_to_update)
