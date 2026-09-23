class_name Hud
extends CanvasLayer
## In-game interface: player and target windows, cast bar, hotbar, chat log,
## loot and inventory windows. Reads state from the player; every action goes
## through World.request_*, the same as keyboard input.

const HELP_TEXT := """[b]Movement[/b]   W/S forward/back · A/D turn (strafe while holding right mouse) · Space jump
[b]Camera[/b]   Right-drag to look · Wheel to zoom (all the way in = first person)
[b]Targeting[/b]   Left-click · Tab nearest enemy · F1 self · Esc clear / interrupt cast
[b]Combat[/b]   Q auto attack · 1-4 abilities & spells · C consider (con colors!)
[b]Resting[/b]   X sit / stand. Sitting regenerates much faster; moving stands you up.
[b]Loot[/b]   L or double-click a corpse · I inventory (click to equip / unequip)
[b]Talk[/b]   E or double-click to hail · click gold words in replies to ask about them
[b]Trade[/b]   G to trade with your target · click bag items to offer them (quest turn-ins)
[b]Dying[/b]   You respawn at the obelisk without your gear. Run back and loot your corpse.
H to hide this."""

var player: Player
var root: Control

var _name_label: Label
var _hp_bar: ProgressBar
var _hp_text: Label
var _mana_row: Control
var _mana_bar: ProgressBar
var _mana_text: Label
var _xp_bar: ProgressBar
var _xp_text: Label

var _target_panel: PanelContainer
var _target_name: Label
var _target_bar: ProgressBar
var _target_text: Label

var _cast_panel: PanelContainer
var _cast_bar: ProgressBar
var _cast_label: Label

var _attack_button: Button
var _sit_button: Button
var _spell_buttons: Array[Button] = []

var _log: RichTextLabel
var _log_lines := 0
var _keyword_re := RegEx.create_from_string("\\[([^\\]]+)\\]")

var _trade_panel: PanelContainer
var _trade_title: Label
var _trade_slots: Array[Button] = []
var _bag_hint: Label

var _quest_panel: PanelContainer
var _quest_label: RichTextLabel

var _loot_panel: PanelContainer
var _loot_title: Label
var _loot_list: VBoxContainer
var _loot_corpse: Corpse

var _inv_panel: PanelContainer
var _equip_box: VBoxContainer
var _bag_grid: GridContainer
var _coin_label: Label
var _stats_label: Label

var _help_panel: PanelContainer
var _banner: Label
var _banner_time := 0.0
var _death_label: Label


func _ready() -> void:
	layer = 10
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	_build_player_window()
	_build_target_window()
	_build_cast_bar()
	_build_hotbar()
	_build_log()
	_build_quest_tracker()
	_build_loot_window()
	_build_trade_window()
	_build_inventory()
	_build_help()
	_build_overlays()
	World.log_message.connect(add_log)
	World.loot_opened.connect(_on_loot_opened)
	World.loot_changed.connect(_on_loot_opened)
	World.loot_closed.connect(_on_loot_closed)
	World.player_died.connect(_on_player_died)
	World.trade_opened.connect(_on_trade_opened)
	World.trade_changed.connect(_refresh_trade)
	World.trade_closed.connect(func() -> void: _trade_panel.visible = false; _refresh_inventory())


func bind_player(p: Player) -> void:
	player = p
	player.inventory_changed.connect(_refresh_inventory)
	player.inventory_changed.connect(_refresh_quests)
	player.quests_changed.connect(_refresh_quests)
	for i in _spell_buttons.size():
		var btn := _spell_buttons[i]
		btn.visible = i < player.spells.size()
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
	var xp := _bar_row(Color(0.85, 0.7, 0.25), 7.0)
	_xp_bar = xp[0]
	_xp_text = xp[1]
	v.add_child(xp[2])


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


func _build_hotbar() -> void:
	var p := UIKit.panel()
	UIKit.place(p, Vector2(1, 1), Vector2(-12, -12))
	root.add_child(p)
	var h := GridContainer.new()
	h.columns = 4
	h.add_theme_constant_override("h_separation", 6)
	h.add_theme_constant_override("v_separation", 6)
	p.add_child(h)
	var size := Vector2(128, 40)
	_attack_button = UIKit.button("Q  Attack", size)
	_attack_button.pressed.connect(func() -> void: World.request_toggle_attack(player.entity_id))
	h.add_child(_attack_button)
	for i in 4:
		var b := UIKit.button("", size)
		b.pressed.connect(func() -> void:
			if i < player.spells.size():
				World.request_cast(player.entity_id, player.spells[i]))
		h.add_child(b)
		_spell_buttons.append(b)
	_sit_button = UIKit.button("X  Sit", size)
	_sit_button.pressed.connect(func() -> void: World.request_sit(player.entity_id, not player.sitting))
	h.add_child(_sit_button)
	var con := UIKit.button("C  Consider", size)
	con.pressed.connect(func() -> void: World.request_consider(player.entity_id))
	h.add_child(con)
	var bags := UIKit.button("I  Inventory", size)
	bags.pressed.connect(_toggle_inventory)
	h.add_child(bags)


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
	p.add_child(_log)


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
	v.add_child(UIKit.label("Click items in your bags to offer them.", 12, UIKit.DIM))
	var grid := GridContainer.new()
	grid.columns = 2
	v.add_child(grid)
	for i in World.TRADE_SLOTS:
		var b := UIKit.button("", Vector2(126, 34))
		b.clip_text = true
		b.add_theme_font_size_override("font_size", 11)
		b.pressed.connect(func() -> void: World.request_trade_remove(player.entity_id, i))
		grid.add_child(b)
		_trade_slots.append(b)
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


