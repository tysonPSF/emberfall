class_name Pack
extends RefCounted
## What a character carries, EverQuest-style: 8 general slots, each empty or
## holding one entry. An entry is {"item": id, "count": n} for ordinary items
## (count > 1 only for stackables, up to the item's "stack"), and a bag entry
## also has "contents": an Array of entries (empty ones are {}) as long as the
## bag's "bag" size. Bags never go inside bags.
##
## Places are written as strings: "g:3" is general slot 3, "b:3:5" is slot 5
## of the bag in general slot 3.

const GENERAL := 8

var slots: Array = []  # GENERAL entries


func _init() -> void:
	slots.resize(GENERAL)
	for i in GENERAL:
		slots[i] = {}


static func entry(item_id: String, count := 1) -> Dictionary:
	var e := {"item": item_id, "count": count}
	var size := bag_size_of(item_id)
	if size > 0:
		var contents: Array = []
		contents.resize(size)
		for i in size:
			contents[i] = {}
		e["contents"] = contents
	return e


static func bag_size_of(item_id: String) -> int:
	return int(GameData.item(item_id).get("bag", 0))


static func stack_of(item_id: String) -> int:
	return maxi(1, int(GameData.item(item_id).get("stack", 1)))


static func is_empty_entry(e: Variant) -> bool:
	return not (e is Dictionary) or (e as Dictionary).is_empty()


# --- places ----------------------------------------------------------------------

## The entry at a place ("g:3" or "b:3:5"), or {} if empty or not a place.
func get_at(place: String) -> Dictionary:
	var p := place.split(":")
	if p[0] == "g" and p.size() == 2:
		var g := int(p[1])
		return slots[g] if g >= 0 and g < GENERAL else {}
	if p[0] == "b" and p.size() == 3:
		var bag := get_at("g:" + p[1])
		var contents: Array = bag.get("contents", [])
		var i := int(p[2])
		return contents[i] if i >= 0 and i < contents.size() else {}
	return {}


func set_at(place: String, e: Dictionary) -> void:
	var p := place.split(":")
	if p[0] == "g":
		slots[int(p[1])] = e
	elif p[0] == "b":
		(slots[int(p[1])]["contents"] as Array)[int(p[2])] = e


## Whether a place exists and could hold this entry (bags stay out of bags).
func fits(place: String, e: Dictionary) -> bool:
	var p := place.split(":")
	if p[0] == "g" and p.size() == 2:
		return int(p[1]) >= 0 and int(p[1]) < GENERAL
	if p[0] == "b" and p.size() == 3:
		var bag := get_at("g:" + p[1])
		var i := int(p[2])
		return bag.has("contents") and i >= 0 and i < (bag["contents"] as Array).size() \
				and (e.is_empty() or not e.has("contents"))
	return false


## Every place, general slots first, then each bag's slots in order.
func places() -> Array:
	var out: Array = []
	for g in GENERAL:
		out.append("g:%d" % g)
	for g in GENERAL:
		for i in (slots[g] as Dictionary).get("contents", []).size():
			out.append("b:%d:%d" % [g, i])
	return out


# --- counting --------------------------------------------------------------------

## Every entry carried, bags and their contents included.
func entries() -> Array:
	var out: Array = []
	for place in places():
		var e := get_at(place)
		if not e.is_empty():
			out.append(e)
	return out


## How many of this exact item (quality included) are carried.
func count(item_id: String) -> int:
	var n := 0
	for e: Dictionary in entries():
		if e["item"] == item_id:
			n += int(e["count"])
	return n


## Every item id carried, one per unit (a stack of 5 is listed 5 times).
func item_ids() -> Array:
	var out: Array = []
	for e: Dictionary in entries():
		for k in int(e["count"]):
			out.append(e["item"])
	return out


func is_empty() -> bool:
	return entries().is_empty()


# --- adding and removing ---------------------------------------------------------

