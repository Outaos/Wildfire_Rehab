# Step 5
"""
This script defines the LineProcessor class, which performs the following:
- Inserts line geometries into the wildfire rehab line layer
- Transfers matching attribute values based on start/end vertex matching
- Maps and inserts coded domain values (e.g., RLType1) using predefined mappings
- Updates missing values in Fire_Num, Fire_Name, and Status fields
"""

# Wildfire_Rehab_Tool/c_lines/line_processor.py

import arcpy
import os
from a_utils.domain_mappings import LINE_DOMAIN_MAPPING, normalize_label

class LineProcessor:
    def __init__(self, fire_name, fire_number, status):
        self.fire_name = fire_name
        self.fire_number = fire_number
        self.status = status

    def copy_lines(self):
        # This method will be called with target already preloaded
        pass  # Implement later if needed to separate geometry copy logic

    def copy_attributes(self, target_layer):
        mapping = self._build_field_mapping(target_layer)
        if not mapping:
            arcpy.AddWarning("No matching line fields found.")
            return

        source_layer = target_layer  # Assumes source and target are already aligned
        sr = arcpy.Describe(target_layer).spatialReference
        fields_to_copy = ["SHAPE@"] + list(mapping.values())
        source_dict = {}

        with arcpy.da.SearchCursor(source_layer, fields_to_copy) as cursor:
            for row in cursor:
                line = row[0].projectAs(sr)
                coords = self._get_line_coords(line)
                source_dict[coords] = row[1:]

        with arcpy.da.Editor(self._get_workspace(target_layer)):
            with arcpy.da.UpdateCursor(target_layer, ["SHAPE@"] + list(mapping.keys())) as cursor:
                for row in cursor:
                    coords = self._get_line_coords(row[0])
                    if coords not in source_dict:
                        continue
                    values = source_dict[coords]
                    for i, val in enumerate(values):
                        row[i + 1] = val
                    cursor.updateRow(row)

    def copy_domains(self, target_layer):
        field_map = {
            "RLType1": "RLType1",
            "RLType2": "RLType2",
            "RLType3": "RLType3",
            "FLType1": "FLType1",
            "FLType2": "FLType2",
            "LineWidth": "LineWidth",
            "AvgSlope": "Slope"
        }
        sr = arcpy.Describe(target_layer).spatialReference
        source_layer = target_layer  # Aligned assumption
        source_dict = {}

        with arcpy.da.SearchCursor(source_layer, ["SHAPE@"] + list(field_map.values())) as cursor:
            for row in cursor:
                line = row[0].projectAs(sr)
                coords = self._get_line_coords(line)
                source_dict[coords] = dict(zip(field_map.values(), row[1:]))

        with arcpy.da.Editor(self._get_workspace(target_layer)):
            with arcpy.da.UpdateCursor(target_layer, ["SHAPE@"] + list(field_map.keys())) as cursor:
                for row in cursor:
                    coords = self._get_line_coords(row[0])
                    if coords not in source_dict:
                        continue
                    values = source_dict[coords]
                    for i, target_field in enumerate(field_map.keys(), start=1):
                        raw_val = values.get(field_map[target_field])
                        if not raw_val:
                            continue
                        norm = normalize_label(raw_val)
                        mapped = LINE_DOMAIN_MAPPING.get(norm)
                        if mapped:
                            row[i] = mapped
                    cursor.updateRow(row)

    def update_static_fields(self, target_layer):
        with arcpy.da.Editor(self._get_workspace(target_layer)):
            with arcpy.da.UpdateCursor(target_layer, ["Fire_Num", "Fire_Name", "Status"]) as cursor:
                for row in cursor:
                    if not row[0]: row[0] = self.fire_number
                    if not row[1]: row[1] = self.fire_name
                    if not row[2] or row[2] == "RehabRequiresFieldVerification":
                        row[2] = self.status
                    cursor.updateRow(row)

    def _get_workspace(self, layer):
        props = layer.connectionProperties
        if 'connection_info' in props:
            return props['connection_info']['database']
        return os.path.dirname(layer.dataSource)

    def _get_line_coords(self, geom):
        first = geom.firstPoint
        last = geom.lastPoint
        return (round(first.X, 3), round(first.Y, 3)), (round(last.X, 3), round(last.Y, 3))

    def _build_field_mapping(self, layer):
        fields = [f.name for f in arcpy.ListFields(layer)]
        mapping = {}
        if "TimeStamp" in fields:
            mapping["CaptureDate"] = "TimeStamp"
        if "desc" in fields:
            mapping["Description"] = "desc"
        if "name" in fields:
            mapping["Label"] = "name"
        if "CritWork" in fields:
            mapping["CritWork"] = "CritWork"
        if "ProtValue" in fields:
            mapping["ProtValue"] = "ProtValue"
        if "LineWidth" in fields:
            mapping["LineWidth"] = "LineWidth"
        if "Slope" in fields:
            mapping["AvgSlope"] = "Slope"
        return mapping
