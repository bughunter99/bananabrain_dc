#include "ai_dc2.h"
#include "MsgBusBridge.h"
#include <iostream>

using namespace BWAPI;
using namespace Filter;

namespace {
    auto& python_bridge = MsgBusBridge::Instance();
}

void ai_dc2::onStart()
{
    int enemy_count = static_cast<int>(Broodwar->enemies().size());
    int map_width = Broodwar->mapWidth();
    int map_height = Broodwar->mapHeight();
    auto serialize_units = [](Player player) -> std::string {
        std::string value;
        if (player == nullptr) {
            return value;
        }
        for (auto& unit : player->getUnits()) {
            if (!unit || !unit->exists()) {
                continue;
            }
            if (!value.empty()) value += ";";
            value += std::to_string(unit->getID()) + ","
                + unit->getType().getName() + ","
                + std::to_string(unit->getPosition().x) + ","
                + std::to_string(unit->getPosition().y) + ","
                + (unit->isIdle() ? "1" : "0") + ","
                + (unit->isCarryingMinerals() ? "1" : "0") + ","
                + (unit->isCarryingGas() ? "1" : "0") + ","
                + (unit->isCompleted() ? "1" : "0") + ","
                + (unit->isConstructing() ? "1" : "0");
        }
        return value;
    };
    std::string own_units_str;
    if (Broodwar->self() != nullptr) {
        own_units_str = serialize_units(Broodwar->self());
    }
    std::string enemy_units_str;
    if (Broodwar->enemy() != nullptr) {
        enemy_units_str = serialize_units(Broodwar->enemy());
    }
    std::string mineral_fields_str;
    for (const auto& unit : Broodwar->getNeutralUnits()) {
        if (!unit || !unit->exists()) {
            continue;
        }
        if (!unit->getPlayer() || !unit->getPlayer()->isNeutral()) {
            continue;
        }
        if (!unit->getType().isMineralField()) {
            continue;
        }
        if (!mineral_fields_str.empty()) mineral_fields_str += ";";
        mineral_fields_str += std::to_string(unit->getID()) + ","
            + std::to_string(unit->getPosition().x) + ","
            + std::to_string(unit->getPosition().y);
    }

    // Serialize all start locations as "tx,ty;tx,ty;..."
    std::string start_locs_str;
    for (const auto& tp : Broodwar->getStartLocations()) {
        if (!start_locs_str.empty()) start_locs_str += ";";
        start_locs_str += std::to_string(tp.x) + "," + std::to_string(tp.y);
    }
    std::string self_start_str;
    if (Broodwar->self()) {
        TilePosition st = Broodwar->self()->getStartLocation();
        self_start_str = std::to_string(st.x) + "," + std::to_string(st.y);
    }

    python_bridge.start();
    python_bridge.send_event("onStart", {
        {"race", Broodwar->self() ? Broodwar->self()->getRace().getName() : "Unknown"},
        {"enemy_race", Broodwar->enemy() ? Broodwar->enemy()->getRace().getName() : "Unknown"},
        {"enemy_count", std::to_string(enemy_count)},
        {"is_replay", Broodwar->isReplay() ? "true" : "false"},
        {"map_name", Broodwar->mapName()},
        {"map_width_tiles", std::to_string(map_width)},
        {"map_height_tiles", std::to_string(map_height)},
        {"start_locations", start_locs_str},
        {"self_start", self_start_str},
        {"own_units", own_units_str},
        {"enemy_units", enemy_units_str},
        {"mineral_fields", mineral_fields_str}
    });

    // Enable the UserInput flag, which allows us to control the bot and type messages.
    Broodwar->enableFlag(Flag::UserInput);

    // Uncomment the following line and the bot will know about everything through the fog of war (cheat).
    //Broodwar->enableFlag(Flag::CompleteMapInformation);

    // Set the command optimization level so that common commands can be grouped
    // and reduce the bot's APM (Actions Per Minute).
    Broodwar->setCommandOptimizationLevel(2);

    // Check if this is a replay
    if ( Broodwar->isReplay() )
    {

        // Announce the players in the replay
        Broodwar << "The following players are in this replay:" << std::endl;
        
        // Iterate all the players in the game using a std:: iterator
        Playerset players = Broodwar->getPlayers();
        for(auto p : players)
        {
            // Only print the player if they are not an observer
            if ( !p->isObserver() )
                Broodwar << p->getName() << ", playing as " << p->getRace() << std::endl;
        }

    }
    else // if this is not a replay
    {
        // Retrieve you and your enemy's races. enemy() will just return the first enemy.
        // If you wish to deal with multiple enemies then you must use enemies().
        if ( Broodwar->enemy() ) // First make sure there is an enemy
            Broodwar << "The matchup is " << Broodwar->self()->getRace() << " vs " << Broodwar->enemy()->getRace() << std::endl;
    }

}

