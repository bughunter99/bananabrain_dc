#include "ai_dc.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <iomanip>
#include <sstream>

namespace {
	ai_dc* g_active_bot = nullptr;
	bool g_manual_mode = false;
	bool g_python_mode = false;

	std::unique_ptr<Strategy> create_strategy_for_race(Race race)
	{
		switch (race) {
		case Races::Protoss:
			return std::make_unique<ProtossStrategy>();
		case Races::Terran:
			return std::make_unique<TerranStrategy>();
		case Races::Zerg:
			return std::make_unique<ZergStrategy>();
		default:
			return nullptr;
		}
	}

	std::string escape_log_value(const std::string& value)
	{
		std::string escaped;
		escaped.reserve(value.size());
		for (char ch : value) {
			switch (ch) {
			case '\\':
				escaped += "\\\\";
				break;
			case '"':
				escaped += "\\\"";
				break;
			case '\r':
				escaped += "\\r";
				break;
			case '\n':
				escaped += "\\n";
				break;
			default:
				escaped += ch;
				break;
			}
		}
		return escaped;
	}

	std::string timestamp_now(const char* format)
	{
		std::time_t current_time = std::time(nullptr);
		std::tm local_time = {};
		localtime_s(&local_time, &current_time);
		std::ostringstream output;
		output << std::put_time(&local_time, format);
		return output.str();
	}

	std::string player_name(Player player)
	{
		return player ? player->getName() : "Unknown";
	}

	std::string position_string(Position position)
	{
		if (position.x < 0 || position.y < 0) {
			return "none";
		}
		return std::to_string(position.x) + "," + std::to_string(position.y);
	}

	bool is_visible_combat_unit(Unit unit)
	{
		if (unit == nullptr || !unit->exists()) return false;
		if (unit->getType().isWorker() || unit->getType().isBuilding()) return false;
		if (unit->isConstructing()) return false;
		return true;
	}

	std::string summarize_top_unit_counts(const std::map<std::string, int>& counts, size_t limit = 3)
	{
		std::vector<std::pair<std::string, int>> items(counts.begin(), counts.end());
		std::sort(items.begin(), items.end(), [](const auto& left, const auto& right) {
			if (left.second != right.second) return left.second > right.second;
			return left.first < right.first;
		});
		std::string summary;
		for (size_t i = 0; i < items.size() && i < limit; ++i) {
			if (i) summary += ", ";
			summary += items[i].first + " " + std::to_string(items[i].second);
		}
		return summary;
	}

	void append_arg(std::vector<std::pair<std::string,std::string>>& args,
					const std::string& key,
					const std::string& value)
	{
		args.emplace_back(key, value);
	}

	std::pair<std::string,std::string> arg(const char* key, const std::string& value)
	{
		return std::make_pair(std::string(key), value);
	}
}

void ai_dc::open_log()
{
	if (log_stream_.is_open()) return;

	char module_path[MAX_PATH] = {};
	DWORD path_length = GetModuleFileNameA(nullptr, module_path, MAX_PATH);
	if (path_length == 0 || path_length == MAX_PATH) return;

	std::string executable_path(module_path, path_length);
	std::string::size_type separator = executable_path.find_last_of("\\/");
	std::string directory = (separator == std::string::npos) ? std::string() : executable_path.substr(0, separator + 1);
	log_path_ = directory + "ai_dc" + timestamp_now("%Y%m%d%H");
	log_stream_.open(log_path_, std::ios::out | std::ios::app);
	if (log_stream_.is_open()) {
		log_event("LogOpened", {arg("path", log_path_)}, "none");
	}
}

void ai_dc::close_log()
{
	if (!log_stream_.is_open()) return;
	log_event("LogClosed", {arg("path", log_path_)}, "none");
	log_stream_.close();
	last_unit_commands_.clear();
}

void ai_dc::log_event(const std::string& event_name,
						std::initializer_list<std::pair<std::string,std::string>> args,
						const std::string& action)
{
	log_event(event_name, std::vector<std::pair<std::string,std::string>>(args), action);
}

void ai_dc::log_event(const std::string& event_name,
						const std::vector<std::pair<std::string,std::string>>& args,
						const std::string& action)
{
	if (!log_stream_.is_open()) return;

	log_stream_ << timestamp_now("%Y-%m-%d %H:%M:%S")
				 << " | event=" << event_name
				 << " | args={";

	bool first = true;
	for (const auto& arg : args) {
		if (!first) log_stream_ << ", ";
		first = false;
		log_stream_ << arg.first << "=\"" << escape_log_value(arg.second) << "\"";
	}

	log_stream_ << "} | action=\"" << escape_log_value(action) << "\"" << std::endl;
	log_stream_.flush();
}

std::vector<std::pair<std::string,std::string>> ai_dc::base_unit_args(Unit unit) const
{
	std::vector<std::pair<std::string,std::string>> args;
	append_arg(args, "frame", std::to_string(Broodwar->getFrameCount()));
	if (!unit) return args;

	append_arg(args, "unit_id", std::to_string(unit->getID()));
	append_arg(args, "unit_type", unit->getType().getName());
	append_arg(args, "player", player_name(unit->getPlayer()));
	append_arg(args, "position", position_string(unit->getPosition()));
	return args;
}

std::string ai_dc::describe_command(const UnitCommand& command) const
{
	std::ostringstream description;
	description << command.getType().getName();

	Unit target = command.getTarget();
	if (target != nullptr) {
		description << " target_unit=" << target->getID() << ":" << target->getType().getName();
	} else {
		Position target_position = command.getTargetPosition();
		if (target_position.x >= 0 && target_position.y >= 0) {
			description << " target_pos=" << position_string(target_position);
		}
	}

	return description.str();
}

