import arcpy

# Function to detect both self-intersections and intersections between different lines
def detect_line_intersections(input_fc, output_fc):
    # Get the spatial reference of the input feature class
    spatial_reference = arcpy.Describe(input_fc).spatialReference
    
    # Create an empty point feature class to store intersection points in the default geodatabase
    arcpy.management.CreateFeatureclass(arcpy.env.workspace, output_fc, "POINT", spatial_reference=spatial_reference)
    
    # Add fields to the output feature class to store the OIDs of intersecting features
    arcpy.management.AddField(output_fc, "Line1_OID", "LONG")
    arcpy.management.AddField(output_fc, "Line2_OID", "LONG")

    # Create an InsertCursor to add intersection points
    with arcpy.da.InsertCursor(output_fc, ["SHAPE@", "Line1_OID", "Line2_OID"]) as insert_cursor:
        
        # Create a SearchCursor to iterate through each line feature in the input feature class
        with arcpy.da.SearchCursor(input_fc, ["OID@", "SHAPE@"]) as cursor1:
            for row1 in cursor1:
                oid1 = row1[0]
                line1 = row1[1]
                
                # Check for self-intersections within the same line (if multipart)
                segment_list = []
                for part in line1:
                    for i in range(len(part) - 1):  # Loop through each segment
                        segment = arcpy.Polyline(arcpy.Array([part[i], part[i+1]]))
                        segment_list.append(segment)
                
                # Now check for self-intersections between segments of the same line
                for i, segment1 in enumerate(segment_list):
                    for j, segment2 in enumerate(segment_list):
                        if i != j:  # Don't compare a segment with itself
                            intersection = segment1.intersect(segment2, 1)  # Only detect true intersections
                            if intersection and intersection.pointCount > 0 and not segment1.touches(segment2):
                                arcpy.AddMessage(f"Self-intersection detected in feature {oid1} at {intersection.WKT}.")
                                for point in intersection:
                                    insert_cursor.insertRow([point, oid1, oid1])  # Self-intersection

                # Now check for intersections between different lines
                with arcpy.da.SearchCursor(input_fc, ["OID@", "SHAPE@"]) as cursor2:
                    for row2 in cursor2:
                        oid2 = row2[0]
                        line2 = row2[1]
                        
                        # Avoid comparing the same feature with itself
                        if oid1 != oid2:
                            # Check if the two lines intersect, ignoring touching vertices
                            intersection = line1.intersect(line2, 1)  # 1 is for point output
                            
                            # Ensure the intersection result contains points and the lines don't just touch
                            if intersection and intersection.pointCount > 0 and not line1.touches(line2):
                                arcpy.AddMessage(f"Intersection detected between Line {oid1} and Line {oid2}.")
                                
                                # Insert each intersection point into the output feature class
                                for point in intersection:
                                    insert_cursor.insertRow([point, oid1, oid2])

    arcpy.AddMessage(f"Intersection points saved to {output_fc}.")
    # Automatically add the output feature class to the current map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap
    active_map.addDataFromPath(arcpy.env.workspace + "\\" + output_fc)

    arcpy.AddMessage(f"{output_fc} added to the current map.")
    
# Set the workspace environment to the default geodatabase
arcpy.env.workspace = arcpy.env.workspace  # Default geodatabase

# Parameters from ArcGIS Pro tool
input_feature_class = arcpy.GetParameterAsText(0)  # Input feature class provided by the user
output_feature_class = "Self_Intersection_Points"  # Automatically created output feature class

# Run the line intersection detection and create the output feature class
detect_line_intersections(input_feature_class, output_feature_class)

arcpy.AddMessage(f"Line intersection points saved to {output_feature_class}.")
