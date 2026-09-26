class_name Hud
extends CanvasLayer
## In-game interface: player and target windows, cast bar, hotbar, chat log,
## loot and inventory windows. Reads state from the player; every action goes
## through World.request_*, the same as keyboard input.

const HELP_TEXT := """[b]Movement[/b]   W/S forward/back · A/D strafe · Arrow keys turn · Space jump · hold Shift to run (watch the green bar - it comes back when you ease off)
[b]Camera[/b]   Move the mouse to look · Wheel to zoom (all the way in = first person)
[b]Cursor[/b]   Hold Alt for the mouse pointer; it also returns whenever a window is open
[b]Targeting[/b]   Right-click what's under the crosshair · Tab nearest enemy · T cycles townsfolk and corpses · F1 self · Esc clear / interrupt cast
[b]No mouse?[/b]   Press O for settings and turn Mouse controls off: the cursor stays out and A/D turn. Tab and T target everything without one.
[b]Combat[/b]   Left-click to start attacking your target · Q stops · R fires your bow or sling (pull one mob to you) · the ring around the crosshair fills as your next swing comes up · 1-8 abilities & spells (learn more from your guildmaster) · C consider (con colors!) · K skills (they rise as you use them)
[b]Resting[/b]   X sit / stand. Sitting regenerates much faster; moving stands you up.
[b]Loot[/b]   L or double-click a corpse, then L again to take everything · I inventory (its ? button lists the item controls) · B opens or closes all bags, Esc closes them · right-click an item for details (or to open a bag)
[b]Talk[/b]   E or double-click to hail · click gold words in replies to ask about them
[b]Chat[/b]   Enter to type (plain text is /say) · / starts a command · /tell name · /ooc · /shout · /who · /help
[b]Trade[/b]   G with an NPC targeted: merchants open their shop, bankers your bank, anyone else a give window (quest turn-ins)
[b]Logging out[/b]   Esc with nothing open → Camp. Sit tight for 20 seconds and you're saved to the character screen.
[b]Dying[/b]   You respawn at the obelisk without your gear. Run back and loot your corpse.
H or the gear button to hide this."""

const BAG_TIPS := """Click to pick up and put down · Ctrl-click takes one from a stack
Shift-click equips (or sells, banks, offers in a trade)
Right-click for details, or to open a bag · hover a bag to peek inside
Click the ground to drop what you hold"""

const BUY_BUNDLE := 20  # the shop's "Buy 20" button, for ammunition and other small stackables

const ATTR_NAMES := {"dmg": "Damage", "ac": "AC", "hp": "HP", "mana": "Mana", "str": "STR", "sta": "STA", "agi": "AGI", "wis": "WIS", "int": "INT", "haste": "Haste", "hp_regen": "HP Regen", "mana_regen": "Mana Regen"}
const CROSSHAIR_SIZE := 30.0
const CROSSHAIR_COLOR := Color(1, 0.93, 0.72)  # near-white: gold alone vanished against grass
const CROSSHAIR_SHADOW := Color(0, 0, 0, 0.75)

var player: Player
var root: Control

var _player_panel: PanelContainer
var _name_label: Label
var _hp_bar: ProgressBar
var _hp_text: Label
var _mana_row: Control
var _mana_bar: ProgressBar
var _mana_text: Label
var _stamina_row: Control
var _stamina_bar: ProgressBar
var _stamina_text: Label
var _xp_bar: ProgressBar
var _xp_text: Label
var _buff_label: Label

var _target_panel: PanelContainer
var _target_name: Label
var _target_bar: ProgressBar
var _target_text: Label
var _attack_tag: Label

var _menu_panel: PanelContainer

var _cast_panel: PanelContainer
var _cast_bar: ProgressBar
var _cast_label: Label

var _buff_panel: PanelContainer
var _buff_rows: VBoxContainer
var _buff_shape := ""
var _debuff_panel: PanelContainer
var _debuff_rows: VBoxContainer
var _debuff_shape := ""  # which buffs the rows show, so they're rebuilt only when that changes
var _spell_slots: Array[HotSlot] = []
var _attack_slot: HotSlot
var _ranged_slot: HotSlot
var _sit_slot: HotSlot
var _slot_totals: Dictionary = {}  # cooldown key -> longest wait seen since it was last ready (the sweep's 100%)

var _log: RichTextLabel
var _group_panel: PanelContainer
var _group_rows: VBoxContainer
var _group_shape := ""  # member ids and leader last drawn; the rows are rebuilt when it changes
var _group_bars: Dictionary = {}  # member id -> [hp bar, mana bar, name label]
var _invite_panel: PanelContainer
var _skills_panel: PanelContainer
var _skills_box: VBoxContainer
var _skills_timer := 0.0
var _item_panel: PanelContainer
var _item_title: Label
var _item_text: RichTextLabel
var _item_view_box: SubViewportContainer
var _item_stage: Node3D  # the previewed model turns on this
var _item_cam: Camera3D
var _item_use: Button
var _item_link: Button
var _item_shown := ""
var _item_link_re := RegEx.create_from_string("\\{item:([A-Za-z0-9_@]+)\\}")
var _invite_label: Label
var _chat: LineEdit
var _chat_channel := ""  # "" is say; else "/g", "/sh", "/ooc", "/t Name" or "/r": where plain lines go
var _channel_label: Label
var _log_lines := 0
var _group_log_panel: PanelContainer  # group chat, its own window while you're in a group
var _group_log: RichTextLabel
var _group_log_lines := 0
var _keyword_re := RegEx.create_from_string("\\[([^\\]]+)\\]")

var _trade_panel: PanelContainer
var _trade_title: Label
var _bag_hint: Label

var _service_panel: PanelContainer
var _service_title: Label
var _service_hint: Label
var _shop_list: VBoxContainer
var _shop_scroll: ScrollContainer
var _bank_box: VBoxContainer
var _bank_grid: GridContainer
var _bank_coin_label: Label
var _service_npc: Npc

var _quest_panel: PanelContainer
var _quest_label: RichTextLabel

var _loot_panel: PanelContainer
var _loot_title: Label
var _loot_list: VBoxContainer
var _loot_corpse: Corpse

var _inv_panel: PanelContainer
var _slot_buttons: Dictionary = {}  # place ("g:3", "e:head", "k:2"...) -> [slot Buttons] (the bag bar repeats the general slots)
var _hotbar_panel: PanelContainer
var _bag_bar: PanelContainer
var _bag_free: Label
var _bag_peek: PanelContainer  # a bag's contents while the mouse rests on it in the bag bar
var _toasts: VBoxContainer  # "+3 Wolf Pelt" notes over the bag bar
var _owned: Dictionary = {}  # item id -> how many you own, to notice what's new
var _owned_known := false
var _bag_windows: Dictionary = {}  # general slot -> open bag window
var _doll_view: SubViewport
var _doll_stage: Node3D
var _doll_key := ""
var _cursor_icon: TextureRect
var _cursor_count: Label
var _sell_cursor: Button
var _coin_label: Label
var _weight_label: Label
var _stats_label: Label
var _faction_label: Label

var _help_panel: PanelContainer
var _settings_panel: PanelContainer
var _settings_rows: VBoxContainer
var _banner: Label
var _banner_time := 0.0
var _death_label: Label
var _crosshair: Control
var _ring_drawn := false


func _ready() -> void:
	layer = 10
	add_to_group("hud")  # the player asks us each frame whether a window needs the cursor
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	root.resized.connect(func() -> void: _layout_bags())
	_build_player_window()
	_build_target_window()
	_build_cast_bar()
	_build_hotbar()
	_build_log()
	_build_quest_tracker()
	_build_group_window()
	_build_invite()
	_build_item_window()
	_build_skills_window()
	_build_loot_window()
	_build_trade_window()
	_build_service_window()
	_build_inventory()
	_build_help()
	_build_menu_icons()
	_build_buffs()
	_build_bag_bar()
	_build_settings()
	_build_overlays()
	_build_menu()
	World.log_message.connect(add_log)
	World.loot_opened.connect(_on_loot_opened)
	World.loot_changed.connect(_on_loot_opened)
	World.loot_closed.connect(_on_loot_closed)
	World.player_died.connect(_on_player_died)
	World.service_opened.connect(_on_service_opened)
	World.service_changed.connect(_refresh_service)
	World.service_closed.connect(func() -> void:
		_service_panel.visible = false
		_service_npc = null
		_refresh_inventory())
	World.group_invited.connect(_on_group_invited)
	World.trade_opened.connect(_on_trade_opened)
	World.trade_changed.connect(_refresh_trade)
	World.trade_closed.connect(func() -> void: _trade_panel.visible = false; _refresh_inventory())


func bind_player(p: Player) -> void:
	player = p
	player.inventory_changed.connect(_refresh_inventory)
	player.inventory_changed.connect(_refresh_quests)
	player.quests_changed.connect(_refresh_quests)
	_refresh_inventory()
	_refresh_quests()


func show_banner(text: String) -> void:
	_banner.text = text
	_banner_time = 4.0


# --- building ---------------------------------------------------------------

func _build_player_window() -> void:
	var p := UIKit.panel()
	UIKit.place(p, Vector2(0, 0), Vector2(12, 12))
	root.add_child(p)
	_player_panel = p
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	p.add_child(v)
	_name_label = UIKit.label("", 15, UIKit.GOLD)
	v.add_child(_name_label)
	var hp := _bar_row(Color(0.78, 0.18, 0.16))
	_hp_bar = hp[0]
	_hp_text = hp[1]
	v.add_child(hp[2])
	var mana := _bar_row(Color(0.22, 0.4, 0.9))
	_mana_bar = mana[0]
	_mana_text = mana[1]
	_mana_row = mana[2]
	v.add_child(_mana_row)
	var stam := _bar_row(Color(0.35, 0.72, 0.3), 10.0)
	_stamina_bar = stam[0]
	_stamina_text = stam[1]
	_stamina_row = stam[2]
	v.add_child(_stamina_row)
	var xp := _bar_row(Color(0.85, 0.7, 0.25), 7.0)
	_xp_bar = xp[0]
	_xp_text = xp[1]
	v.add_child(xp[2])
	_buff_label = UIKit.label("", 11, Color(0.6, 0.85, 1.0))
	_buff_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	_buff_label.custom_minimum_size.x = 290
	v.add_child(_buff_label)


func _bar_row(color: Color, height := 14.0) -> Array:
	var row := HBoxContainer.new()
	var b := UIKit.bar(color, 220.0, height)
	b.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var t := UIKit.label("", 12)
	t.custom_minimum_size.x = 96
	row.add_child(b)
	row.add_child(t)
	return [b, t, row]


func _build_target_window() -> void:
	_target_panel = UIKit.panel()
	UIKit.place(_target_panel, Vector2(0.5, 0), Vector2(0, 12))
	root.add_child(_target_panel)
	var v := VBoxContainer.new()
	_target_panel.add_child(v)
	_target_name = UIKit.label("", 16)
	_target_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(_target_name)
	var row := HBoxContainer.new()
	_target_bar = UIKit.bar(Color(0.78, 0.18, 0.16), 260.0)
	_target_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_target_text = UIKit.label("", 12)
	_target_text.custom_minimum_size.x = 40
	row.add_child(_target_bar)
	row.add_child(_target_text)
	v.add_child(row)
	_attack_tag = UIKit.label("AUTO ATTACK", 12, Color(1, 0.4, 0.35))
	_attack_tag.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(_attack_tag)
	_target_panel.visible = false


func _build_cast_bar() -> void:
	_cast_panel = UIKit.panel()
	UIKit.place(_cast_panel, Vector2(0.5, 1), Vector2(0, -150))
	root.add_child(_cast_panel)
	var v := VBoxContainer.new()
	_cast_panel.add_child(v)
	_cast_label = UIKit.label("", 13, Color(0.7, 0.85, 1))
	_cast_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(_cast_label)
	_cast_bar = UIKit.bar(Color(0.55, 0.45, 0.9), 280.0, 10.0)
	v.add_child(_cast_bar)
	_cast_panel.visible = false


## EQ-style hotbar: one row of square gems (spells and abilities, keys 1-8)
## and the three combat toggles (Q attack, R ranged, X sit). Menus live in
## the small icons by the gear, top right.
func _build_hotbar() -> void:
	var p := UIKit.panel()
	UIKit.place(p, Vector2(1, 1), Vector2(-12, -12))
	root.add_child(p)
	_hotbar_panel = p
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 5)
	p.add_child(row)
	for i in 8:
		var slot := HotSlot.new()
		slot.key_text = str(i + 1)
		slot.pressed.connect(func() -> void:
			if i < player.spells.size():
				World.request_cast(player.entity_id, player.spells[i]))
		slot.visible = false
		row.add_child(slot)
		_spell_slots.append(slot)
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(8, 0)
	row.add_child(gap)
	_attack_slot = _action_slot(row, "Q", "action_attack", "Attack (Q)\nTurns auto attack on or off. Glows red while you're swinging.",
			func() -> void: World.request_toggle_attack(player.entity_id))
	_ranged_slot = _action_slot(row, "R", "action_ranged", "Ranged (R)\nFires your bow or sling at your target: pull one mob to you.",
			func() -> void: World.request_ranged(player.entity_id))
	_sit_slot = _action_slot(row, "X", "action_sit", "Sit / Stand (X)\nRest to regain health and mana faster.",
			func() -> void: World.request_sit(player.entity_id, not player.sitting))
	_sit_slot.lit_color = Color(0.45, 0.75, 1.0)


