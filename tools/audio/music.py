"""Original zone music in the spirit of classic EverQuest's MIDI themes: gentle
modal loops, one per zone, synthesized here from scratch (no samples) and
encoded to OGG Vorbis with Blender's bundled FFmpeg.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        -P tools/audio/music.py -- --out assets/music [--only greenmoor] [--wav]

Every track is a small score: a key and mode, a tempo and meter, a chord
progression per section, and a form (A A' B A). Melodies are composed per
phrase from the chords (chord tones on strong beats, scale steps between,
a contour that rises and settles, cadences on the tonic) with a seeded random
source, so a track always comes out the same. Phrase A is written once and
reused, varied, so each piece has a tune you can recognize.

Instruments are additive synthesis in numpy: harp and lute (plucked partials
decaying at different rates), a recorder-like flute (vibrato, breath), a soft
pad, a round bass, a frame drum and a bell; a convolution reverb (decaying
noise) puts them in one room. Tracks loop seamlessly: the reverb tail wraps
onto the start.
"""

import math
import os
import sys
import wave

import numpy as np

SR = 44100
MODES = {
	"major": [0, 2, 4, 5, 7, 9, 11],
	"mixolydian": [0, 2, 4, 5, 7, 9, 10],
	"dorian": [0, 2, 3, 5, 7, 9, 10],
	"aeolian": [0, 2, 3, 5, 7, 8, 10],
	"phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],  # the desert's raised third over a flat second
	"phrygian": [0, 1, 3, 5, 7, 8, 10],  # minor with a flat second: the fire god's darker color
	"lydian": [0, 2, 4, 6, 7, 9, 11],  # major with a raised fourth: bright, floating, unresolved
}


# ---------------------------------------------------------------- instruments

def _t(dur):
	return np.arange(int(dur * SR)) / SR


def _env(n, attack, release):
	e = np.ones(n)
	a = min(int(attack * SR), n)
	r = min(int(release * SR), n - a)
	if a > 0:
		e[:a] = np.linspace(0, 1, a)
	if r > 0:
		e[n - r:] *= np.linspace(1, 0, r)
	return e


def harp(f, dur, vel=0.6, bright=1.0):
	t = _t(dur + 1.8)
	out = np.zeros_like(t)
	for k in range(1, 9):
		if f * k > SR / 2.2:
			break
		out += (1.0 / k ** (1.5 - 0.3 * bright)) * np.sin(2 * np.pi * f * k * t + k) * np.exp(-t * (1.1 + 0.8 * k))
	return out * _env(len(t), 0.004, 0.2) * vel * 0.5


def lute(f, dur, vel=0.6):
	t = _t(dur + 1.0)
	out = np.zeros_like(t)
	for k in range(1, 11):
		if f * k > SR / 2.2:
			break
		det = 1.0 + 0.0015 * (k % 3 - 1)
		out += (1.0 / k ** 1.05) * np.sin(2 * np.pi * f * k * det * t) * np.exp(-t * (2.2 + 1.4 * k))
	return out * _env(len(t), 0.003, 0.15) * vel * 0.45


def flute(f, dur, vel=0.6, rng=None):
	t = _t(dur + 0.25)
	vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.25) / 0.4, 0, 1)  # vibrato eases in
	phase = 2 * np.pi * f * np.cumsum(vib) / SR
	tone = np.sin(phase) + 0.22 * np.sin(2 * phase) + 0.07 * np.sin(3 * phase)
	noise = (rng or np.random.default_rng(1)).standard_normal(len(t))
	breath = np.convolve(noise, np.ones(40) / 40, mode="same") * 0.35
	e = _env(len(t), 0.07, 0.22) * (0.85 + 0.15 * np.exp(-t * 3))  # a little push at the start
	return (tone + breath) * e * vel * 0.32


def pad(f, dur, vel=0.4):
	t = _t(dur + 1.5)
	out = np.zeros_like(t)
	for det in (-0.004, 0.0, 0.0045):
		for k in range(1, 6):
			out += (1.0 / k ** 1.6) * np.sin(2 * np.pi * f * (1 + det) * k * t + det * 900)
	out *= 1.0 + 0.08 * np.sin(2 * np.pi * 0.35 * t)
	return out * _env(len(t), min(1.2, dur * 0.5), 1.5) * vel * 0.09


def bass(f, dur, vel=0.6):
	t = _t(dur + 0.6)
	out = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 3)
	return out * np.exp(-t * 1.2) * _env(len(t), 0.006, 0.3) * vel * 0.5


def drum(vel=0.5, rng=None, low=1.0):
	"""A frame drum; low < 1 tunes it down and lets it ring longer (a deep heartbeat)."""
	t = _t(0.6 / low)
	f = (62 + 40 * np.exp(-t * 18)) * low
	body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7 * low)
	noise = (rng or np.random.default_rng(2)).standard_normal(len(t))
	slap = np.convolve(noise, np.ones(8) / 8, mode="same") * np.exp(-t * 60) * 0.5
	return (body + slap) * vel * 0.5


