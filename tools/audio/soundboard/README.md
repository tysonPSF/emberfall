# Temple Sounds: choosing the magic sounds

Work in progress (2026-10-01), on branch `spell-sounds`. The melee sounds stay as
they are; the spell, casting and level-up sounds are being replaced, chosen by
ear on a private sound board: https://claude.ai/artifact/3R5f1jgo1J7nCstFKksiKN
(Tyson's picks save in its database, collection `picks`, document `board`).

Where it stands (round 4):

- **Casting**: one channeling loop under every spell (`cast_base_a/b/c`: air
  with a shimmer, a warm low swell, glassy tones), plus a quiet touch of the
  spell's element over it (`touch_<element>`: droplets, crackle, electric
  snaps, a breeze, a murmur, tiny bells, a rumble, bubbling).
- **Landing**: one sound for what harms (`land_hit_a/b/c`) and one for what
  helps (`land_help_a/b/c`), plus a one-shot element touch (`tl_<element>`:
  splash, flare, crack, gust, low swoosh, glints, stone thud, fizz).
- **Level up**: three takes (`level_up_a/b/c`), still with bells; may be redone
  the same way.
- No singing bowls or bells in casting or landing: Tyson found them overpowering.

Rebuild the candidates (WAVs plus manifest.json) with
`/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/audio/spell_audition.py -- --out <dir>`;
the instruments live in `tools/audio/sfx.py`. The page here is the published
board's source: its sounds are served beside it as `sounds/<id>.wav`.

Still to do once picked: move the chosen takes into `sfx.py`'s SOUNDS, and have
`Sfx` play the channel plus the spell's element touch while casting
(`SpellFx.update_cast`) and the harm/help landing plus its touch when a spell
lands (`World.spell_fx`), picking the element from the spell's name and fx
color (lightning/storm/shock, frost/ice/water, fire/flame/ember, wind/gale,
shadow/death/soul, light/heal, stone/earth, poison/venom/nature).
