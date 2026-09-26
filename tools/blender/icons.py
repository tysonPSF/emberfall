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
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import gear  # noqa: E402
import props  # noqa: E402
from props import (BONE, CLOTH_RED, CLOTH_WHITE, EMBER, GOLD, HIDE, IRON, LEAF, Prop, RUNE, STONE_DARK, WATER,  # noqa: E402
				   STONE_LIGHT, WOOD, WOOD_GRAY)

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


SMALL = {f.__name__: f for f in [gnoll_fang, beetle_eye, bone_chips, rat_whiskers, fishing_bait, bone_charm,
								 fang_necklace, tarnished_ring, copper_band, bonecarved_talisman, small_sack,
								 worn_backpack, gnollhide_satchel, leather_backpack, braided_whisker_cord, blackpaw_pelt,
									 stitched_blackpaw_hide, tovins_trail_pack, crude_arrow, sling_stone, leather_sling,
									 patchwork_pants, leather_leggings, iron_greaves, wolf_pelt, dire_wolf_fang, bear_claw,
									 bear_hide, spider_silk, venom_sac, orc_tusk, hollow_watch_signet,
									 mire_toad_skin, leech_teeth, turtle_shell_plate, mirescale_scale, waterlogged_locket,
									 snapjaws_shell, drowned_bell, smoked_mereperch, pearl_of_the_mere, scaled_leggings]}


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
