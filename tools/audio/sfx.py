"""Emberfall's sound effects: combat, spells, voices. Built from CC0 recordings
(Kenney's Impact Sounds and RPG Audio, and rubberduck's 80 CC0 RPG SFX and 80
CC0 creature SFX on OpenGameArt: assets/sfx/CREDITS.md) trimmed, layered,
pitched and leveled here, plus a few synthesized in numpy where a recording
wouldn't fit (weapon swooshes, the bowstring, chimes, the cast hum), and
written as short mono WAVs to assets/sfx/<sound>_<n>.wav for the Sfx autoload
(several variants of each, picked at random and pitched a little, so a fight
never repeats itself). Run in Blender, whose audio module (aud) reads OGG:

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \\
        -P tools/audio/sfx.py -- --out assets/sfx [--only hit_slash,parry] [--cache <dir>]

The packs are downloaded once into the cache (default ~/.cache/emberfall_sfx).
Every sound is a recipe in SOUNDS: a list of variants, each a list of layers
(a recording "pack:file" or a synth "~name"), with gain, rate (pitch and speed
together) and a delay; then trimmed, faded and leveled to its group's loudness.
"""

import glob
import math
import os
import sys
import urllib.request
import wave
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music  # noqa: E402  (its instruments: bell, horn, drum)

SR = 44100
PACKS = {
	"IMP": "https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip",
	"KRPG": "https://kenney.nl/media/pages/assets/rpg-audio/8e99002d76-1677590336/kenney_rpg-audio.zip",
	"RPG": "https://opengameart.org/sites/default/files/80-CC0-RPG-SFX_0.zip",
	"CRE": "https://opengameart.org/sites/default/files/80-CC0-creature-SFX_0.zip",
}


# ---------------------------------------------------------------- sources

def fetch(cache):
	for pack, url in PACKS.items():
		d = os.path.join(cache, pack)
		if os.path.isdir(d) and glob.glob(d + "/**/*.ogg", recursive=True):
			continue
		os.makedirs(d, exist_ok=True)
		z = os.path.join(cache, pack + ".zip")
		if not os.path.exists(z):
			print("downloading", url)
			req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (emberfall sfx build)"})
			with urllib.request.urlopen(req) as r, open(z, "wb") as f:
				f.write(r.read())
		zipfile.ZipFile(z).extractall(d)


_cache_dir = ""
_loaded = {}


def load(ref):
	"""A recording "PACK:name" (no extension) as mono float at SR."""
	if ref in _loaded:
		return _loaded[ref]
	import aud
	pack, name = ref.split(":")
	hits = glob.glob(os.path.join(_cache_dir, pack, "**", name + ".ogg"), recursive=True)
	if not hits:
		raise SystemExit("no %s in %s" % (name, pack))
	s = aud.Sound(hits[0])
	d = np.asarray(s.data(), dtype=np.float64)
	x = d.mean(axis=1) if d.ndim > 1 else d
	sr = int(s.specs[0])
	if sr != SR:
		x = np.interp(np.arange(0, len(x) * SR / sr) * sr / SR, np.arange(len(x)), x)
	_loaded[ref] = x
	return x


def rate_change(x, rate):
	"""Faster and higher (rate > 1) or slower and lower, together, like a tape."""
	if abs(rate - 1.0) < 1e-3:
		return x
	n = int(len(x) / rate)
	return np.interp(np.arange(n) * rate, np.arange(len(x)), x)


def trim(x, thresh=0.015):
	a = np.abs(x)
	peak = a.max() if len(a) else 0.0
	if peak <= 0:
		return x
	idx = np.nonzero(a > peak * thresh)[0]
	return x[max(0, idx[0] - 32): min(len(x), idx[-1] + 256)]


def lowpass(x, cutoff):
	"""A one-pole low-pass; cutoff may be a number or an array (a sweep)."""
	c = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), x.shape)
	a = 1.0 - np.exp(-2 * np.pi * c / SR)
	y = np.empty_like(x)
	v = 0.0
	for i in range(len(x)):
		v += a[i] * (x[i] - v)
		y[i] = v
	return y


