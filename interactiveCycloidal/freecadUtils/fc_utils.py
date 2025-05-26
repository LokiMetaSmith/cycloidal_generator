import FreeCAD
import Part # Should be available if FreeCAD is running

# Placeholder for Sketcher, might be needed later
import Sketcher
import Draft # For circular_pattern
import math
import traceback

def get_active_document():
    """Returns the active FreeCAD document or creates a new one if none exists."""
    if FreeCAD.ActiveDocument:
        return FreeCAD.ActiveDocument
    else:
        return FreeCAD.newDocument("CycloidalDrive")

def create_point(x, y, z):
    """Creates a FreeCAD Vector (point)."""
    return FreeCAD.Vector(x, y, z)

def create_component_group(document, name):
    """Creates a new group (App::Part) in the document to hold objects."""
    group = document.addObject('App::Part', name)
    return group

def recompute(document):
    """Recomputes the given document."""
    document.recompute()

def translate_object(obj, x, y, z):
    """Translates an object by the given x, y, z offsets."""
    obj.Placement.Base = obj.Placement.Base.add(FreeCAD.Vector(x, y, z))
    # It might be necessary to recompute the object or document depending on the context
    # For now, recompute will be handled at the end of the script.

def add_sketch(document, name, construction_plane_str="XY"):
    """
    Adds a new sketch to the document.
    construction_plane_str: "XY", "XZ", "YZ".
    For more complex plane definitions, this function would need enhancement
    or the calling code would need to provide a FreeCAD.Plane object.
    """
    sketch = document.addObject('Sketcher::SketchObject', name)
    if construction_plane_str == "XY":
        sketch.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(FreeCAD.Vector(0,0,1),0)) # Default XY plane
    elif construction_plane_str == "XZ":
        sketch.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(FreeCAD.Vector(0,1,0), -90))
    elif construction_plane_str == "YZ":
        sketch.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 90))
    else:
        FreeCAD.Console.PrintWarning(f"Unsupported construction plane string: {construction_plane_str}. Defaulting to XY.")
        sketch.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(FreeCAD.Vector(0,0,1),0))
    return sketch

def add_spline_to_sketch(sketch_object, points_list):
    """
    Adds a B-spline to a FreeCAD sketch from a list of FreeCAD.Vector points.
    Note: FreeCAD's Sketcher uses BSplineCurve, not directly "fitted" splines like Fusion in this context.
    The points_list should be a list of FreeCAD.Vector objects.
    """
    if not points_list:
        FreeCAD.Console.PrintWarning("Cannot add spline: points_list is empty.")
        return None
    
    # Sketcher works with 2D points relative to the sketch plane.
    # For simplicity, assuming points are already on the sketch plane (e.g., Z=0 for an XY sketch)
    # and need to be converted to Geometry objects.
    geo_points = [Part.Point(p.x, p.y) for p in points_list] # Assuming points are on XY plane for the sketch
    
    # Create a BSplineCurve
    # For Sketcher, we add geometry. For complex splines, degree might need adjustment.
    bspline = Part.BSplineCurve()
    bspline.interpolate(geo_points) # Creates a curve that passes through the points
    
    # Add the BSpline as geometry to the sketch.
    # This returns a Sketcher::SketchGeometryExtension object
    return sketch_object.addGeometry(bspline, False)


def add_line_to_sketch(sketch_object, start_vector, end_vector):
    """
    Adds a line segment to a FreeCAD sketch.
    start_vector and end_vector are FreeCAD.Vector objects, assumed to be on the sketch plane.
    """
    # Convert to 2D points for the sketch (assuming they are on the sketch's XY plane)
    p1 = Part.Point(start_vector.x, start_vector.y)
    p2 = Part.Point(end_vector.x, end_vector.y)
    
    line = Part.LineSegment(p1, p2)
    return sketch_object.addGeometry(line, False)

def create_profile_from_sketch(sketch_object):
    """
    In FreeCAD, a valid, closed sketch can often be used directly as a profile.
    This function can be used to validate if the sketch is suitable (e.g., closed).
    For now, it just returns the sketch itself if it's a SketchObject.
    More complex validation (like checking for closed loops) can be added here.
    """
    if sketch_object and sketch_object.isDerivedFrom("Sketcher::SketchObject"):
        # Optional: Add validation logic here (e.g., check if sketch is closed)
        # For example:
        # if not sketch_object.Geometry:
        #     FreeCAD.Console.PrintWarning(f"Sketch {sketch_object.Name} has no geometry.")
        #     return None
        #
        # # A simple check for closed sketch might involve checking if all edges form a closed wire.
        # # This is non-trivial to implement robustly here.
        # # For now, we assume the sketch is properly constructed by the caller.
        FreeCAD.Console.PrintMessage(f"Using sketch {sketch_object.Name} as profile.")
        return sketch_object
    else:
        FreeCAD.Console.PrintError(f"Object {sketch_object.Name if sketch_object else 'None'} is not a valid sketch for profile creation.")
        return None

