class_name Hud
extends CanvasLayer
## In-game interface: player and target windows, cast bar, hotbar, chat log,
## loot and inventory windows. Reads state from the player; every action goes
## through World.request_*, the same as keyboard input.

const HELP_TEXT := """[b]Movement[/b]   W/S forward/back · A/D turn (strafe while holding right mouse) · Space jump
[b]Camera[/b]   Right-drag to look · Wheel to zoom (all the way in = first person)
[b]Targeting[/b]   Left-click · Tab nearest enemy · F1 self · Esc clear / interrupt cast
[b]Combat[/b]   Q auto attack · 1-8 abilities & spells (learn more from your guildmaster) · C consider (con colors!)
[b]Resting[/b]   X sit / stand. Sitting regenerates much faster; moving stands you up.
[b]Loot[/b]   L or double-click a corpse · I inventory (click to equip / unequip)
[b]Talk[/b]   E or double-click to hail · click gold words in replies to ask about them
[b]Trade[/b]   G with an NPC targeted: merchants open their shop, bankers your bank, anyone else a give window (quest turn-ins)
[b]Logging out[/b]   Esc with nothing open → Camp. Sit tight for 20 seconds and you're saved to the character screen.
[b]Dying[/b]   You respawn at the obelisk without your gear. Run back and loot your corpse.
H or the gear button to hide this."""

var player: Player
var root: Control

var _player_panel: PanelContainer
var _name_label: Label
var _hp_bar: ProgressBar
var _hp_text: Label
var _mana_row: Control
var _mana_bar: ProgressBar
var _mana_text: Label
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
var _equip_box: VBoxContainer
var _bag_grid: GridContainer
var _coin_label: Label
var _stats_label: Label
var _faction_label: Label

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
	_build_service_window()
	_build_inventory()
	_build_help()
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