## How many more of an item fit: topping up stacks, then empty slots (bags
## only in general slots).
func room_for(item_id: String) -> int:
	var stack := stack_of(item_id)
	var bag := bag_size_of(item_id) > 0
	var room := 0
	for place in places():
		if bag and not place.begins_with("g:"):
			continue
		var e := get_at(place)
		if e.is_empty():
			room += stack
		elif e["item"] == item_id and stack > 1:
			room += stack - int(e["count"])
	return room


## Adds up to `count`; returns how many didn't fit.
func add(item_id: String, count := 1) -> int:
	var stack := stack_of(item_id)
	if stack > 1:
		for place in places():
			var e := get_at(place)
			if count > 0 and not e.is_empty() and e["item"] == item_id and int(e["count"]) < stack:
				var n := mini(count, stack - int(e["count"]))
				e["count"] = int(e["count"]) + n
				count -= n
	for place in places():
		if count <= 0:
			break
		var fresh := entry(item_id, mini(count, stack))
		if get_at(place).is_empty() and fits(place, fresh):
			set_at(place, fresh)
			count -= int(fresh["count"])
	return count


## Puts a whole entry (a bag with its contents, say) in the first place that
## takes it; false if there is none.
func add_entry(e: Dictionary) -> bool:
	if not e.has("contents"):
		return add(e["item"], int(e["count"])) == 0
	for place in places():
		if get_at(place).is_empty() and fits(place, e):
			set_at(place, e)
			return true
	return false


## Removes `count` of an item from wherever it is; false (and nothing
## removed) if there aren't that many.
func remove(item_id: String, count := 1) -> bool:
	if self.count(item_id) < count:
		return false
	var order := places()
	order.reverse()  # bags first, so general slots empty last
	for place in order:
		var e := get_at(place)
		if count <= 0:
			break
		if e.is_empty() or e["item"] != item_id or e.has("contents") and not _bag_empty(e):
			continue
		var n := mini(count, int(e["count"]))
		e["count"] = int(e["count"]) - n
		count -= n
		if int(e["count"]) <= 0:
			set_at(place, {})
	return true


static func _bag_empty(e: Dictionary) -> bool:
	for c: Variant in e.get("contents", []):
		if not is_empty_entry(c):
			return false
	return true


func clear() -> void:
	for i in GENERAL:
		slots[i] = {}


# --- saving ----------------------------------------------------------------------

func to_save() -> Array:
	return slots.duplicate(true)


## From a save: the new layout, or an old flat item list (which goes into the
## general slots, then a pack for whatever doesn't fit).
static func from_save(saved: Variant, old_items: Array = []) -> Pack:
	var pack := Pack.new()
	if saved is Array:
		for i in mini((saved as Array).size(), GENERAL):
			pack.slots[i] = clean_entry(saved[i])
		return pack
	var known := old_items.filter(func(id: Variant) -> bool: return GameData.items.has(GameData.base_item(str(id))))
	# the old bags held 24 things loose: set aside enough backpacks (8 slots
	# each, taking a general slot) before filling, so nothing is left behind
	var packs := 0
	while known.size() > (GENERAL - packs) + packs * bag_size_of("worn_backpack") and packs < GENERAL:
		packs += 1
	for k in packs:
		pack.slots[GENERAL - 1 - k] = entry("worn_backpack")
	for id: Variant in known:
		pack.add(str(id))
	return pack


## A saved entry made safe: known items only, counts within the stack,
## contents sized to the bag.
static func clean_entry(e: Variant) -> Dictionary:
	if not (e is Dictionary) or (e as Dictionary).is_empty():
		return {}
	var id := str(e.get("item", ""))
	if not GameData.items.has(GameData.base_item(id)):
		return {}
	var out := entry(id, clampi(int(e.get("count", 1)), 1, stack_of(id)))
	if out.has("contents"):
		var saved: Array = e.get("contents", [])
		for i in mini(saved.size(), (out["contents"] as Array).size()):
			var inner := clean_entry(saved[i])
			(out["contents"] as Array)[i] = {} if inner.has("contents") else inner
	return out
