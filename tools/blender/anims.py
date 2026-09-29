"""Extra animations for KayKit's shared Rig_Medium skeleton, for poses the free
packs lack. Exported as their own clip library (assets/animations/), which
models.json "animations" lists after KayKit's, so every character gets them.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/anims.py -- --out assets/animations

Clips:
  Sit_Floor_Down  from standing to sitting on the ground, legs out in front
                  (EverQuest's /sit; knees drawn up vanish into these chibi bodies)
  Sit_Floor_Idle  sitting, breathing (loops)
  Sit_Chair_Idle  slumped in a chair, arms folded, head down: a grumpy regular
                  (seated npcs, npcs.json "seated": "chair"; loops, 3 s)
  Kick            a front kick with the right leg: chamber, snap, recover
  Shield_Bash     a lunge driving the left (shield) arm forward
  Bow_Shoot       bow arm up (the bow is in the left hand), draw to the cheek,
                  hold, release; the body turns side-on to the target
  Swim_Forward    breaststroke with a frog kick, leaning into it (loops, 1.2 s)
  Swim_Idle       treading water: arms sculling, legs cycling, a bob (loops, 2 s)

Emotes (one-shots that start and end on the idle's first frame):
  Emote_Wave      2.0 s  right arm up high, the hand waving out and in three times
  Emote_Bow       2.2 s  hand to the chest, a deep bow from the waist, hold, rise
  Emote_Rude      2.2 s  a fist shaken at the target, leaning in, then turning away
                         nose in the air with a "talk to the hand" palm
  Emote_Cheer     2.2 s  a crouch, a hop with both arms thrown up in a V, two fist pumps
  Emote_Dance     4.0 s  knee lifts with pumping arms and a turning torso, then the
                         disco point with swaying hips (two beats a second)
  Emote_Laugh     2.2 s  leaning back, hands on the belly, chest and head shaking
  Emote_Cry       2.6 s  hunched, both hands to the face, sobbing shoulders
  Emote_Point     1.8 s  the right arm straight out ahead, leaning in, hold
  Emote_Salute    2.0 s  hand to the brow, standing tall, hold, snapped down
  Emote_Kneel     3.2 s  down on the left knee, right hand on the right knee, head
                         bowed, hold about 1.5 s, rise
  Emote_Shrug     1.6 s  forearms out palms up, head tilted
  Emote_Clap      2.0 s  five claps in front of the chest
  Emote_Nod       1.4 s  two nods
  Emote_Shake     1.6 s  three head shakes, hands a little out
  Emote_Flex      2.2 s  a double-arm strongman flex, chest out, three pumps
  Emote_Yawn      2.4 s  arms stretched up and out, head back, then a slump
The emotes' arm angles are solved when the file runs (`_solve`: "dir", "at"
and "on" aims), not typed in; see the note above it.

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

# sitting in a chair, grumpy (Merrick in the tavern): thighs level, shins
# straight down, hips dropped by the thigh's length (0.227) so the feet stay
# on the floor; slumped over, arms folded, head down
_CHAIR_LEGS = {
	"upperleg.l": (-90, 0, -6),
	"upperleg.r": (-90, 0, 6),
	"lowerleg.l": (90, 0, 0),
	"lowerleg.r": (90, 0, 0),
}
_CHAIR_HIPS = (0, -0.227, 0)
_FOLDED = {"r": ("on", "chest", (-0.07, 0.15, 0.17), (1, -0.6, 0.3)),
		   "l": ("on", "chest", (-0.07, 0.11, 0.19), (1, -0.6, 0.3))}


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
	for key in keys:
		frame, rots, hips = key[:3]
		if len(key) > 3 and key[3]:
			rots = _solve(arm, base, rots, hips, key[3])
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


# Solving arm angles. The arms' local axes don't map to simple swings, so the
# emotes say where each arm should go and the angles are worked out here, in
# the pose the rest of the body is in:
#   ("dir", upper, fore[, palm])  the upper arm and forearm point along these
#                                 directions in the chest's frame
#   ("at", hand, pole[, palm])    the hand (the wrist's end) goes to this point,
#                                 measured from the shoulder in the chest's
#                                 frame, the elbow bending out toward `pole`
#   ("on", bone, point, pole[, palm])  the hand goes to a point in that bone's
#                                 frame (from its head), e.g. a cheek on "head"
# Vectors are (out, up, forward): "out" is toward that arm's side, so one
# number serves either arm. Each bone swings the short way from where the
# idle holds it; `palm` then turns the forearm about its length until the
# palm faces that way (it faces the thigh in the idle).
def _pose_set(arm, base, rots, hips):
	for pb in arm.pose.bones:
		rot, loc = base[pb.name]
		pb.rotation_mode = "QUATERNION"
		pb.rotation_quaternion = rot @ Euler([math.radians(a) for a in rots.get(pb.name, (0, 0, 0))], "XYZ").to_quaternion()
		pb.location = loc + (Vector(hips) if pb.name == "hips" else Vector())
	bpy.context.view_layer.update()


def _frame_vec(pb, side, v):
	"""(out, up, forward) in a bone's frame (X left, Y up, Z forward for the
	torso and head) to armature space; the right arm's "out" is -X."""
	m = pb.matrix.to_3x3().normalized()
	return m @ Vector(((1 if side == "l" else -1) * v[0], v[1], v[2]))


