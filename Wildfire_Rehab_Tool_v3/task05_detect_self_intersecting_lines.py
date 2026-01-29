import arcpy
import os

def _get_default_gdb():
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    return aprx.defaultGeodatabase

def _overlap(ext1, ext2):
    """Quick bbox overlap test."""
    return not (ext1.XMax < ext2.XMin or ext1.XMin > ext2.XMax or
                ext1.YMax < ext2.YMin or ext1.YMin > ext2.YMax)

def _iter_points(geom):
    """
    Yield arcpy.Point objects from an intersection result that may be:
    - PointGeometry
    - Multipoint (iterates as Points in some ArcGIS Pro builds, or Arrays in others)
    - (occasionally) a bare Point
    """
    if not geom:
        return

    # Bare arcpy.Point
    if isinstance(geom, arcpy.Point):
        yield geom
        return

    gtype = getattr(geom, "type", "").lower()

    # PointGeometry
    if gtype == "point":
        yield geom.firstPoint
        return

    # Multipoint
    if gtype == "multipoint":
        for part in geom:
            # In some builds, `part` is already a Point
            if isinstance(part, arcpy.Point):
                yield part
            else:
                # In others, `part` is an Array of Points
                for p in part:
                    if p:
                        yield p
        return

    # Fallback: try centroid
    try:
        c = geom.centroid
        if isinstance(c, arcpy.Point):
            yield c
        else:
            yield c.firstPoint
    except Exception:
        return


def _unique_fc_name(out_gdb, base_name):
    """
    Return a valid feature class name in out_gdb.
    If it already exists, append _1, _2, etc.
    """
    base_valid = arcpy.ValidateTableName(base_name, out_gdb)

    # If ValidateTableName changes it, we still keep the suffix logic on the result
    name = base_valid
    out_fc = os.path.join(out_gdb, name)

    if not arcpy.Exists(out_fc):
        return name, out_fc

    i = 1
    while True:
        candidate = arcpy.ValidateTableName(f"{base_valid}_{i}", out_gdb)
        cand_fc = os.path.join(out_gdb, candidate)
        if not arcpy.Exists(cand_fc):
            return candidate, cand_fc
        i += 1

def detect_line_intersections(input_fc, out_name="Self_Intersection_Points", ignore_touches=True):
    # Use default GDB
    out_gdb = _get_default_gdb()
    arcpy.env.workspace = out_gdb

    sr = arcpy.Describe(input_fc).spatialReference

    # Make output name unique (and valid)
    out_name_unique, out_fc = _unique_fc_name(out_gdb, out_name)

    # Create output FC
    arcpy.management.CreateFeatureclass(out_gdb, out_name_unique, "POINT", spatial_reference=sr)
    arcpy.management.AddField(out_fc, "Line1_OID", "LONG")
    arcpy.management.AddField(out_fc, "Line2_OID", "LONG")
    arcpy.management.AddField(out_fc, "Type", "TEXT", field_length=20)

    arcpy.AddMessage(f"Output: {out_fc}")

    # Read all lines once
    lines = []
    with arcpy.da.SearchCursor(input_fc, ["OID@", "SHAPE@"]) as cur:
        for oid, geom in cur:
            if geom is None:
                continue
            lines.append((oid, geom, geom.extent))

    arcpy.AddMessage(f"Loaded {len(lines)} line feature(s).")

    inserted = 0

    with arcpy.da.InsertCursor(out_fc, ["SHAPE@", "Line1_OID", "Line2_OID", "Type"]) as icur:

        # -----------------------------
        # Self-intersections (per feature)
        # -----------------------------
        arcpy.AddMessage("Scanning self-intersections...")
        for oid, line, _ext in lines:
            # Build segments for each part
            segments = []
            for part in line:
                pts = [p for p in part if p]
                for i in range(len(pts) - 1):
                    seg = arcpy.Polyline(arcpy.Array([pts[i], pts[i + 1]]), sr)
                    segments.append(seg)

            # Check only non-adjacent pairs, and only once (j > i)
            for i in range(len(segments)):
                for j in range(i + 1, len(segments)):
                    # Skip neighbors (share endpoints) to reduce “touch” noise
                    if j == i + 1:
                        continue

                    inter = segments[i].intersect(segments[j], 1)  # points
                    if not inter:
                        continue

                    if ignore_touches and segments[i].touches(segments[j]):
                        continue

                    for pt in _iter_points(inter):
                        icur.insertRow([arcpy.PointGeometry(pt, sr), oid, oid, "SELF"])
                        inserted += 1

        arcpy.AddMessage("Self-intersection scan done.")

        # -----------------------------
        # Intersections between different features
        # -----------------------------
        arcpy.AddMessage("Scanning intersections between different lines...")
        for idx1 in range(len(lines)):
            oid1, g1, e1 = lines[idx1]
            for idx2 in range(idx1 + 1, len(lines)):
                oid2, g2, e2 = lines[idx2]

                # Fast bbox reject
                if not _overlap(e1, e2):
                    continue

                inter = g1.intersect(g2, 1)  # point output
                if not inter:
                    continue

                if ignore_touches and g1.touches(g2):
                    continue

                for pt in _iter_points(inter):
                    icur.insertRow([arcpy.PointGeometry(pt, sr), oid1, oid2, "CROSS"])
                    inserted += 1

    arcpy.AddMessage(f"Inserted {inserted} intersection point(s).")

    # Add to map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.activeMap
    if m:
        m.addDataFromPath(out_fc)
        arcpy.AddMessage("Output added to current map.")

    return out_fc

# -----------------------------
# Tool parameters
# -----------------------------
if __name__ == "__main__":
    input_feature_class = arcpy.GetParameterAsText(0)
    out_fc = detect_line_intersections(
        input_feature_class,
        out_name="Self_Intersection_Points",
        ignore_touches=True
    )
    arcpy.AddMessage(f"Done: {out_fc}")
