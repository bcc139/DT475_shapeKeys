"""
DT475 HW05 · Shape keys from OBJ files
=====================================
The only file you edit.  Five functions (Tasks 1-4) are marked TODO.  Read README.md first.

Run: Blender 5.2 > Scripting > Text > Open this file > Alt+P
     Window > Toggle System Console shows the report.
Headless (the same check your instructor uses):
     C:\\blender-5.2.2\\blender.exe -b -P hw05_main.py
Keep hw05_helper.py and the models/ folder next to this file.
Re-running is always safe: the script rebuilds the scene every time.
"""
import importlib
import json
import os
import struct
import sys

import bpy

MODE = "CHECK"      # "CHECK" = build the scene and print the report
                    # "BUILD" = only build the scene (then press Space)


def _here():
    try:
        if os.path.isfile(__file__):
            return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass
    text = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if text is not None and text.filepath:
        return os.path.dirname(os.path.abspath(bpy.path.abspath(text.filepath)))
    return os.getcwd()


HERE = _here()
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import hw05_helper as helper          # noqa: E402
importlib.reload(helper)
helper.set_folder(HERE)


# =========================================================== Task 1 ======
def add_shape_from_obj(base, path, name):
    """Import the OBJ at `path` and turn it into a shape key called `name`
    on the mesh object `base`.  Return the new key block.

    1. target = helper.import_obj(path)
    2. If target and base do not have the same number of vertices:
       delete the target (helper.delete_object) and raise ValueError
       with a clear message.
    3. If base has no shape keys yet, add the Basis first.
    4. Add a key (base.shape_key_add(name=..., from_mix=False)) and copy every
       vertex position: key.data[i].co = target.data.vertices[i].co
    5. Delete the target object, return the key.
    Tip: try/finally is a neat way to make sure step 5 always happens.
    """
    raise NotImplementedError("add_shape_from_obj")


# =========================================================== Task 2 ======
def animate_bounce(base):
    """Key the jump in helper.BOUNCE: rows of (frame, squash, stretch, height).
    For every row: set the Squash and Stretch values and key them, set
    base.location.z to the height and key it (data path "location", index 2).
    The key blocks are in base.data.shape_keys.key_blocks["Squash"] etc.
    """
    raise NotImplementedError("animate_bounce")


# =========================================================== Task 3 ======
def add_smile_driver(base, rig):
    """Drive Smile's value from the bone helper.CTRL ("Smile_Ctrl") in `rig`.
    Moving the bone up by 0.3 along its local Y gives a full smile:
        bone Y  0.0 -> 0     0.15 -> 0.5     0.3 or more -> 1     below 0 -> 0
    Use a Transform Channel variable (type "TRANSFORMS", transform_type
    "LOC_Y", transform_space "LOCAL_SPACE") and a SIMPLE expression, so it
    works without "Auto Run Python Scripts".  The class demo sk3_driver.py
    shows every line you need.  (The Smile slider is 0..1, so Blender clamps
    the value for you; clamp(x) in the expression makes it explicit.)
    """
    raise NotImplementedError("add_smile_driver")


# =========================================================== Task 4 ======
def export_glb(path):
    """Export the scene to `path` as GLB with shape keys (morph targets) and
    animation: bpy.ops.export_scene.gltf(filepath=..., export_format=...,
    export_morph=..., export_animations=...)"""
    raise NotImplementedError("export_glb")


def count_morph_targets(glb_path):
    """Read the GLB file yourself (no Blender) and return how many morph
    targets its mesh has (the largest count over all mesh primitives).

    A GLB file is:  12-byte header  | chunk 0 = JSON | chunk 1 = binary
      header:  magic b"glTF" (4 bytes), version (uint32), total length (uint32)
      chunk 0: length (uint32), type b"JSON" (4 bytes), then `length` bytes of JSON
    struct.unpack_from("<4sII", data, 0) reads the header,
    struct.unpack_from("<I4s", data, 12) reads chunk 0's length and type.
    In the JSON: doc["meshes"][m]["primitives"][p]["targets"] is a list.
    Unsure what the JSON looks like?  Export once with
    export_format="GLTF_SEPARATE" and open the .gltf file in VS Code.
    """
    raise NotImplementedError("count_morph_targets")


# ============================================================ run ========
def main():
    helper.reset_scene()
    base = helper.import_obj(helper.model(helper.BASE_FILE))
    base.name = "Slime"
    for name, file in helper.TARGETS:
        helper.step(f"Task 1 ({name})", add_shape_from_obj, base, helper.model(file), name)
    if base.data.shape_keys and len(base.data.shape_keys.key_blocks) == 4:
        helper.step("Task 2", animate_bounce, base)
    rig = helper.make_control_rig()
    if base.data.shape_keys and "Smile" in base.data.shape_keys.key_blocks:
        helper.step("Task 3", add_smile_driver, base, rig)
    glb = os.path.join(HERE, "slime.glb")
    helper.step("Task 4 (export)", export_glb, glb)
    bpy.context.scene.frame_set(1)
    if MODE == "CHECK":
        helper.run_checks({"add_shape_from_obj": add_shape_from_obj,
                           "count_morph_targets": count_morph_targets},
                          base, rig, glb)


main()