def snare(vel=0.5, rng=None):
	"""A tight frame drum with a rattle: a bright hiss over a short high body, for marching."""
	t = _t(0.35)
	noise = (rng or np.random.default_rng(4)).standard_normal(len(t))
	hiss = (noise - np.convolve(noise, np.ones(5) / 5, mode="same")) * np.exp(-t * 20)  # the high part of the noise
	body = np.sin(2 * np.pi * (180 + 60 * np.exp(-t * 40)) * t) * np.exp(-t * 28)
	return (hiss * 0.8 + body * 0.6) * _env(len(t), 0.001, 0.05) * vel * 0.42


def horn(f, dur, vel=0.6):
	"""A soft brass voice: the upper partials swell in after the attack."""
	t = _t(dur + 0.3)
	vib = 1.0 + 0.003 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.2) / 0.3, 0, 1)
	phase = 2 * np.pi * f * np.cumsum(vib) / SR
	bright = np.clip(t / 0.12, 0, 1)
	out = np.zeros_like(t)
	for k in range(1, 9):
		if f * k > SR / 2.2:
			break
		out += (1.0 / k ** 1.3) * np.sin(k * phase) * (bright if k > 2 else 1.0)
	return out * _env(len(t), 0.05, 0.2) * vel * 0.2


def bell(f, dur, vel=0.4):
	t = _t(dur + 3.0)
	out = np.zeros_like(t)
	for ratio, amp, decay in ((1.0, 1.0, 0.9), (2.76, 0.45, 1.8), (5.4, 0.25, 3.2), (8.9, 0.1, 5.0)):
		out += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * decay)
	return out * _env(len(t), 0.002, 0.5) * vel * 0.18


def anvil(f=880.0, vel=0.5, rng=None):
	"""A hammer on an anvil: a bright, inharmonic metal ring that dies fast,
	with a hard click of noise at the strike."""
	t = _t(1.4)
	out = np.zeros_like(t)
	for ratio, amp, decay in ((1.0, 1.0, 5.0), (2.41, 0.6, 7.0), (3.93, 0.4, 9.0), (5.37, 0.25, 12.0), (7.12, 0.15, 16.0)):
		out += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * decay)
	noise = (rng or np.random.default_rng(3)).standard_normal(len(t))
	click = noise * np.exp(-t * 180) * 0.6
	return (out + click) * _env(len(t), 0.001, 0.1) * vel * 0.16


# ---------------------------------------------------------------- theory

def midi_hz(m):
	return 440.0 * 2 ** ((m - 69) / 12)


class Key:
	def __init__(self, root, mode):
		self.root = root  # midi note of the tonic (octave 4-ish)
		self.steps = MODES[mode]

	def note(self, degree, octave=0):
		"""Scale degree (0 = tonic, may be negative or above 6) to a midi note."""
		o, d = divmod(degree, 7)
		return self.root + 12 * (o + octave) + self.steps[d]

	def chord(self, degree):
		"""Degrees of the triad on a scale degree."""
		return [degree, degree + 2, degree + 4]


# ---------------------------------------------------------------- composing

RHYTHMS = {  # per bar, in beats; 3/4 and 4/4
	3: [[2, 1], [1, 1, 1], [1.5, 0.5, 1], [3], [1, 2], [0.5, 0.5, 1, 1]],
	4: [[2, 2], [1, 1, 2], [1.5, 0.5, 2], [4], [2, 1, 1], [1, 1, 1, 1], [3, 1]],
}


def compose_phrase(key, chords, beats, rng, low=7, high=14, cadence=True, sparse=0.0, avoid=()):
	"""A melody over one chord per bar: [(start beat, length beats, degree)].
	Strong beats land on chord tones, the rest step through the scale, the
	contour rises in the middle of the phrase and settles, and the last note
	rests long on the tonic (or the chord's root for a half cadence). Scale
	degrees in `avoid` (0-6) are left out where possible: skipping the 4th
	and 7th makes a major-mode tune pentatonic."""
	notes = []
	cur = 9  # start around the third above the tonic, an octave up
	bars = len(chords)
	for b, ch in enumerate(chords):
		rhythm = list(RHYTHMS[beats][rng.integers(len(RHYTHMS[beats]))])
		if b == bars - 1:
			rhythm = [beats]  # end the phrase on one long note
		pos = 0.0
		target_high = low + (high - low) * math.sin(math.pi * (b + 0.5) / bars)  # arch contour
		for i, length in enumerate(rhythm):
			strong = pos == 0 or (beats == 4 and pos == 2)
			if rng.random() < sparse and not strong and b != bars - 1:
				pos += length
				continue  # a breath
			tones = [d + 7 * o for d in key.chord(ch) for o in (0, 1, 2)]
			if b == bars - 1 and cadence:
				cands = [d for d in tones if d % 7 == 0] or [d for d in tones if d % 7 == ch % 7]  # tonic, else the chord's root
			elif strong:
				cands = tones
			else:
				cands = [cur + s for s in (-2, -1, 1, 2)]
			cands = [c for c in cands if low - 2 <= c <= high + 2] or tones
			if avoid:
				cands = [c for c in cands if c % 7 not in avoid] or cands
			# prefer small steps, drift toward the contour
			weights = np.array([1.0 / (1 + abs(c - cur)) ** 1.6 * (1.0 / (1 + abs(c - target_high) * 0.25))
								* (0.15 if c == cur else 1.0) for c in cands])  # a tune moves: repeats are rare
			cur = cands[rng.choice(len(cands), p=weights / weights.sum())]
			notes.append((b * beats + pos, length, cur))
			pos += length
	return notes


