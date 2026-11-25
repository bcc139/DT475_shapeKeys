"""
DT475 W14 · Shape keys 3/3 · A bone drives a shape key  (class demo)
==================================================================
Run in a new Blender file: Scripting > Open > Alt+P, then press Space.
Headless: blender -b -P sk3_driver.py

An arm (a tube) with two bones.  When the elbow bends, the biceps should
bulge.  Skinning alone cannot do that, so we add a shape key "Bulge" and let
a DRIVER set its value from the elbow angle:

    Bulge.value = max(0, elbow_angle) / 90 degrees

This is how corrective shapes work in game characters (elbows, knees,
shoulders) and how face rigs link a control bone to blend shapes.
"""
import math
import bpy
import bmesh
from mathutils import Vector

ARM = "SK_ArmRig"
MESH = "SK_ArmMesh"
L = 1.0           # length of each bone
RADIUS = 0.22


def remove_object(name):
    obj = bpy.data.objects.get(name)
    if obj is not None:
        data = obj.data
        bpy.data.objects.remove(obj)
        if data is not None and data.users == 0:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Armature):
                bpy.data.armatures.remove(data)


def make_armature():
    """Two bones along +X: Upper (0..L) and Lower (L..2L)."""
    data = bpy.data.armatures.new(ARM)
    rig = bpy.data.objects.new(ARM, data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    up = data.edit_bones.new("Upper")
    up.head, up.tail = (0, 0, 0), (L, 0, 0)
    lo = data.edit_bones.new("Lower")
    lo.head, lo.tail = (L, 0, 0), (2 * L, 0, 0)
    lo.parent = up
    lo.use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    return rig


def make_tube(rig):
    """A tube along X, skinned to the two bones by hand-made weights."""
    mesh = bpy.data.meshes.new(MESH)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=RADIUS,
                          radius2=RADIUS, depth=2 * L)
    # the cone is made along Z: lay it along X from 0 to 2L, add rings
    for v in bm.verts:
        v.co = Vector((v.co.z + L, v.co.y, -v.co.x))
    edges = [e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) > 1e-6]
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=19, use_grid_fill=True)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(MESH, mesh)
    bpy.context.scene.collection.objects.link(obj)

    # weights: Upper below the elbow, Lower above, a smooth blend around it
    g_up = obj.vertex_groups.new(name="Upper")
    g_lo = obj.vertex_groups.new(name="Lower")
    for v in mesh.vertices:
        t = min(max((v.co.x - (L - 0.15)) / 0.3, 0.0), 1.0)
        g_up.add([v.index], 1.0 - t, "REPLACE")
        g_lo.add([v.index], t, "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    obj.parent = rig
    return obj


# ---------------------------------------------------------------- TODO 1 ---
def make_bulge(obj):
    """Shape key 'Bulge': push the top (+Z) of the upper arm outward,
    strongest in the middle of the upper arm."""
    kb = obj.shape_key_add(name="Bulge", from_mix=False)
    for p in kb.data:
        x, y, z = p.co
        along = math.exp(-((x - 0.55 * L) / (0.22 * L)) ** 2)  # bell around mid upper arm
        side = max(z, 0.0) / RADIUS                           # 0 at the sides, 1 on top
        p.co.z += 0.18 * along * side
        p.co.y *= 1.0 + 0.15 * along
    return kb


# ---------------------------------------------------------------- TODO 2 ---
def add_driver(kb, rig):
    """Bulge.value follows the elbow (bone 'Lower') rotation about its local X."""
    fcurve = kb.driver_add("value")
    drv = fcurve.driver
    drv.type = "SCRIPTED"
    var = drv.variables.new()
    var.name = "bend"
    var.type = "TRANSFORMS"
    tgt = var.targets[0]
    tgt.id = rig
    tgt.bone_target = "Lower"
    tgt.transform_type = "ROT_X"
    tgt.transform_space = "LOCAL_SPACE"
    tgt.rotation_mode = "AUTO"
    drv.expression = "max(0, bend) / 1.5708"       # 90 deg -> 1.0
    return fcurve


def animate_elbow(rig):
    pb = rig.pose.bones["Lower"]
    pb.rotation_mode = "XYZ"
    for frame, deg in [(1, 0), (25, 110), (40, 110), (65, 0), (80, 0)]:
        pb.rotation_euler = (math.radians(deg), 0, 0)
        pb.keyframe_insert("rotation_euler", frame=frame)


def main():
    remove_object("Cube")
    remove_object(MESH)
    remove_object(ARM)
    rig = make_armature()
    arm = make_tube(rig)
    arm.shape_key_add(name="Basis", from_mix=False)
    bulge = make_bulge(arm)
    fc = add_driver(bulge, rig)
    animate_elbow(rig)

    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 80
    print("\nframe  elbow(deg)  Bulge")
    for f in (1, 13, 25, 52, 65):
        scene.frame_set(f)
        deg = math.degrees(rig.pose.bones["Lower"].rotation_euler.x)
        print(f"{f:5d}  {deg:9.1f}  {bulge.value:5.2f}")
    scene.frame_set(1)
    print("simple expression (no Python needed, works without Auto Run):",
          fc.driver.is_simple_expression)


main()
