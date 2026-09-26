"""Renders an inventory icon for every item into assets/icons/<item>.png.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/icons.py -- --out assets/icons [--only cloth_cap,gnoll_fang] [--size 128]

Where the picture comes from, per item (data/items/*.json):
  "wear"   a small model built here if there is one (trousers: KayKit's leg
           parts are mostly boots on these short legs), else the KayKit parts
           it swaps onto the body (models.json "body_parts"), else the gear
           pieces from gear.py
  "model"  the weapon or shield scene named in data/models.json "weapons"
  else     a small model built here (drops, jewelry, bags), in the Dungeon
           palette like everything else
Icons are square, transparent, lit from the upper left and seen from a fixed
three-quarter angle, so a row of them reads as one set. Quality variants
(Fine, Superior...) share the base item's icon; the game tints the frame.
"""

import glob
import json
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import gear  # noqa: E402
import props  # noqa: E402
from props import (BONE, CLAY, CLOTH_RED, CLOTH_WHITE, EMBER, GOLD, HIDE, IRON, LEAF, PETAL_PURPLE, PINE, Prop, RUNE, STONE_DARK,  # noqa: E402
				   STONE_WARM, STONE_LIGHT, WATER, WOOD, WOOD_GRAY)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _res(path):
	return os.path.join(ROOT, path.replace("res://", ""))


# ---------------------------------------------------------------- small models

def gnoll_fang():
	p = Prop("gnoll_fang", 201)
	p.seg((0, 0, 0), (0.05, 0, 0.9), 0.16, 0.0, BONE, sides=7, grad=(0.0, 0.7))
	p.seg((0, 0, -0.05), (0, 0, 0.05), 0.17, 0.16, WOOD, sides=7)                 # root
	return p.build()


def beetle_eye():
	p = Prop("beetle_eye", 203)
	p.blob((0.7, 0.7, 0.7), (0, 0, 0.35), EMBER, segs=(14, 9), grad=(0.0, 0.6), glow=1.2)
	p.blob((0.3, 0.2, 0.3), (0, -0.28, 0.42), STONE_DARK, segs=(8, 6))            # pupil
	return p.build()


def bone_chips():
	p = Prop("bone_chips", 205)
	for k in range(5):
		a = k * 1.3
		p.rock((0.34, 0.26, 0.16), (math.cos(a) * 0.28, math.sin(a) * 0.28, 0.08 + k * 0.03), BONE, jitter=0.12)
	return p.build()


def rat_whiskers():
	p = Prop("rat_whiskers", 207)
	for k in range(6):
		a = math.radians(-35 + k * 14)
		p.seg((0, 0, 0.1), (math.cos(a) * 0.9, math.sin(a) * 0.3, 0.1 + math.sin(a) * 0.2), 0.02, 0.006, WOOD_GRAY, sides=4)
	p.blob((0.14, 0.14, 0.1), (0, 0, 0.1), HIDE, segs=(6, 4))
	return p.build()


def fishing_bait():
	p = Prop("fishing_bait", 209)
	p.seg((0, 0, 0), (0, 0, 0.55), 0.36, 0.36, IRON, sides=12, grad=(0.1, 0.6))
	p.seg((0, 0, 0.55), (0, 0, 0.58), 0.33, 0.33, STONE_DARK, sides=12)
	for k in range(3):                                                             # worms poking out
		a = k * 2.1
		p.seg((math.cos(a) * 0.15, math.sin(a) * 0.15, 0.55), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.85), 0.05, 0.04, CLOTH_RED, sides=5)
	return p.build()


def _cord(p, radius, z, swatch=WOOD_GRAY):
	for k in range(16):
		a0, a1 = k * math.tau / 16, (k + 1) * math.tau / 16
		p.seg((math.cos(a0) * radius, math.sin(a0) * radius * 0.6, z + math.sin(a0) * 0.2),
			  (math.cos(a1) * radius, math.sin(a1) * radius * 0.6, z + math.sin(a1) * 0.2), 0.025, 0.025, swatch, sides=4)


def bone_charm():
	p = Prop("bone_charm", 211)
	_cord(p, 0.5, 0.6)
	p.blob((0.3, 0.1, 0.4), (0, -0.3, 0.2), BONE, segs=(8, 6))
	p.blob((0.1, 0.06, 0.1), (0, -0.36, 0.24), RUNE, segs=(6, 4), glow=0.8)
	return p.build()


def fang_necklace():
	p = Prop("fang_necklace", 213)
	_cord(p, 0.55, 0.6)
	for k in range(5):
		a = math.radians(-70 + k * 35)
		x, y = math.sin(a) * 0.5, -math.cos(a) * 0.3
		p.seg((x, y, 0.45), (x * 1.05, y * 1.05, 0.12), 0.07, 0.0, BONE, sides=5)
	return p.build()


def _ring(p, swatch, stone=None):
	for k in range(14):
		a0, a1 = k * math.tau / 14, (k + 1) * math.tau / 14
		p.seg((math.cos(a0) * 0.4, 0, 0.4 + math.sin(a0) * 0.4), (math.cos(a1) * 0.4, 0, 0.4 + math.sin(a1) * 0.4),
			  0.09, 0.09, swatch, sides=6)
	if stone:
		p.blob((0.22, 0.18, 0.2), (0, 0, 0.86), stone, segs=(8, 6), glow=0.6)


def tarnished_ring():
	p = Prop("tarnished_ring", 215)
	_ring(p, WOOD_GRAY)
	return p.build()


def copper_band():
	p = Prop("copper_band", 217)
	_ring(p, EMBER, stone=LEAF)
	return p.build()


def bonecarved_talisman():
	p = Prop("bonecarved_talisman", 219)
	_cord(p, 0.5, 0.75, HIDE)
	p.seg((0, -0.25, 0.0), (0, -0.25, 0.6), 0.28, 0.24, BONE, sides=6, grad=(0.0, 0.6))
	p.blob((0.16, 0.06, 0.16), (0, -0.5, 0.32), RUNE, segs=(6, 4), glow=1.0)
	return p.build()


def _bag(p, swatch, w, d, h, strap=WOOD, flap=True):
	p.blob((w, d, h), (0, 0, h * 0.5), swatch, segs=(12, 8), grad=(0.1, 0.9))
	if flap:
		p.box((w * 0.8, 0.05, h * 0.35), (0, -d * 0.5, h * 0.72), swatch, rot=(-12, 0, 0), grad=(0.0, 0.6))
	p.seg((-w * 0.35, 0, h * 0.95), (w * 0.35, 0, h * 0.95), 0.04, 0.04, strap, sides=5)


def small_sack():
	p = Prop("small_sack", 221)
	p.blob((0.8, 0.7, 0.75), (0, 0, 0.38), CLOTH_WHITE, segs=(12, 8), grad=(0.1, 0.9))
	p.seg((0, 0, 0.72), (0, 0, 0.95), 0.1, 0.18, CLOTH_WHITE, sides=8)             # gathered neck
	p.seg((0, 0, 0.78), (0, 0, 0.82), 0.13, 0.13, HIDE, sides=8)                   # tie
	return p.build()


def worn_backpack():
	p = Prop("worn_backpack", 223)
	_bag(p, HIDE, 0.8, 0.5, 0.9, strap=WOOD_GRAY)
	return p.build()


def gnollhide_satchel():
	p = Prop("gnollhide_satchel", 225)
	_bag(p, WOOD, 0.9, 0.4, 0.6)
	for k in range(4):
		p.rock((0.18, 0.1, 0.12), (-0.3 + k * 0.2, -0.2, 0.62), HIDE, jitter=0.1)      # fur trim
	return p.build()


def leather_backpack():
	p = Prop("leather_backpack", 227)
	_bag(p, HIDE, 0.85, 0.55, 1.0)
	p.box((0.1, 0.06, 0.12), (0, -0.33, 0.62), GOLD)                              # buckle
	return p.build()


def braided_whisker_cord():
	p = Prop("braided_whisker_cord", 229)
	for ring in range(3):                                                          # a coil of cord, three turns
		for k in range(14):
			a0, a1 = k * math.tau / 14, (k + 1) * math.tau / 14
			r, z = 0.5 - ring * 0.04, 0.1 + ring * 0.09
			p.seg((math.cos(a0) * r, math.sin(a0) * r, z), (math.cos(a1) * r, math.sin(a1) * r, z), 0.06, 0.06, WOOD_GRAY, sides=5, twist=30)
	p.seg((0.5, 0, 0.3), (0.75, -0.2, 0.05), 0.05, 0.03, WOOD_GRAY, sides=5)       # loose end
	return p.build()


def blackpaw_pelt():
	p = Prop("blackpaw_pelt", 231)
	p.blob((1.1, 0.8, 0.12), (0, 0, 0.06), STONE_DARK, segs=(12, 6), grad=(0.0, 0.5), jitter=0.05)
	for x in (-1, 1):                                                              # legs of the hide
		p.blob((0.3, 0.22, 0.1), (x * 0.4, 0.32, 0.05), STONE_DARK, segs=(6, 4), grad=(0.0, 0.5))
		p.blob((0.3, 0.22, 0.1), (x * 0.4, -0.32, 0.05), STONE_DARK, segs=(6, 4), grad=(0.0, 0.5))
	p.blob((0.28, 0.22, 0.1), (0.52, 0, 0.1), WOOD, segs=(8, 5))                  # the paw
	return p.build()


def stitched_blackpaw_hide():
	p = Prop("stitched_blackpaw_hide", 233)
	p.box((0.9, 0.7, 0.14), (0, 0, 0.07), HIDE, grad=(0.1, 0.6))
	p.box((0.9, 0.7, 0.12), (0.03, 0.02, 0.2), STONE_DARK, rot=(0, 0, 4), grad=(0.0, 0.5))   # folded over
	for k in range(6):                                                             # stitches down the edge
		x = -0.38 + k * 0.15
		p.seg((x, -0.36, 0.3), (x + 0.06, -0.33, 0.1), 0.02, 0.02, WOOD_GRAY, sides=4)
	return p.build()


def tovins_trail_pack():
	p = Prop("tovins_trail_pack", 235)
	_bag(p, STONE_DARK, 0.85, 0.55, 1.0, strap=HIDE)
	p.blob((0.1, 0.06, 0.1), (0, -0.34, 0.62), EMBER, segs=(8, 6), glow=1.2)       # the beetle-eye clasp
	for x in (-0.3, 0.3):                                                          # side pouches
		p.blob((0.25, 0.3, 0.36), (x * 1.3, -0.02, 0.36), WOOD, segs=(8, 6))
	return p.build()


def crude_arrow():
	bpy.ops.import_scene.gltf(filepath=_res("res://assets/KayKit_Adventurers_2.0_FREE/Assets/gltf/arrow_bow_bundle.gltf"))


def sling_stone():
	p = Prop("sling_stone", 237)
	for k, (x, y) in enumerate([(0, 0), (0.42, 0.1), (-0.36, 0.18), (0.1, 0.4), (-0.05, -0.38)]):
		p.rock((0.32, 0.28, 0.24), (x, y, 0.12 + (0.14 if k == 0 else 0)), STONE_LIGHT, jitter=0.1)
	return p.build()


def leather_sling():
	p = Prop("leather_sling", 239)
	p.blob((0.6, 0.4, 0.2), (0, 0, 0.1), WOOD, segs=(10, 6), grad=(0.1, 0.7))      # the pouch
	p.rock((0.3, 0.26, 0.22), (0, 0, 0.24), STONE_LIGHT, jitter=0.05)
	for side in (-1, 1):                                                           # two cords, one ending in a loop
		pts = [(side * 0.3, 0, 0.12), (side * 0.6, 0.15, 0.1), (side * 0.85, 0.4, 0.08), (side * 0.95, 0.7, 0.06)]
		for a0, a1 in zip(pts, pts[1:]):
			p.seg(a0, a1, 0.05, 0.05, WOOD, sides=5)
	for k in range(8):
		a0, a1 = k * math.tau / 8, (k + 1) * math.tau / 8
		p.seg((0.95 + math.cos(a0) * 0.1, 0.8 + math.sin(a0) * 0.1, 0.06), (0.95 + math.cos(a1) * 0.1, 0.8 + math.sin(a1) * 0.1, 0.06), 0.045, 0.045, WOOD, sides=5)
	return p.build()


