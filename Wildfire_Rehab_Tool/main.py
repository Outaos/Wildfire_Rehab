# Step 1
"""
This is the entry point of the Wildfire Rehab Tool.
It collects user input parameters from the ArcGIS Pro tool interface,
initializes the RehabJob controller with those parameters,
and triggers the full rehab processing pipeline.
"""

# Wildfire_Rehab_Tool/main.py

from d_runner.rehab_job import RehabJob
import arcpy

def main():
    fire_year = arcpy.GetParameterAsText(0)
    fire_number = arcpy.GetParameterAsText(1)
    backup_folder = arcpy.GetParameterAsText(2)
    data_folder = arcpy.GetParameterAsText(3)
    fire_name = arcpy.GetParameterAsText(4)
    status = arcpy.GetParameterAsText(5)

    job = RehabJob(
        fire_year=fire_year,
        fire_number=fire_number,
        backup_folder=backup_folder,
        data_folder=data_folder,
        fire_name=fire_name,
        status=status
    )
    job.run()

if __name__ == "__main__":
    main()