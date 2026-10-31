# -*- coding: utf-8 -*-
import os
import sys
import runpy
import traceback
from kivy.resources import resource_add_path

# =============================================================================
# ABSOLUTE PATH FIX
# Forces Kivy and Python to register the correct asset directories on launch
# =============================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
resource_add_path(CURRENT_DIR)
resource_add_path(os.path.join(CURRENT_DIR, "launcher"))
resource_add_path(os.path.join(CURRENT_DIR, "data"))

def run_entrypoint(entrypoint):
    """Safely runs the selected python file as the main script."""
    if not entrypoint or not os.path.exists(entrypoint):
        print(f"Error: Entrypoint path does not exist: {entrypoint}")
        run_launcher()
        return

    entrypoint_path = os.path.dirname(entrypoint)
    if entrypoint_path not in sys.path:
        sys.path.append(os.path.realpath(entrypoint_path))
    
    try:
        runpy.run_path(entrypoint, run_name="__main__")
    except Exception:
        traceback.print_exc()
        # Fallback back to the launcher UI instead of crashing completely
        run_launcher()

def run_launcher():
    """Launches the default Kivy Launcher configuration UI."""
    try:
        from launcher.app import Launcher
        Launcher().run()
    except Exception:
        # If it crashes here, write to an internal emergency log file
        with open(os.path.join(CURRENT_DIR, "emergency_crash.txt"), "w") as f:
            traceback.print_file(file=f)
        traceback.print_exc()

def dispatch():
    """Determines whether to run an external script choice or load the launcher."""
    print("Launcher dispatch initialized!")

    # Check for environmental variables (Desktop/Testing environment)
    entrypoint = os.environ.get("KIVYLAUNCHER_ENTRYPOINT")
    if entrypoint is not None:
        return run_entrypoint(entrypoint)

    # Attempt to handle Android specific Intent data
    try:
        from jnius import autoclass
        
        # Safely acquire the native Python Android Activity Context
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        
        if activity is not None:
            intent = activity.getIntent()
            if intent is not None:
                entrypoint = intent.getStringExtra("entrypoint")
                orientation = intent.getStringExtra("orientation")

                # Dynamically assign device orientation adjustments safely
                if orientation == "portrait":
                    activity.setRequestedOrientation(0x1)  # SCREEN_ORIENTATION_PORTRAIT
                elif orientation == "landscape":
                    activity.setRequestedOrientation(0x0)  # SCREEN_ORIENTATION_LANDSCAPE
                elif orientation == "sensor":
                    activity.setRequestedOrientation(0x4)  # SCREEN_ORIENTATION_SENSOR

                if entrypoint is not None:
                    return run_entrypoint(entrypoint)
                    
    except (ImportError, KeyError):
        print("Non-Android target platform detected (Pyjnius bypassed).")
    except Exception:
        print("An error occurred during Android JNI execution:")
        traceback.print_exc()

    # Fallback to standard Launcher UI loop
    run_launcher()

if __name__ == "__main__":
    dispatch()
    