def vary(phrase, rng, amount=0.3):
	"""Phrase A again, slightly different: a few inner notes step elsewhere."""
	out = []
	for i, (s, l, d) in enumerate(phrase):
		if 0 < i < len(phrase) - 1 and rng.random() < amount:
			d += int(rng.choice([-1, 1]))
		out.append((s, l, d))
	return out


# ---------------------------------------------------------------- tracks

TRACKS = {
	"title": {
		"key": (62, "aeolian"), "bpm": 76, "beats": 4, "seed": 11,
		"sections": {"A": [0, 5, 2, 6], "B": [3, 4, 0, 4], "C": [5, 6, 3, 4]},
		"form": ["A", "A", "B", "C", "A"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 1, 2, 1, 0, 2, 1, 2], "pad": True, "bass": True,
		"drum": [0, 2.5], "drum_sections": ["B", "C"], "reverb": 2.8, "sparse": 0.1,
	},
	"emberhold": {
		"key": (62, "major"), "bpm": 92, "beats": 3, "seed": 5,
		"sections": {"A": [0, 3, 4, 0, 5, 1, 4, 0], "B": [3, 0, 3, 4, 5, 3, 4, 4]},
		"form": ["A", "A", "B", "A"],
		"melody": "flute", "arp": "lute", "arp_pattern": [0, 2, 1], "pad": False, "bass": True,
		"drum": [0, 2], "drum_sections": ["A", "B"], "reverb": 1.6, "sparse": 0.0,
	},
	"combat": {
		"key": (64, "aeolian"), "bpm": 132, "beats": 4, "seed": 41,
		"sections": {"A": [0, 5, 6, 0], "B": [3, 0, 5, 4], "C": [0, 5, 3, 4]},
		"form": ["A", "A", "B", "A", "C"],
		"melody": "horn", "arp": "lute", "arp_pattern": [0, 1, 2, 1, 0, 1, 2, 3], "pad": True, "bass": True, "bass_eighths": True,
		"drum": [0, 1, 1.5, 2, 3, 3.5], "drum_sections": ["A", "B", "C"], "reverb": 1.4, "sparse": 0.0,
	},
	"thornwood": {
		"key": (52, "aeolian"), "bpm": 60, "beats": 3, "seed": 71,
		"sections": {"A": [0, 5, 3, 4, 0, 5, 6, 0], "B": [5, 6, 0, 3, 5, 3, 4, 4]},
		"form": ["A", "B", "A", "B"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 2, 4], "pad": True, "bass": True,
		"drum": [0], "drum_sections": ["B"], "reverb": 3.6, "sparse": 0.3, "bells": 0.2,
	},
	"hollowmere": {
		"key": (55, "dorian"), "bpm": 54, "beats": 4, "seed": 97,
		"sections": {"A": [0, 6, 3, 0], "B": [5, 3, 6, 4], "C": [0, 3, 6, 6]},
		"form": ["A", "B", "A", "C"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 1, 2, 4, 2, 1, 0, 2], "pad": True, "bass": False,
		"drum": [], "drum_sections": [], "reverb": 4.4, "sparse": 0.45, "bells": 0.45,
	},
	"harrowfield": {
		"key": (60, "mixolydian"), "bpm": 84, "beats": 3, "seed": 131,
		"sections": {"A": [0, 3, 4, 0, 0, 3, 6, 4], "B": [3, 0, 6, 3, 5, 3, 4, 4]},
		"form": ["A", "B", "A", "B"],
		"melody": "flute", "arp": "lute", "arp_pattern": [0, 2, 1], "pad": True, "bass": True,
		"drum": [0], "drum_sections": ["B"], "reverb": 2.2, "sparse": 0.2, "bells": 0.1,
	},
	"sunward_steps": {
		"key": (62, "mixolydian"), "bpm": 72, "beats": 4, "seed": 163,
		"sections": {"A": [0, 4, 3, 0], "B": [5, 3, 6, 4], "C": [0, 3, 4, 4]},
		"form": ["A", "B", "A", "C"],
		"melody": "horn", "arp": "harp", "arp_pattern": [0, 2, 4, 2, 1, 2, 4, 2], "pad": True, "bass": True,
		"drum": [0, 2], "drum_sections": ["B", "C"], "reverb": 3.4, "sparse": 0.25, "bells": 0.35,
	},
	"the_bleach": {
		"key": (50, "phrygian_dominant"), "bpm": 58, "beats": 4, "seed": 197,
		"sections": {"A": [0, 1, 0, 6], "B": [5, 1, 6, 0], "C": [3, 1, 0, 0]},
		"form": ["A", "B", "A", "C"],
		"melody": "flute", "arp": "lute", "arp_pattern": [0, 1, 2, 1, 0, 2, 1, 0], "pad": True, "bass": True,
		"drum": [0, 1.5], "drum_sections": ["B", "C"], "reverb": 3.8, "sparse": 0.4, "bells": 0.15,
	},
	"rainhold": {
		"key": (57, "dorian"), "bpm": 66, "beats": 3, "seed": 211,
		"sections": {"A": [0, 3, 6, 0, 0, 3, 4, 4], "B": [5, 3, 0, 6, 5, 3, 4, 0]},
		"form": ["A", "B", "A", "B"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 2, 4], "pad": True, "bass": True,
		"drum": [], "drum_sections": [], "reverb": 3.8, "sparse": 0.3, "bells": 0.4,
	},
	"weeping_throat": {
		"key": (50, "aeolian"), "bpm": 76, "beats": 4, "seed": 229,
		"sections": {"A": [0, 6, 5, 6], "B": [3, 0, 6, 4], "C": [0, 5, 3, 4]},
		"form": ["A", "A", "B", "A", "C"],
		"melody": "flute", "arp": "lute", "arp_pattern": [0, 1, 2, 1, 0, 2, 1, 2], "pad": True, "bass": True,
		"drum": [0, 1.5, 2.5, 3], "drum_sections": ["A", "B", "C"], "reverb": 3.0, "sparse": 0.3, "bells": 0.1,
	},
	"high_terrace": {  # misty tea terraces and a fallen monastery: pentatonic flute over a drone, far-off prayer bells
		"key": (64, "major"), "bpm": 56, "beats": 4, "seed": 251,
		"sections": {"A": [0, 5, 3, 0], "B": [5, 1, 3, 4], "C": [3, 5, 1, 0]},
		"form": ["A", "B", "A", "C"],
		"melody": "flute", "avoid": [3, 6], "arp": "harp", "arp_pattern": [0, 4, 2, -1, 1, -1, 4, -1], "pad": True, "bass": False,
		"drone": 0.4, "drum": [0, 2.5], "drum_sections": ["B", "C"], "drum_gain": 0.55,
		"reverb": 4.8, "sparse": 0.4, "bells": 0.55,
	},
	"dewstep": {  # the Dawnstair's first steps: morning over lantern-lit tea gardens, a light pentatonic flute over harp, soft pad, a few bells
		"key": (60, "major"), "bpm": 78, "beats": 3, "seed": 353,
		"sections": {"A": [0, 3, 0, 4, 0, 5, 3, 0], "B": [5, 3, 0, 4, 5, 1, 4, 4]},
		"form": ["A", "A", "B", "A"],
		"melody": "flute", "avoid": [3, 6], "arp": "harp", "arp_pattern": [0, 2, 4, 3, 2, 1], "pad": True, "bass": False,
		"drum": [0], "drum_sections": ["B"], "drum_gain": 0.4, "reverb": 3.0, "sparse": 0.2, "bells": 0.3,
	},
	"cinderpass": {  # black rock, lava and ash: a low phrygian line over a drone and a heartbeat drum
		"key": (52, "phrygian"), "bpm": 52, "beats": 4, "seed": 277,
		"sections": {"A": [0, 1, 0, 5], "B": [5, 6, 1, 0], "C": [3, 1, 6, 0]},
		"form": ["A", "A", "B", "A", "C"],
		"melody": "flute", "melody_octave": -1, "arp": "lute", "arp_pattern": [0, -1, 1, -1, 2, 1, -1, -1], "pad": True, "bass": True,
		"drone": 0.55, "drum": [0, 0.5, 2, 2.5], "drum_sections": ["A", "B", "C"], "drum_low": 0.7,
		"reverb": 3.6, "sparse": 0.45, "bells": 0.08,
	},
	"reedmere": {  # a misty reed marsh and its half-sunken stilt villages: a breathy low flute over a drone, dripping bells, a wandering hand drum
		"key": (51, "aeolian"), "bpm": 60, "beats": 3, "seed": 307,
		"sections": {"A": [0, 6, 3, 2, 0, 5, 6, 0], "B": [5, 2, 3, 6, 5, 3, 4, 4]},
		"form": ["A", "B", "A", "B"],
		"melody": "flute", "melody_octave": -1, "arp": "harp", "arp_pattern": [0, 2, -1, 4, 1, -1], "pad": True, "bass": False,
		"drone": 0.35, "drum": [0, 1.5, 2.5], "drum_sections": ["B"], "drum_gain": 0.45, "drum_skip": 0.4,
		"reverb": 4.6, "sparse": 0.4, "bells": 0.5,
	},
	"drownfast": {  # the drowned kings' citadel under an endless storm: a processional lament over deep drones, sunken bells, far thunder
		"key": (47, "aeolian"), "bpm": 50, "beats": 4, "seed": 331,
		"sections": {"A": [0, 5, 2, 4], "B": [3, 6, 2, 0], "C": [5, 3, 1, 4]},
		"form": ["A", "A", "B", "A", "C"],
		"melody": "flute", "arp": "lute", "arp_pattern": [0, -1, 2, -1, 1, -1, 4, -1], "pad": True, "bass": True,
		"drone": 0.6, "drum": [0, 2], "drum_sections": ["A", "B", "C"], "drum_low": 0.6, "drum_gain": 0.8,
		"reverb": 4.4, "sparse": 0.3, "bells": 0.35, "bell_octave": 0, "thunder": 0.3,
	},
	"the_burn": {  # a burned forest under falling ash: a mournful low flute over drones, sparse deep drum, embers ticking in the lute
		"key": (50, "phrygian"), "bpm": 48, "beats": 4, "seed": 379,
		"sections": {"A": [0, 5, 1, 0], "B": [3, 1, 6, 0], "C": [5, 6, 1, 1]},
		"form": ["A", "B", "A", "C"],
		"melody": "flute", "melody_octave": -1, "arp": "lute", "arp_pattern": [0, -1, -1, 2, -1, -1, 1, -1], "pad": True, "bass": True,
		"drone": 0.6, "drum": [0], "drum_sections": ["B", "C"], "drum_low": 0.6, "drum_gain": 0.7,
		"reverb": 4.2, "sparse": 0.5, "bells": 0.05,
	},
	"blackglass": {  # fields of black volcanic glass: cold harp and bell harmonics up high, eerie and still, a slow low pulse
		"key": (56, "aeolian"), "bpm": 50, "beats": 4, "seed": 401,
		"sections": {"A": [0, 5, 0, 1], "B": [5, 3, 1, 4], "C": [0, 1, 5, 0]},
		"form": ["A", "B", "A", "C"],
		"melody": "flute", "melody_octave": 0, "arp": "harp", "arp_octave": 1, "arp_pattern": [0, -1, 4, -1, 2, -1, -1, -1], "pad": True, "bass": False,
		"drone": 0.3, "drum": [0], "drum_sections": ["A", "B", "C"], "drum_low": 0.55, "drum_gain": 0.5,
		"reverb": 5.2, "sparse": 0.55, "bells": 0.7, "bell_octave": 2,
	},
	"forgehold": {  # the forge city in the volcano's flank: hammers on anvils, a strong bass, a proud horn, warm and loud
		"key": (50, "mixolydian"), "bpm": 88, "beats": 4, "seed": 419,
		"sections": {"A": [0, 6, 3, 0], "B": [3, 0, 6, 4], "C": [5, 6, 0, 4]},
		"form": ["A", "A", "B", "A", "C", "A", "B", "A"],
		"melody": "horn", "arp": "lute", "arp_pattern": [0, 2, 1, 2, 0, 2, 1, 2], "pad": True, "bass": True, "bass_eighths": True,
		"drum": [0, 1.5, 2, 3], "drum_sections": ["A", "B", "C"], "drum_low": 0.75,
		"anvil": [0, 1, 2.5, 3], "anvil_sections": ["A", "B", "C"], "anvil_hz": 740,
		"reverb": 2.4, "sparse": 0.1, "bells": 0.0,
	},
	"dawnwatch": {  # the Dawn-Tusk's fortress on the snowy ridge, under siege: a proud horn over driving bass, marching drums, a watch bell
		"key": (55, "aeolian"), "bpm": 96, "beats": 4, "seed": 431,
		"sections": {"A": [0, 5, 6, 0], "B": [3, 0, 5, 4], "C": [5, 6, 3, 4]},
		"form": ["A", "A", "B", "A", "C", "A", "B", "A"],
		"melody": "horn", "arp": "lute", "arp_pattern": [0, -1, 0, 2, 0, -1, 1, 2], "pad": True, "bass": True, "bass_eighths": True,
		"drum": [0, 2, 2.5], "drum_sections": ["A", "B", "C"], "drum_low": 0.8,
		"snare": [1, 3, 3.75], "snare_sections": ["B", "C"], "snare_gain": 0.9,
		"reverb": 2.6, "sparse": 0.05, "bells": 0.12, "bell_octave": 0,
	},
	"mirror_flats": {  # a salt flat under a mirror of water: lone bells over a floating lydian pad, high harp glints, a lot of silence
		"key": (60, "lydian"), "bpm": 50, "beats": 4, "seed": 443,
		"sections": {"A": [0, 1, 0, 1], "B": [5, 1, 4, 0], "C": [3, 1, 0, 0]},
		"form": ["A", "B", "A", "C"],
		"melody": "bell", "arp": "harp", "arp_octave": 1, "arp_pattern": [0, -1, -1, -1, 4, -1, -1, -1], "pad": True, "bass": False,
		"drone": 0.3, "drum": [], "drum_sections": [],
		"reverb": 5.6, "sparse": 0.6, "bells": 0.4, "bell_octave": 2,
	},
	"silted_reach": {  # a great river delta in the rain: a flowing flute over a rolling lute, a gentle hand-drum pulse, rain all through
		"key": (53, "dorian"), "bpm": 70, "beats": 3, "seed": 457,
		"sections": {"A": [0, 6, 3, 0, 5, 3, 6, 0], "B": [3, 0, 6, 3, 5, 6, 4, 4]},
		"form": ["A", "A", "B", "A", "B"],
		"melody": "flute", "arp": "lute", "arp_pattern": [0, 2, 4, 2, 1, 2], "pad": True, "bass": True,
		"drum": [0, 1.5], "drum_sections": ["A", "B"], "drum_gain": 0.4, "drum_skip": 0.3,
		"reverb": 3.8, "sparse": 0.3, "bells": 0.2, "rain": 0.35,
	},
	"tidemouth": {  # Rainhold's harbor under siege from the sea: a shanty's lilt, lute doubled by a low horn, stamping drum, the harbor bell
		"key": (62, "dorian"), "bpm": 108, "beats": 3, "seed": 467,
		"sections": {"A": [0, 6, 0, 4, 0, 6, 3, 0], "B": [3, 0, 6, 4, 3, 0, 4, 0]},
		"form": ["A", "A", "B", "A", "B"],
		"melody": "lute", "melody_double": "horn", "arp": "lute", "arp_pattern": [0, 2, 1], "pad": True, "bass": True,
		"drum": [0, 2], "drum_sections": ["A", "B"], "drum_low": 0.85,
		"snare": [1], "snare_sections": ["B"], "snare_gain": 0.7,
		"reverb": 2.0, "sparse": 0.05, "bells": 0.15, "bell_octave": 0,
	},
	"galehold": {  # the windmill city on the cliff's edge, Vayuketh's: a bright lilting flute over harp and bells, wind chimes all round, a light pulse
		"key": (62, "lydian"), "bpm": 100, "beats": 3, "seed": 479,
		"sections": {"A": [0, 1, 4, 0, 5, 1, 4, 0], "B": [3, 4, 0, 5, 3, 1, 4, 4]},
		"form": ["A", "A", "B", "A", "B"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 2, 4, 2, 1, 2], "pad": True, "bass": True,
		"drum": [0, 2], "drum_sections": ["A", "B"], "drum_gain": 0.45,
		"reverb": 2.6, "sparse": 0.1, "bells": 0.35, "bell_octave": 1, "chimes": 0.45, "wind": 0.18,
	},
	"windbreak": {  # a broken plateau of wind-cut mesas: open fifths droning under a lonely soaring flute, a far sparse drum, wind across it all
		"key": (57, "dorian"), "bpm": 56, "beats": 4, "seed": 487,
		"sections": {"A": [0, 4, 0, 6], "B": [3, 4, 6, 0], "C": [5, 4, 3, 4]},
		"form": ["A", "B", "A", "C"],
		"melody": "flute", "melody_octave": 1, "avoid": [5], "arp": "harp", "arp_pattern": [0, -1, 2, -1, -1, -1, 4, -1],
		"pad": False, "fifths": 0.45, "bass": False,
		"drone": 0.45, "drum": [0], "drum_sections": ["B", "C"], "drum_low": 0.6, "drum_gain": 0.6,
		"reverb": 5.0, "sparse": 0.45, "bells": 0.1, "bell_octave": 1, "wind": 0.4,
	},
	"the_long_grass": {  # an endless tallgrass sea and the horse-folk: a rolling horn tune over a galloping lute and a steady hoofbeat drum, wide and vast
		"key": (55, "mixolydian"), "bpm": 104, "beats": 4, "seed": 499,
		"sections": {"A": [0, 6, 3, 0], "B": [3, 0, 6, 4], "C": [5, 3, 6, 0]},
		"form": ["A", "A", "B", "A", "C", "A", "B", "A"],
		"melody": "horn", "melody_double": "lute", "melody_double_octave": 1, "arp": "lute",
		"arp_pattern": [0, 0, 2, 0, 1, 0, 2, 4, 0, 0, 2, 0, 1, 0, 4, 2], "pad": True, "bass": True,
		"drum": [0, 0.5, 0.75, 1, 1.5, 1.75, 2, 2.5, 2.75, 3, 3.5, 3.75], "drum_sections": ["A", "B", "C"], "drum_gain": 0.55, "drum_low": 0.85,
		"reverb": 3.4, "sparse": 0.1, "bells": 0.0, "wind": 0.12,
	},
	"greenmoor": {
		"key": (57, "dorian"), "bpm": 68, "beats": 4, "seed": 23,
		"sections": {"A": [0, 3, 0, 6], "B": [3, 6, 0, 4], "C": [2, 3, 0, 0]},
		"form": ["A", "B", "A", "C"],
		"melody": "flute", "arp": "harp", "arp_pattern": [0, 2, 4, 2, 1, 2, 4, 2], "pad": True, "bass": False,
		"drum": [], "drum_sections": [], "reverb": 3.2, "sparse": 0.35, "bells": 0.3,
	},
}


