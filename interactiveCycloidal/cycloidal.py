"""Create cycloidal gearbox"""

import FreeCAD as App
import Part
import math
# import traceback # Not used yet
# from . import fusionUtils # To be removed or replaced


# def run(context):
#     """ The function that is run by Fusion """
# 
#     default_name = 'Cycloidal' # The name which appears in the top bar
#     parameters = fusionUtils.Parameters()
# 
#     """Parameters to appear in the Fusion window
#         Parameters will apear in the order here with the following values:
#         name: the varuable name that will hold the valie
#         units: the units that the value will be converted to. "" for unitless
#         description: the text which will appear with the box
#         default_value: the initial value that will appear before being edited """
# 
#     parameters.addParameter('rotorThickness', "mm", 'Rotor Thickness', .635)
#     parameters.addParameter('housingThickness', "mm", 'Housing Thickness', .635*2)
#     parameters.addParameter('R', "mm", 'Radius', 5)
#     parameters.addParameter('N', "", 'Number of pins', 10)
#     parameters.addParameter('bore', "mm", 'Bore Diameter', 1)
#     parameters.addParameter('numGears', "", 'Number of gears', 1)
#     parameters.addParameter('numHoles', "", 'Number of drive holes', 0)
#     parameters.addParameter('holePinDiameter', "mm", 'Diameter of drive pins', .25)
#     parameters.addParameter('holeCircleDiameter', "mm", 'Diameter of hole circle', 3)
#     parameters.addParameter('eccentricityRatio', "", 'Eccentricity Ratio', .5)
# 
#     created_object = CreatedObject() # Create an instance of the designed class
#     fusionUtils.run(parameters, default_name, created_object)

# def run():
#     """ Placeholder for the main execution function for FreeCAD """
#     # This function will be responsible for setting up parameters 
#     # and calling the build method of CreatedObject.
#     # For now, we can manually define some parameters for testing.
#     params = {
#         'rotorThickness': 6.35, # mm
#         'R': 50.0,              # mm
#         'N': 10,                # Number of pins
#         'eccentricityRatio': 0.5,
#         # Add other necessary parameters with default values
#         'housingThickness': 12.7,
#         'bore': 10.0,
#         'numGears': 1,
#         'numHoles': 0,
#         'holePinDiameter': 2.5,
#         'holeCircleDiameter': 30.0
#     }
#     obj = CreatedObject()
#     obj.parameters = params
#     obj.build() # Removed app and ui, will use App and Gui if needed