def _swing(pb, d, palm=None, hand=None):
	"""Turns a bone the short way until it points along d; with palm, then
	twists it about d until the hand's palm (its -Z) faces palm."""
	d = d.normalized()
	m = pb.matrix.copy()
	r = m.col[1].xyz.normalized().rotation_difference(d).to_matrix() @ m.to_3x3().normalized()
	nm = r.to_4x4()
	nm.translation = m.translation
	pb.matrix = nm
	bpy.context.view_layer.update()
	if palm is not None and hand is not None:
		now = -hand.matrix.col[2].xyz
		now = (now - d * now.dot(d)).normalized()
		want = (palm - d * palm.dot(d)).normalized()
		ang = now.angle(want, 0.0)
		if now.cross(want).dot(d) < 0:
			ang = -ang
		r = Quaternion(d, ang).to_matrix() @ r
		nm = r.to_4x4()
		nm.translation = m.translation
		pb.matrix = nm
		bpy.context.view_layer.update()


def _extra(base, pb):
	e = (base[pb.name][0].inverted() @ pb.rotation_quaternion).to_euler("XYZ")
	return tuple(round(math.degrees(a), 2) for a in e)


def _solve(arm, base, rots, hips, aims):
	"""rots plus the solved upper arm and forearm angles for each arm in aims."""
	_pose_set(arm, base, rots, hips)
	out = dict(rots)
	bones = arm.pose.bones
	chest = bones["chest"]
	for side, aim in aims.items():
		up, lo, wr, hand = (bones[b + "." + side] for b in ("upperarm", "lowerarm", "wrist", "hand"))
		kind = aim[0]
		palm = None
		if kind == "dir":
			d_up, d_lo = _frame_vec(chest, side, aim[1]), _frame_vec(chest, side, aim[2])
			if len(aim) > 3:
				palm = _frame_vec(chest, side, aim[3])
		else:
			s = up.head.copy()
			if kind == "at":
				t = s + _frame_vec(chest, side, aim[1])
				pole, rest = aim[2], aim[3:]
			else:
				ref = bones[aim[1]]
				t = ref.head + _frame_vec(ref, side, aim[2])
				pole, rest = aim[3], aim[4:]
			if rest:
				palm = _frame_vec(chest, side, rest[0])
			a, b = up.length, lo.length + wr.length
			v = t - s
			dist = max(min(v.length, a + b - 0.002), abs(a - b) + 0.002)
			u = v.normalized()
			p = _frame_vec(chest, side, pole)
			p = (p - u * p.dot(u)).normalized()
			c = (a * a + dist * dist - b * b) / (2 * a * dist)
			elbow = s + a * (u * c + p * math.sqrt(max(0.0, 1 - c * c)))
			d_up, d_lo = elbow - s, s + u * dist - elbow
		_swing(up, d_up)
		_swing(lo, d_lo, palm, hand)
		out[up.name] = _extra(base, up)
		out[lo.name] = _extra(base, lo)
	return out


