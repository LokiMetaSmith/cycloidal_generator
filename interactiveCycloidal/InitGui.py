# InitGui.py for interactiveCycloidal addon

import FreeCADGui as Gui
# Import the command class from freecadUtils.py located in the same directory
from .freecadUtils import CycloidCommand

def run_command_registration():
    """Registers the command with FreeCAD. 
       This function can be expanded if more GUI initializations are needed."""
    Gui.addCommand('Cycloidal_Gear_Generator', CycloidCommand())
    # If you wanted to add it to a menu/toolbar directly, you could do it here,
    # for example:
    # Gui.SendMsgToActiveView("AddCommandToPath") # Example, actual API might differ or be more complex

# FreeCAD will look for specific functions like onWorkbenchActivated,
# but for simple command registration, executing it directly or via a helper function is common.
# Some addons register commands inside a class that gets loaded by FreeCAD.
# For now, direct registration or via a simple function call is fine.
# Let's ensure it runs when this module is loaded by FreeCAD's GUI initialization.

# Run the registration.
# FreeCAD typically executes InitGui.py when the GUI starts up and the Mod directory is scanned.
run_command_registration()

# Alternatively, some sources suggest FreeCAD calls specific functions.
# For simple command addition, the above is usually sufficient.
# If issues arise, might need to wrap in initialize() or similar if FreeCAD expects that.
# For now, this direct approach after import should work.
