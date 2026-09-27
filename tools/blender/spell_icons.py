"""Renders the hotbar icons: one per spell and ability (assets/icons/spell_<id>.png)
and one per hotbar action (assets/icons/action_<name>.png).

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/blender/spell_icons.py -- --out assets/icons [--only kick,gate] [--size 128]

Same camera, light and Dungeon palette as the item icons (icons.py), so the
hotbar and the bags read as one set. Magic glows (Prop's `glow`); the HUD puts
each icon on a gem colored by what the spell does, so shapes carry the meaning
and color carries the kind.
"""

import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import icons  # noqa: E402
import props  # noqa: E402
from props import (BONE, CLOTH_RED, CLOTH_WHITE, EMBER, FLAME, GOLD, HIDE, IRON, LEAF, Prop, RUNE,  # noqa: E402
				   PINE, STONE_DARK, STONE_LIGHT, STONE_WARM, WATER, WOOD, WOOD_GRAY)


def _ring(p, radius, z, r, swatch, glow=0.0, sides=18, tilt=0.0):
	for k in range(sides):
		a0, a1 = k * math.tau / sides, (k + 1) * math.tau / sides
		pt = lambda a: (math.cos(a) * radius, math.sin(a) * radius * math.cos(tilt), z + math.sin(a) * radius * math.sin(tilt))
		p.seg(pt(a0), pt(a1), r, r, swatch, sides=5, glow=glow)


def _import(path, rot=(0, 0, 0), loc=(0, 0, 0)):
	before = set(bpy.data.objects)
	bpy.ops.import_scene.gltf(filepath=icons._res(path))
	for o in set(bpy.data.objects) - before:
		if o.parent is None:
			o.rotation_mode = "XYZ"
			o.rotation_euler = [math.radians(a) for a in rot]
			o.location = loc


# ---------------------------------------------------------------- warrior abilities

def kick():
	p = Prop("kick", 301)
	p.seg((0, 0, 0.9), (0, 0, 0.25), 0.2, 0.22, HIDE, sides=8)                     # shaft
	p.blob((0.62, 0.34, 0.3), (0.2, 0, 0.15), HIDE, segs=(10, 6))                   # foot
	p.seg((0, 0, 0.9), (0, 0, 0.98), 0.23, 0.23, WOOD, sides=8)                     # cuff
	for k in range(3):                                                             # motion lines
		p.seg((-0.35, 0.2, 0.2 + k * 0.22), (-0.8, 0.2, 0.25 + k * 0.22), 0.03, 0.0, CLOTH_WHITE, sides=4)
	return p.build()


def taunt():
	p = Prop("taunt", 303)
	p.box((0.22, 0.2, 0.75), (0, 0, 0.62), CLOTH_RED, glow=1.6)                    # an angry "!"
	p.blob((0.26, 0.24, 0.26), (0, 0, 0.05), CLOTH_RED, segs=(8, 6), glow=1.6)
	for x in (-1, 1):                                                              # shouted at, from both sides
		for k in range(3):
			a = math.radians(-30 + k * 30)
			p.seg((x * 0.3, 0, 0.6 + math.sin(a) * 0.2), (x * (0.3 + math.cos(a) * 0.35), 0, 0.6 + math.sin(a) * 0.55), 0.04, 0.0, FLAME, sides=4, glow=1.4)
	return p.build()


def bash():
	p = Prop("bash", 305)
	p.seg((0, 0, 0.55), (0, -0.12, 0.55), 0.62, 0.62, WOOD, sides=20)              # a round shield, face on
	_ring(p, 0.62, 0.55, 0.06, IRON, sides=20, tilt=math.pi / 2)
	p.blob((0.3, 0.2, 0.3), (0, -0.15, 0.55), IRON, segs=(10, 6))                  # boss
	for k in range(6):                                                             # the impact, off its edge
		a = k * math.tau / 6 + 0.3
		p.seg((0.62, -0.2, 0.95), (0.62 + math.cos(a) * 0.4, -0.2, 0.95 + math.sin(a) * 0.4), 0.06, 0.0, FLAME, sides=4, glow=1.5)
	return p.build()


def bind_wound():
	p = Prop("bind_wound", 307)
	p.seg((0, 0, 0), (0, 0, 0.45), 0.4, 0.4, CLOTH_WHITE, sides=16, grad=(0.0, 0.5))  # a roll of bandage, standing
	p.seg((0, 0, 0.44), (0, 0, 0.47), 0.13, 0.13, WOOD_GRAY, sides=10)
	p.box((0.35, 0.1, 0.02), (0.18, -0.36, 0.47), CLOTH_RED)                        # red cross on the end
	p.box((0.1, 0.35, 0.02), (0.18, -0.36, 0.47), CLOTH_RED)
	p.box((0.5, 0.02, 0.4), (0.3, -0.4, 0.2), CLOTH_WHITE, rot=(0, 0, 25))          # the loose end unwinding
	return p.build()


def battle_cry():
	p = Prop("battle_cry", 309)
	pts = [(math.cos(t) * 0.55, 0, 0.35 + math.sin(t) * 0.35) for t in [i * math.pi / 6 for i in range(-1, 6)]]
	for i, (a, b) in enumerate(zip(pts, pts[1:])):                                 # curved horn, widening to the bell
		p.seg(a, b, 0.06 + i * 0.04, 0.1 + i * 0.04, BONE, sides=10)
	for i in (1, 3):
		p.blob((0.2 + i * 0.07, 0.2 + i * 0.07, 0.08), pts[i], GOLD, segs=(10, 4))
	for k in range(3):                                                             # the sound
		_ring(p, 0.2 + k * 0.18, 0.15, 0.025, FLAME, glow=1.2, sides=10, tilt=math.pi / 2)
	return p.build()


# ---------------------------------------------------------------- healing

def _cross(p, s, swatch, glow):
	p.box((0.22 * s, 0.2 * s, 0.8 * s), (0, 0, 0.4 * s), swatch, glow=glow)
	p.box((0.62 * s, 0.2 * s, 0.22 * s), (0, 0, 0.5 * s), swatch, glow=glow)


def minor_healing():
	p = Prop("minor_healing", 311)
	for x in (-1, 1):                                                              # two leaves around a light
		p.blob((0.28, 0.08, 0.6), (x * 0.25, 0, 0.4), LEAF, rot=(0, x * 35, 0), segs=(8, 6), glow=0.6)
	p.blob((0.3, 0.3, 0.3), (0, 0, 0.3), GOLD, segs=(10, 8), glow=2.0)
	return p.build()


def light_healing():
	p = Prop("light_healing", 313)
	_cross(p, 1.0, GOLD, 1.8)
	_ring(p, 0.55, 0.45, 0.03, LEAF, glow=1.5, tilt=math.pi / 2)
	return p.build()


def circle_of_mending():
	p = Prop("circle_of_mending", 315)
	for k in range(6):
		a = k * math.tau / 6
		p.blob((0.22, 0.22, 0.22), (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.12), LEAF, segs=(8, 6), glow=1.8)
	_ring(p, 0.6, 0.12, 0.035, GOLD, glow=1.2)
	_cross(p, 0.55, GOLD, 1.6)
	return p.build()


# ---------------------------------------------------------------- damage

def _mace(p, swatch, glow):
	p.seg((0, 0, 0), (0, 0, 0.75), 0.05, 0.05, WOOD, sides=6)
	p.blob((0.34, 0.34, 0.38), (0, 0, 0.88), swatch, segs=(8, 6), glow=glow)
	for k in range(6):
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.14, math.sin(a) * 0.14, 0.88), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.88), 0.06, 0.0, swatch, sides=4, glow=glow)


def strike():
	p = Prop("strike", 317)
	_mace(p, IRON, 0.0)
	for k in range(4):                                                             # a flash where it lands
		a = k * math.tau / 4 + 0.4
		p.seg((0, 0, 0.88), (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.88 + 0.25), 0.05, 0.0, GOLD, sides=4, glow=1.6)
	return p.build()


def smite():
	p = Prop("smite", 319)
	_mace(p, GOLD, 1.4)
	for k in range(10):                                                            # sunburst
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.3, -0.05, 0.88 + math.sin(a) * 0.3), (math.cos(a) * 0.8, -0.05, 0.88 + math.sin(a) * 0.8), 0.05, 0.0, FLAME, sides=4, glow=2.0)
	return p.build()


def blast_of_frost():
	p = Prop("blast_of_frost", 321)
	for k, (x, y, h, lean) in enumerate([(0, 0, 1.0, 0), (0.28, 0.1, 0.7, 20), (-0.26, 0.05, 0.75, -22), (0.1, -0.25, 0.55, 12), (-0.1, 0.28, 0.6, -10)]):
		top = (x + math.sin(math.radians(lean)) * h, y, math.cos(math.radians(lean)) * h)
		p.seg((x, y, 0), top, 0.14, 0.0, WATER, sides=5, glow=1.2)
	return p.build()


def fire_bolt():
	p = Prop("fire_bolt", 323)
	p.blob((0.36, 0.36, 0.36), (0.45, 0, 0.5), FLAME, segs=(10, 8), glow=2.5)       # the head
	p.seg((0.45, 0, 0.5), (-0.7, 0, 0.35), 0.2, 0.0, EMBER, sides=8, glow=1.8)       # the tail
	p.seg((0.3, 0.05, 0.6), (-0.4, 0.1, 0.62), 0.08, 0.0, FLAME, sides=5, glow=2.0)
	return p.build()


def burning_embers():
	p = Prop("burning_embers", 325)
	for k in range(7):
		a = k * 2.4
		p.rock((0.3, 0.26, 0.2), (math.cos(a) * 0.3 * (k % 3), math.sin(a) * 0.3 * (k % 3), 0.1 + (0.12 if k == 0 else 0)), STONE_DARK, jitter=0.1)
	for k in range(5):
		a = k * 1.3
		p.blob((0.12, 0.12, 0.12), (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.28 + k * 0.05), EMBER, segs=(6, 4), glow=3.0)
	for k in range(3):                                                             # little flames
		a = k * 2.1
		p.seg((math.cos(a) * 0.2, math.sin(a) * 0.2, 0.2), (math.cos(a) * 0.25, math.sin(a) * 0.25, 0.7 + k * 0.1), 0.1, 0.0, FLAME, sides=5, glow=2.2)
	return p.build()


# ---------------------------------------------------------------- utility

def gate():
	p = Prop("gate", 327)
	_ring(p, 0.6, 0.65, 0.08, RUNE, glow=2.0, sides=22, tilt=math.pi / 2)
	for k in range(3):                                                             # the swirl inside
		_ring(p, 0.42 - k * 0.12, 0.65, 0.03, WATER, glow=1.5, sides=14, tilt=math.pi / 2)
	p.box((1.2, 0.5, 0.1), (0, 0, 0.0), STONE_LIGHT)                                # standing stone base
	return p.build()


def homeward():
	p = Prop("homeward", 649)
	_ring(p, 0.62, 0.62, 0.07, GOLD, glow=2.0, sides=22, tilt=math.pi / 2)
	p.box((0.44, 0.3, 0.32), (0, 0, 0.5), STONE_WARM)                                  # a little house in the ring
	p.poly([(-0.3, -0.16, 0.66), (0.3, -0.16, 0.66), (0.3, 0.16, 0.66), (-0.3, 0.16, 0.66), (0, -0.16, 0.9), (0, 0.16, 0.9)],
		   [(0, 1, 4), (3, 2, 5), (0, 4, 5, 3), (1, 2, 5, 4)], CLOTH_RED)
	p.box((0.1, 0.02, 0.14), (0, -0.16, 0.45), FLAME, glow=2.5)                       # its lit door
	return p.build()

def root():
	p = Prop("root", 329)
	p.seg((0, 0, 0), (0, 0, 0.02), 0.7, 0.7, LEAF, sides=16)                        # ground
	for k in range(5):
		a = k * math.tau / 5
		pts = [(math.cos(a + t * 0.6) * (0.5 - t * 0.12), math.sin(a + t * 0.6) * (0.5 - t * 0.12), t * 0.22) for t in range(5)]
		for i, (b, c) in enumerate(zip(pts, pts[1:])):
			p.seg(b, c, 0.09 - i * 0.015, 0.075 - i * 0.015, WOOD, sides=6)
	return p.build()


def minor_shielding():
	p = Prop("minor_shielding", 331)
	p.box((0.8, 0.12, 0.95), (0, 0, 0.5), RUNE, glow=1.2)                          # a shield of light
	p.seg((0, -0.07, 0.05), (0, -0.07, 0.03), 0.4, 0.0, RUNE, sides=4, glow=1.2)
	p.seg((0, 0, 0.0), (0, 0, -0.3), 0.4, 0.0, RUNE, sides=4, glow=1.2)            # pointed foot
	p.box((0.1, 0.05, 0.6), (0, -0.09, 0.5), GOLD, glow=1.0)
	p.box((0.45, 0.05, 0.1), (0, -0.09, 0.6), GOLD, glow=1.0)
	return p.build()


def courage():
	p = Prop("courage", 333)
	p.seg((0, 0, 0.1), (0, 0, 1.0), 0.07, 0.02, IRON, sides=4, glow=0.4)            # an upright blade
	p.box((0.5, 0.1, 0.08), (0, 0, 0.12), GOLD)
	p.seg((0, 0, 0.12), (0, 0, -0.2), 0.05, 0.05, WOOD, sides=6)
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.15, -0.1, 0.6 + math.sin(a) * 0.15), (math.cos(a) * 0.55, -0.1, 0.6 + math.sin(a) * 0.55), 0.04, 0.0, FLAME, sides=4, glow=1.8)
	return p.build()


def hearthward():
	p = Prop("hearthward", 335)
	p.box((0.8, 0.6, 0.55), (0, 0, 0.28), STONE_LIGHT)                             # a little house
	p.poly([(-0.5, -0.35, 0.55), (0.5, -0.35, 0.55), (0.5, 0.35, 0.55), (-0.5, 0.35, 0.55), (0, -0.35, 0.95), (0, 0.35, 0.95)],
		   [(0, 1, 4), (3, 2, 5), (0, 4, 5, 3), (1, 2, 5, 4)], CLOTH_RED)
	p.box((0.22, 0.02, 0.22), (0, -0.31, 0.25), FLAME, glow=2.5)                   # the hearth's light
	_ring(p, 0.72, 0.4, 0.03, GOLD, glow=1.4, sides=20)
	return p.build()


def hearthbond():
	p = Prop("hearthbond", 337)
	_ring(p, 0.35, 0.45, 0.07, GOLD, glow=0.8, tilt=math.pi / 2)
	for k in range(18):                                                            # a second ring through the first
		a0, a1 = k * math.tau / 18, (k + 1) * math.tau / 18
		pt = lambda a: (0.4 + math.cos(a) * 0.35, math.sin(a) * 0.35, 0.45)
		p.seg(pt(a0), pt(a1), 0.07, 0.07, GOLD, sides=5, glow=0.8)
	p.blob((0.25, 0.25, 0.25), (0.2, 0, 0.45), EMBER, segs=(8, 6), glow=2.5)
	return p.build()


def blessing_of_the_elders():
	p = Prop("blessing_of_the_elders", 351)
	for s in (-1, 1):                               # a pair of tusks curving up, like the elephant gods'
		pts = [(s * 0.35, 0, 0.05), (s * 0.42, 0, 0.4), (s * 0.36, 0, 0.72), (s * 0.18, 0, 0.98)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.14 - i * 0.035, 0.1 - i * 0.03, GOLD, sides=8, glow=0.8)
	p.blob((0.34, 0.34, 0.34), (0, 0, 0.5), FLAME, segs=(10, 8), glow=2.5)   # the light between them
	_ring(p, 0.62, 0.45, 0.03, GOLD, glow=1.2, sides=20, tilt=math.pi / 2)
	return p.build()


# ---------------------------------------------------------------- levels 11-15

def _sword(p, glow=0.0, swatch=IRON):
	p.seg((0, 0, 0.25), (0, 0, 1.15), 0.07, 0.015, swatch, sides=4, glow=glow)       # blade
	p.box((0.46, 0.1, 0.08), (0, 0, 0.24), GOLD)                                     # guard
	p.seg((0, 0, 0.22), (0, 0, -0.1), 0.045, 0.045, WOOD, sides=6)                   # grip
	p.blob((0.1, 0.1, 0.1), (0, 0, -0.13), GOLD, segs=(6, 4))


def heroic_strike():
	p = Prop("heroic_strike", 361)
	_sword(p, glow=0.4)
	for k in range(7):                                                            # the swing's arc
		a = math.radians(200 + k * 20)
		p.seg((math.cos(a) * 0.7, -0.1, 0.65 + math.sin(a) * 0.7), (math.cos(a + 0.3) * 0.7, -0.1, 0.65 + math.sin(a + 0.3) * 0.7),
			  0.05 - k * 0.005, 0.04 - k * 0.005, FLAME, sides=4, glow=1.6)
	return p.build()


def rally():
	p = Prop("rally", 363)
	p.seg((0, 0, 0), (0, 0, 1.2), 0.04, 0.035, WOOD, sides=6)                       # a war banner
	p.box((0.62, 0.05, 0.62), (0.33, 0, 0.84), CLOTH_RED, grad=(0.1, 0.6))
	p.poly([(0.02, 0, 0.53), (0.64, 0, 0.53), (0.33, 0, 0.3)], [(0, 1, 2)], CLOTH_RED)
	p.box((0.18, 0.06, 0.18), (0.33, -0.03, 0.86), GOLD, glow=0.8)
	for k in range(3):
		_ring(p, 0.25 + k * 0.18, 0.2, 0.025, FLAME, glow=1.2, sides=12, tilt=math.pi / 2)
	return p.build()


def shield_wall():
	p = Prop("shield_wall", 365)
	for x, y in ((-0.28, 0.1), (0.28, 0.1), (0.0, -0.1)):                             # shields locked edge to edge
		p.seg((x, y, 0.5), (x, y - 0.1, 0.5), 0.34, 0.34, WOOD, sides=14)
		p.blob((0.14, 0.08, 0.14), (x, y - 0.13, 0.5), IRON, segs=(8, 5))
	p.box((1.3, 0.05, 1.2), (0, 0.2, 0.55), RUNE, glow=0.6, grad=(0.3, 0.6))            # the ward behind
	return p.build()


def healing():
	p = Prop("healing", 367)
	_cross(p, 1.1, GOLD, 2.2)
	for k in range(6):
		a = k * math.tau / 6
		p.blob((0.16, 0.16, 0.16), (math.cos(a) * 0.55, 0, 0.5 + math.sin(a) * 0.55), LEAF, segs=(6, 4), glow=1.8)
	return p.build()


def blessed_armor():
	p = Prop("blessed_armor", 369)
	p.blob((0.8, 0.45, 0.9), (0, 0, 0.45), GOLD, segs=(12, 8), glow=0.4)               # a breastplate
	p.box((0.08, 0.05, 0.7), (0, -0.23, 0.48), STONE_LIGHT, glow=0.6)
	for s in (-1, 1):
		p.blob((0.34, 0.3, 0.2), (s * 0.44, 0, 0.85), GOLD, segs=(8, 5))              # pauldrons
	_ring(p, 0.7, 0.45, 0.03, FLAME, glow=1.6, sides=20, tilt=math.pi / 2)
	return p.build()


def circle_of_renewal():
	p = Prop("circle_of_renewal", 371)
	_ring(p, 0.66, 0.12, 0.05, LEAF, glow=1.4, sides=22)
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.66, math.sin(a) * 0.66, 0.12), (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.9), 0.05, 0.0, LEAF, sides=4, glow=1.8)
	_cross(p, 0.5, GOLD, 2.0)
	return p.build()


def hallowed_strike():
	p = Prop("hallowed_strike", 373)
	p.seg((0, 0, 0), (0, 0, 0.8), 0.05, 0.05, WOOD, sides=6)                           # a hammer
	p.box((0.62, 0.3, 0.3), (0, 0, 0.9), GOLD, glow=1.2)
	for k in range(12):
		a = k * math.tau / 12
		p.seg((math.cos(a) * 0.35, -0.1, 0.9 + math.sin(a) * 0.35), (math.cos(a) * 0.8, -0.1, 0.9 + math.sin(a) * 0.8), 0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.2)
	return p.build()