func _build_hotbar() -> void:
	var p := UIKit.panel()
	UIKit.place(p, Vector2(1, 1), Vector2(-12, -12))
	root.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	p.add_child(v)
	var spells_grid := GridContainer.new()
	spells_grid.columns = 4
	spells_grid.add_theme_constant_override("h_separation", 6)
	spells_grid.add_theme_constant_override("v_separation", 6)
	v.add_child(spells_grid)
	var size := Vector2(128, 40)
	for i in 8:
		var b := UIKit.button("", size)
		b.clip_text = true
		b.pressed.connect(func() -> void:
			if i < player.spells.size():
				World.request_cast(player.entity_id, player.spells[i]))
		b.visible = false
		spells_grid.add_child(b)
		_spell_buttons.append(b)
	var actions := GridContainer.new()
	actions.columns = 4
	actions.add_theme_constant_override("h_separation", 6)
	v.add_child(actions)
	_attack_button = UIKit.button("Q  Attack", size)
	_attack_button.pressed.connect(func() -> void: World.request_toggle_attack(player.entity_id))
	actions.add_child(_attack_button)
	_sit_button = UIKit.button("X  Sit", size)
	_sit_button.pressed.connect(func() -> void: World.request_sit(player.entity_id, not player.sitting))
	actions.add_child(_sit_button)
	var con := UIKit.button("C  Consider", size)
	con.pressed.connect(func() -> void: World.request_consider(player.entity_id))
	actions.add_child(con)
	var bags := UIKit.button("I  Inventory", size)
	bags.pressed.connect(_toggle_inventory)
	actions.add_child(bags)


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
	var hints := {"shop": "Click an item to buy it. Click items in your bags to sell them.",
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
			b.tooltip_text = _item_tooltip(item_id)
			b.disabled = player.coin < int(ware["price"])
			b.pressed.connect(func() -> void: World.request_buy(player.entity_id, item_id))
			_shop_list.add_child(b)
	else:
		for child in _bank_grid.get_children():
			child.queue_free()
		for i in int(World.cfg("bank_slots", 16)):
			var b := UIKit.button("", Vector2(78, 34))
			b.clip_text = true
			b.add_theme_font_size_override("font_size", 10)
			if i < player.bank_items.size():
				b.text = GameData.item_name(player.bank_items[i])
				b.tooltip_text = _item_tooltip(player.bank_items[i]) + "\nClick to withdraw."
				b.pressed.connect(func() -> void: World.request_bank_withdraw(player.entity_id, i))
			else:
				b.disabled = true
			_bank_grid.add_child(b)
		_bank_coin_label.text = "In the bank: %s" % World.format_coin(player.bank_coin)


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
	v.add_child(UIKit.label("Faction", 13, UIKit.GOLD))
	_faction_label = UIKit.label("", 12, UIKit.DIM)
	v.add_child(_faction_label)
	_inv_panel.visible = false


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
	var reloader := get_tree().get_first_node_in_group("reloader")
	if reloader != null:  # dev builds only
		var reload := UIKit.button("Reload game  (F5)", Vector2(0, 38))
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
	if _inv_panel.visible:
		var lines: PackedStringArray = []
		if GameData.deities.has(player.deity):
			var d: Dictionary = GameData.deities[player.deity]
			lines.append("Follower of %s, %s" % [d["name"], d["title"]])
		for faction_id: String in GameData.factions:
			lines.append("%s:  %s" % [World.faction_name(faction_id), World.standing_tier(World.standing(player, faction_id))[1]])
		_faction_label.text = "\n".join(lines)
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
	_attack_button.text = "Q  Attacking" if player.auto_attack else "Q  Attack"
	_attack_button.modulate = Color(1, 0.35, 0.3) if player.auto_attack else Color.WHITE
	_sit_button.text = "X  Stand" if player.sitting else "X  Sit"
	for i in _spell_buttons.size():
		var btn := _spell_buttons[i]
		btn.visible = i < player.spells.size()
		if not btn.visible:
			continue
		var spell_id: String = player.spells[i]
		var s: Dictionary = GameData.spells[spell_id]
		if btn.get_meta("spell", "") != spell_id:
			btn.set_meta("spell", spell_id)
			btn.tooltip_text = spell_tooltip(spell_id)
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
		b.add_theme_color_override("font_color", GameData.item_color(entry["item"]))
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


func _show_help(on: bool) -> void:
	_help_panel.visible = on
	if on:
		_inv_panel.visible = false  # they share the right side of the screen


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
			b.add_theme_color_override("font_color", GameData.item_color(item_id))
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
			b.add_theme_color_override("font_color", GameData.item_color(item_id))
			b.tooltip_text = _item_tooltip(item_id)
			if player.service == "shop" and _service_npc != null:
				var price := World.sell_price(_service_npc, item_id)
				b.tooltip_text += "\n%s" % ("Sells for %s." % World.format_coin(price) if price > 0 else "The merchant won't buy this.")
			b.pressed.connect(func() -> void:
				if player.trade_npc_id >= 0:
					World.request_trade_add(player.entity_id, i)
				elif player.service == "shop":
					World.request_sell(player.entity_id, i)
				elif player.service == "bank":
					World.request_bank_deposit(player.entity_id, i)
				else:
					World.request_equip(player.entity_id, i))
		else:
			b.disabled = true
		_bag_grid.add_child(b)
	_coin_label.text = World.format_coin(player.coin)
	var action := "equip it"
	if player.trade_npc_id >= 0:
		action = "offer it"
	elif player.service == "shop":
		action = "sell it"
	elif player.service == "bank":
		action = "bank it"
	_bag_hint.text = "Bags  (click an item to %s)" % action


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


func _item_tooltip(item_id: String) -> String:
	var it: Dictionary = GameData.item(item_id)
	var lines: PackedStringArray = [str(it.get("name", item_id))]
	if it.has("slot"):
		lines.append("Slot: %s" % str(it["slot"]).capitalize())
	if it.has("dmg"):
		lines.append("Damage %d   Delay %.1fs" % [int(it["dmg"]), float(it["delay"])])
	if it.has("ac"):
		lines.append("AC %d" % int(it["ac"]))
	if it.has("hp"):
		lines.append("HP +%d" % int(it["hp"]))
	if int(it.get("value", 0)) > 0:
		lines.append("Value: %s" % World.format_coin(int(it["value"])))
	return "\n".join(lines)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("inventory"):
		_toggle_inventory()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("help"):
		_show_help(not _help_panel.visible)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("cancel"):
		if _service_panel.visible:
			World.request_service_close(player.entity_id)
			get_viewport().set_input_as_handled()
		elif _trade_panel.visible:
			World.request_trade_cancel(player.entity_id)
			get_viewport().set_input_as_handled()
		elif _loot_panel.visible:
			World.request_loot_close(player.entity_id)
			get_viewport().set_input_as_handled()
		elif _inv_panel.visible:
			_inv_panel.visible = false
			get_viewport().set_input_as_handled()
		elif _menu_panel.visible:
			_menu_panel.visible = false
			get_viewport().set_input_as_handled()
		elif player != null and player.cast.is_empty() and not is_instance_valid(player.target):
			_menu_panel.visible = true  # nothing else to cancel: open the menu
			get_viewport().set_input_as_handled()
