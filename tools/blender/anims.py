"""Extra animations for KayKit's shared Rig_Medium skeleton, for poses the free
packs lack. Exported as their own clip library (assets/animations/), which
models.json "animations" lists after KayKit's, so every character gets them.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/anims.py -- --out assets/animations

Clips:
  Sit_Floor_Down  from standing to sitting on the ground, legs out in front
                  (EverQuest's /sit; knees drawn up vanish into these chibi bodies)
  Sit_Floor_Idle  sitting, breathing (loops)

Poses are built on the first frame of KayKit's Idle_A (so arms, hands and
head start where the idle has them) plus rotations in each bone's own axes.
The rig is Z-up and faces -Y; leg bones point down with X as their hinge, so
a negative X turn swings a thigh forward and a positive one folds a knee.
"""

import math
import os
import sys

import bpy
from mathutils import Euler, Quaternion, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOURCE = os.path.join(ROOT, "assets/KayKit_Adventurers_2.0_FREE/Animations/gltf/Rig_Medium/Rig_Medium_General.glb")
FPS = 30

# the seated pose: extra rotation per bone (degrees, bone-local XYZ) on top of
# the idle, and how far the hips drop (meters, down)
SIT = {
	"spine": (4, 0, 0),
	"upperleg.l": (-88, 0, -10),
	"upperleg.r": (-88, 0, 10),
	"lowerleg.l": (12, 0, 0),
	"lowerleg.r": (12, 0, 0),
	"foot.l": (-25, 0, 0),
	"foot.r": (-25, 0, 0),
}
HIP_DROP = 0.38


def _args():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	opts = {"--out": "assets/animations"}
	for i, a in enumerate(argv):
		if a in opts and i + 1 < len(argv):
			opts[a] = argv[i + 1]
	return opts


def _base_pose(arm):
	"""Each bone's rotation and location on the idle's first frame."""
	arm.animation_data.action = bpy.data.actions["Idle_A"]
	bpy.context.scene.frame_set(0)
	return {pb.name: (pb.rotation_quaternion.copy(), pb.location.copy()) for pb in arm.pose.bones}


def _pose(arm, base, amount, breathe=0.0):
	"""Sets the pose `amount` of the way (0..1) from the idle to seated."""
	for pb in arm.pose.bones:
		rot, loc = base[pb.name]
		pb.rotation_mode = "QUATERNION"
		extra = SIT.get(pb.name, (0, 0, 0))
		if pb.name in ("spine", "chest"):
			extra = (extra[0] + breathe, extra[1], extra[2])
		e = Euler([math.radians(a * amount) for a in extra], "XYZ").to_quaternion()
		pb.rotation_quaternion = rot @ e
		pb.location = loc.copy()
		if pb.name == "hips":
			pb.location = loc + Vector((0, -HIP_DROP * amount, 0))  # hips point up: local -Y is down


def _key(arm, frame):
	for pb in arm.pose.bones:
		pb.keyframe_insert("rotation_quaternion", frame=frame)
		pb.keyframe_insert("location", frame=frame)


def _new_action(arm, name):
	act = bpy.data.actions.new(name)
	arm.animation_data.action = act
	return act


def main():
	opts = _args()
	bpy.ops.wm.read_factory_settings(use_empty=True)
	bpy.ops.import_scene.gltf(filepath=SOURCE)
	arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
	base = _base_pose(arm)
	keep = []

	act = _new_action(arm, "Sit_Floor_Down")
	for f, t in [(0, 0.0), (6, 0.35), (12, 0.8), (16, 1.0)]:
		_pose(arm, base, t)
		_key(arm, f)
	keep.append(act)

	act = _new_action(arm, "Sit_Floor_Idle")
	for f, b in [(0, 0.0), (30, 2.5), (60, 0.0)]:
		_pose(arm, base, 1.0, b)
		_key(arm, f)
	keep.append(act)

	for tr in list(arm.animation_data.nla_tracks):  # the import's own tracks, one per KayKit clip
		arm.animation_data.nla_tracks.remove(tr)
	for a in list(bpy.data.actions):
		if a not in keep:
			bpy.data.actions.remove(a)
	for o in list(bpy.data.objects):
		if o != arm:
			bpy.data.objects.remove(o, do_unlink=True)
	for a in keep:  # the exporter takes actions from NLA tracks
		tr = arm.animation_data.nla_tracks.new()
		tr.name = a.name
		strip = tr.strips.new(a.name, 0, a)
		curves = sum(len(cb.fcurves) for layer in a.layers for st in layer.strips for cb in st.channelbags)
		print("clip %s: %d channels, slot %s" % (a.name, curves, strip.action_slot.name_display if strip.action_slot else "-"))
	arm.animation_data.action = None
	os.makedirs(opts["--out"], exist_ok=True)
	path = os.path.abspath(os.path.join(opts["--out"], "Rig_Medium_Extra.glb"))
	bpy.context.scene.render.fps = FPS
	bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_animations=True,
							  export_animation_mode="NLA_TRACKS", export_skins=True, export_def_bones=False,
							  export_optimize_animation_size=False,  # keep constant channels: arms held at the idle's angle still need a track
							  export_optimize_animation_keep_anim_armature=True, export_force_sampling=True)
	print("exported %s: %s" % (path, [a.name for a in keep]))


if __name__ == "__main__":
	main()