func _action_slot(row: Control, key: String, icon_name: String, tip: String, act: Callable) -> HotSlot:
	var slot := HotSlot.new()
	slot.key_text = key
	slot.picture = GameData.icon(icon_name)
	slot.tooltip_text = tip
	slot.pressed.connect(act)
	row.add_child(slot)
	return slot


## Inventory, skills and consider: small icons beside the gear, top right.
func _build_menu_icons() -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 5)
	UIKit.place(row, Vector2(1, 0), Vector2(-54, 12))
	root.add_child(row)
	for m: Array in [["C", "action_consider", "Consider (C)\nHow tough is your target, and how do they regard you?", func() -> void: World.request_consider(player.entity_id)],
			["K", "action_skills", "Skills (K)", func() -> void: _toggle_skills()],
			["I", "leather_backpack", "Inventory (I)", func() -> void: _toggle_inventory()]]:
		var slot := HotSlot.new()
		slot.custom_minimum_size = Vector2(36, 36)
		slot.key_text = m[0]
		slot.picture = GameData.icon(m[1])
		slot.tooltip_text = m[2]
		slot.pressed.connect(m[3])
		row.add_child(slot)


## Your buffs, on the right: icon, name and time left (or "until level 10"),
## the spell's description on hover. Stays clear of the inventory and help
## windows, which share that side.
func _build_buffs() -> void:
	_buff_panel = UIKit.panel()
	root.add_child(_buff_panel)
	_buff_rows = VBoxContainer.new()
	_buff_rows.add_theme_constant_override("separation", 4)
	_buff_panel.add_child(_buff_rows)
	_buff_panel.visible = false
	_debuff_panel = UIKit.panel()
	root.add_child(_debuff_panel)
	_debuff_rows = VBoxContainer.new()
	_debuff_rows.add_theme_constant_override("separation", 4)
	_debuff_panel.add_child(_debuff_rows)
	_debuff_panel.visible = false


## [spell id, seconds left] for what's hurting or holding you: damage over
## time (poison, fire, frost) and roots.
func _debuff_list() -> Array:
	var out: Array = []
	for dot: Dictionary in player.dots:
		out.append([str(dot["spell"]), maxf(0.0, (int(dot.get("ticks", 1)) - 1) * 3.0 + float(dot.get("next", 0.0)))])
	if player.root_left > 0.0:
		out.append(["root", player.root_left])
	return out


## [spell id, seconds left or -1 for "until a level"] for each buff on you.
func _buff_list() -> Array:
	var out: Array = []
	if player.elders_blessing():
		out.append(["blessing_of_the_elders", -1.0])
	for spell_id: String in player.buffs:
		out.append([spell_id, float(player.buffs[spell_id].get("left", 0.0))])
	return out


func _update_buffs() -> void:
	_buff_shape = _fill_effects(_buff_panel, _buff_rows, _buff_shape, _buff_list(), "Buffs", UIKit.GOLD, HotSlot.GEMS["buff"])
	_debuff_shape = _fill_effects(_debuff_panel, _debuff_rows, _debuff_shape, _debuff_list(), "Debuffs", Color(1.0, 0.45, 0.4), HotSlot.GEMS["damage"])
	# right edge under the top icons, or left of whichever right-side window is open
	var right := root.size.x - 12.0
	for w: Control in [_inv_panel, _help_panel]:
		if w.visible:
			right = minf(right, w.position.x - 8.0)
	var y := 60.0
	for panel: PanelContainer in [_buff_panel, _debuff_panel]:
		if not panel.visible:
			continue
		panel.reset_size()
		panel.position = Vector2(right - panel.size.x, y)
		y += panel.size.y + 6.0


## Fills a buff-style window from [[spell id, seconds left (-1 for "until a
## level")]]; rebuilds its rows only when the list of effects changes. Returns
## the new shape.
func _fill_effects(panel: PanelContainer, rows_box: VBoxContainer, shape_was: String, list: Array, title: String, title_color: Color, gem: Color) -> String:
	panel.visible = not list.is_empty()
	if list.is_empty():
		return ""
	var shape := str(list.map(func(b: Array) -> String: return b[0]))
	if shape != shape_was:
		for c in rows_box.get_children():
			c.queue_free()
		rows_box.add_child(UIKit.label(title, 12, title_color))
		for b: Array in list:
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 6)
			row.mouse_filter = Control.MOUSE_FILTER_PASS
			row.tooltip_text = _buff_tooltip(b[0])
			var slot := HotSlot.new()
			slot.custom_minimum_size = Vector2(28, 28)
			slot.picture = GameData.icon("spell_" + str(b[0]))
			var s: Dictionary = GameData.spells.get(b[0], {})
			slot.fallback = "".join(Array(str(s.get("name", "?")).split(" ")).map(func(w: String) -> String: return w.left(1)))
			slot.gem = gem
			slot.tooltip_text = row.tooltip_text
			row.add_child(slot)
			var text := VBoxContainer.new()
			text.add_theme_constant_override("separation", 0)
			var name := UIKit.label(str(s.get("name", b[0])), 12, UIKit.TEXT)
			var left := UIKit.label("", 11, UIKit.DIM)
			left.name = "left"
			text.add_child(name)
			text.add_child(left)
			row.add_child(text)
			row.set_meta("spell", b[0])
			rows_box.add_child(row)
	var rows := rows_box.get_children().filter(func(c: Node) -> bool: return c.has_meta("spell"))
	for i in mini(rows.size(), list.size()):
		var secs: float = list[i][1]
		var tip := _buff_tooltip(list[i][0], secs)
		(rows[i] as Control).tooltip_text = tip
		for c: Control in (rows[i] as Node).find_children("*", "HotSlot", false, false):
			c.tooltip_text = tip
		var label := (rows[i] as Node).find_child("left", true, false) as Label
		label.text = "until level %d" % int(World.cfg("elders_blessing", {}).get("until_level", 10)) if secs < 0.0 \
				else ("%dm %02ds" % [int(secs) / 60, int(secs) % 60] if secs >= 60.0 else "%ds" % ceili(secs))
	return shape


## A buff's tooltip: what it does, its effects, and how long it has left (the
## Blessing of the Elders: which level it fades at, and how far that is).
func _buff_tooltip(spell_id: String, secs := 0.0) -> String:
	var s: Dictionary = GameData.spells.get(spell_id, {})
	var lines: PackedStringArray = [str(s.get("name", spell_id))]
	if s.has("desc"):
		lines.append(str(s["desc"]))
	var stats: Dictionary = s.get("stats", {})
	var fx := PackedStringArray()
	for stat: String in stats:
		fx.append("%s %+d" % [ATTR_NAMES.get(stat, stat.to_upper()), int(stats[stat])])
	if spell_id == "blessing_of_the_elders":
		fx.append("Experience +%d%%" % int(World.cfg("elders_blessing", {}).get("xp_pct", 15)))
	if str(s.get("type", "")) == "dot":
		for dot: Dictionary in player.dots:
			if dot["spell"] == spell_id:
				fx.append("%d damage every 3 seconds" % int(dot["damage"]))
				break
	if spell_id == "root" and player.root_left > 0.0:
		fx.append("You can't move")
	if not fx.is_empty():
		lines.append("   ".join(fx))
	if spell_id == "blessing_of_the_elders":
		var until := int(World.cfg("elders_blessing", {}).get("until_level", 10))
		var togo := until - player.level
		lines.append("Fades at level %d (you're level %d: %d to go)" % [until, player.level, togo])
	elif secs > 0.0:
		lines.append("Time left: %s" % ("%dm %02ds" % [int(secs) / 60, int(secs) % 60] if secs >= 60.0 else "%ds" % ceili(secs)))
	return "\n".join(lines)


## The bag bar: your eight general slots over the hotbar, always there. They
## work like the inventory window's (click, ctrl-click, shift-click, right-click
## a bag to open it); bags show how full they are, rest the mouse on one to peek
## inside, and "+3 Wolf Pelt" notes float up when something new comes in.
func _build_bag_bar() -> void:
	_bag_bar = UIKit.panel()
	root.add_child(_bag_bar)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 4)
	_bag_bar.add_child(row)
	for g in Pack.GENERAL:
		var b := _make_slot("g:%d" % g, "", 40)
		var fill := UIKit.label("", 10, Color(0.85, 0.85, 0.8))
		fill.name = "fill"
		fill.set_anchors_preset(Control.PRESET_TOP_LEFT)
		fill.offset_left = 3
		fill.offset_top = 1
		fill.add_theme_color_override("font_outline_color", Color(0, 0, 0))
		fill.add_theme_constant_override("outline_size", 4)
		fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(fill)
		b.mouse_entered.connect(func() -> void: _peek_bag(g, b))
		b.mouse_exited.connect(func() -> void: _peek_bag(-1, null))
		row.add_child(b)
	_bag_free = UIKit.label("", 12, UIKit.DIM)
	_bag_free.custom_minimum_size.x = 34
	_bag_free.size_flags_horizontal = Control.SIZE_EXPAND_FILL  # takes up any width the character window adds
	_bag_free.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_bag_free.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_bag_free.tooltip_text = "Free slots, in your general slots and all your bags."
	_bag_free.mouse_filter = Control.MOUSE_FILTER_PASS
	row.add_child(_bag_free)
	_toasts = VBoxContainer.new()
	_toasts.add_theme_constant_override("separation", 2)
	_toasts.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_toasts)
	_refresh_inventory()


## Fill counts on the bags, and free slots in all.
func _refresh_bag_bar() -> void:
	if _bag_bar == null or player == null:
		return
	var free := 0
	for place: String in player.pack.places():
		if player.pack.get_at(place).is_empty():
			free += 1
	for g in Pack.GENERAL:
		var b := _bag_bar_slot(g)
		if b == null:
			continue
		var e: Dictionary = player.pack.slots[g]
		var fill := b.find_child("fill", false, false) as Label
		if e.has("contents"):
			var inside: Array = e["contents"]
			var used := inside.filter(func(c: Dictionary) -> bool: return not c.is_empty()).size()
			fill.text = "%d/%d" % [used, inside.size()]
			fill.add_theme_color_override("font_color", Color(1, 0.55, 0.45) if used >= inside.size() else Color(0.85, 0.85, 0.8))
		else:
			fill.text = ""
	_bag_free.text = "%d\nfree" % free
	_bag_free.add_theme_color_override("font_color", Color(1, 0.55, 0.45) if free == 0 else UIKit.DIM)


func _bag_bar_slot(g: int) -> Button:
	for b: Variant in _slot_buttons.get("g:%d" % g, []):
		if is_instance_valid(b) and (b as Node).find_child("fill", false, false) != null:
			return b
	return null


## Shows a bag's contents over its slot while the mouse rests there (unless
## the bag is open anyway); g < 0 hides it.
func _peek_bag(g: int, slot: Button) -> void:
	if _bag_peek != null:
		_bag_peek.queue_free()
		_bag_peek = null
	if g < 0 or _bag_windows.has(g):
		return
	var e: Dictionary = player.pack.slots[g]
	if not e.has("contents"):
		return
	_bag_peek = UIKit.panel()
	_bag_peek.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 3)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bag_peek.add_child(v)
	v.add_child(UIKit.label(GameData.item_name(e["item"]), 12, UIKit.GOLD))
	var grid := GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation", 3)
	grid.add_theme_constant_override("v_separation", 3)
	v.add_child(grid)
	for c: Dictionary in e["contents"]:
		var cell := PanelContainer.new()
		cell.custom_minimum_size = Vector2(32, 32)
		cell.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0.1, 0.1, 0.12, 0.9)
		sb.set_corner_radius_all(3)
		cell.add_theme_stylebox_override("panel", sb)
		if not c.is_empty():
			var icon := TextureRect.new()
			icon.texture = GameData.item_icon(c["item"])
			icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
			cell.add_child(icon)
			if int(c.get("count", 1)) > 1:
				var n := UIKit.label(str(c["count"]), 10, UIKit.TEXT)
				n.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
				n.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
				n.mouse_filter = Control.MOUSE_FILTER_IGNORE
				cell.add_child(n)
		grid.add_child(cell)
	root.add_child(_bag_peek)
	_bag_peek.reset_size()
	var size := _bag_peek.get_combined_minimum_size()
	_bag_peek.position = Vector2(clampf(slot.global_position.x + slot.size.x * 0.5 - size.x * 0.5, 12.0, root.size.x - size.x - 12.0),
			_bag_bar.position.y - size.y - 6.0)


## "Elowen wants 4 (you have 2)" for each active quest of yours that wants
## this item.
func _quest_wants(item_id: String) -> Array:
	var out: Array = []
	if item_id == "" or player == null:
		return out
	for quest_id: String in player.quests:
		var q: Dictionary = GameData.quests.get(quest_id, {})
		if not player.quests[quest_id].get("active", false) or not (q.get("wants", {}) as Dictionary).has(item_id):
			continue
		var need := int(q["wants"][item_id])
		var have := int(World.quest_progress(player, quest_id).get(item_id, 0))
		out.append("Quest: %s wants %d (you have %d)" % [GameData.npcs[q["giver"]]["name"], need, have])
	return out