std::string ai_dc::current_action_for(Unit unit) const
{
	if (unit == nullptr || Broodwar->self() == nullptr) return "none";
	if (unit->getPlayer() != Broodwar->self()) return "none";
	return describe_command(unit->getLastCommand());
}

void ai_dc::log_unit_event(const std::string& event_name,
							 Unit unit,
							 const std::vector<std::pair<std::string,std::string>>& extra_args)
{
	auto args = base_unit_args(unit);
	args.insert(args.end(), extra_args.begin(), extra_args.end());
	log_event(event_name, args, current_action_for(unit));
}

void ai_dc::emit_battle_judgement()
{
	if (BroodwarPtr == nullptr || Broodwar->self() == nullptr || strategy_ == nullptr) return;

	int own_army = 0;
	int enemy_army = 0;
	int enemy_near_home = 0;
	int own_workers = 0;
	int own_bases = 0;
	int own_completed_tech = 0;
	int enemy_air = 0;
	std::map<std::string, int> own_composition;
	std::map<std::string, int> enemy_composition;
	Position home_position = Position(Broodwar->self()->getStartLocation());
	for (auto unit : Broodwar->self()->getUnits()) {
		if (is_visible_combat_unit(unit)) {
			own_army++;
			own_composition[unit->getType().getName()]++;
		}
		if (unit != nullptr && unit->exists() && unit->getType().isWorker()) own_workers++;
		if (unit != nullptr && unit->exists() && unit->getType().isResourceDepot() && unit->isCompleted()) own_bases++;
		if (unit != nullptr && unit->exists() && unit->isCompleted() && !unit->getType().isWorker() && !unit->getType().isBuilding()) {
			own_completed_tech++;
		}
	}
	for (auto& enemy_player : Broodwar->enemies()) {
		for (auto enemy_unit : enemy_player->getUnits()) {
			if (!is_visible_combat_unit(enemy_unit) || !enemy_unit->isVisible()) continue;
			enemy_army++;
			enemy_composition[enemy_unit->getType().getName()]++;
			if (enemy_unit->getType().isFlyer()) enemy_air++;
			if (home_position.isValid() && enemy_unit->getDistance(home_position) <= 384) {
				enemy_near_home++;
			}
		}
	}

	std::string judgement;
	std::string level = "info";
	std::vector<std::string> tags;
	auto add_tag = [&](const std::string& tag) {
		if (std::find(tags.begin(), tags.end(), tag) == tags.end()) tags.push_back(tag);
	};
	if (enemy_army == 0) {
		judgement = "적이 가시 범위에 없어서 정찰/확인이 우선";
		add_tag("scout_needed");
	} else if (enemy_near_home > 0 && own_army + 2 < enemy_army) {
		judgement = "적이 본진 근처에 접근했고 병력도 밀려서 후퇴/수비 필요";
		level = "warn";
		add_tag("enemy_pressure");
		add_tag("retreat_needed");
		add_tag("home_threat");
		add_tag("rush_alert");
	} else if (enemy_army > own_army + 2) {
		judgement = "적 병력이 더 많아서 방어 비중을 높여야 함";
		level = "warn";
		add_tag("army_deficit");
		add_tag("defend_more");
		add_tag("fallback_defense");
	} else if (own_army >= enemy_army + 3) {
		judgement = "병력 우위라 공격 전환이 가능함";
		level = "ok";
		add_tag("attack_window");
		add_tag("army_advantage");
		add_tag("counter_attack_window");
	} else if (enemy_near_home > 0) {
		judgement = "적 병력이 본진 근처에 보여 경계가 필요";
		level = "warn";
		add_tag("enemy_pressure");
		add_tag("home_threat");
		add_tag("vision_check");
	} else {
		judgement = "병력 균형 상태라 자원/테크 진행을 유지";
		add_tag("macro_continue");
	}
	if (own_workers < 8) add_tag("worker_shortage");
	else if (own_workers < 12) add_tag("eco_greedy_ok");
	if (own_workers >= 14 && own_bases == 1 && enemy_army == 0) add_tag("expand_window");
	if (own_bases >= 2 && enemy_near_home == 0 && enemy_army > 0) add_tag("expand_safe");
	if (own_completed_tech < enemy_air && enemy_air > 0) add_tag("air_threat");
	if (own_completed_tech > enemy_army + 4) add_tag("tech_lead");
	if (own_completed_tech + 2 < enemy_army) add_tag("tech_deficit");
	if (Broodwar->self()->minerals() < 150) add_tag("low_minerals");
	if (Broodwar->self()->gas() < 100) add_tag("low_gas");
	if (Broodwar->self()->supplyUsed() + 4 >= Broodwar->self()->supplyTotal()) add_tag("supply_block_risk");
	if (Broodwar->self()->minerals() >= 400 && own_workers < 24) add_tag("worker_production_prioritized");
	if (Broodwar->self()->minerals() >= 400 && own_bases == 1 && enemy_near_home == 0) add_tag("expand_affordable");
	if (enemy_near_home > 0 && own_army == 0) add_tag("base_defenseless");
	if (enemy_air > 0 && own_completed_tech == 0) add_tag("no_anti_air_info");

	std::string tag_text;
	for (size_t i = 0; i < tags.size(); ++i) {
		if (i) tag_text += ",";
		tag_text += tags[i];
	}
	std::string own_summary = summarize_top_unit_counts(own_composition);
	std::string enemy_summary = summarize_top_unit_counts(enemy_composition);

	std::string signature = level + "|" + judgement + "|" + tag_text + "|" + own_summary + "|" + enemy_summary + "|" + std::to_string(own_army) + "|" + std::to_string(enemy_army) + "|" + std::to_string(enemy_near_home);
	if (signature == last_battle_judgement_) return;
	last_battle_judgement_ = signature;

	log_event("BattleJudgement", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("level", level),
		arg("message", judgement),
		arg("tags", tag_text),
		arg("own_summary", own_summary),
		arg("enemy_summary", enemy_summary),
		arg("own_army", std::to_string(own_army)),
		arg("enemy_army", std::to_string(enemy_army)),
		arg("enemy_near_home", std::to_string(enemy_near_home)),
		arg("own_workers", std::to_string(own_workers)),
		arg("own_bases", std::to_string(own_bases)),
		arg("own_tech", std::to_string(own_completed_tech)),
		arg("enemy_air", std::to_string(enemy_air)),
		arg("mode", strategy_->mode()),
		arg("opening", strategy_->opening())
	}, "none");
	python_bridge.send_event("battle_judgement", {
		{"level", level},
		{"message", judgement},
		{"tags", tag_text},
		{"own_summary", own_summary},
		{"enemy_summary", enemy_summary},
		{"own_army", std::to_string(own_army)},
		{"enemy_army", std::to_string(enemy_army)},
		{"enemy_near_home", std::to_string(enemy_near_home)},
		{"own_workers", std::to_string(own_workers)},
		{"own_bases", std::to_string(own_bases)},
		{"own_tech", std::to_string(own_completed_tech)},
		{"enemy_air", std::to_string(enemy_air)},
		{"mode", strategy_->mode()},
		{"opening", strategy_->opening()}
	});
}