def _trousers(p, cloth, band, leg_r=0.2, flare=0.02):
	"""A pair of trousers laid out flat, facing the camera: waistband, seat, two legs."""
	p.box((0.72, 0.26, 0.14), (0, 0, 1.0), band, grad=(0.1, 0.6))                  # waistband
	p.box((0.66, 0.24, 0.3), (0, 0, 0.8), cloth, grad=(0.1, 0.7))                   # seat
	for x in (-1, 1):
		p.seg((x * 0.17, 0, 0.72), (x * 0.24, 0, 0.0), leg_r, leg_r + flare, cloth, sides=10, grad=(0.1, 0.8))


def patchwork_pants():
	p = Prop("patchwork_pants", 241)
	_trousers(p, WOOD, HIDE)
	for (x, z, sw) in [(-0.2, 0.45, CLOTH_WHITE), (0.24, 0.25, CLOTH_RED), (-0.12, 0.85, CLOTH_WHITE)]:  # the patches
		p.box((0.16, 0.05, 0.16), (x, -0.2, z), sw, rot=(0, 12, 0))
	return p.build()


def leather_leggings():
	p = Prop("leather_leggings", 243)
	_trousers(p, HIDE, WOOD)
	for x in (-1, 1):                                                              # knee pads and a strap each
		p.blob((0.2, 0.1, 0.16), (x * 0.2, -0.2, 0.38), WOOD, segs=(8, 5))
		p.seg((x * 0.35, 0, 0.18), (x * 0.1, 0, 0.18), 0.03, 0.03, WOOD, sides=5)
	p.box((0.1, 0.06, 0.08), (0, -0.15, 1.0), GOLD)                                 # buckle
	return p.build()


def iron_greaves():
	p = Prop("iron_greaves", 245)
	_trousers(p, STONE_LIGHT, HIDE, leg_r=0.21, flare=0.03)
	for x in (-1, 1):
		for z in (0.62, 0.42, 0.16):                                               # plate bands
			p.seg((x * 0.2, 0, z), (x * 0.21, 0, z - 0.05), 0.235, 0.24, IRON, sides=10)
		p.blob((0.22, 0.12, 0.2), (x * 0.21, -0.18, 0.38), STONE_LIGHT, segs=(8, 6))   # knee cop
	p.box((0.74, 0.28, 0.08), (0, 0, 1.05), HIDE)                                   # leather belt under the plate
	return p.build()


def wolf_pelt():
	p = Prop("wolf_pelt", 251)
	p.blob((1.1, 0.8, 0.12), (0, 0, 0.06), WOOD_GRAY, segs=(12, 6), grad=(0.0, 0.5), jitter=0.05)
	for x in (-1, 1):
		p.blob((0.3, 0.22, 0.1), (x * 0.4, 0.32, 0.05), WOOD_GRAY, segs=(6, 4), grad=(0.0, 0.5))
		p.blob((0.3, 0.22, 0.1), (x * 0.4, -0.32, 0.05), WOOD_GRAY, segs=(6, 4), grad=(0.0, 0.5))
	p.blob((0.34, 0.2, 0.12), (-0.55, 0, 0.1), STONE_LIGHT, segs=(8, 5))              # the head end
	p.seg((0.5, 0, 0.08), (0.9, 0.1, 0.06), 0.1, 0.04, WOOD_GRAY, sides=6)           # tail
	return p.build()


def dire_wolf_fang():
	p = Prop("dire_wolf_fang", 253)
	p.seg((0, 0, 0), (0.12, 0, 1.0), 0.2, 0.0, BONE, sides=7, grad=(0.0, 0.7))
	p.seg((0, 0, -0.05), (0, 0, 0.08), 0.21, 0.2, CLOTH_RED, sides=7)
	return p.build()


def bear_claw():
	p = Prop("bear_claw", 255)
	for k in range(3):
		x = -0.3 + k * 0.3
		p.seg((x, 0, 0.1), (x + 0.15, -0.1, 0.8), 0.1, 0.0, BONE, sides=6, grad=(0.0, 0.6))
	p.blob((1.0, 0.5, 0.35), (0, 0.1, 0.1), STONE_DARK, segs=(10, 6))
	return p.build()


def bear_hide():
	p = Prop("bear_hide", 257)
	p.box((0.95, 0.7, 0.16), (0, 0, 0.08), STONE_DARK, grad=(0.1, 0.7))
	p.box((0.9, 0.66, 0.14), (0.04, 0.03, 0.22), STONE_DARK, rot=(0, 0, 5), grad=(0.0, 0.6))
	p.seg((-0.5, -0.3, 0.3), (0.5, -0.3, 0.3), 0.04, 0.04, HIDE, sides=5)             # a tie
	return p.build()


def spider_silk():
	p = Prop("spider_silk", 259)
	p.blob((0.8, 0.7, 0.75), (0, 0, 0.38), CLOTH_WHITE, segs=(12, 8), grad=(0.0, 0.5))
	for k in range(5):                                                             # wound strands
		z = 0.12 + k * 0.13
		r = 0.42 - abs(k - 2) * 0.05
		for j in range(10):
			a0, a1 = j * math.tau / 10, (j + 1) * math.tau / 10
			p.seg((math.cos(a0) * r, math.sin(a0) * r * 0.9, z), (math.cos(a1) * r, math.sin(a1) * r * 0.9, z + 0.02), 0.02, 0.02, STONE_LIGHT, sides=3)
	return p.build()


def venom_sac():
	p = Prop("venom_sac", 261)
	p.blob((0.7, 0.62, 0.7), (0, 0, 0.35), LEAF, segs=(12, 8), grad=(0.0, 0.5), glow=0.8)
	p.seg((0, 0, 0.68), (0.1, -0.05, 0.95), 0.1, 0.05, CLOTH_RED, sides=6)
	return p.build()


def orc_tusk():
	p = Prop("orc_tusk", 263)
	pts = [(0, 0, 0), (0.1, 0, 0.35), (0.25, 0, 0.65), (0.48, 0, 0.85)]
	for i, (a0, a1) in enumerate(zip(pts, pts[1:])):
		p.seg(a0, a1, 0.2 - i * 0.06, 0.14 - i * 0.05, BONE, sides=7, grad=(0.0, 0.6))
	p.seg((0, 0, -0.08), (0, 0, 0.06), 0.21, 0.2, HIDE, sides=7)
	return p.build()


def hollow_watch_signet():
	p = Prop("hollow_watch_signet", 265)
	_ring(p, IRON, stone=WATER)
	return p.build()


# ---------------------------------------------------------------- Hollowmere

def mire_toad_skin():
	p = Prop("mire_toad_skin", 271)
	p.blob((1.1, 0.85, 0.12), (0, 0, 0.06), LEAF, segs=(12, 6), grad=(0.2, 0.8), jitter=0.05)
	for k in range(9):  # warts
		a = k * 2.4
		p.blob((0.12, 0.12, 0.08), (math.cos(a) * 0.35 * (k % 3 + 1) / 3, math.sin(a) * 0.28 * (k % 3 + 1) / 3, 0.13), WOOD, segs=(6, 4))
	for x in (-1, 1):
		p.seg((x * 0.45, 0.3, 0.05), (x * 0.75, 0.55, 0.03), 0.08, 0.05, LEAF, sides=5)
		p.seg((x * 0.45, -0.3, 0.05), (x * 0.7, -0.5, 0.03), 0.08, 0.05, LEAF, sides=5)
	return p.build()


def leech_teeth():
	p = Prop("leech_teeth", 273)
	for k in range(10):  # a ring of little hooked teeth, still in their pink rim
		a0, a1 = k * math.tau / 10, (k + 1) * math.tau / 10
		p.seg((math.cos(a0) * 0.42, math.sin(a0) * 0.42, 0.1), (math.cos(a1) * 0.42, math.sin(a1) * 0.42, 0.1), 0.1, 0.1, CLOTH_RED, sides=6)
		p.seg((math.cos(a0) * 0.36, math.sin(a0) * 0.36, 0.16), (math.cos(a0) * 0.2, math.sin(a0) * 0.2, 0.42), 0.06, 0.0, BONE, sides=4)
	return p.build()


def turtle_shell_plate():
	p = Prop("turtle_shell_plate", 275)
	p.poly([(0, 0.55, 0.1), (0.5, 0.25, 0.14), (0.45, -0.35, 0.1), (-0.05, -0.55, 0.08), (-0.5, -0.2, 0.12), (-0.4, 0.35, 0.1)],
		   [(0, 1, 2, 3, 4, 5)], WOOD_GRAY, grad=(0.2, 0.9))
	p.blob((0.9, 0.95, 0.3), (0, 0, 0.1), STONE_DARK, segs=(6, 4), grad=(0.1, 0.8))
	p.blob((0.3, 0.3, 0.12), (0.05, 0.02, 0.24), LEAF, segs=(6, 4))  # moss
	return p.build()


def mirescale_scale():
	p = Prop("mirescale_scale", 277)
	p.poly([(0, 0.6, 0.02), (0.38, 0.1, 0.1), (0.25, -0.45, 0.06), (0, -0.6, 0.02), (-0.25, -0.45, 0.06), (-0.38, 0.1, 0.1)],
		   [(0, 1, 2, 3, 4, 5)], LEAF, grad=(0.0, 0.7))
	p.seg((0, 0.55, 0.1), (0, -0.55, 0.1), 0.05, 0.03, WOOD, sides=4)  # the ridge
	return p.build()


def waterlogged_locket():
	p = Prop("waterlogged_locket", 279)
	_cord(p, 0.5, 0.75, WOOD_GRAY)
	p.blob((0.46, 0.14, 0.52), (0, -0.3, 0.3), IRON, segs=(10, 6), grad=(0.1, 0.9))
	p.blob((0.16, 0.08, 0.16), (0.08, -0.38, 0.38), LEAF, segs=(6, 4))  # weed stuck to it
	p.seg((0.0, -0.38, 0.55), (-0.2, -0.36, 0.1), 0.03, 0.02, LEAF, sides=3)
	return p.build()


def snapjaws_shell():
	p = Prop("snapjaws_shell", 281)
	p.blob((1.3, 1.1, 0.55), (0, 0, 0.25), STONE_DARK, segs=(10, 6), grad=(0.1, 0.9))
	for k in range(5):  # ridge spikes
		p.seg((0, -0.4 + k * 0.2, 0.5), (0, -0.4 + k * 0.2, 0.78), 0.08, 0.0, WOOD_GRAY, sides=4)
	for x in (-0.35, 0.35):
		for k in range(3):
			p.seg((x, -0.3 + k * 0.3, 0.42), (x * 1.1, -0.3 + k * 0.3, 0.6), 0.06, 0.0, WOOD_GRAY, sides=4)
	p.blob((0.35, 0.3, 0.12), (-0.25, 0.1, 0.52), LEAF, segs=(6, 4))
	return p.build()


def drowned_bell():
	p = Prop("drowned_bell", 283)
	p.seg((0, 0, 0.0), (0, 0, 0.75), 0.42, 0.22, IRON, sides=12, grad=(0.1, 0.9))
	p.seg((0, 0, -0.04), (0, 0, 0.04), 0.46, 0.44, IRON, sides=12)
	p.blob((0.2, 0.2, 0.18), (0, 0, 0.82), IRON, segs=(8, 5))
	for k in range(6):  # weed and verdigris
		a = k * 1.1
		p.blob((0.14, 0.08, 0.2), (math.cos(a) * 0.36, math.sin(a) * 0.36, 0.3 + (k % 3) * 0.12), LEAF, segs=(5, 4))
	p.seg((0, 0, 0.9), (0, 0, 1.1), 0.05, 0.05, WOOD_GRAY, sides=5)  # a scrap of rope
	return p.build()


def smoked_mereperch():
	p = Prop("smoked_mereperch", 285)
	p.blob((1.0, 0.35, 0.28), (0, 0, 0.14), WOOD, segs=(10, 6), grad=(0.1, 0.8))
	p.poly([(0.45, 0, 0.14), (0.8, 0.2, 0.2), (0.8, -0.2, 0.2)], [(0, 1, 2)], WOOD)  # tail
	p.blob((0.08, 0.08, 0.08), (-0.38, -0.1, 0.2), STONE_DARK, segs=(5, 4))  # eye
	p.seg((-0.2, 0, 0.3), (0.3, 0, 0.3), 0.02, 0.02, HIDE, sides=3)  # the smoking string
	return p.build()


def pearl_of_the_mere():
	p = Prop("pearl_of_the_mere", 287)
	_cord(p, 0.5, 0.75, WOOD_GRAY)
	p.blob((0.4, 0.38, 0.4), (0, -0.3, 0.28), CLOTH_WHITE, segs=(12, 8), grad=(0.0, 0.4), glow=0.4)
	p.seg((0, -0.3, 0.5), (0, -0.3, 0.62), 0.07, 0.07, GOLD, sides=6)
	return p.build()