## Notes over the bag bar for whatever you now own more of than before
## (loot, a purchase, a reward); moving things between bags doesn't count.
func _notice_new_items() -> void:
	if player == null or _toasts == null:
		return
	var now := {}
	for id: Variant in player.owned_item_ids():
		now[id] = int(now.get(id, 0)) + 1
	if _owned_known:
		for id: String in now:
			var gained := int(now[id]) - int(_owned.get(id, 0))
			if gained > 0:
				_toast(id, gained)
	_owned = now
	_owned_known = true


func _toast(item_id: String, n: int) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var icon := TextureRect.new()
	icon.texture = GameData.item_icon(item_id)
	icon.custom_minimum_size = Vector2(26, 26)
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	row.add_child(icon)
	var label := UIKit.label("+%d %s" % [n, GameData.item_name(item_id)] if n > 1 else "+ %s" % GameData.item_name(item_id), 14, GameData.item_color(item_id))
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	label.add_theme_constant_override("outline_size", 5)
	row.add_child(label)
	_toasts.add_child(row)
	while _toasts.get_child_count() > 5:
		_toasts.get_child(0).free()
	var tw := row.create_tween()
	tw.tween_interval(2.5)
	tw.tween_property(row, "modulate:a", 0.0, 1.0)
	tw.tween_callback(row.queue_free)


func _layout_bag_bar() -> void:
	if _bag_bar == null or _hotbar_panel == null:
		return
	# with the character window open, it and the bar share one width
	_bag_bar.custom_minimum_size.x = 0.0
	_inv_panel.custom_minimum_size.x = 0.0
	if _inv_panel.visible:
		var width := maxf(_bag_bar.get_combined_minimum_size().x, _inv_panel.get_combined_minimum_size().x)
		_bag_bar.custom_minimum_size.x = width
		_inv_panel.custom_minimum_size.x = width
	_bag_bar.reset_size()
	_bag_bar.position = Vector2(_hotbar_panel.position.x + _hotbar_panel.size.x - _bag_bar.size.x, _hotbar_panel.position.y - _bag_bar.size.y - 6.0)
	_toasts.reset_size()
	_toasts.position = Vector2(_bag_bar.position.x, _bag_bar.position.y - _toasts.size.y - 8.0)
	_toasts.visible = _bag_peek == null and not _inv_panel.visible and _bag_windows.is_empty()  # the peek, the character window and open bags sit where the notes do
	if _inv_panel.visible:  # the character window stands on the bag bar, right edges lined up
		_inv_panel.reset_size()
		var bottom := _bag_bar.position.y - 6.0
		_inv_panel.position = Vector2(_bag_bar.position.x + _bag_bar.size.x - _inv_panel.size.x, maxf(bottom - _inv_panel.size.y, 12.0))


func _toggle_skills() -> void:
	_skills_panel.visible = not _skills_panel.visible
	_skills_timer = 0.0


func _build_log() -> void:
	var p := UIKit.panel()
	UIKit.place(p, Vector2(0, 1), Vector2(12, -12))
	root.add_child(p)
	_log = RichTextLabel.new()
	_log.custom_minimum_size = Vector2(500, 200)
	_log.scroll_following = true
	_log.selection_enabled = false
	_log.add_theme_font_size_override("normal_font_size", 13)
	_log.meta_underlined = false
	_log.meta_clicked.connect(_on_log_keyword)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	p.add_child(v)
	v.add_child(_log)
	_chat = LineEdit.new()
	_chat.placeholder_text = "Enter to chat, / for commands (/help)"
	_chat.max_length = World.CHAT_MAX
	_chat.add_theme_font_size_override("font_size", 13)
	_chat.text_submitted.connect(func(t: String) -> void:
		var cmd := t.strip_edges().get_slice(" ", 0).to_lower()
		if cmd == "/follow" or cmd == "/f":
			player.start_follow()  # your own feet: handled on this machine
		elif cmd == "/stopfollow":
			player.stop_follow()
		else:
			var line := _through_channel(t.strip_edges())
			if line != "":
				World.request_chat(player.entity_id, line)
		_chat.clear()
		_chat.release_focus())
	_chat.gui_input.connect(func(ev: InputEvent) -> void:
		if ev.is_action_pressed("cancel"):
			_chat.clear()
			_chat.release_focus()
			_chat.accept_event())
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	_channel_label = UIKit.label("", 13, World.C_CHAT_SAY)
	row.add_child(_channel_label)
	_chat.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(_chat)
	v.add_child(row)
	_set_channel("")
	_build_group_log()


## Group chat's own window, beside the main one: shown only while you're in a
## group, so what your group says doesn't scroll away under the fight. The
## lines still show in the main window too. The button talks to the group.
func _build_group_log() -> void:
	_group_log_panel = UIKit.panel()
	UIKit.place(_group_log_panel, Vector2(0, 1), Vector2(530, -12))
	root.add_child(_group_log_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	_group_log_panel.add_child(v)
	var head := HBoxContainer.new()
	var title := UIKit.label("Group", 13, World.C_CHAT_GROUP)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(title)
	var talk := UIKit.button("Talk (/g)", Vector2(84, 24))
	talk.add_theme_font_size_override("font_size", 11)
	talk.focus_mode = Control.FOCUS_NONE
	talk.tooltip_text = "Chat to your group: plain lines go to /g until you switch (/s for say)."
	talk.pressed.connect(func() -> void:
		_set_channel("/g")
		_open_chat(""))
	head.add_child(talk)
	v.add_child(head)
	_group_log = RichTextLabel.new()
	_group_log.custom_minimum_size = Vector2(340, 150)
	_group_log.scroll_following = true
	_group_log.selection_enabled = false
	_group_log.add_theme_font_size_override("normal_font_size", 13)
	_group_log.meta_underlined = false
	_group_log.meta_clicked.connect(_on_log_keyword)
	v.add_child(_group_log)
	_group_log_panel.visible = false


## Chat channels stick, as in EQ's chat windows: using /g (or /sh, /ooc,
## /t Name, /r) makes plain lines go there until another channel (or /s) is
## used. A channel command on its own just switches. Returns the line to
## send, or "" when there is nothing to send.
func _through_channel(line: String) -> String:
	if line == "":
		return ""
	if not line.begins_with("/"):
		return line if _chat_channel == "" else "%s %s" % [_chat_channel, line]
	var cmd := line.get_slice(" ", 0).to_lower()
	var rest := line.substr(cmd.length()).strip_edges()
	match cmd:
		"/say", "/s":
			_set_channel("")
		"/g", "/gsay", "/group":
			_set_channel("/g")
		"/shout", "/sh":
			_set_channel("/sh")
		"/ooc", "/o":
			_set_channel("/ooc")
		"/reply", "/r":
			_set_channel("/r")
		"/tell", "/t", "/msg":
			if rest == "":
				return line  # the server explains how to /tell
			_set_channel("/t " + rest.get_slice(" ", 0))
			rest = rest.substr(rest.get_slice(" ", 0).length()).strip_edges()
		_:
			return line  # other commands (/who, /loc, /invite...) don't change the channel
	return "" if rest == "" else line


func _set_channel(channel: String) -> void:
	_chat_channel = channel
	var names := {"": ["Say", World.C_CHAT_SAY], "/g": ["Group", World.C_CHAT_GROUP], "/sh": ["Shout", World.C_CHAT_SHOUT],
			"/ooc": ["OOC", World.C_CHAT_OOC], "/r": ["Reply", World.C_CHAT_TELL]}
	var shown: Array = names.get(channel, ["Tell " + channel.substr(3), World.C_CHAT_TELL])
	_channel_label.text = "%s:" % shown[0]
	_channel_label.add_theme_color_override("font_color", shown[1])
	_chat.placeholder_text = "Enter to %s, / for commands (/help)" % ("say" if channel == "" else "chat in " + str(shown[0]).to_lower() if not channel.begins_with("/t") else "send a tell")


## True while the chat line has the keyboard: the player stops moving.
func is_typing() -> bool:
	return _chat != null and _chat.has_focus()


func _open_chat(prefix: String) -> void:
	_chat.grab_focus()
	_chat.text = prefix
	_chat.caret_column = prefix.length()


## Your group: each member's name, health and mana. Click one to target them
## (F2-F6 do the same, in this order).
func _build_group_window() -> void:
	_group_panel = UIKit.panel()
	UIKit.place(_group_panel, Vector2(0, 0.5), Vector2(12, -40))
	root.add_child(_group_panel)
	_group_rows = VBoxContainer.new()
	_group_rows.add_theme_constant_override("separation", 4)
	_group_panel.add_child(_group_rows)
	_group_panel.visible = false


func _update_group() -> void:
	var others := player.group.filter(func(m: Dictionary) -> bool: return int(m["id"]) != player.entity_id)
	_group_panel.visible = not player.group.is_empty()
	_group_log_panel.visible = not player.group.is_empty()
	var shape := str(player.group.map(func(m: Dictionary) -> String: return "%s:%s" % [m["id"], m["leader"]]))
	if shape != _group_shape:
		_group_shape = shape
		for child in _group_rows.get_children():
			child.queue_free()
		_group_bars.clear()
		_group_rows.add_child(UIKit.label("Group", 13, UIKit.GOLD))
		var ordered := player.group.filter(func(x: Dictionary) -> bool: return int(x["id"]) == player.entity_id) + others  # you first
		for i in ordered.size():
			var m: Dictionary = ordered[i]
			var row := Button.new()
			row.flat = true
			row.focus_mode = Control.FOCUS_NONE
			row.custom_minimum_size = Vector2(210, 44)
			var v := VBoxContainer.new()
			v.add_theme_constant_override("separation", 2)
			v.mouse_filter = Control.MOUSE_FILTER_IGNORE
			v.set_anchors_preset(Control.PRESET_FULL_RECT)
			row.add_child(v)
			var name := UIKit.label("", 12, UIKit.TEXT)
			name.mouse_filter = Control.MOUSE_FILTER_IGNORE
			v.add_child(name)
			var hp := UIKit.bar(Color(0.8, 0.22, 0.2), 200.0, 8.0)
			var mana := UIKit.bar(Color(0.25, 0.4, 0.9), 200.0, 5.0)
			v.add_child(hp)
			v.add_child(mana)
			var id := int(m["id"])
			var key := i  # 0 is you (F1); others are F2 onward
			row.pressed.connect(func() -> void:
				if key == 0:
					World.request_set_target(player.entity_id, player.entity_id)
				else:
					player.target_group_member(key - 1))
			_group_rows.add_child(row)
			_group_bars[id] = [hp, mana, name]
	for m: Dictionary in player.group:
		var parts: Array = _group_bars.get(int(m["id"]), [])
		if parts.is_empty():
			continue
		var cls := str(GameData.classes.get(str(m["class"]), {}).get("name", "?"))
		var away := "" if World.get_object(int(m["id"])) != null or int(m["id"]) == player.entity_id else "  (elsewhere)"
		(parts[2] as Label).text = "%s%s  %d %s%s%s" % ["* " if m["leader"] else "", m["name"], int(m["level"]), cls.left(3),
				"  (dead)" if m.get("dead", false) else "", away]
		(parts[0] as ProgressBar).max_value = maxi(1, int(m["max_hp"]))
		(parts[0] as ProgressBar).value = int(m["hp"])
		(parts[1] as ProgressBar).max_value = maxi(1, int(m["max_mana"]))
		(parts[1] as ProgressBar).value = int(m["mana"])
		(parts[1] as ProgressBar).visible = int(m["max_mana"]) > 0


## K: every skill your class can learn, by group, with its value, the cap at
## your level, and a bar. Skills rise as you use them.
func _build_skills_window() -> void:
	_skills_panel = UIKit.panel()
	UIKit.place(_skills_panel, Vector2(0.5, 0.5), Vector2(-260, -40))
	root.add_child(_skills_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	_skills_panel.add_child(v)
	v.add_child(UIKit.label("Skills", 16, UIKit.GOLD))
	var note := UIKit.label("Skills rise as you use them, up to a cap that grows with your level. K or Esc to close.", 11, UIKit.DIM)
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.custom_minimum_size.x = 330
	v.add_child(note)
	_skills_box = VBoxContainer.new()
	_skills_box.add_theme_constant_override("separation", 3)
	v.add_child(_skills_box)
	_skills_panel.visible = false


func _refresh_skills() -> void:
	for child in _skills_box.get_children():
		child.queue_free()
	var table: Dictionary = GameData.skills["skills"]
	for group: String in GameData.skills["groups"]:
		var rows: Array = []
		for id: String in table:
			var cap := GameData.skill_cap(player.char_class, id, player.level)
			if table[id]["group"] == group and cap > 0:
				rows.append([id, mini(int(player.skills.get(id, 0)), cap), cap])
		if rows.is_empty():
			continue
		_skills_box.add_child(UIKit.label(group, 13, UIKit.GOLD))
		for r: Array in rows:
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 8)
			var name := UIKit.label(GameData.skill_name(r[0]), 12, UIKit.TEXT)
			name.custom_minimum_size.x = 120
			row.add_child(name)
			var bar := UIKit.bar(Color(0.86, 0.72, 0.42), 130.0, 8.0)
			bar.max_value = r[2]
			bar.value = r[1]
			bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			row.add_child(bar)
			var nums := UIKit.label("%d / %d" % [r[1], r[2]], 12, UIKit.DIM if r[1] < r[2] else UIKit.GOLD)
			row.add_child(nums)
			_skills_box.add_child(row)


## Right-click on an item button opens the item window. Buttons that are
## reused (trade slots) keep the item they show in a meta, hooked up once.
func _inspectable(b: Button, item_id: String) -> void:
	b.set_meta("inspect_item", item_id)
	if b.has_meta("inspect_hooked"):
		return
	b.set_meta("inspect_hooked", true)
	b.gui_input.connect(func(ev: InputEvent) -> void:
		if ev is InputEventMouseButton and ev.pressed and ev.button_index == MOUSE_BUTTON_RIGHT:
			var id := str(b.get_meta("inspect_item", ""))
			if id != "":
				show_item(id))


## The item window: everything about one item, with a turning 3D preview when
## it has a model (worn gear, weapons, shields). It stays open until closed.
func _build_item_window() -> void:
	_item_panel = UIKit.panel()
	UIKit.place(_item_panel, Vector2(0.5, 0.45), Vector2(-120, 0))
	root.add_child(_item_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	v.custom_minimum_size.x = 300
	_item_panel.add_child(v)
	_item_title = UIKit.label("", 17, UIKit.GOLD)
	_item_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(_item_title)
	_item_view_box = SubViewportContainer.new()
	_item_view_box.stretch = true
	_item_view_box.custom_minimum_size = Vector2(300, 190)
	v.add_child(_item_view_box)
	var view := SubViewport.new()
	view.own_world_3d = true
	view.transparent_bg = true
	view.msaa_3d = Viewport.MSAA_2X
	_item_view_box.add_child(view)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_CLEAR_COLOR
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.75, 0.78, 0.85)
	env.environment.ambient_light_energy = 0.9
	view.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-45, 30, 0)
	sun.light_energy = 1.2
	view.add_child(sun)
	_item_stage = Node3D.new()
	view.add_child(_item_stage)
	_item_cam = Camera3D.new()
	_item_cam.fov = 35.0
	view.add_child(_item_cam)
	_item_text = RichTextLabel.new()
	_item_text.bbcode_enabled = true
	_item_text.fit_content = true
	_item_text.scroll_active = false
	_item_text.custom_minimum_size.x = 300
	_item_text.add_theme_font_size_override("normal_font_size", 13)
	v.add_child(_item_text)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	_item_use = UIKit.button("Use", Vector2(90, 32))
	_item_use.pressed.connect(func() -> void:
		for slot: String in player.equipment:
			if player.equipment[slot] == _item_shown:
				World.request_item_click(player.entity_id, slot))
	row.add_child(_item_use)
	_item_link = UIKit.button("Link in chat", Vector2(0, 32))
	_item_link.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_item_link.pressed.connect(func() -> void:
		_open_chat(_chat.text + ("" if _chat.text == "" or _chat.text.ends_with(" ") else " ") + "{item:%s} " % _item_shown))
	row.add_child(_item_link)
	var close := UIKit.button("Close", Vector2(80, 32))
	close.pressed.connect(func() -> void: _item_panel.visible = false)
	row.add_child(close)
	v.add_child(row)
	_item_panel.visible = false