void ai_dc::log_recent_unit_commands()
{
	if (Broodwar->self() == nullptr) return;

	std::set<int> active_unit_ids;
	const int current_frame = Broodwar->getFrameCount();
	const int latency = Broodwar->getRemainingLatencyFrames();

	for (auto& unit : Broodwar->self()->getUnits()) {
		if (unit == nullptr) continue;

		const int unit_id = unit->getID();
		active_unit_ids.insert(unit_id);

		UnitCommand command = unit->getLastCommand();
		CommandSnapshot snapshot;
		snapshot.frame = unit->getLastCommandFrame();
		snapshot.signature = describe_command(command);

		auto previous = last_unit_commands_.find(unit_id);
		const bool changed = (previous == last_unit_commands_.end() ||
							 previous->second.frame != snapshot.frame ||
							 previous->second.signature != snapshot.signature);

		if (changed && snapshot.frame + latency >= current_frame) {
			auto args = base_unit_args(unit);
			append_arg(args, "command_frame", std::to_string(snapshot.frame));
			log_event("UnitCommand", args, snapshot.signature);
		}

		last_unit_commands_[unit_id] = snapshot;
	}

	for (auto it = last_unit_commands_.begin(); it != last_unit_commands_.end();) {
		if (active_unit_ids.count(it->first) == 0) {
			it = last_unit_commands_.erase(it);
		} else {
			++it;
		}
	}
}

