# Step 3
"""
This script defines the ProjectSetup class, which handles shared spatial setup tasks
used by both point and line processing steps:
- Backing up the source geodatabase
- Importing and grouping rehab layers into the map
- Reprojecting collected input shapefiles to BC Albers
"""

# Wildfire_Rehab_Tool/a_utils/project_setup.py

import arcpy
import os
import re

class ProjectSetup:
    def __init__(self, fire_year, fire_number, backup_folder, data_folder):
        self.fire_year = fire_year
        self.fire_number = fire_number
        self.backup_folder = backup_folder
        self.data_folder = data_folder
        self.group_input = f"{fire_number}_Input"
        self.group_output = f"{fire_number}_Original"

    def backup_geodatabase(self):
        fire_code = self.fire_number[:2]
        input_gdb = fr"\\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{self.fire_year}\Cariboo\{fire_code}\{self.fire_number}\Data\{self.fire_number}_Rehab.gdb"
        output_gdb = os.path.join(self.backup_folder, f"{self.fire_number}_Rehab_BU.gdb")

        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)

        arcpy.Copy_management(input_gdb, output_gdb)
        arcpy.AddMessage("1. Backup completed successfully.")

    def import_output_layers(self):
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        map_obj = aprx.activeMap
        gdb_path = self._construct_gdb_path()
        dataset = "wildfireBC_Rehab"

        fc_points = os.path.join(gdb_path, dataset, "wildfireBC_Rehab_Point")
        fc_lines = os.path.join(gdb_path, dataset, "wildfireBC_Rehab_Line")

        if not arcpy.Exists(fc_points) or not arcpy.Exists(fc_lines):
            raise FileNotFoundError("Expected rehab point/line feature classes not found.")

        if not any(lyr.name == self.group_output for lyr in map_obj.listLayers() if lyr.isGroupLayer):
            group_layer = map_obj.createGroupLayer(self.group_output)
            map_obj.addLayerToGroup(group_layer, map_obj.addDataFromPath(fc_points))
            map_obj.addLayerToGroup(group_layer, map_obj.addDataFromPath(fc_lines))
            aprx.save()

        return fc_points, fc_lines

    def import_input_shapefiles(self):
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        map_obj = aprx.activeMap

        if not os.path.exists(self.data_folder):
            raise FileNotFoundError(f"Input folder '{self.data_folder}' not found.")

        group_layer = self._get_or_create_group_layer(map_obj, self.group_input)

        for file in os.listdir(self.data_folder):
            if file.lower().endswith(".shp"):
                shp_path = os.path.join(self.data_folder, file)
                new_layer = map_obj.addDataFromPath(shp_path)
                map_obj.addLayerToGroup(group_layer, new_layer)
                map_obj.removeLayer(new_layer)

        aprx.save()

    def reproject_inputs(self):
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        map_obj = aprx.activeMap
        group_layer = self._find_group_layer(map_obj, self.group_input)
        bc_albers = arcpy.SpatialReference(3005)

        reprojected = []
        for lyr in group_layer.listLayers():
            if lyr.dataSource.endswith(".shp"):
                desc = arcpy.Describe(lyr)
                if desc.shapeType == "Point" and desc.spatialReference.factoryCode == 4326:
                    sanitized = self._sanitize_name(lyr.name)
                    output_fc = os.path.join(arcpy.env.workspace, f"{sanitized}_BC")
                    arcpy.management.Project(lyr.dataSource, output_fc, bc_albers)
                    reprojected.append(output_fc)

        if not reprojected:
            arcpy.AddError("No eligible point shapefiles were reprojected.")

        return reprojected

    def _construct_gdb_path(self):
        fire_code = self.fire_number[:2]
        return fr"\\\spatialfiles.bcgov\work\!Shared_Access\Provincial_Wildfire_Rehab\FireSeasonWork\{self.fire_year}\Cariboo\{fire_code}\{self.fire_number}\Data\{self.fire_number}_Rehab.gdb"

    def _get_or_create_group_layer(self, map_obj, group_name):
        for lyr in map_obj.listLayers():
            if lyr.isGroupLayer and lyr.name == group_name:
                return lyr
        return map_obj.createGroupLayer(group_name)

    def _find_group_layer(self, map_obj, group_name):
        for lyr in map_obj.listLayers():
            if lyr.isGroupLayer and lyr.name == group_name:
                return lyr
        raise ValueError(f"Group layer '{group_name}' not found.")

    def _sanitize_name(self, name):
        name = re.sub(r'[^\w]+', '_', name)
        if not re.match(r'^[A-Za-z_]', name):
            name = f"_{name}"
        return name
