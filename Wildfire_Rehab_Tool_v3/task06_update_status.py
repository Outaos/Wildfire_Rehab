import arcpy

"""
Workflow
5.1 Quickly updates Point/Line Status.

"""

def update_status(fc, new_status):
    # Check if there is a selection
    fidset = arcpy.Describe(fc).FIDSet
    if not fidset:
        msg = "Step 5. No features are selected. Please select one or more features before running the tool."
        arcpy.AddWarning(msg)
        raise arcpy.ExecuteError(msg)

    with arcpy.da.UpdateCursor(fc, ["Status"]) as cursor:
        for row in cursor:
            row[0] = new_status
            cursor.updateRow(row)
    arcpy.AddMessage(f"Step 5.  All selected features updated to Status = '{new_status}'.")

# Get user inputs from tool
fc = arcpy.GetParameterAsText(0)  
new_status = arcpy.GetParameterAsText(1) 

'''
Current
RehabCompleted
RehabFieldVerified
RehabObligationsTransferred
RehabPFR/ArchCompleted
RehabRequiresFieldVerification
Retired
'''

# Run the update
update_status(fc, new_status)