void ai_dc::onStart()
{
	g_active_bot = this;
	open_log();
	log_event("onStart", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("self_race", Broodwar->self() ? Broodwar->self()->getRace().getName() : "Unknown"),
		arg("enemy_count", std::to_string((int)Broodwar->enemies().size())),
		arg("is_replay", Broodwar->isReplay() ? "true" : "false")
	}, "none");

	python_bridge.start();

	// Build rich onStart payload (mineral fields, geysers, own starting units, start tile)
	{
		auto esc = [](const std::string& s) { return MsgBusBridge::escape_json(s); };

		// Mineral fields
		std::string minerals_json = "[";
		bool first = true;
		for (auto m : Broodwar->getMinerals()) {
			if (!first) minerals_json += ",";
			first = false;
			minerals_json += "{\"id\":" + std::to_string(m->getID()) +
			                 ",\"x\":" + std::to_string(m->getPosition().x) +
			                 ",\"y\":" + std::to_string(m->getPosition().y) +
			                 ",\"res\":" + std::to_string(m->getResources()) + "}";
		}
		minerals_json += "]";

		// Vespene geysers
		std::string geysers_json = "[";
		first = true;
		for (auto g : Broodwar->getGeysers()) {
			if (!first) geysers_json += ",";
			first = false;
			geysers_json += "{\"id\":" + std::to_string(g->getID()) +
			                ",\"x\":" + std::to_string(g->getPosition().x) +
			                ",\"y\":" + std::to_string(g->getPosition().y) + "}";
		}
		geysers_json += "]";

		// Own starting units
		std::string start_units_json = "[";
		first = true;
		if (Broodwar->self()) {
			for (auto u : Broodwar->self()->getUnits()) {
				if (!first) start_units_json += ",";
				first = false;
				start_units_json += "{\"id\":" + std::to_string(u->getID()) +
				                    ",\"type\":\"" + esc(u->getType().getName()) + "\"" +
				                    ",\"x\":" + std::to_string(u->getPosition().x) +
				                    ",\"y\":" + std::to_string(u->getPosition().y) + "}";
			}
		}
		start_units_json += "]";

		// Start tile (TilePosition * 32 = pixel position of tile top-left)
		TilePosition start_tile = Broodwar->self() ? Broodwar->self()->getStartLocation() : TilePositions::Invalid;
		std::string stx = std::to_string(start_tile.isValid() ? start_tile.x : -1);
		std::string sty = std::to_string(start_tile.isValid() ? start_tile.y : -1);

		// Enemy candidate start locations (for Python scouting/attack targeting)
		std::string enemy_starts_json = "[";
		first = true;
		for (const TilePosition& loc : Broodwar->getStartLocations()) {
			if (start_tile.isValid() && loc == start_tile) continue;
			if (!first) enemy_starts_json += ",";
			first = false;
			enemy_starts_json += "{\"tile_x\":" + std::to_string(loc.x) +
			                    ",\"tile_y\":" + std::to_string(loc.y) + "}";
		}
		enemy_starts_json += "]";

		std::string self_race = Broodwar->self() ? Broodwar->self()->getRace().getName() : "Unknown";
		int enemy_count = (int)Broodwar->enemies().size();

		std::string payload = "{\"self_race\":\"" + esc(self_race) + "\"" +
		                      ",\"enemy_count\":" + std::to_string(enemy_count) +
		                      ",\"is_replay\":" + (Broodwar->isReplay() ? "true" : "false") +
		                      ",\"map_width_tiles\":" + std::to_string(Broodwar->mapWidth()) +
		                      ",\"map_height_tiles\":" + std::to_string(Broodwar->mapHeight()) +
		                      ",\"start_tile_x\":" + stx +
		                      ",\"start_tile_y\":" + sty +
		                      ",\"enemy_start_locations\":" + enemy_starts_json +
		                      ",\"mineral_fields\":" + minerals_json +
		                      ",\"geysers\":" + geysers_json +
		                      ",\"units\":" + start_units_json + "}";

		python_bridge.send_raw_event("onStart", payload);
	}

	// Enable the UserInput flag, which allows us to control the bot and type messages.
	Broodwar->enableFlag(Flag::UserInput);
 
	if (!Broodwar->isReplay())
	{
		bool ok = true;
		
		switch (Broodwar->self()->getRace()) {
			case Races::Protoss:
				strategy_.reset(new ProtossStrategy());
				break;
			case Races::Terran:
				strategy_.reset(new TerranStrategy());
				break;
			case Races::Zerg:
				strategy_.reset(new ZergStrategy());
				break;
			default:
				Broodwar->sendText("Error: This bot only plays Protoss or Terran or Zerg");
				ok = false;
				break;
		}
		
		is_1v1_ = (Broodwar->enemies().size() == 1 && Broodwar->allies().size() == 0);
		
		if (!is_1v1_) {
			if (Broodwar->getGameType() == GameTypes::Free_For_All ||
				Broodwar->getGameType() == GameTypes::Team_Free_For_All) {
				is_ffa_ = true;
			} else {
				int computer_opponents = 0;
				for (auto& enemy : Broodwar->enemies()) {
					if (enemy->getType() == PlayerTypes::Computer) {
						computer_opponents++;
					}
				}
				if (computer_opponents < 2) {
					is_ffa_ = true;
				}
			}
		}
		
		if (ok) {
			configuration.init();
			srand(static_cast<unsigned int>(time(nullptr)));
			bwem_map.Initialize(BroodwarPtr);
			bwem_map.FindBasesForStartingLocations();
			bwem_map.EnableAutomaticPathAnalysis();
			base_state.init_bases();
			path_finder.init();
			opponent_model.init();
			building_placement_manager.init();
			spending_manager.init_resource_counters();
			if (is_1v1_) result_store.init();
			strategy_->pick_strategy(is_1v1_);
			walkability_grid.init();
			room_grid.init();
			worker_manager.init_optimal_mining_data();
			tactics_manager.set_is_ffa(is_ffa_);
			initialized_ = true;
			g_manual_mode = true;   // start paused: wait for UI command
			g_python_mode = false;  // reset python mode on new game
			log_event("onStart_initialized", {
				arg("frame", std::to_string(Broodwar->getFrameCount())),
				arg("is_1v1", is_1v1_ ? "true" : "false"),
				arg("is_ffa", is_ffa_ ? "true" : "false"),
				arg("opening", strategy_ ? strategy_->opening() : "")
			}, "none");
			python_bridge.send_event("onStart_initialized", {
				{"is_1v1", is_1v1_ ? "true" : "false"},
				{"is_ffa", is_ffa_ ? "true" : "false"},
				{"opening", strategy_ ? strategy_->opening() : ""}
			});
			python_bridge.send_event("manual_mode_changed", {
				{"manual_mode", "true"}
			});
		}
	}
}

void ai_dc::onEnd(bool winner)
{
	if (g_active_bot == this) g_active_bot = nullptr;
	set_manual_mode(false);  // sends manual_mode_changed event so Python state stays in sync

	log_event("onEnd", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("winner", winner ? "true" : "false")
	}, "none");

	python_bridge.send_event("onEnd", {
		{"winner", winner ? "true" : "false"},
		{"frame", std::to_string(Broodwar->getFrameCount())}
	});

	if (initialized_) {
		if (is_1v1_) {
			strategy_->apply_result(winner);
			result_store.store();
		}
		worker_manager.store_optimal_mining_data();
	}

	python_bridge.stop();
	close_log();
}

bool ai_dc::force_opening(const std::string& opening)
{
	if (!initialized_ || BroodwarPtr == nullptr || Broodwar->self() == nullptr) return false;

	auto new_strategy = create_strategy_for_race(Broodwar->self()->getRace());
	if (!new_strategy || !new_strategy->force_opening(opening)) return false;

	strategy_ = std::move(new_strategy);
	log_event("onStrategyChanged", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("opening", strategy_->opening()),
		arg("mode", strategy_->mode())
	}, "none");
	python_bridge.send_event("onStrategyChanged", {
		{"opening", strategy_->opening()},
		{"mode", strategy_->mode()}
	});
	return true;
}

bool force_strategy_opening(const std::string& opening)
{
	return g_active_bot != nullptr && g_active_bot->force_opening(opening);
}

void set_manual_mode(bool manual)
{
	g_manual_mode = manual;
	if (BroodwarPtr != nullptr && Broodwar->self() != nullptr) {
		python_bridge.send_event("manual_mode_changed", {
			{"manual_mode", manual ? "true" : "false"}
		});
	}
}

