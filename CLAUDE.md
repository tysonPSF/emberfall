# Emberfall

Classic-EverQuest-style RPG in Godot 4.7 (GDScript). Solo slice now; multiplayer/grouping planned.

## Architecture rules

- **All state changes go through the `World` autoload** (`scripts/autoload/world.gd`). Input and UI call `World.request_*(entity_id, ...)` with ids, never mutate Entity stats/inventory directly. These functions become server RPCs later; keep them id-based and self-validating (range, ownership, dead checks).
- Player-facing messages go through `World.say(entity, text, color)`, not `log_message.emit`, so they can be routed per-connection later.
- Content is data: add mobs/items/spells/zones in `data/*.json`, not code. JSON numbers parse as float, so cast with `int()`.
- Nodes are built in code (no hand-authored scenes besides `scenes/main.tscn`). `Entity.make_visual(look)` builds either a rigged model or placeholder primitives.
- Art is KayKit (CC0) in `assets/`, referenced by id through `data/models.json`. All characters share the `Rig_Medium` skeleton, so one animation library (`CharacterModel.library()`) drives every model and weapons attach to bone `handslot.r`. Use the glTF files; the fbx/obj folders carry `.gdignore`. Classes, mobs and items pick art with `model` / `weapon` fields.
- Physics layers are in `scripts/core/layers.gd`. Entities don't collide with each other.

## Verify changes

```sh
/Applications/Godot.app/Contents/MacOS/Godot --headless --path . --import   # parse/compile check
/Applications/Godot.app/Contents/MacOS/Godot --path . -- --autotest --shots=<dir>  # scripted playthrough + screenshots
```