func show_item(item_id: String) -> void:
	var it := GameData.item(item_id)
	if it.is_empty():
		return
	_item_shown = item_id
	_item_title.text = str(it["name"])
	_item_title.add_theme_color_override("font_color", GameData.item_color(item_id))
	var lines := _item_tooltip(item_id, true).split("\n")
	lines.remove_at(0)  # the name is the title
	_item_text.text = "\n".join(lines)
	var worn := item_id in player.equipment.values()
	_item_use.visible = it.has("click") and worn
	for child in _item_stage.get_children():
		child.queue_free()
	var paths: Array = []
	var wear := str(it.get("wear", ""))
	if wear != "":
		for p: Dictionary in GameData.models.get("gear", {}).get(wear, {}).get("pieces", []):
			if not str(p["path"]).ends_with("_r.glb"):  # one of a pair is enough to show
				paths.append(p["path"])
	elif it.has("model") and GameData.models["weapons"].has(str(it["model"])):
		paths.append(GameData.models["weapons"][str(it["model"])])
	_item_view_box.visible = not paths.is_empty()
	if not paths.is_empty():
		var holder := Node3D.new()
		_item_stage.add_child(holder)
		var box := AABB()
		var first := true
		for path: String in paths:
			var model: Node3D = (load(path) as PackedScene).instantiate()
			holder.add_child(model)
			for mi: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
				var b := _relative_aabb(mi, holder)
				box = b if first else box.merge(b)
				first = false
		holder.position = -box.get_center()  # turn around the piece's middle
		_item_stage.rotation = Vector3.ZERO
		var radius := maxf(box.size.length() * 0.5, 0.2)
		_item_cam.position = Vector3(0, radius * 0.45, radius * 3.0)
		_item_cam.look_at(Vector3.ZERO)
	_item_panel.visible = true


static func _relative_aabb(mi: MeshInstance3D, ancestor: Node3D) -> AABB:
	var xf := Transform3D.IDENTITY
	var n: Node = mi
	while n != ancestor and n != null:
		xf = (n as Node3D).transform * xf
		n = n.get_parent()
	return xf * mi.get_aabb()


func _build_invite() -> void:
	_invite_panel = UIKit.panel()
	UIKit.place(_invite_panel, Vector2(0.5, 0.3), Vector2.ZERO)
	root.add_child(_invite_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	_invite_panel.add_child(v)
	_invite_label = UIKit.label("", 15, UIKit.TEXT)
	v.add_child(_invite_label)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var yes := UIKit.button("Accept", Vector2(120, 34))
	yes.pressed.connect(func() -> void: World.request_group_accept(player.entity_id))
	var no := UIKit.button("Decline", Vector2(120, 34))
	no.pressed.connect(func() -> void: World.request_group_decline(player.entity_id))
	row.add_child(yes)
	row.add_child(no)
	v.add_child(row)
	_invite_panel.visible = false


func _on_group_invited(from_name: String) -> void:
	_invite_panel.visible = from_name != ""
	_invite_label.text = "%s invites you to join a group." % from_name


## Active quests and what's still needed, under the player window.
func _build_quest_tracker() -> void:
	_quest_panel = UIKit.panel()
	UIKit.place(_quest_panel, Vector2(0, 0), Vector2(12, 124))
	root.add_child(_quest_panel)
	_quest_label = RichTextLabel.new()
	_quest_label.bbcode_enabled = true
	_quest_label.fit_content = true
	_quest_label.scroll_active = false
	_quest_label.custom_minimum_size = Vector2(240, 0)
	_quest_label.add_theme_font_size_override("normal_font_size", 13)
	_quest_label.add_theme_font_size_override("bold_font_size", 13)
	_quest_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_quest_panel.add_child(_quest_label)
	_quest_panel.visible = false


func _build_loot_window() -> void:
	_loot_panel = UIKit.panel()
	UIKit.place(_loot_panel, Vector2(0.5, 0.5), Vector2(-260, -40))
	root.add_child(_loot_panel)
	var v := VBoxContainer.new()
	v.custom_minimum_size.x = 260
	_loot_panel.add_child(v)
	_loot_title = UIKit.label("", 15, UIKit.GOLD)
	v.add_child(_loot_title)
	_loot_list = VBoxContainer.new()
	v.add_child(_loot_list)
	var row := HBoxContainer.new()
	var all := UIKit.button("Loot All")
	all.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	all.pressed.connect(func() -> void:
		if is_instance_valid(_loot_corpse):
			World.request_loot_all(player.entity_id, _loot_corpse.object_id))
	var done := UIKit.button("Done")
	done.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	done.pressed.connect(func() -> void: World.request_loot_close(player.entity_id))
	row.add_child(all)
	row.add_child(done)
	v.add_child(row)
	_loot_panel.visible = false



## EQ-style give window: four slots filled by clicking bag items.
func _build_trade_window() -> void:
	_trade_panel = UIKit.panel()
	UIKit.place(_trade_panel, Vector2(0.5, 0.5), Vector2(-260, -40))
	root.add_child(_trade_panel)
	var v := VBoxContainer.new()
	v.custom_minimum_size.x = 260
	v.add_theme_constant_override("separation", 6)
	_trade_panel.add_child(v)
	_trade_title = UIKit.label("", 15, UIKit.GOLD)
	v.add_child(_trade_title)
	var hint := UIKit.label("Put items here from your cursor, or shift-click them in your bags. Click one to take it back.", 12, UIKit.DIM)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.custom_minimum_size.x = 250
	v.add_child(hint)
	var grid := GridContainer.new()
	grid.columns = World.TRADE_SLOTS
	grid.add_theme_constant_override("h_separation", 6)
	v.add_child(grid)
	for i in World.TRADE_SLOTS:
		grid.add_child(_make_slot("t:%d" % i, ""))
	var row := HBoxContainer.new()
	var give := UIKit.button("Give")
	give.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	give.pressed.connect(func() -> void: World.request_trade_give(player.entity_id))
	var cancel := UIKit.button("Cancel")
	cancel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	cancel.pressed.connect(func() -> void: World.request_trade_cancel(player.entity_id))
	row.add_child(give)
	row.add_child(cancel)
	v.add_child(row)
	_trade_panel.visible = false


## Merchant shop or bank, whichever the npc offers.
func _build_service_window() -> void:
	_service_panel = UIKit.panel()
	UIKit.place(_service_panel, Vector2(0.5, 0.5), Vector2(-240, -60))
	root.add_child(_service_panel)
	var v := VBoxContainer.new()
	v.custom_minimum_size.x = 330
	v.add_theme_constant_override("separation", 6)
	_service_panel.add_child(v)
	_service_title = UIKit.label("", 15, UIKit.GOLD)
	v.add_child(_service_title)
	_service_hint = UIKit.label("", 12, UIKit.DIM)
	v.add_child(_service_hint)
	_shop_scroll = ScrollContainer.new()
	_shop_scroll.custom_minimum_size = Vector2(330, 300)
	_shop_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	v.add_child(_shop_scroll)
	_shop_list = VBoxContainer.new()
	_shop_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_shop_scroll.add_child(_shop_list)
	_sell_cursor = UIKit.button("", Vector2(0, 36))
	_sell_cursor.pressed.connect(func() -> void: World.request_sell(player.entity_id, "cursor"))
	v.add_child(_sell_cursor)
	_sell_cursor.visible = false
	_bank_box = VBoxContainer.new()
	v.add_child(_bank_box)
	_bank_grid = GridContainer.new()
	_bank_grid.columns = 4
	_bank_box.add_child(_bank_grid)
	_bank_coin_label = UIKit.label("", 13, UIKit.GOLD)
	_bank_box.add_child(_bank_coin_label)
	var coin_row := HBoxContainer.new()
	var dep := UIKit.button("Deposit all coin")
	dep.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dep.pressed.connect(func() -> void: World.request_bank_coin(player.entity_id, player.coin))
	var wd := UIKit.button("Withdraw all coin")
	wd.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	wd.pressed.connect(func() -> void: World.request_bank_coin(player.entity_id, -player.bank_coin))
	coin_row.add_child(dep)
	coin_row.add_child(wd)
	_bank_box.add_child(coin_row)
	var done := UIKit.button("Done")
	done.pressed.connect(func() -> void: World.request_service_close(player.entity_id))
	v.add_child(done)
	_service_panel.visible = false


func _on_service_opened(npc: Npc, kind: String) -> void:
	_service_npc = npc
	var titles := {"shop": npc.display_name, "bank": "%s  -  Hearthbank" % npc.display_name,
			"guild": "%s  -  %s training" % [npc.display_name, GameData.classes[player.char_class]["name"]]}
	var hints := {"shop": "Click an item to buy one (Buy 20 for arrows and stones). Click items in your bags to sell them.",
			"bank": "Click items in your bags to deposit them; click a bank slot to take it back.",
			"guild": "Click a spell to learn it. New spells go on the next number key."}
	_service_title.text = titles[kind]
	_service_hint.text = hints[kind]
	_shop_scroll.visible = kind != "bank"
	_bank_box.visible = kind == "bank"
	_service_panel.visible = true
	_inv_panel.visible = true
	_help_panel.visible = false
	_refresh_service()
	_refresh_inventory()


func _refresh_service() -> void:
	if _service_npc == null or not is_instance_valid(_service_npc):
		return
	if player.service == "guild":
		for child in _shop_list.get_children():
			child.queue_free()
		for entry: Dictionary in World.class_spells(player.char_class):
			var spell_id: String = entry["spell"]
			var why := World.train_block(player, spell_id)
			var price := World.format_coin(int(entry["cost"])) if int(entry["cost"]) > 0 else "free"
			var b := UIKit.button("Lv %d   %s   %s" % [entry["level"], GameData.spells[spell_id]["name"], "(known)" if why == "Known." else price])
			b.alignment = HORIZONTAL_ALIGNMENT_LEFT
			b.add_theme_font_size_override("font_size", 12)
			b.tooltip_text = spell_tooltip(spell_id) + ("\n" + why if why != "" else "")
			b.disabled = why != ""
			b.pressed.connect(func() -> void: World.request_train(player.entity_id, spell_id))
			_shop_list.add_child(b)
	elif player.service == "shop":
		for child in _shop_list.get_children():
			child.queue_free()
		for ware: Dictionary in World.merchant_wares(_service_npc):
			var item_id: String = ware["item"]
			var count := int(ware["count"])
			var text := "%s   %s" % [GameData.item_name(item_id), World.format_coin(int(ware["price"]))]
			if count > 0:
				text += "   (%d)" % count
			var b := UIKit.button(text)
			b.alignment = HORIZONTAL_ALIGNMENT_LEFT
			b.add_theme_font_size_override("font_size", 12)
			b.icon = GameData.item_icon(item_id)
			b.expand_icon = false
			b.add_theme_constant_override("icon_max_width", 24)
			b.tooltip_text = _item_tooltip(item_id) + "\nRight-click for details."
			_inspectable(b, item_id)
			b.disabled = player.coin < int(ware["price"])
			var stack := Pack.stack_of(item_id)
			if stack > 1:
				b.tooltip_text += "\nShift-click to buy a stack of %d." % stack
			b.pressed.connect(func() -> void: World.request_buy(player.entity_id, item_id, stack if Input.is_key_pressed(KEY_SHIFT) else 1))
			if stack < BUY_BUNDLE:
				_shop_list.add_child(b)
				continue
			# arrows, stones and the like: a button for a bundle beside the row
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 4)
			b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(b)
			var bundle := UIKit.button("Buy %d" % BUY_BUNDLE, Vector2(64, 0))
			bundle.add_theme_font_size_override("font_size", 12)
			bundle.tooltip_text = "Buy %d %s for %s." % [BUY_BUNDLE, World.plural(GameData.item_name(item_id)), World.format_coin(int(ware["price"]) * BUY_BUNDLE)]
			bundle.disabled = player.coin < int(ware["price"]) * BUY_BUNDLE or (count > 0 and count < BUY_BUNDLE)
			bundle.pressed.connect(func() -> void: World.request_buy(player.entity_id, item_id, BUY_BUNDLE))
			row.add_child(bundle)
			_shop_list.add_child(row)
	else:
		if _bank_grid.get_child_count() == 0:
			for i in player.bank.size():
				_bank_grid.add_child(_make_slot("k:%d" % i, ""))
		_refresh_inventory()
		_bank_coin_label.text = "In the bank: %s" % _coin_text(player.bank_coin)