# ---------------------------------------------------------------- synths

def whoosh(dur=0.32, lo=500.0, hi=2600.0, seed=1, peak_at=0.45):
	"""A blade through the air: noise through a band that sweeps up and back
	down, swelling to its loudest a little before the middle."""
	rng = np.random.default_rng(seed)
	n = int(dur * SR)
	t = np.arange(n) / n
	noise = rng.standard_normal(n)
	sweep = lo + (hi - lo) * np.sin(np.pi * np.clip(t / (peak_at * 2), 0, 1)) ** 1.5
	band = lowpass(noise, sweep) - lowpass(noise, sweep * 0.35)
	env = np.where(t < peak_at, (t / peak_at) ** 2, np.exp(-(t - peak_at) / (1 - peak_at) * 4.5))
	return band * env


def twang(f=150.0, dur=0.5, seed=1):
	"""A bowstring let go: a plucked string (Karplus-Strong) with a slap of noise."""
	rng = np.random.default_rng(seed)
	n = int(dur * SR)
	p = int(SR / f)
	buf = rng.uniform(-1, 1, p)
	out = np.empty(n)
	for i in range(n):
		out[i] = buf[i % p]
		buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * 0.994
	t = np.arange(n) / SR
	slap = lowpass(rng.standard_normal(n), 1800.0) * np.exp(-t * 60) * 1.2
	return (out * np.exp(-t * 6) + slap)


def chime(notes, step=0.07, ring=1.2, vel=0.5):
	"""Bells in a quick run (a heal, a blessing)."""
	n = int((step * len(notes) + ring + 0.5) * SR)
	out = np.zeros(n)
	for k, m in enumerate(notes):
		b = music.bell(music.midi_hz(m), ring, vel)
		i = int(k * step * SR)
		out[i:i + len(b)] += b[:n - i]
	return out


def shimmer(dur=0.9, seed=3, rise=True):
	"""Many small high bells and a rising band of air: a buff settling on you."""
	rng = np.random.default_rng(seed)
	n = int((dur + 1.0) * SR)
	out = np.zeros(n)
	for k in range(14):
		m = int(rng.choice([84, 86, 88, 91, 93, 96, 98]))
		b = music.bell(music.midi_hz(m), 0.8, 0.25 + 0.2 * rng.random())
		i = int((k / 14 if rise else rng.random()) * dur * SR)
		out[i:i + len(b)] += b[:n - i]
	air = whoosh(dur, 1500, 6000, seed, 0.7)
	out[:len(air)] += air * 0.35
	return out


def hum(dur=2.0, seed=5):
	"""The cast hum: a soft beating chord and a breath of air, made to loop."""
	n = int(dur * SR)
	t = np.arange(n) / SR
	out = np.zeros(n)
	for f, a in ((220.0, 1.0), (330.0, 0.6), (440.5, 0.45), (661.0, 0.25), (880.0, 0.15)):
		cyc = max(1, round(f * dur))  # whole cycles over the loop, so it wraps without a click
		out += a * np.sin(2 * np.pi * (cyc / dur) * t)
	out *= 0.7 + 0.3 * np.sin(2 * np.pi * (3 / dur) * t)  # a slow pulse, three to the loop
	rng = np.random.default_rng(seed)
	air = lowpass(rng.standard_normal(n + 4000), 2400.0)[2000:2000 + n] * 0.25
	return out + air


def fanfare():
	"""Level up: a bright rising call on brass over a bell."""
	notes = [(0.0, 67), (0.12, 72), (0.24, 76), (0.4, 79)]
	n = int(2.4 * SR)
	out = np.zeros(n)
	for at, m in notes:
		h = music.horn(music.midi_hz(m), 0.9 if m == 79 else 0.2, 0.7)
		i = int(at * SR)
		out[i:i + len(h)] += h[:n - i]
	for m in (79, 84):
		b = music.bell(music.midi_hz(m), 1.6, 0.5)
		i = int(0.4 * SR)
		out[i:i + len(b)] += b[:n - i]
	return out