def scaled_leggings():
	p = Prop("scaled_leggings", 289)
	_trousers(p, LEAF, WOOD)
	for x in (-1, 1):
		for z in (0.6, 0.42, 0.24):
			p.seg((x * 0.2, 0, z), (x * 0.21, 0, z - 0.06), 0.225, 0.23, LEAF, sides=8, grad=(0.0, 0.6))
	return p.build()


# ---------------------------------------------------------------- Harrowfield

def boar_tusk():
	p = Prop("boar_tusk", 291)
	pts = [(0, 0, 0), (0.12, 0, 0.3), (0.3, 0, 0.55), (0.55, 0, 0.66)]
	for i, (a0, a1) in enumerate(zip(pts, pts[1:])):
		p.seg(a0, a1, 0.14 - i * 0.04, 0.1 - i * 0.035, BONE, sides=7, grad=(0.0, 0.6))
	return p.build()


def boar_hide():
	p = Prop("boar_hide", 293)
	p.blob((1.1, 0.8, 0.12), (0, 0, 0.06), WOOD_GRAY, segs=(12, 6), grad=(0.1, 0.7), jitter=0.05)
	for k in range(7):  # the bristle ridge down the back
		p.seg((-0.4 + k * 0.13, 0, 0.1), (-0.4 + k * 0.13, 0, 0.3), 0.04, 0.0, STONE_DARK, sides=3)
	return p.build()


def brigand_armband():
	p = Prop("brigand_armband", 295)
	for k in range(12):
		a0, a1 = k * math.tau / 12, (k + 1) * math.tau / 12
		p.seg((math.cos(a0) * 0.4, math.sin(a0) * 0.4, 0.2), (math.cos(a1) * 0.4, math.sin(a1) * 0.4, 0.2), 0.14, 0.14, CLOTH_RED, sides=6)
	p.box((0.2, 0.3, 0.06), (0.42, 0, 0.12), CLOTH_RED, rot=(0, 30, 0))  # the knot's tails
	return p.build()


def garricks_ledger():
	p = Prop("garricks_ledger", 297)
	p.box((0.8, 1.0, 0.18), (0, 0, 0.09), HIDE, grad=(0.2, 0.9))
	p.box((0.74, 0.94, 0.12), (0.03, 0, 0.12), CLOTH_WHITE, grad=(0.3, 0.6))
	p.box((0.8, 0.08, 0.2), (0, 0.3, 0.1), CLOTH_RED)  # a strap
	return p.build()


def straw_heart():
	p = Prop("straw_heart", 299)
	for s_ in (-1, 1):
		p.blob((0.45, 0.35, 0.45), (s_ * 0.18, 0, 0.55), GOLD, segs=(8, 6), jitter=0.03)
	p.seg((0, 0, 0.1), (0, 0, 0.6), 0.35, 0.05, GOLD, sides=8)
	for k in range(4):  # red thread wound round it
		p.seg((-0.4, 0, 0.3 + k * 0.1), (0.4, 0, 0.35 + k * 0.1), 0.02, 0.02, CLOTH_RED, sides=3)
	return p.build()


def loaf_of_bread():
	p = Prop("loaf_of_bread", 301)
	p.blob((1.0, 0.55, 0.45), (0, 0, 0.22), WOOD, segs=(10, 6), grad=(0.0, 0.7))
	for k in range(3):
		p.box((0.06, 0.4, 0.04), (-0.25 + k * 0.25, 0, 0.44), CLOTH_WHITE, rot=(0, 0, 20))
	return p.build()


def harvest_band():
	p = Prop("harvest_band", 303)
	_ring(p, GOLD, stone=LEAF)
	return p.build()


# ---------------------------------------------------------------- Sunward Steps

def ram_horn():
	p = Prop("ram_horn", 305)
	pts = []
	for k in range(9):  # a curling spiral
		a = k * 0.8
		r = 0.5 - k * 0.04
		pts.append((math.cos(a) * r, 0, 0.55 + math.sin(a) * r))
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.17 - i * 0.015, 0.155 - i * 0.015, BONE, sides=7, grad=(0.1, 0.7))
	return p.build()


def ram_fleece():
	p = Prop("ram_fleece", 307)
	for k in range(9):
		p.blob((0.4, 0.35, 0.22), (math.cos(k * 2.1) * 0.35 * (k % 3) / 2.0, math.sin(k * 2.1) * 0.3 * (k % 3) / 2.0, 0.12), CLOTH_WHITE, segs=(8, 5), grad=(0.1, 0.6))
	return p.build()


def sunhawk_feather():
	p = Prop("sunhawk_feather", 309)
	p.seg((0, 0, 0), (0.1, 0, 1.1), 0.03, 0.01, WOOD, sides=4)
	p.poly([(0.02, 0, 0.25), (0.35, 0, 0.55), (0.28, 0, 1.0), (0.1, 0, 1.12), (-0.18, 0, 0.8), (-0.12, 0, 0.35)], [(0, 1, 2, 3, 4, 5)], GOLD, grad=(0.0, 0.8))
	p.box((0.3, 0.02, 0.15), (0.12, 0, 1.0), EMBER)
	return p.build()


def sunstone_shard():
	p = Prop("sunstone_shard", 311)
	p.seg((0, 0, 0), (0.1, 0, 0.9), 0.3, 0.0, GOLD, sides=5, glow=1.4)
	p.seg((0.25, 0.1, 0), (0.35, 0.1, 0.5), 0.18, 0.0, GOLD, sides=5, glow=1.2)
	return p.build()


def linen_wrappings():
	p = Prop("linen_wrappings", 313)
	for k in range(4):
		p.seg((-0.4, 0, 0.1 + k * 0.14), (0.4, 0, 0.14 + k * 0.14), 0.12, 0.12, CLOTH_WHITE, sides=8, grad=(0.2, 0.7))
	p.box((0.12, 0.3, 0.7), (0.45, 0, 0.2), CLOTH_WHITE, rot=(0, 20, 0))  # a loose end
	return p.build()


def pilgrim_token():
	p = Prop("pilgrim_token", 315)
	p.seg((0, -0.05, 0.45), (0, 0.05, 0.45), 0.42, 0.42, STONE_WARM, sides=14)
	p.seg((0, -0.08, 0.45), (0, -0.1, 0.45), 0.2, 0.2, GOLD, sides=12, glow=0.4)
	p.seg((0, 0, 0.9), (0, 0, 1.1), 0.04, 0.04, WOOD_GRAY, sides=4)
	return p.build()


def cult_sigil():
	p = Prop("cult_sigil", 317)
	p.seg((0, -0.04, 0.5), (0, 0.04, 0.5), 0.3, 0.3, CLOTH_RED, sides=12)
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.3, 0, 0.5 + math.sin(a) * 0.3), (math.cos(a) * 0.55, 0, 0.5 + math.sin(a) * 0.55), 0.07, 0.0, EMBER, sides=3)
	return p.build()


def sun_scarab():
	p = Prop("sun_scarab", 319)
	p.blob((0.7, 0.9, 0.35), (0, 0, 0.18), GOLD, segs=(10, 6), glow=0.6)
	p.blob((0.4, 0.3, 0.25), (0, -0.5, 0.18), GOLD, segs=(8, 5), glow=0.4)
	p.box((0.03, 0.8, 0.02), (0, 0.05, 0.36), STONE_DARK)
	for s_ in (-1, 1):
		for k in range(3):
			p.seg((s_ * 0.3, -0.2 + k * 0.25, 0.1), (s_ * 0.55, -0.25 + k * 0.3, 0.0), 0.04, 0.03, GOLD, sides=4)
	return p.build()


def hierophants_mask():
	p = Prop("hierophants_mask", 321)
	p.blob((0.7, 0.2, 0.85), (0, 0, 0.55), GOLD, segs=(10, 8), glow=0.5)
	for s_ in (-1, 1):
		p.blob((0.14, 0.1, 0.1), (s_ * 0.16, -0.1, 0.62), STONE_DARK, segs=(6, 4))
	for k in range(12):
		a = k * math.tau / 12
		p.seg((math.cos(a) * 0.42, 0.02, 0.55 + math.sin(a) * 0.48), (math.cos(a) * 0.72, 0.02, 0.55 + math.sin(a) * 0.8), 0.06, 0.0, EMBER, sides=3)
	return p.build()


def dawn_tusk_pendant():
	p = Prop("dawn_tusk_pendant", 323)
	_cord(p, 0.5, 0.75, GOLD)
	p.seg((0, -0.3, 0.55), (0.15, -0.34, 0.1), 0.1, 0.02, BONE, sides=6)  # a tusk
	p.seg((0, -0.32, 0.62), (0, -0.36, 0.62), 0.16, 0.16, GOLD, sides=12, glow=0.6)  # and a small sun
	return p.build()


# ---------------------------------------------------------------- The Bleach

def _stinger(p, swatch, scale=1.0, glow=0.0):
	pts = [(0, 0, 0.1), (0.25, 0, 0.35), (0.35, 0, 0.7), (0.2, 0, 1.0), (-0.05, 0, 1.08)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		a = tuple(c * scale for c in a)
		b = tuple(c * scale for c in b)
		p.seg(a, b, (0.16 - i * 0.03) * scale, (0.13 - i * 0.03) * scale, swatch, sides=7, grad=(0.1, 0.7), glow=glow)
	tip = tuple(c * scale for c in (-0.05, 0, 1.08))
	p.seg(tip, (-0.3 * scale, 0, 0.85 * scale), 0.05 * scale, 0.0, BONE, sides=5)


def chitin_plate():
	p = Prop("chitin_plate", 325)
	p.blob((0.9, 0.7, 0.18), (0, 0, 0.1), STONE_WARM, segs=(10, 6), grad=(0.1, 0.7))
	for k in range(3):  # ridges across the plate
		p.seg((-0.4, -0.3 + k * 0.3, 0.2), (0.4, -0.3 + k * 0.3, 0.2), 0.04, 0.04, CLAY, sides=5)
	return p.build()


def scorpion_stinger():
	p = Prop("scorpion_stinger", 327)
	_stinger(p, CLAY)
	return p.build()


def queens_stinger():
	p = Prop("queens_stinger", 329)
	_stinger(p, CLOTH_RED, scale=1.25, glow=0.4)
	return p.build()


def bleached_bone():
	p = Prop("bleached_bone", 331)
	p.seg((-0.55, 0, 0.3), (0.55, 0, 0.5), 0.1, 0.1, BONE, sides=8)
	for x, z in ((-0.6, 0.3), (0.6, 0.5)):
		for s_ in (-1, 1):
			p.blob((0.16, 0.16, 0.16), (x, s_ * 0.08, z + 0.08), BONE, segs=(7, 5))
	return p.build()


def salt_crystal():
	p = Prop("salt_crystal", 333)
	for (x, y, h, r) in ((0, 0, 0.9, 0.2), (0.22, 0.1, 0.55, 0.14), (-0.2, 0.05, 0.6, 0.15), (0.05, -0.2, 0.45, 0.12)):
		p.seg((x, y, 0), (x * 1.3, y * 1.3, h), r, 0.0, CLOTH_WHITE, sides=6, glow=0.2)
	return p.build()


def raider_scarf():
	p = Prop("raider_scarf", 335)
	for k in range(5):
		p.seg((-0.5, 0, 0.12 + k * 0.1), (0.5, 0, 0.16 + k * 0.1), 0.09, 0.09, STONE_WARM, sides=8, grad=(0.2, 0.7))
	p.box((0.18, 0.04, 0.6), (0.55, 0, 0.1), STONE_WARM, rot=(0, 25, 0))  # a trailing end
	p.box((0.18, 0.05, 0.05), (0.55, 0, -0.18), CLOTH_RED, rot=(0, 25, 0))
	return p.build()


def raider_warhorn():
	p = Prop("raider_warhorn", 337)
	pts = [(-0.6, 0, 0.3), (-0.2, 0, 0.2), (0.2, 0, 0.3), (0.5, 0, 0.6)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.06 + i * 0.07, 0.12 + i * 0.08, BONE, sides=10, grad=(0.1, 0.7))
	for a, b, r in (((-0.24, 0, 0.21), (-0.16, 0, 0.2), 0.16), ((0.3, 0, 0.36), (0.36, 0, 0.44), 0.24)):  # gold bands round the horn
		p.seg(a, b, r, r, GOLD, sides=10)
	return p.build()


def titans_heart():
	p = Prop("titans_heart", 339)
	p.blob((0.55, 0.5, 0.6), (0, 0, 0.5), BONE, segs=(10, 8), jitter=0.05, grad=(0.1, 0.7))
	p.blob((0.3, 0.28, 0.32), (0, -0.25, 0.5), CLOTH_RED, segs=(8, 6), glow=1.2)
	for s_ in (-1, 1):  # stumps of great vessels
		p.seg((s_ * 0.2, 0, 0.9), (s_ * 0.3, 0, 1.15), 0.12, 0.1, BONE, sides=7)
	return p.build()


def bone_talisman():
	p = Prop("bone_talisman", 341)
	_cord(p, 0.5, 0.75, HIDE)
	p.box((0.3, 0.08, 0.45), (0, -0.32, 0.3), BONE)
	p.seg((0, -0.38, 0.35), (0, -0.4, 0.35), 0.08, 0.08, CLOTH_WHITE, sides=6, glow=0.5)
	return p.build()



# ---------------------------------------------------------------- the Long Monsoon

def _fish(p, body, fin, length=1.0, fat=0.3, spots=None):
	p.blob((length, fat * 0.8, fat * 1.6), (0, 0, 0.35), body, segs=(12, 6), grad=(0.1, 0.8))
	p.poly([(length * 0.45, 0, 0.35), (length * 0.75, 0, 0.62), (length * 0.75, 0, 0.08)], [(0, 1, 2)], fin)       # tail
	p.poly([(-0.15, 0, 0.35 + fat * 0.7), (0.2, 0, 0.35 + fat * 0.7), (0.05, 0, 0.35 + fat * 1.3)], [(0, 1, 2)], fin)  # dorsal fin
	p.blob((0.09, 0.05, 0.09), (-length * 0.36, -fat * 0.3, 0.42), STONE_DARK, segs=(6, 4))                          # eye
	for (x, z) in spots or []:
		p.blob((0.1, 0.04, 0.1), (x, -fat * 0.36, z), fin, segs=(6, 4))


def river_trout():
	p = Prop("river_trout", 343)
	_fish(p, STONE_LIGHT, CLOTH_RED, spots=[(0.0, 0.42), (0.15, 0.3), (-0.12, 0.3)])
	return p.build()


def mud_carp():
	p = Prop("mud_carp", 345)
	_fish(p, WOOD, HIDE, length=0.9, fat=0.38)
	return p.build()


def lagoon_snapper():
	p = Prop("lagoon_snapper", 347)
	_fish(p, CLOTH_RED, EMBER, length=0.95, fat=0.36)
	return p.build()


def monsoon_eel():
	p = Prop("monsoon_eel", 349)
	pts = [(-0.6, 0, 0.3), (-0.3, 0, 0.45), (0.0, 0, 0.3), (0.3, 0, 0.15), (0.6, 0, 0.3)]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.11 - i * 0.015, 0.1 - i * 0.02, WATER, sides=7, grad=(0.1, 0.8))
	p.blob((0.04, 0.03, 0.04), (-0.62, -0.08, 0.34), STONE_DARK, segs=(6, 4))
	return p.build()