def _voice(name, f, dur, vel, rng):
	"""One melody note on the named instrument."""
	if name == "horn":
		return horn(f, dur, vel)
	if name == "bell":
		return bell(f, dur, vel * 1.6)
	if name == "lute":
		return lute(f, dur, vel * 1.25)
	return flute(f, dur, vel, rng)


def render(name, spec):
	rng = np.random.default_rng(spec["seed"])
	key = Key(*spec["key"])
	beats, bpm = spec["beats"], spec["bpm"]
	beat = 60.0 / bpm
	bars_total = sum(len(spec["sections"][s]) for s in spec["form"])
	length = bars_total * beats * beat
	n = int((length + 4.0) * SR)
	L, R = np.zeros(n), np.zeros(n)

	def put(sig, at, pan=0.0, gain=1.0):
		i = max(0, int(at * SR))  # a humanized note at 0:00 can't start before the track
		j = min(n, i + len(sig))
		if i >= n:
			return
		L[i:j] += sig[:j - i] * gain * math.cos((pan + 1) * math.pi / 4)
		R[i:j] += sig[:j - i] * gain * math.sin((pan + 1) * math.pi / 4)

	phrases = {}  # each section's tune, written the first time it's heard
	bar = 0
	for si, sec in enumerate(spec["form"]):
		chords = spec["sections"][sec]
		if sec not in phrases:
			phrases[sec] = compose_phrase(key, chords, beats, rng, sparse=spec.get("sparse", 0.0),
										  cadence=(sec != "B"), avoid=tuple(spec.get("avoid", ())))
			tune = phrases[sec]
		else:
			tune = vary(phrases[sec], rng)
		t0 = bar * beats * beat
		# melody
		for s, l, d in tune:
			f = midi_hz(key.note(d, spec.get("melody_octave", 0)))
			vel = 0.55 + 0.1 * rng.random()
			at = t0 + s * beat + rng.normal(0, 0.006)
			put(_voice(spec["melody"], f, l * beat * 0.95, vel, rng), at, pan=0.15)
			if spec.get("melody_double"):  # a second voice on the tune (an octave down unless told), for weight
				f2 = f * 2 ** spec.get("melody_double_octave", -1)
				put(_voice(spec["melody_double"], f2, l * beat * 0.95, vel * 0.7, rng), at + 0.004, pan=-0.1)
		# a drone under the whole section: the tonic and its fifth, two octaves down
		if spec.get("drone"):
			sec_len = len(chords) * beats * beat
			for m in (key.note(0, -2), key.note(4, -2)):
				put(pad(midi_hz(m), sec_len, spec["drone"]), t0, pan=0.0)
		# harmony, per bar
		for b, ch in enumerate(chords):
			tb = t0 + b * beats * beat
			triad = [key.note(d, -1) for d in key.chord(ch)]
			if spec["pad"]:
				for m in triad:
					put(pad(midi_hz(m), beats * beat * 1.02, 0.45), tb, pan=-0.2)
			if spec.get("fifths"):  # open fifths, no third: root, fifth and octave spread wide
				for m, pan in ((key.note(ch, -1), -0.5), (key.note(ch, -1) + 7, 0.5), (key.note(ch, 0), 0.0)):
					put(pad(midi_hz(m), beats * beat * 1.02, spec["fifths"]), tb, pan=pan)
			if spec.get("bass_eighths"):  # a driving ostinato: root and octave on every half beat
				for k in range(beats * 2):
					m = key.note(ch, -2) + (12 if k % 4 == 3 else 0)
					put(bass(midi_hz(m), beat * 0.45, 0.5 if k % 2 == 0 else 0.38), tb + k * beat / 2)
			elif spec["bass"]:
				put(bass(midi_hz(key.note(ch, -2)), beats * beat * 0.9, 0.55), tb)
			pattern = spec["arp_pattern"]
			step = beats * beat / len(pattern)
			ao = spec.get("arp_octave", -1)
			tones = [key.note(d, ao) for d in key.chord(ch)] + [key.note(ch + 7, ao), key.note(ch + 9, ao)]
			for k, idx in enumerate(pattern):
				if idx < 0:
					continue  # a rest in the pattern
				f = midi_hz(tones[idx])
				vel = (0.5 if k == 0 else 0.34) + 0.06 * rng.random()
				inst = lute(f, step * 1.5, vel) if spec["arp"] == "lute" else harp(f, step * 2.5, vel)
				put(inst, tb + k * step + rng.normal(0, 0.004), pan=-0.35 if k % 2 else -0.15)
			if sec in spec["drum_sections"]:
				for d in spec["drum"]:
					if spec.get("drum_skip") and d != 0 and rng.random() < spec["drum_skip"]:
						continue  # an irregular hand: some off-beats go unplayed
					put(drum(0.55 if d == 0 or d == 2 else 0.35, rng, spec.get("drum_low", 1.0)), tb + d * beat, pan=0.05,
						gain=spec.get("drum_gain", 1.0))
			if sec in spec.get("snare_sections", ()):
				for d in spec["snare"]:  # marching sticks: accents on the backbeat, a lighter pickup before the bar
					put(snare(0.5 if d == int(d) else 0.3, rng), tb + d * beat + rng.normal(0, 0.004), pan=-0.1,
						gain=spec.get("snare_gain", 1.0))
			if sec in spec.get("anvil_sections", ()):
				for k, d in enumerate(spec["anvil"]):  # the smiths' hammers: a strong strike, then lighter taps, a second smith answering
					hz = spec.get("anvil_hz", 800) * (1.0 if k % 2 == 0 else 1.19)
					put(anvil(hz, 0.6 if d == 0 else 0.38, rng), tb + d * beat + rng.normal(0, 0.005), pan=0.45 if k % 2 else -0.45)
			if spec.get("bells") and rng.random() < spec["bells"]:
				put(bell(midi_hz(key.note(rng.choice(key.chord(ch)), spec.get("bell_octave", 1))), 2.0, 0.5),
					tb + beat * rng.integers(1, beats), pan=0.4)
			if spec.get("chimes") and rng.random() < spec["chimes"]:
				# wind chimes: a few high pentatonic tinkles in a quick cluster, where the breeze catches them
				at = tb + beat * rng.uniform(0, beats - 0.5)
				pan = rng.uniform(-0.8, 0.8)
				for k in range(int(rng.integers(3, 7))):
					d = int(rng.choice([0, 1, 2, 4, 5])) + 7 * int(rng.integers(0, 2))
					put(bell(midi_hz(key.note(d, 2)), 1.2, 0.22 + 0.12 * rng.random()), at + k * rng.uniform(0.07, 0.22),
						pan=float(np.clip(pan + rng.uniform(-0.2, 0.2), -1, 1)))
			if spec.get("thunder") and rng.random() < spec["thunder"]:
				# far thunder: a slow low swell on the chord's root and a few deep drum rolls under it
				at = tb + beat * rng.uniform(0.5, beats - 1)
				put(pad(midi_hz(key.note(ch, -2)), beats * beat * 1.4, 0.8), at, pan=rng.uniform(-0.5, 0.5))
				for k in range(int(rng.integers(2, 5))):
					put(drum(0.25 + 0.1 * rng.random(), rng, 0.55), at + 0.6 + k * rng.uniform(0.15, 0.4),
						pan=rng.uniform(-0.6, 0.6), gain=0.6)
		bar += len(chords)

	if spec.get("rain"):
		# rain: a soft bed of dark noise, swelling slowly, different in each ear.
		# It runs the whole length at an even level, so the loop point hides in it.
		m = int(length * SR)
		for chan, seed in ((L, 303), (R, 404)):
			noise = np.random.default_rng(seed).standard_normal(m)
			noise = np.convolve(noise, np.ones(14) / 14, mode="same")
			swell = 0.8 + 0.2 * np.sin(2 * np.pi * np.arange(m) / SR / length * 2 + seed)  # whole cycles over the loop
			chan[:m] += noise * swell * spec["rain"] * 0.12

	if spec.get("wind"):
		# wind: a band of airy noise (a light blur minus a heavy one) rising and
		# falling in gusts, whole cycles over the loop so the seam hides in it
		m = int(length * SR)
		tt = np.arange(m) / SR
		for chan, seed in ((L, 505), (R, 606)):
			noise = np.random.default_rng(seed).standard_normal(m)
			band = np.convolve(noise, np.ones(9) / 9, mode="same") - np.convolve(noise, np.ones(120) / 120, mode="same")
			gust = sum(np.sin(2 * np.pi * tt / length * c + seed * k) * a for k, (c, a) in enumerate(((3, 0.5), (7, 0.3), (13, 0.2)), 1))
			swell = np.clip(0.35 + 0.5 * gust, 0.05, 1.0)
			chan[:m] += band * swell * spec["wind"] * 1.2

	# the room: a decaying-noise reverb, a little different on each side
	for chan, seed in ((L, 101), (R, 202)):
		ir_t = _t(spec["reverb"])
		noise = np.random.default_rng(seed).standard_normal(len(ir_t))
		noise = np.convolve(noise, np.ones(6) / 6, mode="same")  # darker tail
		ir = noise * np.exp(-ir_t * 6.9 / spec["reverb"])
		ir[: int(0.012 * SR)] = 0  # pre-delay
		ir /= np.sqrt(np.sum(ir ** 2))
		size = 1 << int(math.ceil(math.log2(len(chan) + len(ir))))
		wet = np.fft.irfft(np.fft.rfft(chan, size) * np.fft.rfft(ir, size), size)[: len(chan)]
		chan[:] = chan * 0.78 + wet * 0.42
	# loop: fold everything after the end back onto the start, so it wraps seamlessly
	end = int(length * SR)
	for chan in (L, R):
		tail = chan[end:]
		chan[: len(tail)] += tail
	L, R = L[:end], R[:end]
	peak = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
	scale = 0.8 / peak
	return np.stack([L * scale, R * scale], axis=1), length


