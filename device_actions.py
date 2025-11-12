import code_generator
from firmware_manager import open_firmware_manager

# Retained for backward compatibility; simulator support has been removed.
simulator_process = None

def create_device_commands(parent, gui_refs):
    """
    Creates a dictionary of device-related commands.
    This helps keep the menu creation code clean by preparing the lambdas.
    """
    return {
        'generate_cpp_code': lambda: code_generator.show_code_generator(parent, gui_refs),
        'open_firmware_manager': lambda: open_firmware_manager(parent, gui_refs)
    }