def jungle_catfish():
	p = Prop("jungle_catfish", 351)
	_fish(p, STONE_DARK, HIDE, length=1.05, fat=0.34)
	for s_ in (-1, 1):  # whiskers
		p.seg((-0.5, s_ * 0.08, 0.32), (-0.75, s_ * 0.2, 0.2), 0.015, 0.01, HIDE, sides=3)
	return p.build()


def rainbow_koi():
	p = Prop("rainbow_koi", 353)
	_fish(p, GOLD, CLOTH_RED, length=0.95, fat=0.32, spots=[(0.0, 0.45), (0.2, 0.32), (-0.15, 0.28)])
	p.blob((0.12, 0.02, 0.1), (0.1, -0.15, 0.4), WATER, segs=(6, 4), glow=0.8)
	return p.build()


def tattered_boot():
	p = Prop("tattered_boot", 355)
	p.seg((0, 0, 0.1), (0, 0, 0.75), 0.2, 0.22, HIDE, sides=8, grad=(0.1, 0.6))
	p.blob((0.4, 0.22, 0.14), (-0.22, 0, 0.1), HIDE, segs=(8, 5))
	p.blob((0.12, 0.05, 0.1), (-0.5, -0.05, 0.14), LEAF, segs=(6, 4))  # weed hanging off it
	return p.build()


def troll_tusk():
	p = Prop("troll_tusk", 357)
	p.seg((0, 0, 0.05), (0.2, 0, 0.6), 0.16, 0.08, BONE, sides=7, grad=(0.1, 0.7))
	p.seg((0.2, 0, 0.6), (0.1, 0, 0.95), 0.08, 0.0, BONE, sides=6)
	p.seg((0, 0, 0.02), (0, 0, 0.12), 0.18, 0.18, LEAF, sides=8)  # a mossy root
	return p.build()


def frog_skin():
	p = Prop("frog_skin", 359)
	p.blob((0.7, 0.55, 0.08), (0, 0, 0.1), GOLD, segs=(10, 6))
	for (x, y) in ((-0.3, 0.1), (0.15, -0.2), (0.25, 0.2), (-0.05, 0.0)):
		p.blob((0.1, 0.1, 0.03), (x, y, 0.17), STONE_DARK, segs=(6, 4))
	return p.build()


def croc_hide():
	p = Prop("croc_hide", 361)
	p.blob((0.8, 0.5, 0.1), (0, 0, 0.1), LEAF, segs=(10, 6), grad=(0.1, 0.5))
	for k in range(5):  # scutes
		p.box((0.12, 0.35, 0.08), (-0.4 + k * 0.2, 0, 0.2), STONE_DARK)
	return p.build()


def croc_tooth():
	p = Prop("croc_tooth", 363)
	p.seg((0, 0, 0.0), (0.05, 0, 0.9), 0.16, 0.0, BONE, sides=6, grad=(0.1, 0.7))
	return p.build()


def elemental_essence():
	p = Prop("elemental_essence", 365)
	p.blob((0.4, 0.4, 0.5), (0, 0, 0.45), WATER, segs=(10, 8), glow=1.4)
	p.seg((0, 0, 0.85), (0, 0, 1.1), 0.12, 0.12, STONE_LIGHT, sides=8)  # a stoppered vial of rain
	return p.build()


def gorraks_crown():
	p = Prop("gorraks_crown", 367)
	for k in range(8):  # a ring of river stones
		a = k * math.tau / 8
		p.blob((0.16, 0.16, 0.14), (math.cos(a) * 0.45, math.sin(a) * 0.45, 0.2), STONE_LIGHT if k % 2 else STONE_DARK, segs=(6, 4))
	for s_ in (-1, 1):  # antlers
		p.seg((s_ * 0.4, 0, 0.3), (s_ * 0.6, 0, 0.9), 0.05, 0.03, BONE, sides=5)
		p.seg((s_ * 0.52, 0, 0.65), (s_ * 0.3, 0, 0.95), 0.03, 0.02, BONE, sides=4)
	p.blob((0.18, 0.14, 0.16), (0, -0.46, 0.34), BONE, segs=(6, 5))  # a small skull at the front
	return p.build()


def heart_of_the_storm():
	p = Prop("heart_of_the_storm", 369)
	p.blob((0.45, 0.45, 0.5), (0, 0, 0.5), STONE_DARK, segs=(10, 8), jitter=0.05)
	for pts in (((-0.3, -0.3, 0.9), (-0.05, -0.35, 0.6), (-0.2, -0.38, 0.45)), ((0.3, -0.3, 0.3), (0.1, -0.36, 0.5), (0.25, -0.4, 0.7))):
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.04, 0.03, GOLD, sides=4, glow=2.2)
	return p.build()


def graveljaws_tooth():
	p = Prop("graveljaws_tooth", 371)
	p.seg((0, 0, 0.0), (0.12, 0, 1.1), 0.26, 0.0, BONE, sides=7, grad=(0.05, 0.6))
	p.blob((0.12, 0.05, 0.1), (0.02, -0.18, 0.35), LEAF, segs=(6, 4))  # moss
	return p.build()


def tide_trunk_charm():
	p = Prop("tide_trunk_charm", 373)
	_cord(p, 0.5, 0.75, WATER)
	p.blob((0.3, 0.12, 0.28), (0, -0.32, 0.4), STONE_LIGHT, segs=(8, 6))            # a little stone elephant head
	p.seg((0, -0.4, 0.35), (0.05, -0.45, 0.62), 0.05, 0.03, STONE_LIGHT, sides=5)    # trunk raised
	p.blob((0.08, 0.08, 0.08), (0.06, -0.46, 0.7), WATER, segs=(6, 4), glow=1.6)     # a drop of water
	return p.build()


# ---------------------------------------------------------------- tradeskills

AMBER = (1, 3)       # baked crust, fried food
ORANGE = (4, 2)      # spice, broth
PINK = (2, 2)        # raw meat
MOSS = PINE
LAVENDER = PETAL_PURPLE


def _frame(p, lo, hi):
	"""Two specks at opposite corners, too small to see, so a set of icons
	(small and large ore, the three healing potions) share one framing and
	their sizes compare."""
	p.blob((0.001, 0.001, 0.001), lo, STONE_DARK, segs=(3, 3))
	p.blob((0.001, 0.001, 0.001), hi, STONE_DARK, segs=(3, 3))


def _loop(p, center, radius, z_axis, r, swatch, n=14, squash=1.0, glow=0.0):
	"""A ring of segments round `center`, in the xy plane (z_axis) or the xz plane."""
	cx, cy, cz = center
	for k in range(n):
		a0, a1 = k * math.tau / n, (k + 1) * math.tau / n
		if z_axis:
			a = (cx + math.cos(a0) * radius, cy + math.sin(a0) * radius * squash, cz)
			b = (cx + math.cos(a1) * radius, cy + math.sin(a1) * radius * squash, cz)
		else:
			a = (cx + math.cos(a0) * radius, cy, cz + math.sin(a0) * radius * squash)
			b = (cx + math.cos(a1) * radius, cy, cz + math.sin(a1) * radius * squash)
		p.seg(a, b, r, r, swatch, sides=5, glow=glow)


# supplies

def bag_of_flour():
	p = Prop("bag_of_flour", 401)
	p.blob((0.95, 0.8, 0.8), (0, 0, 0.4), CLOTH_WHITE, segs=(12, 8), grad=(0.15, 0.95))
	_loop(p, (0, 0, 0.74), 0.36, True, 0.07, STONE_WARM, n=14, squash=0.85)       # rolled-down rim
	p.blob((0.62, 0.52, 0.26), (0, 0, 0.78), CLOTH_WHITE, segs=(10, 6), grad=(0.0, 0.3), glow=0.25)  # the flour heap
	for k in range(4):                                                             # a wheat sprig stamped on the front
		z = 0.22 + k * 0.1
		p.blob((0.08, 0.03, 0.12), (-0.05, -0.4, z), GOLD, rot=(0, 30, 0), segs=(6, 4))
		p.blob((0.08, 0.03, 0.12), (0.05, -0.4, z), GOLD, rot=(0, -30, 0), segs=(6, 4))
	p.box((0.025, 0.02, 0.5), (0, -0.39, 0.3), GOLD)
	return p.build()


def jar_of_spices():
	p = Prop("jar_of_spices", 403)
	p.seg((0, 0, 0), (0, 0, 0.55), 0.3, 0.38, CLAY, sides=12, grad=(0.1, 0.8))
	p.seg((0, 0, 0.55), (0, 0, 0.7), 0.38, 0.26, CLAY, sides=12)
	p.blob((0.62, 0.62, 0.22), (0, 0, 0.74), CLOTH_RED, segs=(12, 6), grad=(0.0, 0.6))  # cloth over the lid
	p.seg((0, 0, 0.66), (0, 0, 0.7), 0.29, 0.29, GOLD, sides=12)                   # its tie
	for k in range(5):                                                             # a pinch spilled in front
		a = k * 1.25
		p.rock((0.2, 0.18, 0.12), (0.45 + math.cos(a) * 0.12, -0.35 + math.sin(a) * 0.1, 0.05), ORANGE, jitter=0.1)
	p.seg((0.25, -0.55, 0.04), (0.75, -0.2, 0.04), 0.05, 0.05, WOOD, sides=6)       # a cinnamon stick
	return p.build()


