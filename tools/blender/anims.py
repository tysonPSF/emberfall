"""Extra animations for KayKit's shared Rig_Medium skeleton, for poses the free
packs lack. Exported as their own clip library (assets/animations/), which
models.json "animations" lists after KayKit's, so every character gets them.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/anims.py -- --out assets/animations

Clips:
  Sit_Floor_Down  from standing to sitting on the ground, legs out in front
                  (EverQuest's /sit; knees drawn up vanish into these chibi bodies)
  Sit_Floor_Idle  sitting, breathing (loops)
  Kick            a front kick with the right leg: chamber, snap, recover
  Shield_Bash     a lunge driving the left (shield) arm forward
  Bow_Shoot       bow arm up (the bow is in the left hand), draw to the cheek,
                  hold, release; the body turns side-on to the target
  Swim_Forward    breaststroke with a frog kick, leaning into it (loops, 1.2 s)
  Swim_Idle       treading water: arms sculling, legs cycling, a bob (loops, 2 s)

Poses are built on the first frame of KayKit's Idle_A (so arms, hands and
head start where the idle has them) plus rotations in each bone's own axes.
The rig is Z-up and faces -Y; leg bones point down with X as their hinge, so
a negative X turn swings a thigh forward and a positive one folds a knee.
Upper arms: +X raises the arm forward, +Z out to the side (-Z across the
body); a forearm's -Z bends the elbow. The hips bone points up: its local -Y
is down and +Z is forward.
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


def _keys(arm, base, name, keys, smooth=False):
	"""An action from [(frame, {bone: (x, y, z) degrees}, hips offset (x, y, z))],
	each pose added onto the idle's first frame. `smooth` keeps each bone's
	quaternion on the same side as its previous key, so keys interpolate the
	short way round."""
	act = _new_action(arm, name)
	last = {}
	for frame, rots, hips in keys:
		for pb in arm.pose.bones:
			rot, loc = base[pb.name]
			pb.rotation_mode = "QUATERNION"
			q = rot @ Euler([math.radians(a) for a in rots.get(pb.name, (0, 0, 0))], "XYZ").to_quaternion()
			if smooth and pb.name in last and q.dot(last[pb.name]) < 0.0:
				q.negate()
			last[pb.name] = q
			pb.rotation_quaternion = q
			pb.location = loc + (Vector(hips) if pb.name == "hips" else Vector())
		_key(arm, frame)
	return act


KICK = [
	(0, {}, (0, 0, 0)),
	(6, {"upperleg.r": (-50, 0, 0), "lowerleg.r": (80, 0, 0), "foot.r": (-10, 0, 0), "spine": (-6, 0, 0),
		 "upperleg.l": (6, 0, 0), "lowerleg.l": (12, 0, 0), "upperarm.l": (-10, 0, 25), "upperarm.r": (-10, 0, -25)}, (0, -0.04, 0)),
	(10, {"upperleg.r": (-88, 0, 0), "lowerleg.r": (4, 0, 0), "foot.r": (-25, 0, 0), "spine": (-12, 0, 0),
		  "upperleg.l": (8, 0, 0), "lowerleg.l": (14, 0, 0), "upperarm.l": (-20, 0, 35), "upperarm.r": (-20, 0, -35)}, (0, -0.05, -0.08)),
	(14, {"upperleg.r": (-80, 0, 0), "lowerleg.r": (10, 0, 0), "foot.r": (-20, 0, 0), "spine": (-10, 0, 0),
		  "upperleg.l": (8, 0, 0), "lowerleg.l": (14, 0, 0), "upperarm.l": (-15, 0, 30), "upperarm.r": (-15, 0, -30)}, (0, -0.05, -0.06)),
	(21, {}, (0, 0, 0)),
]
BASH = [
	(0, {}, (0, 0, 0)),
	(6, {"upperarm.l": (35, 0, 15), "lowerarm.l": (0, 0, -55), "spine": (4, 22, 0), "chest": (0, 10, 0),
		 "upperleg.r": (12, 0, 0), "lowerleg.r": (10, 0, 0)}, (0, 0, -0.08)),
	(9, {"upperarm.l": (82, 0, -12), "lowerarm.l": (0, 0, -12), "spine": (10, -18, 0), "chest": (0, -8, 0),
		 "upperleg.l": (-35, 0, 0), "lowerleg.l": (30, 0, 0), "upperleg.r": (18, 0, 0), "lowerleg.r": (6, 0, 0)}, (0, -0.05, 0.28)),
	(13, {"upperarm.l": (78, 0, -10), "lowerarm.l": (0, 0, -15), "spine": (8, -14, 0), "chest": (0, -6, 0),
		  "upperleg.l": (-32, 0, 0), "lowerleg.l": (28, 0, 0), "upperleg.r": (16, 0, 0), "lowerleg.r": (6, 0, 0)}, (0, -0.05, 0.25)),
	(20, {}, (0, 0, 0)),
]

# The stance at full draw: the torso turns side-on (a negative spine twist
# brings the left shoulder toward the target) and the head turns back to look
# down the arrow. The arm angles were searched for in Blender (hand and elbow
# positions: bow hand out at shoulder height, draw hand under the chin, elbow
# high and back), since the arms' local axes don't map to simple swings.
_DRAW = {"spine": (0, -35, 0), "chest": (0, -15, 0), "head": (0, 45, 0),
		 "upperarm.l": (80, 0, 0),
		 "upperarm.r": (140, -60, -40), "lowerarm.r": (120, 0, -140)}
BOW = [
	(0, {}, (0, 0, 0)),
	(7, {"spine": (0, -25, 0), "chest": (0, -10, 0), "head": (0, 32, 0),  # bow up, fingers on the string
		 "upperarm.l": (75, 0, 0),
		 "upperarm.r": (-20, 60, 120), "lowerarm.r": (0, 0, -60)}, (0, 0, 0)),
	(15, _DRAW, (0, 0, 0)),
	(21, _DRAW, (0, 0, 0)),
	(23, dict(_DRAW, **{"upperarm.r": (110, -90, -40), "lowerarm.r": (80, 0, -180)}), (0, 0, 0)),  # loose: the hand flies back
	(28, dict(_DRAW, **{"upperarm.r": (115, -80, -40), "lowerarm.r": (90, 0, -170)}), (0, 0, 0)),
	(38, {}, (0, 0, 0)),
]

# Swimming, with the water at the chest (the game keeps the body upright, so
# the lean is in the clip). The arm angles were solved in Blender by aiming
# each upper arm and forearm down a direction in the torso's frame (elbow and
# hand positions: reaching ahead, sweeping wide, pulling in under the chin),
# like Bow_Shoot's, since the arms' local axes don't map to simple swings.
# Swim_Forward: the torso leans ~25 degrees from the hips, head up; a
# breaststroke (reach, sweep out, pull in, recover) over a frog kick.
# Swim_Idle: treading water, arms sculling out and in at chest height (two
# figure-eights a loop), the legs cycling slowly in turn, a gentle bob.
SWIM = [
	(0, {"hips": (10, 0, 0), "spine": (10, 0, 0), "chest": (5, 0, 0), "head": (-22, 0, 0),
		 "upperarm.l": (66.2, 38.7, -56.6), "lowerarm.l": (2.8, -0.9, 37), "upperarm.r": (78.6, -37.5, 45),
		 "lowerarm.r": (4, 1.5, -40), "upperleg.l": (25, 0, 0), "lowerleg.l": (10, 0, 0),
		 "foot.l": (35, 0, 0), "upperleg.r": (25, 0, 0), "lowerleg.r": (10, 0, 0), "foot.r": (35, 0, 0)}, (0, 0, 0)),
	(9, {"hips": (10, 0, 0), "spine": (10, 0, 0), "chest": (5, 0, 0), "head": (-22, 0, 0),
		 "upperarm.l": (78.3, 8.9, -10.9), "lowerarm.l": (-3.9, 2, 55.8), "upperarm.r": (76.5, -6.3, 8),
		 "lowerarm.r": (-6.4, -3.5, -56.8), "upperleg.l": (15, 0, -8), "lowerleg.l": (60, 0, 0),
		 "foot.l": (20, 0, 0), "upperleg.r": (15, 0, 8), "lowerleg.r": (60, 0, 0), "foot.r": (20, 0, 0)}, (0, 0.01, 0)),
	(17, {"hips": (10, 0, 0), "spine": (10, 0, 0), "chest": (5, 0, 0), "head": (-22, 0, 0),
		 "upperarm.l": (58.8, -12.9, 22.7), "lowerarm.l": (35.7, 9.8, -29.7),
		 "upperarm.r": (52.2, 11.2, -22.6), "lowerarm.r": (43, -9.7, 24.3), "upperleg.l": (0, 0, -20),
		 "lowerleg.l": (105, 0, 0), "foot.l": (-10, 0, 0), "upperleg.r": (0, 0, 20),
		 "lowerleg.r": (105, 0, 0), "foot.r": (-10, 0, 0)}, (0, 0.03, 0)),
	(24, {"hips": (10, 0, 0), "spine": (10, 0, 0), "chest": (5, 0, 0), "head": (-22, 0, 0),
		 "upperarm.l": (44.3, 16.4, -39), "lowerarm.l": (22.4, 7.8, -37.8), "upperarm.r": (46, -17.3, 39.4),
		 "lowerarm.r": (32, -9.5, 32.3), "upperleg.l": (10, 0, -30), "lowerleg.l": (30, 0, 0),
		 "foot.l": (15, 0, 0), "upperleg.r": (10, 0, 30), "lowerleg.r": (30, 0, 0), "foot.r": (15, 0, 0)}, (0, 0.015, 0)),
	(30, {"hips": (10, 0, 0), "spine": (10, 0, 0), "chest": (5, 0, 0), "head": (-22, 0, 0),
		 "upperarm.l": (58.6, 36.5, -60.9), "lowerarm.l": (7.4, -2, 30.8), "upperarm.r": (70, -37, 51.2),
		 "lowerarm.r": (9.8, 3.1, -34.8), "upperleg.l": (22, 0, -10), "lowerleg.l": (12, 0, 0),
		 "foot.l": (30, 0, 0), "upperleg.r": (22, 0, 10), "lowerleg.r": (12, 0, 0), "foot.r": (30, 0, 0)}, (0, 0.0, 0)),
	(36, {"hips": (10, 0, 0), "spine": (10, 0, 0), "chest": (5, 0, 0), "head": (-22, 0, 0),
		 "upperarm.l": (66.2, 38.7, -56.6), "lowerarm.l": (2.8, -0.9, 37), "upperarm.r": (78.6, -37.5, 45),
		 "lowerarm.r": (4, 1.5, -40), "upperleg.l": (25, 0, 0), "lowerleg.l": (10, 0, 0),
		 "foot.l": (35, 0, 0), "upperleg.r": (25, 0, 0), "lowerleg.r": (10, 0, 0), "foot.r": (35, 0, 0)}, (0, 0, 0)),
]
TREAD = [
	(0, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-6, 0, 0), "upperarm.l": (54.3, 8.4, -16.2),
		 "lowerarm.l": (12.2, -1.9, 18), "upperarm.r": (55.3, -7.7, 14.6), "lowerarm.r": (15.7, 3.1, -21.8),
		 "upperleg.l": (-22, 0, -8), "lowerleg.l": (70, 0, 0), "foot.l": (-10, 0, 0),
		 "upperleg.r": (-22, 0, 8), "lowerleg.r": (20, 0, 0), "foot.r": (-10, 0, 0)}, (0, 0.0, 0)),
	(5, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-3.4, 0, 0), "upperarm.l": (56.6, 8.3, -15.4),
		 "lowerarm.l": (19.9, -1.7, 9.6), "upperarm.r": (57.5, -7.4, 13.4), "lowerarm.r": (24.6, 3.1, -14.2),
		 "upperleg.l": (-30, 0, -8), "lowerleg.l": (66.7, 0, 0), "foot.l": (-5, 0, 0),
		 "upperleg.r": (-14, 0, 8), "lowerleg.r": (23.3, 0, 0), "foot.r": (-15, 0, 0)}, (0, 0.017, 0)),
	(10, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-3.4, 0, 0), "upperarm.l": (56.6, 8.3, -15.4),
		 "lowerarm.l": (7.1, 1.1, -17.5), "upperarm.r": (57.5, -7.4, 13.4), "lowerarm.r": (15, -1.9, 14),
		 "upperleg.l": (-35.9, 0, -8), "lowerleg.l": (57.5, 0, 0), "foot.l": (-1.3, 0, 0),
		 "upperleg.r": (-8.1, 0, 8), "lowerleg.r": (32.5, 0, 0), "foot.r": (-18.7, 0, 0)}, (0, 0.017, 0)),
	(15, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-6, 0, 0), "upperarm.l": (54.3, 8.4, -16.2),
		 "lowerarm.l": (16.6, 4.6, -30.6), "upperarm.r": (55.3, -7.7, 14.6), "lowerarm.r": (25.4, -5.9, 26),
		 "upperleg.l": (-38, 0, -8), "lowerleg.l": (45, 0, 0), "upperleg.r": (-6, 0, 8),
		 "lowerleg.r": (45, 0, 0), "foot.r": (-20, 0, 0)}, (0, 0.0, 0)),
	(20, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-8.6, 0, 0), "upperarm.l": (52, 8.4, -17.1),
		 "lowerarm.l": (25.9, 3.6, -15.6), "upperarm.r": (53, -7.9, 15.7), "lowerarm.r": (33.4, -3.1, 10.4),
		 "upperleg.l": (-35.9, 0, -8), "lowerleg.l": (32.5, 0, 0), "foot.l": (-1.3, 0, 0),
		 "upperleg.r": (-8.1, 0, 8), "lowerleg.r": (57.5, 0, 0), "foot.r": (-18.7, 0, 0)}, (0, -0.017, 0)),
	(25, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-8.6, 0, 0), "upperarm.l": (52, 8.4, -17.1),
		 "lowerarm.l": (7.8, -0.6, 8.1), "upperarm.r": (53, -7.9, 15.7), "lowerarm.r": (12.7, 1.3, -11.4),
		 "upperleg.l": (-30, 0, -8), "lowerleg.l": (23.3, 0, 0), "foot.l": (-5, 0, 0),
		 "upperleg.r": (-14, 0, 8), "lowerleg.r": (66.7, 0, 0), "foot.r": (-15, 0, 0)}, (0, -0.017, 0)),
	(30, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-6, 0, 0), "upperarm.l": (54.3, 8.4, -16.2),
		 "lowerarm.l": (12.2, -1.9, 18), "upperarm.r": (55.3, -7.7, 14.6), "lowerarm.r": (15.7, 3.1, -21.8),
		 "upperleg.l": (-22, 0, -8), "lowerleg.l": (20, 0, 0), "foot.l": (-10, 0, 0),
		 "upperleg.r": (-22, 0, 8), "lowerleg.r": (70, 0, 0), "foot.r": (-10, 0, 0)}, (0, -0.0, 0)),
	(35, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-3.4, 0, 0), "upperarm.l": (56.6, 8.3, -15.4),
		 "lowerarm.l": (19.9, -1.7, 9.6), "upperarm.r": (57.5, -7.4, 13.4), "lowerarm.r": (24.6, 3.1, -14.2),
		 "upperleg.l": (-14, 0, -8), "lowerleg.l": (23.3, 0, 0), "foot.l": (-15, 0, 0),
		 "upperleg.r": (-30, 0, 8), "lowerleg.r": (66.7, 0, 0), "foot.r": (-5, 0, 0)}, (0, 0.017, 0)),
	(40, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-3.4, 0, 0), "upperarm.l": (56.6, 8.3, -15.4),
		 "lowerarm.l": (7.1, 1.1, -17.5), "upperarm.r": (57.5, -7.4, 13.4), "lowerarm.r": (15, -1.9, 14),
		 "upperleg.l": (-8.1, 0, -8), "lowerleg.l": (32.5, 0, 0), "foot.l": (-18.7, 0, 0),
		 "upperleg.r": (-35.9, 0, 8), "lowerleg.r": (57.5, 0, 0), "foot.r": (-1.3, 0, 0)}, (0, 0.017, 0)),
	(45, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-6, 0, 0), "upperarm.l": (54.3, 8.4, -16.2),
		 "lowerarm.l": (16.6, 4.6, -30.6), "upperarm.r": (55.3, -7.7, 14.6), "lowerarm.r": (25.4, -5.9, 26),
		 "upperleg.l": (-6, 0, -8), "lowerleg.l": (45, 0, 0), "foot.l": (-20, 0, 0),
		 "upperleg.r": (-38, 0, 8), "lowerleg.r": (45, 0, 0)}, (0, 0.0, 0)),
	(50, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-8.6, 0, 0), "upperarm.l": (52, 8.4, -17.1),
		 "lowerarm.l": (25.9, 3.6, -15.6), "upperarm.r": (53, -7.9, 15.7), "lowerarm.r": (33.4, -3.1, 10.4),
		 "upperleg.l": (-8.1, 0, -8), "lowerleg.l": (57.5, 0, 0), "foot.l": (-18.7, 0, 0),
		 "upperleg.r": (-35.9, 0, 8), "lowerleg.r": (32.5, 0, 0), "foot.r": (-1.3, 0, 0)}, (0, -0.017, 0)),
	(55, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-8.6, 0, 0), "upperarm.l": (52, 8.4, -17.1),
		 "lowerarm.l": (7.8, -0.6, 8.1), "upperarm.r": (53, -7.9, 15.7), "lowerarm.r": (12.7, 1.3, -11.4),
		 "upperleg.l": (-14, 0, -8), "lowerleg.l": (66.7, 0, 0), "foot.l": (-15, 0, 0),
		 "upperleg.r": (-30, 0, 8), "lowerleg.r": (23.3, 0, 0), "foot.r": (-5, 0, 0)}, (0, -0.017, 0)),
	(60, {"spine": (5, 0, 0), "chest": (2, 0, 0), "head": (-6, 0, 0), "upperarm.l": (54.3, 8.4, -16.2),
		 "lowerarm.l": (12.2, -1.9, 18), "upperarm.r": (55.3, -7.7, 14.6), "lowerarm.r": (15.7, 3.1, -21.8),
		 "upperleg.l": (-22, 0, -8), "lowerleg.l": (70, 0, 0), "foot.l": (-10, 0, 0),
		 "upperleg.r": (-22, 0, 8), "lowerleg.r": (20, 0, 0), "foot.r": (-10, 0, 0)}, (0, -0.0, 0)),
]


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
	keep.append(_keys(arm, base, "Kick", KICK))
	keep.append(_keys(arm, base, "Shield_Bash", BASH))
	keep.append(_keys(arm, base, "Bow_Shoot", BOW))
	keep.append(_keys(arm, base, "Swim_Forward", SWIM, smooth=True))
	keep.append(_keys(arm, base, "Swim_Idle", TREAD, smooth=True))

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
