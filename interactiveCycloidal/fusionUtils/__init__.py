import adsk.core
import adsk.fusion
import traceback
import math

class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, app, ui, object_class, input_parameters, build_method_name='build'): # Added build_method_name
        super().__init__()
        self.object_class = object_class
        self.app = app
        self.parameters = input_parameters # This is Parameters object (list/dict of Parameter)
        self.ui = ui
        self.build_method_name = build_method_name

    def notify(self, args):
        try:
            units_mgr = self.app.activeProduct.unitsManager
            command = args.firingEvent.sender
            inputs = command.commandInputs

            # Populate self.object_class.parameters (which is a dict in CreatedObject/TempCreatedObjectForFusion)
            # The object_class instance should have a 'parameters' dict attribute.
            if not hasattr(self.object_class, 'parameters') or not isinstance(self.object_class.parameters, dict):
                # Initialize if not present, though cycloidal.py's TempCreatedObjectForFusion does this.
                self.object_class.parameters = {}

            for current_input in inputs:
                # self.parameters is the Parameters definition object
                # self.object_class.parameters is the dict to store evaluated values
                defined_parameter = self.parameters.parameter_dict[current_input.id]
                # Fusion command inputs return values in internal units (e.g., cm for length).
                # If input.expression is used, it might contain units.
                # If input.value is used, it's already in internal units.
                # units_mgr.evaluateExpression is robust for handling expressions with units.
                self.object_class.parameters[current_input.id] = units_mgr.evaluateExpression(current_input.expression, defined_parameter.units)

            # Call the designated build method on the object_class instance.
            # This method is now responsible for API wrapper setup and calling the core build.
            build_method_to_call = getattr(self.object_class, self.build_method_name)
            build_method_to_call() # No app/ui args needed here as wrapper handles them
            
            args.isValidResult = True

        except:
            if self.ui:
                self.ui.messageBox('Failed in CommandExecuteHandler.notify:\n{}'.format(traceback.format_exc()))

class CommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui

    def notify(self, args):
        try:
            # When the command is destroyed, terminate the script.
            # This will remove all handlers automatically.
            adsk.terminate()
        except:
            if self.ui:
                self.ui.messageBox('Failed in CommandDestroyHandler.notify:\n{}'.format(traceback.format_exc()))

class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, app, ui, object_class, input_parameters, handlers, build_method_name='build'): # Added build_method_name
        super().__init__()  
        self.object_class = object_class
        self.app = app    
        self.parameters = input_parameters # This is Parameters definition object
        self.ui = ui
        self.handlers = handlers # Storing handlers to keep them alive
        self.build_method_name = build_method_name


    def notify(self, args):
        try:
            cmd = args.command
            cmd.isRepeatable = False # Typically, for complex generations, set to False.
            
            # Pass build_method_name to CommandExecuteHandler
            onExecute = CommandExecuteHandler(self.app, self.ui, self.object_class, self.parameters, self.build_method_name)
            cmd.execute.add(onExecute)
            
            # Also pass build_method_name to executePreview if it's intended to behave similarly (e.g., for live updates)
            # For this project, executePreview might not be used for full build, but for consistency:
            onExecutePreview = CommandExecuteHandler(self.app, self.ui, self.object_class, self.parameters, self.build_method_name)
            cmd.executePreview.add(onExecutePreview) # If preview should also run the build logic
            
            onDestroy = CommandDestroyHandler(self.ui)
            cmd.destroy.add(onDestroy)
            
            # Keep handlers alive
            self.handlers.append(onExecute)
            self.handlers.append(onExecutePreview)
            self.handlers.append(onDestroy)

            # Create the inputs for the command.
            inputs = cmd.commandInputs
            units_mgr = self.app.activeProduct.unitsManager
            internal_unit = units_mgr.internalUnit # Default internal unit for length is 'cm'

            for parameter_def in self.parameters.parameter_list:
                initial_value = parameter_def.default_value
                
                # Handle unit conversion for default values if units are specified (e.g., "mm")
                # ValueInput.createByReal expects the value in internal units (cm for length).
                if parameter_def.units and parameter_def.units != "" and parameter_def.units != internal_unit :
                    try:
                        # Convert the default_value from its specified unit to internal units.
                        initial_value_in_internal_units = units_mgr.convert(parameter_def.default_value, parameter_def.units, internal_unit)
                        init_value_obj = adsk.core.ValueInput.createByReal(initial_value_in_internal_units)
                    except:
                        if self.ui:
                            self.ui.messageBox(f"Failed to convert default value for {parameter_def.id} from {parameter_def.units} to {internal_unit}.\nUsing raw value.")
                        init_value_obj = adsk.core.ValueInput.createByReal(parameter_def.default_value) # Fallback
                else: # Unitless or already in internal units
                    init_value_obj = adsk.core.ValueInput.createByReal(parameter_def.default_value)

                inputs.addValueInput(parameter_def.id, parameter_def.description, parameter_def.units if parameter_def.units else "", init_value_obj)

        except:
            if self.ui:
                self.ui.messageBox('Failed in CommandCreatedHandler.notify:\n{}'.format(traceback.format_exc()))

class Parameter:
    def __init__(self, name, units, description, default_value):
        self.id = name
        self.units = units # e.g., "mm", "cm", "deg", "" for unitless
        self.description = description
        self.default_value = default_value # Expected to be in the unit system of 'units'

class Parameters:
    def __init__(self):
        self.parameter_list = []
        self.parameter_dict = {}

    def addParameter(self, name, units, description, default_value):
        new_param = Parameter(name, units, description, default_value)
        self.parameter_list.append(new_param)
        self.parameter_dict[name] = new_param

def createNewComponent(app): # This function might not be used by the wrapper path anymore
    # Get the active design.
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)
    root_comp = design.rootComponent
    all_occs = root_comp.occurrences
    new_occ = all_occs.addNewComponent(adsk.core.Matrix3D.create())
    return new_occ.component

# Modified run function to accept build_method_name
def run(parameters_definition, default_name, object_to_build_instance, build_method_name='build'):
    handlers = [] # To keep event handlers alive.
    app = adsk.core.Application.get()
    if not app:
        return # Should not happen if running as Fusion Add-in
    
    ui = app.userInterface

    try:
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        if not design:
            if ui:
                ui.messageBox('It is not supported in current workspace, please change to MODEL workspace and try again.')
            return

        # Get the CommandDefinitions collection.
        command_definitions = ui.commandDefinitions
        
        # Get the command definition or create it if it doesn't exist.
        cmd_def = command_definitions.itemById(default_name)
        if not cmd_def:
            cmd_def = command_definitions.addButtonDefinition(default_name, 
                                                            'Create ' + default_name, 
                                                            'Creates a ' + default_name + '.', # Tooltip
                                                            '') # Resources folder can be empty

        # Connect to the command created event.
        # Pass build_method_name to CommandCreatedHandler
        on_command_created = CommandCreatedHandler(app, ui, object_to_build_instance, parameters_definition, handlers, build_method_name)
        cmd_def.commandCreated.add(on_command_created)
        handlers.append(on_command_created) # Keep handler alive
        
        # Execute the command.
        inputs = adsk.core.NamedValues.create() # Used if you want to execute with predefined inputs programmatically
        cmd_def.execute(inputs)

        # Prevent this module from being terminated when the script returns,
        # because behavior of Autodesk Fusion 360 is 
        # to terminate the script after execution.
        adsk.autoTerminate(False)
    except:
        if ui:
            ui.messageBox('Failed in fusionUtils.run setup:\n{}'.format(traceback.format_exc()))