def vial_of_water():
	p = Prop("vial_of_water", 405)
	p.seg((0, 0, 0.12), (0, 0, 1.0), 0.16, 0.16, RUNE, sides=10, grad=(0.0, 0.5), glow=0.35)  # a thin tube of water
	p.blob((0.32, 0.32, 0.26), (0, 0, 0.13), RUNE, segs=(10, 6), grad=(0.3, 0.6), glow=0.35)
	p.seg((0, 0, 0.95), (0, 0, 1.02), 0.2, 0.2, CLOTH_WHITE, sides=10)              # the lip
	p.seg((0, 0, 1.0), (0, 0, 1.16), 0.13, 0.15, WOOD, sides=8)                     # cork
	p.box((0.05, 0.02, 0.5), (-0.07, -0.16, 0.55), CLOTH_WHITE, glow=0.6)           # the glint on the glass
	return p.build()


def tanning_salts():
	p = Prop("tanning_salts", 407)
	p.seg((0, 0, 0), (0, 0, 0.42), 0.48, 0.55, WOOD, sides=14, grad=(0.1, 0.8))    # a little tub
	for z in (0.08, 0.34):
		p.seg((0, 0, z), (0, 0, z + 0.05), 0.5 + z * 0.16 + 0.01, 0.5 + z * 0.16 + 0.02, STONE_DARK, sides=14)
	for k in range(9):                                                             # heaped with coarse white salt
		a = k * 2.4
		r = 0.1 + (k % 3) * 0.14
		p.rock((0.28, 0.26, 0.22), (math.cos(a) * r, math.sin(a) * r, 0.48 + (0.12 if k < 3 else 0.0)), CLOTH_WHITE,
			   grad=(0.0, 0.5), jitter=0.12)
	return p.build()


def spool_of_thread():
	p = Prop("spool_of_thread", 409)
	p.seg((0, 0, 0), (0, 0, 0.1), 0.42, 0.42, WOOD, sides=14)                       # flanges
	p.seg((0, 0, 0.8), (0, 0, 0.9), 0.42, 0.42, WOOD, sides=14)
	p.seg((0, 0, 0.1), (0, 0, 0.8), 0.33, 0.33, CLOTH_RED, sides=14, grad=(0.0, 0.6))  # the thread
	for k in range(6):                                                             # wound turns
		z = 0.16 + k * 0.11
		p.seg((0, 0, z), (0, 0, z + 0.02), 0.345, 0.345, CLOTH_RED, sides=14, grad=(0.9, 1.0))
	pts = [(0.3, -0.18, 0.55), (0.55, -0.35, 0.35), (0.6, -0.5, 0.1), (0.45, -0.65, 0.02)]  # a loose end
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.025, 0.025, CLOTH_RED, sides=4)
	p.seg((-0.2, -0.28, 0.25), (-0.05, -0.3, 0.95), 0.025, 0.008, STONE_LIGHT, sides=4, glow=0.4)  # a needle stuck in
	return p.build()


def bundle_of_herbs():
	p = Prop("bundle_of_herbs", 411)
	tops = [(-0.45, 0.0, 0.95), (-0.2, 0.05, 1.1), (0.05, 0.0, 1.15), (0.3, 0.05, 1.05), (0.5, 0.0, 0.85), (-0.1, -0.1, 0.95), (0.2, -0.1, 0.9)]
	for k, t in enumerate(tops):
		p.seg((t[0] * 0.08, 0, 0), t, 0.03, 0.02, LEAF, sides=4)
		for j in range(3):                                                         # leaves up the stem
			f = 0.55 + j * 0.2
			x, y, z = t[0] * f, t[1] * f, t[2] * f
			sw = MOSS if (k + j) % 2 else LEAF
			p.blob((0.2, 0.06, 0.12), (x + (0.08 if j % 2 else -0.08), y - 0.05, z), sw, rot=(0, 35 if j % 2 else -35, 0), segs=(6, 4))
		if k in (1, 3, 5):                                                         # a few in flower
			p.blob((0.1, 0.1, 0.16), (t[0], t[1], t[2] + 0.05), LAVENDER, segs=(6, 4), grad=(0.0, 0.4))
	p.seg((0, 0, 0.2), (0, 0, 0.3), 0.1, 0.1, WOOD_GRAY, sides=8)                   # the twine
	return p.build()


def _ore(p, size, loc, seed_off, glints):
	p.rock(size, loc, STONE_DARK, grad=(0.0, 0.45), jitter=0.12)
	for k in range(glints):
		a = (k + seed_off) * 2.3
		x = loc[0] + math.cos(a) * size[0] * 0.3
		z = loc[2] + (0.1 + (k % 3) * 0.12) * size[2]
		p.blob((0.1, 0.06, 0.1), (x, loc[1] - size[1] * 0.42, z), EMBER, segs=(5, 4), glow=1.0)


def small_brick_of_ore():
	p = Prop("small_brick_of_ore", 413)
	_ore(p, (0.85, 0.7, 0.6), (0, 0, 0.3), 0, 4)
	_frame(p, (-0.7, -0.5, 0.0), (0.7, 0.5, 0.85))
	return p.build()


def large_brick_of_ore():
	p = Prop("large_brick_of_ore", 415)
	p.box((1.3, 0.95, 0.55), (0, 0, 0.3), STONE_DARK, grad=(0.0, 0.5), jitter=0.06)   # a squared block
	for k in range(6):
		x = -0.45 + k * 0.18
		p.blob((0.12, 0.07, 0.12), (x, -0.48, 0.15 + (k % 3) * 0.13), EMBER, segs=(5, 4), glow=1.0)
		p.blob((0.12, 0.12, 0.07), (x + 0.05, -0.2 + (k % 2) * 0.3, 0.58), EMBER, segs=(5, 4), glow=1.0)
	_ore(p, (0.45, 0.4, 0.35), (0.25, 0.1, 0.72), 2, 2)                               # a lump on top
	_frame(p, (-0.7, -0.5, 0.0), (0.7, 0.5, 0.85))
	return p.build()


def water_flask():
	p = Prop("water_flask", 417)
	p.seg((0, -0.15, 0.45), (0, 0.15, 0.45), 0.42, 0.42, STONE_LIGHT, sides=18, grad=(0.0, 0.7))  # a round tin canteen
	p.seg((0, -0.17, 0.45), (0, -0.13, 0.45), 0.22, 0.22, WATER, sides=16, glow=0.3)             # a blue boss on its face
	p.seg((0, -0.04, 0.45), (0, 0.04, 0.45), 0.45, 0.45, HIDE, sides=18)                          # stitched leather band
	p.seg((0, 0, 0.85), (0, 0, 1.0), 0.1, 0.12, STONE_LIGHT, sides=8)
	p.seg((0, 0, 1.0), (0, 0, 1.12), 0.09, 0.11, WOOD, sides=8)                                  # cork
	pts = [(-0.44, 0, 0.5), (-0.5, 0, 0.95), (-0.3, 0, 1.25), (0.0, 0, 1.33), (0.3, 0, 1.25), (0.5, 0, 0.95), (0.44, 0, 0.5)]
	for a, b in zip(pts, pts[1:]):                                                                # carrying strap
		p.seg(a, b, 0.035, 0.035, HIDE, sides=5)
	return p.build()


def bundle_of_shafts():
	p = Prop("bundle_of_shafts", 419)
	for k in range(9):
		dy = (k % 3 - 1) * 0.1
		dz = (k // 3 - 1) * 0.1
		p.seg((-0.7 + (k % 4) * 0.04, dy, 0.1 + dz), (0.62 - (k % 3) * 0.04, dy, 0.85 + dz), 0.05, 0.05, WOOD, sides=6, grad=(0.1, 0.5))
	for t in (0.28, 0.72):                                                         # two ties
		x, z = -0.68 + t * 1.3, 0.1 + t * 0.75
		p.seg((x - 0.04, 0, z - 0.03), (x + 0.04, 0, z + 0.03), 0.22, 0.22, CLOTH_RED, sides=10)
	return p.build()


def smithy_hammer():
	p = Prop("smithy_hammer", 421)
	p.seg((-0.25, 0, 0.0), (0.05, 0, 1.0), 0.06, 0.07, WOOD, sides=8, grad=(0.1, 0.6))      # haft
	p.seg((-0.24, 0, 0.03), (-0.17, 0, 0.3), 0.08, 0.08, HIDE, sides=8)                    # grip wrap
	p.box((0.62, 0.24, 0.24), (0.08, 0, 1.02), STONE_DARK, rot=(0, 16.7, 0), grad=(0.0, 0.6))  # the head
	p.seg((0.36, 0, 0.94), (0.46, 0, 0.91), 0.17, 0.17, STONE_LIGHT, sides=8)               # striking face
	p.seg((-0.2, 0, 1.12), (-0.38, 0, 1.18), 0.1, 0.02, STONE_DARK, sides=4)                # the peen
	return p.build()


def sewing_kit():
	p = Prop("sewing_kit", 423)
	p.box((1.05, 0.65, 0.34), (0, 0, 0.17), WOOD, grad=(0.1, 0.8))                         # a little box
	p.box((1.05, 0.06, 0.62), (0, 0.36, 0.58), WOOD, rot=(-18, 0, 0), grad=(0.1, 0.7))       # its lid, open
	p.box((0.12, 0.06, 0.1), (0, -0.34, 0.26), GOLD)                                         # latch
	for k, sw in enumerate((CLOTH_RED, RUNE, GOLD)):                                         # spools inside
		x = -0.3 + k * 0.22
		p.seg((x, 0.05, 0.3), (x, 0.05, 0.5), 0.09, 0.09, sw, sides=10)
		p.seg((x, 0.05, 0.49), (x, 0.05, 0.53), 0.11, 0.11, WOOD_GRAY, sides=10)
	p.blob((0.3, 0.3, 0.24), (0.33, -0.05, 0.42), CLOTH_RED, segs=(10, 6), grad=(0.0, 0.6))  # pincushion
	for k in range(3):
		a = k * 1.1 - 1.1
		p.seg((0.33 + math.sin(a) * 0.05, -0.05, 0.5), (0.33 + math.sin(a) * 0.25, -0.1, 0.8), 0.02, 0.006, STONE_LIGHT, sides=4, glow=0.4)
		p.blob((0.05, 0.05, 0.05), (0.33 + math.sin(a) * 0.25, -0.1, 0.8), CLOTH_WHITE, segs=(5, 4))
	return p.build()


def mortar_and_pestle():
	p = Prop("mortar_and_pestle", 425)
	p.seg((0, 0, 0), (0, 0, 0.1), 0.32, 0.36, STONE_LIGHT, sides=14)
	p.seg((0, 0, 0.1), (0, 0, 0.5), 0.36, 0.55, STONE_LIGHT, sides=14, grad=(0.0, 0.8))    # the bowl
	p.seg((0, 0, 0.49), (0, 0, 0.51), 0.46, 0.46, STONE_DARK, sides=14)                    # its dark hollow
	for k in range(5):                                                                     # herbs being ground
		a = k * 1.3
		p.blob((0.14, 0.1, 0.06), (math.cos(a) * 0.22, math.sin(a) * 0.2, 0.52), LEAF, segs=(6, 4))
	p.seg((-0.15, 0.05, 0.42), (0.35, -0.05, 1.1), 0.07, 0.1, STONE_WARM, sides=10, grad=(0.0, 0.6))  # pestle
	p.blob((0.22, 0.22, 0.22), (0.36, -0.05, 1.12), STONE_WARM, segs=(8, 6))
	return p.build()


# recipe books: a standing book, cover to the camera, pages on the right

def _book(p, cover, trim=GOLD):
	p.box((0.84, 0.05, 1.08), (0, -0.12, 0.54), cover, grad=(0.1, 0.7))    # front cover
	p.box((0.84, 0.05, 1.08), (0, 0.12, 0.54), cover, grad=(0.2, 0.8))     # back cover
	p.box((0.08, 0.29, 1.08), (-0.4, 0, 0.54), cover, grad=(0.1, 0.8))     # spine
	p.box((0.78, 0.2, 1.0), (0.0, 0, 0.54), CLOTH_WHITE, grad=(0.2, 0.7))  # pages
	for x in (-0.36, 0.36):                                                 # metal corners
		for z in (0.06, 1.02):
			p.box((0.14, 0.07, 0.14), (x, -0.13, z), trim)
	p.box((0.84, 0.07, 0.05), (0, -0.13, 0.2), trim)                        # bands across the cover
	p.box((0.84, 0.07, 0.05), (0, -0.13, 0.88), trim)


def hearthside_cookbook():
	p = Prop("hearthside_cookbook", 427)
	_book(p, CLOTH_RED)
	p.blob((0.46, 0.08, 0.28), (0, -0.17, 0.55), AMBER, segs=(10, 6), grad=(0.0, 0.6))     # a loaf
	for k in range(3):
		p.box((0.04, 0.03, 0.18), (-0.12 + k * 0.12, -0.21, 0.58), CLOTH_WHITE, rot=(0, 25, 0))
	return p.build()


def tailors_pattern_book():
	p = Prop("tailors_pattern_book", 429)
	_book(p, WATER, trim=STONE_LIGHT)
	p.seg((-0.22, -0.17, 0.3), (0.22, -0.17, 0.8), 0.035, 0.008, CLOTH_WHITE, sides=5, glow=0.5)  # a needle
	_loop(p, (0.19, -0.17, 0.72), 0.045, False, 0.012, CLOTH_WHITE, n=6)
	pts = [(0.19, -0.18, 0.72), (0.3, -0.18, 0.6), (0.05, -0.18, 0.45), (0.25, -0.18, 0.32)]  # its thread
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.02, 0.02, GOLD, sides=4)
	return p.build()