void ai_dc2::onEnd(bool isWinner)
{
    python_bridge.send_event("onEnd", {
        {"is_winner", isWinner ? "true" : "false"}
    });
    python_bridge.stop();

    // Called when the game ends
    if ( isWinner )
    {
        // Log your win here!
    }
}

void ai_dc2::onFrame()
{
    python_bridge.poll_actions();

    std::string mineral_fields_str;
    for (const auto& unit : Broodwar->getNeutralUnits()) {
        if (!unit || !unit->exists()) {
            continue;
        }
        if (!unit->getPlayer() || !unit->getPlayer()->isNeutral()) {
            continue;
        }
        if (!unit->getType().isMineralField()) {
            continue;
        }
        if (!mineral_fields_str.empty()) mineral_fields_str += ";";
        mineral_fields_str += std::to_string(unit->getID()) + ","
            + std::to_string(unit->getPosition().x) + ","
            + std::to_string(unit->getPosition().y);
    }

    if ( (Broodwar->getFrameCount() % 24) == 0 )
    {
        int own_unit_count = 0;
        int enemy_unit_count = 0;
        int own_worker_count = 0;
        int enemy_worker_count = 0;
        int own_army_supply = 0;
        int enemy_army_supply = 0;

        if (Broodwar->self() != nullptr) {
            for (auto& unit : Broodwar->self()->getUnits()) {
                if (!unit || !unit->exists()) {
                    continue;
                }
                ++own_unit_count;
                if (unit->getType().isWorker()) {
                    ++own_worker_count;
                }
                if (!unit->getType().isWorker() && !unit->getType().isBuilding()) {
                    own_army_supply += unit->getType().supplyRequired();
                }
            }
        }

        if (Broodwar->enemy() != nullptr) {
            for (auto& unit : Broodwar->enemy()->getUnits()) {
                if (!unit || !unit->exists()) {
                    continue;
                }
                ++enemy_unit_count;
                if (unit->getType().isWorker()) {
                    ++enemy_worker_count;
                }
                if (!unit->getType().isWorker() && !unit->getType().isBuilding()) {
                    enemy_army_supply += unit->getType().supplyRequired();
                }
            }
        }

        std::string own_units_str;
        if (Broodwar->self() != nullptr) {
            for (auto& u : Broodwar->self()->getUnits()) {
                if (!u || !u->exists()) {
                    continue;
                }
                if (!own_units_str.empty()) own_units_str += ";";
                own_units_str += std::to_string(u->getID()) + ","
                     + u->getType().getName() + ","
                     + std::to_string(u->getPosition().x) + ","
                     + std::to_string(u->getPosition().y) + ","
                     + (u->isIdle() ? "1" : "0") + ","
                     + (u->isCarryingMinerals() ? "1" : "0") + ","
                     + (u->isCarryingGas() ? "1" : "0") + ","
                     + (u->isCompleted() ? "1" : "0") + ","
                     + (u->isConstructing() ? "1" : "0");
            }
        }

        std::string enemy_units_str;
        if (Broodwar->enemy() != nullptr) {
            for (auto& u : Broodwar->enemy()->getUnits()) {
                if (!u || !u->exists()) {
                    continue;
                }
                if (!enemy_units_str.empty()) enemy_units_str += ";";
                enemy_units_str += std::to_string(u->getID()) + ","
                    + u->getType().getName() + ","
                    + std::to_string(u->getPosition().x) + ","
                    + std::to_string(u->getPosition().y) + ","
                    + (u->isIdle() ? "1" : "0") + ","
                    + (u->isCarryingMinerals() ? "1" : "0") + ","
                    + (u->isCarryingGas() ? "1" : "0") + ","
                    + (u->isCompleted() ? "1" : "0") + ","
                    + (u->isConstructing() ? "1" : "0");
            }
        }

        python_bridge.send_event("onFrame", {
            {"race", Broodwar->self() ? Broodwar->self()->getRace().getName() : "Unknown"},
            {"enemy_race", Broodwar->enemy() ? Broodwar->enemy()->getRace().getName() : "Unknown"},
            {"enemy_count", std::to_string(static_cast<int>(Broodwar->enemies().size()))},
            {"minerals", std::to_string(Broodwar->self() ? Broodwar->self()->minerals() : 0)},
            {"gas", std::to_string(Broodwar->self() ? Broodwar->self()->gas() : 0)},
            {"supply_used", std::to_string(Broodwar->self() ? Broodwar->self()->supplyUsed() : 0)},
            {"supply_total", std::to_string(Broodwar->self() ? Broodwar->self()->supplyTotal() : 0)},
            {"own_unit_count", std::to_string(own_unit_count)},
            {"enemy_unit_count", std::to_string(enemy_unit_count)},
            {"own_worker_count", std::to_string(own_worker_count)},
            {"enemy_worker_count", std::to_string(enemy_worker_count)},
            {"army_supply", std::to_string(own_army_supply)},
            {"enemy_army_supply", std::to_string(enemy_army_supply)},
            {"enemy_offense_supply", std::to_string(enemy_army_supply)},
            {"defense_supply", std::to_string(own_army_supply)},
            {"mineral_fields", mineral_fields_str},
            {"enemy_units", enemy_units_str},
            {"own_units", [&]() -> std::string {
                std::string s;
                if (Broodwar->self()) {
                    for (auto& u : Broodwar->self()->getUnits()) {
                        if (!u || !u->exists()) {
                            continue;
                        }
                        if (!s.empty()) s += ";";
                        s += std::to_string(u->getID()) + ","
                             + u->getType().getName() + ","
                             + std::to_string(u->getPosition().x) + ","
                             + std::to_string(u->getPosition().y) + ","
                             + (u->isIdle() ? "1" : "0") + ","
                             + (u->isCarryingMinerals() ? "1" : "0") + ","
                             + (u->isCarryingGas() ? "1" : "0") + ","
                             + (u->isCompleted() ? "1" : "0") + ","
                             + (u->isConstructing() ? "1" : "0");
                    }
                }
                return s;
            }()},
            {"overlord_units", [&]() -> std::string {
                std::string s;
                if (Broodwar->self()) {
                    for (auto& u : Broodwar->self()->getUnits()) {
                        if (u && u->exists() && u->getType() == UnitTypes::Zerg_Overlord) {
                            if (!s.empty()) s += ";";
                            s += std::to_string(u->getID()) + ","
                                 + std::to_string(u->getPosition().x) + ","
                                 + std::to_string(u->getPosition().y) + ","
                                 + (u->isIdle() ? "1" : "0");
                        }
                    }
                }
                return s;
            }()},
            {"explored_start_tiles", [&]() -> std::string {
                std::string s;
                for (const auto& tp : Broodwar->getStartLocations()) {
                    if (Broodwar->isExplored(tp)) {
                        if (!s.empty()) s += ";";
                        s += std::to_string(tp.x) + "," + std::to_string(tp.y);
                    }
                }
                return s;
            }()}
        });
    }

    // Called once every game frame

    // Display the game frame rate as text in the upper left area of the screen
    Broodwar->drawTextScreen(200, 0,    "FPS: %d", Broodwar->getFPS() );
    Broodwar->drawTextScreen(200, 20, "Average FPS: %f", Broodwar->getAverageFPS() );

    // Return if the game is a replay or is paused
    if ( Broodwar->isReplay() || Broodwar->isPaused() || !Broodwar->self() )
        return;

    // Prevent spamming by only running our onFrame once every number of latency frames.
    // Latency frames are the number of frames before commands are processed.
    if ( Broodwar->getFrameCount() % Broodwar->getLatencyFrames() != 0 )
        return;

    return;
}