class CreatedObject:
    """ The class which contains definitions to create the part """

    def __init__(self):
        self.parameters = {} # Ensure parameters are initialized

    def build(self): # Removed app, ui arguments
        """ Perform the features to create the component """

        # newComp = fusionUtils.createNewComponent(app) # Fusion specific
        # if newComp is None:
        #     ui.messageBox('New component failed to create', 'New Component Failed')
        #     return

        doc = App.ActiveDocument
        if not doc:
            doc = App.newDocument("CycloidalDrive")

        # Copy parameters into local variables for ease of use
        eccentricityRatio = self.parameters["eccentricityRatio"]
        rotorThickness = self.parameters["rotorThickness"]
        housingThickness = self.parameters["housingThickness"] # Not used in this part
        R = self.parameters["R"]
        N = self.parameters["N"]
        bore = self.parameters["bore"] 
        numGears = self.parameters["numGears"]
        numHoles = self.parameters["numHoles"] 
        holePinDiameter = self.parameters["holePinDiameter"] 
        holeCircleDiameter = self.parameters["holeCircleDiameter"] 
        # units_mgr = app.activeProduct.unitsManager # Fusion specific

        #other constants based on the original inputs
        housing_cir = 2 * R * math.pi
        Rr = housing_cir / (4 * N)#roller radius
        E = eccentricityRatio * Rr#eccentricity
        maxDist = 0.25 * Rr #maximum allowed distance between points
        minDist = 0.5 * maxDist #the minimum allowed distance between points
        
        
        # product = app.activeProduct # Fusion specific
        # design = adsk.fusion.Design.cast(product) # Fusion specific
        # root = design.rootComponent # Fusion specific

        # rotorOcc = root.occurrences.addNewComponent(adsk.core.Matrix3D.create()) # Fusion specific
        # rotor = rotorOcc.component # Fusion specific
        # rotor.name = 'rotor' # Fusion specific
        rotor_obj = doc.addObject("Part::Feature", "Rotor")


        # sk = rotor.sketches.add(root.xYConstructionPlane) # Fusion specific

        # points = adsk.core.ObjectCollection.create() # Fusion specific
        fc_points = []


        #ui.messageBox('Ratio will be ' + 1/N) # UI specific

        (xs, ys) = getPoint(0, R, Rr, E, N)
        # points.add(adsk.core.Point3D.create(xs,ys,0)) # Fusion specific
        fc_points.append(App.Vector(xs, ys, 0))


        et = 2 * math.pi / (N-1)
        (xe, ye) = getPoint(et, R, Rr, E, N)
        x = xs
        y = ys
        dist = 0
        ct = 0
        dt = math.pi / N
        numPoints = 0

        while ((math.sqrt((x-xe)**2 + (y-ye)**2) > maxDist or ct < et/2) and ct < et): #close enough to the end to call it, but over half way
        #while (ct < et/80): #close enough to the end to call it, but over half way
            (xt, yt) = getPoint(ct+dt, R, Rr, E, N)
            dist = getDist(x, y, xt, yt)

            ddt = dt/2
            lastTooBig = False
            lastTooSmall = False

            while (dist > maxDist or dist < minDist):
                if (dist > maxDist):
                    if (lastTooSmall):
                        ddt /= 2

                    lastTooSmall = False
                    lastTooBig = True

                    if (ddt > dt/2):
                        ddt = dt/2

                    dt -= ddt

                elif (dist < minDist):
                    if (lastTooBig):
                        ddt /= 2

                    lastTooSmall = True
                    lastTooBig = False
                    dt += ddt


                (xt, yt) = getPoint(ct+dt, R, Rr, E, N)
                dist = getDist(x, y, xt, yt)

            x = xt
            y = yt
            # points.add(adsk.core.Point3D.create(x,y,0)) # Fusion specific
            fc_points.append(App.Vector(x, y, 0))
            numPoints += 1
            ct += dt

        # points.add(adsk.core.Point3D.create(xe,ye,0)) # Fusion specific
        fc_points.append(App.Vector(xe, ye, 0))
        
        # crv = sk.sketchCurves.sketchFittedSplines.add(points) # Fusion specific
        geom_curve = Part.BSplineCurve()
        geom_curve.setPoles(fc_points)
        cycloid_edge = geom_curve.toShape()

        # lines = sk.sketchCurves.sketchLines # Fusion specific
        # line1 = lines.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), crv.startSketchPoint) # Fusion specific
        # line2 = lines.addByTwoPoints(line1.startSketchPoint, crv.endSketchPoint) # Fusion specific
        start_point_vector = fc_points[0]
        end_point_vector = fc_points[-1]
        center_point_vector = App.Vector(0,0,0)
        line1_edge = Part.LineSegment(center_point_vector, start_point_vector).toShape()
        line2_edge = Part.LineSegment(end_point_vector, center_point_vector).toShape()


        # prof = sk.profiles.item(0) # Fusion specific
        profile_wire = Part.Wire([line1_edge, cycloid_edge, line2_edge])
        profile_face = Part.Face(profile_wire)

        # distance = adsk.core.ValueInput.createByReal(rotorThickness) # Fusion specific
        rotor_solid = profile_face.extrude(App.Vector(0, 0, rotorThickness))
        
        # Rotor Circular Pattern
        num_total_lobes = N - 1
        final_rotor_shape = None

        if num_total_lobes <= 0:
            App.Console.PrintWarning(f"N value is {N}, resulting in {num_total_lobes} lobes. Rotor will be an empty shape.\n")
            final_rotor_shape = Part.Shape() # Create an empty shape
        elif num_total_lobes == 1:
            final_rotor_shape = rotor_solid
        else: # num_total_lobes > 1
            angle_step = 360.0 / num_total_lobes
            
            solids_list = [rotor_solid] # Start with the first lobe
            
            # Loop to create and rotate N-2 additional copies
            # The loop should run N-2 times. If N-1 is total lobes, and 1 exists.
            # So, if i goes from 1 to num_total_lobes -1
            for i in range(1, num_total_lobes): 
                copied_lobe = rotor_solid.copy()
                rotation_angle = i * angle_step
                copied_lobe.rotate(App.Vector(0,0,0), App.Vector(0,0,1), rotation_angle)
                solids_list.append(copied_lobe)
            
            # Fuse the lobes
            if len(solids_list) > 1:
                fused_rotor = solids_list[0]
                for k in range(1, len(solids_list)):
                    fused_rotor = fused_rotor.fuse(solids_list[k])
                final_rotor_shape = fused_rotor
            else: # Should technically be covered by num_total_lobes == 1
                final_rotor_shape = solids_list[0]
        
        rotor_obj.Shape = final_rotor_shape

        # Rotor Offset
        if final_rotor_shape and not final_rotor_shape.isNull(): # Only offset if shape exists
            current_placement = rotor_obj.Placement
            new_translation = current_placement.Base + App.Vector(E, 0, 0)
            new_placement = App.Placement(new_translation, current_placement.Rotation)
            rotor_obj.Placement = new_placement
        
        doc.recompute()

        # # Get extrude features
        # extrudes = rotor.features.extrudeFeatures # Fusion specific
        # extrude1 = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation) # Fusion specific

        # # Get the extrusion body
        # body1 = extrude1.bodies.item(0) # Fusion specific
        # body1.name = "rotor" # Fusion specific

        # inputEntites = adsk.core.ObjectCollection.create() # Fusion specific
        # inputEntites.add(body1) # Fusion specific

        # # Get Z axis for circular pattern
        # zAxis = rotor.zConstructionAxis # Fusion specific

        # # Create the input for circular pattern
        # circularFeats = rotor.features.circularPatternFeatures # Fusion specific
        # circularFeatInput = circularFeats.createInput(inputEntites, zAxis) # Fusion specific

        # # Set the quantity of the elements
        # circularFeatInput.quantity = adsk.core.ValueInput.createByReal(N-1) # Fusion specific

        # # Set the angle of the circular pattern
        # circularFeatInput.totalAngle = adsk.core.ValueInput.createByString('360 deg') # Fusion specific

        # # Set symmetry of the circular pattern
        # circularFeatInput.isSymmetric = True # Fusion specific

        # # Create the circular pattern
        # circularFeat = circularFeats.add(circularFeatInput) # Fusion specific

        # ToolBodies = adsk.core.ObjectCollection.create() # Fusion specific
        # for b in circularFeat.bodies: # Fusion specific
            # ToolBodies.add(b) # Fusion specific

        # combineInput = rotor.features.combineFeatures.createInput(body1, ToolBodies) # Fusion specific
        # combineInput.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation # Fusion specific
        # combineInput.isNewComponent = False # Fusion specific

        # rotor.features.combineFeatures.add(combineInput) # Fusion specific

        # #Offset the rotor to make the shaft rotat concentric with origin
        # transform = rotorOcc.transform # Fusion specific
        # transform.translation = adsk.core.Vector3D.create(E, 0, 0) # Fusion specific
        # rotorOcc.transform = transform # Fusion specific
        # design.snapshots.add() # Fusion specific

        housing_obj = doc.addObject("Part::Feature", "Housing")

        if N <= 0:
            App.Console.PrintWarning(f"Number of pins N is {N}. Housing will be an empty shape.\n")
            housing_obj.Shape = Part.Shape()
        else:
            # Create a single roller (pin)
            roller_center_pos = App.Vector(R, 0, 0) # Centered at (R,0,0) for the first pin
            roller_axis_dir = App.Vector(0, 0, 1) # Extruded along Z
            single_roller_solid = Part.makeCylinder(Rr, housingThickness, roller_center_pos, roller_axis_dir)

            all_roller_solids = []
            roller_angle_step = 360.0 / N

            for i in range(N): # Loop N times, from 0 to N-1
                current_roller = single_roller_solid.copy()
                rotation_angle = i * roller_angle_step
                # Rotate around Z-axis, using origin as center
                current_roller.rotate(App.Vector(0,0,0), App.Vector(0,0,1), rotation_angle)
                all_roller_solids.append(current_roller)
            
            if all_roller_solids:
                rollers_compound = Part.Compound(all_roller_solids)
                housing_obj.Shape = rollers_compound
            else: # Should not happen if N > 0
                App.Console.PrintWarning("Roller solids list is empty even though N > 0. Housing will be empty.\n")
                housing_obj.Shape = Part.Shape()

        # #add a sketch so rotor clearance is obvious # Fusion specific code, can be removed or adapted later
        # sketches = housing.sketches # Fusion specific
        # rotorClearanceSketch = sketches.add(root.xYConstructionPlane) # Fusion specific
        # sketchCircles = rotorClearanceSketch.sketchCurves.sketchCircles # Fusion specific
        # centerPoint = adsk.core.Point3D.create(0, 0, 0) # Fusion specific
        # sketchCircles.addByCenterRadius(centerPoint, R) # Fusion specific

        # #add rollers # This section is now handled by the FreeCAD code above
        # rollerSketch = sketches.add(root.xYConstructionPlane) # Fusion specific
        # sketchCircles = rollerSketch.sketchCurves.sketchCircles # Fusion specific
        # centerPoint = adsk.core.Point3D.create(R, 0, 0) # Fusion specific
        # sketchCircles.addByCenterRadius(centerPoint, Rr ) # Fusion specific

        # rollerProfile = rollerSketch.profiles.item(0) # Fusion specific
        # distance = adsk.core.ValueInput.createByReal(housingThickness) # Fusion specific
        # rollerExtrudes = housing.features.extrudeFeatures.addSimple(rollerProfile, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation) # Fusion specific

        # # Get the extrusion body
        # roller = rollerExtrudes.bodies.item(0) # Fusion specific
        # roller.name = "roller" # Fusion specific

        # inputEntites = adsk.core.ObjectCollection.create() # Fusion specific
        # inputEntites.add(roller) # Fusion specific

        # # Create the input for circular pattern
        # circularFeats = housing.features.circularPatternFeatures # Fusion specific
        # zAxis = housing.zConstructionAxis # Fusion specific
        # circularFeatInput = circularFeats.createInput(inputEntites, zAxis) # Fusion specific

        # # Set the quantity of the elements
        # circularFeatInput.quantity = adsk.core.ValueInput.createByReal(N) # Fusion specific

        # # Set the angle of the circular pattern
        # circularFeatInput.totalAngle = adsk.core.ValueInput.createByString('360 deg') # Fusion specific

        # # Set symmetry of the circular pattern
        # circularFeatInput.isSymmetric = True # Fusion specific

        # # Create the circular pattern
        # circularFeat = circularFeats.add(circularFeatInput) # Fusion specific


        # # create center hole
        if rotor_obj.Shape and not rotor_obj.Shape.isNull():
            hole_radius = bore / 2
            # The rotor is already offset by E, so the hole should be at the local origin of the rotor object's current placement.
            # However, the rotor's shape itself is defined with its geometric center at (0,0,0) before the Placement is applied.
            # The Placement of rotor_obj is (E,0,0). So a cylinder at (E,0,0) in global coords is correct.
            hole_pos = App.Vector(E, 0, 0) 
            hole_axis = App.Vector(0, 0, 1)
            center_hole_cyl = Part.makeCylinder(hole_radius, rotorThickness, hole_pos, hole_axis)
            rotor_obj.Shape = rotor_obj.Shape.cut(center_hole_cyl)

        # #Create holes for pins
        if numHoles > 0 and rotor_obj.Shape and not rotor_obj.Shape.isNull():
            pin_hole_radius = holePinDiameter / 2
            # First pin hole is at (E, holeCircleDiameter/2, 0) in global coordinates,
            # which is (0, holeCircleDiameter/2, 0) relative to the rotor's eccentric center (E,0,0)
            first_pin_hole_pos = App.Vector(E, holeCircleDiameter / 2, 0)
            single_pin_cyl = Part.makeCylinder(pin_hole_radius, rotorThickness, first_pin_hole_pos, App.Vector(0,0,1))

            all_pin_hole_cyls_shape = None
            if numHoles == 1:
                all_pin_hole_cyls_shape = single_pin_cyl
            elif numHoles > 1:
                pin_hole_solids = []
                pin_pattern_angle_step = 360.0 / numHoles
                pattern_center = App.Vector(E, 0, 0) # Pattern around rotor's eccentric center
                pattern_axis = App.Vector(0,0,1)

                for j in range(numHoles): # Loop numHoles times
                    current_pin_hole_cyl = single_pin_cyl.copy()
                    pin_rotation_angle = j * pin_pattern_angle_step
                    # Rotate the cylinder which is already at first_pin_hole_pos
                    # The rotation is around pattern_center
                    current_pin_hole_cyl.rotate(pattern_center, pattern_axis, pin_rotation_angle)
                    pin_hole_solids.append(current_pin_hole_cyl)
                
                if pin_hole_solids:
                    all_pin_hole_cyls_shape = pin_hole_solids[0]
                    for k_pin in range(1, len(pin_hole_solids)):
                        all_pin_hole_cyls_shape = all_pin_hole_cyls_shape.fuse(pin_hole_solids[k_pin])
            
            if all_pin_hole_cyls_shape and not all_pin_hole_cyls_shape.isNull():
                rotor_obj.Shape = rotor_obj.Shape.cut(all_pin_hole_cyls_shape)

        # # Create multiple gears
        if rotor_obj.Shape and not rotor_obj.Shape.isNull() and int(numGears) > 1:
            base_rotor_shape_for_stacking = rotor_obj.Shape.copy() # This is the first gear

            for gear_copy_idx in range(1, int(numGears)): # Loop for additional gears
                additional_gear = base_rotor_shape_for_stacking.copy()
                
                current_z_offset = gear_copy_idx * rotorThickness
                additional_gear.translate(App.Vector(0, 0, current_z_offset))
                
                # Conditional Rotation: 1st copy (2nd gear) rotates, 3rd copy (4th gear) rotates, etc.
                if (gear_copy_idx -1) % 2 == 0:
                    # Rotation center for this specific gear, which is already translated.
                    # The shape's geometry is defined relative to (0,0,0) before rotor_obj.Placement.
                    # So, for the shape itself, rotation is around its own X=0, Y=0, Z=current_z_offset + thickness/2
                    rot_center = App.Vector(0, 0, current_z_offset + rotorThickness / 2)
                    rot_axis = App.Vector(0, 1, 0) # Global Y-axis
                    additional_gear.rotate(rot_center, rot_axis, 180)
                
                rotor_obj.Shape = rotor_obj.Shape.fuse(additional_gear)

        # body = body1 # Fusion specific # Keep this commented
        
        # # Check to see if the body is in the root component or another one.
        # target = None # Fusion specific
        # if body.assemblyContext: # Fusion specific
            # # It's in another component.
            # target = body.assemblyContext # Fusion specific
        # else: # Fusion specific
            # # It's in the root component.
            # target = root # Fusion specific

        # # Get the xSize.
        # xSize = body.boundingBox.maxPoint.x - body.boundingBox.minPoint.x # Fusion specific            

        # # Create several copies of the body.
        # currentZ = 0 # Fusion specific
        # for i in range(0,int(numGears)-1): # Fusion specific
            # # Create the copy.
            # newBody = body.copyToComponent(target) # Fusion specific
            
            # # Increment the position.            
            # currentZ +=  rotorThickness # Fusion specific

            # trans = adsk.core.Matrix3D.create() # Fusion specific
            # trans.translation = adsk.core.Vector3D.create(0, 0, currentZ) # Fusion specific
            

            # # Move the body using a move feature.
            # bodyColl = adsk.core.ObjectCollection.create() # Fusion specific
            # bodyColl.add(newBody) # Fusion specific
            # moveInput = root.features.moveFeatures.createInput(bodyColl, trans) # Fusion specific
            # moveFeat = root.features.moveFeatures.add(moveInput) # Fusion specific
            
            # if (i%2 == 0): # Fusion specific
                # rotation = adsk.core.Matrix3D.create() # Fusion specific
                # rotation.setToRotation(units_mgr.convert(180, "deg", "rad"), root.yConstructionAxis.geometry.getData()[2], adsk.core.Point3D.create(0, 0, currentZ + rotorThickness/2)) # Fusion specific
                # moveInput2 = root.features.moveFeatures.createInput(bodyColl, rotation) # Fusion specific
                # moveFeat = root.features.moveFeatures.add(moveInput2) # Fusion specific


def getPoint(t, R, Rr, E, N):
    """ Get a point on a cycloid with the given parameters

        t: parameter
        R: major radius
        Rr: rolling radius
        E: eccentricity
        N: number of pins """
    psi = math.atan2(math.sin((1-N)*t), ((R/(E*N))-math.cos((1-N)*t)))
    x = (R*math.cos(t))-(Rr*math.cos(t+psi))-(E*math.cos(N*t))
    y = (-R*math.sin(t))+(Rr*math.sin(t+psi))+(E*math.sin(N*t))
    return (x,y)


def getDist(xa, ya, xb, yb):
    """ Get distance between two 2D points (xa,ya) and (xb,yb)"""
    return math.sqrt((xa-xb)**2 + (ya-yb)**2)
