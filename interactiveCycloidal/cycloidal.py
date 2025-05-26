import traceback
import math
# Removed adsk.core, adsk.fusion as they are now abstracted by the wrapper
from . import fusionUtils # Still needed for the run() entry point and Parameters
# The specific wrappers will be imported by the entry points (run() here, or freecad_runner.py)

# Geometric helper functions (CAD Agnostic)
def getPoint(t, R, Rr, E, N):
    psi = math.atan2(math.sin((1-N)*t), ((R/(E*N))-math.cos((1-N)*t)))
    x = (R*math.cos(t))-(Rr*math.cos(t+psi))-(E*math.cos(N*t))
    y = (-R*math.sin(t))+(Rr*math.sin(t+psi))+(E*math.sin(N*t))
    return (x,y)

def getDist(xa, ya, xb, yb):
    return math.sqrt((xa-xb)**2 + (ya-yb)**2)

# Main class for creating the cycloidal drive
class CreatedObject:
    def __init__(self, cad_api_wrapper):
        self.cad_api = cad_api_wrapper
        self.parameters = {} # Parameters will be populated by the calling script

    def build(self):
        # Get the root component/document context from the wrapper
        # In Fusion, this is rootComponent. In FreeCAD, this is the document.
        root_model_context = self.cad_api.get_root_component()

        # Copy parameters into local variables for ease of use.
        # IMPORTANT: Assuming these parameters are in MM.
        # The wrapper's create_value_input_real or direct usage should handle units.
        rotorThickness = self.parameters["rotorThickness"]
        housingThickness = self.parameters["housingThickness"]
        R = self.parameters["R"] # Major radius in mm
        N = self.parameters["N"] # Number of pins/rollers
        bore = self.parameters["bore"] # Bore diameter in mm
        numGears = self.parameters["numGears"]
        numHoles = self.parameters["numHoles"]
        holePinDiameter = self.parameters["holePinDiameter"]
        holeCircleDiameter = self.parameters["holeCircleDiameter"]
        eccentricityRatio = self.parameters["eccentricityRatio"]

        # Derived constants
        housing_cir = 2 * R * math.pi
        Rr = housing_cir / (4 * N) # Roller radius in mm
        E = eccentricityRatio * Rr # Eccentricity in mm
        maxDist = 0.25 * Rr
        minDist = 0.5 * maxDist
        
        # --- Create Rotor ---
        # In Fusion, components are occurrences in the root. In FreeCAD, could be App::Part in the doc.
        rotor_comp_obj = self.cad_api.create_component_occurrence(root_model_context, 'RotorComponent')
        # Get the actual component/part context from this occurrence/group for adding features
        rotor_context = self.cad_api.get_component_from_occurrence(rotor_comp_obj)
        if rotor_context is None: # Safety check if wrapper could not get/create component
             self.cad_api.message_box("Failed to create or get rotor component context.")
             return

        xy_plane_rotor = self.cad_api.get_construction_plane(rotor_context, 'xy')
        rotor_sketch = self.cad_api.create_sketch_on_xy_plane(rotor_context, 'rotor_profile_sketch')

        points_data = []
        (xs, ys) = getPoint(0, R, Rr, E, N)
        points_data.append((xs, ys, 0))

        et = 2 * math.pi / (N - 1)
        (xe, ye) = getPoint(et, R, Rr, E, N)
        
        current_t = 0
        current_x, current_y = xs, ys
        
        # Calculate points for the spline
        # This loop logic is from the original script
        dt_param = math.pi / N 
        num_spline_points = 0
        temp_points_for_spline = [(xs,ys,0)]

        while ((math.sqrt((current_x - xe)**2 + (current_y - ye)**2) > maxDist or current_t < et / 2) and current_t < et):
            (next_x_try, next_y_try) = getPoint(current_t + dt_param, R, Rr, E, N)
            dist_try = getDist(current_x, current_y, next_x_try, next_y_try)
            
            ddt_adj = dt_param / 2
            last_too_big = False
            last_too_small = False

            while (dist_try > maxDist or dist_try < minDist):
                if (dist_try > maxDist):
                    if (last_too_small):
                        ddt_adj /= 2
                    last_too_small = False
                    last_too_big = True
                    if (ddt_adj > dt_param/2): # Prevent ddt from growing too large
                        ddt_adj = dt_param/2
                    dt_param -= ddt_adj
                elif (dist_try < minDist):
                    if (last_too_big):
                        ddt_adj /= 2
                    last_too_small = True
                    last_too_big = False
                    dt_param += ddt_adj
                
                (next_x_try, next_y_try) = getPoint(current_t + dt_param, R, Rr, E, N)
                dist_try = getDist(current_x, current_y, next_x_try, next_y_try)

            current_x, current_y = next_x_try, next_y_try
            temp_points_for_spline.append((current_x, current_y, 0))
            num_spline_points +=1
            current_t += dt_param
            
        temp_points_for_spline.append((xe, ye, 0))
        
        point_collection_rotor_spline = self.cad_api.add_points_to_collection(temp_points_for_spline)
        rotor_spline = self.cad_api.add_fitted_spline(rotor_sketch, point_collection_rotor_spline)

        # Add lines to close the profile (center to spline ends)
        # Need to get start/end points from the spline if API supports it, or use xs,ys,xe,ye
        # For now, assume (xs,ys) and (xe,ye) are correct start/end points of the drawn spline geometry
        start_spline_point_data = temp_points_for_spline[0]
        end_spline_point_data = temp_points_for_spline[-1]

        lines_to_add = [
            ((0,0,0), start_spline_point_data),
            ((0,0,0), end_spline_point_data)
        ]
        self.cad_api.add_line_segments_to_sketch(rotor_sketch, lines_to_add)
        
        rotor_profile = self.cad_api.get_profile_from_sketch(rotor_sketch)
        
        # Extrude the rotor
        # The cad_api.extrude method should handle component context internally if needed
        rotor_extrusion_thickness = self.cad_api.create_value_input_real(rotorThickness) # Wrapper handles units
        rotor_solid_feature = self.cad_api.extrude(
            rotor_profile, 
            rotor_extrusion_thickness, 
            'rotor_initial_solid', 
            operation_type="NewBodyFeatureOperation" # Standard string for op type
        )
        # Let's assume rotor_solid_feature is the main body or feature we need for patterning/combines

        # Circular pattern for rotor lobes
        # The entity to pattern is the rotor_solid_feature or its body
        # Fusion needs an ObjectCollection. FreeCAD might take the object name or object itself.
        # The wrapper's collect_entities_for_pattern should handle this.
        entities_to_pattern_rotor = self.cad_api.collect_entities_for_pattern([rotor_solid_feature])
        z_axis_rotor = self.cad_api.get_construction_axis(rotor_context, 'z')
        
        # Quantity for pattern: N-1 for the cycloidal lobes as per original logic
        pattern_quantity_rotor = N - 1 
        if pattern_quantity_rotor > 0 : # Only pattern if more than one segment needed
            rotor_pattern_feature = self.cad_api.circular_pattern(
                entities_to_pattern_rotor, 
                z_axis_rotor, 
                pattern_quantity_rotor, 
                '360 deg', # total angle as string
                'rotor_lobe_pattern'
            )
            # Combine the patterned bodies with the first one
            # This requires getting all bodies from the pattern and the initial extrusion
            # The API wrapper should provide a way to get these bodies
            # For now, assuming combine_bodies can take the main feature and the pattern feature
            # This part is tricky and depends heavily on wrapper implementation details.
            # A robust way: get all bodies from rotor_solid_feature and rotor_pattern_feature.
            # FusionAPIWrapper.collect_bodies_from_features might be useful.
            # Let's assume for now the wrapper's combine can handle features if they produce bodies.
            
            # Simplified: Assume rotor_solid_feature is the target, and pattern creates tools
            # This needs careful implementation in wrappers.
            # A common strategy is to get a list of all body objects.
            # For now, let's assume rotor_pattern_feature results in "tool bodies"
            # and rotor_solid_feature is the "target body"
            
            # The original script combines the items from circularFeat.bodies with body1 (initial extrude)
            # The wrapper needs a way to get these "tool bodies" from the pattern feature.
            # This is a complex step to abstract perfectly without knowing how wrappers handle feature->body mapping.
            # Let's make a placeholder call, assuming combine_bodies is smart or we prepare inputs carefully.
            
            # If circular_pattern returns a list of bodies or a group:
            # For now, this combine step is simplified and might need adjustment based on wrapper behavior
            # The original logic joins all patterned bodies together.
            # If rotor_pattern_feature IS the collection of all bodies (original + patterned)
            # then a combine isn't needed unless they are separate and need joining.
            # Fusion's pattern adds to the component. FreeCAD's might create a link array or copies.

            # Let's assume the pattern creates *new* bodies, and we want to join them to the *first* one.
            # This logic needs refinement based on how wrappers return patterned objects.
            # If the pattern feature itself represents all the bodies combined, no extra combine is needed.
            # If it returns a list of new bodies, they need to be combined.
            # The Fusion script does a combine. So let's try to emulate.
            
            # This is a conceptual placeholder for "get all bodies of the pattern"
            # tool_bodies_from_pattern = self.cad_api.get_bodies_from_feature(rotor_pattern_feature)
            # self.cad_api.combine_bodies(
            #     rotor_solid_feature, # target
            #     tool_bodies_from_pattern, # tools
            #     "JoinFeatureOperation",
            #     "combined_rotor_lobes"
            # )
            self.cad_api.message_box("Rotor Patterned. Combine step for rotor lobes needs review based on wrapper behavior.")
        else: # Only one segment, rotor_solid_feature is the final rotor shape before translation
             pass


        # Offset the rotor
        self.cad_api.translate_component_occurrence(rotor_comp_obj, E, 0, 0)
        # If snapshot is needed, wrapper should handle it or have a method.
        # self.cad_api.add_snapshot("Rotor complete")


        # --- Create Housing ---
        housing_comp_obj = self.cad_api.create_component_occurrence(root_model_context, 'HousingComponent')
        housing_context = self.cad_api.get_component_from_occurrence(housing_comp_obj)
        if housing_context is None:
            self.cad_api.message_box("Failed to create or get housing component context.")
            return

        xy_plane_housing = self.cad_api.get_construction_plane(housing_context, 'xy')

        # Add a sketch for rotor clearance visualization
        rotor_clearance_sketch = self.cad_api.create_sketch_on_xy_plane(housing_context, 'rotor_clearance_viz')
        self.cad_api.add_circle(rotor_clearance_sketch, (0,0,0), R) # R is major radius


        # Add rollers
        roller_sketch = self.cad_api.create_sketch_on_xy_plane(housing_context, 'roller_profile_sketch')
        self.cad_api.add_circle(roller_sketch, (R, 0, 0), Rr) # Rr is roller radius

        roller_profile = self.cad_api.get_profile_from_sketch(roller_sketch)
        
        roller_extrusion_thickness = self.cad_api.create_value_input_real(housingThickness)
        roller_solid_feature = self.cad_api.extrude(
            roller_profile, 
            roller_extrusion_thickness, 
            'roller_solid',
            operation_type="NewBodyFeatureOperation"
        )

        # Circular pattern for rollers
        entities_to_pattern_roller = self.cad_api.collect_entities_for_pattern([roller_solid_feature])
        z_axis_housing = self.cad_api.get_construction_axis(housing_context, 'z')
        
        housing_pattern_feature = self.cad_api.circular_pattern(
            entities_to_pattern_roller, 
            z_axis_housing, 
            N, # Number of rollers
            '360 deg',
            'roller_pattern'
        )
        # Similar to rotor, the combine logic for patterned rollers would go here if needed.
        # Fusion script implies pattern creates final set.

        # Create center bore for rotor (as a cut in the housing or rotor itself?)
        # Original script seems to add bore to housing, then holes to rotor (or vice-versa).
        # The Fusion code creates a centerHoleSketch, extrudes a cut.
        # This should likely be on the ROTOR component.
        # Let's assume it's a cut on the main rotor body/feature.
        # This requires getting the main rotor body after any combines.
        # For now, this part is complex due to component/body referencing.
        # Placeholder:
        self.cad_api.message_box("Center bore creation needs careful component/body referencing after refactor.")
        # if bore > 0:
        #     center_hole_sketch = self.cad_api.create_sketch_on_xy_plane(rotor_context, 'center_bore_sketch')
        #     # Add circle at (E,0,0) with radius bore/2
        #     # ... self.cad_api.add_circle(center_hole_sketch, (E,0,0), bore/2)
        #     center_hole_profile = self.cad_api.get_profile_from_sketch(center_hole_sketch)
        #     bore_cut_thickness = self.cad_api.create_value_input_real(rotorThickness)
        #     self.cad_api.extrude(
        #         rotor_context, # Target component for the cut
        #         center_hole_profile,
        #         bore_cut_thickness,
        #         'center_bore_cut',
        #         operation_type="CutFeatureOperation" # This needs a target body within the component
        #     )


        # Create holes for drive pins (on the rotor)
        # Placeholder, similar complexity to bore.
        self.cad_api.message_box("Drive pin holes creation needs careful component/body referencing.")
        # if numHoles > 0 and holePinDiameter > 0 and holeCircleDiameter > 0:
        #     pin_hole_sketch = self.cad_api.create_sketch_on_xy_plane(rotor_context, 'pin_holes_sketch')
        #     # Add circle at (E, holeCircleDiameter/2, 0) with radius holePinDiameter/2 + E (original logic seems complex here)
        #     # ... self.cad_api.add_circle(pin_hole_sketch, (E, holeCircleDiameter/2, 0), holePinDiameter/2)
        #     # ... (extrude cut, then pattern the cut feature)


        # Create multiple gears (stacking rotors)
        # Placeholder
        self.cad_api.message_box("Multiple gear stacking needs careful body copying and transformation logic within wrapper.")
        # if numGears > 1:
        #     # This requires copying the main rotor body and transforming it.
        #     # The wrapper would need a copy_body and transform_body/object method.
        #     pass

        self.cad_api.recompute() # Final recompute
        self.cad_api.message_box("Cycloidal drive generation attempted using CAD API wrapper.")