SYNTHS = {
	"~swish_light": lambda s: whoosh(0.22, 900, 4200, s, 0.4),
	"~swish": lambda s: whoosh(0.32, 600, 3000, s, 0.45),
	"~swish_heavy": lambda s: whoosh(0.46, 300, 1800, s, 0.5),
	"~swish_claw": lambda s: whoosh(0.2, 500, 2400, s, 0.35),
	"~twang": lambda s: twang(130 + 25 * (s % 3), 0.45, s),
	"~heal": lambda s: chime([72, 76, 79, 84] if s % 2 else [74, 77, 81, 86]),
	"~buff": lambda s: shimmer(0.8, s),
	"~gate": lambda s: whoosh(0.9, 200, 3000, s, 0.6),
	"~hum": lambda s: hum(2.0, s),
	"~fanfare": lambda s: fanfare(),
	"~bell_low": lambda s: music.bell(music.midi_hz(60), 1.2, 0.6),
}


# ---------------------------------------------------------------- the sounds
# name: (group, [variant, ...]); a variant is [layer, ...]; a layer is
# (source, gain, rate, delay seconds). Groups set loudness (LEVELS, peak).

def V(*layers):
	"""A variant: layers as "source" or (source, gain=1, rate=1, delay=0)."""
	out = []
	for l in layers:
		l = (l,) if isinstance(l, str) else tuple(l)
		out.append(l + (1.0, 1.0, 0.0)[len(l) - 1:])
	return out


