# Step 2
"""
This script defines the RehabJob class, which acts as the controller for the entire workflow.
It first performs the shared setup (e.g., backup, layer imports, reprojection),
then delegates to the PointProcessor and LineProcessor classes to process point and line features.
"""

# Wildfire_Rehab_Tool/d_runner/rehab_job.py

from a_utils.project_setup import ProjectSetup
from b_points.point_processor import PointProcessor
from c_lines.line_processor import LineProcessor

class RehabJob:
    def __init__(self, fire_year, fire_number, backup_folder, data_folder, fire_name, status):
        self.setup = ProjectSetup(fire_year, fire_number, backup_folder, data_folder)
        self.fire_name = fire_name
        self.fire_number = fire_number
        self.status = status

    def run(self):
        # Step 1: Shared setup
        self.setup.backup_geodatabase()
        fc_points, fc_lines = self.setup.import_output_layers()
        self.setup.import_input_shapefiles()
        point_layers = self.setup.reproject_inputs()

        # Step 2: Point Processing
        point_proc = PointProcessor(self.fire_name, self.fire_number, self.status)
        for pt_layer in point_layers:
            point_proc.copy_points(pt_layer, fc_points)
            point_proc.copy_attributes(pt_layer, fc_points)
            point_proc.copy_domains(pt_layer, fc_points)
        point_proc.update_static_fields(fc_points)

        # Step 3: Line Processing
        line_proc = LineProcessor(self.fire_name, self.fire_number, self.status)
        line_proc.copy_lines()
        line_proc.update_static_fields(fc_lines)
        line_proc.copy_attributes(fc_lines)
        line_proc.copy_domains(fc_lines)