def frost_lance():
	p = Prop("frost_lance", 375)
	p.seg((-0.7, 0, 0.1), (0.75, 0, 1.0), 0.13, 0.0, WATER, sides=6, glow=1.4)
	for k in range(4):
		t = 0.15 + k * 0.2
		x, z = -0.7 + t * 1.45, 0.1 + t * 0.9
		p.seg((x, 0, z), (x - 0.18, 0.1 * (k % 2 * 2 - 1), z + 0.2), 0.05, 0.0, WATER, sides=4, glow=1.0)
	return p.build()


def emberstorm():
	p = Prop("emberstorm", 377)
	for k in range(26):                                                           # a spiral of embers
		t = k / 26
		a = t * math.tau * 2.2
		r = 0.2 + t * 0.55
		p.blob((0.12, 0.12, 0.12), (math.cos(a) * r, math.sin(a) * r, 0.1 + t * 0.9), EMBER if k % 3 else FLAME, segs=(6, 4), glow=2.6)
	return p.build()


def greater_shielding():
	p = Prop("greater_shielding", 379)
	p.blob((1.2, 1.2, 1.1), (0, 0, 0.0), RUNE, segs=(14, 8), glow=1.0, grad=(0.2, 0.5))   # a dome of force
	p.box((0.12, 0.1, 0.8), (0, -0.62, 0.3), GOLD, glow=1.4)
	p.box((0.55, 0.1, 0.12), (0, -0.62, 0.45), GOLD, glow=1.4)
	return p.build()


def ice_comet():
	p = Prop("ice_comet", 381)
	p.blob((0.55, 0.55, 0.55), (0.45, 0, 0.35), WATER, segs=(12, 8), glow=1.8)
	for k, (dy, dz) in enumerate(((0, 0), (0.12, 0.1), (-0.1, -0.08))):
		p.seg((0.45, dy, 0.35 + dz), (-0.8, dy * 2, 1.05 + dz), 0.22 - k * 0.05, 0.0, CLOTH_WHITE, sides=6, glow=1.2)
	return p.build()


# ---------------------------------------------------------------- monsters' (shown as debuffs)

def thornback_venom():
	p = Prop("thornback_venom", 391)
	p.seg((0, 0, 1.0), (0, 0, 0.35), 0.2, 0.05, STONE_DARK, sides=6)                  # a fang
	for k in range(3):                                                            # dripping venom
		z = 0.25 - k * 0.3
		p.blob((0.16 - k * 0.02, 0.16 - k * 0.02, 0.24 - k * 0.03), (0.02 * k, 0, z), LEAF, segs=(8, 6), glow=1.8)
	_ring(p, 0.55, 0.55, 0.03, LEAF, glow=1.0, sides=16, tilt=math.pi / 2)
	return p.build()


def grave_chill():
	p = Prop("grave_chill", 393)
	p.blob((0.55, 0.5, 0.55), (0, 0, 0.55), BONE, segs=(10, 8))                     # a skull
	for s in (-1, 1):
		p.blob((0.14, 0.08, 0.14), (s * 0.13, -0.24, 0.58), WATER, segs=(6, 4), glow=2.0)
	for k in range(6):                                                            # frost around it
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.35, 0, 0.55 + math.sin(a) * 0.35), (math.cos(a) * 0.7, 0, 0.55 + math.sin(a) * 0.7), 0.06, 0.0, WATER, sides=4, glow=1.2)
	return p.build()


def spirit_bolt():
	p = Prop("spirit_bolt", 395)
	for k in range(3):
		t = k / 3
		p.blob((0.3 - k * 0.07, 0.3 - k * 0.07, 0.3 - k * 0.07), (0.4 - t * 0.9, 0, 0.55 + t * 0.2), LEAF, segs=(8, 6), glow=2.2 - k * 0.5)
	p.seg((0.4, 0, 0.55), (-0.7, 0, 0.85), 0.14, 0.0, CLOTH_WHITE, sides=6, glow=1.4)
	return p.build()


def leech_bite():
	p = Prop("leech_bite", 397)
	_ring(p, 0.45, 0.55, 0.12, CLOTH_RED, sides=14, tilt=math.pi / 2)            # the sucker
	for k in range(9):                                                            # its teeth
		a = k * math.tau / 9
		p.seg((math.cos(a) * 0.38, 0, 0.55 + math.sin(a) * 0.38), (math.cos(a) * 0.16, -0.05, 0.55 + math.sin(a) * 0.16), 0.06, 0.0, BONE, sides=4)
	for k in range(3):                                                            # blood
		p.blob((0.12, 0.12, 0.18), (0.1 * k - 0.1, 0, 0.05 - k * 0.12), CLOTH_RED, segs=(8, 6), glow=1.2)
	return p.build()


def marsh_bolt():
	p = Prop("marsh_bolt", 399)
	for k in range(4):
		t = k / 4
		p.blob((0.34 - k * 0.07,) * 3, (0.45 - t * 1.0, 0, 0.5 + t * 0.25), LEAF, segs=(8, 6), glow=1.6 - k * 0.3)
	for k in range(5):                                                            # stinking bubbles
		p.blob((0.1, 0.1, 0.1), (0.3 - k * 0.2, 0, 0.85 + (k % 2) * 0.12), WOOD_GRAY, segs=(6, 4))
	return p.build()


def drowning_cold():
	p = Prop("drowning_cold", 401)
	p.blob((0.5, 0.46, 0.5), (0, 0, 0.62), BONE, segs=(10, 8))                     # a skull
	for s_ in (-1, 1):
		p.blob((0.12, 0.08, 0.12), (s_ * 0.12, -0.22, 0.64), WATER, segs=(6, 4), glow=2.0)
	p.box((1.4, 1.4, 0.5), (0, 0, 0.25), WATER, glow=0.6)                          # the water rising over it
	for k in range(4):                                                            # bubbles
		p.blob((0.1, 0.1, 0.1), (0.3 - k * 0.15, -0.3, 0.95 + k * 0.12), WATER, segs=(6, 4), glow=1.0)
	return p.build()


def backstab():
	p = Prop("backstab", 403)
	p.seg((0.45, 0, 1.0), (-0.25, 0, 0.25), 0.07, 0.0, STONE_LIGHT, sides=4, glow=0.4)     # a dagger driving down
	p.box((0.36, 0.1, 0.08), (0.48, 0, 1.02), GOLD, rot=(0, 45, 0))                       # its guard
	p.seg((0.52, 0, 1.08), (0.72, 0, 1.28), 0.06, 0.05, WOOD, sides=6)                    # grip
	p.blob((0.9, 0.35, 0.7), (-0.2, 0.15, 0.2), CLOTH_RED, segs=(10, 6))                  # a back, struck
	return p.build()


def hide():
	p = Prop("hide", 405)
	p.blob((0.7, 0.6, 0.9), (0, 0, 0.55), STONE_DARK, segs=(10, 8), glow=0.0)             # a hooded shape
	p.blob((0.46, 0.3, 0.4), (0, -0.22, 0.7), IRON, segs=(8, 6))                          # the dark under the hood
	for s_ in (-1, 1):
		p.blob((0.08, 0.05, 0.05), (s_ * 0.1, -0.36, 0.72), LEAF, segs=(6, 4), glow=2.0)    # two eyes
	return p.build()


def sneak():
	p = Prop("sneak", 407)
	for k in range(3):                                                                    # soft footprints
		for s_ in (-1, 1):
			p.blob((0.2, 0.3, 0.05), (s_ * 0.2 + k * 0.05, -0.6 + k * 0.55 + (0.2 if s_ > 0 else 0), 0.05), STONE_LIGHT, segs=(8, 4), glow=0.3 - k * 0.1)
	return p.build()


def evade():
	p = Prop("evade", 409)
	for k in range(3):                                                                    # a figure fading out of a swirl
		p.blob((0.5 - k * 0.1, 0.3, 0.8 - k * 0.15), (-0.4 + k * 0.35, 0, 0.5), CLOTH_WHITE if k == 0 else STONE_LIGHT, segs=(8, 6), glow=0.6 - k * 0.2)
	_ring(p, 0.6, 0.5, 0.04, CLOTH_WHITE, glow=0.8, sides=16, tilt=math.pi / 2)
	return p.build()


def envenom_blade():
	p = Prop("envenom_blade", 411)
	p.seg((0, 0, 0.1), (0, 0, 1.1), 0.1, 0.0, STONE_LIGHT, sides=4)                       # a blade point up
	p.box((0.4, 0.1, 0.08), (0, 0, 0.1), GOLD)
	for k in range(4):                                                                    # green drips down it
		p.blob((0.1, 0.1, 0.16), (0.05 * (k % 2 * 2 - 1), 0, 0.9 - k * 0.2), LEAF, segs=(6, 4), glow=1.6)
	return p.build()


def rogue_venom():
	p = Prop("rogue_venom", 413)
	p.blob((0.55, 0.55, 0.7), (0, 0, 0.4), LEAF, segs=(10, 8), glow=1.2)                   # a vial of it
	p.seg((0, 0, 0.72), (0, 0, 0.95), 0.12, 0.12, STONE_LIGHT, sides=8)
	p.seg((0, 0, 0.95), (0, 0, 1.05), 0.14, 0.14, WOOD, sides=8)
	return p.build()


def rake():
	p = Prop("rake", 415)
	for k in range(3):                                                                    # three claw-slashes
		x = -0.3 + k * 0.3
		p.seg((x - 0.25, 0, 1.0), (x + 0.25, 0, 0.1), 0.06, 0.02, CLOTH_RED, sides=4, glow=1.2)
	return p.build()


# ---------------------------------------------------------------- levels 16-20

def provoke():
	p = Prop("provoke", 417)
	p.blob((0.5, 0.45, 0.55), (0, 0, 0.55), CLOTH_RED, segs=(10, 8), glow=0.8)            # a roaring face of red
	for k in range(3):
		_ring(p, 0.45 + k * 0.22, 0.55, 0.03, CLOTH_RED, glow=1.2 - k * 0.3, sides=16, tilt=math.pi / 2)
	return p.build()


def defensive_stance():
	p = Prop("defensive_stance", 419)
	p.blob((0.95, 0.25, 1.05), (0, 0, 0.55), IRON, segs=(12, 8))                         # a tower shield
	p.box((0.12, 0.3, 0.8), (0, -0.1, 0.55), STONE_LIGHT)
	p.box((0.6, 0.3, 0.12), (0, -0.1, 0.7), STONE_LIGHT)
	return p.build()


def cleave():
	p = Prop("cleave", 421)
	for k in range(5):                                                                    # a wide arc
		a0, a1 = math.radians(200 + k * 28), math.radians(228 + k * 28)
		p.seg((math.cos(a0) * 0.7, 0, 0.55 + math.sin(a0) * 0.7), (math.cos(a1) * 0.7, 0, 0.55 + math.sin(a1) * 0.7), 0.08, 0.08, GOLD, sides=4, glow=1.4)
	p.seg((0.2, 0, 0.1), (0.2, 0, 0.9), 0.05, 0.05, WOOD, sides=5)                        # an axe at the center
	p.blob((0.4, 0.08, 0.3), (0.38, 0, 0.8), IRON, segs=(8, 4))
	return p.build()


def greater_healing():
	p = Prop("greater_healing", 423)
	p.box((0.28, 0.1, 0.95), (0, 0, 0.55), GOLD, glow=1.8)                                 # a bright cross
	p.box((0.95, 0.1, 0.28), (0, 0, 0.6), GOLD, glow=1.8)
	_ring(p, 0.6, 0.58, 0.04, CLOTH_WHITE, glow=1.2, sides=18, tilt=math.pi / 2)
	return p.build()


def divine_aura():
	p = Prop("divine_aura", 425)
	p.blob((0.4, 0.3, 0.6), (0, 0, 0.5), CLOTH_WHITE, segs=(8, 6))                         # a figure
	p.blob((1.2, 1.2, 1.3), (0, 0, 0.55), GOLD, segs=(12, 8), glow=0.8)                    # in a golden shell
	return p.build()


def sunfire():
	p = Prop("sunfire", 427)
	p.blob((0.55, 0.55, 0.55), (0, 0, 0.6), GOLD, segs=(12, 8), glow=2.4)                  # a small sun
	for k in range(10):
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.38, 0, 0.6 + math.sin(a) * 0.38), (math.cos(a) * 0.75, 0, 0.6 + math.sin(a) * 0.75), 0.07, 0.0, EMBER, sides=4, glow=1.6)
	return p.build()


def lightning_bolt():
	p = Prop("lightning_bolt", 429)
	pts = [(0.3, 0, 1.1), (-0.05, 0, 0.7), (0.15, 0, 0.62), (-0.3, 0, 0.05)]
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.09, 0.07, CLOTH_WHITE, sides=5, glow=2.4)
	return p.build()


def frost_snare():
	p = Prop("frost_snare", 431)
	_ring(p, 0.5, 0.2, 0.08, WATER, glow=1.4, sides=16)                                   # a frost ring at the feet
	for k in range(6):                                                                    # ice spikes rising
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.45, math.sin(a) * 0.45, 0.1), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.75), 0.09, 0.0, WATER, sides=4, glow=1.0)
	return p.build()


def fireball():
	p = Prop("fireball", 433)
	p.blob((0.7, 0.7, 0.7), (0.15, 0, 0.7), EMBER, segs=(12, 8), glow=2.2)
	for k in range(4):                                                                    # its trail
		p.blob((0.35 - k * 0.07,) * 3, (-0.35 - k * 0.22, 0, 0.5 - k * 0.12), FLAME, segs=(8, 6), glow=1.6 - k * 0.3)
	return p.build()


def assassinate():
	p = Prop("assassinate", 435)
	p.seg((0.35, 0, 1.05), (-0.3, 0, 0.1), 0.08, 0.0, STONE_LIGHT, sides=4, glow=0.5)     # a blade plunging
	p.box((0.36, 0.1, 0.08), (0.38, 0, 1.08), CLOTH_RED, rot=(0, 45, 0))
	p.blob((0.1, 0.06, 0.1), (-0.05, 0, 0.35), CLOTH_RED, segs=(6, 4), glow=1.4)           # a drop of blood
	p.blob((0.08, 0.05, 0.08), (0.1, 0, 0.2), CLOTH_RED, segs=(6, 4), glow=1.4)
	return p.build()


def blind():
	p = Prop("blind", 437)
	p.blob((0.7, 0.3, 0.45), (0, 0, 0.6), CLOTH_WHITE, segs=(10, 6))                       # an eye...
	p.blob((0.25, 0.1, 0.25), (0, -0.14, 0.6), STONE_DARK, segs=(8, 6))
	for k in range(8):                                                                    # ...in a cloud of dust
		a = k * math.tau / 8
		p.blob((0.18, 0.18, 0.18), (math.cos(a) * 0.55, -0.1, 0.6 + math.sin(a) * 0.4), HIDE, segs=(6, 4))
	return p.build()


def deadly_poison():
	p = Prop("deadly_poison", 439)
	for s_ in (-1, 1):                                                                    # two blades crossed, dripping
		p.seg((s_ * 0.45, 0, 0.1), (-s_ * 0.3, 0, 1.0), 0.07, 0.0, STONE_LIGHT, sides=4)
	for k in range(5):
		p.blob((0.1, 0.1, 0.15), (0.2 * (k - 2) * 0.5, 0, 0.35 - (k % 2) * 0.1), LEAF, segs=(6, 4), glow=1.8)
	p.blob((0.3, 0.12, 0.3), (0, -0.1, 0.9), BONE, segs=(8, 5))                            # a small skull
	return p.build()


def deadly_venom():
	p = Prop("deadly_venom", 441)
	p.blob((0.6, 0.6, 0.75), (0, 0, 0.42), LEAF, segs=(10, 8), glow=1.6)
	p.seg((0, 0, 0.78), (0, 0, 1.0), 0.13, 0.13, STONE_LIGHT, sides=8)
	p.blob((0.3, 0.12, 0.3), (0, -0.28, 0.45), BONE, segs=(8, 5))
	return p.build()


def dawn_tusk_blessing():
	p = Prop("dawn_tusk_blessing", 443)
	p.blob((0.6, 0.5, 0.55), (0, 0, 0.4), STONE_LIGHT, segs=(10, 8))                      # an elephant's head
	for s_ in (-1, 1):
		p.blob((0.1, 0.35, 0.4), (s_ * 0.36, 0.05, 0.42), STONE_LIGHT, segs=(6, 5))        # ears
		p.seg((s_ * 0.12, -0.25, 0.25), (s_ * 0.2, -0.45, 0.15), 0.05, 0.02, BONE, sides=5)  # tusks
	p.seg((0, -0.3, 0.3), (0, -0.4, 0.85), 0.09, 0.06, STONE_LIGHT, sides=6)               # the trunk, raised
	p.seg((0, -0.42, 1.05), (0, -0.46, 1.05), 0.26, 0.26, GOLD, sides=14, glow=1.6)        # holding the sun
	return p.build()


# ---------------------------------------------------------------- The Bleach (monster spells)

def scorpion_venom():
	p = Prop("scorpion_venom", 445)
	pts = [(0.35, 0, 0.1), (0.45, 0, 0.55), (0.25, 0, 0.95), (-0.1, 0, 1.05)]            # a stinger's curve
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.14 - i * 0.03, 0.11 - i * 0.03, HIDE, sides=6)
	p.seg((-0.1, 0, 1.05), (-0.3, 0, 0.8), 0.05, 0.0, STONE_DARK, sides=5)
	p.blob((0.12, 0.12, 0.16), (-0.32, 0, 0.62), GOLD, segs=(6, 4), glow=1.8)             # a drop of venom
	return p.build()


def salt_gaze():
	p = Prop("salt_gaze", 447)
	p.blob((0.75, 0.3, 0.45), (0, 0, 0.6), CLOTH_WHITE, segs=(10, 6), glow=0.4)          # a pale reptile eye
	p.box((0.08, 0.1, 0.4), (0, -0.14, 0.6), STONE_DARK)
	for k in range(6):                                                                    # salt crystals round it
		a = k * math.tau / 6
		p.seg((math.cos(a) * 0.55, 0, 0.6 + math.sin(a) * 0.45), (math.cos(a) * 0.8, 0, 0.6 + math.sin(a) * 0.62), 0.07, 0.0, STONE_LIGHT, sides=4)
	return p.build()


# ---------------------------------------------------------------- levels 21-25

def shield_slam():
	p = Prop("shield_slam", 449)
	p.seg((0, 0.1, 0.55), (0, -0.05, 0.55), 0.45, 0.45, WOOD, sides=14)                   # a round shield
	p.blob((0.16, 0.1, 0.16), (0, -0.1, 0.55), IRON, segs=(8, 5))
	for k in range(5):                                                                    # stars of the stun
		a = k * math.tau / 5 + 0.3
		p.blob((0.09, 0.09, 0.09), (math.cos(a) * 0.62, -0.15, 1.02 + math.sin(a) * 0.12), GOLD, segs=(5, 4), glow=2.0)
	return p.build()


def battle_fury():
	p = Prop("battle_fury", 451)
	for s_ in (-1, 1):                                                                    # two blades in motion
		p.seg((s_ * 0.4, 0, 0.1), (-s_ * 0.2, 0, 1.0), 0.07, 0.0, IRON, sides=4)
	for k in range(4):                                                                    # speed lines of fire
		p.seg((-0.7, -0.1, 0.2 + k * 0.22), (-0.2, -0.1, 0.25 + k * 0.22), 0.04, 0.0, FLAME, sides=4, glow=1.8)
	p.blob((0.25, 0.2, 0.25), (0, -0.05, 0.55), CLOTH_RED, segs=(8, 5), glow=1.4)
	return p.build()


def whirlwind():
	p = Prop("whirlwind", 453)
	for k in range(4):                                                                    # a spiral of cuts
		_ring(p, 0.3 + k * 0.14, 0.2 + k * 0.22, 0.04, GOLD if k % 2 else CLOTH_WHITE, glow=1.4, sides=14)
	_sword(p, glow=0.4)
	return p.build()


