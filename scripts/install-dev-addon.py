import bpy
from pathlib import Path

THIS_DIR = Path(__file__).parent.absolute()

addon_name = "building_tools_latest.zip"
addon_path = THIS_DIR.parent.joinpath(addon_name)

def install_dev_addon():
    if addon_path.exists():
        # -- check if the addon is already installed, 
        #    if so, disable and remove it first
        addon_module = "building_tools"
        if addon_module in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_disable(module=addon_module)
            # bpy.ops.preferences.addon_remove(module=addon_module)
        
        
        bpy.ops.preferences.addon_install(
            overwrite=True,
            filepath=str(addon_path),
        )
    else:
        print(f"Addon not found: {addon_path}")
        return


if __name__ == "__main__":
    install_dev_addon()