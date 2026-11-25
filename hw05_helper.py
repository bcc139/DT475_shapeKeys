"""
DT475 HW05 helper: Blender plumbing and the auto-check.
You do NOT need to read or edit this file.  Keep it next to hw05_main.py.
"""
import math
import os
import traceback

import bpy
from mathutils import Vector

BASE_FILE = "slime_base.obj"
WRONG_FILE = "slime_wrong.obj"
TARGETS = [("Squash", "slime_squash.obj"),
           ("Stretch", "slime_stretch.obj"),
           ("Smile", "slime_smile.obj")]

# Task 2 key table: frame -> (Squash, Stretch, height of the slime)
BOUNCE = [
    (1,  0.0, 0.0, 0.0),    # rest
    (6,  1.0, 0.0, 0.0),    # anticipation: squash down
    (10, 0.0, 1.0, 0.4),    # take-off: stretch up
    (18, 0.0, 0.0, 1.5),    # top of the jump: round
    (26, 0.0, 1.0, 0.4),    # falling: stretch
    (30, 1.0, 0.0, 0.0),    # landing: squash
    (36, 0.0, 0.0, 0.0),    # settle
]

RIG = "SlimeRig"
CTRL = "Smile_Ctrl"
SMILE_TESTS = [(0.0, 0.0), (0.15, 0.5), (0.3, 1.0), (0.6, 1.0), (-0.2, 0.0)]

_models_dir = None


# ---------------------------------------------------------------- scene ---
def set_folder(folder):
    global _models_dir
    _models_dir = os.path.join(folder, "models")


def model(name):
    path = os.path.join(_models_dir, name)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{path} not found: keep the models/ folder next to hw05_main.py")
    return path


def delete_object(obj):
    data = obj.data
    bpy.data.objects.remove(obj)
    if data is not None and data.users == 0:
        if isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
        elif isinstance(data, bpy.types.Armature):
            bpy.data.armatures.remove(data)