bool is_manual_mode()
{
	return g_manual_mode;
}

void set_python_mode(bool python_mode)
{
	g_python_mode = python_mode;
	if (BroodwarPtr != nullptr && Broodwar->self() != nullptr) {
		python_bridge.send_event("python_mode_changed", {
			{"python_mode", python_mode ? "true" : "false"}
		});
	}
}

bool is_python_mode()
{
	return g_python_mode;
}

void gather_workers_minerals()
{
	if (BroodwarPtr == nullptr || Broodwar->self() == nullptr) return;
	for (Unit u : Broodwar->self()->getUnits()) {
		if (!u->exists() || !u->getType().isWorker()) continue;
		// Skip workers that are already busy: constructing, moving to build,
		// carrying resources back, or already gathering — only redirect truly idle ones.
		if (!u->isIdle()) continue;
		// Find nearest mineral with resources remaining
		Unit best = nullptr;
		int best_dist = INT_MAX;
		for (Unit m : Broodwar->getMinerals()) {
			if (!m->exists() || m->getResources() <= 0) continue;
			int d = u->getDistance(m);
			if (d < best_dist) { best_dist = d; best = m; }
		}
		if (best) u->gather(best);
	}
}

void scout_with_worker()
{
	if (BroodwarPtr == nullptr || Broodwar->self() == nullptr) return;
	// Pick the first idle or mineral-gathering worker
	Unit scout = nullptr;
	for (Unit u : Broodwar->self()->getUnits()) {
		if (!u->exists() || !u->getType().isWorker()) continue;
		scout = u;
		if (u->isIdle()) break; // prefer idle worker
	}
	if (!scout) return;
	// Find a start location that is not ours to scout
	TilePosition home = Broodwar->self()->getStartLocation();
	for (const TilePosition& loc : Broodwar->getStartLocations()) {
		if (loc == home) continue;
		scout->move(Position(loc));
		return;
	}
}

void block_entrance_with_workers()
{
	if (BroodwarPtr == nullptr || Broodwar->self() == nullptr) return;
	auto& bwem = BWEM::Map::Instance();
	TilePosition home = Broodwar->self()->getStartLocation();
	// Find the BWEM area containing home base
	const BWEM::Area* home_area = bwem.GetNearestArea(home);
	if (!home_area) return;
	// Find the widest chokepoint bordering the home area
	const BWEM::ChokePoint* best_cp = nullptr;
	int best_width = -1;
	for (const BWEM::Area* adj : home_area->AccessibleNeighbours()) {
		for (const BWEM::ChokePoint& cp : home_area->ChokePoints(adj)) {
			if (cp.Blocked()) continue;
			int w = (int)cp.Geometry().size();
			if (w > best_width) { best_width = w; best_cp = &cp; }
		}
	}
	if (!best_cp) return;
	Position choke_pos(best_cp->Center());
	// Send up to 3 workers to block
	int sent = 0;
	for (Unit u : Broodwar->self()->getUnits()) {
		if (!u->exists() || !u->getType().isWorker()) continue;
		u->move(choke_pos);
		if (++sent >= 3) break;
	}
}