def healing_tide():
	p = Prop("healing_tide", 455)
	for k in range(3):                                                                    # waves
		for j in range(6):
			x0, x1 = -0.75 + j * 0.25, -0.5 + j * 0.25
			z = 0.2 + k * 0.28
			p.seg((x0, 0, z + (0.08 if j % 2 else 0)), (x1, 0, z + (0 if j % 2 else 0.08)), 0.06, 0.06, WATER, sides=5, glow=1.0)
	_cross(p, 0.45, GOLD, 2.0)
	return p.build()


def word_of_awe():
	p = Prop("word_of_awe", 457)
	p.blob((0.3, 0.3, 0.3), (0, 0, 0.6), CLOTH_WHITE, segs=(8, 6), glow=2.6)               # a burst of holy light
	for k in range(12):
		a = k * math.tau / 12
		r1 = 0.8 if k % 2 else 0.55
		p.seg((math.cos(a) * 0.3, 0, 0.6 + math.sin(a) * 0.3), (math.cos(a) * r1, 0, 0.6 + math.sin(a) * r1), 0.06, 0.0, GOLD, sides=4, glow=1.8)
	return p.build()


def armor_of_faith():
	p = Prop("armor_of_faith", 459)
	p.blob((0.8, 0.45, 0.9), (0, 0, 0.45), STONE_LIGHT, segs=(12, 8), glow=0.3)           # a breastplate
	_cross(p, 0.45, GOLD, 1.8)
	for s_ in (-1, 1):
		p.blob((0.34, 0.3, 0.2), (s_ * 0.44, 0, 0.85), STONE_LIGHT, segs=(8, 5))
	_ring(p, 0.72, 0.45, 0.03, GOLD, glow=1.4, sides=20, tilt=math.pi / 2)
	return p.build()


def chain_lightning():
	p = Prop("chain_lightning", 461)
	for ox, oz, sc in ((0.0, 0.1, 1.0), (-0.5, 0.0, 0.6), (0.5, 0.05, 0.6)):               # a bolt forking to two more
		pts = [(ox + 0.25 * sc, 0, oz + 1.0 * sc), (ox - 0.05 * sc, 0, oz + 0.62 * sc), (ox + 0.12 * sc, 0, oz + 0.55 * sc), (ox - 0.25 * sc, 0, oz)]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.07 * sc + 0.02, 0.05 * sc + 0.02, CLOTH_WHITE, sides=5, glow=2.4)
	return p.build()


def arcane_harvest():
	p = Prop("arcane_harvest", 463)
	p.blob((0.3, 0.3, 0.3), (0, 0, 0.45), RUNE, segs=(10, 8), glow=2.2)                   # mana drawn inward
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.85, 0, 0.45 + math.sin(a) * 0.6), (math.cos(a) * 0.4, 0, 0.45 + math.sin(a) * 0.3), 0.0, 0.06, RUNE, sides=4, glow=1.6)
	return p.build()


def meteor():
	p = Prop("meteor", 465)
	p.blob((0.55, 0.5, 0.5), (-0.2, 0, 0.35), STONE_DARK, segs=(10, 8), jitter=0.06)       # a burning stone
	p.blob((0.45, 0.45, 0.45), (-0.15, -0.05, 0.4), EMBER, segs=(10, 8), glow=1.2)
	for k in range(4):                                                                    # plunging from high up
		p.blob((0.3 - k * 0.05,) * 3, (0.2 + k * 0.2, 0, 0.7 + k * 0.2), FLAME, segs=(8, 6), glow=1.8 - k * 0.3)
	return p.build()


def crippling_poison():
	p = Prop("crippling_poison", 467)
	p.seg((0.35, 0, 0.1), (-0.3, 0, 1.0), 0.08, 0.0, STONE_LIGHT, sides=4)                 # a blade...
	for k in range(4):                                                                    # ...dripping pale green
		p.blob((0.09, 0.09, 0.13), (0.1 - k * 0.1, -0.05, 0.4 + k * 0.12), WATER, segs=(6, 4), glow=1.6)
	_ring(p, 0.35, 0.08, 0.05, WATER, glow=1.2, sides=12)                                 # binding the feet
	return p.build()


def crippling_venom():
	p = Prop("crippling_venom", 469)
	_ring(p, 0.5, 0.15, 0.08, WATER, glow=1.4, sides=16)
	p.blob((0.4, 0.4, 0.5), (0, 0, 0.55), WATER, segs=(10, 8), glow=1.2)
	return p.build()


def eviscerate():
	p = Prop("eviscerate", 471)
	for k in range(3):                                                                    # three raking slashes
		p.seg((-0.5 + k * 0.3, 0, 1.0), (-0.1 + k * 0.3, 0, 0.1), 0.06, 0.02, CLOTH_RED, sides=4, glow=1.6)
	p.seg((0.5, 0, 0.9), (0.2, 0, 0.3), 0.06, 0.0, STONE_LIGHT, sides=4)
	return p.build()


def vanish():
	p = Prop("vanish", 473)
	for k in range(6):                                                                    # a hood fading to smoke
		p.blob((0.45 - k * 0.05, 0.35 - k * 0.04, 0.3), (0, 0, 0.3 + k * 0.15), STONE_DARK, segs=(8, 6))
	for k in range(6):
		a = k * math.tau / 6
		p.blob((0.12, 0.12, 0.12), (math.cos(a) * 0.6, 0, 0.7 + math.sin(a) * 0.35), RUNE, segs=(6, 4), glow=1.2)
	return p.build()


# ---------------------------------------------------------------- the Long Monsoon

def storm_bolt():
	p = Prop("storm_bolt", 475)
	p.blob((0.9, 0.5, 0.35), (0, 0, 1.0), STONE_DARK, segs=(10, 6))                        # a storm cloud
	pts = [(0.15, 0, 0.85), (-0.1, 0, 0.5), (0.1, 0, 0.45), (-0.2, 0, 0.0)]
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.08, 0.06, GOLD, sides=5, glow=2.4)
	return p.build()


def frog_poison():
	p = Prop("frog_poison", 477)
	p.blob((0.7, 0.55, 0.4), (0, 0, 0.35), GOLD, segs=(10, 6), glow=0.6)                   # a warning-yellow back
	for (x, y) in ((-0.2, -0.1), (0.15, 0.1), (0.05, -0.18)):
		p.blob((0.14, 0.14, 0.08), (x, y, 0.55), STONE_DARK, segs=(6, 4))
	for k in range(3):
		p.blob((0.08, 0.08, 0.12), (-0.3 + k * 0.3, -0.25, 0.05), LEAF, segs=(6, 4), glow=1.6)
	return p.build()


def death_roll():
	p = Prop("death_roll", 479)
	for k in range(3):                                                                    # a rolling swirl of water
		_ring(p, 0.3 + k * 0.18, 0.55, 0.05, WATER, glow=1.0, sides=16, tilt=math.pi / 2)
	for s_ in (-1, 1):                                                                    # jaws
		p.seg((0.0, 0, 0.55), (0.7, 0, 0.55 + s_ * 0.25), 0.1, 0.05, LEAF, sides=5)
	return p.build()


def tide_trunk_blessing():
	p = Prop("tide_trunk_blessing", 481)
	p.blob((0.6, 0.5, 0.55), (0, 0, 0.4), STONE_LIGHT, segs=(10, 8))                      # an elephant's head
	for s_ in (-1, 1):
		p.blob((0.1, 0.35, 0.4), (s_ * 0.36, 0.05, 0.42), STONE_LIGHT, segs=(6, 5))
		p.seg((s_ * 0.12, -0.25, 0.25), (s_ * 0.2, -0.45, 0.15), 0.05, 0.02, BONE, sides=5)
	p.seg((0, -0.3, 0.3), (0, -0.4, 0.85), 0.09, 0.06, STONE_LIGHT, sides=6)               # the trunk, raised...
	for k in range(5):                                                                    # ...spraying rain
		p.blob((0.08, 0.08, 0.12), (-0.3 + k * 0.15, -0.45, 1.05 - abs(k - 2) * 0.08), WATER, segs=(6, 4), glow=1.6)
	return p.build()


def fish():
	p = Prop("fish", 483)
	p.seg((-0.5, 0, 0.0), (0.5, 0, 1.1), 0.03, 0.015, WOOD, sides=5)                        # a rod
	p.seg((0.5, 0, 1.1), (0.55, 0, 0.3), 0.008, 0.008, CLOTH_WHITE, sides=3)                # the line
	p.blob((0.1, 0.1, 0.1), (0.55, 0, 0.3), CLOTH_RED, segs=(6, 4))                         # a float
	_ring(p, 0.3, 0.2, 0.025, WATER, glow=1.0, sides=16)                                  # ripples
	return p.build()


# ---------------------------------------------------------------- Magician and Necromancer

PURPLE = (3, 1)       # deep violet, for death magic
SICKLY = (6, 1)       # lime-to-teal, for disease
AMBER = (1, 3)        # warm orange-gold
CRIMSON = (4, 1)      # deep red-magenta


def _flame(p, x, z, s, glow=1.8):
	"""A licking flame: an ember core under a tapering yellow tongue."""
	p.blob((0.55 * s, 0.45 * s, 0.5 * s), (x, 0, z + 0.25 * s), EMBER, segs=(10, 6), glow=glow)
	p.seg((x, 0, z + 0.3 * s), (x + 0.05 * s, 0, z + 1.15 * s), 0.26 * s, 0.0, FLAME, sides=8, glow=glow + 0.4)
	for sx in (-1, 1):
		p.seg((x + sx * 0.15 * s, 0, z + 0.3 * s), (x + sx * 0.32 * s, 0, z + 0.85 * s), 0.13 * s, 0.0, FLAME, sides=6, glow=glow)


def _swirl(p, cx, cz, r0, r1, turns, swatch, glow, thick=0.06, steps=30):
	"""A flat spiral in the picture plane, from r0 out to r1."""
	pts = []
	for k in range(steps + 1):
		t = k / steps
		a = t * turns * math.tau
		r = r0 + (r1 - r0) * t
		pts.append((cx + math.cos(a) * r, 0, cz + math.sin(a) * r))
	for k, (a, b) in enumerate(zip(pts, pts[1:])):
		w = thick * (0.4 + 0.6 * k / steps)
		p.seg(a, b, w, w, swatch, sides=5, glow=glow)


def _elemental(p, swatch, s=1.0, glow=0.0):
	"""A small stocky elemental figure: head, body, fists."""
	p.blob((0.55 * s, 0.4 * s, 0.6 * s), (0, 0, 0.45 * s), swatch, segs=(10, 6), glow=glow)
	p.blob((0.32 * s, 0.3 * s, 0.3 * s), (0, 0, 0.95 * s), swatch, segs=(8, 6), glow=glow)
	for sx in (-1, 1):
		p.seg((sx * 0.25 * s, 0, 0.65 * s), (sx * 0.45 * s, 0, 0.3 * s), 0.1 * s, 0.1 * s, swatch, sides=6, glow=glow)
		p.blob((0.2 * s, 0.2 * s, 0.2 * s), (sx * 0.47 * s, 0, 0.25 * s), swatch, segs=(6, 5), glow=glow)
		p.seg((sx * 0.14 * s, 0, 0.2 * s), (sx * 0.18 * s, 0, 0.0), 0.1 * s, 0.1 * s, swatch, sides=6, glow=glow)


def _skull(p, x, z, s, swatch=BONE, eyes=None, eye_glow=2.0):
	p.blob((0.62 * s, 0.55 * s, 0.6 * s), (x, 0, z + 0.1 * s), swatch, segs=(12, 8))     # cranium
	p.blob((0.38 * s, 0.4 * s, 0.25 * s), (x, -0.02 * s, z - 0.22 * s), swatch, segs=(8, 5))  # jaw
	for sx in (-1, 1):
		p.blob((0.17 * s, 0.1 * s, 0.17 * s), (x + sx * 0.14 * s, -0.24 * s, z + 0.05 * s), eyes or STONE_DARK,
			   segs=(6, 4), glow=eye_glow if eyes else 0.0)
	p.blob((0.07 * s, 0.06 * s, 0.1 * s), (x, -0.27 * s, z - 0.1 * s), STONE_DARK, segs=(5, 4))  # nose
	for k in range(4):                                                                    # teeth
		p.box((0.05 * s, 0.03 * s, 0.07 * s), (x - 0.1 * s + k * 0.066 * s, -0.2 * s, z - 0.3 * s), STONE_DARK)


def _drop(p, x, z, s, swatch, glow):
	p.blob((0.4 * s, 0.4 * s, 0.4 * s), (x, 0, z), swatch, segs=(10, 6), glow=glow)
	p.seg((x, 0, z + 0.1 * s), (x, 0, z + 0.48 * s), 0.19 * s, 0.0, swatch, sides=10, glow=glow)


def call_of_earth():
	p = Prop("call_of_earth", 501)
	p.rock((1.0, 0.8, 1.0), (0, 0, 0.55), STONE_WARM, jitter=0.06)                          # a boulder fist, raised
	for k in range(4):                                                                    # knuckles
		p.rock((0.28, 0.28, 0.28), (-0.36 + k * 0.24, -0.34, 0.95), STONE_WARM, jitter=0.04)
	p.rock((0.3, 0.3, 0.4), (0.5, -0.2, 0.55), STONE_WARM, jitter=0.04)                     # thumb
	for k in range(3):                                                                    # amber cracks
		p.seg((-0.3 + k * 0.28, -0.42, 0.75), (-0.2 + k * 0.28, -0.42, 0.25), 0.045, 0.025, AMBER, sides=4, glow=2.6)
	_ring(p, 0.55, 0.0, 0.035, AMBER, glow=1.8, sides=18)                                 # summoning circle
	return p.build()


def call_of_water():
	p = Prop("call_of_water", 503)
	_swirl(p, 0, 0.7, 0.05, 0.6, 2.2, WATER, 1.4, thick=0.11)
	p.blob((0.2, 0.2, 0.2), (0, -0.05, 0.7), CLOTH_WHITE, segs=(8, 6), glow=1.6)
	_ring(p, 0.5, 0.0, 0.035, WATER, glow=1.8, sides=18)
	return p.build()


def call_of_fire():
	p = Prop("call_of_fire", 505)
	_flame(p, 0, 0.05, 1.3, glow=1.8)
	_ring(p, 0.55, 0.0, 0.035, FLAME, glow=1.8, sides=18)
	return p.build()


def call_of_air():
	p = Prop("call_of_air", 507)
	for k in range(6):                                                                    # a funnel of wind
		_ring(p, 0.1 + k * 0.1, 0.1 + k * 0.2, 0.04, CLOTH_WHITE if k % 2 else RUNE, glow=1.2, sides=16, tilt=0.35)
	_ring(p, 0.5, 0.0, 0.035, RUNE, glow=1.8, sides=18)
	return p.build()


def call_of_the_primal():
	p = Prop("call_of_the_primal", 509)
	for x, z, s in ((-0.35, 0.55, 0.5), (0.3, 0.55, 0.55), (0, 0.7, 0.6)):               # a storm cloud
		p.blob((s, s * 0.7, s * 0.8), (x, 0, z), STONE_DARK, segs=(10, 6))
	for k in range(5):                                                                    # a crown of lightning
		x = -0.4 + k * 0.2
		h = 1.25 if k % 2 == 0 else 1.1
		p.seg((x, -0.05, 0.9), (x, -0.05, h), 0.06, 0.0, GOLD, sides=4, glow=2.6)
	pts = [(0.1, -0.1, 0.35), (-0.1, -0.1, 0.1), (0.08, -0.1, 0.05), (-0.12, -0.1, -0.3)]
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, 0.07, 0.05, GOLD, sides=5, glow=2.4)
	return p.build()


def renew_elements():
	p = Prop("renew_elements", 511)
	_elemental(p, STONE_WARM, s=0.9)
	for k in range(5):                                                                    # rising healing motes
		a = k * math.tau / 5 + 0.4
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.62, -0.1, 0.5 + math.sin(a) * 0.45), LEAF, segs=(6, 4), glow=2.0)
	p.box((0.08, 0.06, 0.3), (0, -0.25, 0.45), GOLD, glow=2.2)                             # a small gold cross on the chest
	p.box((0.3, 0.06, 0.08), (0, -0.25, 0.48), GOLD, glow=2.2)
	return p.build()


def greater_renewal():
	p = Prop("greater_renewal", 513)
	_elemental(p, STONE_WARM, s=1.1)
	_ring(p, 0.8, 0.55, 0.05, LEAF, glow=2.0, sides=22, tilt=math.pi / 2)                  # a halo of green
	for k in range(8):
		a = k * math.tau / 8
		p.blob((0.12, 0.12, 0.12), (math.cos(a) * 0.8, -0.1, 0.55 + math.sin(a) * 0.8), GOLD, segs=(6, 4), glow=2.2)
	p.box((0.1, 0.06, 0.4), (0, -0.28, 0.5), GOLD, glow=2.4)
	p.box((0.4, 0.06, 0.1), (0, -0.28, 0.54), GOLD, glow=2.4)
	return p.build()


def burnout():
	p = Prop("burnout", 515)
	_flame(p, 0.2, 0.05, 0.85, glow=2.0)
	for k in range(4):                                                                    # speed lines
		p.seg((-0.85, 0, 0.15 + k * 0.22), (-0.3, 0, 0.18 + k * 0.22), 0.045, 0.0, FLAME if k % 2 else EMBER, sides=4, glow=1.6)
	return p.build()


def elemental_bond():
	p = Prop("elemental_bond", 517)
	_ring(p, 0.55, 0.55, 0.035, GOLD, glow=1.6, sides=20, tilt=math.pi / 2)               # linked in a ring
	for (a, sw) in ((math.pi / 2, FLAME), (0, WATER), (-math.pi / 2, STONE_WARM), (math.pi, CLOTH_WHITE)):
		p.blob((0.34, 0.34, 0.34), (math.cos(a) * 0.55, -0.05, 0.55 + math.sin(a) * 0.55), sw, segs=(10, 6),
			   glow=0.4 if sw == STONE_WARM else 1.4)
	return p.build()


def primal_fury():
	p = Prop("primal_fury", 519)
	p.blob((0.5, 0.45, 0.5), (0, 0, 0.5), EMBER, segs=(10, 8), glow=2.2)                   # an exploding flame
	for k in range(10):
		a = k * math.tau / 10 + 0.15
		r1 = 0.95 if k % 2 else 0.7
		p.seg((math.cos(a) * 0.2, 0, 0.5 + math.sin(a) * 0.2), (math.cos(a) * r1, 0, 0.5 + math.sin(a) * r1),
			  0.13, 0.0, FLAME if k % 2 else CLOTH_RED, sides=6, glow=2.2)
	return p.build()


def elemental_aegis():
	p = Prop("elemental_aegis", 521)
	p.blob((1.4, 1.2, 1.5), (0, 0, 0.1), STONE_WARM, segs=(14, 10), jitter=0.03)          # a stone dome
	p.blob((1.9, 1.7, 0.14), (0, 0, 0.1), STONE_DARK, segs=(16, 4))                        # on dark ground
	for z in (0.35, 0.6):                                                                 # its courses of stone
		rz = math.sqrt(max(0.0, 1 - ((z - 0.1) / 0.75) ** 2))
		_ring(p, 0.72 * rz, z, 0.03, STONE_DARK, sides=20)
	_ring(p, 0.74, 0.14, 0.05, AMBER, glow=2.0, sides=22)
	p.blob((0.22, 0.12, 0.22), (0, -0.6, 0.45), AMBER, segs=(8, 6), glow=2.4)
	return p.build()