func _on_trade_opened(npc: Npc) -> void:
	_trade_title.text = "Trading with %s" % npc.display_name
	_trade_panel.visible = true
	_inv_panel.visible = true
	_help_panel.visible = false
	_refresh_inventory()
	_refresh_trade()


func _refresh_trade() -> void:
	_refresh_inventory()  # the trade slots are item slots like the rest


## EQ-style inventory: equipment slots around your character, your stats,
## eight general slots (bags go here; right-click one to open it) and coin.
## Items move with the cursor: click to pick up, click to put down.
func _build_inventory() -> void:
	_inv_panel = UIKit.panel()  # placed over the bag bar by _layout_bag_bar
	root.add_child(_inv_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	_inv_panel.add_child(v)
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 4)
	v.add_child(head)
	var title := UIKit.label("Inventory", 16, UIKit.GOLD)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(title)
	var tips := UIKit.button("?", Vector2(24, 22))
	tips.tooltip_text = "How to move items"
	tips.pressed.connect(func() -> void:
		_bag_hint.visible = not _bag_hint.visible
		_inv_panel.reset_size())
	head.add_child(tips)
	var close := UIKit.button("x", Vector2(24, 22))
	close.tooltip_text = "Close (I)"
	close.pressed.connect(_toggle_inventory)
	head.add_child(close)
	_bag_hint = UIKit.label(BAG_TIPS, 11, UIKit.DIM)
	_bag_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_bag_hint.custom_minimum_size.x = 330
	_bag_hint.visible = false
	v.add_child(_bag_hint)
	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 10)
	v.add_child(top)
	# the paper doll
	var doll := VBoxContainer.new()
	doll.add_theme_constant_override("separation", 4)
	top.add_child(doll)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 4)
	doll.add_child(row)
	var left := VBoxContainer.new()
	left.add_theme_constant_override("separation", 4)
	row.add_child(left)
	for slot in ["head", "neck", "arms", "hands", "ring1"]:
		left.add_child(_make_slot("e:" + slot, _slot_label(slot)))
	var view_box := SubViewportContainer.new()
	view_box.stretch = true
	view_box.custom_minimum_size = Vector2(140, 236)
	row.add_child(view_box)
	_doll_view = SubViewport.new()
	_doll_view.own_world_3d = true
	_doll_view.transparent_bg = true
	_doll_view.msaa_3d = Viewport.MSAA_2X
	view_box.add_child(_doll_view)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_CLEAR_COLOR
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.75, 0.78, 0.85)
	_doll_view.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-35, 150, 0)
	_doll_view.add_child(sun)
	_doll_stage = Node3D.new()
	_doll_view.add_child(_doll_stage)
	var cam := Camera3D.new()
	cam.fov = 30.0
	cam.position = Vector3(0, 0.95, -4.3)
	_doll_view.add_child(cam)
	cam.look_at_from_position(cam.position, Vector3(0, 0.82, 0))
	var right := VBoxContainer.new()
	right.add_theme_constant_override("separation", 4)
	row.add_child(right)
	for slot in ["chest", "waist", "legs", "feet", "ring2"]:
		right.add_child(_make_slot("e:" + slot, _slot_label(slot)))
	var hands := HBoxContainer.new()
	hands.alignment = BoxContainer.ALIGNMENT_CENTER
	hands.add_theme_constant_override("separation", 4)
	for slot in ["primary", "secondary", "range"]:
		hands.add_child(_make_slot("e:" + slot, _slot_label(slot)))
	doll.add_child(hands)
	# stats
	var stats := VBoxContainer.new()
	stats.add_theme_constant_override("separation", 2)
	stats.custom_minimum_size.x = 150
	top.add_child(stats)
	_stats_label = UIKit.label("", 12, UIKit.TEXT)
	stats.add_child(_stats_label)
	_coin_label = UIKit.label("", 12, UIKit.GOLD)
	stats.add_child(_coin_label)
	_weight_label = UIKit.label("", 12, UIKit.TEXT)
	_weight_label.tooltip_text = "What you carry, worn and packed, and your coin. Past your limit you slow down; the banker keeps coin weightless."
	_weight_label.mouse_filter = Control.MOUSE_FILTER_PASS
	stats.add_child(_weight_label)
	# standing with each faction, folded away: it's long and rarely needed
	var faction_button := UIKit.button("Faction  +", Vector2(0, 22))
	faction_button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	faction_button.flat = true
	faction_button.add_theme_font_size_override("font_size", 12)
	faction_button.add_theme_color_override("font_color", UIKit.GOLD)
	faction_button.tooltip_text = "How each faction regards you"
	stats.add_child(faction_button)
	_faction_label = UIKit.label("", 11, UIKit.DIM)
	_faction_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_faction_label.custom_minimum_size.x = 150
	_faction_label.visible = false
	v.add_child(_faction_label)
	faction_button.pressed.connect(func() -> void:
		_faction_label.visible = not _faction_label.visible
		faction_button.text = "Faction  -" if _faction_label.visible else "Faction  +"
		_inv_panel.reset_size())
	# the general slots are the bag bar, which the window sits on
	_inv_panel.visible = false
	# what the cursor holds, following the mouse
	_cursor_icon = TextureRect.new()
	_cursor_icon.custom_minimum_size = Vector2(40, 40)
	_cursor_icon.size = Vector2(40, 40)
	_cursor_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_cursor_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_cursor_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_cursor_icon.z_index = 50
	_cursor_count = UIKit.label("", 12, UIKit.TEXT)
	_cursor_count.position = Vector2(24, 24)
	_cursor_icon.add_child(_cursor_count)
	root.add_child(_cursor_icon)
	_cursor_icon.visible = false


static func _slot_label(slot: String) -> String:
	return {"head": "Head", "neck": "Neck", "arms": "Arms", "hands": "Hands", "ring1": "Ring", "ring2": "Ring",
			"chest": "Chest", "waist": "Waist", "legs": "Legs", "feet": "Feet", "primary": "Primary", "secondary": "Second", "range": "Range"}.get(slot, slot)


## An item slot: icon, stack count, a frame in the item's quality color.
## Left click moves via the cursor, shift-click is the quick action for the
## place, right-click opens the item window (or a bag).
func _make_slot(place: String, empty_text: String, size := 44) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(size, size)
	b.clip_text = true
	b.add_theme_font_size_override("font_size", 9)
	b.add_theme_color_override("font_color", Color(0.55, 0.55, 0.55))
	b.set_meta("empty_text", empty_text)
	var icon := TextureRect.new()
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icon.set_anchors_preset(Control.PRESET_FULL_RECT)
	icon.offset_left = 3
	icon.offset_top = 3
	icon.offset_right = -3
	icon.offset_bottom = -3
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(icon)
	var count := UIKit.label("", 11, UIKit.TEXT)
	count.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	count.offset_left = -22
	count.offset_top = -17
	count.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	count.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(count)
	b.gui_input.connect(func(ev: InputEvent) -> void:
		if not (ev is InputEventMouseButton and ev.pressed):
			return
		var mb := ev as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.ctrl_pressed or mb.meta_pressed:
				World.request_pick_one(player.entity_id, place)  # split a stack, one at a time
			elif mb.shift_pressed and player.cursor.is_empty():
				_quick_action(place)
			else:
				World.request_click(player.entity_id, place)
			b.accept_event()
		elif mb.button_index == MOUSE_BUTTON_RIGHT:
			var e := World._entry_at(player, place)
			if e.has("contents") and place.begins_with("g:"):
				_toggle_bag(int(place.get_slice(":", 1)))
			elif not e.is_empty():
				show_item(e["item"])
			b.accept_event())
	var quest := UIKit.label("!", 13, Color(1.0, 0.82, 0.3))  # a quest of yours wants this
	quest.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	quest.offset_left = -12
	quest.offset_top = -1
	quest.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	quest.add_theme_constant_override("outline_size", 4)
	quest.mouse_filter = Control.MOUSE_FILTER_IGNORE
	quest.visible = false
	b.add_child(quest)
	(_slot_buttons.get_or_add(place, []) as Array).append(b)
	return b


## The first live button showing a place (tests click it).
func _slot_button(place: String) -> Button:
	for b: Variant in _slot_buttons.get(place, []):
		if is_instance_valid(b) and not (b as Node).is_queued_for_deletion():
			return b
	return null


func _fill_slot(b: Button, e: Dictionary) -> void:
	var icon := b.get_child(0) as TextureRect
	var count := b.get_child(1) as Label
	var quest := b.get_child(2) as Label
	var wants := _quest_wants(str(e.get("item", "")))
	quest.visible = not wants.is_empty()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.1, 0.1, 0.12, 0.9)
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(3)
	if e.is_empty():
		icon.texture = null
		count.text = ""
		b.text = str(b.get_meta("empty_text", ""))
		b.tooltip_text = ""
		sb.border_color = Color(0.3, 0.3, 0.32)
	else:
		var id: String = e["item"]
		icon.texture = GameData.item_icon(id)
		b.text = "" if icon.texture != null else GameData.item_name(id)
		count.text = str(e["count"]) if int(e.get("count", 1)) > 1 else ""
		b.tooltip_text = _item_tooltip(id) + ("\nRight-click to open." if e.has("contents") else "\nRight-click for details.")
		for w: String in wants:
			b.tooltip_text += "\n" + w
		sb.border_color = GameData.item_color(id) if GameData.quality_tier(id).get("id", "") != "" else Color(0.55, 0.45, 0.25)
		if player.service == "shop" and _service_npc != null:
			var price := World.sell_price(_service_npc, id) * int(e.get("count", 1))
			b.tooltip_text += "\n%s" % ("Shift-click to sell for %s." % World.format_coin(price) if price > 0 else "The merchant won't buy this.")
	for state in ["normal", "hover", "pressed", "disabled"]:
		b.add_theme_stylebox_override(state, sb)


## Shift-click: sell with a shop open, bank with the bank open, offer in a
## trade, otherwise wear it (or take it off, from an equipment slot).
func _quick_action(place: String) -> void:
	var kind := place.get_slice(":", 0)
	var id := player.entity_id
	if kind == "e":
		World.request_unequip(id, place.get_slice(":", 1))
	elif kind == "k":
		World.request_bank_withdraw(id, int(place.get_slice(":", 1)))
	elif kind == "t":
		World.request_click(id, place)
	elif player.trade_npc_id >= 0:
		World.request_trade_add(id, place)
	elif player.service == "shop":
		World.request_sell(id, place)
	elif player.service == "bank":
		World.request_bank_deposit(id, place)
	else:
		World.request_equip(id, place)