def _crouch(h, fwd=0.0):
	"""Leg angles and hips offset that lower the hips by h with the feet flat
	where they stood (thigh 0.227 m + shin 0.149 m)."""
	t = math.degrees(math.acos(max(-1.0, 1 - h / 0.376)))
	legs = {}
	for s in ("l", "r"):
		legs["upperleg." + s] = (-t, 0, 0)
		legs["lowerleg." + s] = (2 * t, 0, 0)
		legs["foot." + s] = (-t, 0, 0)
	return legs, (0, -h, fwd - 0.078 * math.sin(math.radians(t)))


def _with(*parts):
	out = {}
	for p in parts:
		out.update(p)
	return out


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


# --- Emotes ------------------------------------------------------------------
# Social one-shots, each starting and ending on the idle's first frame. Keys are
# (frame, {bone: degrees}, hips offset (left, up, forward), {"r"/"l": aim});
# the aims are solved above. The heads are huge and the arms short (the hand
# reaches about 0.58 m from the shoulder, the head's side is 0.43 m from the
# middle), so hands stay beside or in front of the head, never over it.

def _wave_arm(out):
	return {"r": ("dir", (0.8, 0.55, 0.3), (out, 0.95, 0.25), (0, 0, 1))}


_WAVE_T = {"chest": (-3, 0, 0), "head": (-4, 0, -10)}
WAVE = [
	(0, {}, (0, 0, 0)),
	(9, _WAVE_T, (0, 0, 0), _wave_arm(0.35)),
	(15, _with(_WAVE_T, {"head": (-4, 0, -13)}), (0, 0, 0), _wave_arm(0.95)),
	(21, _WAVE_T, (0, 0, 0), _wave_arm(0.25)),
	(27, _with(_WAVE_T, {"head": (-4, 0, -13)}), (0, 0, 0), _wave_arm(0.95)),
	(33, _WAVE_T, (0, 0, 0), _wave_arm(0.25)),
	(39, _with(_WAVE_T, {"head": (-4, 0, -13)}), (0, 0, 0), _wave_arm(0.95)),
	(45, _WAVE_T, (0, 0, 0), _wave_arm(0.4)),
	(60, {}, (0, 0, 0)),
]

_BOW_HAND = {"r": ("at", (-0.17, -0.12, 0.3), (1, -0.5, 0), (-1, 0, -0.3)),
			 "l": ("dir", (0.45, -0.85, -0.25), (0.35, -0.9, -0.1))}
_BOWED = {"spine": (25, 0, 0), "chest": (20, 0, 0), "head": (15, 0, 0)}
BOW_EMOTE = [
	(0, {}, (0, 0, 0)),
	(9, {"head": (6, 0, 0)}, (0, 0, 0), _BOW_HAND),
	(22, _BOWED, (0, 0, -0.05), _BOW_HAND),
	(42, _with(_BOWED, {"head": (18, 0, 0)}), (0, 0, -0.05), _BOW_HAND),
	(55, {"spine": (5, 0, 0), "head": (4, 0, 0)}, (0, 0, 0), _BOW_HAND),
	(66, {}, (0, 0, 0)),
]

# a fist shaken at the target, leaning in, then turning away nose in the air
# and flicking the hand out: "bah, get lost"
_RUDE_LEAN = {"spine": (12, -4, 0), "chest": (6, -3, 0), "head": (-10, 4, 0)}
_ON_HIP = ("at", (0.2, -0.34, -0.03), (1, 0.1, -0.7))


def _fist(fore):
	return {"r": ("dir", (0.8, 0.5, 0.35), fore, (-1, 0, 0)), "l": _ON_HIP}


