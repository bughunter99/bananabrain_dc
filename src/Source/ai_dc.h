#pragma once

#include <BWAPI.h>
#include "bwem.h"
#include "JPS.h"
#include <set>
#include <array>
#include <vector>
#include <map>
#include <deque>
#include <algorithm>
#include <ctime>
#include <fstream>
#include <functional>
#include <chrono>
#include <random>
#include <optional>
#include <climits>

using namespace BWAPI;

static constexpr auto M_PI = 3.14159265358979323846;

#include "FastPosition.h"
#include "UnitUtils.h"
#include "Utils.h"
#include "UnitPotential.h"
#include "Configuration.h"

#include "BaseState.h"
#include "PathFinder.h"
#include "Information.h"
#include "Grids.h"
#include "Tactics.h"
#include "OpponentModel.h"
#include "Micro.h"
#include "Macro.h"
#include "WallPlacement.h"
#include "BuildingPlacement.h"
#include "Worker.h"
#include "Results.h"
#include "MsgBusBridge.h"
#include "Strategy.h"

// Remember not to use "Broodwar" in any global class constructor!

namespace {
	auto& bwem_map = BWEM::Map::Instance();
	
	auto& configuration = Configuration::Instance();
	auto& base_state = BaseState::Instance();
	auto& path_finder = PathFinder::Instance();
	auto& walkability_grid = WalkabilityGrid::Instance();
	auto& connectivity_grid = ConnectivityGrid::Instance();
	auto& threat_grid = ThreatGrid::Instance();
	auto& unit_grid = UnitGrid::Instance();
	auto& room_grid = RoomGrid::Instance();
	auto& micro_manager = MicroManager::Instance();
	auto& information_manager = InformationManager::Instance();
	auto& tactics_manager = TacticsManager::Instance();
	auto& opponent_model = OpponentModel::Instance();
	auto& worker_manager = WorkerManager::Instance();
	auto& building_manager = BuildingManager::Instance();
	auto& building_placement_manager = BuildingPlacementManager::Instance();
	auto& spending_manager = SpendingManager::Instance();
	auto& training_manager = TrainingManager::Instance();
	auto& result_store = ResultStore::Instance();
	auto& python_bridge = MsgBusBridge::Instance();
}

class ai_dc : public AIModule
{
public:
	// Virtual functions for callbacks, leave these as they are.
	virtual void onStart();
	virtual void onEnd(bool isWinner);
	virtual void onFrame();
	virtual void onSendText(std::string text);
	virtual void onReceiveText(Player player, std::string text);
	virtual void onPlayerLeft(Player player);
	virtual void onNukeDetect(Position target);
	virtual void onUnitDiscover(Unit unit);
	virtual void onUnitEvade(Unit unit);
	virtual void onUnitShow(Unit unit);
	virtual void onUnitHide(Unit unit);
	virtual void onUnitCreate(Unit unit);
	virtual void onUnitDestroy(Unit unit);
	virtual void onUnitMorph(Unit unit);
	virtual void onUnitRenegade(Unit unit);
	virtual void onSaveGame(std::string gameName);
	virtual void onUnitComplete(Unit unit);
	// Everything below this line is safe to modify.
	
	void before();
	void after();
	void surrender_if_hope_lost();
	void draw();
	void draw_info();
	bool force_opening(const std::string& opening);
	
private:
	struct CommandSnapshot
	{
		int frame = -1;
		std::string signature;
	};

	void open_log();
	void close_log();
	void log_event(const std::string& event_name,
					   std::initializer_list<std::pair<std::string,std::string>> args,
					   const std::string& action = "none");
	void log_event(const std::string& event_name,
					   const std::vector<std::pair<std::string,std::string>>& args,
					   const std::string& action = "none");
	void log_unit_event(const std::string& event_name,
						Unit unit,
						const std::vector<std::pair<std::string,std::string>>& extra_args = {});
	void log_recent_unit_commands();
	std::vector<std::pair<std::string,std::string>> base_unit_args(Unit unit) const;
	std::string current_action_for(Unit unit) const;
	std::string describe_command(const UnitCommand& command) const;

	int max_duration_ = 0;
	int frame_zero_duration_ = 0;
	bool initialized_ = false;
	bool is_1v1_ = false;
	bool is_ffa_ = false;
	std::string log_path_;
	std::ofstream log_stream_;
	std::map<int,CommandSnapshot> last_unit_commands_;
	std::unique_ptr<Strategy> strategy_;
};

bool force_strategy_opening(const std::string& opening);

// Manual-mode control: when manual_mode=true, strategy and after() are skipped.
// Workers do nothing until an explicit command is issued via the web bridge.
void set_manual_mode(bool manual);
bool is_manual_mode();
void set_python_mode(bool python_mode);
bool is_python_mode();
void gather_workers_minerals();
void scout_with_worker();
void block_entrance_with_workers();

class PerformanceTimer
{
public:
	PerformanceTimer();
	int duration();
	
private:
	int64_t start_;
};
