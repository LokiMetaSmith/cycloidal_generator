import FreeCAD
from . import fc_utils # Using relative import

class FreeCADAPIWrapper:
    def __init__(self, doc):
        if doc is None:
            FreeCAD.Console.PrintMessage("No active document provided to FreeCADAPIWrapper, getting/creating one.")
            self.doc = fc_utils.get_active_document()
        else:
            self.doc = doc
        self.root_component = self.doc # In FreeCAD, the document itself often acts as the root for parts

    def get_active_document(self):
        return self.doc

    def recompute(self):
        fc_utils.recompute(self.doc)
        FreeCAD.Gui.ActiveDocument.recompute() # Sometimes GUI recompute is also needed
        FreeCAD.Gui.SendMsgToActiveView("ViewFit")


    def create_component_group(self, name):
        """Creates a group (App::Part) to hold objects/features."""
        return fc_utils.create_component_group(self.doc, name)

    def create_sketch_on_xy_plane(self, parent_object_or_group, sketch_name):
        """
        Creates a sketch on the XY plane.
        parent_object_or_group: In FreeCAD, sketches are added to the document,
                               but can be associated with a body or part for organization.
                               For now, adding directly to document.
        """
        sketch = fc_utils.add_sketch(self.doc, sketch_name, "XY")
        # If parent_object_or_group is an App::Part, we can add the sketch to its group.
        if parent_object_or_group and hasattr(parent_object_or_group, "addObject"):
            try:
                # This might not be the standard way if parent is a PartDesign.Body
                # For App::Part, this works.
                # parent_object_or_group.addObject(sketch) # This might cause issues if sketch is already added
                pass # Sketch is already added to doc. Grouping is more for visual tree.
            except Exception as e:
                FreeCAD.Console.PrintWarning(f"Could not add sketch to parent group {parent_object_or_group.Name}: {e}")
        return sketch

    def add_points_to_collection(self, points_data_list):
        """
        Converts a list of (x,y,z) tuples/lists to FreeCAD.Vector objects.
        In Fusion, this might create an ObjectCollection. Here, it's just a list of Vectors.
        """
        return [fc_utils.create_point(p[0], p[1], p[2]) for p in points_data_list]

    def add_fitted_spline(self, sketch_object, points_collection):
        """Adds a B-spline passing through the points to the sketch."""
        return fc_utils.add_spline_to_sketch(sketch_object, points_collection)

    def add_line_segments_to_sketch(self, sketch_object, point_tuples_list):
        """
        Adds multiple line segments to a sketch.
        point_tuples_list: A list of ((x1,y1,z1), (x2,y2,z2)) tuples.
        Z is often ignored by sketcher if sketch is on XY.
        Returns a list of the created line geometry objects.
        """
        lines = []
        for p_tuple in point_tuples_list:
            start_vec = fc_utils.create_point(p_tuple[0][0], p_tuple[0][1], p_tuple[0][2])
            end_vec = fc_utils.create_point(p_tuple[1][0], p_tuple[1][1], p_tuple[1][2])
            line = fc_utils.add_line_to_sketch(sketch_object, start_vec, end_vec)
            if line:
                lines.append(line)
        return lines
        
    def get_profile_from_sketch(self, sketch_object):
        """Returns the sketch if it's a valid profile source."""
        return fc_utils.create_profile_from_sketch(sketch_object)

    def extrude(self, profile_sketch, thickness, name, operation_type="NewBody"):
        """Extrudes a sketch profile. Operation type is for future use (cut, join)."""
        # 'component' argument is not strictly needed if extruding in the main doc context
        return fc_utils.extrude_profile(self.doc, profile_sketch, thickness, name, operation_type)

    def circular_pattern(self, object_to_pattern_name, axis_vector_tuple, center_vector_tuple, quantity, total_angle_degrees, name):
        """
        Creates a circular pattern.
        axis_vector_tuple: (x,y,z) for pattern axis.
        center_vector_tuple: (x,y,z) for pattern center.
        """
        axis_vec = fc_utils.create_point(axis_vector_tuple[0], axis_vector_tuple[1], axis_vector_tuple[2])
        center_vec = fc_utils.create_point(center_vector_tuple[0], center_vector_tuple[1], center_vector_tuple[2])
        return fc_utils.circular_pattern(self.doc, object_to_pattern_name, axis_vec, center_vec, quantity, total_angle_degrees, name)

    def combine_bodies(self, base_object_name, tool_object_names_list, operation, name):
        """
        Performs boolean operations.
        operation: "fuse", "cut", "common".
        """
        # 'component' not strictly needed if objects are in the main doc
        return fc_utils.combine_objects(self.doc, base_object_name, tool_object_names_list, operation, name)

    def translate_object(self, obj_name, x, y, z):
        """Translates an object by name."""
        obj = self.doc.getObject(obj_name)
        if obj:
            fc_utils.translate_object(obj, x, y, z)
            self.recompute() # Translation often requires recompute to see effect
        else:
            FreeCAD.Console.PrintError(f"Object '{obj_name}' not found for translation.")

    def add_circle(self, sketch_object, center_tuple, radius):
        """Adds a circle to the specified sketch."""
        if not sketch_object:
            FreeCAD.Console.PrintError("add_circle: Sketch object is None.")
            return None
        center_vec = fc_utils.create_point(center_tuple[0], center_tuple[1], center_tuple[2])
        # Z-coordinate of center_tuple might be ignored if sketch is strictly 2D (e.g. on XY plane)
        # or should be 0 if points are defined on the sketch plane.
        return fc_utils.add_circle_to_sketch(sketch_object, center_vec, radius)
    
    # --- Mappings for Fusion 360 specific concepts / common parameters ---
    
    def get_root_component(self):
        """Returns the document itself, which acts as the root for parts in simple FreeCAD scripts."""
        return self.doc

    def get_construction_plane(self, component_or_doc, plane_name):
        """
        Returns a representation of a construction plane.
        In FreeCAD, this is often implicit or defined by sketch placement.
        For XY, XZ, YZ, we can return string identifiers used by `add_sketch`.
        `component_or_doc` is mostly self.doc here.
        """
        plane_name_upper = plane_name.upper()
        if plane_name_upper in ["XY", "XZ", "YZ"]:
            return plane_name_upper
        # Potentially map to FreeCAD plane objects if needed later
        FreeCAD.Console.PrintWarning(f"Using basic plane string '{plane_name_upper}'. Complex planes not yet supported in wrapper.")
        return plane_name_upper # Default to XY if not recognized, or handle error

    def get_construction_axis(self, component_or_doc, axis_name):
        """
        Returns a FreeCAD.Vector for standard axes 'x', 'y', 'z'.
        `component_or_doc` is mostly self.doc here.
        """
        axis_name_lower = axis_name.lower()
        if axis_name_lower == 'x':
            return FreeCAD.Vector(1,0,0)
        elif axis_name_lower == 'y':
            return FreeCAD.Vector(0,1,0)
        elif axis_name_lower == 'z':
            return FreeCAD.Vector(0,0,1)
        FreeCAD.Console.PrintError(f"Unknown axis name: {axis_name}")
        return FreeCAD.Vector(0,0,1) # Default to Z-axis

    def create_value_input_real(self, value):
        """Fusion's ValueInput.createByReal equivalent. In FreeCAD, numbers are used directly."""
        return float(value)

    def message_box(self, text):
        """Shows a message to the user."""
        FreeCAD.Console.PrintMessage(text) # Simple console message
        # For a GUI popup, would need PySide, e.g., from FreeCADGui import PySide
        # QtGui.QMessageBox.information(None, "Cycloidal Generator", text)
        # This requires FreeCAD to be in GUI mode.

    # Placeholder for methods that will be in FusionAPIWrapper and need a counterpart
    # or a clear "not applicable" path in FreeCAD.

    def get_component_from_occurrence(self, occurrence):
        """In FreeCAD, if occurrence is an App::Part, it's like a component."""
        if occurrence and hasattr(occurrence, "OutList"): # App::Part has OutList
            return occurrence
        return self.doc # Fallback or needs specific handling

    def create_component_occurrence(self, target_component_or_doc, name, transform_matrix=None):
        """
        Creates something like a component occurrence. In FreeCAD, this could be an App::Part
        added to the document or another App::Part.
        `target_component_or_doc` is usually self.doc.
        `transform_matrix` is a FreeCAD.Matrix, not a Fusion Matrix3D.
        """
        new_group = self.create_component_group(name)
        if transform_matrix and hasattr(new_group, "Placement") and isinstance(transform_matrix, FreeCAD.Placement):
            new_group.Placement = transform_matrix
        elif transform_matrix and isinstance(transform_matrix, FreeCAD.Matrix):
             new_group.Placement = FreeCAD.Placement(transform_matrix)
        return new_group

    # TODO: Add more wrapper methods as identified during refactoring of cycloidal.py