void ai_dc2::onSendText(std::string text)
{

    // Send the text to the game if it is not being processed.
    Broodwar->sendText("%s", text.c_str());


    // Make sure to use %s and pass the text as a parameter,
    // otherwise you may run into problems when you use the %(percent) character!

}

void ai_dc2::onReceiveText(BWAPI::Player player, std::string text)
{
    // Parse the received text
    Broodwar << player->getName() << " said \"" << text << "\"" << std::endl;
}

void ai_dc2::onPlayerLeft(BWAPI::Player player)
{
    (void)player;
}

void ai_dc2::onNukeDetect(BWAPI::Position target)
{
    python_bridge.send_event("onNukeDetect", {
        {"x", std::to_string(target.x)},
        {"y", std::to_string(target.y)}
    });


    // You can also retrieve all the nuclear missile targets using Broodwar->getNukeDots()!
}

void ai_dc2::onUnitDiscover(BWAPI::Unit unit)
{
}

void ai_dc2::onUnitEvade(BWAPI::Unit unit)
{
}

void ai_dc2::onUnitShow(BWAPI::Unit unit)
{
}

void ai_dc2::onUnitHide(BWAPI::Unit unit)
{
}

void ai_dc2::onUnitCreate(BWAPI::Unit unit)
{
    if (unit != nullptr)
    {
        python_bridge.send_event("onUnitCreate", {
            {"id", std::to_string(unit->getID())},
            {"type", unit->getType().getName()},
            {"player", unit->getPlayer() ? unit->getPlayer()->getName() : "Unknown"}
        });
    }

}

void ai_dc2::onUnitDestroy(BWAPI::Unit unit)
{
    if (unit != nullptr)
    {
        python_bridge.send_event("onUnitDestroy", {
            {"id", std::to_string(unit->getID())},
            {"type", unit->getType().getName()},
            {"player", unit->getPlayer() ? unit->getPlayer()->getName() : "Unknown"}
        });
    }
}

void ai_dc2::onUnitMorph(BWAPI::Unit unit)
{
    (void)unit;
}

void ai_dc2::onUnitRenegade(BWAPI::Unit unit)
{
}

void ai_dc2::onSaveGame(std::string gameName)
{
    Broodwar << "The game was saved to \"" << gameName << "\"" << std::endl;
}

void ai_dc2::onUnitComplete(BWAPI::Unit unit)
{
}
