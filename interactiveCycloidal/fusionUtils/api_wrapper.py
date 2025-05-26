import adsk.core
import adsk.fusion
# It's likely that the original fusionUtils will be used by this wrapper,
# or its functions will be absorbed/adapted here.
from . import fusionUtils # Relative import for existing utilities

class FusionAPIWrapper:
    def __init__(self, app, ui):
        self.app = app
        self.ui = ui
        self.product = self.app.activeProduct
        self.design = adsk.fusion.Design.cast(self.product)
        if not self.design:
            raise RuntimeError("FusionAPIWrapper: Not in an active design environment (e.g., Model workspace).")
        self.root_comp = self.design.rootComponent
        self.units_mgr = self.app.activeProduct.unitsManager

    def get_active_document(self):
        """In Fusion, the app's activeProduct (Design) is the context."""
        return self.design

    def recompute(self):
        """Fusion 360 recomputes automatically most of the time.
           A full recompute might be design.computeAll() if needed,
           but often changes trigger necessary updates.
           Adding a snapshot can be a way to ensure timeline capture."""
        if self.design:
            # self.design.computeAll() # This can be heavy
            # For script changes, often not needed unless parameters are changed non-interactively.
            # Adding a snapshot is good practice for operations that should appear in timeline.
            # self.design.snapshots.add()
            pass # Placeholder, as direct recompute is less common unless issues arise.

    def create_component_group(self, name):
        """
        In Fusion, creating a new component serves as a 'group'.
        This wrapper method will align with FreeCAD's concept if used,
        but typically direct component creation is preferred.
        This might map to creating an occurrence or a new component.
        For simplicity, let's make it create a new component and return its occurrence.
        """
        return self.create_component_occurrence(self.root_comp, name)


    def create_sketch_on_xy_plane(self, component, sketch_name):
        """Creates a sketch on the XY plane of the given component."""
        if not component or not isinstance(component, adsk.fusion.Component):
            raise ValueError("Valid component must be provided to create_sketch_on_xy_plane.")
        xy_plane = component.xYConstructionPlane
        sketch = component.sketches.add(xy_plane)
        sketch.name = sketch_name
        return sketch

    def add_points_to_collection(self, points_data_list):
        """
        Converts a list of (x,y,z) tuples/lists to Fusion's Point3D objects
        and adds them to an ObjectCollection.
        """
        points_collection = adsk.core.ObjectCollection.create()
        for p_data in points_data_list:
            # Assuming points_data_list are already in internal units (cm for Fusion by default)
            points_collection.add(adsk.core.Point3D.create(p_data[0], p_data[1], p_data[2]))
        return points_collection

    def add_fitted_spline(self, sketch_object, points_collection):
        """Adds a fitted spline through the points in the collection to the sketch."""
        if not points_collection or points_collection.count == 0:
            self.ui.messageBox("No points provided for spline.")
            return None
        return sketch_object.sketchCurves.sketchFittedSplines.add(points_collection)

    def add_line_segments_to_sketch(self, sketch_object, point_tuples_list):
        """
        Adds multiple line segments to a sketch.
        point_tuples_list: A list of ((x1,y1,z1), (x2,y2,z2)) tuples.
        Returns a list of the created SketchLine objects.
        """
        lines = []
        sketch_lines = sketch_object.sketchCurves.sketchLines
        for p_tuple in point_tuples_list:
            start_point = adsk.core.Point3D.create(p_tuple[0][0], p_tuple[0][1], p_tuple[0][2])
            end_point = adsk.core.Point3D.create(p_tuple[1][0], p_tuple[1][1], p_tuple[1][2])
            line = sketch_lines.addByTwoPoints(start_point, end_point)
            if line:
                lines.append(line)
        return lines

    def get_profile_from_sketch(self, sketch_object):
        """Gets the first profile from a sketch."""
        # Assuming the sketch forms a single, closed profile for simplicity
        if sketch_object.profiles.count > 0:
            return sketch_object.profiles.item(0)
        self.ui.messageBox(f"Sketch {sketch_object.name} contains no profiles.")
        return None

    def extrude(self, component, profile, thickness, name, operation_type_str="NewBodyFeatureOperation"):
        """
        Extrudes a sketch profile.
        operation_type_str can be "NewBodyFeatureOperation", "CutFeatureOperation", "JoinFeatureOperation".
        """
        if not component or not isinstance(component, adsk.fusion.Component):
            raise ValueError("Valid component must be provided for extrude operation.")
        if not profile or not isinstance(profile, adsk.fusion.Profile):
            raise ValueError("Valid profile must be provided for extrude operation.")

        distance = adsk.core.ValueInput.createByReal(thickness) # Assuming thickness is in cm
        
        op_map = {
            "NewBodyFeatureOperation": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            "CutFeatureOperation": adsk.fusion.FeatureOperations.CutFeatureOperation,
            "JoinFeatureOperation": adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "IntersectFeatureOperation": adsk.fusion.FeatureOperations.IntersectFeatureOperation
        }
        operation = op_map.get(operation_type_str, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, operation)
        extrude_input.setDistanceExtent(False, distance) # oneSideExtent
        
        extrude_feature = extrudes.add(extrude_input)
        # Name the body created by this extrusion
        if extrude_feature.bodies.count > 0:
            body = extrude_feature.bodies.item(0)
            body.name = name # Name the body, feature name is harder to set uniquely
        return extrude_feature # Or return body

    def circular_pattern(self, component, entities_to_pattern_collection, axis, quantity, total_angle_str, name):
        """
        Creates a circular pattern.
        entities_to_pattern_collection: ObjectCollection of features/bodies.
        axis: A SketchLine, ConstructionAxis, or BRepEdge representing the axis.
        quantity: Number of instances (as ValueInput).
        total_angle_str: Angle string e.g., "360 deg".
        """
        if not component or not isinstance(component, adsk.fusion.Component):
            raise ValueError("Valid component must be provided for circular_pattern.")

        circular_feats = component.features.circularPatternFeatures
        pattern_input = circular_feats.createInput(entities_to_pattern_collection, axis)
        
        qty_input = adsk.core.ValueInput.createByReal(quantity) # Direct quantity
        angle_input = adsk.core.ValueInput.createByString(total_angle_str)

        pattern_input.quantity = qty_input
        pattern_input.totalAngle = angle_input
        pattern_input.isSymmetric = False # Asymmetric by default

        circular_feature = circular_feats.add(pattern_input)
        circular_feature.name = name
        return circular_feature

    def combine_bodies(self, component, target_body, tool_bodies_collection, operation_str, name="Combine"):
        """
        Performs boolean operations.
        operation_str: "JoinFeatureOperation", "CutFeatureOperation", "IntersectFeatureOperation".
        """
        if not component or not isinstance(component, adsk.fusion.Component):
            raise ValueError("Valid component must be provided for combine_bodies.")

        op_map = {
            "JoinFeatureOperation": adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "CutFeatureOperation": adsk.fusion.FeatureOperations.CutFeatureOperation,
            "IntersectFeatureOperation": adsk.fusion.FeatureOperations.IntersectFeatureOperation
        }
        operation = op_map.get(operation_str)
        if operation is None:
            raise ValueError(f"Invalid combine operation string: {operation_str}")

        combine_features = component.features.combineFeatures
        combine_input = combine_features.createInput(target_body, tool_bodies_collection)
        combine_input.operation = operation
        combine_input.isNewComponent = False # Combine within the same component
        
        combine_feature = combine_features.add(combine_input)
        # combine_feature.name = name # Naming features can be tricky with auto-naming
        return combine_feature


    def translate_component_occurrence(self, occurrence, x, y, z, is_relative=True):
        """Translates a component occurrence."""
        if not isinstance(occurrence, adsk.fusion.Occurrence):
            raise ValueError("Valid occurrence must be provided for translation.")

        current_transform = occurrence.transform
        new_vector = adsk.core.Vector3D.create(x, y, z)

        if is_relative:
            current_transform.translation = current_transform.translation.asVector().add(new_vector)
        else: # Absolute
            current_transform.translation = new_vector
        
        occurrence.transform = current_transform


    def get_root_component(self):
        return self.root_comp

    def get_construction_plane(self, component, plane_name):
        """Returns a standard construction plane from the component."""
        plane_name_lower = plane_name.lower()
        if plane_name_lower == "xy":
            return component.xYConstructionPlane
        elif plane_name_lower == "xz":
            return component.xZConstructionPlane
        elif plane_name_lower == "yz":
            return component.yZConstructionPlane
        self.ui.messageBox(f"Unknown construction plane name: {plane_name}")
        return component.xYConstructionPlane # Default

    def get_construction_axis(self, component, axis_name):
        """Returns a standard construction axis from the component."""
        axis_name_lower = axis_name.lower()
        if axis_name_lower == 'x':
            return component.xConstructionAxis
        elif axis_name_lower == 'y':
            return component.yConstructionAxis
        elif axis_name_lower == 'z':
            return component.zConstructionAxis
        self.ui.messageBox(f"Unknown construction axis name: {axis_name}")
        return component.zConstructionAxis # Default

    def create_value_input_real(self, value):
        """Creates a ValueInput from a real number (assuming current internal units, e.g., cm)."""
        return adsk.core.ValueInput.createByReal(value)

    def message_box(self, text):
        if self.ui:
            self.ui.messageBox(text)

    def get_component_from_occurrence(self, occurrence):
        """Gets the component from an occurrence."""
        if isinstance(occurrence, adsk.fusion.Occurrence):
            return occurrence.component
        return None # Or raise error

    def create_component_occurrence(self, target_component, name, transform_matrix=None):
        """
        Creates a new component occurrence within the target_component.
        transform_matrix: adsk.core.Matrix3D, optional.
        Returns the new Occurrence.
        """
        if not isinstance(target_component, adsk.fusion.Component):
            raise ValueError("Target for new occurrence must be a Component.")

        if transform_matrix is None:
            transform_matrix = adsk.core.Matrix3D.create() # Identity matrix
        
        new_occurrence = target_component.occurrences.addNewComponent(transform_matrix)
        if new_occurrence.component: # Name the underlying component
            new_occurrence.component.name = name
        return new_occurrence

    def add_circle(self, sketch_object, center_tuple, radius):
        """
        Adds a circle to the specified sketch using Fusion 360 API.
        Assumes center_tuple and radius are in millimeters (mm) as per cycloidal.py conventions.
        Converts these to centimeters (cm) for Fusion's internal API.
        """
        if not sketch_object or not isinstance(sketch_object, adsk.fusion.Sketch):
            # self.ui is not always available if wrapper is used outside command context.
            # Consider logging or raising error. For now, print to console if possible.
            print("FusionAPIWrapper.add_circle: Invalid sketch object.")
            # if self.ui: self.ui.messageBox("FusionAPIWrapper.add_circle: Invalid sketch object.")
            return None
        if radius <= 0:
            print("FusionAPIWrapper.add_circle: Radius must be positive.")
            # if self.ui: self.ui.messageBox("FusionAPIWrapper.add_circle: Radius must be positive.")
            return None

        # Convert center_tuple (mm) to Point3D (cm)
        center_x_cm = center_tuple[0] / 10.0
        center_y_cm = center_tuple[1] / 10.0
        center_z_cm = center_tuple[2] / 10.0 # Though Z is often 0 for sketches on XY
        center_point_internal = adsk.core.Point3D.create(center_x_cm, center_y_cm, center_z_cm)
        
        # Convert radius (mm) to internal units (cm)
        radius_internal = radius / 10.0

        sketch_circles = sketch_object.sketchCurves.sketchCircles
        new_circle = sketch_circles.addByCenterRadius(center_point_internal, radius_internal)
        return new_circle

    # --- Utility to collect bodies for operations ---
    def collect_bodies_from_features(self, features_list):
        """Collects all bodies from a list of features into an ObjectCollection."""
        body_collection = adsk.core.ObjectCollection.create()
        for feature in features_list:
            if hasattr(feature, 'bodies') and feature.bodies.count > 0:
                for i in range(feature.bodies.count):
                    body_collection.add(feature.bodies.item(i))
        return body_collection
        
    def collect_entities_for_pattern(self, objects_list):
        """
        Collects features or bodies into an ObjectCollection for patterning.
        Assumes objects_list contains features or bodies.
        """
        collection = adsk.core.ObjectCollection.create()
        for obj in objects_list:
            # This needs to be robust based on what kind of entities are being patterned
            # (e.g., features for CircularPatternFeatures, bodies for others)
            collection.add(obj)
        return collection

    def get_occurrence_body(self, occurrence_name, body_name_in_occurrence_component):
        """ Helper to get a specific body from a named occurrence. """
        occ = self.root_comp.occurrences.itemByName(occurrence_name)
        if not occ:
            self.ui.messageBox(f"Occurrence '{occurrence_name}' not found.")
            return None
        
        comp = occ.component
        body = comp.bRepBodies.itemByName(body_name_in_occurrence_component)
        if not body:
             # Sometimes bodies are directly under features after creation, try finding it more broadly
            if comp.features: # Check if there are features
                for feature in comp.features:
                    if hasattr(feature, 'bodies'):
                        for b in feature.bodies:
                            if b.name == body_name_in_occurrence_component:
                                return b
            self.ui.messageBox(f"Body '{body_name_in_occurrence_component}' not found in component '{comp.name}'.")
            return None
        return body