func _on_trade_opened(npc: Npc) -> void:
	_trade_title.text = "Trading with %s" % npc.display_name
	_trade_panel.visible = true
	_inv_panel.visible = true
	_help_panel.visible = false
	_refresh_inventory()
	_refresh_trade()


func _refresh_trade() -> void:
	for i in _trade_slots.size():
		var b := _trade_slots[i]
		var has := i < player.trade_items.size()
		b.text = GameData.item_name(player.trade_items[i]) if has else "—"
		b.disabled = not has
		b.tooltip_text = "Click to take it back." if has else ""


func _build_inventory() -> void:
	_inv_panel = UIKit.panel()
	UIKit.place(_inv_panel, Vector2(1, 0.5), Vector2(-12, -40))
	root.add_child(_inv_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	_inv_panel.add_child(v)
	v.add_child(UIKit.label("Inventory", 16, UIKit.GOLD))
	_stats_label = UIKit.label("", 12, UIKit.DIM)
	v.add_child(_stats_label)
	_equip_box = VBoxContainer.new()
	v.add_child(_equip_box)
	_bag_hint = UIKit.label("", 12, UIKit.DIM)
	v.add_child(_bag_hint)
	_bag_grid = GridContainer.new()
	_bag_grid.columns = 4
	v.add_child(_bag_grid)
	_coin_label = UIKit.label("", 13, UIKit.GOLD)
	v.add_child(_coin_label)
	_inv_panel.visible = false


func _build_help() -> void:
	_help_panel = UIKit.panel()
	UIKit.place(_help_panel, Vector2(1, 0), Vector2(-12, 12))
	root.add_child(_help_panel)
	var t := RichTextLabel.new()
	t.bbcode_enabled = true
	t.fit_content = true
	t.custom_minimum_size = Vector2(560, 0)
	t.add_theme_font_size_override("normal_font_size", 12)
	t.add_theme_font_size_override("bold_font_size", 12)
	t.text = HELP_TEXT
	_help_panel.add_child(t)


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


# --- updates ----------------------------------------------------------------

func _process(delta: float) -> void:
	_banner_time -= delta
	_banner.modulate.a = clampf(_banner_time, 0.0, 1.0)
	if player == null:
		return
	var cls_name: String = GameData.classes[player.char_class]["name"]
	_name_label.text = "%s   Level %d %s" % [player.display_name, player.level, cls_name]
	_hp_bar.max_value = player.max_hp
	_hp_bar.value = player.hp
	_hp_text.text = " %d / %d" % [maxi(player.hp, 0), player.max_hp]
	_mana_row.visible = player.max_mana > 0
	_mana_bar.max_value = player.max_mana
	_mana_bar.value = player.mana
	_mana_text.text = " %d / %d" % [player.mana, player.max_mana]
	var pct := 100.0 * player.xp / player.xp_to_next()
	_xp_bar.value = pct
	_xp_text.text = " XP %.1f%%" % pct
	_death_label.visible = player.dead

	_update_target()
	_update_cast()
	_update_hotbar()
	if _inv_panel.visible:
		_stats_label.text = "AC %d   Damage %d-%d   Delay %.1fs" % [player.ac, player.dmg_min, player.dmg_max, player.attack_delay]


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
	elif t is Corpse:
		_target_name.text = (t as Corpse).display_name
		_target_name.add_theme_color_override("font_color", UIKit.DIM)
		_target_bar.value = 0
		_target_text.text = ""


func _update_cast() -> void:
	_cast_panel.visible = not player.cast.is_empty()
	if _cast_panel.visible:
		_cast_label.text = GameData.spells[player.cast["spell"]]["name"]
		_cast_bar.value = 100.0 * player.cast["time"] / player.cast["total"]


func _update_hotbar() -> void:
	_attack_button.modulate = Color(1, 0.45, 0.4) if player.auto_attack else Color.WHITE
	_sit_button.text = "X  Stand" if player.sitting else "X  Sit"
	for i in mini(_spell_buttons.size(), player.spells.size()):
		var spell_id: String = player.spells[i]
		var s: Dictionary = GameData.spells[spell_id]
		var btn := _spell_buttons[i]
		btn.visible = true
		var cd: float = player.cooldowns.get(spell_id, 0.0)
		btn.text = "%d  %s" % [i + 1, s["name"]] if cd <= 0.0 else "%d  %.1f" % [i + 1, cd]
		btn.disabled = cd > 0.0 or player.mana < int(s.get("mana", 0))


## Appends a chat line. [Bracketed] words become gold links; clicking one says
## that keyword to your target, like typing it in EverQuest.
func add_log(text: String, color: Color) -> void:
	if _log_lines > 0:
		_log.newline()
	_log.push_color(color)
	var at := 0
	for m in _keyword_re.search_all(text):
		_log.add_text(text.substr(at, m.get_start() - at))
		_log.push_meta(m.get_string(1))
		_log.push_color(UIKit.GOLD)
		_log.add_text(m.get_string())
		_log.pop()
		_log.pop()
		at = m.get_end()
	_log.add_text(text.substr(at))
	_log.pop()
	_log_lines += 1
	if _log_lines > 300:
		_log.remove_paragraph(0)
		_log_lines -= 1


# --- windows ------------------------------------------------------------------

func _on_log_keyword(meta: Variant) -> void:
	if player != null:
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
		if str(entry.get("slot", "")) != "":
			label += "  (worn)"
		var b := UIKit.button(label)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.tooltip_text = _item_tooltip(entry["item"])
		b.pressed.connect(func() -> void: World.request_loot_item(player.entity_id, c.object_id, i))
		_loot_list.add_child(b)


func _on_loot_closed(c: Corpse) -> void:
	if c == null or c == _loot_corpse:
		_loot_panel.visible = false
		_loot_corpse = null


func _on_player_died(p: Player) -> void:
	if p == player:
		World.request_loot_close(player.entity_id)


func _toggle_inventory() -> void:
	_inv_panel.visible = not _inv_panel.visible
	if _inv_panel.visible:
		_help_panel.visible = false  # they share the right side of the screen
	_refresh_inventory()


func _refresh_inventory() -> void:
	if player == null:
		return
	for child in _equip_box.get_children():
		child.queue_free()
	for slot in World.EQUIP_SLOTS:
		var item_id: String = player.equipment.get(slot, "")
		var text := "%s:  %s" % [slot.capitalize(), GameData.item_name(item_id) if item_id != "" else "—"]
		var b := UIKit.button(text)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.disabled = item_id == ""
		if item_id != "":
			b.tooltip_text = _item_tooltip(item_id) + "\nClick to unequip."
			b.pressed.connect(func() -> void: World.request_unequip(player.entity_id, slot))
		_equip_box.add_child(b)
	for child in _bag_grid.get_children():
		child.queue_free()
	var slots := int(World.cfg("inventory_slots", 24))
	for i in slots:
		var b := UIKit.button("", Vector2(112, 34))
		b.clip_text = true
		b.add_theme_font_size_override("font_size", 11)
		if i < player.inventory.size():
			var item_id: String = player.inventory[i]
			b.text = GameData.item_name(item_id)
			b.tooltip_text = _item_tooltip(item_id)
			b.pressed.connect(func() -> void:
				if player.trade_npc_id >= 0:
					World.request_trade_add(player.entity_id, i)
				else:
					World.request_equip(player.entity_id, i))
		else:
			b.disabled = true
		_bag_grid.add_child(b)
	_coin_label.text = World.format_coin(player.coin)
	_bag_hint.text = "Bags  (click an item to %s)" % ("offer it" if player.trade_npc_id >= 0 else "equip it")


func _item_tooltip(item_id: String) -> String:
	var it: Dictionary = GameData.items.get(item_id, {})
	var lines: PackedStringArray = [str(it.get("name", item_id))]
	if it.has("slot"):
		lines.append("Slot: %s" % str(it["slot"]).capitalize())
	if it.has("dmg"):
		lines.append("Damage %d   Delay %.1fs" % [int(it["dmg"]), float(it["delay"])])
	if it.has("ac"):
		lines.append("AC %d" % int(it["ac"]))
	if it.has("hp"):
		lines.append("HP +%d" % int(it["hp"]))
	if not it.has("slot"):
		lines.append("(Trade goods — vendors will want these later.)")
	return "\n".join(lines)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("inventory"):
		_toggle_inventory()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("help"):
		_help_panel.visible = not _help_panel.visible
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("cancel"):
		if _trade_panel.visible:
			World.request_trade_cancel(player.entity_id)
			get_viewport().set_input_as_handled()
		elif _loot_panel.visible:
			World.request_loot_close(player.entity_id)
			get_viewport().set_input_as_handled()
		elif _inv_panel.visible:
			_inv_panel.visible = false
			get_viewport().set_input_as_handled()