def raise_bones():
	p = Prop("raise_bones", 523)
	p.blob((1.5, 1.0, 0.25), (0, 0, 0.0), STONE_DARK, segs=(14, 6))                       # the ground
	for k in range(5):                                                                    # dirt thrown up
		a = k * math.tau / 5
		p.rock((0.16, 0.16, 0.14), (math.cos(a) * 0.45, math.sin(a) * 0.3, 0.12), WOOD_GRAY)
	p.seg((0, 0, 0.05), (0.02, 0, 0.55), 0.07, 0.06, BONE, sides=6)                        # forearm bones
	p.seg((0.08, 0, 0.05), (0.1, 0, 0.55), 0.05, 0.05, BONE, sides=6)
	p.blob((0.3, 0.14, 0.2), (0.05, 0, 0.62), BONE, segs=(8, 5))                           # the palm
	for k in range(4):                                                                    # clawing fingers
		x = -0.1 + k * 0.1
		p.seg((x, 0, 0.7), (x - 0.02, 0, 0.9 - abs(k - 1.5) * 0.04), 0.03, 0.025, BONE, sides=5)
		p.seg((x - 0.02, 0, 0.9 - abs(k - 1.5) * 0.04), (x - 0.05, -0.06, 1.02 - abs(k - 1.5) * 0.05), 0.025, 0.0, BONE, sides=5)
	p.seg((0.16, 0, 0.58), (0.3, 0, 0.78), 0.035, 0.0, BONE, sides=5)                      # thumb
	for k in range(4):                                                                    # a sickly glow round the grave
		a = k * math.tau / 4 + 0.6
		p.blob((0.08, 0.08, 0.08), (math.cos(a) * 0.5, -0.1, 0.35 + math.sin(a) * 0.25), SICKLY, segs=(6, 4), glow=2.0)
	return p.build()


def raise_skeletal_knight():
	p = Prop("raise_skeletal_knight", 525)
	_skull(p, 0, 0.45, 1.0, eyes=SICKLY, eye_glow=2.6)
	p.blob((0.74, 0.66, 0.5), (0, 0.06, 0.74), IRON, segs=(12, 8))                         # an open helm over it
	p.seg((-0.37, -0.02, 0.62), (0.37, -0.02, 0.62), 0.05, 0.05, IRON, sides=6)             # its brow band
	p.box((0.07, 0.08, 0.3), (0, -0.3, 0.6), IRON)                                          # nasal guard
	p.seg((0, 0.1, 0.95), (0, 0.2, 1.25), 0.07, 0.02, CLOTH_RED, sides=5)                   # a crest
	for sx in (-1, 1):                                                                    # cheek guards, beside the face
		p.box((0.08, 0.35, 0.4), (sx * 0.36, 0.05, 0.4), IRON)
	return p.build()


def _bone(p, a, b, r, glow=0.0):
	a, b = list(a), list(b)
	p.seg(a, b, r, r, BONE, sides=8, glow=glow)
	for end, other in ((a, b), (b, a)):
		d = [(e - o) for e, o in zip(end, other)]
		n = math.sqrt(sum(c * c for c in d))
		perp = (-d[2] / n, 0, d[0] / n)
		for s_ in (-1, 1):
			p.blob((r * 2.4, r * 2.4, r * 2.4), (end[0] + perp[0] * r * s_, 0, end[2] + perp[2] * r * s_), BONE, segs=(8, 6), glow=glow)


def mend_bones():
	p = Prop("mend_bones", 527)
	_bone(p, (-0.6, 0, 0.1), (0.6, 0, 0.9), 0.09)
	for k in range(4):                                                                    # green stitches knitting it
		t = 0.3 + k * 0.13
		cx, cz = -0.6 + 1.2 * t, 0.1 + 0.8 * t
		p.seg((cx - 0.12, -0.12, cz + 0.16), (cx + 0.12, -0.12, cz - 0.16), 0.035, 0.035, LEAF, sides=4, glow=2.2)
	for k in range(5):
		a = k * math.tau / 5
		p.blob((0.08, 0.08, 0.08), (math.cos(a) * 0.7, -0.1, 0.5 + math.sin(a) * 0.55), LEAF, segs=(6, 4), glow=1.8)
	return p.build()


def dark_empowerment():
	p = Prop("dark_empowerment", 529)
	for k in range(8):                                                                    # a purple aura
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.5, 0.1, 0.5 + math.sin(a) * 0.5), (math.cos(a) * 0.85, 0.1, 0.5 + math.sin(a) * 0.85), 0.1, 0.0, PURPLE, sides=5, glow=2.0)
	_skull(p, 0, 0.5, 1.3, eyes=PURPLE, eye_glow=3.0)
	return p.build()


def _stream(p, x0, x1, z, amp, r, swatch, glow, n=12):
	pts = [(x0 + (x1 - x0) * k / n, 0, z + math.sin(k / n * math.tau * 1.2) * amp) for k in range(n + 1)]
	for a, b in zip(pts, pts[1:]):
		p.seg(a, b, r, r, swatch, sides=5, glow=glow)


def lifetap():
	p = Prop("lifetap", 531)
	_stream(p, -0.85, 0.35, 0.45, 0.12, 0.035, CLOTH_RED, 1.8)                             # a thin stream...
	_drop(p, 0.5, 0.35, 0.8, CLOTH_RED, 1.8)                                                # ...pulling a drop along
	for k in range(3):
		p.blob((0.08, 0.08, 0.08), (-0.6 + k * 0.35, -0.05, 0.45 + (0.12 if k % 2 else -0.08)), CLOTH_RED, segs=(6, 4), glow=2.0)
	return p.build()


def siphon_life():
	p = Prop("siphon_life", 533)
	for dz, amp in ((0.0, 0.18), (0.18, 0.12), (-0.18, 0.12)):                             # a braided torrent
		_stream(p, -0.9, 0.3, 0.5 + dz, amp, 0.06, CLOTH_RED, 2.0)
	_drop(p, 0.5, 0.35, 1.2, CLOTH_RED, 2.0)
	return p.build()


def soul_rend():
	p = Prop("soul_rend", 535)
	for sx, tilt in ((-1, 12), (1, -12)):                                                  # a ghostly soul torn in two
		cx = sx * 0.28
		p.blob((0.38, 0.3, 0.42), (cx, 0, 0.85), CLOTH_RED, rot=(0, tilt, 0), segs=(10, 6), glow=2.0)
		p.seg((cx, 0, 0.75), (cx + sx * 0.2, 0, 0.05), 0.2, 0.02, CLOTH_RED, sides=8, glow=1.8)
		for k in range(3):                                                                # the jagged tear
			z = 0.95 - k * 0.3
			p.seg((cx - sx * 0.14, -0.02, z), (cx - sx * 0.2, -0.02, z - 0.15), 0.05, 0.0, CRIMSON, sides=4, glow=1.4)
	for sx in (-1, 1):                                                                     # hollow eyes on the halves
		p.blob((0.08, 0.06, 0.1), (sx * 0.2, -0.16, 0.9), STONE_DARK, segs=(6, 4))
	return p.build()


def disease_cloud():
	p = Prop("disease_cloud", 537)
	for x, z, s in ((-0.4, 0.5, 0.55), (0.35, 0.5, 0.6), (0, 0.72, 0.7), (-0.1, 0.4, 0.6)):
		p.blob((s, s * 0.7, s * 0.8), (x, 0, z), SICKLY, segs=(10, 6), glow=0.8)
	rng = [(-0.6, 0.05), (-0.25, -0.05), (0.15, 0.1), (0.5, 0.0), (-0.45, 1.05), (0.4, 1.0), (0.0, 1.15), (0.7, 0.55), (-0.75, 0.6)]
	for x, z in rng:                                                                        # floating specks
		p.blob((0.09, 0.09, 0.09), (x, -0.3, z), LEAF if x > 0 else PINE, segs=(5, 4), glow=1.6)
	return p.build()


def venom_bolt():
	p = Prop("venom_bolt", 539)
	p.seg((-0.7, 0, 0.95), (0.35, 0, 0.35), 0.0, 0.2, LEAF, sides=8, glow=1.8)              # a streaking bolt
	p.blob((0.42, 0.42, 0.42), (0.4, 0, 0.32), LEAF, segs=(10, 8), glow=2.0)
	for k in range(3):                                                                    # dripping
		x = -0.25 + k * 0.25
		_drop(p, x, 0.3 - k * 0.12 + 0.1 * (k == 0), 0.35, SICKLY, 1.8)
	for k in range(3):                                                                    # its trail
		x = -0.8 + k * 0.15
		p.seg((x, 0, 1.1 - k * 0.1), (x + 0.3, 0, 0.95 - k * 0.12), 0.03, 0.0, SICKLY, sides=4, glow=1.4)
	return p.build()


def bond_of_death():
	p = Prop("bond_of_death", 541)
	_drop(p, -0.6, 0.25, 0.9, CLOTH_RED, 1.8)                                               # two drops...
	_drop(p, 0.6, 0.25, 0.9, CLOTH_RED, 1.8)
	for k, x in enumerate((-0.28, 0.0, 0.28)):                                            # ...chained together
		tilt = math.pi / 2 if k % 2 == 0 else 0.0
		for s_ in range(14):
			a0, a1 = s_ * math.tau / 14, (s_ + 1) * math.tau / 14
			pt = lambda a: (x + math.cos(a) * 0.17, math.sin(a) * 0.1 * math.cos(tilt), 0.35 + math.sin(a) * 0.1 * math.sin(tilt) + math.sin(a) * 0.1 * (1 - math.sin(tilt)))
			p.seg(pt(a0), pt(a1), 0.04, 0.04, IRON if k != 1 else PURPLE, sides=5, glow=0.0 if k != 1 else 1.8)
	return p.build()


def dread():
	p = Prop("dread", 543)
	p.blob((0.95, 0.5, 1.05), (0, 0.1, 0.5), PURPLE, segs=(14, 10), glow=0.4)              # a dark face...
	for sx in (-1, 1):                                                                     # ...wide staring eyes
		p.blob((0.28, 0.1, 0.34), (sx * 0.2, -0.16, 0.68), CLOTH_WHITE, segs=(10, 6), glow=1.2)
		p.blob((0.08, 0.06, 0.08), (sx * 0.2, -0.22, 0.66), STONE_DARK, segs=(6, 4))
		p.seg((sx * 0.08, -0.16, 0.95), (sx * 0.34, -0.14, 0.88), 0.03, 0.03, STONE_DARK, sides=4)   # brows up
	p.blob((0.24, 0.1, 0.34), (0, -0.16, 0.2), STONE_DARK, segs=(10, 6))                  # a screaming mouth
	return p.build()


def mass_dread():
	p = Prop("mass_dread", 545)
	for k in range(3):                                                                    # a shockwave rolling out
		_ring(p, 0.3 + k * 0.28, 0.1, 0.06 - k * 0.012, PURPLE, glow=2.2 - k * 0.5, sides=22)
	for k in range(3):                                                                    # tiny faces fleeing
		a = math.radians(210 + k * 60)
		x, y = math.cos(a) * 0.95, math.sin(a) * 0.6
		p.blob((0.2, 0.2, 0.22), (x, y, 0.25), PURPLE, segs=(8, 6), glow=0.6)
		for sx in (-1, 1):
			p.blob((0.06, 0.04, 0.07), (x + sx * 0.05, y - 0.1, 0.28), CLOTH_WHITE, segs=(5, 4), glow=1.4)
	p.blob((0.3, 0.3, 0.3), (0, 0, 0.15), PURPLE, segs=(8, 6), glow=2.6)
	return p.build()


def feign_death():
	p = Prop("feign_death", 547)
	p.box((0.5, 0.2, 0.8), (0.45, 0.25, 0.4), STONE_LIGHT)                                 # a tombstone
	p.seg((0.45, 0.35, 0.8), (0.45, 0.15, 0.8), 0.25, 0.25, STONE_LIGHT, sides=12)
	p.box((0.06, 0.03, 0.35), (0.45, 0.13, 0.55), STONE_DARK)                               # its cross
	p.box((0.22, 0.03, 0.06), (0.45, 0.13, 0.62), STONE_DARK)
	p.blob((1.1, 0.4, 0.3), (-0.3, -0.2, 0.15), CLOTH_RED, segs=(10, 6))                    # a figure lying flat
	p.blob((0.3, 0.3, 0.3), (-0.95, -0.2, 0.2), HIDE, segs=(8, 6))
	for sx in (-1, 1):                                                                     # limbs sprawled
		p.seg((-0.55, -0.2 + sx * 0.18, 0.15), (-0.45, -0.2 + sx * 0.42, 0.1), 0.06, 0.05, HIDE, sides=5)
		p.seg((0.2, -0.2 + sx * 0.1, 0.12), (0.4, -0.2 + sx * 0.2, 0.1), 0.08, 0.07, STONE_DARK, sides=5)
	for k in range(3):                                                                    # "z" wisps, not quite asleep
		p.blob((0.1, 0.1, 0.1), (-0.8 + k * 0.2, -0.3, 0.45 + k * 0.15), PURPLE, segs=(5, 4), glow=1.6)
	return p.build()


def clinging_darkness():
	p = Prop("clinging_darkness", 549)
	for sx in (-1, 1):                                                                     # a pair of feet
		p.seg((sx * 0.22, 0.05, 0.7), (sx * 0.22, 0.05, 0.25), 0.1, 0.12, WOOD, sides=8)       # boots
		p.blob((0.26, 0.5, 0.22), (sx * 0.22, -0.12, 0.15), WOOD, segs=(8, 5))
	for k in range(6):                                                                    # tendrils coiling up round them
		x = -0.6 + k * 0.24
		pts = [(x, -0.25, 0.0), (x + 0.12, -0.35, 0.25), (x - 0.05, -0.38, 0.5), (x + 0.1, -0.35, 0.8 - abs(k - 2.5) * 0.12)]
		for j, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.07 - j * 0.02, 0.05 - j * 0.02, PURPLE, sides=5, glow=1.2)
	p.blob((1.4, 0.9, 0.12), (0, 0, 0.0), STONE_DARK, segs=(12, 6))                        # a pool of shadow
	return p.build()


def elemental_flame():
	p = Prop("elemental_flame", 551)
	_flame(p, 0, 0, 0.8, glow=2.0)
	for k in range(3):                                                                    # licking sideways
		p.seg((0.1, 0, 0.35 + k * 0.2), (0.7, 0, 0.55 + k * 0.25), 0.1, 0.0, FLAME, sides=6, glow=2.0)
	return p.build()


def gust_of_wind():
	p = Prop("gust_of_wind", 553)
	for k, z in enumerate((0.25, 0.55, 0.85)):                                             # three gust lines, curling
		x0 = -0.8 + k * 0.15
		p.seg((x0, 0, z), (0.3, 0, z), 0.04, 0.04, CLOTH_WHITE if k != 1 else RUNE, sides=5, glow=1.2)
		_swirl(p, 0.3, z + 0.13, 0.13, 0.02, 0.8, CLOTH_WHITE if k != 1 else RUNE, 1.2, thick=0.05, steps=10)
	return p.build()


# ---------------------------------------------------------------- actions

def action_attack():
	for x, yaw in ((-0.12, 35), (0.12, -35)):
		_import("res://assets/KayKit_Adventurers_2.0_FREE/Assets/gltf/sword_1handed.gltf", rot=(0, yaw, 0), loc=(x, 0, 0))


def action_ranged():
	_import("res://assets/KayKit_Adventurers_2.0_FREE/Assets/gltf/bow_withString.gltf", rot=(0, 30, 0))
	_import("res://assets/KayKit_Adventurers_2.0_FREE/Assets/gltf/arrow_bow.gltf", rot=(0, -60, 0), loc=(0.05, -0.05, 0.1))


def action_sit():
	p = Prop("action_sit", 341)
	p.seg((0, 0, 0.5), (0, 0, 0.58), 0.45, 0.45, WOOD, sides=12)                   # a stool
	for k in range(3):
		a = k * math.tau / 3
		p.seg((math.cos(a) * 0.3, math.sin(a) * 0.3, 0.5), (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.0), 0.05, 0.05, WOOD_GRAY, sides=5)
	for k in range(3):                                                             # resting "z"s
		s = 0.12 + k * 0.05
		x, z = 0.35 + k * 0.2, 0.8 + k * 0.25
		p.box((s * 2, 0.04, 0.04), (x, 0, z + s), CLOTH_WHITE, glow=0.6)
		p.box((s * 2, 0.04, 0.04), (x, 0, z - s), CLOTH_WHITE, glow=0.6)
		p.box((s * 2.6, 0.04, 0.04), (x, 0, z), CLOTH_WHITE, rot=(0, 45, 0), glow=0.6)
	return p.build()


def action_consider():
	p = Prop("action_consider", 343)
	p.blob((1.0, 0.5, 0.6), (0, 0, 0.3), CLOTH_WHITE, segs=(14, 10))               # an eye
	p.blob((0.42, 0.2, 0.42), (0, -0.2, 0.3), RUNE, segs=(12, 8), glow=0.8)
	p.blob((0.2, 0.1, 0.2), (0, -0.28, 0.3), STONE_DARK, segs=(8, 6))
	return p.build()


def action_skills():
	p = Prop("action_skills", 345)
	for x in (-1, 1):                                                              # an open book
		p.box((0.55, 0.7, 0.05), (x * 0.3, 0, 0.1), CLOTH_WHITE, rot=(0, x * -12, 0))
		p.box((0.6, 0.75, 0.04), (x * 0.3, 0, 0.05), CLOTH_RED, rot=(0, x * -12, 0))
	for k in range(4):
		p.box((0.35, 0.03, 0.01), (-0.3, -0.2 + k * 0.12, 0.14), STONE_DARK, rot=(0, 12, 0))
	return p.build()


def action_hail():
	p = Prop("action_hail", 347)
	p.blob((0.5, 0.3, 0.55), (0, 0, 0.45), HIDE, segs=(10, 8))                      # an open hand raised
	for k in range(4):
		x = -0.22 + k * 0.15
		p.seg((x, 0, 0.7), (x * 1.1, 0, 1.05 - abs(k - 1.5) * 0.06), 0.06, 0.05, HIDE, sides=6)
	p.seg((0.28, 0, 0.45), (0.5, 0, 0.7), 0.06, 0.05, HIDE, sides=6)                  # thumb
	for k in range(3):                                                               # a wave
		_ring(p, 0.55 + k * 0.14, 0.6, 0.02, GOLD, glow=1.0, sides=6, tilt=math.pi / 2)
	return p.build()


def action_loot():
	p = Prop("action_loot", 349)
	p.blob((0.8, 0.6, 0.6), (0, 0, 0.3), HIDE, segs=(10, 8))                         # a sack...
	p.seg((0, 0, 0.62), (0, 0, 0.78), 0.12, 0.18, HIDE, sides=8)
	for k in range(4):                                                               # ...spilling coins
		p.seg((-0.5 + k * 0.28, -0.3, 0.05), (-0.5 + k * 0.28, -0.3, 0.1), 0.13, 0.13, GOLD, sides=10, glow=0.6)
	return p.build()


def _pet_head(p):
	p.blob((0.5, 0.42, 0.5), (0, 0, 0.55), STONE_LIGHT, segs=(10, 8))                # a small elemental's head
	for s_ in (-1, 1):
		p.blob((0.1, 0.06, 0.1), (s_ * 0.12, -0.2, 0.6), GOLD, segs=(6, 4), glow=1.6)


def action_pet_attack():
	p = Prop("action_pet_attack", 351)
	_pet_head(p)
	p.seg((0.3, 0, 0.1), (0.9, 0, 0.95), 0.06, 0.0, IRON, sides=4)                    # a blade behind it
	return p.build()


def action_pet_back():
	p = Prop("action_pet_back", 353)
	_pet_head(p)
	for k in range(3):                                                               # arrows pointing back
		p.seg((0.9 - k * 0.05, 0, 0.2 + k * 0.3), (0.45, 0, 0.2 + k * 0.3), 0.04, 0.04, CLOTH_WHITE, sides=4, glow=0.8)
		p.seg((0.45, 0, 0.2 + k * 0.3), (0.58, 0, 0.3 + k * 0.3), 0.03, 0.03, CLOTH_WHITE, sides=4, glow=0.8)
	return p.build()


def action_pet_follow():
	p = Prop("action_pet_follow", 355)
	_pet_head(p)
	for k in range(3):                                                               # footprints
		p.blob((0.12, 0.2, 0.03), (-0.5 + k * 0.25, -0.1, 0.02 + (k % 2) * 0.12), LEAF, segs=(6, 4), glow=0.8)
	return p.build()