SOUNDS = {
	# swings: the air, by the weapon
	"swing_light": ("swing", [V(("~swish_light", 1.0, 1.0 + 0.05 * k)) for k in range(4)]),
	"swing": ("swing", [V(("~swish", 1.0, 1.0 + 0.04 * k)) for k in range(4)]),
	"swing_heavy": ("swing", [V(("~swish_heavy", 1.0, 1.0 - 0.04 * k)) for k in range(4)]),
	"swing_claw": ("swing", [V(("~swish_claw", 1.0, 1.0 + 0.06 * k)) for k in range(3)]),
	# hits, by what struck: the body of the blow plus the edge
	"hit_slash": ("hit", [V(("IMP:impactPunch_medium_00%d" % k, 0.8), ("KRPG:knifeSlice" + ("2" if k % 2 else ""), 0.7, 1.0 + 0.08 * k)) for k in range(4)]),
	"hit_pierce": ("hit", [V(("IMP:impactSoft_medium_00%d" % k, 1.0), ("KRPG:knifeSlice2", 0.45, 1.3 + 0.08 * k)) for k in range(3)]),
	"hit_blunt": ("hit", [V(("IMP:impactPunch_heavy_00%d" % k, 1.0), ("IMP:impactWood_medium_00%d" % (k % 2), 0.35, 0.8)) for k in range(4)]),
	"hit_claw": ("hit", [V(("IMP:impactPunch_medium_00%d" % (k + 1), 0.8, 1.1), ("KRPG:knifeSlice", 0.35, 1.5)) for k in range(3)]),
	"hit_arrow": ("hit", [V(("IMP:impactWood_light_00%d" % k, 0.8, 0.9), ("IMP:impactSoft_medium_00%d" % k, 0.9)) for k in range(3)]),
	"crit": ("hit", [V(("IMP:impactPunch_heavy_00%d" % k, 1.0, 0.85), ("IMP:impactBell_heavy_004", 0.25, 1.4)) for k in range(2)]),
	# what was struck rings under the blow: bone, stone, metal
	"mat_bone": ("mat", [V(("IMP:impactWood_light_00%d" % k, 1.0, 1.35)) for k in range(3)]),
	"mat_stone": ("mat", [V(("IMP:impactMining_00%d" % k, 1.0)) for k in range(3)]),
	"mat_metal": ("mat", [V(("IMP:impactPlate_medium_00%d" % k, 1.0)) for k in range(3)]),
	# blocked and parried: wood and steel
	"block": ("hit", [V(("IMP:impactWood_heavy_00%d" % k, 1.0), ("IMP:impactPlate_light_00%d" % k, 0.4)) for k in range(3)]),
	"parry": ("hit", [V(("IMP:impactMetal_medium_00%d" % (k * 2 % 5), 1.0), ("IMP:impactPlate_light_00%d" % k, 0.5, 1.2)) for k in range(3)]),
	# ranged
	"bow_release": ("swing", [V(("~twang", 1.0, 1.0), ("~swish_light", 0.7, 1.2, 0.02)) for k in range(3)]),
	"sling": ("swing", [V(("~swish_claw", 1.0, 1.3)) for k in range(2)]),
	# spells: the cast hum, then what lands, by its look (SpellFx kinds)
	"cast_loop": ("loop", [V("~hum")]),
	"spell_burst": ("spell", [V(("RPG:spell_fire_06", 1.0), ("RPG:spell_0%d" % (k % 2 + 1), 0.5)) for k in range(3)]),
	"spell_impact": ("spell", [V(("RPG:spell_0%d" % (k % 2 + 1), 1.0), ("IMP:impactPunch_heavy_00%d" % k, 0.6)) for k in range(3)]),
	"spell_heal": ("chime", [V("~heal") for k in range(2)]),
	"spell_buff": ("chime", [V("~buff") for k in range(2)]),
	"spell_dot": ("spell", [V(("RPG:creature_slime_0%d" % (k * 2 + 1), 0.8, 0.8), ("RPG:spell_fire_07", 0.8)) for k in range(2)]),
	"spell_root": ("spell", [V(("RPG:stones_0%d" % (k * 3 + 1), 1.0), ("IMP:impactWood_heavy_00%d" % k, 0.6, 0.8)) for k in range(2)]),
	"spell_gate": ("chime", [V(("~gate", 1.0), ("~bell_low", 0.6, 1.0, 0.3))]),
	"spell_taunt": ("voice", [V(("CRE:grunt_04", 1.0, 0.95)), V(("CRE:troll_03", 1.0, 1.1))]),
	"level_up": ("chime", [V("~fanfare")]),
	# voices, by kind (Sfx.voice_of): aggro when it comes for you, hurt now and then when hit, death
	"humanoid_aggro": ("voice", [V(("CRE:grunt_04", 1.0, r)) for r in (1.0, 0.9)] + [V(("CRE:troll_03", 1.0, 1.15))]),
	"humanoid_hurt": ("voice", [V(("CRE:grunt_0%d" % k, 1.0)) for k in (1, 3, 5)]),
	"humanoid_death": ("voice", [V(("CRE:grunt_02", 1.0, 0.85)), V(("CRE:grunt_01", 1.0, 0.8))]),
	"beast_aggro": ("voice", [V(("RPG:creature_roar_01", 1.0)), V(("RPG:creature_roar_03", 1.0)), V(("CRE:howl", 1.0))]),
	"beast_hurt": ("voice", [V(("RPG:creature_hurt_01", 1.0)), V(("CRE:monster_03", 1.0, 1.1))]),
	"beast_death": ("voice", [V(("RPG:creature_roar_02", 1.0, 0.8)), V(("CRE:monster_06", 1.0, 0.85))]),
	"small_aggro": ("voice", [V(("RPG:creature_misc_05", 1.0)), V(("RPG:creature_misc_01", 1.0, 1.1))]),
	"small_hurt": ("voice", [V(("RPG:creature_misc_02", 1.0)), V(("RPG:creature_misc_07", 1.0))]),
	"small_death": ("voice", [V(("RPG:creature_misc_03", 1.0)), V(("RPG:creature_misc_08", 1.0, 0.9))]),
	"bug_aggro": ("voice", [V(("CRE:bug_03", 1.0)), V(("CRE:bug_04", 0.8))]),
	"bug_hurt": ("voice", [V(("CRE:bug_01", 1.0))]),
	"bug_death": ("voice", [V(("CRE:bug_02", 1.0, 0.85))]),
	"undead_aggro": ("voice", [V(("CRE:monster_04", 1.0)), V(("CRE:monster_07", 1.0)), V(("RPG:creature_monster_03", 1.0))]),
	"undead_hurt": ("voice", [V(("RPG:creature_monster_04", 1.0), ("IMP:impactWood_light_000", 0.4, 1.3))]),
	"undead_death": ("voice", [V(("CRE:monster_04", 1.0, 0.85), ("RPG:stones_02", 0.6, 1.2, 0.25))]),
	"big_aggro": ("voice", [V(("CRE:roar_02", 1.0, 0.85)), V(("CRE:monster_06", 1.0, 0.8))]),
	"big_hurt": ("voice", [V(("CRE:troll_02", 1.0, 0.8))]),
	"big_death": ("voice", [V(("RPG:creature_die_01", 1.0, 0.9))]),
	"stone_aggro": ("voice", [V(("IMP:impactMining_003", 1.0, 0.7), ("CRE:monster_04", 0.7, 0.7))]),
	"stone_hurt": ("voice", [V(("IMP:impactMining_004", 1.0, 0.8))]),
	"stone_death": ("voice", [V(("RPG:stones_03", 1.0, 0.8), ("IMP:impactMining_002", 0.8, 0.6))]),
	"slime_aggro": ("voice", [V(("RPG:creature_slime_02", 1.0))]),
	"slime_hurt": ("voice", [V(("RPG:creature_slime_03", 1.0))]),
	"slime_death": ("voice", [V(("RPG:creature_slime_04", 1.0, 0.8))]),
	"bird_aggro": ("voice", [V(("CRE:scream_01", 1.0, 1.35)), V(("CRE:scream_02", 1.0, 1.45))]),
	"bird_hurt": ("voice", [V(("RPG:creature_misc_06", 1.0, 1.1))]),
	"bird_death": ("voice", [V(("CRE:scream_02", 1.0, 1.2))]),
	"player_hurt": ("voice", [V(("CRE:hurt_0%d" % k, 1.0)) for k in (3, 4, 5)]),
	"player_death": ("voice", [V(("CRE:grunt_02", 1.0, 0.8), ("IMP:impactSoft_heavy_000", 0.7, 1.0, 0.35))]),
}

