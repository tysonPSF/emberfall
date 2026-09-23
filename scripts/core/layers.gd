class_name Layers
## Physics layer bits, plus the render layers at the bottom.

const WORLD := 1      # terrain, trees, buildings
const ENTITIES := 2   # players and mobs (they pass through each other)
const CORPSES := 4    # clickable, never blocks movement

## Render layer bits (VisualInstance3D.layers), separate from physics.
const RENDER_ENTITIES := 2  # character and corpse meshes; ground decals skip them
