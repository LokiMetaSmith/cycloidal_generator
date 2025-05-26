# freecad_cycloidal_runner.py

import FreeCAD
import FreeCADGui # Needed for some operations like recompute or if using GUI elements
import Part # Needed for basic Part operations if not handled by wrapper fully
import Sketcher # Needed for sketch objects if not handled by wrapper fully

# Make sure the script can find the interactiveCycloidal module.
# This might require adding the parent directory of interactiveCycloidal to sys.path
# if running from an arbitrary location, or if FreeCAD's Python doesn't see it.
# For simplicity, assuming it's run in an environment where the module is discoverable.
import sys
import os
# Assuming this script is in the root, and interactiveCycloidal is a subdirectory.
# Adjust path if necessary, or ensure FreeCAD's Python path includes this project structure.
# script_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(script_dir) # If script was one level down
# sys.path.append(project_root) # Or script_dir if interactiveCycloidal is sibling

try:
    from interactiveCycloidal.cycloidal import CreatedObject, getPoint, getDist # Main class and helpers
    from interactiveCycloidal.freecadUtils.api_wrapper import FreeCADAPIWrapper
except ImportError as e:
    FreeCAD.Console.PrintError(f"Failed to import necessary modules: {e}\n")
    FreeCAD.Console.PrintError("Ensure the script is run from the project root or that interactiveCycloidal is in Python path.\n")
    # Example: Add current dir to path if interactiveCycloidal is a subfolder
    # sys.path.append(os.getcwd())
    # from interactiveCycloidal.cycloidal import CreatedObject
    # from interactiveCycloidal.freecadUtils.api_wrapper import FreeCADAPIWrapper
    raise # Re-raise after printing message, to stop execution if imports fail.

def run_generator_freecad():
    FreeCAD.Console.PrintMessage("Starting FreeCAD Cycloidal Drive Generator...\n")

    # Get active document or create a new one
    doc = FreeCAD.ActiveDocument
    if not doc:
        doc = FreeCAD.newDocument("CycloidalDriveProduct")
        FreeCAD.Console.PrintMessage("Created new document: CycloidalDriveProduct\n")
    
    # Initialize the FreeCAD API Wrapper
    try:
        fc_api_wrapper = FreeCADAPIWrapper(doc)
        FreeCAD.Console.PrintMessage("FreeCADAPIWrapper initialized.\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"Failed to initialize FreeCADAPIWrapper: {e}\n")
        return

    # Instantiate the main object that builds the geometry
    try:
        cycloid_obj = CreatedObject(fc_api_wrapper)
        FreeCAD.Console.PrintMessage("CreatedObject (cycloidal logic) initialized.\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"Failed to initialize CreatedObject: {e}\n")
        return

    # Define parameters for the cycloidal drive (all in mm for consistency)
    # These match the parameters defined in `interactiveCycloidal.cycloidal.run()` for Fusion
    cycloid_obj.parameters = {
        "rotorThickness": 10.0,     # mm
        "housingThickness": 12.0,   # mm (was 2*rotor, now explicit)
        "R": 50.0,                  # Major radius in mm
        "N": 10,                    # Number of pins/rollers
        "bore": 10.0,               # Bore diameter in mm
        "numGears": 1,              # Number of gears to stack
        "numHoles": 4,              # Number of drive holes on rotor
        "holePinDiameter": 5.0,     # Diameter of drive pins in mm
        "holeCircleDiameter": 30.0, # Diameter of the circle on which drive holes are placed (mm)
        "eccentricityRatio": 0.5    # Ratio (0 to 1), E = eccentricityRatio * Rr
    }
    FreeCAD.Console.PrintMessage(f"Parameters set: {cycloid_obj.parameters}\n")

    try:
        FreeCAD.Console.PrintMessage("Calling build()...\n")
        cycloid_obj.build()
        FreeCAD.Console.PrintMessage("Build process completed.\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error during cycloid_obj.build(): {e}\n")
        import traceback
        FreeCAD.Console.PrintError(traceback.format_exc() + "\n")
        return

    try:
        FreeCAD.Console.PrintMessage("Performing final document recompute and view fit...\n")
        doc.recompute()
        if FreeCAD.GuiUp: # Check if GUI is running
            FreeCADGui.ActiveDocument.recompute() # Recompute GUI representation
            FreeCADGui.SendMsgToActiveView("ViewFit") # Fit view to screen
        FreeCAD.Console.PrintMessage("FreeCAD Cycloidal Drive Generation Finished.\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error during final recompute/view fit: {e}\n")
        return

if __name__ == "__main__":
    # This allows running the script from FreeCAD's Python console using:
    # exec(open("path/to/freecad_cycloidal_runner.py").read())
    # Or by adding it as a macro.
    
    # Check if running inside FreeCAD
    if FreeCAD.GuiUp: # or hasattr(FreeCAD, "ActiveDocument")
        run_generator_freecad()
    else:
        # This case is if the script is run from a plain Python interpreter outside FreeCAD
        # which is not the primary use case for this runner.
        print("This script is intended to be run from within FreeCAD.")
        print("Attempting to run FreeCAD related parts - this will likely fail if FreeCAD modules are not available.")
        # For testing module structure outside FreeCAD (very limited):
        # try:
        #     from interactiveCycloidal.cycloidal import CreatedObject
        #     print("Successfully imported CreatedObject outside FreeCAD (structure test).")
        # except ImportError as e:
        #     print(f"Failed to import CreatedObject outside FreeCAD: {e}")
        #     print("Ensure your PYTHONPATH is set up correctly if testing structure.")
