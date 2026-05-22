#include "BananaBrain.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <iomanip>
#include <sstream>

namespace {
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

void BananaBrain::open_log()
{
	if (log_stream_.is_open()) return;

	char module_path[MAX_PATH] = {};
	DWORD path_length = GetModuleFileNameA(nullptr, module_path, MAX_PATH);
	if (path_length == 0 || path_length == MAX_PATH) return;

	std::string executable_path(module_path, path_length);
	std::string::size_type separator = executable_path.find_last_of("\\/");
	std::string directory = (separator == std::string::npos) ? std::string() : executable_path.substr(0, separator + 1);
	log_path_ = directory + "BananaBrain" + timestamp_now("%Y%m%d%H");
	log_stream_.open(log_path_, std::ios::out | std::ios::app);
	if (log_stream_.is_open()) {
		log_event("LogOpened", {arg("path", log_path_)}, "none");
	}
}

void BananaBrain::close_log()
{
	if (!log_stream_.is_open()) return;
	log_event("LogClosed", {arg("path", log_path_)}, "none");
	log_stream_.close();
	last_unit_commands_.clear();
}

void BananaBrain::log_event(const std::string& event_name,
						std::initializer_list<std::pair<std::string,std::string>> args,
						const std::string& action)
{
	log_event(event_name, std::vector<std::pair<std::string,std::string>>(args), action);
}

void BananaBrain::log_event(const std::string& event_name,
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

std::vector<std::pair<std::string,std::string>> BananaBrain::base_unit_args(Unit unit) const
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

std::string BananaBrain::describe_command(const UnitCommand& command) const
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

std::string BananaBrain::current_action_for(Unit unit) const
{
	if (unit == nullptr || Broodwar->self() == nullptr) return "none";
	if (unit->getPlayer() != Broodwar->self()) return "none";
	return describe_command(unit->getLastCommand());
}

void BananaBrain::log_unit_event(const std::string& event_name,
							 Unit unit,
							 const std::vector<std::pair<std::string,std::string>>& extra_args)
{
	auto args = base_unit_args(unit);
	args.insert(args.end(), extra_args.begin(), extra_args.end());
	log_event(event_name, args, current_action_for(unit));
}

void BananaBrain::log_recent_unit_commands()
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

void BananaBrain::onStart()
{
	open_log();
	log_event("onStart", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("self_race", Broodwar->self() ? Broodwar->self()->getRace().getName() : "Unknown"),
		arg("enemy_count", std::to_string((int)Broodwar->enemies().size())),
		arg("is_replay", Broodwar->isReplay() ? "true" : "false")
	}, "none");

	python_bridge.start();
	python_bridge.send_event("onStart", {
		{"self_race", Broodwar->self() ? Broodwar->self()->getRace().getName() : "Unknown"},
		{"enemy_count", std::to_string((int)Broodwar->enemies().size())},
		{"is_replay", Broodwar->isReplay() ? "true" : "false"}
	});

	// Enable the UserInput flag, which allows us to control the bot and type messages.
	//Broodwar->enableFlag(Flag::UserInput);
 
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
		}
	}
}

void BananaBrain::onEnd(bool winner)
{
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

void BananaBrain::onFrame()
{
	if (!initialized_) return;
	if (Broodwar->isPaused() || !Broodwar->self()) return;
	if (configuration.human_opponent() && Broodwar->getFrameCount() == 240) Broodwar->sendText("glhf");

	python_bridge.poll_actions();

	if ((Broodwar->getFrameCount() % 240) == 0) {
		python_bridge.send_event("onFrame", {
			{"minerals", std::to_string(Broodwar->self()->minerals())},
			{"gas", std::to_string(Broodwar->self()->gas())},
			{"supply_used", std::to_string(Broodwar->self()->supplyUsed())},
			{"supply_total", std::to_string(Broodwar->self()->supplyTotal())},
			{"mode", strategy_ ? strategy_->mode() : ""}
		});
	}
	
	PerformanceTimer performance_timer;
	
	before();
	strategy_->frame();
	after();
	log_recent_unit_commands();
	surrender_if_hope_lost();
	
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

void BananaBrain::onSendText(std::string text)
{
	log_event("onSendText", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("text", text)
	}, "none");
}

void BananaBrain::onReceiveText(BWAPI::Player player, std::string text)
{
	log_event("onReceiveText", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("player", player_name(player)),
		arg("text", text)
	}, "none");
}

void BananaBrain::onPlayerLeft(BWAPI::Player player)
{
	log_event("onPlayerLeft", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("player", player_name(player))
	}, "none");
}

void BananaBrain::onNukeDetect(BWAPI::Position target)
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

void BananaBrain::onUnitDiscover(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitDiscover", unit);
	}
	if (unit->getType().isBuilding()) connectivity_grid.invalidate();
	information_manager.onUnitDiscover(unit);
}

void BananaBrain::onUnitEvade(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitEvade", unit);
	}
	information_manager.onUnitEvade(unit);
}

void BananaBrain::onUnitShow(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitShow", unit);
	}
}

void BananaBrain::onUnitHide(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitHide", unit);
	}
}

void BananaBrain::onUnitCreate(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitCreate", unit);
	}
	if (unit->getType().isBuilding()) connectivity_grid.invalidate();
	training_manager.onUnitCreate(unit);
	auto unit_player = unit->getPlayer();
	if (unit_player == Broodwar->self() || (unit_player != nullptr && unit_player->isEnemy(Broodwar->self()))) {
		python_bridge.send_event("onUnitCreate", {
			{"unit_type", unit->getType().getName()},
			{"player", unit_player ? unit_player->getName() : "Unknown"}
		});
	}
}

void BananaBrain::onUnitDestroy(BWAPI::Unit unit)
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
	auto unit_player = unit->getPlayer();
	if (unit_player == Broodwar->self() || (unit_player != nullptr && unit_player->isEnemy(Broodwar->self()))) {
		python_bridge.send_event("onUnitDestroy", {
			{"unit_type", unit->getType().getName()},
			{"player", unit_player ? unit_player->getName() : "Unknown"}
		});
	}
	if (unit != nullptr) {
		last_unit_commands_.erase(unit->getID());
	}
}

void BananaBrain::onUnitMorph(BWAPI::Unit unit)
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

void BananaBrain::onUnitRenegade(BWAPI::Unit unit)
{
	if (unit != nullptr) {
		log_unit_event("onUnitRenegade", unit);
	}
	worker_manager.onUnitLost(unit);
}

void BananaBrain::onSaveGame(std::string gameName)
{
	log_event("onSaveGame", {
		arg("frame", std::to_string(Broodwar->getFrameCount())),
		arg("game_name", gameName)
	}, "none");
}

void BananaBrain::onUnitComplete(BWAPI::Unit unit)
{
	if (unit != nullptr && (unit->getPlayer() == Broodwar->self() || unit->getPlayer()->isEnemy(Broodwar->self()))) {
		log_unit_event("onUnitComplete", unit);
	}
	training_manager.onUnitComplete(unit);
	auto unit_player = unit->getPlayer();
	if (unit_player == Broodwar->self() || (unit_player != nullptr && unit_player->isEnemy(Broodwar->self()))) {
		python_bridge.send_event("onUnitComplete", {
			{"unit_type", unit->getType().getName()},
			{"player", unit_player ? unit_player->getName() : "Unknown"}
		});
	}
}

void BananaBrain::draw() {
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

void BananaBrain::before()
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

void BananaBrain::after()
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

void BananaBrain::surrender_if_hope_lost()
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

void BananaBrain::draw_info()
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