def alchemists_notes():
	p = Prop("alchemists_notes", 431)
	_book(p, MOSS, trim=GOLD)
	p.blob((0.3, 0.08, 0.26), (0, -0.17, 0.46), RUNE, segs=(10, 6), glow=1.2)       # a flask
	p.box((0.09, 0.07, 0.2), (0, -0.17, 0.66), CLOTH_WHITE)
	p.box((0.14, 0.07, 0.04), (0, -0.17, 0.76), CLOTH_WHITE)
	for s_ in (-1, 1):                                                           # loose papers
		p.box((0.3, 0.02, 0.4), (0.3 * s_ + 0.1, -0.02, 0.9), CLOTH_WHITE, rot=(0, s_ * 20, 0))
	return p.build()


def smiths_handbook():
	p = Prop("smiths_handbook", 433)
	_book(p, STONE_DARK, trim=EMBER)
	p.seg((-0.12, -0.17, 0.3), (0.08, -0.17, 0.72), 0.03, 0.03, WOOD, sides=5)          # a hammer
	p.box((0.34, 0.08, 0.14), (0.1, -0.18, 0.72), EMBER, rot=(0, 25, 0), glow=0.9)
	return p.build()


# drops

def raw_meat():
	p = Prop("raw_meat", 435)
	tilt = Euler((math.radians(50), 0, math.radians(8)))

	def at(x, y, z):
		return tuple(tilt.to_matrix() @ Vector((x, y, z)) + Vector((0, 0, 0.45)))
	rot = (50, 0, 8)
	p.blob((1.15, 0.9, 0.3), at(0, 0, -0.04), CLOTH_WHITE, rot=rot, segs=(14, 6), grad=(0.1, 0.5))      # fat rind
	p.blob((1.05, 0.8, 0.32), at(-0.03, -0.02, 0.04), CLOTH_RED, rot=rot, segs=(14, 6), grad=(0.0, 0.7), jitter=0.02)
	for k in range(4):                                                               # marbling
		p.box((0.28, 0.05, 0.03), at(-0.32 + k * 0.17, -0.18 + (k % 2) * 0.28, 0.2), PINK, rot=(50, 0, 30 + k * 20))
	p.seg(at(0.24, 0.08, 0.1), at(0.24, 0.08, 0.26), 0.14, 0.14, BONE, sides=10)          # the bone
	p.seg(at(0.24, 0.08, 0.25), at(0.24, 0.08, 0.28), 0.07, 0.07, STONE_WARM, sides=8)
	return p.build()


def _frog_pair(p, swatch, flat=False, lift=0.0):
	"""Two frog legs joined at the hip: thigh, shin and a webbed foot each."""
	def at(x, h):
		return (x, h * 0.7 - 0.45, 0.14 + lift + (0.02 if h > 0.5 else 0.0)) if flat else (x, 0, h)
	p.blob((0.3, 0.22, 0.2) if not flat else (0.3, 0.2, 0.18), at(0, 1.0), swatch, segs=(8, 5))
	for s_ in (-1, 1):
		hip, knee, ankle = at(s_ * 0.08, 0.98), at(s_ * 0.42, 0.55), at(s_ * 0.18, 0.18)
		p.seg(hip, knee, 0.14, 0.1, swatch, sides=8, grad=(0.1, 0.7))
		p.blob((0.2, 0.18, 0.18), knee, swatch, segs=(6, 4))
		p.seg(knee, ankle, 0.09, 0.05, swatch, sides=7, grad=(0.1, 0.7))
		toes = [at(s_ * 0.12, -0.05), at(s_ * 0.28, -0.08), at(s_ * 0.4, 0.0)]
		for t in toes:
			p.seg(ankle, t, 0.03, 0.02, swatch, sides=4)
		p.poly([ankle] + toes, [(0, 1, 2), (0, 2, 3)], swatch)


def frog_legs():
	p = Prop("frog_legs", 437)
	_frog_pair(p, LEAF)
	return p.build()


# intermediates

def tanned_leather():
	p = Prop("tanned_leather", 439)
	p.poly([(-0.5, 0.0, 0.05), (0.5, 0.0, 0.05), (0.55, -0.35, 0.03), (0.35, -0.7, 0.02), (-0.2, -0.75, 0.02), (-0.55, -0.4, 0.03)],
		   [(0, 1, 2, 3, 4, 5)], HIDE, grad=(0.0, 0.3))                                     # the sheet, unrolled
	p.seg((-0.55, 0.1, 0.28), (0.55, 0.1, 0.28), 0.26, 0.26, HIDE, sides=14, grad=(0.0, 0.8))  # rolled up behind
	p.seg((0.55, 0.1, 0.28), (0.57, 0.1, 0.28), 0.18, 0.18, WOOD, sides=12)               # the end of the roll
	for x in (-0.3, 0.3):
		p.seg((x - 0.03, 0.1, 0.28), (x + 0.03, 0.1, 0.28), 0.28, 0.28, WOOD, sides=12)      # ties
	return p.build()


def thick_leather():
	p = Prop("thick_leather", 441)
	for k in range(3):                                                               # a folded stack
		p.box((1.1 - k * 0.06, 0.8 - k * 0.04, 0.14), (k * 0.03, k * 0.02, 0.07 + k * 0.15), MOSS, rot=(0, 0, k * 4 - 4), grad=(0.1, 0.7))
	for r in range(3):                                                               # rows of scutes on top
		for c in range(4):
			p.blob((0.18, 0.14, 0.1), (-0.36 + c * 0.24 + 0.06, -0.24 + r * 0.24 + 0.04, 0.43), LEAF, segs=(6, 4), grad=(0.0, 0.5))
	p.seg((-0.1, -0.45, 0.25), (-0.1, 0.45, 0.25), 0.05, 0.05, HIDE, sides=5)              # strap round the stack
	p.box((0.08, 0.9, 0.52), (-0.1, 0.0, 0.26), HIDE)
	return p.build()


def _bolt(p, cloth, grad=(0.0, 0.7), glow=0.0, stripe=None):
	p.seg((-0.6, 0.15, 0.36), (0.6, 0.15, 0.36), 0.34, 0.34, cloth, sides=16, grad=grad, glow=glow)   # the roll
	for x in (-0.62, 0.62):                                                               # the board it's wound on
		p.box((0.04, 0.2, 0.2), (x, 0.15, 0.36), WOOD)
	p.box((1.2, 0.5, 0.03), (0, -0.3, 0.02), cloth, grad=grad, glow=glow)                  # a length unrolled
	if stripe:
		for x in (-0.45, 0.45):
			p.seg((x, 0.15, 0.36), (x + 0.04, 0.15, 0.36), 0.35, 0.35, stripe, sides=16)
			p.box((0.04, 0.5, 0.035), (x, -0.3, 0.025), stripe)


def wool_cloth():
	p = Prop("wool_cloth", 443)
	_bolt(p, CLOTH_RED, stripe=CLOTH_WHITE)
	return p.build()


def silk_cloth():
	p = Prop("silk_cloth", 445)
	_bolt(p, LAVENDER, grad=(0.0, 0.3), glow=0.35, stripe=CLOTH_WHITE)
	return p.build()


def _ingot(p, swatch, grad=(0.0, 0.5)):
	w0, d0, w1, d1, h = 0.55, 0.26, 0.42, 0.17, 0.26
	vs = [(-w0, -d0, 0), (w0, -d0, 0), (w0, d0, 0), (-w0, d0, 0), (-w1, -d1, h), (w1, -d1, h), (w1, d1, h), (-w1, d1, h)]
	faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
	p.poly(vs, faces, swatch, grad=grad)
	p.box((0.18, 0.1, 0.01), (0, 0, h + 0.005), STONE_DARK if swatch != STONE_DARK else IRON)  # a maker's stamp


def iron_bar():
	p = Prop("iron_bar", 447)
	_ingot(p, WOOD_GRAY, grad=(0.0, 0.7))
	for (x, y) in ((-0.3, -0.27), (0.2, -0.27), (0.45, 0.0)):                             # rust
		p.blob((0.12, 0.04, 0.08), (x, y, 0.12), EMBER, segs=(6, 4), grad=(0.6, 0.9))
	return p.build()


def steel_bar():
	p = Prop("steel_bar", 449)
	_ingot(p, STONE_LIGHT, grad=(0.0, 0.45))
	p.box((0.7, 0.02, 0.04), (0, -0.22, 0.14), CLOTH_WHITE, glow=0.8)                       # a bright edge
	return p.build()


# food

def roast_meat():
	p = Prop("roast_meat", 451)
	p.blob((0.75, 0.62, 0.9), (-0.12, 0, 0.42), WOOD, rot=(0, 35, 0), segs=(12, 8), grad=(0.0, 0.9))  # the haunch
	p.blob((0.5, 0.42, 0.55), (-0.2, -0.12, 0.5), AMBER, rot=(0, 35, 0), segs=(10, 6), grad=(0.0, 0.8))  # glazed
	p.seg((0.15, 0, 0.65), (0.55, 0, 1.05), 0.09, 0.08, BONE, sides=8)                        # the bone
	for s_ in (-1, 1):
		p.blob((0.16, 0.16, 0.16), (0.58 + s_ * 0.05, s_ * 0.06, 1.08 - s_ * 0.05), BONE, segs=(7, 5))
	for k in range(3):                                                                    # char lines
		p.box((0.3, 0.03, 0.03), (-0.25 + k * 0.12, -0.36, 0.3 + k * 0.14), STONE_DARK, rot=(0, -30, 0))
	return p.build()


def _fish_at(p, body, fin, loc, s=1.0, fat=0.3):
	x0, y0, z0 = loc
	def at(x, y, z):
		return (x0 + x * s, y0 + y * s, z0 + z * s)
	p.blob((s, fat * 0.8 * s, fat * 1.6 * s), at(0, 0, 0), body, segs=(12, 6), grad=(0.1, 0.8))
	p.poly([at(0.45, 0, 0), at(0.75, 0, 0.27), at(0.75, 0, -0.27)], [(0, 1, 2)], fin)
	p.poly([at(-0.15, 0, fat * 0.7), at(0.2, 0, fat * 0.7), at(0.05, 0, fat * 1.2)], [(0, 1, 2)], fin)
	p.blob((0.09 * s, 0.05 * s, 0.09 * s), at(-0.36, -fat * 0.3, 0.07), STONE_DARK, segs=(6, 4))


def grilled_trout():
	p = Prop("grilled_trout", 453)
	p.box((1.5, 0.6, 0.08), (0.05, 0, 0.04), WOOD, grad=(0.1, 0.5))                             # a plank
	_fish_at(p, AMBER, EMBER, (0, 0, 0.35), fat=0.28)
	for k in range(4):                                                                     # grill marks
		p.box((0.04, 0.02, 0.36), (-0.25 + k * 0.17, -0.115, 0.36), STONE_DARK, rot=(0, 25, 0))
	p.blob((0.22, 0.14, 0.12), (-0.55, -0.15, 0.13), GOLD, segs=(8, 5), glow=0.3)             # a wedge of lemon
	p.blob((0.2, 0.1, 0.05), (0.55, -0.18, 0.1), LEAF, segs=(6, 4))                            # and a sprig
	return p.build()


def _bowl(p, swatch=WOOD, r=0.62, h=0.45):
	p.seg((0, 0, 0), (0, 0, 0.08), r * 0.45, r * 0.5, swatch, sides=14)
	p.seg((0, 0, 0.08), (0, 0, h), r * 0.55, r, swatch, sides=16, grad=(0.1, 0.8))