def extrude_profile(document, profile_sketch, thickness, name, operation_type="NewBody"):
    """
    Creates an extrusion from a profile sketch.
    profile_sketch: The FreeCAD sketch object to extrude.
    thickness: The extrusion depth.
    name: Name for the new extruded object.
    operation_type: Placeholder for future (e.g., "Cut", "Join"), currently makes a new body.
    Returns the new Part::Feature object (the extrusion).
    """
    if not profile_sketch or not profile_sketch.isDerivedFrom("Sketcher::SketchObject"):
        FreeCAD.Console.PrintError(f"Invalid profile sketch: {profile_sketch}")
        return None

    # Ensure the sketch is valid for extrusion (e.g., contains geometry)
    if not profile_sketch.Shape.Wires:
        FreeCAD.Console.PrintError(f"Sketch {profile_sketch.Name} has no wires to extrude.")
        return None

    extrusion = document.addObject("Part::Extrusion", name)
    extrusion.Base = profile_sketch
    extrusion.Dir = FreeCAD.Vector(0, 0, 1) # Extrude along Z-axis of the sketch's plane
    extrusion.LengthFwd = thickness
    extrusion.Solid = True
    
    # For operation_type, future implementation could involve boolean operations
    # if operation_type == "NewBody":
    #     pass # Default behavior
    # elif operation_type == "Cut":
    #     # This would require a base object to cut from
    #     pass 
    
    FreeCAD.Console.PrintMessage(f"Extruded {name} from sketch {profile_sketch.Name}.")
    # document.recompute() # Recompute might be needed here or done globally later
    return extrusion