## A bag's own window, its slots "b:<general slot>:<n>".
func _toggle_bag(g: int) -> void:
	if _bag_windows.has(g):
		(_bag_windows[g] as Node).queue_free()
		_bag_windows.erase(g)
		_layout_bags()
		return
	var e: Dictionary = player.pack.slots[g]
	var panel := UIKit.panel()
	root.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	panel.add_child(v)
	var head := HBoxContainer.new()
	var title := UIKit.label(GameData.item_name(e["item"]), 13, UIKit.GOLD)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(title)
	var close := UIKit.button("x", Vector2(24, 22))
	close.pressed.connect(func() -> void: _toggle_bag(g))
	head.add_child(close)
	v.add_child(head)
	var grid := GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation", 4)
	v.add_child(grid)
	for i in (e["contents"] as Array).size():
		grid.add_child(_make_slot("b:%d:%d" % [g, i], ""))
	panel.set_meta("bag_item", e["item"])
	_bag_windows[g] = panel
	_refresh_inventory()
	_layout_bags()


## B: opens every bag you carry, or closes them all if any are open.
func _toggle_all_bags() -> void:
	if not _bag_windows.is_empty():
		_close_all_bags()
		return
	for g in Pack.GENERAL:
		if (player.pack.slots[g] as Dictionary).has("contents"):
			_toggle_bag(g)


func _close_all_bags() -> void:
	for g: int in _bag_windows.keys():
		_toggle_bag(g)


## Open bags sit just left of the character window, their bottoms level with
## its bottom (by the General slots they came from), lined up leftward in slot
## order: close to the items, EQ style. With the window closed they keep to the
## same corner of the screen.
func _layout_bags() -> void:
	var edge := Vector2(root.size.x - 12.0, root.size.y - 160.0)
	if _bag_bar != null and _bag_bar.visible:
		edge = Vector2(_bag_bar.position.x + _bag_bar.size.x, _bag_bar.position.y - 6.0)
	if _inv_panel.visible:
		edge = Vector2(_inv_panel.position.x, _inv_panel.position.y + _inv_panel.size.y)
	var x := edge.x - 6.0
	var bottom := edge.y
	var row_height := 0.0
	var keys := _bag_windows.keys()
	keys.sort()
	for g: int in keys:
		var panel := _bag_windows[g] as Control
		if not is_instance_valid(panel) or panel.is_queued_for_deletion():
			continue
		panel.reset_size()
		var size := panel.get_combined_minimum_size()
		if x - size.x < 12.0 and row_height > 0.0:  # out of room: start a row above
			x = edge.x - 6.0
			bottom -= row_height + 6.0
			row_height = 0.0
		x -= size.x
		panel.position = Vector2(maxf(x, 12.0), maxf(bottom - size.y, 12.0))
		row_height = maxf(row_height, size.y)
		x -= 6.0


## The paper doll's character: rebuilt when what you wear changes.
func _refresh_doll() -> void:
	var key := JSON.stringify(player.look)
	if key == _doll_key or player.look.is_empty():
		return
	_doll_key = key
	for child in _doll_stage.get_children():
		child.queue_free()
	var model := Entity.make_visual(player.look)
	_doll_stage.add_child(model)
	if model is CharacterModel:
		var m := model as CharacterModel
		var idle := m._clip("idle")
		if idle != "":
			m.anim.play(idle)

## Controls sheet, hidden until the gear button in the top-right corner (or H) opens it.
func _build_help() -> void:
	var gear_button := UIKit.button("", Vector2(36, 36))
	gear_button.tooltip_text = "Controls (H)"
	for state in ["normal", "hover", "pressed"]:
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0.05, 0.05, 0.07, 0.82) if state == "normal" else Color(0.14, 0.12, 0.1, 0.9)
		sb.border_color = Color(0.55, 0.45, 0.25, 0.9)
		sb.set_border_width_all(1)
		sb.set_corner_radius_all(4)
		gear_button.add_theme_stylebox_override(state, sb)
	UIKit.place(gear_button, Vector2(1, 0), Vector2(-12, 12))
	var gear := Control.new()
	gear.set_anchors_preset(Control.PRESET_FULL_RECT)
	gear.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gear.draw.connect(func() -> void:
		var c := gear.size * 0.5
		for k in 8:
			var dir := Vector2.from_angle(k * TAU / 8.0)
			var side := dir.orthogonal()
			gear.draw_colored_polygon(PackedVector2Array([c + dir * 6.0 - side * 2.8, c + dir * 12.0 - side * 2.0,
					c + dir * 12.0 + side * 2.0, c + dir * 6.0 + side * 2.8]), UIKit.GOLD)
		gear.draw_circle(c, 8.5, UIKit.GOLD)
		gear.draw_circle(c, 3.5, Color(0.05, 0.05, 0.07)))
	gear_button.add_child(gear)
	gear_button.pressed.connect(func() -> void: _show_help(not _help_panel.visible))
	root.add_child(gear_button)

	_help_panel = UIKit.panel()
	UIKit.place(_help_panel, Vector2(1, 0), Vector2(-12, 56))
	_help_panel.visible = false
	root.add_child(_help_panel)
	var t := RichTextLabel.new()
	t.bbcode_enabled = true
	t.fit_content = true
	t.custom_minimum_size = Vector2(560, 0)
	t.add_theme_font_size_override("normal_font_size", 12)
	t.add_theme_font_size_override("bold_font_size", 12)
	t.text = HELP_TEXT
	_help_panel.add_child(t)


## Settings, reachable without a mouse: O opens it and each row toggles with the
## letter shown on it, so someone playing on the keyboard can turn the mouse
## scheme off without ever needing to click a button.
func _build_settings() -> void:
	_settings_panel = UIKit.panel()
	UIKit.place(_settings_panel, Vector2(0.5, 0.5), Vector2(0, 0))
	root.add_child(_settings_panel)
	var v := VBoxContainer.new()
	v.custom_minimum_size.x = 420
	v.add_theme_constant_override("separation", 6)
	_settings_panel.add_child(v)
	var title := UIKit.label("Settings", 18, UIKit.GOLD)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	_settings_rows = VBoxContainer.new()
	_settings_rows.add_theme_constant_override("separation", 4)
	v.add_child(_settings_rows)
	var hint := UIKit.label("Press the key shown to change a setting  ·  O or Esc to close", 11, UIKit.DIM)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(hint)
	_settings_panel.visible = false
	_refresh_settings()


func _refresh_settings() -> void:
	for c in _settings_rows.get_children():
		_settings_rows.remove_child(c)
		c.queue_free()
	var b := UIKit.button("[M]   Mouse controls:   %s" % ("On" if Controls.mouse_look else "Off"), Vector2(0, 34))
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.pressed.connect(_toggle_mouse_look)
	_settings_rows.add_child(b)
	var note := UIKit.label(
			"On: the mouse looks around, right-click targets, left-click attacks.\n"
			+ "Off: the cursor stays out, A/D turn, and you click to target.\n"
			+ "Either way, Tab targets the nearest foe and T cycles townsfolk and corpses.",
			11, UIKit.DIM)
	note.autowrap_mode = TextServer.AUTOWRAP_WORD
	note.custom_minimum_size.x = 410
	_settings_rows.add_child(note)
	_settings_rows.add_child(_music_row("[ ]   Music"))


## A music volume slider with its label: in Settings and the Esc menu.
func _music_row(caption: String) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var label := UIKit.label("%s:   %s" % [caption, _volume_text()], 14, UIKit.TEXT)
	label.custom_minimum_size.x = 150
	row.add_child(label)
	var slider := HSlider.new()
	slider.min_value = 0.0
	slider.max_value = 1.0
	slider.step = 0.05
	slider.value = Controls.music_volume
	slider.custom_minimum_size.x = 120
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slider.focus_mode = Control.FOCUS_NONE
	slider.value_changed.connect(func(v: float) -> void:
		Controls.set_music_volume(v)
		label.text = "%s:   %s" % [caption, _volume_text()])
	row.add_child(slider)
	return row


func _volume_text() -> String:
	return "Off" if Controls.music_volume <= 0.001 else "%d%%" % roundi(Controls.music_volume * 100)


func _toggle_mouse_look() -> void:
	Controls.set_mouse_look(not Controls.mouse_look)
	_refresh_settings()


func _show_settings(on: bool) -> void:
	_settings_panel.visible = on


## Esc menu: camp (log out), controls, back to the game.
func _build_menu() -> void:
	_menu_panel = UIKit.panel()
	UIKit.place(_menu_panel, Vector2(0.5, 0.5), Vector2(0, 0))
	root.add_child(_menu_panel)
	var v := VBoxContainer.new()
	v.custom_minimum_size.x = 240
	v.add_theme_constant_override("separation", 8)
	_menu_panel.add_child(v)
	var title := UIKit.label("Emberfall", 18, UIKit.GOLD)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	var music_slot := VBoxContainer.new()  # rebuilt on open, so it matches Settings
	v.add_child(music_slot)
	_menu_panel.visibility_changed.connect(func() -> void:
		if _menu_panel.visible:
			for c in music_slot.get_children():
				c.queue_free()
			music_slot.add_child(_music_row("Music")))
	var camp := UIKit.button("Camp  (log out)", Vector2(0, 38))
	camp.pressed.connect(func() -> void:
		_menu_panel.visible = false
		World.request_camp(player.entity_id))
	v.add_child(camp)
	var controls := UIKit.button("Controls", Vector2(0, 38))
	controls.pressed.connect(func() -> void:
		_menu_panel.visible = false
		_show_help(true))
	v.add_child(controls)
	var settings := UIKit.button("Settings  (O)", Vector2(0, 38))
	settings.pressed.connect(func() -> void:
		_menu_panel.visible = false
		_show_settings(true))
	v.add_child(settings)
	var reloader := get_tree().get_first_node_in_group("reloader")
	if reloader != null:  # dev builds only
		var reload := UIKit.button("Reload game  (F9)", Vector2(0, 38))
		reload.pressed.connect(func() -> void:
			_menu_panel.visible = false
			reloader.reload())
		v.add_child(reload)
	var resume := UIKit.button("Back to the game", Vector2(0, 38))
	resume.pressed.connect(func() -> void: _menu_panel.visible = false)
	v.add_child(resume)
	_menu_panel.visible = false


func _build_overlays() -> void:
	_banner = UIKit.label("", 30, UIKit.GOLD)
	_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	UIKit.place(_banner, Vector2(0.5, 0.22), Vector2.ZERO)
	root.add_child(_banner)
	_death_label = UIKit.label("You have died.", 44, Color(0.9, 0.2, 0.15))
	_death_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	UIKit.place(_death_label, Vector2(0.5, 0.4), Vector2.ZERO)
	_death_label.visible = false
	root.add_child(_death_label)

	_crosshair = Control.new()
	_crosshair.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_crosshair.set_anchors_preset(Control.PRESET_TOP_LEFT)  # positioned per frame from Player.aim_point()
	_crosshair.custom_minimum_size = Vector2(CROSSHAIR_SIZE, CROSSHAIR_SIZE)
	_crosshair.size = Vector2(CROSSHAIR_SIZE, CROSSHAIR_SIZE)
	_crosshair.draw.connect(_draw_crosshair)
	root.add_child(_crosshair)


## Crosshair, plus a ring that fills as the swing recharges while auto attacking.
## The delay is the rules' to set; showing it just makes the rhythm legible
## instead of looking like the game ignored the click.
##
## Everything is drawn twice, a dark outline under a bright core, because the
## reticle has to stay readable against both a sunlit sky and a dark treeline.
func _draw_crosshair() -> void:
	var c := _crosshair.size * 0.5
	for outline in [true, false]:
		var col: Color = CROSSHAIR_SHADOW if outline else CROSSHAIR_COLOR
		var w: float = 4.0 if outline else 2.0
		for d: Vector2 in [Vector2.LEFT, Vector2.RIGHT, Vector2.UP, Vector2.DOWN]:
			_crosshair.draw_line(c + d * 4.0, c + d * 11.0, col, w)
	_crosshair.draw_circle(c, 2.8, CROSSHAIR_SHADOW)
	_crosshair.draw_circle(c, 1.5, CROSSHAIR_COLOR)
	if player == null or not player.auto_attack:
		return
	var radius := CROSSHAIR_SIZE * 0.5 - 3.0
	_crosshair.draw_arc(c, radius, 0.0, TAU, 32, CROSSHAIR_SHADOW, 4.0)
	var delay := maxf(player.attack_delay, 0.01)
	var charge := clampf(1.0 - player.swing_timer / delay, 0.0, 1.0)
	var ready := charge >= 1.0
	_crosshair.draw_arc(c, radius, -PI * 0.5, -PI * 0.5 + TAU * charge, 32,
			Color(1, 0.5, 0.4) if ready else CROSSHAIR_COLOR, 2.5)


## True while any window the player clicks in is open, which frees the cursor.
func wants_cursor() -> bool:
	return (_inv_panel.visible or _service_panel.visible or _trade_panel.visible or _invite_panel.visible or _item_panel.visible or _skills_panel.visible
			or _loot_panel.visible or _help_panel.visible or _menu_panel.visible
			or _settings_panel.visible)


# --- updates ----------------------------------------------------------------