void ai_dc::onFrame()
{
	if (!initialized_) return;
	if (Broodwar->isPaused() || !Broodwar->self()) return;
	if (configuration.human_opponent() && Broodwar->getFrameCount() == 240) Broodwar->sendText("glhf");

	python_bridge.poll_actions();

	// python_mode: 6프레임마다, 일반: 24프레임마다 상태 전송
	const int frame_interval = g_python_mode ? 6 : 24;
	if ((Broodwar->getFrameCount() % frame_interval) == 0) {
		auto esc = [](const std::string& s) { return MsgBusBridge::escape_json(s); };

		// 자신의 유닛 목록 (건물 포함)
		std::string units_json = "[";
		bool first = true;
		for (auto u : Broodwar->self()->getUnits()) {
			if (!first) units_json += ",";
			first = false;

			// 건물이 훈련 중인 유닛 타입
			std::string training_type_json = "null";
			if (u->isTraining() && !u->getTrainingQueue().empty()) {
				training_type_json = "\"" + esc(u->getTrainingQueue().front().getName()) + "\"";
			}
			// 일꾼이 건설 중인 건물 타입
			std::string build_type_json = "null";
			if (u->getBuildType() != UnitTypes::None) {
				build_type_json = "\"" + esc(u->getBuildType().getName()) + "\"";
			}

			units_json += "{\"id\":" + std::to_string(u->getID()) +
			              ",\"type\":\"" + esc(u->getType().getName()) + "\"" +
			              ",\"x\":" + std::to_string(u->getPosition().x) +
			              ",\"y\":" + std::to_string(u->getPosition().y) +
			              ",\"hp\":" + std::to_string(u->getHitPoints()) +
			              ",\"shields\":" + std::to_string(u->getShields()) +
			              ",\"idle\":" + (u->isIdle() ? "true" : "false") +
			              ",\"constructing\":" + (u->isConstructing() ? "true" : "false") +
			              ",\"carrying\":" + ((u->isCarryingMinerals() || u->isCarryingGas()) ? "true" : "false") +
			              ",\"completed\":" + (u->isCompleted() ? "true" : "false") +
			              ",\"training\":" + (u->isTraining() ? "true" : "false") +
			              ",\"is_worker\":" + (u->getType().isWorker() ? "true" : "false") +
			              ",\"is_building\":" + (u->getType().isBuilding() ? "true" : "false") +
			              ",\"training_type\":" + training_type_json +
			              ",\"build_type\":" + build_type_json +
			              "}";
		}
		units_json += "]";

		// 자신의 시작 위치 (타일)
		TilePosition start_tile = Broodwar->self()->getStartLocation();
		int stx = start_tile.isValid() ? start_tile.x : -1;
		int sty = start_tile.isValid() ? start_tile.y : -1;

		std::string frame_payload =
			"{\"minerals\":" + std::to_string(Broodwar->self()->minerals()) +
			",\"gas\":" + std::to_string(Broodwar->self()->gas()) +
			",\"supply_used\":" + std::to_string(Broodwar->self()->supplyUsed()) +
			",\"supply_total\":" + std::to_string(Broodwar->self()->supplyTotal()) +
			",\"mode\":\"" + esc(strategy_ ? strategy_->mode() : "") + "\"" +
			",\"python_mode\":" + (g_python_mode ? "true" : "false") +
			",\"start_tile_x\":" + std::to_string(stx) +
			",\"start_tile_y\":" + std::to_string(sty) +
			",\"own_units\":" + units_json;

		// python_mode 일 때 적 유닛(가시 범위 내) 추가
		if (g_python_mode) {
			std::string enemy_json = "[";
			bool efirst = true;
			for (auto& ep : Broodwar->enemies()) {
				for (auto eu : ep->getUnits()) {
					if (!eu->exists() || !eu->isVisible()) continue;
					if (!efirst) enemy_json += ",";
					efirst = false;
					enemy_json += "{\"id\":" + std::to_string(eu->getID()) +
					              ",\"type\":\"" + esc(eu->getType().getName()) + "\"" +
					              ",\"x\":" + std::to_string(eu->getPosition().x) +
					              ",\"y\":" + std::to_string(eu->getPosition().y) +
					              ",\"hp\":" + std::to_string(eu->getHitPoints()) + "}";
				}
			}
			enemy_json += "]";
			frame_payload += ",\"enemy_units\":" + enemy_json;
		}

		frame_payload += "}";
		python_bridge.send_raw_event("onFrame", frame_payload);
	}
	
	PerformanceTimer performance_timer;
	
	before();
	// Python command-only mode: never run C++ autonomous strategy while python mode is active.
	if (!g_manual_mode && !g_python_mode) {
		strategy_->frame();
		after();
		surrender_if_hope_lost();
		emit_battle_judgement();
	}
	log_recent_unit_commands();
	
	if (configuration.draw_enabled()) {
		draw();
		int duration = performance_timer.duration();
		if (Broodwar->getFrameCount() == 0) {
			frame_zero_duration_ = duration;
		} else {
			max_duration_ = std::max(duration, max_duration_);
		}
		Broodwar->drawTextScreen(4, 16, "Frame duration: %d ms, max %d ms, frame zero %d ms", duration, max_duration_, frame_zero_duration_);
	}
}

void ai_dc::onSendText(std::string text)
{
	log_event("onSendText", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("text", text)
	}, "none");
}

void ai_dc::onReceiveText(BWAPI::Player player, std::string text)
{
	log_event("onReceiveText", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("player", player_name(player)),
		arg("text", text)
	}, "none");
}

void ai_dc::onPlayerLeft(BWAPI::Player player)
{
	log_event("onPlayerLeft", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("player", player_name(player))
	}, "none");
}

void ai_dc::onNukeDetect(BWAPI::Position target)
{
	log_event("onNukeDetect", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("position", position_string(target))
	}, "none");

	python_bridge.send_event("onNukeDetect", {
		{"x", std::to_string(target.x)},
		{"y", std::to_string(target.y)}
	});
}

void ai_dc::onUnitDiscover(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitDiscover", unit);
	}
	if (unit->getType().isBuilding()) connectivity_grid.invalidate();
	information_manager.onUnitDiscover(unit);
}

void ai_dc::onUnitEvade(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitEvade", unit);
	}
	information_manager.onUnitEvade(unit);
}

void ai_dc::onUnitShow(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitShow", unit);
	}
}

void ai_dc::onUnitHide(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitHide", unit);
	}
}

void ai_dc::onUnitCreate(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitCreate", unit);
	}
	if (unit->getType().isBuilding()) connectivity_grid.invalidate();
	training_manager.onUnitCreate(unit);
	auto unit_player = unit->getPlayer();
	if (unit_player == Broodwar->self() || (unit_player != nullptr && unit_player->isEnemy(Broodwar->self()))) {
		bool own = (unit_player == Broodwar->self());
		python_bridge.send_raw_event("onUnitCreate",
			"{\"id\":" + std::to_string(unit->getID()) +
			",\"type\":\"" + MsgBusBridge::escape_json(unit->getType().getName()) + "\"" +
			",\"x\":" + std::to_string(unit->getPosition().x) +
			",\"y\":" + std::to_string(unit->getPosition().y) +
			",\"player\":\"" + MsgBusBridge::escape_json(unit_player ? unit_player->getName() : "Unknown") + "\"" +
			",\"own\":" + (own ? "true" : "false") + "}");
	}
}

void ai_dc::onUnitDestroy(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitDestroy", unit);
	}
	information_manager.onUnitDestroy(unit);
	building_manager.onUnitLost(unit);
	training_manager.onUnitLost(unit);
	worker_manager.onUnitLost(unit);
	bwem_handle_destroy_safe(unit);
	if (unit->getType().isBuilding()) connectivity_grid.invalidate();
	building_placement_manager.onUnitDestroy(unit);
	int destroy_id = unit ? unit->getID() : -1;
	std::string destroy_type = unit ? unit->getType().getName() : "";
	auto unit_player = unit ? unit->getPlayer() : nullptr;
	if (unit_player == Broodwar->self() || (unit_player != nullptr && unit_player->isEnemy(Broodwar->self()))) {
		bool own = (unit_player == Broodwar->self());
		python_bridge.send_raw_event("onUnitDestroy",
			"{\"id\":" + std::to_string(destroy_id) +
			",\"type\":\"" + MsgBusBridge::escape_json(destroy_type) + "\"" +
			",\"player\":\"" + MsgBusBridge::escape_json(unit_player ? unit_player->getName() : "Unknown") + "\"" +
			",\"own\":" + (own ? "true" : "false") + "}");
	}
	if (unit != nullptr) {
		last_unit_commands_.erase(unit->getID());
	}
}

