import FreeCAD as App
import FreeCADGui as Gui
from PySide2 import QtCore, QtGui, QtWidgets
# Import the CreatedObject from cycloidal.py.
# This might require adjusting sys.path or using relative imports if this becomes a proper module.
# For now, assume cycloidal.py is in a place where it can be imported,
# or defer full CreatedObject interaction to a later stage.
# from .cycloidal import CreatedObject # This would be ideal if structured as a package

class CycloidCommand:
    def GetResources(self):
        return {
            'Pixmap': '',  # No icon for now
            'MenuText': QtCore.QT_TRANSLATE_NOOP("CycloidCommand", "Cycloidal Gear Generator"),
            'ToolTip': QtCore.QT_TRANSLATE_NOOP("CycloidCommand", "Creates a cycloidal gear with user-defined parameters")
        }

    def Activated(self):
        self.panel = CycloidTaskPanel()
        Gui.Control.showDialog(self.panel)

    def IsActive(self):
        return True

class CycloidTaskPanel(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Cycloidal Gear Parameters")
        self.layout = QtWidgets.QVBoxLayout(self) # Main layout

        # Form layout for parameters
        formLayout = QtWidgets.QFormLayout()

        # Parameter definitions (name, label, type, default, min, max, decimals, step)
        params_config = [
            ('rotorThickness', "Rotor Thickness (mm):", float, 0.635, 0.1, 1000, 3, 0.1),
            ('housingThickness', "Housing Thickness (mm):", float, 1.27, 0.1, 1000, 3, 0.1),
            ('R', "Radius (R, mm):", float, 50.0, 1.0, 1000, 2, 1.0), # Adjusted R default
            ('N', "Number of Pins (N):", int, 10, 3, 100, 0, 1),
            ('bore', "Bore Diameter (mm):", float, 10.0, 0.1, 1000, 2, 0.5), # Adjusted bore default
            ('numGears', "Number of Gears:", int, 1, 1, 10, 0, 1),
            ('numHoles', "Number of Drive Holes:", int, 0, 0, 100, 0, 1),
            ('holePinDiameter', "Drive Pin Diameter (mm):", float, 2.5, 0.1, 100, 2, 0.1), # Adjusted holePinDiameter default
            ('holeCircleDiameter', "Drive Hole Circle Dia. (mm):", float, 30.0, 1.0, 1000, 2, 1.0), # Adjusted holeCircleDiameter default
            ('eccentricityRatio', "Eccentricity Ratio:", float, 0.5, 0.01, 1.0, 2, 0.01),
        ]

        for name, label_text, param_type, default, p_min, p_max, p_decimals, p_step in params_config:
            label = QtWidgets.QLabel(label_text)
            if param_type == float:
                widget = QtWidgets.QDoubleSpinBox()
                widget.setDecimals(p_decimals)
            else: # int
                widget = QtWidgets.QSpinBox()
            
            widget.setMinimum(p_min)
            widget.setMaximum(p_max)
            widget.setSingleStep(p_step)
            widget.setValue(default)
            
            setattr(self, f"input_{name}", widget) # Store widget, e.g., self.input_rotorThickness
            formLayout.addRow(label, widget)

        self.layout.addLayout(formLayout) # Add form layout to main VBox layout

        # Buttons
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons) # Add buttons after the form

        self.setLayout(self.layout)
        self.resize(400, 350) # Adjusted initial size

    def collectParameters(self):
        params = {}
        params['rotorThickness'] = self.input_rotorThickness.value()
        params['housingThickness'] = self.input_housingThickness.value()
        params['R'] = self.input_R.value()
        params['N'] = self.input_N.value()
        params['bore'] = self.input_bore.value()
        params['numGears'] = self.input_numGears.value()
        params['numHoles'] = self.input_numHoles.value()
        params['holePinDiameter'] = self.input_holePinDiameter.value()
        params['holeCircleDiameter'] = self.input_holeCircleDiameter.value()
        params['eccentricityRatio'] = self.input_eccentricityRatio.value()
        return params

    def accept(self):
        App.Console.PrintMessage("OK clicked. Processing parameters...\n")
        params = self.collectParameters()
        
        CreatedObject = None
        try:
            from .cycloidal import CreatedObject
            App.Console.PrintMessage("Imported CreatedObject using relative import.\n")
        except ImportError as e_rel:
            App.Console.PrintMessage(f"Relative import failed: {e_rel}\nAttempting fallback import...\n")
            import sys
            import os
            current_dir = os.path.dirname(__file__)
            if not current_dir: # if __file__ is not absolute or not defined
                 # Try to get path if running in FreeCAD macro editor
                 try:
                     current_dir = os.path.dirname(Gui.ActiveDocument.FileName) # Might not be reliable
                 except Exception as e_ad:
                     App.Console.PrintWarning(f"Could not reliably get current_dir from ActiveDocument: {e_ad}\n")
                     # As a last resort, assume it's in one of the macro paths
                     # This is not robust
                     # current_dir = App.getUserMacroDir(True) # Example

            if current_dir and current_dir not in sys.path:
                sys.path.append(current_dir)
            
            try:
                from cycloidal import CreatedObject
                App.Console.PrintMessage(f"Imported CreatedObject from cycloidal.py in dir: {current_dir}\n")
            except ImportError as e_abs:
                App.Console.PrintError(f"Absolute import failed: {e_abs}\nCould not import CreatedObject. Ensure cycloidal.py is in the same directory or in sys.path.\n")
                super().reject() # Close dialog without further processing
                return
            except Exception as e_gen:
                App.Console.PrintError(f"An unexpected error occurred during fallback import: {e_gen}\n")
                super().reject()
                return

        if CreatedObject:
            creator = CreatedObject()
            creator.parameters = params
            creator.build()
            if App.ActiveDocument: # Ensure there's an active document to recompute
                App.ActiveDocument.recompute()
            App.Console.PrintMessage("Cycloidal gear generation complete.\n")
        else:
            App.Console.PrintError("Failed to load CreatedObject class.\n")

        super().accept()

    def reject(self):
        App.Console.PrintMessage("Cancel clicked.\n")
        super().reject() # or self.close()

# It's good practice to register the command with FreeCAD
# This is typically done outside the class definitions, at the module level.
# Example:
# if Gui.GuiUp: # Ensure this runs only in GUI mode
#    Gui.addCommand('CycloidCommand', CycloidCommand())