LEVELS = {"swing": 0.42, "hit": 0.8, "mat": 0.5, "spell": 0.7, "chime": 0.55, "loop": 0.3, "voice": 0.65}  # peak per group


def render(name, group, layers, seed):
	parts = []
	for src, gain, rate, delay in layers:
		x = SYNTHS[src](seed) if src.startswith("~") else trim(load(src))
		x = rate_change(x, rate)
		x = x / max(np.abs(x).max(), 1e-9) * gain
		parts.append((x, delay))
	n = max(int(d * SR) + len(x) for x, d in parts)
	out = np.zeros(n)
	for x, d in parts:
		i = int(d * SR)
		out[i:i + len(x)] += x
	if group != "loop":
		out = trim(out, 0.004)
		fade = min(len(out) // 4, int(0.03 * SR))
		out[-fade:] *= np.linspace(1, 0, fade)
		out[:16] *= np.linspace(0, 1, 16)
	return out / max(np.abs(out).max(), 1e-9) * LEVELS[group]


def write_wav(path, x):
	data = (np.clip(x, -1, 1) * 32767).astype("<i2")
	with wave.open(path, "wb") as w:
		w.setnchannels(1)
		w.setsampwidth(2)
		w.setframerate(SR)
		w.writeframes(data.tobytes())


def main():
	global _cache_dir
	argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	out = argv[argv.index("--out") + 1] if "--out" in argv else "assets/sfx"
	only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
	_cache_dir = argv[argv.index("--cache") + 1] if "--cache" in argv else os.path.expanduser("~/.cache/emberfall_sfx")
	fetch(_cache_dir)
	os.makedirs(out, exist_ok=True)
	for name, (group, variants) in SOUNDS.items():
		if only and name not in only:
			continue
		for old in glob.glob(os.path.join(out, name + "_[0-9]*.wav")):
			os.remove(old)
		for k, layers in enumerate(variants, 1):
			x = render(name, group, layers, 7 + k * 13)
			write_wav(os.path.join(out, "%s_%d.wav" % (name, k)), x)
		print("sound %s: %d" % (name, len(variants)))


if __name__ == "__main__":
	main()