void ai_dc::onUnitMorph(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitMorph", unit);
	}
	worker_manager.onUnitMorph(unit);
	training_manager.onUnitMorph(unit);
	auto unit_player = unit->getPlayer();
	if (unit_player == Broodwar->self() || (unit_player != nullptr && unit_player->isEnemy(Broodwar->self()))) {
		python_bridge.send_event("onUnitMorph", {
			{"unit_type", unit->getType().getName()},
			{"player", unit_player ? unit_player->getName() : "Unknown"}
		});
	}
}

void ai_dc::onUnitRenegade(BWAPI::Unit unit)
{
	if (unit != nullptr) {
		log_unit_event("onUnitRenegade", unit);
	}
	worker_manager.onUnitLost(unit);
}

void ai_dc::onSaveGame(std::string gameName)
{
	log_event("onSaveGame", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("game_name", gameName)
	}, "none");
}

void ai_dc::onUnitComplete(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitComplete", unit);
	}
	training_manager.onUnitComplete(unit);
	auto unit_player = unit->getPlayer();
	if (unit_player == Broodwar->self() || (unit_player != nullptr && unit_player->isEnemy(Broodwar->self()))) {
		bool own = (unit_player == Broodwar->self());
		python_bridge.send_raw_event("onUnitComplete",
			"{\"id\":" + std::to_string(unit->getID()) +
			",\"type\":\"" + MsgBusBridge::escape_json(unit->getType().getName()) + "\"" +
			",\"x\":" + std::to_string(unit->getPosition().x) +
			",\"y\":" + std::to_string(unit->getPosition().y) +
			",\"player\":\"" + MsgBusBridge::escape_json(unit_player ? unit_player->getName() : "Unknown") + "\"" +
			",\"own\":" + (own ? "true" : "false") + "}");
	}
}

void ai_dc::draw() {
	draw_info();
	base_state.draw();
	information_manager.draw();
	tactics_manager.draw();
	micro_manager.draw();
	building_placement_manager.draw();
	worker_manager.draw_for_workers();
	//room_grid.draw();
	//threat_grid.draw(true);
}

void ai_dc::before()
{
	information_manager.update_units_and_buildings();
	walkability_grid.update();
	connectivity_grid.update();
	base_state.update_base_information();
	path_finder.close_small_chokepoints_if_needed();
	unit_grid.update();
	training_manager.init_unit_count_map();
	building_manager.init_building_count_map();
	building_manager.init_base_defense_map();
	building_manager.init_upgrade_and_research();
	building_manager.update_supply_requests();
	information_manager.update_information();
	tactics_manager.update();
	opponent_model.update();
	threat_grid.update();
	micro_manager.prepare_combat();
	worker_manager.before();
}

void ai_dc::after()
{
	spending_manager.init_spendable();
	worker_manager.after();
	
	training_manager.update_overlord_training();
	if (training_manager.worker_production() && !training_manager.worker_cut()) training_manager.apply_worker_train_orders();
	building_manager.update_requested_building_count_for_pre_upgrade();
	building_manager.apply_building_requests(true);
    building_manager.apply_upgrades(true);
	if (training_manager.prioritize_training()) training_manager.apply_train_orders();
	building_manager.apply_building_requests(false);
    building_manager.apply_upgrades(false);
	building_manager.apply_research();
	if (!training_manager.prioritize_training()) training_manager.apply_train_orders();
	if (training_manager.worker_production() && training_manager.worker_cut()) training_manager.apply_worker_train_orders();
	
	building_manager.repair_damaged_buildings();
	building_manager.continue_unfinished_buildings_without_worker();
	worker_manager.apply_worker_orders();
	micro_manager.apply_combat_orders();
	building_manager.cancel_doomed_buildings();
}

void ai_dc::surrender_if_hope_lost()
{
	if ((Broodwar->getFrameCount() % (2 * 24)) != 0) return;
	
	for (auto& unit : Broodwar->self()->getUnits()) {
		if (unit->getType().isResourceDepot() && MineralGas(Broodwar->self()).can_pay(Broodwar->self()->getRace().getWorker())) return;
		if (unit->getType().isBuilding() && !unit->getTrainingQueue().empty()) return;
		if (unit->getType().groundWeapon() != WeaponTypes::None ||
			unit->getType().airWeapon() != WeaponTypes::None ||
			unit->getType() == UnitTypes::Protoss_Carrier ||
			unit->getType() == UnitTypes::Protoss_Reaver ||
			unit->getType() == UnitTypes::Zerg_Egg ||
			unit->getType() == UnitTypes::Zerg_Lurker_Egg ||
			unit->getType() == UnitTypes::Zerg_Cocoon) return;
	}
	
	Unitset enemy_units = Broodwar->enemies().getUnits();
	bool visible_attacker_found = std::any_of(enemy_units.begin(), enemy_units.end(), [](Unit unit){
		return (unit->getType().groundWeapon() != WeaponTypes::None ||
				unit->getType() == UnitTypes::Protoss_Carrier ||
				unit->getType() == UnitTypes::Protoss_Reaver);
	});
	if (!visible_attacker_found) return;
	
	if (configuration.human_opponent()) Broodwar->sendText("gg");
	Broodwar->leaveGame();
}