RUDE = [
	(0, {}, (0, 0, 0)),
	(8, _RUDE_LEAN, (0, 0, 0.04), _fist((0.45, 0.85, 0.3))),
	(12, _RUDE_LEAN, (0, 0, 0.05), _fist((0.42, 0.6, 0.68))),
	(15, _RUDE_LEAN, (0, 0, 0.05), _fist((0.5, 0.86, 0.1))),
	(18, _RUDE_LEAN, (0, 0, 0.05), _fist((0.42, 0.6, 0.68))),
	(21, _RUDE_LEAN, (0, 0, 0.05), _fist((0.5, 0.86, 0.1))),
	(24, _RUDE_LEAN, (0, 0, 0.05), _fist((0.42, 0.6, 0.68))),
	(28, _RUDE_LEAN, (0, 0, 0.04), _fist((0.45, 0.85, 0.3))),
	(32, _with(_RUDE_LEAN, {"head": (-12, 0, 0)}), (0, 0, 0.02), {"r": ("dir", (0.7, -0.4, 0.6), (0.3, -0.1, 0.95)), "l": _ON_HIP}),
	(38, {"spine": (-3, 12, 0), "chest": (-4, 8, 0), "head": (-20, 40, 0)}, (0, 0, -0.02),
	 {"r": ("dir", (0.45, 0.2, 0.9), (0.4, 0.5, 0.8), (0, 0, 1)), "l": _ON_HIP}),
	(42, {"spine": (-4, 14, 0), "chest": (-5, 9, 0), "head": (-24, 45, 0)}, (0, 0, -0.02),
	 {"r": ("dir", (0.45, 0.25, 0.88), (0.4, 0.45, 0.82), (0, 0, 1)), "l": _ON_HIP}),
	(54, {"spine": (-4, 14, 0), "chest": (-5, 9, 0), "head": (-24, 45, 0)}, (0, 0, -0.02),
	 {"r": ("dir", (0.45, 0.25, 0.88), (0.4, 0.45, 0.82), (0, 0, 1)), "l": _ON_HIP}),
	(66, {}, (0, 0, 0)),
]

_V = {s: ("dir", (0.8, 0.58, 0.15), (0.65, 0.75, 0.15), (0, 0, 1)) for s in ("r", "l")}
_PUMP = {s: ("dir", (0.95, 0.2, 0.2), (0.45, 0.9, 0.15), (-1, 0, 0)) for s in ("r", "l")}
_CHEER_UP = {"chest": (-6, 0, 0), "head": (-12, 0, 0)}
_TUCK = {"upperleg.l": (-12, 0, 0), "lowerleg.l": (28, 0, 0), "foot.l": (20, 0, 0),
		 "upperleg.r": (-12, 0, 0), "lowerleg.r": (28, 0, 0), "foot.r": (20, 0, 0)}
_C1, _C1H = _crouch(0.07)
_C2, _C2H = _crouch(0.04)
CHEER = [
	(0, {}, (0, 0, 0)),
	(7, _with(_C1, {"spine": (8, 0, 0), "head": (4, 0, 0)}), _C1H,
	 {"r": ("dir", (0.3, -0.85, -0.3), (0.3, -0.5, 0.8)), "l": ("dir", (0.3, -0.85, -0.3), (0.3, -0.5, 0.8))}),
	(13, _with(_TUCK, _CHEER_UP), (0, 0.13, 0), _V),
	(19, _with(_C2, _CHEER_UP), _C2H, _V),
	(25, {"chest": (-3, 0, 0), "head": (-6, 0, 0)}, (0, 0, 0), _PUMP),
	(31, _with(_CHEER_UP), (0, 0, 0), _V),
	(37, {"chest": (-3, 0, 0), "head": (-6, 0, 0)}, (0, 0, 0), _PUMP),
	(43, _with(_CHEER_UP), (0, 0, 0), _V),
	(52, {"chest": (-4, 0, 0), "head": (-8, 0, 0)}, (0, 0, 0), _V),
	(66, {}, (0, 0, 0)),
]


# The dance, two beats a second: four beats of knee-lifts with the arms
# pumping in turn and the torso turning with them, then four of the
# disco point (up and out, down and across) with the hips swaying.
def _knee(s):
	return {"upperleg." + s: (-48, 0, 0), "lowerleg." + s: (80, 0, 0), "foot." + s: (-15, 0, 0)}


def _pump_arms(front):
	back = "l" if front == "r" else "r"
	return {front: ("dir", (0.5, -0.2, 0.85), (0.4, 0.75, 0.55), (-1, 0, 0)),
			back: ("dir", (0.35, -0.8, -0.5), (0.25, -0.1, 0.95), (-1, 0, 0))}