def reset_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in list(bpy.data.objects):
        n = obj.name
        if n == "Cube" or n == RIG or n.startswith("Slime") or n.startswith("slime_"):
            delete_object(obj)
    bpy.data.orphans_purge(do_recursive=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 40
    scene.frame_set(1)


def import_obj(path):
    """Import one OBJ file and return the new mesh object.
    Note: Blender's OBJ importer keeps the file's Y-up coordinates in the mesh
    and stores the Y-up -> Z-up conversion as a 90 deg rotation of the object."""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if len(new) != 1:
        raise RuntimeError(f"expected one mesh in {os.path.basename(path)}, got {len(new)}")
    return new[0]


def make_control_rig():
    """An armature with one bone, Smile_Ctrl, beside the slime.  It points up,
    so moving it up in Pose Mode (G Z) raises its local Y location."""
    data = bpy.data.armatures.new(RIG)
    rig = bpy.data.objects.new(RIG, data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = data.edit_bones.new(CTRL)
    eb.head, eb.tail = (1.5, 0, 0.9), (1.5, 0, 1.2)
    bpy.ops.object.mode_set(mode="OBJECT")
    pb = rig.pose.bones[CTRL]
    pb.lock_location = (True, False, True)
    pb.lock_rotation = (True, True, True)
    pb.lock_rotation_w = True
    pb.lock_scale = (True, True, True)
    rig.show_in_front = True
    return rig


def step(label, fn, *args):
    """Run one of your functions; report TODO / errors instead of stopping."""
    try:
        return fn(*args)
    except NotImplementedError:
        print(f"  [TODO] {label}: not implemented yet")
    except Exception as exc:
        print(f"  [ERROR] {label}: {type(exc).__name__}: {exc}")
        traceback.print_exc()
    return None


# ---------------------------------------------------------------- check ---
def read_obj_vertices(path):
    out = []
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                out.append(tuple(float(t) for t in line.split()[1:4]))
    return out


_ID_LISTS = ("objects", "meshes", "armatures", "actions", "materials", "images",
             "textures", "collections", "cameras", "lights", "node_groups")
_glb_cache = {}


def glb_morph_targets(path):
    """The checker's own count: import the GLB with Blender's glTF importer,
    count the shape keys it rebuilds, then remove everything it added."""
    stamp = (path, os.path.getmtime(path))
    if stamp in _glb_cache:
        return _glb_cache[stamp]
    view_layer = bpy.context.view_layer
    active, selected = view_layer.objects.active, list(bpy.context.selected_objects)
    frame = bpy.context.scene.frame_current
    before = {name: set(getattr(bpy.data, name)) for name in _ID_LISTS}
    bpy.ops.import_scene.gltf(filepath=path)
    added = {name: [i for i in getattr(bpy.data, name) if i not in before[name]]
             for name in _ID_LISTS}
    count = max((len(m.shape_keys.key_blocks) - 1 for m in added["meshes"] if m.shape_keys),
                default=0)
    bpy.data.batch_remove([i for ids in added.values() for i in ids])
    for obj in bpy.context.scene.objects:
        obj.select_set(obj in selected)
    view_layer.objects.active = active
    bpy.context.scene.frame_set(frame)
    _glb_cache[stamp] = count
    return count


def key_blocks(base):
    keys = base.data.shape_keys
    return keys.key_blocks if keys else []


def find_smile_driver(base):
    keys = base.data.shape_keys
    if keys is None or keys.animation_data is None:
        return None
    for fc in keys.animation_data.drivers:
        if fc.data_path == 'key_blocks["Smile"].value':
            return fc
    return None


class Report:
    def __init__(self):
        self.rows, self.total, self.got = [], 0.0, 0.0

    def add(self, tag, label, got, out_of, note=""):
        self.total += out_of
        self.got += got
        self.rows.append((tag, label, got, out_of, note))

    def run(self, label, out_of, fn):
        try:
            got, note = fn()
            got = max(0.0, min(out_of, got * out_of))
            tag = "PASS" if got >= out_of - 1e-9 else ("PART" if got > 0 else "FAIL")
            self.add(tag, label, got, out_of, note)
        except NotImplementedError as exc:
            self.add("TODO", label, 0.0, out_of, f"not implemented yet ({exc})")
        except Exception as exc:
            self.add("FAIL", label, 0.0, out_of, f"crashed: {type(exc).__name__}: {exc}")

    def show(self):
        print("\n================= HW05 CHECK REPORT =================")
        for tag, label, got, out_of, note in self.rows:
            print(f" [{tag}] {label:<48s} {got:4.2f} / {out_of:4.2f}   {note}")
        print(f"\n Auto-checked points: {self.got:.2f} / {self.total:.2f}"
              "   (written answers + code quality are marked by hand)")
        print("====================================================\n")


def run_checks(funcs, base, rig, glb_path):
    rep = Report()
    scene = bpy.context.scene

    # ---- Task 1
    def t1a():
        if not key_blocks(base):
            raise NotImplementedError("no shape keys yet")
        names = [kb.name for kb in key_blocks(base)]
        want = ["Basis"] + [n for n, _ in TARGETS]
        return (1.0 if names == want else 0.0), f"keys: {names}"
    rep.run("Task 1a  Basis + Squash, Stretch, Smile", 0.5, t1a)

    def t1b():
        if not key_blocks(base):
            raise NotImplementedError("no shape keys yet")
        score, notes = 0.0, []
        for name, file in TARGETS:
            kb = base.data.shape_keys.key_blocks.get(name)
            if kb is None:
                notes.append(f"{name} missing")
                continue
            want = read_obj_vertices(model(file))
            if len(want) != len(kb.data):
                notes.append(f"{name}: {len(kb.data)} verts, file has {len(want)}")
                continue
            worst = max((kb.data[i].co - Vector(want[i])).length
                        for i in range(len(want)))
            if worst < 1e-4:
                score += 1 / 3
            else:
                notes.append(f"{name} off by up to {worst:.4f}")
        return score, "; ".join(notes) or "every vertex matches its file"
    rep.run("Task 1b  every vertex copied from its file", 1.5, t1b)

    def t1c():
        n_obj, n_keys = len(bpy.data.objects), len(key_blocks(base))
        raised = False
        try:
            funcs["add_shape_from_obj"](base, model(WRONG_FILE), "Wrong")
        except ValueError:
            raised = True
        extra_obj = len(bpy.data.objects) - n_obj
        extra_keys = len(key_blocks(base)) - n_keys
        kb = base.data.shape_keys.key_blocks.get("Wrong") if base.data.shape_keys else None
        if kb is not None:
            base.shape_key_remove(kb)
        for o in list(bpy.data.objects):
            if o.name.startswith("slime_wrong"):
                delete_object(o)
        score = (0.5 if raised else 0.0) + (0.5 if extra_obj == 0 and extra_keys == 0 else 0.0)
        return score, (f"ValueError {'raised' if raised else 'NOT raised'}; "
                       f"left behind {extra_obj} object(s), {extra_keys} key(s)")
    rep.run("Task 1c  wrong vertex count -> ValueError", 1.0, t1c)

    # ---- Task 2
    def t2(part):
        def run():
            keys = base.data.shape_keys
            if keys is None or "Squash" not in keys.key_blocks or "Stretch" not in keys.key_blocks:
                raise NotImplementedError("needs Task 1 first")
            owner = keys if part == "shape" else base
            if owner.animation_data is None or owner.animation_data.action is None:
                raise NotImplementedError("no keyframes yet")
            ok, bad = 0, []
            for frame, sq, st, z in BOUNCE:
                scene.frame_set(frame)
                kbs = base.data.shape_keys.key_blocks
                if part == "shape":
                    good = abs(kbs["Squash"].value - sq) < 1e-3 and abs(kbs["Stretch"].value - st) < 1e-3
                else:
                    good = abs(base.location.z - z) < 1e-3
                ok += good
                if not good:
                    bad.append(str(frame))
            scene.frame_set(1)
            return ok / len(BOUNCE), ("all frames match" if not bad else "wrong at frames " + ", ".join(bad))
        return run
    rep.run("Task 2a  Squash / Stretch follow the key table", 1.5, t2("shape"))
    rep.run("Task 2b  height follows the key table", 0.5, t2("height"))

    # ---- Task 3
    def t3a():
        if find_smile_driver(base) is None:
            raise NotImplementedError("no driver on Smile")
        pb = rig.pose.bones[CTRL]
        ok, notes = 0, []
        for loc, want in SMILE_TESTS:
            pb.location = (0, loc, 0)
            bpy.context.view_layer.update()
            got = base.data.shape_keys.key_blocks["Smile"].value
            if abs(got - want) < 1e-3:
                ok += 1
            else:
                notes.append(f"bone {loc:+.2f} -> {got:.2f} (want {want:.2f})")
        pb.location = (0, 0, 0)
        bpy.context.view_layer.update()
        return ok / len(SMILE_TESTS), "; ".join(notes) or "all bone positions give the right Smile"
    rep.run("Task 3a  bone Smile_Ctrl drives Smile (0..1)", 1.5, t3a)

    def t3b():
        fc = find_smile_driver(base)
        if fc is None:
            raise NotImplementedError("no driver on Smile")
        drv = fc.driver
        uses_bone = any(v.type == "TRANSFORMS" and v.targets[0].id == rig and
                        v.targets[0].bone_target == CTRL for v in drv.variables)
        score = (0.5 if uses_bone else 0.0) + (0.5 if drv.is_simple_expression else 0.0)
        return score, (f"Transform Channel on {CTRL}: {uses_bone}; "
                       f"simple expression (runs without Auto Run): {drv.is_simple_expression}")
    rep.run("Task 3b  Transform Channel var + simple expr.", 0.5, t3b)

    # ---- Task 4
    def t4a():
        if not os.path.isfile(glb_path):
            raise NotImplementedError("slime.glb was not written")
        n = glb_morph_targets(glb_path)
        return (1.0 if n == len(TARGETS) else 0.0), f"slime.glb has {n} morph target(s)"
    rep.run("Task 4a  GLB export keeps the 3 morph targets", 1.0, t4a)

    def t4b():
        if not os.path.isfile(glb_path):
            raise NotImplementedError("slime.glb was not written")
        got = funcs["count_morph_targets"](glb_path)
        want = glb_morph_targets(glb_path)
        return (1.0 if got == want else 0.0), f"your count {got}, checker {want}"
    rep.run("Task 4b  count_morph_targets reads the GLB", 0.5, t4b)

    rep.show()
    return rep