void ai_dc::draw_info()
{
	Broodwar->drawTextScreen(4, 26, "Time %s (frame %d)", frame_to_string(Broodwar->getFrameCount()).c_str(), Broodwar->getFrameCount());
	Broodwar->drawTextScreen(4, 36, "Playing: %s vs %s on %s%s", Broodwar->self()->getRace().getName().c_str(), opponent_model.enemy_race().getName().c_str(), Broodwar->mapFileName().c_str(), base_state.is_island_map() ? " (island map)" : "");
	Broodwar->drawTextScreen(4, 46, "Income: %d/%d ratio=%.1f",
							 spending_manager.income_per_minute().minerals,
							 spending_manager.income_per_minute().gas,
							 (double)spending_manager.income_per_minute().minerals / (double)spending_manager.income_per_minute().gas);
	Broodwar->drawTextScreen(4, 56, "Training: %.1f/%.1f/%.1f ratio=%.1f",
							 spending_manager.training_cost_per_minute().minerals,
							 spending_manager.training_cost_per_minute().gas,
							 spending_manager.training_cost_per_minute().supply,
							 spending_manager.training_cost_per_minute().minerals / spending_manager.training_cost_per_minute().gas);
	Broodwar->drawTextScreen(4, 66, "Worker training: %.1f/%.1f/%.1f", spending_manager.worker_training_cost_per_minute().minerals, spending_manager.worker_training_cost_per_minute().gas, spending_manager.worker_training_cost_per_minute().supply);
	Broodwar->drawTextScreen(4, 76, "Remainder: %d/%d", spending_manager.remainder().minerals, spending_manager.remainder().gas);
	Broodwar->drawTextScreen(4, 86, "Spendable: %d/%d", spending_manager.spendable().minerals, spending_manager.spendable().gas);
	Broodwar->drawTextScreen(4, 96, "Worker/Army supply: %g/%g opponent: %g/%g",
							 tactics_manager.worker_supply() * 0.5, tactics_manager.army_supply() * 0.5,
							 tactics_manager.enemy_worker_supply() * 0.5, tactics_manager.enemy_army_supply() * 0.5);
	Broodwar->drawTextScreen(4, 106, "Enemy defense and offense supply: %g/%g",
							 tactics_manager.enemy_defense_supply() * 0.5,
							 tactics_manager.enemy_offense_supply() * 0.5);
	Broodwar->drawTextScreen(4, 116, "Average #workers/mineral: %.1f, #mining bases: %d",
							 worker_manager.average_workers_per_mineral(),
							 base_state.mining_base_count());
	if (Broodwar->self()->getRace() == Races::Protoss) {
		Broodwar->drawTextScreen(4, 126, "Gateway distribution: Z %.2f, D %.2f, Ht %.2f, Dt %.2f",
								 training_manager.gateway_train_distribution().get(UnitTypes::Protoss_Zealot),
								 training_manager.gateway_train_distribution().get(UnitTypes::Protoss_Dragoon),
								 training_manager.gateway_train_distribution().get(UnitTypes::Protoss_High_Templar),
								 training_manager.gateway_train_distribution().get(UnitTypes::Protoss_Dark_Templar));
	}
	if (Broodwar->self()->getRace() == Races::Terran) {
		Broodwar->drawTextScreen(4, 126, "Factory distribution: V %.2f, S %.2f, G %.2f",
								 training_manager.factory_train_distribution().get(UnitTypes::Terran_Vulture),
								 training_manager.factory_train_distribution().get(UnitTypes::Terran_Siege_Tank_Tank_Mode),
								 training_manager.factory_train_distribution().get(UnitTypes::Terran_Goliath));
	}
	if (Broodwar->self()->getRace() == Races::Zerg) {
		Broodwar->drawTextScreen(4, 126, "Larva distribution: D %.2f, O %.2f, Z %.2f, H %.2f, M %.2f S %.2f Df %.2f U %.2f",
								 training_manager.larva_train_distribution().get(UnitTypes::Zerg_Drone),
								 training_manager.larva_train_distribution().get(UnitTypes::Zerg_Overlord),
								 training_manager.larva_train_distribution().get(UnitTypes::Zerg_Zergling),
								 training_manager.larva_train_distribution().get(UnitTypes::Zerg_Hydralisk),
								 training_manager.larva_train_distribution().get(UnitTypes::Zerg_Mutalisk),
								 training_manager.larva_train_distribution().get(UnitTypes::Zerg_Scourge),
								 training_manager.larva_train_distribution().get(UnitTypes::Zerg_Defiler),
								 training_manager.larva_train_distribution().get(UnitTypes::Zerg_Ultralisk));
	}
	Broodwar->drawTextScreen(4, 136, "Mode: %s", strategy_->mode().c_str());
	Broodwar->drawTextScreen(4, 146, "Opening: %s", strategy_->opening().c_str());
	Broodwar->drawTextScreen(4, 156, "Late game strategy: %s", strategy_->late_game_strategy().c_str());
	Broodwar->drawTextScreen(4, 166, "Enemy opening: %s", opponent_model.enemy_opening_info().c_str());
	Broodwar->drawTextScreen(4, 176, "Lost workers/units: %d/%d",
							 worker_manager.lost_worker_count(),
							 training_manager.lost_unit_count());
}

PerformanceTimer::PerformanceTimer()
{
	LARGE_INTEGER start;
	QueryPerformanceCounter(&start);
	start_ = start.QuadPart;
}

int PerformanceTimer::duration()
{
	LARGE_INTEGER end;
	LARGE_INTEGER frequency;
	QueryPerformanceCounter(&end);
	QueryPerformanceFrequency(&frequency);
	double frequency_rec = 1000.0 / frequency.QuadPart;
	return int((end.QuadPart - start_) * frequency_rec + 0.5);
}