_DB, _DBH = _crouch(0.05)
_POINT_UP = {"r": ("dir", (0.8, 0.6, 0.25), (0.66, 0.74, 0.2)), "l": _ON_HIP}
_POINT_DOWN = {"r": ("dir", (-0.2, -0.75, 0.6), (-0.3, -0.75, 0.55)), "l": _ON_HIP}
DANCE = [
	(0, {}, (0, 0, 0)),
	(7, _with(_DB, {"spine": (4, 0, 0)}), _DBH, _pump_arms("l")),
	(15, _with(_knee("l"), {"spine": (-2, -14, 0), "chest": (0, -6, 0), "head": (0, 10, 6)}), (0, 0, 0), _pump_arms("r")),
	(22, _with(_DB, {"spine": (4, 0, 0)}), _DBH, _pump_arms("l")),
	(30, _with(_knee("r"), {"spine": (-2, 14, 0), "chest": (0, 6, 0), "head": (0, -10, -6)}), (0, 0, 0), _pump_arms("l")),
	(37, _with(_DB, {"spine": (4, 0, 0)}), _DBH, _pump_arms("r")),
	(45, _with(_knee("l"), {"spine": (-2, -14, 0), "chest": (0, -6, 0), "head": (0, 10, 6)}), (0, 0, 0), _pump_arms("r")),
	(52, _with(_DB, {"spine": (4, 0, 0)}), _DBH, _pump_arms("l")),
	(60, _with(_knee("r"), {"spine": (-2, 14, 0), "chest": (0, 6, 0), "head": (0, -10, -6)}), (0, 0, 0), _pump_arms("l")),
	(67, _with(_DB, {"spine": (0, 0, 6), "head": (0, 0, -6)}), (_DBH[0] + 0.04, _DBH[1], _DBH[2]), _POINT_DOWN),
	(75, {"spine": (-4, 10, -5), "chest": (-4, 0, 0), "head": (-15, 0, 8)}, (-0.04, 0, 0), _POINT_UP),
	(82, _with(_DB, {"spine": (4, 0, 6), "head": (8, 0, -6)}), (_DBH[0] + 0.04, _DBH[1], _DBH[2]), _POINT_DOWN),
	(90, {"spine": (-4, 10, -5), "chest": (-4, 0, 0), "head": (-15, 0, 8)}, (-0.04, 0, 0), _POINT_UP),
	(97, _with(_DB, {"spine": (4, 0, 6), "head": (8, 0, -6)}), (_DBH[0] + 0.04, _DBH[1], _DBH[2]), _POINT_DOWN),
	(105, {"spine": (-4, 10, -5), "chest": (-4, 0, 0), "head": (-15, 0, 8)}, (-0.04, 0, 0), _POINT_UP),
	(120, {}, (0, 0, 0)),
]

_BELLY = {"r": ("at", (-0.12, -0.36, 0.3), (1, -0.3, 0.2), (-0.4, 0, -1)),
		  "l": ("at", (-0.1, -0.44, 0.28), (1, -0.3, 0.2), (-0.4, 0, -1))}


def _laugh(k):
	return {"spine": (-13, 0, 3 * k), "chest": (-14 + 7 * k, 0, 0), "head": (-28 - 8 * k, 0, 0)}


LAUGH = [
	(0, {}, (0, 0, 0)),
	(10, _laugh(0), (0, 0, 0.03), _BELLY),
] + [(13 + 3 * i, _laugh(1 if i % 2 == 0 else -1), (0, 0.012 * (i % 2), 0.03), _BELLY) for i in range(14)] + [
	(58, _laugh(0), (0, 0, 0.03), _BELLY),
	(66, {}, (0, 0, 0)),
]

# hands to the (lower) face; the head, pitched down, meets them
_FACE = {s: ("on", "head", (0.2, 0.1, 0.6), (1, -0.4, 0), (-1, 0, -1)) for s in ("r", "l")}


def _sob(k):
	return {"spine": (9, 0, 3 * k), "chest": (8 + 4 * abs(k), 0, 0), "head": (16 - 3 * k, 0, 0)}