def action_pet_guard():
	p = Prop("action_pet_guard", 357)
	_pet_head(p)
	p.seg((0.55, 0.1, 0.5), (0.55, -0.05, 0.5), 0.3, 0.3, WOOD, sides=12)             # a shield beside it
	p.blob((0.12, 0.08, 0.12), (0.55, -0.08, 0.5), IRON, segs=(8, 5))
	return p.build()


def action_pet_sit():
	p = Prop("action_pet_sit", 359)
	_pet_head(p)
	for k in range(2):                                                               # resting z's
		x, z = 0.5 + k * 0.2, 0.8 + k * 0.25
		p.box((0.24, 0.04, 0.04), (x, 0, z + 0.1), CLOTH_WHITE, glow=0.6)
		p.box((0.24, 0.04, 0.04), (x, 0, z - 0.1), CLOTH_WHITE, glow=0.6)
		p.box((0.3, 0.04, 0.04), (x, 0, z), CLOTH_WHITE, rot=(0, 45, 0), glow=0.6)
	return p.build()


# ---------------------------------------------------------------- shaman

def _paw(p, x, z, s, swatch, glow):
	"""A paw print standing upright to face the camera: a pad and four toes."""
	p.blob((0.42 * s, 0.1, 0.36 * s), (x, 0, z), swatch, segs=(10, 6), glow=glow)
	for k, (dx, dz) in enumerate(((-0.27, 0.3), (-0.1, 0.42), (0.1, 0.42), (0.27, 0.3))):
		p.blob((0.15 * s, 0.1, 0.18 * s), (x + dx * s, 0, z + dz * s), swatch, segs=(8, 5), glow=glow)


def _swarm(p, n, spread, swatch, glow, seed):
	import random
	rnd = random.Random(seed)
	for k in range(n):   # insects: a body and two pale wings each
		x, z = rnd.uniform(-spread, spread), 0.5 + rnd.uniform(-spread, spread) * 0.8
		p.blob((0.2, 0.14, 0.13), (x, -0.1, z), swatch, segs=(6, 4), glow=glow)
		for sx in (-1, 1):
			p.blob((0.17, 0.03, 0.1), (x + sx * 0.14, -0.14, z + 0.09), CLOTH_WHITE, rot=(0, sx * 30, 0), segs=(5, 3), glow=0.6)


def _snowflake(p, cx, cz, r, glow):
	for k in range(6):
		a = k * math.tau / 6
		tip = (cx + math.cos(a) * r, 0, cz + math.sin(a) * r)
		p.seg((cx, 0, cz), tip, 0.05, 0.02, WATER, sides=5, glow=glow)
		mid = (cx + math.cos(a) * r * 0.6, 0, cz + math.sin(a) * r * 0.6)
		for b in (-0.6, 0.6):
			p.seg(mid, (mid[0] + math.cos(a + b) * r * 0.25, 0, mid[2] + math.sin(a + b) * r * 0.25), 0.03, 0.01, WATER, sides=4, glow=glow)


def _moon(p, cx, cz, r, glow):
	for k in range(9):   # a crescent: blobs along an arc, thinning at the horns
		a = math.radians(110 + k * 17.5)
		w = 0.2 * r * math.sin(math.radians(k * 180 / 8)) + 0.05
		p.blob((w * 2, 0.1, w * 2), (cx + math.cos(a) * r, 0, cz + math.sin(a) * r), GOLD, segs=(8, 5), glow=glow)


def _zs(p, x, z, s, glow=0.8):
	p.box((0.24 * s, 0.04, 0.04 * s), (x, 0, z + 0.1 * s), CLOTH_WHITE, glow=glow)
	p.box((0.24 * s, 0.04, 0.04 * s), (x, 0, z - 0.1 * s), CLOTH_WHITE, glow=glow)
	p.box((0.3 * s, 0.04, 0.04 * s), (x, 0, z), CLOTH_WHITE, rot=(0, 45, 0), glow=glow)


def frost_rift():
	p = Prop("frost_rift", 601)
	for k in range(5):   # a jagged crack in the ground
		x0, x1 = -0.8 + k * 0.32, -0.48 + k * 0.32
		p.seg((x0, 0, 0.1 + 0.06 * (k % 2)), (x1, 0, 0.1 + 0.06 * ((k + 1) % 2)), 0.06, 0.06, STONE_DARK, sides=4)
	for x, h, lean in ((-0.45, 0.55, -15), (-0.1, 0.9, 5), (0.25, 0.7, 12), (0.55, 0.45, 25)):   # ice shards bursting up
		top = (x + math.sin(math.radians(lean)) * h, 0, 0.1 + math.cos(math.radians(lean)) * h)
		p.seg((x, 0, 0.1), top, 0.13, 0.0, WATER, sides=5, glow=1.4)
	return p.build()


def sicken():
	p = Prop("sicken", 603)
	_swirl(p, 0, 0.55, 0.1, 0.55, 1.6, SICKLY, 1.4, thick=0.08)
	for x, z in ((-0.55, 0.1), (0.1, 0.02), (0.6, 0.15)):
		_drop(p, x, z, 0.35, SICKLY, 1.6)
	return p.build()


def strengthen():
	p = Prop("strengthen", 605)
	p.blob((0.6, 0.45, 0.55), (0, 0, 0.5), HIDE, segs=(10, 8))   # a clenched fist
	for k in range(4):
		p.blob((0.17, 0.2, 0.17), (-0.22 + k * 0.15, -0.2, 0.68), HIDE, segs=(6, 5))
	p.seg((0, 0, 0.25), (0, 0, -0.2), 0.2, 0.22, HIDE, sides=8)
	_ring(p, 0.72, 0.5, 0.05, FLAME, glow=1.8, sides=16)
	return p.build()


def inner_fire():
	p = Prop("inner_fire", 607)
	_flame(p, 0, 0.3, 0.9, glow=2.2)
	_ring(p, 0.62, 0.55, 0.06, GOLD, glow=1.2, sides=18)
	return p.build()


def drowsy():
	p = Prop("drowsy", 609)
	p.blob((1.2, 0.35, 0.25), (0, 0, 0.12), SICKLY, segs=(12, 6), glow=0.4)   # a slow snail's body
	p.seg((0.5, 0, 0.15), (0.72, 0, 0.45), 0.1, 0.08, SICKLY, sides=6, glow=0.4)   # its head, up
	for dx in (0.0, 0.1):   # drooping eye stalks
		p.seg((0.68 + dx, 0, 0.45), (0.8 + dx, -0.05, 0.62), 0.03, 0.02, SICKLY, sides=4, glow=0.4)
	_swirl(p, -0.1, 0.55, 0.05, 0.42, 2.0, WOOD, 0.3, thick=0.1)   # its shell
	p.blob((0.85, 0.3, 0.85), (-0.1, 0.08, 0.55), AMBER, segs=(12, 8))
	_zs(p, 0.45, 1.05, 0.7)
	return p.build()


def spirit_of_bear():
	p = Prop("spirit_of_bear", 611)
	_paw(p, 0, 0.35, 1.35, WOOD, 0.6)
	for k in range(4):   # claws
		dx = (-0.36, -0.13, 0.13, 0.36)[k]
		p.seg((dx, -0.05, 0.95), (dx * 1.1, -0.05, 1.15), 0.05, 0.0, BONE, sides=4)
	return p.build()


def spirit_mend():
	p = Prop("spirit_mend", 613)
	p.blob((0.55, 0.12, 0.85), (0, 0, 0.5), LEAF, rot=(0, 25, 0), segs=(10, 6), glow=1.2)   # a leaf
	p.seg((0.22, -0.02, 0.05), (-0.2, -0.02, 0.9), 0.025, 0.01, PINE, sides=4)
	for k in range(4):   # slow motes rising round it
		a = k * math.tau / 4
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.62, -0.1, 0.5 + math.sin(a) * 0.5), LEAF, segs=(6, 4), glow=2.0)
	return p.build()


def tainted_breath():
	p = Prop("tainted_breath", 615)
	_stream(p, -0.8, 0.7, 0.5, 0.18, 0.12, SICKLY, 1.2)
	for x, z, r in ((0.45, 0.62, 0.3), (0.7, 0.45, 0.25), (0.25, 0.42, 0.22)):
		p.blob((r, r * 0.8, r), (x, 0, z), LEAF, segs=(8, 6), glow=1.0)
	return p.build()


def feet_like_cat():
	p = Prop("feet_like_cat", 617)
	_paw(p, -0.35, 0.25, 0.8, GOLD, 1.0)
	_paw(p, 0.35, 0.65, 0.8, GOLD, 1.0)
	return p.build()


def frost_strike():
	p = Prop("frost_strike", 619)
	p.seg((-0.7, 0, 1.0), (0.45, 0, 0.2), 0.12, 0.12, WATER, sides=6, glow=1.4)   # an ice spear
	p.seg((0.45, 0, 0.2), (0.7, 0, 0.02), 0.2, 0.0, WATER, sides=6, glow=2.0)
	for k in range(3):
		p.seg((-0.7 + k * 0.2, 0.1, 1.0 - k * 0.14), (-0.95 + k * 0.2, 0.1, 1.12 - k * 0.14), 0.03, 0.0, CLOTH_WHITE, sides=4, glow=0.8)
	return p.build()


def walking_sleep():
	p = Prop("walking_sleep", 621)
	_moon(p, -0.1, 0.5, 0.5, 1.4)
	_zs(p, 0.5, 0.85, 0.8)
	_zs(p, 0.7, 0.45, 0.55)
	return p.build()


def spirit_healing():
	p = Prop("spirit_healing", 623)
	_cross(p, 0.9, LEAF, 1.8)
	_swirl(p, 0, 0.5, 0.55, 0.75, 1.0, CLOTH_WHITE, 0.8, thick=0.04)
	return p.build()


def quickness():
	p = Prop("quickness", 625)
	for k in range(3):   # chevrons racing forward
		x = -0.55 + k * 0.4
		p.seg((x - 0.2, 0, 0.85), (x + 0.15, 0, 0.5), 0.07, 0.07, GOLD, sides=5, glow=1.4 + k * 0.3)
		p.seg((x + 0.15, 0, 0.5), (x - 0.2, 0, 0.15), 0.07, 0.07, GOLD, sides=5, glow=1.4 + k * 0.3)
	return p.build()


def talisman_of_the_totem():
	p = Prop("talisman_of_the_totem", 627)
	for k, sw in enumerate((WOOD, CLOTH_RED, WOOD)):   # a little totem pole of three faces
		z = 0.2 + k * 0.36
		p.box((0.46, 0.4, 0.32), (0, 0, z), sw)
		for sx in (-1, 1):
			p.blob((0.08, 0.05, 0.06), (sx * 0.1, -0.21, z + 0.05), CLOTH_WHITE if k != 1 else GOLD, segs=(6, 4), glow=0.8)
	for sx in (-1, 1):   # its wings at the top
		p.seg((0, 0, 0.9), (sx * 0.7, 0, 1.05), 0.12, 0.03, STONE_WARM, sides=4)
	return p.build()


def envenomed_breath():
	p = Prop("envenomed_breath", 629)
	for x, z, r in ((-0.3, 0.5, 0.5), (0.25, 0.45, 0.55), (0, 0.75, 0.5)):
		p.blob((r, r * 0.7, r * 0.8), (x, 0, z), PINE, segs=(10, 6), glow=0.8)
	p.seg((0.05, -0.3, 0.55), (0.12, -0.35, 0.05), 0.12, 0.0, BONE, sides=5)   # a dripping fang
	_drop(p, 0.14, -0.15, 0.3, SICKLY, 2.0)
	return p.build()


def spirit_regrowth():
	p = Prop("spirit_regrowth", 631)
	p.seg((0, 0, 0.0), (0.05, 0, 0.9), 0.05, 0.03, PINE, sides=5, glow=0.6)   # a sprout
	for k, (z, side) in enumerate(((0.3, -1), (0.52, 1), (0.74, -1))):
		p.blob((0.4, 0.08, 0.2), (side * 0.2, 0, z), LEAF, rot=(0, side * -25, 0), segs=(8, 4), glow=1.4)
	_ring(p, 0.7, 0.45, 0.04, LEAF, glow=1.6, sides=18)
	return p.build()


def tagars_insects():
	p = Prop("tagars_insects", 633)
	_swarm(p, 7, 0.6, STONE_DARK, 0.4, 7)
	return p.build()


def winters_roar():
	p = Prop("winters_roar", 635)
	_snowflake(p, 0, 0.55, 0.62, 1.6)
	return p.build()


def spirit_of_the_wolf():
	p = Prop("spirit_of_the_wolf", 637)
	p.blob((0.62, 0.55, 0.58), (0, 0, 0.5), WATER, segs=(10, 8), glow=0.9)   # a spirit wolf's head
	p.seg((0, -0.25, 0.42), (0, -0.62, 0.32), 0.2, 0.1, WATER, sides=8, glow=0.9)   # muzzle
	p.blob((0.12, 0.1, 0.1), (0, -0.66, 0.36), STONE_DARK, segs=(6, 4))
	for sx in (-1, 1):
		p.seg((sx * 0.2, 0, 0.72), (sx * 0.3, 0.05, 1.08), 0.12, 0.0, WATER, sides=4, glow=0.9)   # ears
		p.blob((0.09, 0.05, 0.07), (sx * 0.16, -0.26, 0.6), CLOTH_WHITE, segs=(6, 4), glow=2.5)
	return p.build()


def chant_of_the_pack():
	p = Prop("chant_of_the_pack", 639)
	for x, z in ((-0.5, 0.2), (0.0, 0.62), (0.5, 0.2)):
		_paw(p, x, z, 0.6, WOOD_GRAY, 0.9)
	return p.build()


def winters_grasp():
	p = Prop("winters_grasp", 641)
	p.blob((0.55, 0.35, 0.35), (0, 0, 0.2), WATER, segs=(10, 6), glow=1.0)   # an icy palm
	for k in range(5):   # clawed fingers curling up
		x = -0.36 + k * 0.18
		pts = [(x, 0, 0.3), (x * 1.2, -0.05, 0.65), (x * 0.9, -0.15, 0.95)]
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.07, 0.05, WATER, sides=5, glow=1.3)
		p.seg(pts[-1], (x * 0.7, -0.25, 1.08), 0.05, 0.0, CLOTH_WHITE, sides=4, glow=1.5)
	return p.build()


def turgurs_insects():
	p = Prop("turgurs_insects", 643)
	_swarm(p, 10, 0.7, AMBER, 1.2, 11)
	return p.build()


def kraggs_mending():
	p = Prop("kraggs_mending", 645)
	for sx in (-1, 1):   # a glowing heart
		p.blob((0.5, 0.35, 0.5), (sx * 0.22, 0, 0.66), LEAF, segs=(10, 8), glow=1.8)
	p.seg((0, 0, 0.6), (0, 0, 0.05), 0.42, 0.0, LEAF, sides=10, glow=1.8)
	_ring(p, 0.8, 0.5, 0.04, GOLD, glow=1.4, sides=20)
	return p.build()


def ancestral_ward():
	p = Prop("ancestral_ward", 647)
	for k in range(3):   # three standing stones, each with a spirit's glowing eyes
		a = math.radians(210 + k * 60)
		x = math.cos(a) * 0.6
		p.box((0.28, 0.25, 0.8 - 0.15 * (k != 1)), (x, 0, 0.4), STONE_LIGHT)
		for sx in (-1, 1):
			p.blob((0.06, 0.04, 0.05), (x + sx * 0.06, -0.14, 0.55), GOLD, segs=(5, 3), glow=2.5)
	_ring(p, 0.85, 0.05, 0.05, GOLD, glow=1.6, sides=20, tilt=1.2)
	return p.build()


# ---------------------------------------------------------------- ranger, level 30 and the Ashfall / High Terrace monsters

MIST = (5, 3)         # soft gray: ash, smoke, stone dust
CLAY = props.CLAY
PETAL_PURPLE = props.PETAL_PURPLE


def _ring_at(p, cx, cz, radius, r, swatch, glow=0.0, sides=18, a0=0.0, a1=math.tau, y=0.0):
	"""A ring (or an arc from a0 to a1) standing in the picture plane around (cx, cz)."""
	for k in range(sides):
		t0, t1 = a0 + (a1 - a0) * k / sides, a0 + (a1 - a0) * (k + 1) / sides
		p.seg((cx + math.cos(t0) * radius, y, cz + math.sin(t0) * radius),
			  (cx + math.cos(t1) * radius, y, cz + math.sin(t1) * radius), r, r, swatch, sides=5, glow=glow)


def _arrow(p, a, b, head=STONE_LIGHT, shaft=WOOD, fletch=CLOTH_WHITE, glow=0.0, r=0.035, hs=1.0, barbs=False):
	"""An arrow from its nock at a to its point at b, fletched in the picture plane."""
	a, b = Vector(a), Vector(b)
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x))
	p.seg(a, b, r, r, shaft, sides=6)
	p.seg(b - d * 0.04 * hs, b + d * 0.24 * hs, 0.095 * hs, 0.0, head, sides=4, glow=glow)
	if barbs:   # hooks along the head, raking back
		for k in range(3):
			base = b + d * (0.18 - k * 0.1) * hs
			for sgn in (-1, 1):
				p.seg(base, base - d * 0.14 * hs + n * sgn * 0.13 * hs, 0.035 * hs, 0.0, head, sides=4, glow=glow)
	for sgn, sw in ((1, fletch), (-1, fletch)):
		nn = n * sgn * 0.12 * hs
		root, tip = a + d * 0.03, a + d * 0.3 * hs
		p.poly([tuple(root), tuple(tip), tuple(tip - d * 0.07 * hs + nn), tuple(root + nn * 0.9)], [(0, 1, 2, 3)], sw)
	p.seg(a - d * 0.03, a + d * 0.03, r * 1.3, r * 1.3, CLOTH_RED, sides=5)


def _fl(p, x, y, z, s, glow=2.0, core=EMBER, tongue=FLAME):
	"""A flame like _flame, but at any depth."""
	p.blob((0.55 * s, 0.45 * s, 0.5 * s), (x, y, z + 0.25 * s), core, segs=(10, 6), glow=glow)
	p.seg((x, y, z + 0.3 * s), (x + 0.05 * s, y, z + 1.15 * s), 0.26 * s, 0.0, tongue, sides=8, glow=glow + 0.4)
	for sx in (-1, 1):
		p.seg((x + sx * 0.15 * s, y, z + 0.3 * s), (x + sx * 0.32 * s, y, z + 0.85 * s), 0.13 * s, 0.0, tongue, sides=6, glow=glow)


def _feather_fan(p, cx, cz, angles, length, swatch, tip=None, glow=0.0, r=0.08):
	for k, deg in enumerate(angles):
		a = math.radians(deg)
		end = (cx + math.cos(a) * length, 0, cz + math.sin(a) * length)
		p.seg((cx, 0, cz), end, r, r * 0.35, swatch, sides=5, glow=glow)
		if tip:
			p.seg(end, (end[0] + math.cos(a) * 0.12, 0, end[2] + math.sin(a) * 0.12), r * 0.35, 0.0, tip, sides=5, glow=glow)


def _dagger(p, base, tip, glow=0.0, blade=STONE_LIGHT, edge=None, w=0.075):
	base, tip = Vector(base), Vector(tip)
	d = (tip - base).normalized()
	n = Vector((-d.z, 0, d.x))
	p.seg(base, tip, w, 0.0, blade, sides=4, glow=glow)
	p.seg(base - n * w * 2, base + n * w * 2, w * 0.5, w * 0.5, GOLD, sides=5)
	p.seg(base, base - d * w * 3, w * 0.55, w * 0.55, WOOD, sides=6)
	p.blob((w, w, w), tuple(base - d * w * 3.3), GOLD, segs=(6, 4))
	if edge:
		p.seg(base + d * 0.05 - Vector((0, 0.05, 0)), tip - Vector((0, 0.05, 0)), 0.02, 0.0, edge, sides=4, glow=2.2)


