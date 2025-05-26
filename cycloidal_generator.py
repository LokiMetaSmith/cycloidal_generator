# Author - mawildoer
# Description - cycloidal drive generator (Refactored for FreeCAD)

import FreeCAD as App
import Part
import math

def getPoint(t, R, Rr, E, N):
    psi = math.atan2(math.sin((1-N)*t), ((R/(E*N))-math.cos((1-N)*t)))
    x = (R*math.cos(t))-(Rr*math.cos(t+psi))-(E*math.cos(N*t))
    y = (-R*math.sin(t))+(Rr*math.sin(t+psi))+(E*math.sin(N*t))
    return (x,y)

def getDist(xa, ya, xb, yb):
    return math.sqrt((xa-xb)**2 + (ya-yb)**2)

def run():
    doc = App.ActiveDocument if App.ActiveDocument else App.newDocument("CycloidalGen")

    #####   HARDCODED PARAMETERS (as per original script) #####
    rotorThickness = 1.0 # rotor thickness(cm) - Using float for FreeCAD units
    housingThickness = 2.0 * rotorThickness
    R = 5.0 # rotor radius (cm)
    N = 50 # number of rollers
    ####################################################

    # Other constants based on the original inputs
    housing_cir = 2 * R * math.pi
    Rr = housing_cir / (4 * N) # roller radius
    E = 0.5 * Rr # eccentricity
    maxDist = 0.25 * Rr # maximum allowed distance between points
    minDist = 0.5 * maxDist # the minimum allowed distance between points

    # Rotor Generation
    rotor_obj = doc.addObject("Part::Feature", "GeneratedRotor")
    fc_points = []

    (xs, ys) = getPoint(0, R, Rr, E, N)
    fc_points.append(App.Vector(xs, ys, 0))

    # Corrected et for N-1 lobes, but point generation logic uses N for some angle calculations.
    # The original Fusion script used N-1 for the 'et' parameter, which is the angle for one segment of the N-1 lobes.
    # The getPoint function itself seems to handle the cycloidal math based on N.
    # If N is total rollers, then N-1 is total lobes on the rotor.
    if N - 1 <= 0: # Need at least one lobe for et to be valid
        App.Console.PrintWarning(f"N value ({N}) is too small to form lobes. Rotor will be empty.\n")
        rotor_obj.Shape = Part.Shape()
    else:
        et = 2 * math.pi / (N - 1) # Angle for one full lobe segment
        (xe, ye) = getPoint(et, R, Rr, E, N)
        x = xs
        y = ys
        dist = 0
        ct = 0 # Current angle in the generation of a single lobe segment
        # dt is an adaptive step, initialized based on N for overall smoothness.
        # This dt is for generating points within a single lobe, not the angle between lobes.
        dt = math.pi / N 
        numPoints = 0

        while ((math.sqrt((x-xe)**2 + (y-ye)**2) > maxDist or ct < et/2) and ct < et):
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
            fc_points.append(App.Vector(x, y, 0))
            numPoints += 1
            ct += dt

        fc_points.append(App.Vector(xe, ye, 0))
        
        geom_curve = Part.BSplineCurve()
        geom_curve.setPoles(fc_points)
        # cycloid_edge = Part.Edge(geom_curve) # This is incorrect, use toShape()
        cycloid_edge = geom_curve.toShape()


        line1_edge = Part.LineSegment(App.Vector(0,0,0), fc_points[0]).toShape()
        line2_edge = Part.LineSegment(fc_points[-1], App.Vector(0,0,0)).toShape()

        profile_wire = Part.Wire([line1_edge, cycloid_edge, line2_edge])
        if not profile_wire.isClosed():
            App.Console.PrintWarning("Profile wire for rotor lobe is not closed. Attempting to fix.\n")
            # Attempt to force close, or check points more carefully
            edges = [line1_edge, cycloid_edge, line2_edge]
            if line2_edge.LastVertex.Point.distanceToPoint(line1_edge.FirstVertex.Point) < 1e-5 : # Check if end of line2 meets start of line1
                 profile_wire = Part.Wire(edges)
            else: # Add a segment if there is a gap
                 closing_segment = Part.LineSegment(line2_edge.LastVertex.Point, line1_edge.FirstVertex.Point).toShape()
                 edges.append(closing_segment)
                 profile_wire = Part.Wire(edges)

        profile_face = Part.Face(profile_wire)
        single_lobe_solid = profile_face.extrude(App.Vector(0, 0, rotorThickness))

        num_lobes = N - 1 # N rollers means N-1 lobes for the rotor
        final_rotor_shape = None

        if num_lobes <= 0:
            App.Console.PrintWarning(f"N value ({N}) results in {num_lobes} lobes. Rotor will be an empty shape.\n")
            final_rotor_shape = Part.Shape()
        elif num_lobes == 1:
            final_rotor_shape = single_lobe_solid
        else:
            lobe_solids = [single_lobe_solid]
            angle_step = 360.0 / num_lobes
            for i in range(1, num_lobes): # Create num_lobes-1 copies
                copied_lobe = single_lobe_solid.copy()
                copied_lobe.rotate(App.Vector(0,0,0), App.Vector(0,0,1), i * angle_step)
                lobe_solids.append(copied_lobe)
            
            fused_lobes = lobe_solids[0]
            for k in range(1, len(lobe_solids)):
                fused_lobes = fused_lobes.fuse(lobe_solids[k])
            final_rotor_shape = fused_lobes
        
        rotor_obj.Shape = final_rotor_shape
        rotor_obj.Placement = App.Placement(App.Vector(E,0,0), App.Rotation())

    # Housing and Rollers Generation
    housing_obj = doc.addObject("Part::Feature", "GeneratedHousing")
    if N <= 0:
        App.Console.PrintWarning(f"N value ({N}) is zero or negative. Housing will be an empty shape.\n")
        housing_obj.Shape = Part.Shape()
    else:
        single_roller_solid = Part.makeCylinder(Rr, housingThickness, App.Vector(R,0,0), App.Vector(0,0,1))
        all_roller_solids = [single_roller_solid] # Start with the first one
        
        if N > 1: # Only pattern if more than one roller
            roller_angle_step = 360.0 / N
            for i in range(1, N): # Create N-1 copies
                copied_roller = single_roller_solid.copy()
                copied_roller.rotate(App.Vector(0,0,0), App.Vector(0,0,1), i * roller_angle_step)
                all_roller_solids.append(copied_roller)
        
        if all_roller_solids:
             rollers_compound = Part.Compound(all_roller_solids)
             housing_obj.Shape = rollers_compound
        else: # Should not happen if N > 0
             App.Console.PrintWarning("Roller solids list is empty even though N > 0. Housing will be empty.\n")
             housing_obj.Shape = Part.Shape()

    doc.recompute()
    
    # Keep getPoint and getDist functions as they are.
    # Removed Fusion-specific UI calls and traceback handling.

# Example of how to run this if it's in a FreeCAD macro:
# run()