_SAG, _SAGH = _crouch(0.025)
_SAG2, _SAG2H = _crouch(0.04)
CRY = [
	(0, {}, (0, 0, 0)),
	(6, {"spine": (6, 0, 0), "head": (10, 0, 0)}, (0, 0, 0),
	 {s: ("dir", (0.5, -0.3, 0.8), (0.1, 0.6, 0.8)) for s in ("r", "l")}),
	(12, _with(_SAG, _sob(0)), _SAGH, _FACE),
] + [(16 + 4 * i, _with(_SAG2 if i % 2 == 0 else _SAG, _sob(1 if i % 2 == 0 else -1)), _SAG2H if i % 2 == 0 else _SAGH, _FACE)
	 for i in range(12)] + [
	(66, _with(_SAG, _sob(0)), _SAGH, _FACE),
	(78, {}, (0, 0, 0)),
]

_POINTING = {"spine": (8, 10, 0), "chest": (4, 5, 0), "head": (-12, -8, 0)}
POINT = [
	(0, {}, (0, 0, 0)),
	(7, _POINTING, (0, 0, 0.03), {"r": ("dir", (0.3, 0.5, 1), (0.25, 0.45, 1), (-1, -0.3, 0)),
								  "l": ("dir", (0.3, -0.9, -0.3), (0.2, -0.9, 0.1))}),
	(11, _POINTING, (0, 0, 0.04), {"r": ("dir", (0.3, 0.38, 1), (0.25, 0.35, 1), (-1, -0.3, 0)),
								   "l": ("dir", (0.3, -0.9, -0.3), (0.2, -0.9, 0.1))}),
	(40, _POINTING, (0, 0, 0.04), {"r": ("dir", (0.3, 0.38, 1), (0.25, 0.35, 1), (-1, -0.3, 0)),
								   "l": ("dir", (0.3, -0.9, -0.3), (0.2, -0.9, 0.1))}),
	(54, {}, (0, 0, 0)),
]

_UPRIGHT = {"spine": (-3, 0, 0), "chest": (-4, 0, 0), "head": (-3, 0, 0)}
_SALUTE = {"r": ("on", "head", (0.5, 0.22, 0.48), (1, 0.2, 0.1), (0, 0, 1))}
SALUTE = [
	(0, {}, (0, 0, 0)),
	(9, _UPRIGHT, (0, 0, 0), _SALUTE),
	(42, _UPRIGHT, (0, 0, 0), _SALUTE),
	(46, _UPRIGHT, (0, 0, 0), {"r": ("dir", (0.3, -1, 0.02), (0.25, -1, 0.05))}),
	(60, {}, (0, 0, 0)),
]

_KNEEL = {"upperleg.l": (2, 0, -3), "lowerleg.l": (101, 0, 0), "foot.l": (25, 0, 0),
		  "upperleg.r": (-74, 0, 3), "lowerleg.r": (76, 0, 0), "foot.r": (0, 0, 0),
		  "spine": (8, 0, 0), "chest": (4, 0, 0), "head": (25, 0, 0)}
_KNEEL_HIPS = (0, -0.18, 0)
_KNEEL_HALF = {"upperleg.l": (-5, 0, -3), "lowerleg.l": (90, 0, 0), "foot.l": (20, 0, 0),
			   "upperleg.r": (-50, 0, 3), "lowerleg.r": (20, 0, 0), "foot.r": (30, 0, 0),
			   "spine": (10, 0, 0), "head": (10, 0, 0)}
_ON_KNEE = {"r": ("on", "lowerleg.r", (0, -0.08, -0.1), (1, 0, -0.2)),
			"l": ("dir", (0.2, -1, 0.1), (0.1, -1, 0.2))}
_KNEEL_START = {"upperleg.l": (-4, 0, -3), "lowerleg.l": (90, 0, 0), "foot.l": (10, 0, 0),
				"upperleg.r": (-40, 0, 3), "lowerleg.r": (30, 0, 0), "foot.r": (10, 0, 0), "spine": (5, 0, 0), "head": (5, 0, 0)}
_KNEEL_LIFT = {"upperleg.l": (-20, 0, -3), "lowerleg.l": (65, 0, 0), "foot.l": (0, 0, 0),  # the back foot lifted
			   "upperleg.r": (-15, 0, 3), "lowerleg.r": (20, 0, 0), "foot.r": (-5, 0, 0)}