def false_sunfire():
	p = Prop("false_sunfire", 701)
	for k in range(12):                                                                   # crooked, blood-red rays
		a = k * math.tau / 12
		r1 = 0.95 if k % 2 else 0.78
		mid = (math.cos(a + 0.18) * 0.62, 0.05, 0.55 + math.sin(a + 0.18) * 0.62)
		p.seg((math.cos(a) * 0.4, 0.05, 0.55 + math.sin(a) * 0.4), mid, 0.07, 0.05, CRIMSON, sides=4, glow=1.6)
		p.seg(mid, (math.cos(a - 0.1) * r1, 0.05, 0.55 + math.sin(a - 0.1) * r1), 0.05, 0.0, EMBER, sides=4, glow=2.0)
	p.blob((0.82, 0.4, 0.82), (0, 0, 0.55), PURPLE, segs=(14, 10), glow=0.9)                # a dark sun
	_ring_at(p, 0, 0.55, 0.42, 0.035, FLAME, glow=2.2, sides=22, y=-0.05)
	p.blob((0.46, 0.12, 0.2), (0, -0.18, 0.55), FLAME, segs=(10, 6), glow=3.0)              # with an eye
	p.blob((0.09, 0.06, 0.2), (0, -0.25, 0.55), STONE_DARK, segs=(6, 4))
	return p.build()


def aimed_shot():
	p = Prop("aimed_shot", 703)
	_arrow(p, (-0.75, 0, 0.0), (0.28, 0, 0.72), hs=1.2)
	_ring_at(p, 0.45, 0.84, 0.3, 0.03, GOLD, glow=1.8, sides=20)                           # the mark it's aimed at
	for a in range(4):
		t = a * math.pi / 2 + math.pi / 4
		p.seg((0.45 + math.cos(t) * 0.22, -0.02, 0.84 + math.sin(t) * 0.22),
			  (0.45 + math.cos(t) * 0.42, -0.02, 0.84 + math.sin(t) * 0.42), 0.03, 0.03, GOLD, sides=4, glow=1.8)
	return p.build()


def track():
	p = Prop("track", 705)
	for k, (x, z) in enumerate(((-0.62, -0.1), (-0.15, 0.12), (0.3, -0.02))):          # a trail of prints
		_paw(p, x, z, 0.6, HIDE, 0.3 + k * 0.3)
	p.blob((0.8, 0.16, 0.42), (0.1, -0.05, 0.85), CLOTH_WHITE, segs=(12, 6), glow=0.5)  # a watching eye above
	p.blob((0.34, 0.1, 0.34), (0.1, -0.12, 0.85), LEAF, segs=(8, 6), glow=1.4)
	p.blob((0.13, 0.06, 0.18), (0.1, -0.18, 0.85), STONE_DARK, segs=(6, 4))
	_ring_at(p, 0.1, 0.72, 0.5, 0.04, WOOD, a0=0.5, a1=math.pi - 0.5, sides=10, y=-0.05)
	return p.build()


def flame_lick():
	p = Prop("flame_lick", 707)
	for sx in (-1, 1):                                                                    # two crossed twigs
		p.seg((sx * -0.55, 0, 0.0), (sx * 0.55, 0, 0.22), 0.07, 0.06, WOOD, sides=6)
	_fl(p, 0, -0.05, 0.1, 0.62, glow=2.2)
	p.seg((0.1, -0.1, 0.45), (0.35, -0.1, 0.8), 0.06, 0.0, FLAME, sides=5, glow=2.4)     # a licking tongue
	return p.build()


def ensnare():
	p = Prop("ensnare", 709)
	_ring(p, 0.48, 0.05, 0.05, HIDE, sides=20)                                            # a noose on the ground
	pts = [(0.5, 0, 0.0), (0.62, 0, 0.35), (0.62, 0, 0.75), (0.45, 0, 1.05), (0.15, 0, 1.15)]  # a bent sapling
	for i, (a, b) in enumerate(zip(pts, pts[1:])):
		p.seg(a, b, 0.07 - i * 0.012, 0.06 - i * 0.012, WOOD, sides=6)
	for x, z in ((0.3, 1.15), (0.6, 0.95)):
		p.blob((0.2, 0.08, 0.12), (x, 0, z + 0.06), LEAF, segs=(6, 4), glow=0.6)
	p.seg((0.15, 0, 1.15), (0.0, -0.1, 0.1), 0.03, 0.03, HIDE, sides=4)                  # the line down to the loop
	p.blob((0.12, 0.12, 0.12), (0.0, -0.45, 0.06), HIDE, segs=(6, 4))                     # its knot
	for k in range(5):                                                                    # a green glow round the snare
		a = k * math.tau / 5 + 0.3
		p.blob((0.09, 0.09, 0.09), (math.cos(a) * 0.62, math.sin(a) * 0.62, 0.2), LEAF, segs=(6, 4), glow=2.0)
	return p.build()


def salve():
	p = Prop("salve", 711)
	p.seg((0, 0, 0.0), (0, 0, 0.45), 0.36, 0.42, CLAY, sides=14)                          # a little clay pot
	p.seg((0, 0, 0.42), (0, 0, 0.5), 0.46, 0.46, CLAY, sides=14)
	p.blob((0.8, 0.8, 0.2), (0, 0, 0.52), LEAF, segs=(12, 6), glow=1.6)                     # of green ointment
	p.blob((0.5, 0.12, 0.2), (0.25, -0.1, 0.72), LEAF, rot=(0, -35, 0), segs=(8, 4), glow=0.8)   # a leaf on it
	p.seg((0.05, -0.1, 0.6), (0.45, -0.1, 0.85), 0.02, 0.01, PINE, sides=4)
	for k in range(3):
		p.blob((0.1, 0.1, 0.1), (-0.3 + k * 0.28, -0.1, 0.85 + (k % 2) * 0.18), GOLD, segs=(6, 4), glow=2.0)
	return p.build()


def strength_of_the_wild():
	p = Prop("strength_of_the_wild", 713)
	_ring_at(p, 0.0, 0.55, 0.78, 0.04, LEAF, glow=1.4, sides=24, y=0.25)                   # a green aura
	p.seg((-0.65, 0, 0.3), (0.12, 0, 0.3), 0.16, 0.15, HIDE, sides=8)                    # a flexed arm
	p.blob((0.52, 0.34, 0.36), (-0.22, 0, 0.44), HIDE, segs=(10, 6))                       # its bicep
	p.seg((0.12, 0, 0.3), (0.28, 0, 0.88), 0.14, 0.13, HIDE, sides=8)
	p.blob((0.32, 0.3, 0.3), (0.12, 0, 0.3), HIDE, segs=(8, 6))
	p.blob((0.36, 0.34, 0.34), (0.3, 0, 0.98), HIDE, segs=(10, 6))                         # fist
	for k in range(6):                                                                    # a band of leaves
		a = k * math.tau / 6
		p.blob((0.16, 0.06, 0.1), (0.2 + math.cos(a) * 0.17, math.sin(a) * 0.17, 0.6), LEAF, rot=(0, 0, math.degrees(a)), segs=(6, 4), glow=1.0)
	return p.build()


def icicle():
	p = Prop("icicle", 715)
	p.blob((1.2, 0.45, 0.24), (0, 0, 1.05), CLOTH_WHITE, segs=(12, 6))                      # a snowy ledge
	for x, h, r in ((0, 1.05, 0.2), (-0.35, 0.55, 0.11), (0.33, 0.7, 0.13)):              # icicles hanging off it
		p.seg((x, 0, 1.0), (x + 0.02, 0, 1.0 - h), r, 0.0, WATER, sides=6, glow=1.3)
	_drop(p, 0.03, -0.35, 0.28, WATER, 1.8)
	return p.build()


def entangle():
	p = Prop("entangle", 717)
	for v in range(3):                                                                    # three vines twisting up
		pts = []
		for k in range(19):
			t = k / 18
			a = v * math.tau / 3 + t * 2.2 * math.pi
			r = 0.45 - t * 0.2
			pts.append((math.cos(a) * r, math.sin(a) * r, t * 1.15))
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.075 - i * 0.003, 0.072 - i * 0.003, PINE, sides=6)
			if i % 4 == 2:
				p.blob((0.24, 0.08, 0.13), b, LEAF, rot=(0, 30 * (1 if v % 2 else -1), 0), segs=(6, 4), glow=0.8)
	p.blob((1.2, 1.0, 0.1), (0, 0, 0.0), STONE_DARK, segs=(12, 4))
	return p.build()


def eagle_eye():
	p = Prop("eagle_eye", 719)
	_feather_fan(p, 0, 0.62, (60, 80, 100, 120), 0.6, WOOD, tip=CLOTH_WHITE, r=0.09)      # a crest of feathers
	p.blob((1.1, 0.2, 0.52), (0, 0, 0.45), CLOTH_WHITE, segs=(14, 6))                        # an eye
	p.blob((0.46, 0.1, 0.46), (0, -0.1, 0.45), GOLD, segs=(10, 8), glow=1.6)
	p.blob((0.2, 0.06, 0.26), (0, -0.16, 0.45), STONE_DARK, segs=(8, 5))
	_ring_at(p, 0, 0.1, 0.5, 0.04, HIDE, a0=0.55, a1=math.pi - 0.55, sides=10, y=-0.05)   # its brow
	return p.build()


def multishot():
	p = Prop("multishot", 721)
	for deg in (18, 42, 66):                                                              # three arrows, fanned
		a = math.radians(deg)
		_arrow(p, (-0.7, 0, 0.0), (-0.7 + math.cos(a) * 1.35, 0, math.sin(a) * 1.35), glow=0.4)
	return p.build()


def natures_mend():
	p = Prop("natures_mend", 723)
	p.seg((0, 0, -0.1), (0.05, 0, 0.55), 0.05, 0.04, PINE, sides=5)                     # a stem
	for sx in (-1, 1):
		p.blob((0.4, 0.08, 0.16), (sx * 0.2, 0, 0.12), LEAF, rot=(0, sx * -30, 0), segs=(8, 4), glow=0.8)
	for k in range(5):                                                                    # a white bloom
		a = k * math.tau / 5 + math.pi / 2
		p.blob((0.34, 0.1, 0.34), (math.cos(a) * 0.26, -0.02, 0.72 + math.sin(a) * 0.26), CLOTH_WHITE, segs=(8, 5), glow=1.2)
	p.blob((0.24, 0.12, 0.24), (0, -0.1, 0.72), GOLD, segs=(8, 5), glow=2.2)
	for k in range(4):
		a = k * math.tau / 4 + 0.6
		p.blob((0.09, 0.09, 0.09), (math.cos(a) * 0.72, -0.1, 0.55 + math.sin(a) * 0.55), LEAF, segs=(6, 4), glow=2.0)
	return p.build()


def call_of_flame():
	p = Prop("call_of_flame", 725)
	p.blob((0.7, 0.1, 1.0), (0, 0.05, 0.5), LEAF, rot=(0, -20, 0), segs=(12, 6))          # a forest leaf
	p.seg((0.18, 0.0, 0.0), (-0.18, 0.0, 1.0), 0.03, 0.015, PINE, sides=4)
	for x, z, s in ((-0.35, 0.05, 0.5), (0.32, 0.25, 0.55), (-0.12, 0.6, 0.6), (0.22, 0.75, 0.45)):  # caught fire
		_fl(p, x, -0.12, z, s, glow=2.0)
	return p.build()


def thornskin():
	p = Prop("thornskin", 727)
	p.seg((0, 0.06, 0.55), (0, -0.08, 0.55), 0.58, 0.58, WOOD, sides=18)                   # a bark shield
	_ring_at(p, 0, 0.55, 0.36, 0.03, WOOD_GRAY, sides=16, y=-0.09)
	_ring_at(p, 0, 0.55, 0.18, 0.03, WOOD_GRAY, sides=12, y=-0.09)
	for k in range(10):                                                                   # ringed with thorns
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.5, 0, 0.55 + math.sin(a) * 0.5), (math.cos(a) * 0.85, 0, 0.55 + math.sin(a) * 0.85), 0.08, 0.0, PINE, sides=5)
	for x, z in ((-0.25, 0.75), (0.25, 0.75), (0.0, 0.3), (0.3, 0.4), (-0.3, 0.38)):
		p.seg((x, -0.08, z), (x * 1.2, -0.35, z + 0.08), 0.06, 0.0, LEAF, sides=5, glow=0.8)
	return p.build()


def rapid_fire():
	p = Prop("rapid_fire", 729)
	for k, (x, z) in enumerate(((-0.35, 0.95), (-0.1, 0.55), (0.15, 0.15))):             # three arrows in quick flight
		_arrow(p, (x - 0.6, 0, z), (x + 0.55, 0, z + 0.05), head=GOLD, glow=1.4)
		for j in range(2):                                                                # speed streaks
			p.seg((x - 1.05, 0.05, z + 0.08 - j * 0.16), (x - 0.7, 0.05, z + 0.08 - j * 0.16), 0.025, 0.0, GOLD, sides=4, glow=1.8)
	return p.build()


def barbed_arrow():
	p = Prop("barbed_arrow", 731)
	_arrow(p, (-0.7, 0, 0.0), (0.35, 0, 0.9), head=CRIMSON, glow=1.2, hs=1.5, barbs=True)
	for x, z, s in ((0.62, 0.55, 0.25), (0.72, 0.2, 0.2)):                                # dripping blood
		_drop(p, x, z, s, CLOTH_RED, 1.0)
	return p.build()


def frost_wind():
	p = Prop("frost_wind", 733)
	for k, (z, x1, sw) in enumerate(((0.95, 0.35, CLOTH_WHITE), (0.55, 0.55, WATER), (0.15, 0.2, CLOTH_WHITE))):  # gusts ending in curls
		p.seg((-0.85, 0, z), (x1, 0, z), 0.045, 0.045, sw, sides=5, glow=1.2)
		_swirl(p, x1, z + 0.13, 0.13, 0.02, -0.9, sw, 1.2, thick=0.05, steps=14)
	_snowflake(p, 0.65, 0.95, 0.2, 1.8)
	_snowflake(p, -0.35, 0.35, 0.14, 1.8)
	_snowflake(p, 0.55, 0.05, 0.12, 1.8)
	return p.build()


def call_of_the_hawk():
	p = Prop("call_of_the_hawk", 735)
	for sx in (-1, 1):                                                                    # spread wings
		base = 90 - sx * 90
		angs = [base + sx * d for d in (-10, 5, 20, 35, 50)]
		_feather_fan(p, sx * 0.12, 0.62, angs, 0.78, WOOD, tip=CLOTH_WHITE, r=0.09)
	_feather_fan(p, 0, 0.35, (-115, -90, -65), 0.4, WOOD, tip=CLOTH_WHITE, r=0.08)       # tail
	p.blob((0.3, 0.28, 0.55), (0, -0.05, 0.52), HIDE, segs=(10, 6))                        # body
	p.blob((0.26, 0.24, 0.26), (0, -0.05, 0.9), WOOD, segs=(8, 6))                         # head
	p.seg((0, -0.2, 0.92), (0, -0.34, 0.82), 0.06, 0.0, GOLD, sides=5)                    # hooked beak
	for sx in (-1, 1):
		p.blob((0.06, 0.04, 0.06), (sx * 0.08, -0.17, 0.95), GOLD, segs=(5, 3), glow=2.0)
	_ring(p, 0.55, -0.05, 0.035, GOLD, glow=1.8, sides=18)                                # summoning circle
	return p.build()


def volley():
	p = Prop("volley", 737)
	for deg in (50, 70, 90, 110, 130):                                                    # five arrows loosed at once
		a = math.radians(deg)
		_arrow(p, (0, 0, -0.1), (math.cos(a) * 1.25, 0, -0.1 + math.sin(a) * 1.25), glow=0.5, hs=0.9)
	_ring_at(p, 0, -0.1, 1.45, 0.03, GOLD, glow=1.6, sides=16, a0=math.radians(40), a1=math.radians(140))
	return p.build()


def guardian_of_the_wild():
	p = Prop("guardian_of_the_wild", 739)
	p.blob((0.42, 0.38, 0.52), (0, 0, 0.45), HIDE, segs=(10, 8))                           # a stag's head
	p.seg((0, -0.12, 0.35), (0, -0.3, 0.05), 0.17, 0.1, HIDE, sides=8)                    # muzzle
	p.blob((0.12, 0.08, 0.08), (0, -0.33, 0.06), STONE_DARK, segs=(6, 4))
	for sx in (-1, 1):
		p.blob((0.08, 0.05, 0.08), (sx * 0.13, -0.18, 0.52), LEAF, segs=(6, 4), glow=2.6)
		p.seg((sx * 0.2, 0, 0.55), (sx * 0.42, 0.05, 0.62), 0.07, 0.0, HIDE, sides=5)      # ears
		pts = [(sx * 0.12, 0, 0.72), (sx * 0.3, 0, 0.95), (sx * 0.5, 0, 1.15), (sx * 0.62, 0, 1.4)]  # antlers of light
		for a, b in zip(pts, pts[1:]):
			p.seg(a, b, 0.05, 0.04, LEAF, sides=5, glow=1.5)
		for (bx, bz), (tx, tz) in (((0.3, 0.95), (0.18, 1.25)), ((0.5, 1.15), (0.4, 1.42)), ((0.4, 1.05), (0.72, 1.1))):
			p.seg((sx * bx, 0, bz), (sx * tx, 0, tz), 0.04, 0.0, LEAF, sides=5, glow=1.5)
	_ring(p, 0.62, -0.05, 0.035, GOLD, glow=1.6, sides=18)
	return p.build()


def natures_renewal():
	p = Prop("natures_renewal", 741)
	p.seg((0, 0, 0.0), (0, 0, 0.55), 0.12, 0.08, WOOD, sides=7)                          # a tree of life
	for sx in (-1, 1):
		p.seg((0, 0, 0.05), (sx * 0.3, 0, -0.02), 0.07, 0.02, WOOD, sides=5)
		p.seg((0, 0, 0.45), (sx * 0.25, 0, 0.7), 0.05, 0.03, WOOD, sides=5)
	for x, z, s in ((0, 0.95, 0.62), (-0.35, 0.78, 0.46), (0.35, 0.78, 0.46), (-0.2, 1.15, 0.4), (0.22, 1.12, 0.42)):
		p.blob((s, s * 0.8, s * 0.85), (x, 0, z), LEAF, segs=(10, 6), glow=1.3)
	for k in range(7):                                                                    # golden motes round it
		a = k * math.tau / 7
		p.blob((0.09, 0.09, 0.09), (math.cos(a) * 0.8, -0.2, 0.7 + math.sin(a) * 0.6), GOLD, segs=(6, 4), glow=2.4)
	_ring(p, 0.55, 0.0, 0.035, LEAF, glow=1.8, sides=18)
	return p.build()


def piercing_shot():
	p = Prop("piercing_shot", 743)
	n = Vector((0.75, -0.66, 0.0))
	c = Vector((0.0, 0.0, 0.5))
	p.seg(tuple(c - n * 0.06), tuple(c + n * 0.06), 0.5, 0.5, WOOD, sides=14)            # a plank shield, run through
	side = Vector((0.66, 0.75, 0.0))
	for k in (-1, 1):                                                                     # its plank seams
		off = c - n * 0.075 + Vector((0, 0, k * 0.2))
		p.seg(tuple(off - side * 0.42), tuple(off + side * 0.42), 0.02, 0.02, WOOD_GRAY, sides=4)
	_arrow(p, (-0.95, 0, 0.2), (0.85, 0, 0.8), glow=0.8, hs=1.1)
	for k in range(6):                                                                    # splinters bursting out
		a = k * math.tau / 6 + 0.3
		p.box((0.16, 0.05, 0.05), (0.18 + math.cos(a) * 0.16, -0.12, 0.58 + math.sin(a) * 0.16), WOOD, rot=(0, -math.degrees(a), 0))
	for j in (-1, 1):                                                                     # a streak along its path
		p.seg((-0.95, 0.05, 0.2 + j * 0.1), (-0.35, 0.05, 0.4 + j * 0.1), 0.025, 0.0, CLOTH_WHITE, sides=4, glow=1.6)
	return p.build()