func _process(delta: float) -> void:
	_banner_time -= delta
	_banner.modulate.a = clampf(_banner_time, 0.0, 1.0)
	if player == null:
		_crosshair.visible = false
		return
	_crosshair.visible = player.mouse_looking
	if _crosshair.visible:
		_crosshair.position = player.aim_point() - _crosshair.size * 0.5
	# Redraw while the ring is advancing, plus once more after auto attack stops
	# so the last frame with a ring on it gets cleared.
	if _crosshair.visible and (player.auto_attack or _ring_drawn):
		_crosshair.queue_redraw()
	_ring_drawn = player.auto_attack
	_update_buffs()
	_layout_bag_bar()
	var cls_name: String = GameData.classes[player.char_class]["name"]
	_name_label.text = "%s   Level %d %s" % [player.display_name, player.level, cls_name]
	_hp_bar.max_value = player.max_hp
	_hp_bar.value = player.hp
	_hp_text.text = " %d / %d" % [maxi(player.hp, 0), player.max_hp]
	_mana_row.visible = player.max_mana > 0
	_mana_bar.max_value = player.max_mana
	_mana_bar.value = player.mana
	_mana_text.text = " %d / %d" % [player.mana, player.max_mana]
	_stamina_row.visible = player.max_stamina > 0
	_stamina_bar.max_value = player.max_stamina
	_stamina_bar.value = player.stamina
	_stamina_text.text = " %d / %d%s" % [int(player.stamina), player.max_stamina, "  running" if player.sprinting else ""]
	var pct := 100.0 * player.xp / player.xp_to_next()
	_xp_bar.value = pct
	_xp_text.text = " XP %.1f%%" % pct
	var buffs: PackedStringArray = []
	for spell_id: String in player.buffs:
		var left := int(player.buffs[spell_id]["left"])
		buffs.append("%s %d:%02d" % [GameData.spells[spell_id]["name"], left / 60, left % 60])
	_buff_label.text = "  ·  ".join(buffs)
	_buff_label.visible = not buffs.is_empty()
	_quest_panel.position.y = _player_panel.position.y + _player_panel.size.y + 8.0  # tracker hangs below, however tall
	_death_label.visible = player.dead

	_update_target()
	_update_cast()
	_update_hotbar()
	_update_group()
	if _item_panel.visible:
		_item_stage.rotate_y(delta * 0.8)
	_cursor_icon.visible = not player.cursor.is_empty()
	if _cursor_icon.visible:
		_cursor_icon.texture = GameData.item_icon(player.cursor["item"])
		_cursor_count.text = str(player.cursor["count"]) if int(player.cursor.get("count", 1)) > 1 else ""
		_cursor_icon.position = root.get_local_mouse_position() - Vector2(20, 20)
	if _skills_panel.visible:
		_skills_timer -= delta
		if _skills_timer <= 0.0:
			_skills_timer = 0.5
			_refresh_skills()
	if _inv_panel.visible:
		var lines: PackedStringArray = []
		for faction_id: String in GameData.factions:
			lines.append("%s:  %s" % [World.faction_name(faction_id), World.standing_tier(World.standing(player, faction_id))[1]])
		_faction_label.text = "\n".join(lines)
		var attr := PackedStringArray()
		for stat: String in Player.ATTRIBUTES:
			if int(player.attributes.get(stat, 0)) != 0:
				attr.append("%s %+d%s" % [ATTR_NAMES[stat], int(player.attributes[stat]), "%" if stat == "haste" else ""])
		var sheet := PackedStringArray([player.display_name, "Level %d %s" % [player.level, GameData.classes[player.char_class]["name"]]])
		if GameData.deities.has(player.deity):
			sheet.append("Follower of %s" % GameData.deities[player.deity]["name"])
		sheet.append_array(["", "HP  %d / %d" % [maxi(player.hp, 0), player.max_hp]])
		if player.max_mana > 0:
			sheet.append("Mana  %d / %d" % [player.mana, player.max_mana])
		sheet.append("Stamina  %d / %d" % [int(player.stamina), player.max_stamina])
		sheet.append_array(["", "AC  %d" % player.ac, "Damage  %d-%d" % [player.dmg_min, player.dmg_max], "Delay  %.1fs" % player.attack_delay])
		if player.off_delay > 0.0:
			sheet.append("Off hand  %d-%d, %.1fs" % [player.off_dmg_min, player.off_dmg_max, player.off_delay])
		sheet.append("")
		for stat: String in ["str", "sta", "agi", "wis", "int"]:
			sheet.append("%s  %+d" % [ATTR_NAMES[stat], int(player.attributes.get(stat, 0))])
		if int(player.attributes.get("haste", 0)) != 0:
			sheet.append("Haste  %d%%" % int(player.attributes["haste"]))
		_stats_label.text = "\n".join(sheet)


func _update_target() -> void:
	var t := player.target
	if not is_instance_valid(t):
		_target_panel.visible = false
		return
	_target_panel.visible = true
	if t is Entity:
		var e := t as Entity
		var color := Color(0.6, 0.8, 1.0)
		if e is Mob:
			color = World.CON_COLORS[World.con_of(player.level, e.level)]
		_target_name.text = e.display_name
		_target_name.add_theme_color_override("font_color", color)
		var pct := 100.0 * maxf(e.hp, 0) / e.max_hp
		_target_bar.value = pct
		_target_text.text = " %d%%" % int(ceil(pct))
		_attack_tag.visible = player.auto_attack
	elif t is Corpse:
		_target_name.text = (t as Corpse).display_name
		_target_name.add_theme_color_override("font_color", UIKit.DIM)
		_target_bar.value = 0
		_target_text.text = ""
		_attack_tag.visible = false


func _update_cast() -> void:
	_cast_panel.visible = not player.cast.is_empty() or player.camp_left > 0.0
	if not player.cast.is_empty():
		_cast_label.text = GameData.spells[player.cast["spell"]]["name"]
		_cast_bar.value = 100.0 * player.cast["time"] / player.cast["total"]
	elif player.camp_left > 0.0:
		var total := float(World.cfg("camp_seconds", 20.0))
		_cast_label.text = "Camping... %ds" % ceili(player.camp_left)
		_cast_bar.value = 100.0 * (1.0 - player.camp_left / total)


func _update_hotbar() -> void:
	var t := player.valid_target_entity()
	_attack_slot.show_state(0.0, 0.0, not player.dead, player.auto_attack)
	var weapon := GameData.item(str(player.equipment.get("range", "")))
	var can_fire := not weapon.is_empty() and t != null and World.can_attack(player, t) \
			and player.distance_to(t) <= float(weapon.get("range", 30.0)) and (not weapon.has("ammo") or _has_ammo(str(weapon["ammo"])))
	var ammo_kind := str(weapon.get("ammo", ""))
	var ammo_left := 0
	if ammo_kind != "":
		for e: Dictionary in player.pack.entries():
			if str(GameData.item(e["item"]).get("ammo_type", "")) == ammo_kind:
				ammo_left += int(e.get("count", 1))
	var ammo_text := str(ammo_left) if ammo_kind != "" else ""
	if ammo_text != _ranged_slot.count_text:
		_ranged_slot.count_text = ammo_text
		_ranged_slot.queue_redraw()
	var ranged_left := float(player.cooldowns.get("ranged", 0.0))
	_ranged_slot.show_state(_sweep("ranged", ranged_left), ranged_left, can_fire, false)
	_sit_slot.show_state(0.0, 0.0, not player.dead, player.sitting)
	for i in _spell_slots.size():
		var slot := _spell_slots[i]
		slot.visible = i < player.spells.size()
		if not slot.visible:
			continue
		var spell_id: String = player.spells[i]
		var s: Dictionary = GameData.spells[spell_id]
		if slot.get_meta("spell", "") != spell_id:
			slot.set_meta("spell", spell_id)
			slot.tooltip_text = spell_tooltip(spell_id)
			slot.picture = GameData.icon("spell_" + spell_id)
			slot.fallback = "".join(Array(str(s["name"]).split(" ")).map(func(w: String) -> String: return w.left(1)))
			slot.gem = HotSlot.GEMS[_gem_kind(s)]
			slot.queue_redraw()
		var cd := float(player.cooldowns.get(spell_id, 0.0))
		var on := (str(s["type"]) == "hide" and player.hidden) or (str(s["type"]) == "sneak" and player.sneaking)  # toggles glow while on
		slot.show_state(_sweep(spell_id, cd), cd, _spell_usable(s, t), on)


## What kind of gem a spell sits on: damage red, heals green, buffs blue,
## everything else (root, gate, taunt) violet, warrior abilities bronze.
static func _gem_kind(s: Dictionary) -> String:
	if s.get("ability", false):
		return "ability"
	match str(s.get("type", "")):
		"damage", "dot":
			return "damage"
		"heal":
			return "heal"
		"buff":
			return "buff"
	return "utility"


## A spell's gem lights up when it could be cast now: enough mana, not already
## casting, and (for a spell aimed at someone) a fitting target within range.
func _spell_usable(s: Dictionary, t: Entity) -> bool:
	if player.dead or player.mana < int(s.get("mana", 0)) or not player.cast.is_empty():
		return false
	if s.get("requires", "") == "shield" and not World.has_shield(player):
		return false
	var reach := float(s.get("range", 0.0))
	match str(s.get("target", "self")):
		"enemy":
			return t != null and World.can_attack(player, t) and (reach <= 0.0 or player.distance_to(t) <= reach)
		"friendly":
			return t == null or t == player or not (t is Player) or reach <= 0.0 or player.distance_to(t) <= reach
	return true


## How much of a cooldown is left, 0..1, measured against the longest wait seen
## since it was last ready (so it works for spells, the bow and anything else).
func _sweep(key: String, left: float) -> float:
	if left <= 0.0:
		_slot_totals.erase(key)
		return 0.0
	_slot_totals[key] = maxf(float(_slot_totals.get(key, 0.0)), left)
	return clampf(left / float(_slot_totals[key]), 0.0, 1.0)


func _has_ammo(kind: String) -> bool:
	for e: Dictionary in player.pack.entries():
		if str(GameData.item(e["item"]).get("ammo_type", "")) == kind:
			return true
	return false


## Appends a chat line. [Bracketed] words become gold links; clicking one says
## that keyword to your target, like typing it in EverQuest.
func add_log(text: String, color: Color) -> void:
	_log_lines = _write_line(_log, _log_lines, text, color)
	if color == World.C_CHAT_GROUP and _group_log != null:  # group chat also gets its own window
		_group_log_lines = _write_line(_group_log, _group_log_lines, text, color)


## Writes one line into a chat window, links and all; returns its new line count.
func _write_line(box: RichTextLabel, lines: int, text: String, color: Color) -> int:
	if lines > 0:
		box.newline()
	box.push_color(color)
	var at := 0
	var links := color == World.C_NPC  # only NPCs' [keywords] are clickable, never players' chat
	var marks: Array = []  # [start, end, kind, value]
	for m in (_keyword_re.search_all(text) if links else []):
		marks.append([m.get_start(), m.get_end(), "say", m.get_string(1)])
	for m in _item_link_re.search_all(text):  # linked items: {item:<id>}
		if GameData.items.has(GameData.base_item(m.get_string(1))):
			marks.append([m.get_start(), m.get_end(), "item", m.get_string(1)])
	marks.sort_custom(func(a: Array, b: Array) -> bool: return a[0] < b[0])
	for mk: Array in marks:
		if mk[0] < at:
			continue
		box.add_text(text.substr(at, mk[0] - at))
		if mk[2] == "item":
			box.push_meta("item:" + str(mk[3]))
			box.push_color(GameData.item_color(mk[3]))
			box.add_text("[%s]" % GameData.item_name(mk[3]))
		else:
			box.push_meta(mk[3])
			box.push_color(UIKit.GOLD)
			box.add_text(text.substr(mk[0], mk[1] - mk[0]))
		box.pop()
		box.pop()
		at = mk[1]
	box.add_text(text.substr(at))
	box.pop()
	lines += 1
	if lines > 300:
		box.remove_paragraph(0)
		lines -= 1
	return lines


# --- windows ------------------------------------------------------------------

func _on_log_keyword(meta: Variant) -> void:
	if str(meta).begins_with("item:"):
		show_item(str(meta).substr(5))
	elif player != null:
		World.request_say(player.entity_id, str(meta))


func _refresh_quests() -> void:
	var lines: PackedStringArray = []
	for quest_id: String in player.quests:
		if not player.quests[quest_id].get("active", false) or not GameData.quests.has(quest_id):
			continue
		var q: Dictionary = GameData.quests[quest_id]
		lines.append("[b][color=#%s]%s[/color][/b]" % [UIKit.GOLD.to_html(false), q["name"]])
		var have := World.quest_progress(player, quest_id)
		for item_id: String in q["wants"]:
			var need := int(q["wants"][item_id])
			var done := int(have[item_id]) >= need
			lines.append("[color=#%s]  %s  %d/%d[/color]" % ["8fe08f" if done else "d8d8d0", GameData.item_name(item_id), have[item_id], need])
		if World.quest_items_ready(player, quest_id):
			lines.append("[color=#8fe08f]  Trade them to %s (G)[/color]" % GameData.npcs[q["giver"]]["name"])
	_quest_label.text = "\n".join(lines)
	_quest_panel.visible = not lines.is_empty()