KNEEL = [
	(0, {}, (0, 0, 0)),
	(3, _KNEEL_LIFT, (0, -0.01, 0)),
	(6, _KNEEL_START, (0, -0.06, 0)),
	(10, _KNEEL_HALF, (0, -0.08, 0)),
	(20, _KNEEL, _KNEEL_HIPS, _ON_KNEE),
	(43, _with(_KNEEL, {"head": (28, 0, 0)}), _KNEEL_HIPS, _ON_KNEE),
	(66, _KNEEL, _KNEEL_HIPS, _ON_KNEE),
	(76, _KNEEL_HALF, (0, -0.08, 0)),
	(81, _KNEEL_START, (0, -0.06, 0)),
	(88, _KNEEL_LIFT, (0, -0.01, 0)),
	(96, {}, (0, 0, 0)),
]

_SHRUG_ARMS = {"r": ("dir", (0.45, -0.85, 0.15), (0.8, 0.15, 0.6), (0, 1, 0)),
			   "l": ("dir", (0.45, -0.85, 0.15), (0.8, 0.15, 0.6), (0, 1, 0))}
SHRUG = [
	(0, {}, (0, 0, 0)),
	(9, {"chest": (-4, 0, 0), "head": (-6, 0, 14)}, (0, 0, 0), _SHRUG_ARMS),
	(14, {"chest": (-5, 0, 0), "head": (-7, 0, 17)}, (0, 0, 0), _SHRUG_ARMS),
	(30, {"chest": (-4, 0, 0), "head": (-6, 0, 15)}, (0, 0, 0), _SHRUG_ARMS),
	(48, {}, (0, 0, 0)),
]

_CLAP_T = {"chest": (3, 0, 0), "head": (5, 0, 0)}
_CLAP_IN = {s: ("at", (-0.17, -0.15, 0.33), (1, -0.6, -0.2), (-1, 0, 0)) for s in ("r", "l")}
_CLAP_OUT = {s: ("at", (0.02, -0.12, 0.3), (1, -0.6, -0.2), (-1, 0, 0)) for s in ("r", "l")}
CLAP = [(0, {}, (0, 0, 0))] + [
	(f, _CLAP_T, (0, 0, 0), _CLAP_OUT if i % 2 == 0 else _CLAP_IN)
	for i, f in enumerate([8, 11, 16, 19, 24, 27, 32, 35, 40, 43, 48])] + [(60, {}, (0, 0, 0))]

NOD = [
	(0, {}, (0, 0, 0)),
	(7, {"head": (18, 0, 0), "chest": (3, 0, 0)}, (0, 0, 0)),
	(13, {"head": (-4, 0, 0)}, (0, 0, 0)),
	(20, {"head": (18, 0, 0), "chest": (3, 0, 0)}, (0, 0, 0)),
	(27, {"head": (-3, 0, 0)}, (0, 0, 0)),
	(34, {"head": (4, 0, 0)}, (0, 0, 0)),
	(42, {}, (0, 0, 0)),
]

_NO_HANDS = {s: ("dir", (0.35, -0.9, 0.1), (0.55, -0.3, 0.75), (0, 1, 0)) for s in ("r", "l")}
SHAKE = [(0, {}, (0, 0, 0))] + [
	(f, {"head": (2, y, 0), "chest": (0, -y * 0.15, 0)}, (0, 0, 0), _NO_HANDS)
	for f, y in [(6, 24), (13, -24), (20, 24), (27, -24), (34, 20), (40, -8)]] + [(48, {}, (0, 0, 0))]

_FLEX = {s: ("dir", (1, 0.25, 0.1), (0.38, 1, -0.05), (-1, 0, 0)) for s in ("r", "l")}
_FLEX_PUMP = {s: ("dir", (1, 0.4, 0.05), (0.42, 1, 0.05), (-1, 0, 0)) for s in ("r", "l")}
FLEX = [
	(0, {}, (0, 0, 0)),
	(10, {"spine": (-4, 8, 0), "chest": (-8, 0, 0), "head": (-6, -6, 0)}, (0, 0, 0), _FLEX),
	(18, {"spine": (-5, 8, 0), "chest": (-12, 0, 0), "head": (-8, -6, 0)}, (0, 0.015, 0), _FLEX_PUMP),
	(26, {"spine": (-4, -8, 0), "chest": (-8, 0, 0), "head": (-6, 6, 0)}, (0, 0, 0), _FLEX),
	(34, {"spine": (-5, -8, 0), "chest": (-12, 0, 0), "head": (-8, 6, 0)}, (0, 0.015, 0), _FLEX_PUMP),
	(42, {"spine": (-4, 0, 0), "chest": (-8, 0, 0), "head": (-6, 0, 0)}, (0, 0, 0), _FLEX),
	(50, {"spine": (-5, 0, 0), "chest": (-12, 0, 0), "head": (-8, 0, 0)}, (0, 0.01, 0), _FLEX_PUMP),
	(66, {}, (0, 0, 0)),
]