def wildfire():
	p = Prop("wildfire", 745)
	p.seg((0, 0, 0.0), (0, 0, 0.25), 0.08, 0.08, WOOD, sides=6)                          # a pine, burning
	for k, (z, r) in enumerate(((0.2, 0.5), (0.5, 0.4), (0.78, 0.3))):
		p.seg((0, 0, z), (0, 0, z + 0.45), r, 0.0, PINE, sides=8)
	for x, y, z, s in ((-0.45, -0.2, 0.0, 0.55), (0.45, -0.2, 0.0, 0.6), (-0.22, -0.3, 0.35, 0.5), (0.25, -0.3, 0.55, 0.45), (0.0, -0.1, 0.9, 0.55)):
		_fl(p, x, y, z, s, glow=2.2)
	p.blob((1.6, 0.9, 0.1), (0, 0, 0.0), STONE_DARK, segs=(12, 4))
	return p.build()


def hawks_fury():
	p = Prop("hawks_fury", 747)
	p.blob((0.62, 0.5, 0.58), (-0.3, 0, 0.6), WOOD, segs=(10, 8))                           # a hawk's head, screaming
	p.blob((0.36, 0.3, 0.3), (-0.22, -0.12, 0.48), CLOTH_WHITE, segs=(8, 6))                 # pale cheek
	p.seg((-0.05, 0, 0.66), (0.28, 0, 0.6), 0.14, 0.05, GOLD, sides=6)                     # hooked beak
	p.seg((0.28, 0, 0.6), (0.3, 0, 0.44), 0.05, 0.0, GOLD, sides=5)
	p.seg((-0.05, 0, 0.52), (0.18, 0, 0.44), 0.06, 0.0, GOLD, sides=5)
	p.blob((0.14, 0.06, 0.1), (-0.12, -0.25, 0.72), FLAME, segs=(6, 4), glow=3.0)           # a furious eye
	p.seg((-0.25, -0.24, 0.84), (0.0, -0.24, 0.76), 0.04, 0.04, STONE_DARK, sides=4)        # its brow
	for k in range(3):                                                                    # fiery talon rakes
		x = 0.45 + k * 0.2
		p.seg((x, -0.1, 1.15 - k * 0.05), (x - 0.25, -0.1, 0.05 - k * 0.05), 0.06, 0.02, FLAME, sides=4, glow=2.2)
	for k in range(3):
		p.seg((-0.55, 0.05, 0.85 - k * 0.12), (-0.95, 0.05, 0.95 - k * 0.2), 0.08, 0.02, WOOD, sides=5)   # swept-back crest
	return p.build()


def trueshot():
	p = Prop("trueshot", 749)
	for k, (r, sw) in enumerate(((0.62, CLOTH_RED), (0.48, CLOTH_WHITE), (0.34, CLOTH_RED), (0.2, CLOTH_WHITE), (0.08, GOLD))):  # a target
		p.seg((0, 0.04 - k * 0.025, 0.6), (0, -0.0 - k * 0.025, 0.6), r, r, sw, sides=20, glow=2.0 if sw == GOLD else 0.0)
	for sx in (-1, 1):
		p.seg((sx * 0.3, 0.1, 0.3), (sx * 0.5, 0.25, -0.2), 0.05, 0.05, WOOD, sides=5)
	_arrow(p, (-0.62, -0.75, 1.1), (0, -0.12, 0.6), glow=1.0)                             # dead center
	for k in range(8):
		a = k * math.tau / 8
		p.seg((math.cos(a) * 0.1, -0.2, 0.6 + math.sin(a) * 0.1), (math.cos(a) * 0.3, -0.2, 0.6 + math.sin(a) * 0.3), 0.025, 0.0, GOLD, sides=4, glow=2.4)
	return p.build()


def storm_of_arrows():
	p = Prop("storm_of_arrows", 751)
	for x, z, s in ((-0.45, 1.25, 0.55), (0.1, 1.35, 0.65), (0.55, 1.22, 0.5), (-0.1, 1.15, 0.5)):  # a dark cloud
		p.blob((s, s * 0.6, s * 0.7), (x, 0.1, z), STONE_DARK, segs=(10, 6))
	for k, (x, z) in enumerate(((-0.7, 0.55), (-0.45, 0.2), (-0.2, 0.65), (0.05, 0.1), (0.3, 0.55), (0.55, 0.15), (0.75, 0.6), (-0.05, -0.3))):  # raining arrows
		_arrow(p, (x - 0.08, -0.1, z + 0.55), (x + 0.08, -0.1, z), glow=0.8, hs=0.7, r=0.028)
	return p.build()


def mighty_blow():
	p = Prop("mighty_blow", 753)
	p.blob((1.6, 1.0, 0.12), (0, 0, 0.0), STONE_DARK, segs=(12, 4))                          # the ground, cracking
	for k in range(5):
		a = k * math.tau / 5 + 0.4
		p.seg((0, 0, 0.06), (math.cos(a) * 0.75, math.sin(a) * 0.5, 0.06), 0.04, 0.01, FLAME, sides=4, glow=2.0)
	c = Vector((-0.05, 0, 0.42))
	d = Vector((0.55, 0, 0.83)).normalized()
	perp = Vector((-d.z, 0, d.x))
	p.seg(tuple(c), tuple(c + d * 1.0), 0.06, 0.06, WOOD, sides=6)                         # a great maul
	p.seg(tuple(c - perp * 0.42), tuple(c + perp * 0.42), 0.25, 0.25, STONE_LIGHT, sides=8)
	for sgn in (-1, 1):
		p.seg(tuple(c + perp * sgn * 0.3), tuple(c + perp * sgn * 0.36), 0.27, 0.27, IRON, sides=8)
	p.blob((0.12, 0.12, 0.12), tuple(c + d * 1.02), IRON, segs=(6, 4))
	for k in range(9):                                                                    # the impact
		a = math.pi * (0.05 + k * 0.11)
		p.seg((0.25 + math.cos(a) * 0.4, -0.3, 0.05 + math.sin(a) * 0.35), (0.25 + math.cos(a) * 0.75, -0.3, 0.05 + math.sin(a) * 0.62),
			  0.045, 0.0, GOLD, sides=4, glow=2.2)
	return p.build()


def unbreakable():
	p = Prop("unbreakable", 755)
	_ring_at(p, 0, 0.5, 0.8, 0.04, CLOTH_WHITE, glow=1.6, sides=24, y=0.3)                # a silver halo
	p.box((1.0, 0.42, 0.22), (0.05, 0, 0.75), STONE_LIGHT)                                 # an anvil
	p.seg((-0.45, 0, 0.75), (-0.85, 0, 0.8), 0.12, 0.0, STONE_LIGHT, sides=8)             # its horn
	p.box((0.4, 0.3, 0.35), (0.05, 0, 0.5), STONE_LIGHT)
	p.box((0.8, 0.5, 0.2), (0.05, 0, 0.23), STONE_LIGHT)
	p.box((1.02, 0.44, 0.04), (0.05, 0, 0.87), CLOTH_WHITE, glow=1.2)
	for x, z, g in ((0.62, 1.1, 0.3), (-0.62, 0.15, 0.22)):                              # a glint
		p.seg((x, -0.25, z - g), (x, -0.25, z + g), 0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.5)
		p.seg((x, -0.25, z + g * 0.05), (x, -0.25, z - g), 0.04, 0.0, CLOTH_WHITE, sides=4, glow=2.5)
		p.seg((x - g * 0.7, -0.25, z), (x + g * 0.7, -0.25, z), 0.03, 0.03, CLOTH_WHITE, sides=4, glow=2.5)
	return p.build()


def _axe(p, a, b, flip=1):
	a, b = Vector(a), Vector(b)
	d = (b - a).normalized()
	n = Vector((-d.z, 0, d.x)) * flip
	fwd = Vector((0, -0.07, 0))
	p.seg(a, b + d * 0.05, 0.055, 0.055, WOOD, sides=6)
	top, bot = b - d * 0.02, b - d * 0.5
	pts = [top, top + n * 0.3 + d * 0.1, top + n * 0.6 + d * 0.14, bot + n * 0.6 - d * 0.14, bot + n * 0.3 - d * 0.1, bot]
	p.poly([tuple(v + fwd) for v in pts], [(0, 1, 2, 3, 4, 5)], STONE_LIGHT)
	e0, e1 = top + n * 0.6 + d * 0.14, bot + n * 0.6 - d * 0.14
	p.seg(tuple(e0 + fwd), tuple(e1 + fwd), 0.035, 0.035, CLOTH_WHITE, sides=4, glow=1.0)   # its bright edge
	p.box((0.16, 0.16, 0.16), tuple(b - d * 0.2), IRON)


def rampage():
	p = Prop("rampage", 757)
	for k in range(12):                                                                   # a red burst of rage
		a = k * math.tau / 12
		r1 = 0.95 if k % 2 else 0.7
		p.seg((math.cos(a) * 0.25, 0.3, 0.5 + math.sin(a) * 0.25), (math.cos(a) * r1 * 0.9, 0.3, 0.5 + math.sin(a) * r1 * 0.9), 0.12, 0.0,
			  CRIMSON if k % 2 else CLOTH_RED, sides=5, glow=1.8)
	_axe(p, (-0.55, 0, -0.1), (0.55, 0, 1.0), flip=-1)                                    # two axes crossed
	_axe(p, (0.55, -0.1, -0.1), (-0.55, -0.1, 1.0), flip=1)
	return p.build()


def superior_healing():
	p = Prop("superior_healing", 759)
	for sx in (-1, 1):                                                                    # wings of light
		base = 90 - sx * 90
		_feather_fan(p, sx * 0.2, 0.62, [base + sx * d for d in (-25, -5, 15, 35)], 0.7, CLOTH_WHITE, glow=1.0, r=0.1)
	p.box((0.26, 0.24, 0.95), (0, -0.05, 0.5), GOLD, glow=2.2)                               # a great gold cross
	p.box((0.7, 0.24, 0.26), (0, -0.05, 0.62), GOLD, glow=2.2)
	for k in range(6):
		a = k * math.tau / 6 + 0.25
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.95, -0.2, 0.55 + math.sin(a) * 0.65), LEAF, segs=(6, 4), glow=2.2)
	return p.build()


def dawns_wrath():
	p = Prop("dawns_wrath", 761)
	p.seg((0, 0.2, 0.4), (0, 0.1, 0.4), 0.5, 0.5, GOLD, sides=20, glow=2.2)               # the dawn sun on the horizon
	for k in range(7):
		a = math.radians(15 + k * 25)
		p.seg((math.cos(a) * 0.55, 0.15, 0.4 + math.sin(a) * 0.55), (math.cos(a) * 1.0, 0.15, 0.4 + math.sin(a) * 1.0), 0.07, 0.0, FLAME, sides=4, glow=2.2)
	p.box((1.9, 0.6, 0.45), (0, 0.1, 0.1), STONE_WARM)                                    # the horizon hides its lower half
	for sx in (-1, 1):                                                                    # two gleaming tusks sweeping up
		pts = [(sx * 0.55, -0.3, 0.2), (sx * 0.4, -0.35, 0.55), (sx * 0.15, -0.4, 0.8), (sx * -0.1, -0.4, 0.95)]
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			p.seg(a, b, 0.1 - i * 0.03, 0.07 - i * 0.03 if i < 2 else 0.0, BONE, sides=7, glow=0.8)
	return p.build()


def aegis_of_the_dawn():
	p = Prop("aegis_of_the_dawn", 763)
	_ring_at(p, 0, 0.55, 0.95, 0.04, CLOTH_WHITE, glow=1.4, sides=24, y=0.2)                # a group halo
	p.box((1.0, 0.12, 0.72), (0, 0.02, 0.8), GOLD, glow=0.8)                                # a kite shield, gold-rimmed
	p.seg((0, 0.02, 0.45), (0, 0.02, -0.35), 0.71, 0.0, GOLD, sides=4, glow=0.8, twist=45)
	p.box((0.84, 0.1, 0.6), (0, -0.03, 0.8), CLOTH_WHITE, glow=0.3)
	p.seg((0, -0.03, 0.51), (0, -0.03, -0.22), 0.6, 0.0, CLOTH_WHITE, sides=4, glow=0.3, twist=45)
	p.seg((0, -0.09, 0.6), (0, -0.14, 0.6), 0.28, 0.28, FLAME, sides=14, glow=2.2)          # its rising-sun blazon
	for k in range(5):
		a = math.radians(20 + k * 35)
		p.seg((math.cos(a) * 0.32, -0.12, 0.6 + math.sin(a) * 0.32), (math.cos(a) * 0.5, -0.12, 0.6 + math.sin(a) * 0.5), 0.05, 0.0, FLAME, sides=4, glow=2.4)
	p.box((0.8, 0.08, 0.2), (0, -0.12, 0.44), STONE_WARM)
	obj = p.build()
	obj.data.transform(Matrix.Rotation(math.radians(29), 4, "Z"))                          # turned to face the viewer
	return obj


def glacial_spike():
	p = Prop("glacial_spike", 765)
	p.blob((1.5, 0.9, 0.3), (0, 0, 0.0), CLOTH_WHITE, segs=(12, 5))                          # icy ground
	p.seg((-0.35, 0, 0.0), (0.3, 0, 1.0), 0.26, 0.22, WATER, sides=6, glow=1.1)            # a spear of ice as big as a man
	p.seg((0.3, 0, 1.0), (0.45, 0, 1.3), 0.22, 0.0, WATER, sides=6, glow=1.5)
	p.seg((-0.3, -0.18, 0.1), (0.35, -0.18, 1.05), 0.04, 0.02, CLOTH_WHITE, sides=4, glow=1.6)  # a bright facet
	for x, h, lean in ((-0.65, 0.4, -25), (0.35, 0.35, 30), (0.6, 0.25, 40)):
		top = (x + math.sin(math.radians(lean)) * h, -0.1, 0.05 + math.cos(math.radians(lean)) * h)
		p.seg((x, -0.1, 0.05), top, 0.1, 0.0, RUNE, sides=5, glow=1.2)
	return p.build()


def mana_ward():
	p = Prop("mana_ward", 767)
	p.seg((0, 0.06, 0.55), (0, -0.04, 0.55), 0.7, 0.7, PURPLE, sides=6, glow=1.0)          # a hexagon ward
	for k in range(6):
		a0, a1 = k * math.tau / 6, (k + 1) * math.tau / 6
		for r, sw, g in ((0.72, CLOTH_WHITE, 1.4), (0.42, RUNE, 2.0)):
			p.seg((math.cos(a0) * r, -0.06, 0.55 + math.sin(a0) * r), (math.cos(a1) * r, -0.06, 0.55 + math.sin(a1) * r), 0.035, 0.035, sw, sides=5, glow=g)
		p.seg((math.cos(a0) * 0.42, -0.06, 0.55 + math.sin(a0) * 0.42), (math.cos(a0) * 0.72, -0.06, 0.55 + math.sin(a0) * 0.72), 0.025, 0.025, RUNE, sides=4, glow=1.6)
	p.blob((0.22, 0.14, 0.34), (0, -0.1, 0.55), CLOTH_WHITE, rot=(0, 0, 0), segs=(4, 3), glow=2.6)   # a rune-gem
	return p.build()


def inferno():
	p = Prop("inferno", 769)
	p.blob((1.9, 1.0, 0.12), (0, 0.1, 0.0), STONE_DARK, segs=(12, 4))
	for x, y, s in ((-0.62, 0.1, 0.7), (0.62, 0.1, 0.75), (-0.3, -0.05, 0.95), (0.3, -0.05, 1.0), (0.0, -0.2, 1.2)):  # a wall of fire
		_fl(p, x, y, 0.0, s, glow=2.0, core=CLOTH_RED if s > 0.9 else EMBER)
	for k in range(6):                                                                    # sparks
		a = k * 1.1
		p.blob((0.07, 0.07, 0.07), (math.cos(a) * 0.7, -0.3, 1.1 + math.sin(a) * 0.25), FLAME, segs=(5, 3), glow=3.0)
	return p.build()


def shadowstrike():
	p = Prop("shadowstrike", 771)
	for x, z, s in ((-0.45, 0.25, 0.6), (-0.2, 0.05, 0.55), (-0.55, 0.6, 0.45), (-0.05, 0.35, 0.5)):  # a shadow
		p.blob((s, s * 0.8, s), (x, 0.1, z), PURPLE, segs=(10, 6), glow=0.5)
	_dagger(p, (-0.15, -0.15, 0.35), (0.85, -0.15, 1.25), edge=PETAL_PURPLE, w=0.12)                 # a blade out of it
	for k in range(3):
		p.seg((-0.3 + k * 0.1, -0.05, 0.6 + k * 0.15), (0.25 + k * 0.1, -0.05, 1.1 + k * 0.08), 0.02, 0.0, PURPLE, sides=4, glow=2.0)
	return p.build()


def blade_flurry():
	p = Prop("blade_flurry", 773)
	for k in range(4):                                                                    # daggers spinning like a wheel
		a = k * math.tau / 4 + 0.3
		base = (math.cos(a) * 0.32, 0, 0.55 + math.sin(a) * 0.32)
		tip = (math.cos(a) * 0.95, 0, 0.55 + math.sin(a) * 0.95)
		_dagger(p, base, tip, w=0.12)
		_ring_at(p, 0, 0.55, 1.0, 0.035, CLOTH_WHITE, glow=1.8, sides=6, a0=a + 0.3, a1=a + 1.25)
	p.blob((0.2, 0.2, 0.2), (0, 0, 0.55), GOLD, segs=(8, 5), glow=1.5)
	return p.build()


def deathmark():
	p = Prop("deathmark", 775)
	_ring_at(p, 0, 0.62, 0.6, 0.06, CRIMSON, glow=1.8, sides=22)                           # a mark on the foe
	for sx in (-1, 1):
		p.seg((sx * -0.45, -0.05, 1.05), (sx * 0.45, -0.05, 0.2), 0.1, 0.06, CLOTH_RED, sides=5, glow=1.6)
	for x, z, s in ((-0.25, -0.1, 0.25), (0.3, -0.2, 0.3), (0.0, -0.4, 0.22)):             # bleeding
		_drop(p, x, z, s, CLOTH_RED, 1.0)
	return p.build()


def elemental_mending():
	p = Prop("elemental_mending", 777)
	_fl(p, 0, 0.1, 0.0, 1.1, glow=1.6, core=AMBER)                                          # an elemental's flame
	p.box((0.18, 0.1, 0.6), (0, -0.35, 0.5), LEAF, glow=2.4)                                # knit back with green
	p.box((0.55, 0.1, 0.18), (0, -0.35, 0.55), LEAF, glow=2.4)
	_ring_at(p, 0, 0.6, 0.8, 0.035, LEAF, glow=1.4, sides=24, a0=math.radians(200), a1=math.radians(340))
	for k in range(3):
		p.blob((0.1, 0.1, 0.1), (-0.55 + k * 0.55, -0.3, 1.2 - (k % 2) * 0.15), LEAF, segs=(6, 4), glow=2.2)
	return p.build()


def primal_surge():
	p = Prop("primal_surge", 779)
	for v, sw in enumerate((FLAME, WATER, STONE_WARM, CLOTH_WHITE)):                      # four elements spiraling up
		pts = []
		for k in range(21):
			t = k / 20
			a = v * math.tau / 4 + t * 1.5 * math.pi
			r = 0.75 * (1 - t) + 0.08
			pts.append((math.cos(a) * r, math.sin(a) * r * 0.5, t * 0.95))
		for i, (a, b) in enumerate(zip(pts, pts[1:])):
			w = 0.1 - i * 0.003
			p.seg(a, b, w, w, sw, sides=6, glow=0.6 if sw == STONE_WARM else 1.6)
	p.seg((0, 0, 0.9), (0, 0, 1.4), 0.26, 0.0, GOLD, sides=4, glow=2.4)                   # surging to a point
	return p.build()


def call_of_the_elemental_lord():
	p = Prop("call_of_the_elemental_lord", 781)
	_elemental(p, STONE_DARK, s=1.05)                                                      # a lord of stone and fire
	p.blob((0.3, 0.1, 0.3), (0, -0.2, 0.5), EMBER, segs=(8, 6), glow=3.0)                   # molten heart
	for sx in (-1, 1):
		_fl(p, sx * 0.28, 0, 0.62, 0.3, glow=2.2)
		p.blob((0.08, 0.05, 0.06), (sx * 0.08, -0.15, 1.0), FLAME, segs=(5, 3), glow=3.0)
	for k in range(5):                                                                    # a crown
		x = -0.2 + k * 0.1
		p.seg((x, 0, 1.08), (x, 0, 1.3 if k % 2 == 0 else 1.2), 0.05, 0.0, GOLD, sides=4, glow=1.4)
	_ring(p, 0.14, 1.1, 0.03, GOLD, glow=1.4, sides=12)
	_ring(p, 0.7, 0.0, 0.04, FLAME, glow=2.0, sides=20)
	return p.build()


