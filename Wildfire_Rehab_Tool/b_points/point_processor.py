# Step 4
"""
This script defines the PointProcessor class, which is responsible for:
- Copying point geometries into the wildfire rehab layer
- Transferring basic attributes based on spatial match
- Applying domain values based on label normalization
- Updating static fields like Fire_Num, Fire_Name, and Status
"""

# Wildfire_Rehab_Tool/b_points/point_processor.py

import arcpy
import os
from a_utils.domain_mappings import POINT_DOMAIN_MAPPING, normalize_label

class PointProcessor:
    def __init__(self, fire_name, fire_number, status):
        self.fire_name = fire_name
        self.fire_number = fire_number
        self.status = status

    def copy_points(self, source_layer, target_layer):
        with arcpy.da.Editor(self._get_workspace(target_layer)):
            with arcpy.da.SearchCursor(source_layer, ["SHAPE@"]) as search:
                with arcpy.da.InsertCursor(target_layer, ["SHAPE@", "Fire_Num"]) as insert:
                    for row in search:
                        insert.insertRow((row[0], ''))
        arcpy.AddMessage("Points copied successfully.")

    def copy_attributes(self, source_layer, target_layer):
        mapping = self._build_field_mapping(source_layer)
        if not mapping:
            arcpy.AddWarning("No attribute fields matched.")
            return

        source_dict = self._index_by_coordinates(source_layer, mapping.values(), target_layer)
        with arcpy.da.Editor(self._get_workspace(target_layer)):
            with arcpy.da.UpdateCursor(target_layer, ["SHAPE@"] + list(mapping.keys())) as cursor:
                for row in cursor:
                    coords = self._get_centroid_coords(row[0])
                    if coords in source_dict:
                        values = source_dict[coords]
                        for i, val in enumerate(values):
                            row[i + 1] = val
                        cursor.updateRow(row)

    def copy_domains(self, source_layer, target_layer):
        field_map = {
            "RPtType1": "sym_name",
            "RPtType2": "RPtType2",
            "RPtType3": "RPtType3"
        }
        source_dict = self._index_by_coordinates(source_layer, field_map.values(), target_layer)
        with arcpy.da.Editor(self._get_workspace(target_layer)):
            with arcpy.da.UpdateCursor(target_layer, ["SHAPE@"] + list(field_map.keys())) as cursor:
                for row in cursor:
                    coords = self._get_centroid_coords(row[0])
                    if coords not in source_dict:
                        continue
                    source_vals = source_dict[coords]
                    for i, (target_field, source_field) in enumerate(field_map.items(), start=1):
                        raw_val = source_vals.get(source_field)
                        if not raw_val:
                            continue
                        norm = normalize_label(raw_val)
                        mapped = POINT_DOMAIN_MAPPING.get(norm)
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

    def _get_centroid_coords(self, geom):
        c = geom.centroid
        return (round(c.X, 3), round(c.Y, 3))

    def _index_by_coordinates(self, layer, fields, target_layer):
        sr = arcpy.Describe(target_layer).spatialReference
        full_fields = ["SHAPE@"] + list(fields)
        data = {}
        with arcpy.da.SearchCursor(layer, full_fields) as cursor:
            for row in cursor:
                proj_geom = row[0].projectAs(sr)
                coords = self._get_centroid_coords(proj_geom)
                if len(fields) == 1:
                    data[coords] = [row[1]]
                else:
                    data[coords] = dict(zip(fields, row[1:]))
        return data

    def _build_field_mapping(self, layer):
        fields = [f.name for f in arcpy.ListFields(layer)]
        mapping = {}
        if "TimeStamp" in fields:
            mapping["CaptureDate"] = "TimeStamp"
        elif "TimeWhen" in fields:
            mapping["CaptureDate"] = "TimeWhen"

        if "desc" in fields:
            mapping["Description"] = "desc"
        elif "Descr" in fields:
            mapping["Comments"] = "Descr"

        if "name" in fields:
            mapping["Label"] = "name"

        if "CritWork" in fields:
            mapping["CritWork"] = "CritWork"

        if "ProtValue" in fields:
            mapping["ProtValue"] = "ProtValue"

        return mapping