_STRETCH = {s: ("dir", (0.75, 0.62, 0.02), (0.55, 0.82, 0.12), (0, 0, 1)) for s in ("r", "l")}
_SLUMP = {"spine": (8, 0, 0), "chest": (8, 0, 0), "head": (14, 0, 0)}
YAWN = [
	(0, {}, (0, 0, 0)),
	(14, {"spine": (-4, 0, 0), "chest": (-5, 0, 0), "head": (-14, 0, 0)}, (0, 0.005, 0),
	 {s: ("dir", (0.8, 0.45, 0.1), (0.5, 0.8, 0.1), (0, 0, 1)) for s in ("r", "l")}),
	(26, {"spine": (-8, 0, 0), "chest": (-10, 0, 0), "head": (-28, 0, 0)}, (0, 0.01, 0), _STRETCH),
	(38, {"spine": (-9, 0, 0), "chest": (-11, 0, 0), "head": (-30, 0, 0)}, (0, 0.01, 0), _STRETCH),
	(48, {"spine": (-2, 0, 0), "chest": (-2, 0, 0), "head": (-8, 0, 0)}, (0, 0, 0),
	 {s: ("dir", (0.95, -0.1, -0.1), (0.9, -0.3, 0)) for s in ("r", "l")}),
	(57, _SLUMP, (0, -0.01, 0), {s: ("dir", (0.32, -0.95, 0.25), (0.3, -0.9, 0.35)) for s in ("r", "l")}),
	(64, _with(_SLUMP, {"head": (16, 0, 0)}), (0, -0.01, 0), {s: ("dir", (0.32, -0.95, 0.25), (0.3, -0.9, 0.35)) for s in ("r", "l")}),
	(72, {}, (0, 0, 0)),
]

SIT_CHAIR = [
	(0, _with(_CHAIR_LEGS, {"spine": (8, 0, 0), "chest": (5, 0, 0), "head": (12, 0, 0)}), _CHAIR_HIPS, _FOLDED),
	(45, _with(_CHAIR_LEGS, {"spine": (8, 0, 0), "chest": (7.5, 0, 0), "head": (14, -4, 0)}), _CHAIR_HIPS, _FOLDED),
	(90, _with(_CHAIR_LEGS, {"spine": (8, 0, 0), "chest": (5, 0, 0), "head": (12, 0, 0)}), _CHAIR_HIPS, _FOLDED),
]

EMOTES = [("Emote_Wave", WAVE), ("Emote_Bow", BOW_EMOTE), ("Emote_Rude", RUDE), ("Emote_Cheer", CHEER),
		  ("Emote_Dance", DANCE), ("Emote_Laugh", LAUGH), ("Emote_Cry", CRY), ("Emote_Point", POINT),
		  ("Emote_Salute", SALUTE), ("Emote_Kneel", KNEEL), ("Emote_Shrug", SHRUG), ("Emote_Clap", CLAP),
		  ("Emote_Nod", NOD), ("Emote_Shake", SHAKE), ("Emote_Flex", FLEX), ("Emote_Yawn", YAWN)]


def build(arm, base):
	"""Every clip, as actions on the armature (the import's own clips are left
	for main to remove)."""
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
	keep.append(_keys(arm, base, "Sit_Chair_Idle", SIT_CHAIR, smooth=True))
	for name, keys in EMOTES:
		keep.append(_keys(arm, base, name, keys, smooth=True))
	return keep


def main():
	opts = _args()
	bpy.ops.wm.read_factory_settings(use_empty=True)
	bpy.ops.import_scene.gltf(filepath=SOURCE)
	arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
	base = _base_pose(arm)
	keep = build(arm, base)

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