func _on_loot_opened(c: Corpse) -> void:
	_loot_corpse = c
	_loot_panel.visible = true
	_loot_title.text = c.display_name
	for child in _loot_list.get_children():
		child.queue_free()
	for i in c.entries.size():
		var entry: Dictionary = c.entries[i]
		var label := GameData.item_name(entry["item"])
		if int(entry.get("count", 1)) > 1:
			label += " x%d" % int(entry["count"])
		if str(entry.get("slot", "")) != "":
			label += "  (worn)"
		var b := UIKit.button(label)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.icon = GameData.item_icon(entry["item"])
		b.add_theme_constant_override("icon_max_width", 26)
		b.add_theme_color_override("font_color", GameData.item_color(entry["item"]))
		b.tooltip_text = _item_tooltip(entry["item"]) + "\nRight-click for details."
		_inspectable(b, entry["item"])
		b.pressed.connect(func() -> void: World.request_loot_item(player.entity_id, c.object_id, i))
		_loot_list.add_child(b)


func _on_loot_closed(c: Corpse) -> void:
	if c == null or c == _loot_corpse:
		_loot_panel.visible = false
		_loot_corpse = null


func _on_player_died(p: Player) -> void:
	if p == player:
		World.request_loot_close(player.entity_id)


func _show_help(on: bool) -> void:
	_help_panel.visible = on
	if on:
		_inv_panel.visible = false  # they share the right side of the screen


func _toggle_inventory() -> void:
	_inv_panel.visible = not _inv_panel.visible
	if _inv_panel.visible:
		_help_panel.visible = false  # they share the right side of the screen
	else:
		if not player.cursor.is_empty():
			World.request_stow_cursor(player.entity_id)  # closing with something held puts it away
		for g: int in _bag_windows.keys():
			_toggle_bag(g)
	_layout_bag_bar()
	_refresh_inventory()


func _refresh_inventory() -> void:
	_layout_bags.call_deferred()  # the character window may have changed size
	if player == null:
		return
	for place: String in _slot_buttons.keys():
		var live: Array = (_slot_buttons[place] as Array).filter(func(s: Variant) -> bool:
			return is_instance_valid(s) and not (s as Node).is_queued_for_deletion())  # a bag window closed
		if live.is_empty():
			_slot_buttons.erase(place)
			continue
		_slot_buttons[place] = live
		var e := World._entry_at(player, place)
		for slot: Button in live:
			_fill_slot(slot, e)
	_refresh_bag_bar()
	_notice_new_items()
	for g: int in _bag_windows.keys():  # a bag moved or emptied out of its slot closes its window
		var e: Dictionary = player.pack.slots[g]
		if e.get("item", "") != (_bag_windows[g] as Node).get_meta("bag_item"):
			_toggle_bag(g)
	if _inv_panel.visible:
		_refresh_doll()
	_coin_label.text = _coin_text(player.coin)
	var load := player.carried_weight()
	var limit := player.carry_capacity()
	_weight_label.text = "Weight  %.1f / %d" % [load, int(limit)]
	_weight_label.add_theme_color_override("font_color", Color(1, 0.5, 0.4) if load > limit else UIKit.TEXT)
	if _sell_cursor != null:
		_refresh_sell_cursor()


## With a shop open and an item on the cursor: "Sell <item> for <price>".
func _refresh_sell_cursor() -> void:
	var held := player.cursor
	_sell_cursor.visible = player.service == "shop" and _service_npc != null and not held.is_empty()
	if _sell_cursor.visible:
		var price := World.sell_price(_service_npc, held["item"]) * int(held.get("count", 1))
		_sell_cursor.text = "Sell %s for %s" % [GameData.item_name(held["item"]) + (" x%d" % int(held["count"]) if int(held.get("count", 1)) > 1 else ""),
				World.format_coin(price)] if price > 0 else "%s won't buy that" % _service_npc.display_name
		_sell_cursor.disabled = price <= 0


## EQ shows coin as four piles: platinum, gold, silver, copper.
static func _coin_text(copper: int) -> String:
	return "%d pp   %d gp   %d sp   %d cp" % [copper / 1000, (copper / 100) % 10, (copper / 10) % 10, copper % 10]



func spell_tooltip(spell_id: String) -> String:
	var s: Dictionary = GameData.spells.get(spell_id, {})
	var lines: PackedStringArray = [str(s.get("name", spell_id))]
	if s.has("desc"):
		lines.append(str(s["desc"]))
	var per := float(s.get("per_level", 0))
	match str(s.get("type", "")):
		"damage", "heal":
			lines.append("%s %d-%d%s" % ["Heals" if s["type"] == "heal" else "Damage", int(s["min"]), int(s["max"]), "  (+%.1f per level)" % per if per > 0 else ""])
		"dot":
			lines.append("%d damage every 3s, %d times" % [int(s["tick"]), int(s["ticks"])])
	var cost := "Mana %d" % int(s.get("mana", 0)) if int(s.get("mana", 0)) > 0 else "Ability"
	lines.append("%s   Cast %.1fs   Recast %.0fs" % [cost, float(s.get("cast_time", 0)), float(s.get("recast", 0))])
	return "\n".join(lines)


func _item_tooltip(item_id: String, colored := false) -> String:
	var it: Dictionary = GameData.item(item_id)
	var lines: PackedStringArray = [str(it.get("name", item_id))]
	var flags := PackedStringArray()
	if it.get("lore", false):
		flags.append("LORE ITEM")
	if it.get("no_drop", false):
		flags.append("NO DROP")
	if not flags.is_empty():
		lines.append("  ".join(flags))
	var wt := "Weight %.1f" % GameData.item_weight(item_id)
	if float(it.get("weight_reduction", 0.0)) > 0.0:
		wt += "   Lightens what's inside by %d%%" % roundi(float(it["weight_reduction"]) * 100.0)
	lines.append(wt)
	if it.has("slot"):
		lines.append("Slot: %s" % str(it["slot"]).capitalize())
	if it.has("dmg") and it.has("delay"):
		lines.append("Damage %d   Delay %.1fs" % [int(it["dmg"]), float(it["delay"])])
		if World.offhand_weapon(item_id):
			lines.append("One-handed: can be wielded in the off hand (Dual Wield)")
	elif it.has("ammo_type"):
		lines.append("Ammunition (%s)%s" % [it["ammo_type"], "   Damage +%d" % int(it["dmg"]) if int(it.get("dmg", 0)) > 0 else ""])
	if it.has("range"):
		lines.append("Range %dm   Skill: %s%s" % [int(it["range"]), GameData.skill_name(str(it.get("skill", ""))), "   Uses %s" % it["ammo_name"] if it.has("ammo_name") else ""])
	if it.has("ac"):
		lines.append("AC %d" % int(it["ac"]))
	if it.has("hp"):
		lines.append("HP +%d" % int(it["hp"]))
	if it.has("mana"):
		lines.append("Mana +%d" % int(it["mana"]))
	var attr := PackedStringArray()
	for stat: String in Player.ATTRIBUTES:
		if int(it.get(stat, 0)) != 0:
			attr.append("%s %+d%s" % [ATTR_NAMES[stat], int(it[stat]), "%" if stat == "haste" else ""])
	if not attr.is_empty():
		lines.append("   ".join(attr))
	var proc: Dictionary = it.get("proc", {})
	if not proc.is_empty():
		lines.append("Effect: %s  (%d%% on hit)" % [GameData.spells[proc["spell"]]["name"], roundi(float(proc["chance"]) * 100)])
	var click: Dictionary = it.get("click", {})
	if not click.is_empty():
		lines.append("Click effect: %s  (recharges in %ds)" % [GameData.spells[click["spell"]]["name"], int(click.get("recast", 60))])
	var classes: Array = it.get("classes", [])
	if not classes.is_empty():
		lines.append("Class: %s" % " ".join(classes.map(func(c: String) -> String: return str(GameData.classes[c]["name"]))))
	var deities: Array = it.get("deities", [])
	if not deities.is_empty():
		lines.append("Deity: %s" % " ".join(deities.map(func(d: String) -> String: return str(GameData.deities[d]["name"]))))
	if it.has("rec_level"):
		var weak := player != null and player.level < int(it["rec_level"])
		lines.append("Recommended level: %d%s" % [int(it["rec_level"]), "  (weaker until then)" if weak else ""])
	if player != null and it.has("slot"):
		var why := World.equip_block(player, item_id)
		if why != "":
			lines.append(why)
	if int(it.get("value", 0)) > 0:
		lines.append("Value: %s" % World.format_coin(int(it["value"])))
	lines.append_array(_compare_lines(item_id, colored))
	return "\n".join(lines)


## "Compared to your Cloth Cap: AC +1, STA -1" for gear not being worn.
const COMPARE_STATS := ["dmg", "delay", "ac", "hp", "mana", "str", "sta", "agi", "wis", "int", "haste", "hp_regen", "mana_regen"]


## An item against what you wear in its slot: [what it's compared with,
## [[change text, better?], ...]], or [] when there's nothing to compare (not
## wearable, or it's what you're wearing). Rings compare with an empty ring
## slot if you have one, else your first ring.
func _comparison(item_id: String) -> Array:
	var it := GameData.item(item_id)
	var slot := str(it.get("slot", ""))
	if slot == "" or player == null or item_id in player.equipment.values():
		return []
	var slots: Array = World.SLOT_FITS.get(slot, [slot])
	var worn_id := ""
	for sl: String in slots:
		if not player.equipment.has(sl):
			worn_id = ""
			break
		if worn_id == "":
			worn_id = str(player.equipment[sl])
	var worn := GameData.item(worn_id) if worn_id != "" else {}
	var rows: Array = []
	for stat: String in COMPARE_STATS:
		var a := float(it.get(stat, 0))
		var b := float(worn.get(stat, 0))
		if stat == "delay" and (a == 0.0 or b == 0.0):
			continue  # delay only means something weapon to weapon
		var d := a - b
		if absf(d) < 0.001:
			continue
		var text := "Delay %+.1fs" % d if stat == "delay" else "%s %+d%s" % [ATTR_NAMES.get(stat, stat.to_upper()), roundi(d), "%" if stat == "haste" else ""]
		rows.append([text, d < 0.0 if stat == "delay" else d > 0.0])  # a shorter delay swings faster
	var what := "your " + str(worn["name"]) if worn_id != "" else "an empty %s slot" % _slot_label(str(slots[0])).to_lower()
	return [what, rows]


## The comparison as tooltip lines (plain) or item-window text (gains green,
## losses red).
func _compare_lines(item_id: String, colored := false) -> PackedStringArray:
	var c := _comparison(item_id)
	if c.is_empty():
		return PackedStringArray()
	var parts := PackedStringArray()
	for row: Array in c[1]:
		parts.append(("[color=#%s]%s[/color]" % ["8fe08f" if row[1] else "f07a6a", row[0]]) if colored else str(row[0]))
	var head := ("[color=#%s]Compared to %s:[/color]" % [UIKit.GOLD.to_html(false), c[0]]) if colored else "Compared to %s:" % c[0]
	return PackedStringArray(["", head, "  " + ("   ".join(parts) if not parts.is_empty() else "no change")])


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var key := (event as InputEventKey).keycode
		if key == KEY_ENTER or key == KEY_KP_ENTER or key == KEY_SLASH:
			_open_chat("/" if key == KEY_SLASH else "")
			get_viewport().set_input_as_handled()
			return
	if event.is_action_pressed("inventory"):
		_toggle_inventory()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("bags"):
		_toggle_all_bags()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("skills"):
		_toggle_skills()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("help"):
		_show_help(not _help_panel.visible)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("settings"):
		_show_settings(not _settings_panel.visible)
		get_viewport().set_input_as_handled()
	elif _settings_panel.visible and event.is_action_pressed("settings_mouse_look"):
		_toggle_mouse_look()
		get_viewport().set_input_as_handled()
	elif _settings_panel.visible and (event.is_action_pressed("settings_music_down", true) or event.is_action_pressed("settings_music_up", true)):
		Controls.set_music_volume(Controls.music_volume + (0.05 if event.is_action("settings_music_up") else -0.05))
		_refresh_settings()
		get_viewport().set_input_as_handled()
	elif _loot_panel.visible and event.is_action_pressed("loot") and _loot_corpse != null:
		# Second press takes the lot, so looting never needs the mouse.
		World.request_loot_all(player.entity_id, _loot_corpse.object_id)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("cancel"):
		if _skills_panel.visible:
			_skills_panel.visible = false
			get_viewport().set_input_as_handled()
		elif _item_panel.visible:
			_item_panel.visible = false
			get_viewport().set_input_as_handled()
		elif _settings_panel.visible:
			_settings_panel.visible = false
			get_viewport().set_input_as_handled()
		elif _service_panel.visible:
			World.request_service_close(player.entity_id)
			get_viewport().set_input_as_handled()
		elif _trade_panel.visible:
			World.request_trade_cancel(player.entity_id)
			get_viewport().set_input_as_handled()
		elif _loot_panel.visible:
			World.request_loot_close(player.entity_id)
			get_viewport().set_input_as_handled()
		elif _inv_panel.visible:
			_toggle_inventory()  # its bags close with it
			get_viewport().set_input_as_handled()
		elif not _bag_windows.is_empty():
			_close_all_bags()
			get_viewport().set_input_as_handled()
		elif _menu_panel.visible:
			_menu_panel.visible = false
			get_viewport().set_input_as_handled()
		elif player != null and player.cast.is_empty() and not is_instance_valid(player.target):
			_menu_panel.visible = true  # nothing else to cancel: open the menu
			get_viewport().set_input_as_handled()