def circular_pattern(document, object_to_pattern_name, axis_vector, center_vector, quantity, total_angle_degrees, name):
    """
    Creates a circular pattern of an object.
    object_to_pattern_name: Name of the object to pattern.
    axis_vector: FreeCAD.Vector defining the axis of rotation.
    center_vector: FreeCAD.Vector defining the center of the pattern.
    quantity: Total number of instances (including the original).
    total_angle_degrees: The angle over which to distribute the instances.
    name: Name for the array object.
    Returns the array object or None.
    """
    obj_to_pattern = document.getObject(object_to_pattern_name)
    if not obj_to_pattern:
        FreeCAD.Console.PrintError(f"Object to pattern '{object_to_pattern_name}' not found.")
        return None

    if int(quantity) <= 1:
        FreeCAD.Console.PrintWarning("Quantity for pattern must be greater than 1. Returning original object.")
        return obj_to_pattern # Or clone it if a separate object is expected

    # Draft.array creates linked objects by default. For independent objects, a loop with copy and placement is needed.
    # For simplicity, using Draft.array first.
    # The 'name' parameter for Draft.array is for the array object itself.
    
    # Ensure Draft module is available
    if "Draft" not in globals():
        FreeCAD.Console.PrintError("Draft module is not available. Cannot create circular pattern.")
        return None

    try:
        # Fuse an array of copies to make them independent if needed, or handle linked objects
        # For now, let's create simple copies and place them if Draft.array proves too complex with linked objects
        
        patterned_objects = []
        # patterned_objects.append(obj_to_pattern) # Original object is part of the count

        # If we want truly independent objects, we need to copy the shape and create new Part::Features
        original_shape = obj_to_pattern.Shape.copy()

        # Create a group for the patterned items
        pattern_group = create_component_group(document, name + "_group")


        for i in range(int(quantity)):
            new_obj_name = f"{name}_{i}"
            new_part_feature = document.addObject("Part::Feature", new_obj_name)
            new_part_feature.Shape = original_shape # Assign a copy of the shape
            
            angle_rad = math.radians((total_angle_degrees / quantity) * i)
            
            placement = FreeCAD.Placement()
            placement.Rotation = FreeCAD.Rotation(axis_vector, math.degrees(angle_rad)) # Rotation expects degrees
            placement.Base = center_vector # Initial position relative to which rotation happens
            
            # If the original object is not at the center_vector, we need to adjust
            # For an object whose center of rotation should be 'center_vector' and axis 'axis_vector'
            # The object itself is first placed as if center_vector is the origin, then rotated, then moved to center_vector.
            # More simply: Rotate around the axis passing through center_vector.
            
            # Create a placement that rotates around axis_vector passing through center_vector
            # Then apply this placement to the new_part_feature
            # obj_original_placement = obj_to_pattern.Placement
            
            # Create a rotation around the 'axis_vector' by 'angle_rad' with 'center_vector' as the center.
            rot = FreeCAD.Rotation(axis_vector, math.degrees(angle_rad))
            
            # Get the original object's position relative to the pattern center
            # This is complex if the object's local origin isn't what we want to rotate
            # Assuming obj_to_pattern is already positioned correctly for the first instance (i=0)
            # if i == 0, placement is obj_to_pattern.Placement
            
            if i == 0: # First object is the original one, or a copy in its place
                new_part_feature.Placement = obj_to_pattern.Placement
            else:
                # This needs careful handling of placements.
                # A common way is to place the object at origin, rotate, then translate to final pattern position.
                # Or, more directly, use Placement's multiply capability if object is already relative to center.
                # Let's assume obj_to_pattern is the first element and we rotate its copies.
                
                # Create a new placement for each copy
                copy_placement = obj_to_pattern.Placement.copy()
                # Create a rotation transformation
                rotation_transform = FreeCAD.Placement(FreeCAD.Vector(0,0,0), rot, center_vector)
                # Multiply the original placement by this rotation transformation
                copy_placement = rotation_transform.multiply(copy_placement)
                new_part_feature.Placement = copy_placement

            pattern_group.addObject(new_part_feature)
            patterned_objects.append(new_part_feature)
        
        # For Draft.array approach (simpler but creates links):
        # array = Draft.make_polar_array(
        #     obj_to_pattern,
        #     number=int(quantity),
        #     angle=total_angle_degrees,
        #     center=center_vector,
        #     use_link=True, # Use True for App::Link, False for simple copies (might not be fully independent)
        #     prop_name="PolarArray" # Name of the property holding the array info
        # )
        # array.Label = name
        # document.recompute()
        # return array
        
        document.recompute() # Recompute after adding all objects and setting placements
        return pattern_group # Return the group containing patterned objects

    except Exception as e:
        FreeCAD.Console.PrintError(f"Error creating circular pattern: {e}\n{traceback.format_exc()}")
        return None