def fish_stew():
	p = Prop("fish_stew", 455)
	_bowl(p)
	p.seg((0, 0, 0.4), (0, 0, 0.43), 0.56, 0.56, ORANGE, sides=16, grad=(0.1, 0.3))          # the broth
	for k in range(6):                                                                     # fish and herbs in it
		a = k * 1.05
		sw = CLOTH_WHITE if k % 2 else LEAF
		p.blob((0.16, 0.12, 0.07), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.45), sw, segs=(6, 4))
	p.seg((0.1, 0.1, 0.42), (0.6, 0.35, 0.95), 0.04, 0.05, WOOD_GRAY, sides=6)             # a spoon
	for k in range(2):                                                                     # steam
		x = -0.15 + k * 0.3
		p.seg((x, 0, 0.55), (x + 0.08, 0, 0.8), 0.05, 0.02, CLOTH_WHITE, sides=5, glow=0.3)
		p.seg((x + 0.08, 0, 0.8), (x, 0, 1.0), 0.02, 0.0, CLOTH_WHITE, sides=5, glow=0.3)
	return p.build()


def hunters_pie():
	p = Prop("hunters_pie", 457)
	p.seg((0, 0, 0), (0, 0, 0.2), 0.62, 0.72, CLAY, sides=18)                                  # the dish
	p.blob((1.3, 1.3, 0.4), (0, 0, 0.22), AMBER, segs=(16, 8), grad=(0.0, 0.7))              # the crust
	_loop(p, (0, 0, 0.24), 0.64, True, 0.07, GOLD, n=16)                                      # crimped edge
	for k in range(3):                                                                     # vents
		a = k * math.tau / 3 + 0.3
		p.box((0.2, 0.04, 0.04), (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.42), WOOD, rot=(0, 0, math.degrees(a)))
	p.blob((0.16, 0.12, 0.08), (0, 0, 0.43), LEAF, segs=(6, 4))                                # a sprig on top
	return p.build()


def _plate(p, swatch=STONE_LIGHT, r=0.7):
	p.seg((0, 0, 0), (0, 0, 0.05), r * 0.8, r, swatch, sides=18, grad=(0.0, 0.6))
	p.seg((0, 0, 0.05), (0, 0, 0.07), r, r * 1.02, swatch, sides=18, grad=(0.0, 0.4))


def frog_legs_saute():
	p = Prop("frog_legs_saute", 459)
	_plate(p, STONE_WARM, r=0.62)
	_frog_pair(p, AMBER, flat=True, lift=0.0)
	for k in range(5):                                                                     # herbs
		a = k * 1.3
		p.blob((0.1, 0.08, 0.04), (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.1), LEAF, segs=(5, 4))
	return p.build()


def lagoon_feast():
	p = Prop("lagoon_feast", 461)
	p.blob((1.9, 1.2, 0.12), (0, 0, 0.06), WOOD, segs=(18, 6), grad=(0.1, 0.6))                # a wide board
	for k in range(4):                                                                     # banana leaves
		p.blob((0.7, 0.22, 0.03), (-0.3 + k * 0.2, 0.1, 0.13), LEAF, rot=(0, 0, -30 + k * 20), segs=(8, 4))
	_fish_at(p, CLOTH_RED, EMBER, (-0.15, 0.1, 0.32), s=0.8, fat=0.3)                           # a snapper
	p.blob((0.34, 0.34, 0.24), (0.6, -0.25, 0.2), WOOD, segs=(10, 6), grad=(0.3, 0.9))          # half a coconut
	p.seg((0.6, -0.25, 0.3), (0.6, -0.25, 0.32), 0.15, 0.15, CLOTH_WHITE, sides=10)
	for k in range(3):                                                                     # fruit
		p.blob((0.2, 0.2, 0.2), (-0.65 + k * 0.17, -0.35 + (k % 2) * 0.08, 0.22), ORANGE, segs=(8, 6), grad=(0.0, 0.5))
	for k in range(3):                                                                     # prawns
		x = 0.25 + k * 0.14
		p.seg((x, 0.35, 0.16), (x + 0.08, 0.4, 0.3), 0.06, 0.03, PINK, sides=6)
	return p.build()


def koi_platter():
	p = Prop("koi_platter", 463)
	_plate(p, WATER, r=0.8)
	for k in range(5):                                                                     # a bed of leaves
		a = k * math.tau / 5
		p.blob((0.45, 0.18, 0.03), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.09), LEAF, rot=(0, 0, math.degrees(a)), segs=(8, 4))
	_fish_at(p, CLOTH_WHITE, EMBER, (0, 0, 0.3), s=0.95, fat=0.3)
	for (x, z, sw) in ((0.0, 0.08, CLOTH_RED), (0.2, -0.03, EMBER), (-0.17, -0.05, GOLD), (0.05, -0.08, CLOTH_RED)):  # koi patches
		p.blob((0.2, 0.04, 0.15), (x, -0.12, 0.3 + z), sw, segs=(6, 4))
	p.blob((0.12, 0.03, 0.1), (0.1, -0.13, 0.36), WATER, segs=(6, 4), glow=0.8)                  # the rainbow sheen
	for k in range(4):                                                                     # jeweled garnish round the rim
		a = k * math.tau / 4 + 0.6
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.68, math.sin(a) * 0.68, 0.12), (RUNE, LAVENDER, LEAF, EMBER)[k], segs=(6, 4), glow=0.8)
	return p.build()


# potions: the liquid is the bottle; glass shows as neck, lip, a glint and a cork

def _potion(p, top, neck=0.28, neck_r=0.1, cork=WOOD):
	"""Glass neck, lip and cork on a bottle whose shoulder ends at `top`."""
	p.seg((0, 0, top - 0.05), (0, 0, top + neck), neck_r, neck_r * 0.9, CLOTH_WHITE, sides=10, grad=(0.1, 0.5))
	p.seg((0, 0, top + neck - 0.02), (0, 0, top + neck + 0.04), neck_r * 1.3, neck_r * 1.3, CLOTH_WHITE, sides=10)
	p.seg((0, 0, top + neck + 0.03), (0, 0, top + neck + 0.16), neck_r * 0.85, neck_r, cork, sides=8)
	return top + neck


POTION_FRAME = ((-0.5, -0.5, 0.0), (0.5, 0.5, 1.38))


def minor_healing_potion():
	p = Prop("minor_healing_potion", 465)
	p.blob((0.62, 0.62, 0.62), (0, 0, 0.31), CLOTH_RED, segs=(12, 8), grad=(0.0, 0.6), glow=0.9)
	_potion(p, 0.58, neck=0.16, neck_r=0.08)
	p.box((0.04, 0.02, 0.16), (-0.12, -0.3, 0.38), CLOTH_WHITE, glow=0.8)
	_frame(p, *POTION_FRAME)
	return p.build()


def healing_potion():
	p = Prop("healing_potion", 467)
	p.blob((0.8, 0.8, 0.8), (0, 0, 0.4), CLOTH_RED, segs=(14, 8), grad=(0.0, 0.6), glow=1.0)
	_potion(p, 0.76, neck=0.24, neck_r=0.09)
	p.box((0.05, 0.02, 0.22), (-0.16, -0.38, 0.5), CLOTH_WHITE, glow=0.8)
	_frame(p, *POTION_FRAME)
	return p.build()


def greater_healing_potion():
	p = Prop("greater_healing_potion", 469)
	p.blob((1.0, 1.0, 0.86), (0, 0, 0.43), CLOTH_RED, segs=(16, 10), grad=(0.0, 0.6), glow=1.2)
	p.seg((0, 0, 0.74), (0, 0, 0.95), 0.26, 0.13, CLOTH_RED, sides=12, glow=1.2)            # a pear-shaped shoulder
	p.seg((0, 0, 0.9), (0, 0, 1.12), 0.13, 0.12, CLOTH_WHITE, sides=10)
	p.seg((0, 0, 0.98), (0, 0, 1.03), 0.16, 0.16, GOLD, sides=10)                           # gold collar
	p.seg((0, 0, 1.1), (0, 0, 1.3), 0.1, 0.14, GOLD, sides=8, glow=0.3)                      # gold stopper
	p.blob((0.12, 0.12, 0.12), (0, 0, 1.32), GOLD, segs=(6, 4))
	p.box((0.06, 0.02, 0.28), (-0.22, -0.46, 0.5), CLOTH_WHITE, glow=0.8)
	_frame(p, *POTION_FRAME)
	return p.build()


def antidote():
	p = Prop("antidote", 471)
	p.seg((0, 0, 0.05), (0, 0, 0.85), 0.2, 0.2, LEAF, sides=12, grad=(0.0, 0.6), glow=0.9)    # a tall slim vial
	p.seg((0, 0, 0.0), (0, 0, 0.06), 0.18, 0.2, LEAF, sides=12, glow=0.9)
	p.seg((0, 0, 0.85), (0, 0, 0.92), 0.2, 0.12, CLOTH_WHITE, sides=12)
	_potion(p, 0.95, neck=0.12, neck_r=0.08)
	p.box((0.26, 0.02, 0.3), (0, -0.21, 0.45), CLOTH_WHITE, grad=(0.1, 0.4))                  # a paper label
	p.box((0.16, 0.025, 0.04), (0, -0.22, 0.5), LEAF)
	p.box((0.04, 0.025, 0.16), (0, -0.22, 0.5), LEAF)
	return p.build()


def clarity_tonic():
	p = Prop("clarity_tonic", 473)
	p.seg((0, 0, 0.05), (0, 0, 0.45), 0.2, 0.46, RUNE, sides=6, grad=(0.0, 0.5), glow=1.1)    # a cut-crystal bottle
	p.seg((0, 0, 0.45), (0, 0, 0.8), 0.46, 0.14, RUNE, sides=6, grad=(0.0, 0.5), glow=1.1)
	_potion(p, 0.8, neck=0.12, neck_r=0.1, cork=STONE_LIGHT)
	p.blob((0.12, 0.12, 0.12), (0, 0, 1.12), RUNE, segs=(6, 4), glow=1.5)                     # a crystal on the stopper
	p.box((0.05, 0.02, 0.26), (-0.18, -0.36, 0.45), CLOTH_WHITE, glow=0.8)
	return p.build()


def draught_of_toughness():
	p = Prop("draught_of_toughness", 475)
	p.box((0.62, 0.5, 0.62), (0, 0, 0.31), HIDE, grad=(0.0, 0.7), glow=0.4)                    # a square-shouldered jug
	p.seg((0, 0, 0.6), (0, 0, 0.75), 0.24, 0.12, HIDE, sides=8, glow=0.4)
	_potion(p, 0.72, neck=0.1, neck_r=0.1)
	p.box((0.66, 0.54, 0.1), (0, 0, 0.18), IRON)                                               # an iron band
	for x in (-0.2, 0.2):
		p.blob((0.07, 0.04, 0.07), (x, -0.27, 0.18), STONE_LIGHT, segs=(5, 4))                 # rivets
	_loop(p, (0.36, 0, 0.42), 0.14, False, 0.04, HIDE, n=8)                                     # a handle
	return p.build()


def troll_tonic():
	p = Prop("troll_tonic", 477)
	p.blob((0.7, 0.66, 0.6), (0, 0, 0.3), MOSS, segs=(12, 8), grad=(0.0, 0.7), glow=0.8)       # a gourd
	p.blob((0.42, 0.4, 0.4), (0.05, 0, 0.72), MOSS, segs=(10, 6), grad=(0.0, 0.7), glow=0.8)
	p.seg((0.05, 0, 0.88), (0.1, 0, 1.05), 0.08, 0.07, WOOD, sides=6)                           # a stick for a stopper
	p.seg((0.05, 0, 0.55), (0.05, 0, 0.6), 0.23, 0.23, WOOD_GRAY, sides=10)                     # twine round the waist
	for k in range(5):                                                                     # clinging moss
		a = k * 1.4
		p.blob((0.16, 0.08, 0.12), (math.cos(a) * 0.3, math.sin(a) * 0.3 - 0.05, 0.12 + (k % 3) * 0.14), LEAF, segs=(5, 4))
	p.seg((0.3, -0.1, 0.62), (0.45, -0.1, 0.4), 0.06, 0.0, BONE, sides=5)                       # a troll tooth tied on
	return p.build()


