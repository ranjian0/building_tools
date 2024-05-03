import bpy
import sys
import json
import subprocess
import importlib.util
import addon_utils
from pathlib import Path
from types import SimpleNamespace

prompt = """
You are a skilled architect tasked with designing a building for a client. The client wants a building that is both beautiful and functional. 
The user will provide you with a list of requirements and constraints, and you will use your expertise to design a building that meets the client's needs.

The client's requirements are as follows:
- The building must be at least 2 stories tall.

Your respose will be in the form of json commands that will be fed to a script that will generate the building in a 3D modeling software.
The commands available are:
- CREATE_FLOORPLAN with the options ["RANDOM", "RECTANGULAR", "CIRCULAR", "L_SHAPED"]
- CREATE_FLOORS with the option "num_floors"
- ADD_ROOF with the option ["FLAT", "GABLE", "HIP"]

As an example, if the user provides the following requirements:
- The building must be at least 3 stories tall.

Your response should be:
{
    "CREATE_FLOORPLAN": "RANDOM",
    "CREATE_FLOORS": {
        "num_floors": 3
    },
    "ADD_ROOF": "FLAT"
}
"""


def is_development():
    for mod in addon_utils.modules():
        if mod.__name__ == "building_tools":
            return False
    return True


def ensure_openai_lib():
    openai_installed = importlib.util.find_spec("openai")
    if openai_installed:
        return

    blender_bin = sys.executable
    print([blender_bin, "-m", "pip", "install", "openai"])
    subprocess.run([blender_bin, "-m" "pip", "install", "openai"])


def get_blender_preferences():
    if is_development():
        prefs = SimpleNamespace(api_key="", gpt_model="")
        env_file = Path(__file__).parent.parent.parent / ".env.json"
        if env_file.exists():
            with env_file.open() as f:
                data = json.load(f)
                prefs.api_key = data["OPENAI_API_KEY"]
                prefs.gpt_model = data["GPT_MODEL"]
        return prefs

    prefs = bpy.context.preferences.addons[__package__].preferences
    return prefs


def generate_ai_building():
    from openai import OpenAI

    prefs = get_blender_preferences()
    client = OpenAI(api_key=prefs.api_key)

    response = client.chat.completions.create(
        model=prefs.gpt_model, messages=[{"role": "system", "content": prompt}]
    )

    return response.choices[0].message.content


class BTOOLS_OT_ai_generate(bpy.types.Operator):
    bl_idname = "btools.ai_generate"
    bl_label = "Generate Building"
    bl_description = "Use OpenAI's GPT to generate a building design"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ensure_openai_lib()

        response = generate_ai_building()
        print("AI Response:\n", response)
        return {"FINISHED"}