# --- Fusion 360 Specific Entry Point ---
# This part remains largely specific to how Fusion 360 add-ins are structured.
# It will now use the FusionAPIWrapper.

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Setup for Fusion UI - this part is from fusionUtils and original cycloidal.py
        default_name = 'CycloidalGeneratorViaWrapper'
        parameters_definition = fusionUtils.Parameters()
        parameters_definition.addParameter('rotorThickness', "mm", 'Rotor Thickness (mm)', 10.0) #Default 0.635cm -> 6.35mm
        parameters_definition.addParameter('housingThickness', "mm", 'Housing Thickness (mm)', 20.0) #Default 1.27cm -> 12.7mm
        parameters_definition.addParameter('R', "mm", 'Radius (mm)', 50.0) # Default 5cm -> 50mm
        parameters_definition.addParameter('N', "", 'Number of pins', 10)
        parameters_definition.addParameter('bore', "mm", 'Bore Diameter (mm)', 10.0)
        parameters_definition.addParameter('numGears', "", 'Number of gears', 1)
        parameters_definition.addParameter('numHoles', "", 'Number of drive holes', 0)
        parameters_definition.addParameter('holePinDiameter', "mm", 'Diameter of drive pins (mm)', 5.0)
        parameters_definition.addParameter('holeCircleDiameter', "mm", 'Diameter of hole circle (mm)', 30.0)
        parameters_definition.addParameter('eccentricityRatio', "", 'Eccentricity Ratio (0 to 1)', 0.5)

        # This is the callback that fusionUtils.run will trigger after parameters are collected
        def build_cycloidal_with_params(collected_parameters):
            try:
                # Import the FusionAPIWrapper here, assuming it's in fusionUtils.api_wrapper
                from .fusionUtils.api_wrapper import FusionAPIWrapper
                
                fusion_api = FusionAPIWrapper(app, ui)
                
                # Create the main object and pass the wrapper and parameters
                created_obj_instance = CreatedObject(fusion_api)
                created_obj_instance.parameters = collected_parameters # parameters are already evaluated by fusionUtils
                
                created_obj_instance.build()
                ui.messageBox("Build process completed via FusionAPIWrapper.")
            except:
                if ui:
                    ui.messageBox('Build failed:\n{}'.format(traceback.format_exc()))

        # Use a modified version of fusionUtils.run or a new mechanism
        # For now, let's assume fusionUtils.run can be adapted or we make a simplified call structure.
        # The original fusionUtils.run takes (parameters, default_name, createdObject_instance_for_build_method)
        # We need to adapt how parameters are passed to the CreatedObject.
        
        # Simplified: create a temporary handler structure similar to fusionUtils
        # This part needs careful integration with how fusionUtils sets up commands
        
        handlers = [] # Required by fusionUtils.CommandCreatedHandler
        
        # The CommandExecuteHandler in fusionUtils will be the one to call build_cycloidal_with_params
        # We need to ensure it gets the parameters correctly.
        # Let's create a simple "command object" that fusionUtils can use
        # which will then call our build_cycloidal_with_params.
        
        class TempCreatedObjectForFusion:
            def __init__(self, app_ref, ui_ref, params_callback):
                self.app = app_ref
                self.ui = ui_ref
                self.parameters_callback = params_callback # This will store collected params
                self.cad_api = None # Will be set by handler
                self.parameters = {} # Will be set by handler

            # This 'build' is what CommandExecuteHandler will call
            def build_fusion_entry(self): # Renamed to avoid conflict if direct class was used
                # Parameters should have been collected by Fusion's CommandInput system
                # and placed into self.parameters by the CommandExecuteHandler.
                self.parameters_callback(self.parameters)

        # This temp_obj's 'build_fusion_entry' method will be called by fusionUtils's CommandExecuteHandler
        # The handler will populate temp_obj.parameters with values from the UI.
        temp_obj_for_fusion_command = TempCreatedObjectForFusion(app, ui, build_cycloidal_with_params)

        # Call the fusionUtils entry point that sets up the UI and command handlers
        # This `run` function from fusionUtils expects an object that has a `build` method
        # and will receive parameters.
        # We need to ensure the CommandExecuteHandler in fusionUtils:
        # 1. Creates FusionAPIWrapper
        # 2. Assigns it to createdObject.cad_api
        # 3. Puts evaluated parameters into createdObject.parameters
        # 4. Calls createdObject.build()
        # This requires modification of fusionUtils CommandExecuteHandler.
        # For now, let's assume it's modified or we pass a simple object whose 'build' method
        # then calls our main logic.
        
        # The CommandExecuteHandler in fusionUtils.py needs to be adapted.
        # It expects an object, and it populates `object_class.parameters`.
        # Then it calls `object_class.build(self.app, self.ui)`.
        # We will pass `temp_obj_for_fusion_command` as the `object_class`.
        # Its `build_fusion_entry` method will then call `build_cycloidal_with_params`.
        # The parameters are already in `mm` as defined in `parameters_definition`.
        # `fusionUtils.CommandExecuteHandler` will convert them to numbers.
        
        fusionUtils.run(parameters_definition, default_name, temp_obj_for_fusion_command, build_method_name='build_fusion_entry')
        # Note: Added 'build_method_name' argument to fusionUtils.run to specify which method to call.
        # This requires a small modification to fusionUtils.run and CommandExecuteHandler.

    except:
        if ui:
            ui.messageBox('Failed at run setup:\n{}'.format(traceback.format_exc()))