def combine_objects(document, base_object_name, tool_object_names_list, operation, name):
    """
    Performs boolean operations (fuse, cut, common) on Part objects.
    base_object_name: Name of the base Part object.
    tool_object_names_list: List of names of the tool Part objects.
    operation: "fuse", "cut", or "common".
    name: Name for the resulting Part object.
    Returns the new Part object or None.
    """
    base_obj = document.getObject(base_object_name)
    if not base_obj:
        FreeCAD.Console.PrintError(f"Base object '{base_object_name}' not found.")
        return None

    tool_objs = []
    for tool_name in tool_object_names_list:
        obj = document.getObject(tool_name)
        if not obj:
            FreeCAD.Console.PrintError(f"Tool object '{tool_name}' not found.")
            return None
        tool_objs.append(obj)

    if not tool_objs and operation != "copy": # Some operations might not need tools
        FreeCAD.Console.PrintError("No tool objects provided for the operation.")
        return None

    try:
        if operation.lower() == "fuse":
            # Part.multiFuse might be better if available and fusing multiple tools with base
            # For now, fuse tools together first if multiple, then fuse with base or fuse one by one
            if len(tool_objs) > 1:
                fused_tools_doc_object = document.addObject("Part::MultiFuse", name + "_fused_tools")
                fused_tools_doc_object.Shapes = tool_objs
                document.recompute() # Recompute to get the shape of fused_tools_doc_object
                if not fused_tools_doc_object.Shape.isValid():
                    FreeCAD.Console.PrintError("Fusing tools failed.")
                    return None
                
                final_fusion = document.addObject("Part::Fuse", name)
                final_fusion.Base = base_obj
                final_fusion.Tool = fused_tools_doc_object
            elif tool_objs:
                final_fusion = document.addObject("Part::Fuse", name)
                final_fusion.Base = base_obj
                final_fusion.Tool = tool_objs[0]
            else: # No tools, effectively a copy of the base
                 new_obj = document.copyObject(base_obj, True) # True for recursive copy
                 new_obj.Label = name
                 return new_obj

            result_obj = final_fusion

        elif operation.lower() == "cut":
            if not tool_objs:
                FreeCAD.Console.PrintError("No tool object provided for cut operation.")
                return None
            # If multiple tools, they should ideally be fused into a single tool first
            # For simplicity, assuming one tool or tools that can be cut sequentially or as a multi-cut
            if len(tool_objs) > 1:
                # Create a compound of tool objects if Part.MultiCut is not available/easy
                # Or fuse them into one tool
                fused_tool_for_cut = document.addObject("Part::MultiFuse", name + "_tool_for_cut")
                fused_tool_for_cut.Shapes = tool_objs
                document.recompute()
                if not fused_tool_for_cut.Shape.isValid():
                     FreeCAD.Console.PrintError("Fusing tools for cut operation failed.")
                     return None
                
                cut_op = document.addObject("Part::Cut", name)
                cut_op.Base = base_obj
                cut_op.Tool = fused_tool_for_cut
            else:
                cut_op = document.addObject("Part::Cut", name)
                cut_op.Base = base_obj
                cut_op.Tool = tool_objs[0]
            
            result_obj = cut_op

        elif operation.lower() == "common":
            # Similar to fuse, handle multiple tools if necessary
            if len(tool_objs) > 1:
                fused_tools_for_common = document.addObject("Part::MultiFuse", name + "_fused_tools_common")
                fused_tools_for_common.Shapes = tool_objs
                document.recompute()
                if not fused_tools_for_common.Shape.isValid():
                    FreeCAD.Console.PrintError("Fusing tools for common operation failed.")
                    return None

                common_op = document.addObject("Part::Common", name)
                common_op.Base = base_obj
                common_op.Tool = fused_tools_for_common
            elif tool_objs:
                common_op = document.addObject("Part::Common", name)
                common_op.Base = base_obj
                common_op.Tool = tool_objs[0]
            else:
                FreeCAD.Console.PrintError("No tool object provided for common operation.")
                return None
            result_obj = common_op
            
        else:
            FreeCAD.Console.PrintError(f"Unsupported boolean operation: {operation}")
            return None

        document.recompute() # IMPORTANT after boolean operations
        
        # Check if the operation was successful by checking the validity of the resulting shape
        if not result_obj.Shape.isValid():
            FreeCAD.Console.PrintError(f"Boolean operation '{operation}' for '{name}' resulted in an invalid shape.")
            # Clean up the failed object?
            # document.removeObject(result_obj.Name)
            return None
            
        FreeCAD.Console.PrintMessage(f"Performed {operation} for {name}.")
        return result_obj

    except Exception as e:
        FreeCAD.Console.PrintError(f"Error in boolean operation '{operation}' for '{name}': {e}\n{traceback.format_exc()}")
        # Attempt to clean up any intermediate objects if they were created and named
        # intermediate_names = [name + "_fused_tools", name + "_tool_for_cut", name + "_fused_tools_common"]
        # for iname in intermediate_names:
        #     if document.getObject(iname):
        #         document.removeObject(iname)
        return None

def add_circle_to_sketch(sketch_object, center_vector, radius):
    """
    Adds a circle to a FreeCAD sketch.
    Assumes sketch is on XY plane for default circle orientation.
    center_vector should be relative to sketch plane (e.g., Z=0 for XY sketch).
    """
    if not sketch_object or not hasattr(sketch_object, "addGeometry"):
        FreeCAD.Console.PrintError("Invalid sketch object provided to add_circle_to_sketch.")
        return None
    if radius <= 0:
        FreeCAD.Console.PrintError("Radius must be positive.")
        return None
    
    # Sketcher works with 2D geometry relative to its plane.
    # For a sketch on XY plane, center_vector's Z component is effectively ignored by Part.Circle's 2D nature here.
    # The circle is created on the sketch's plane.
    # Part.Circle constructor: Circle(CenterPoint, NormalVector, Radius)
    # NormalVector defines the plane of the circle. For a sketch, this normal is implicitly its Z axis.
    circle = Part.Circle(center_vector, sketch_object.Placement.Rotation.multVec(FreeCAD.Vector(0,0,1)), radius)
    # The normal of the circle should match the normal of the sketch plane.
    # sketch_object.Placement.Rotation.multVec(FreeCAD.Vector(0,0,1)) gives the sketch's normal vector.

    return sketch_object.addGeometry(circle, False) # False for not construction

# TODO: Implement the following functions:
#
#
#
#
#
#
#