def draught_of_swiftness():
	p = Prop("draught_of_swiftness", 479)
	p.seg((0, 0, 0.0), (0, 0, 0.7), 0.46, 0.1, CLOTH_WHITE, sides=14, grad=(0.0, 0.5), glow=1.0)  # a cone flask
	p.seg((0, 0, 0.0), (0, 0, 0.04), 0.46, 0.46, RUNE, sides=14, glow=0.6)
	_potion(p, 0.7, neck=0.14, neck_r=0.1)
	p.poly([(0.1, -0.05, 0.8), (0.55, -0.05, 1.2), (0.62, -0.05, 1.05), (0.2, -0.05, 0.76)], [(0, 1, 2, 3)], GOLD)  # a feather at the neck
	p.seg((0.1, -0.05, 0.78), (0.6, -0.05, 1.14), 0.015, 0.01, WOOD, sides=4)
	p.box((0.05, 0.02, 0.24), (-0.18, -0.3, 0.25), RUNE, rot=(0, 25, 0), glow=0.8)
	return p.build()


# bags

def stitched_hide_pouch():
	p = Prop("stitched_hide_pouch", 481)
	p.blob((0.75, 0.62, 0.7), (0, 0, 0.35), HIDE, segs=(12, 8), grad=(0.1, 0.9))
	p.seg((0, 0, 0.64), (0, 0, 0.9), 0.1, 0.2, HIDE, sides=8)                                   # gathered neck
	p.seg((0, 0, 0.7), (0, 0, 0.75), 0.13, 0.13, WOOD, sides=8)                                 # drawstring
	p.seg((0.1, -0.1, 0.72), (0.3, -0.2, 0.45), 0.025, 0.025, WOOD, sides=4)
	p.blob((0.06, 0.06, 0.06), (0.3, -0.2, 0.43), WOOD, segs=(5, 4))
	for k in range(6):                                                                     # a stitched seam down the front
		z = 0.12 + k * 0.09
		p.seg((-0.05, -0.34, z), (0.05, -0.34, z + 0.03), 0.018, 0.018, CLOTH_WHITE, sides=4)
	p.seg((0, -0.33, 0.1), (0, -0.33, 0.6), 0.012, 0.012, WOOD, sides=4)
	return p.build()


def wool_satchel():
	p = Prop("wool_satchel", 483)
	_bag(p, CLOTH_RED, 0.95, 0.35, 0.65, strap=HIDE)
	p.box((0.8, 0.03, 0.04), (0, -0.17, 0.18), CLOTH_WHITE)                                   # a woven stripe
	p.blob((0.1, 0.06, 0.1), (0, -0.21, 0.5), GOLD, segs=(6, 4))                               # button
	pts = []
	for k in range(9):                                                                     # a long shoulder strap
		a = math.pi * k / 8
		pts.append((-math.cos(a) * 0.45, 0, 0.55 + math.sin(a) * 0.55))
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.04, 0.04, HIDE, sides=5)
	return p.build()


def crocskin_backpack():
	p = Prop("crocskin_backpack", 485)
	_bag(p, MOSS, 0.85, 0.55, 1.0, strap=HIDE)
	for r in range(3):                                                                     # scutes
		for c in range(3):
			p.blob((0.14, 0.06, 0.1), (-0.2 + c * 0.2, -0.28, 0.2 + r * 0.14), LEAF, segs=(6, 4), grad=(0.0, 0.5))
	p.box((0.1, 0.06, 0.12), (0, -0.33, 0.62), GOLD)                                           # buckle
	for x in (-1, 1):
		p.blob((0.22, 0.28, 0.34), (x * 0.46, -0.02, 0.36), HIDE, segs=(8, 6))                 # side pouches
	p.seg((0.3, 0.2, 1.0), (0.45, 0.25, 1.12), 0.06, 0.0, BONE, sides=5)                       # a croc tooth toggle
	return p.build()


def iron_tipped_arrow():
	p = Prop("iron_tipped_arrow", 487)
	a, b = (-0.6, 0, 0.05), (0.5, 0, 0.95)
	p.seg(a, b, 0.035, 0.035, WOOD, sides=6)                                                   # shaft
	p.seg(b, (0.66, 0, 1.08), 0.09, 0.0, STONE_LIGHT, sides=4, glow=0.2)                         # iron head
	p.seg((0.46, 0, 0.92), (0.51, 0, 0.96), 0.06, 0.06, STONE_DARK, sides=6)                     # its socket
	d = (Vector(b) - Vector(a)).normalized()
	for off, sw in (((-d.z, 0, d.x), CLOTH_WHITE), ((d.z, 0, -d.x), CLOTH_RED), ((0, -1, 0), CLOTH_RED)):  # fletching
		n = Vector(off) * 0.13
		root, tip = Vector(a) + d * 0.04, Vector(a) + d * 0.3
		p.poly([tuple(root), tuple(tip), tuple(tip - d * 0.06 + n), tuple(root + n * 0.9)], [(0, 1, 2, 3)], sw)
	p.seg((-0.62, 0, 0.02), (-0.58, 0, 0.06), 0.04, 0.04, CLOTH_RED, sides=5)                    # nock
	return p.build()


TRADESKILLS = [bag_of_flour, jar_of_spices, vial_of_water, tanning_salts, spool_of_thread, bundle_of_herbs, small_brick_of_ore,
			   large_brick_of_ore, water_flask, bundle_of_shafts, smithy_hammer, sewing_kit, mortar_and_pestle, hearthside_cookbook,
			   tailors_pattern_book, alchemists_notes, smiths_handbook, raw_meat, frog_legs, tanned_leather, thick_leather, wool_cloth,
			   silk_cloth, iron_bar, steel_bar, roast_meat, grilled_trout, fish_stew, hunters_pie, frog_legs_saute, lagoon_feast,
			   koi_platter, minor_healing_potion, antidote, healing_potion, clarity_tonic, draught_of_toughness, troll_tonic,
			   draught_of_swiftness, greater_healing_potion, stitched_hide_pouch, wool_satchel, crocskin_backpack, iron_tipped_arrow]


SMALL = {f.__name__: f for f in [gnoll_fang, beetle_eye, bone_chips, rat_whiskers, fishing_bait, bone_charm,
								 fang_necklace, tarnished_ring, copper_band, bonecarved_talisman, small_sack,
								 worn_backpack, gnollhide_satchel, leather_backpack, braided_whisker_cord, blackpaw_pelt,
									 stitched_blackpaw_hide, tovins_trail_pack, crude_arrow, sling_stone, leather_sling,
									 patchwork_pants, leather_leggings, iron_greaves, wolf_pelt, dire_wolf_fang, bear_claw,
									 bear_hide, spider_silk, venom_sac, orc_tusk, hollow_watch_signet,
									 mire_toad_skin, leech_teeth, turtle_shell_plate, mirescale_scale, waterlogged_locket,
									 snapjaws_shell, drowned_bell, smoked_mereperch, pearl_of_the_mere, scaled_leggings,
									 boar_tusk, boar_hide, brigand_armband, garricks_ledger, straw_heart, loaf_of_bread, harvest_band,
									 ram_horn, ram_fleece, sunhawk_feather, sunstone_shard, linen_wrappings, pilgrim_token, cult_sigil,
									 sun_scarab, hierophants_mask, dawn_tusk_pendant, chitin_plate, scorpion_stinger, queens_stinger,
									 bleached_bone, salt_crystal, raider_scarf, raider_warhorn, titans_heart, bone_talisman,
									 river_trout, mud_carp, lagoon_snapper, monsoon_eel, jungle_catfish, rainbow_koi, tattered_boot, troll_tusk,
									 frog_skin, croc_hide, croc_tooth, elemental_essence, gorraks_crown, heart_of_the_storm, graveljaws_tooth, tide_trunk_charm] + TRADESKILLS}


# ---------------------------------------------------------------- rendering

def load_items():
	items = {}
	for path in sorted(glob.glob(os.path.join(ROOT, "data/items/*.json"))):
		items.update(json.load(open(path)))
	return items


def _body_parts(look, models):
	"""Imports a KayKit character and keeps only the parts a wearable swaps in,
	tinted as the game tints them."""
	entry = models["characters"][look["model"]]
	bpy.ops.import_scene.gltf(filepath=_res(entry["path"] if isinstance(entry, dict) else entry))
	parts = look["parts"]
	if all("Arm" in n for n in parts):
		parts = [n for n in parts if n.endswith("ArmLeft")]  # one arm, hung straight down, reads better than a T-pose pair
	for o in list(bpy.context.scene.objects):
		if o.type == "MESH" and o.name not in parts:
			bpy.data.objects.remove(o, do_unlink=True)
	if parts != look["parts"]:
		for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
			world = o.matrix_world.copy()
			o.parent = None
			for m in [m for m in o.modifiers if m.type == "ARMATURE"]:
				o.modifiers.remove(m)
			o.matrix_world = Matrix.Rotation(math.radians(90), 4, "Y") @ world
	if "tint" not in look:
		return
	tint = [int(look["tint"][i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
	for o in bpy.context.scene.objects:
		if o.type != "MESH":
			continue
		for slot in o.material_slots:
			mat = slot.material.copy()
			slot.material = mat
			nodes, links = mat.node_tree.nodes, mat.node_tree.links
			bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
			src = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].links else None
			mix = nodes.new("ShaderNodeMix")
			mix.data_type = "RGBA"
			mix.blend_type = "MULTIPLY"
			mix.inputs["Factor"].default_value = 1.0
			if src:
				links.new(src, mix.inputs["A"])
			mix.inputs["B"].default_value = tint + [1.0]
			links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])


def build_subject(item_id, item, models):
	"""Puts the item's model in the (empty) scene; False if there is none."""
	wear = item.get("wear", "")
	if item_id in SMALL and wear != "":  # a drawn icon beats the body part (KayKit legs are mostly boots)
		SMALL[item_id]()
		return True
	if wear in models.get("body_parts", {}):
		_body_parts(models["body_parts"][wear], models)
		return True
	if wear:
		for piece in gear.OUTFITS.get(wear, []):
			gear._build_piece(piece)
		return True
	if item.get("model") and item["model"] in models["weapons"]:
		bpy.ops.import_scene.gltf(filepath=_res(models["weapons"][item["model"]]))
		return True
	if item_id in SMALL:
		SMALL[item_id]()
		return True
	return False


def render_icon(path, size):
	scene = bpy.context.scene
	meshes = [o for o in scene.objects if o.type == "MESH"]
	lo = Vector((1e9, 1e9, 1e9))
	hi = Vector((-1e9, -1e9, -1e9))
	for o in meshes:
		for c in o.bound_box:
			w = o.matrix_world @ Vector(c)
			lo = Vector((min(lo[i], w[i]) for i in range(3)))
			hi = Vector((max(hi[i], w[i]) for i in range(3)))
	center = (lo + hi) / 2
	span = max((hi - lo).length, 0.01)
	scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
	scene.render.resolution_x = scene.render.resolution_y = size
	scene.render.film_transparent = True
	scene.view_settings.view_transform = "Standard"
	world = bpy.data.worlds.new("w")
	world.use_nodes = True
	world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.82, 0.88, 1)
	world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
	scene.world = world
	sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
	sun.data.energy = 3.5
	sun.rotation_euler = (math.radians(40), math.radians(-20), math.radians(-35))
	bpy.context.collection.objects.link(sun)
	cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
	cam.data.type = "ORTHO"
	cam.data.ortho_scale = span * 0.95
	bpy.context.collection.objects.link(cam)
	direction = Vector((0.55, -1.0, 0.6)).normalized()
	cam.location = center + direction * span * 3
	cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
	scene.camera = cam
	scene.render.filepath = path
	bpy.ops.render.render(write_still=True)


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	opts = {"--out": "assets/icons", "--only": "", "--size": "128"}
	for i, a in enumerate(argv):
		if a in opts and i + 1 < len(argv):
			opts[a] = argv[i + 1]
	os.makedirs(opts["--out"], exist_ok=True)
	only = set(opts["--only"].split(",")) if opts["--only"] else None
	models = json.load(open(os.path.join(ROOT, "data/models.json")))
	missing = []
	for item_id, item in load_items().items():
		if only and item_id not in only:
			continue
		props.reset_scene()
		props._materials.clear()
		if not build_subject(item_id, item, models):
			missing.append(item_id)
			continue
		render_icon(os.path.abspath(os.path.join(opts["--out"], item_id + ".png")), int(opts["--size"]))
		print("icon %s" % item_id)
	if missing:
		print("NO ICON (add a model): %s" % ", ".join(missing))


if __name__ == "__main__":
	main()
