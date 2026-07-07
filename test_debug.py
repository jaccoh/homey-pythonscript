print("Starting test_debug.py")
import sys
print(f"Python: {sys.version}")
print(f"sys.path: {sys.path}")

try:
    from pathlib import Path
    print("Path imported")
    from pythonscript.script_manager import ScriptManager
    print("ScriptManager imported successfully!")
except ImportError as e:
    print(f"Import error: {e}")