def write_wav(path, stereo):
	data = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
	with wave.open(path, "wb") as w:
		w.setnchannels(2)
		w.setsampwidth(2)
		w.setframerate(SR)
		w.writeframes(data.tobytes())


def encode_ogg(wav_path, ogg_path, seconds):
	"""Blender's FFmpeg: a sound strip mixed down to OGG Vorbis."""
	import bpy
	bpy.ops.wm.read_factory_settings(use_empty=True)
	scene = bpy.context.scene
	scene.render.fps = 30
	scene.frame_start = 1
	scene.frame_end = int(math.ceil(seconds * 30))
	ed = scene.sequence_editor_create()
	strips = ed.strips if hasattr(ed, "strips") else ed.sequences
	strip = strips.new_sound("music", wav_path, 1, 1)
	scene.frame_end = strip.frame_final_end - 1  # end inside the strip: a scene longer than its sound mixes down empty
	bpy.ops.sound.mixdown(filepath=ogg_path, container="OGG", codec="VORBIS", format="S16", bitrate=160,
						  mixrate=SR, accuracy=1024)
	# the mixdown keeps writing after the call returns: wait for the file to
	# stop growing, or the next track (or quitting) cuts it short
	import time
	last, still = -1, 0
	while still < 8:
		time.sleep(0.25)
		size = os.path.getsize(ogg_path) if os.path.exists(ogg_path) else 0
		still = still + 1 if size == last and size > 0 else 0
		last = size


def main():
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	out = argv[argv.index("--out") + 1] if "--out" in argv else "assets/music"
	only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
	keep_wav = "--wav" in argv
	os.makedirs(out, exist_ok=True)
	for name, spec in TRACKS.items():
		if only and name not in only:
			continue
		stereo, seconds = render(name, spec)
		wav = os.path.abspath(os.path.join(out, name + ".wav"))
		write_wav(wav, stereo)
		encode_ogg(wav, os.path.abspath(os.path.join(out, name + ".ogg")), seconds)
		if not keep_wav:
			os.remove(wav)
		print("track %s: %.1f s" % (name, seconds))


if __name__ == "__main__":
	main()