def soul_harvest():
	p = Prop("soul_harvest", 783)
	p.seg((0.45, 0, -0.15), (-0.3, 0, 1.15), 0.05, 0.05, WOOD, sides=6)                  # a scythe
	blade = []
	for k in range(9):
		t = k / 8
		a = math.radians(80 + t * 110)
		blade.append((-0.3 + 0.75 + math.cos(a) * 0.75, 0, 1.15 - 0.45 + math.sin(a) * 0.45))
	for i, (a, b) in enumerate(zip(blade, blade[1:])):
		w = 0.09 * (1 - i / 8) + 0.01
		p.seg(a, b, w, w * 0.9, STONE_LIGHT, sides=4)
	for x, z, s in ((0.45, 0.55, 0.3), (0.2, 0.25, 0.24), (0.62, 0.95, 0.22)):             # souls torn loose
		p.blob((s, s * 0.8, s), (x, -0.15, z), PETAL_PURPLE, segs=(8, 6), glow=2.2)
		p.seg((x, -0.15, z), (x + s * 1.3, -0.15, z - s * 0.9), s * 0.35, 0.0, PURPLE, sides=5, glow=1.8)
	return p.build()


def plague():
	p = Prop("plague", 785)
	for x, z, s in ((-0.45, 0.45, 0.6), (0.45, 0.5, 0.6), (0, 0.85, 0.6), (0, 0.2, 0.6)):  # a green miasma
		p.blob((s, s * 0.7, s * 0.8), (x, 0.3, z), SICKLY, segs=(10, 6), glow=0.9)
	_skull(p, 0, 0.5, 0.95, eyes=SICKLY, eye_glow=3.0)
	for k in range(5):                                                                    # flies
		a = k * math.tau / 5 + 0.5
		x, z = math.cos(a) * 0.72, 0.55 + math.sin(a) * 0.62
		p.blob((0.09, 0.07, 0.07), (x, -0.3, z), STONE_DARK, segs=(5, 3))
		p.blob((0.1, 0.02, 0.06), (x, -0.33, z + 0.05), CLOTH_WHITE, segs=(5, 3), glow=0.5)
	return p.build()


def raise_bone_colossus():
	p = Prop("raise_bone_colossus", 787)
	p.blob((1.7, 1.0, 0.2), (0, 0, -0.35), STONE_DARK, segs=(14, 5))
	p.seg((0, 0.05, -0.3), (0, 0.05, 0.75), 0.07, 0.07, BONE, sides=6)                    # spine
	for k in range(4):                                                                    # a great ribcage
		z = 0.62 - k * 0.2
		w = 0.62 - k * 0.07
		for sx in (-1, 1):
			pts = [(0, 0.05, z), (sx * w * 0.7, -0.05, z + 0.02), (sx * w, -0.2, z - 0.12), (sx * w * 0.7, -0.35, z - 0.25)]
			for a, b in zip(pts, pts[1:]):
				p.seg(a, b, 0.045, 0.04, BONE, sides=5)
	for sx in (-1, 1):                                                                    # shoulder knobs
		p.blob((0.3, 0.3, 0.26), (sx * 0.62, 0, 0.72), BONE, segs=(8, 6))
	_skull(p, 0, 1.0, 0.75, eyes=SICKLY, eye_glow=3.0)
	for sx in (-1, 1):                                                                    # horns
		p.seg((sx * 0.2, 0, 1.18), (sx * 0.48, 0, 1.45), 0.07, 0.0, BONE, sides=6)
	return p.build()


def glacial_roar():
	p = Prop("glacial_roar", 789)
	p.blob((0.62, 0.55, 0.58), (-0.35, 0, 0.6), WATER, segs=(10, 8), glow=0.9)           # an ice bear's head, roaring
	for sx in (-1, 1):
		p.blob((0.2, 0.12, 0.2), (-0.35 + sx * 0.2, 0.05, 0.92), WATER, segs=(8, 5), glow=0.9)   # round ears
	p.seg((-0.15, 0, 0.7), (0.25, 0, 0.78), 0.17, 0.13, WATER, sides=8, glow=0.9)          # upper jaw
	p.seg((-0.2, 0, 0.45), (0.18, 0, 0.35), 0.13, 0.1, WATER, sides=8, glow=0.9)           # lower jaw
	for k in range(3):
		x = -0.02 + k * 0.1
		p.seg((x, -0.08, 0.66), (x, -0.08, 0.54), 0.035, 0.0, CLOTH_WHITE, sides=4, glow=1.2)
		p.seg((x - 0.02, -0.08, 0.44), (x - 0.02, -0.08, 0.54), 0.03, 0.0, CLOTH_WHITE, sides=4, glow=1.2)
	p.blob((0.1, 0.06, 0.08), (0.27, -0.05, 0.82), STONE_DARK, segs=(6, 4))
	p.blob((0.1, 0.05, 0.07), (-0.2, -0.26, 0.78), CLOTH_WHITE, segs=(6, 4), glow=2.6)
	for k in range(3):                                                                    # its roar, freezing
		_ring_at(p, 0.25, 0.56, 0.3 + k * 0.2, 0.035, CLOTH_WHITE, glow=1.6, sides=8, a0=-0.7, a1=0.7)
	return p.build()


def tigirs_swarm():
	p = Prop("tigirs_swarm", 791)
	for z in (0.0, 1.0):                                                                  # an hourglass
		p.seg((0, 0, z - 0.04), (0, 0, z + 0.04), 0.38, 0.38, WOOD, sides=10)
	for k in range(3):
		a = k * math.tau / 3 + 0.5
		p.seg((math.cos(a) * 0.32, math.sin(a) * 0.32, 0.0), (math.cos(a) * 0.32, math.sin(a) * 0.32, 1.0), 0.03, 0.03, WOOD, sides=5)
	p.seg((0, 0, 0.94), (0, 0, 0.5), 0.26, 0.04, CLOTH_WHITE, sides=10, glow=0.3)
	p.seg((0, 0, 0.06), (0, 0, 0.5), 0.26, 0.04, CLOTH_WHITE, sides=10, glow=0.3)
	p.seg((0, -0.02, 0.07), (0, -0.02, 0.3), 0.22, 0.0, AMBER, sides=10, glow=1.2)        # sand running low
	_swarm(p, 7, 0.65, AMBER, 1.2, 13)
	return p.build()


def ancestral_avatar():
	p = Prop("ancestral_avatar", 793)
	for k in range(9):                                                                    # a headdress of feathers
		deg = 20 + k * 17.5
		a = math.radians(deg)
		_feather_fan(p, 0, 0.62, (deg,), 0.72, CLOTH_WHITE if k % 2 else CLOTH_RED, tip=STONE_DARK, glow=0.6, r=0.08)
	p.blob((0.72, 0.25, 0.92), (0, -0.05, 0.5), GOLD, segs=(12, 8), glow=1.2)                # a spirit mask
	for sx in (-1, 1):
		p.blob((0.2, 0.1, 0.12), (sx * 0.15, -0.18, 0.62), STONE_DARK, segs=(8, 4))
		p.blob((0.08, 0.05, 0.06), (sx * 0.15, -0.22, 0.62), CLOTH_WHITE, segs=(5, 3), glow=3.0)
		p.box((0.05, 0.03, 0.25), (sx * 0.24, -0.16, 0.38), CLOTH_RED)
	p.seg((0, -0.15, 0.55), (0, -0.25, 0.4), 0.06, 0.04, AMBER, sides=5)
	p.box((0.28, 0.05, 0.06), (0, -0.2, 0.24), STONE_DARK)
	return p.build()


def harpy_shriek():
	p = Prop("harpy_shriek", 795)
	_feather_fan(p, -0.4, 0.62, (100, 130, 160, 190), 0.55, WOOD, tip=CLOTH_WHITE, r=0.08)   # a feathered mane
	p.blob((0.46, 0.4, 0.5), (-0.3, 0, 0.62), HIDE, segs=(10, 8))                             # a harpy's head
	p.seg((-0.12, 0, 0.7), (0.2, 0, 0.72), 0.1, 0.0, GOLD, sides=5)                           # beak, open
	p.seg((-0.12, 0, 0.58), (0.12, 0, 0.47), 0.07, 0.0, GOLD, sides=5)
	p.blob((0.1, 0.05, 0.08), (-0.22, -0.2, 0.74), CLOTH_RED, segs=(6, 4), glow=2.6)
	for k in range(3):                                                                    # the shriek
		_ring_at(p, 0.15, 0.6, 0.28 + k * 0.2, 0.035, GOLD, glow=1.8, sides=8, a0=-0.75, a1=0.75)
	return p.build()


def monk_palm():
	p = Prop("monk_palm", 797)
	for k in range(10):                                                                   # the force of the blow
		a = k * math.tau / 10
		p.seg((math.cos(a) * 0.5, 0.25, 0.6 + math.sin(a) * 0.5), (math.cos(a) * 0.95, 0.25, 0.6 + math.sin(a) * 0.95), 0.06, 0.0, AMBER, sides=4, glow=2.0)
	p.blob((0.55, 0.22, 0.55), (0, 0, 0.45), HIDE, segs=(10, 6))                            # an open palm
	for k, (x, h) in enumerate(((-0.2, 0.4), (-0.07, 0.48), (0.07, 0.46), (0.2, 0.38))):
		p.seg((x, 0, 0.65), (x * 1.1, 0, 0.65 + h), 0.07, 0.06, HIDE, sides=6)
		p.blob((0.12, 0.12, 0.12), (x * 1.1, 0, 0.65 + h), HIDE, segs=(6, 4))
	p.seg((-0.25, 0, 0.4), (-0.48, 0, 0.62), 0.08, 0.06, HIDE, sides=6)                   # thumb
	p.seg((0, 0, 0.2), (0, 0, -0.15), 0.18, 0.18, CLOTH_WHITE, sides=8)                   # a wrapped wrist
	return p.build()


def ember_breath():
	p = Prop("ember_breath", 799)
	p.blob((0.55, 0.45, 0.45), (-0.5, 0, 0.7), STONE_DARK, segs=(10, 6))                   # a drake's head
	p.seg((-0.3, 0, 0.78), (0.05, 0, 0.72), 0.16, 0.1, STONE_DARK, sides=7)               # upper jaw
	p.seg((-0.35, 0, 0.55), (0.0, 0, 0.5), 0.1, 0.07, STONE_DARK, sides=7)                 # lower jaw, gaping
	for sx in (-1, 1):
		p.seg((-0.6, sx * 0.12, 0.85), (-0.95, sx * 0.12, 1.1), 0.08, 0.0, BONE, sides=5)  # horns
	p.blob((0.12, 0.06, 0.07), (-0.38, -0.2, 0.84), FLAME, segs=(6, 4), glow=3.0)
	for k in range(9):                                                                    # a breath of embers
		t = k / 8
		x = 0.05 + t * 0.85
		z = 0.63 - t * 0.35 + math.sin(k * 2.1) * t * 0.2
		s = 0.12 + t * 0.14
		p.blob((s, s, s), (x, -0.05, z), EMBER if k % 2 else FLAME, segs=(6, 4), glow=2.6)
	return p.build()


def cinder_bolt():
	p = Prop("cinder_bolt", 801)
	for k in range(4):                                                                    # a trail of ash smoke
		x, z, s = 0.0 - k * 0.3, 0.55 - k * 0.14, 0.46 - k * 0.08
		p.blob((s, s * 0.8, s * 0.9), (x, 0.1, z), MIST, segs=(8, 6), jitter=0.03)
	p.rock((0.78, 0.7, 0.7), (0.4, 0, 0.72), STONE_DARK, jitter=0.1)                        # a burning cinder
	p.blob((0.62, 0.5, 0.55), (0.42, 0.05, 0.72), EMBER, segs=(8, 6), glow=2.0)             # glowing through its cracks
	for a, b in (((0.2, 0.95), (0.4, 0.72)), ((0.4, 0.72), (0.62, 0.85)), ((0.4, 0.72), (0.36, 0.45)), ((0.62, 0.85), (0.7, 0.62))):
		p.seg((a[0], -0.36, a[1]), (b[0], -0.36, b[1]), 0.045, 0.045, FLAME, sides=4, glow=3.0)
	for k in range(6):                                                                    # and sparks
		p.blob((0.08, 0.08, 0.08), (0.0 - k * 0.2, -0.3, 0.85 - k * 0.1 + (k % 2) * 0.2), FLAME, segs=(5, 3), glow=3.0)
	return p.build()


def ash_chill():
	p = Prop("ash_chill", 803)
	p.blob((0.55, 0.4, 0.55), (0, 0, 0.85), STONE_LIGHT, segs=(10, 8), glow=0.3)             # an ash wraith
	p.seg((0, 0, 0.8), (0.1, 0, 0.2), 0.27, 0.12, STONE_LIGHT, sides=8, glow=0.3)
	_swirl(p, 0.2, 0.2, 0.2, 0.05, 1.0, STONE_LIGHT, 0.3, thick=0.1, steps=12)
	for sx in (-1, 1):
		p.blob((0.12, 0.06, 0.16), (sx * 0.1, -0.2, 0.88), STONE_DARK, segs=(6, 4))
	p.blob((0.12, 0.06, 0.1), (0, -0.2, 0.72), STONE_DARK, segs=(6, 4))
	for sx in (-1, 1):                                                                    # reaching, clawed arms
		p.seg((sx * 0.2, 0, 0.62), (sx * 0.6, -0.1, 0.5), 0.07, 0.03, STONE_LIGHT, sides=5, glow=0.3)
		for d in (-0.1, 0.0, 0.1):
			p.seg((sx * 0.6, -0.1, 0.5), (sx * 0.72, -0.12, 0.5 + d), 0.025, 0.0, STONE_LIGHT, sides=4)
	for k in range(8):                                                                    # drifting ash
		a = k * 0.8
		p.blob((0.06, 0.06, 0.06), (math.cos(a) * (0.5 + 0.05 * k), -0.2, 0.55 + math.sin(a) * 0.5), MIST, segs=(5, 3))
	return p.build()


def searing_blow():
	p = Prop("searing_blow", 805)
	p.blob((1.7, 1.0, 0.12), (0, 0, 0.0), STONE_DARK, segs=(12, 4))
	for k in range(6):                                                                    # molten cracks
		a = k * math.tau / 6
		p.seg((0, 0, 0.06), (math.cos(a) * 0.8, math.sin(a) * 0.5, 0.06), 0.045, 0.01, EMBER, sides=4, glow=2.4)
	p.rock((0.6, 0.55, 0.55), (0, 0, 0.35), EMBER, jitter=0.08)                               # a glowing lump of rock
	p.blob((0.4, 0.4, 0.36), (0, -0.06, 0.38), FLAME, segs=(8, 6), glow=2.2)
	for k in range(7):                                                                    # splashing on impact
		a = math.radians(20 + k * 23)
		p.seg((math.cos(a) * 0.35, -0.2, 0.25 + math.sin(a) * 0.3), (math.cos(a) * 0.8, -0.2, 0.25 + math.sin(a) * 0.7), 0.06, 0.0, FLAME, sides=4, glow=2.4)
		p.blob((0.1, 0.1, 0.1), (math.cos(a) * 0.88, -0.2, 0.25 + math.sin(a) * 0.78), EMBER, segs=(5, 3), glow=2.6)
	return p.build()


NEW_SPELLS = [false_sunfire, aimed_shot, track, flame_lick, ensnare, salve, strength_of_the_wild, icicle, entangle, eagle_eye,
			  multishot, natures_mend, call_of_flame, thornskin, rapid_fire, barbed_arrow, frost_wind, call_of_the_hawk, volley,
			  guardian_of_the_wild, natures_renewal, piercing_shot, wildfire, hawks_fury, trueshot, storm_of_arrows, mighty_blow,
			  unbreakable, rampage, superior_healing, dawns_wrath, aegis_of_the_dawn, glacial_spike, mana_ward, inferno, shadowstrike,
			  blade_flurry, deathmark, elemental_mending, primal_surge, call_of_the_elemental_lord, soul_harvest, plague,
			  raise_bone_colossus, glacial_roar, tigirs_swarm, ancestral_avatar, harpy_shriek, monk_palm, ember_breath, cinder_bolt,
			  ash_chill, searing_blow]


SPELLS = {f.__name__: f for f in [kick, taunt, bash, bind_wound, battle_cry, minor_healing, light_healing,
								  circle_of_mending, strike, smite, blast_of_frost, fire_bolt, burning_embers,
								  gate, root, minor_shielding, courage, hearthward, hearthbond, blessing_of_the_elders,
								  heroic_strike, rally, shield_wall, healing, blessed_armor, circle_of_renewal,
								  hallowed_strike, frost_lance, emberstorm, greater_shielding, ice_comet,
								  thornback_venom, grave_chill, spirit_bolt, leech_bite, marsh_bolt, drowning_cold,
								  backstab, hide, sneak, evade, envenom_blade, rogue_venom, rake,
								  provoke, defensive_stance, cleave, greater_healing, divine_aura, sunfire, lightning_bolt, frost_snare,
								  fireball, assassinate, blind, deadly_poison, deadly_venom, dawn_tusk_blessing,
								  scorpion_venom, salt_gaze, shield_slam, battle_fury, whirlwind, healing_tide, word_of_awe,
								  armor_of_faith, chain_lightning, arcane_harvest, meteor, crippling_poison, crippling_venom, eviscerate, vanish,
								  storm_bolt, frog_poison, death_roll, tide_trunk_blessing, fish,
								  call_of_earth, call_of_water, call_of_fire, call_of_air, call_of_the_primal, renew_elements, greater_renewal, burnout, elemental_bond, primal_fury, elemental_aegis,
								  raise_bones, raise_skeletal_knight, mend_bones, dark_empowerment, lifetap, siphon_life, soul_rend, disease_cloud, venom_bolt,
								  bond_of_death, dread, mass_dread, feign_death, clinging_darkness, elemental_flame, gust_of_wind,
								  frost_rift, sicken, strengthen, inner_fire, drowsy, spirit_of_bear, spirit_mend, tainted_breath, feet_like_cat,
								  frost_strike, walking_sleep, spirit_healing, quickness, talisman_of_the_totem, envenomed_breath, spirit_regrowth,
								  tagars_insects, winters_roar, spirit_of_the_wolf, chant_of_the_pack, winters_grasp, turgurs_insects, kraggs_mending, ancestral_ward, homeward] + NEW_SPELLS}
ACTIONS = {f.__name__: f for f in [action_attack, action_ranged, action_sit, action_consider, action_skills, action_hail, action_loot,
								   action_pet_attack, action_pet_back, action_pet_follow, action_pet_guard, action_pet_sit]}


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	opts = {"--out": "assets/icons", "--only": "", "--size": "128"}
	for i, a in enumerate(argv):
		if a in opts and i + 1 < len(argv):
			opts[a] = argv[i + 1]
	os.makedirs(opts["--out"], exist_ok=True)
	only = set(opts["--only"].split(",")) if opts["--only"] else None
	spells = json.load(open(os.path.join(icons.ROOT, "data/spells.json")))
	missing = [s for s in spells if s not in SPELLS and not s.startswith(("meal_", "potion_"))]  # those show their item's icon
	jobs = [("spell_" + k, f) for k, f in SPELLS.items()] + list(ACTIONS.items())
	for name, build in jobs:
		if only and name not in only and name.replace("spell_", "") not in only:
			continue
		props.reset_scene()
		props._materials.clear()
		build()
		icons.render_icon(os.path.abspath(os.path.join(opts["--out"], name + ".png")), int(opts["--size"]))
		print("icon %s" % name)
	if missing:
		print("NO ICON (add a builder): %s" % ", ".join(missing))


if __name__ == "__main__":
	main()
