#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")

#include "MsgBusBridge.h"

#include <algorithm>
#include <cctype>
#include <cstring>
#include <functional>

using namespace BWAPI;

static_assert(sizeof(sockaddr_in) == 16, "sockaddr_in size mismatch");

static inline SOCKET to_sock(uintptr_t h) { return static_cast<SOCKET>(h); }
static inline uintptr_t from_sock(SOCKET s) { return static_cast<uintptr_t>(s); }
static inline bool sock_valid(uintptr_t h) { return h != ~uintptr_t(0); }
static inline sockaddr_in& as_sin(char (&b)[16]) { return *reinterpret_cast<sockaddr_in*>(b); }

namespace {

static UnitType find_unit_type_by_name(const std::string& name) {
    if (name.empty()) {
        return UnitTypes::None;
    }
    for (const auto& t : UnitTypes::allUnitTypes()) {
        if (t == UnitTypes::Unknown || t == UnitTypes::None) {
            continue;
        }
        const std::string full_name = t.getName();
        if (_stricmp(full_name.c_str(), name.c_str()) == 0) {
            return t;
        }

        const size_t underscore = full_name.find('_');
        if (underscore != std::string::npos) {
            const std::string short_name = full_name.substr(underscore + 1);
            if (_stricmp(short_name.c_str(), name.c_str()) == 0) {
                return t;
            }
        }
    }
    return UnitTypes::None;
}

static UpgradeType find_upgrade_type_by_name(const std::string& name) {
    if (name.empty()) {
        return UpgradeTypes::None;
    }
    for (const auto& t : UpgradeTypes::allUpgradeTypes()) {
        if (t == UpgradeTypes::None) {
            continue;
        }
        const std::string full_name = t.getName();
        if (_stricmp(full_name.c_str(), name.c_str()) == 0) {
            return t;
        }
        const size_t underscore = full_name.find('_');
        if (underscore != std::string::npos) {
            const std::string short_name = full_name.substr(underscore + 1);
            if (_stricmp(short_name.c_str(), name.c_str()) == 0) {
                return t;
            }
        }
    }
    return UpgradeTypes::None;
}

static const char* skip_ws(const char* p) {
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') {
        ++p;
    }
    return p;
}

static bool parse_json_string(const char** pp, std::string& out_value) {
    const char* p = *pp;
    if (*p != '"') {
        return false;
    }
    ++p;
    out_value.clear();
    while (*p && *p != '"') {
        if (*p == '\\') {
            ++p;
            switch (*p) {
            case '"': out_value += '"'; break;
            case '\\': out_value += '\\'; break;
            case '/': out_value += '/'; break;
            case 'n': out_value += '\n'; break;
            case 'r': out_value += '\r'; break;
            case 't': out_value += '\t'; break;
            default: out_value += *p; break;
            }
        } else {
            out_value += *p;
        }
        ++p;
    }
    if (*p == '"') {
        ++p;
    }
    *pp = p;
    return true;
}

static bool parse_json_int(const char** pp, int& out_value) {
    const char* p = *pp;
    bool neg = false;
    if (*p == '-') {
        neg = true;
        ++p;
    }
    if (*p < '0' || *p > '9') {
        return false;
    }
    int v = 0;
    while (*p >= '0' && *p <= '9') {
        v = (v * 10) + (*p - '0');
        ++p;
    }
    out_value = neg ? -v : v;
    *pp = p;
    return true;
}

static void parse_flat_object(const char* p,
                                                            std::map<std::string, std::string>& str_fields,
                                                            std::map<std::string, int>& int_fields) {
    p = skip_ws(p);
    if (*p != '{') {
        return;
    }
    ++p;

    while (true) {
        p = skip_ws(p);
        if (*p == '}' || *p == '\0') {
            break;
        }
        if (*p == ',') {
            ++p;
            continue;
        }

        std::string key;
        if (!parse_json_string(&p, key)) {
            break;
        }
        p = skip_ws(p);
        if (*p != ':') {
            break;
        }
        ++p;
        p = skip_ws(p);

        if (*p == '"') {
            std::string val;
            if (parse_json_string(&p, val)) {
                str_fields[key] = val;
            }
        } else if (*p == '-' || (*p >= '0' && *p <= '9')) {
            int val = 0;
            if (parse_json_int(&p, val)) {
                int_fields[key] = val;
            }
        } else {
            int depth = 0;
            while (*p) {
                if (*p == '{' || *p == '[') {
                    ++depth;
                } else if (*p == '}' || *p == ']') {
                    if (depth == 0) {
                        break;
                    }
                    --depth;
                } else if ((*p == ',' || *p == '}') && depth == 0) {
                    break;
                }
                ++p;
            }
        }
    }
}

static void parse_action_json(const std::string& json,
                                                            std::function<void(const std::map<std::string, std::string>&,
                                                                                                 const std::map<std::string, int>&)> cb) {
    const char* p = skip_ws(json.c_str());

    if (*p == '[') {
        ++p;
        while (true) {
            p = skip_ws(p);
            if (*p == ']' || *p == '\0') {
                break;
            }
            if (*p == ',') {
                ++p;
                continue;
            }
            if (*p == '{') {
                int depth = 1;
                const char* start = p;
                ++p;
                while (*p && depth > 0) {
                    if (*p == '{') {
                        ++depth;
                    } else if (*p == '}') {
                        --depth;
                    } else if (*p == '"') {
                        ++p;
                        while (*p && *p != '"') {
                            if (*p == '\\') {
                                ++p;
                            }
                            ++p;
                        }
                    }
                    if (depth > 0 || *p == '}') {
                        ++p;
                    } else {
                        break;
                    }
                }

                std::string obj_str(start, p);
                std::map<std::string, std::string> sf;
                std::map<std::string, int> nf;
                parse_flat_object(obj_str.c_str(), sf, nf);
                cb(sf, nf);
            } else {
                ++p;
            }
        }
    } else if (*p == '{') {
        std::map<std::string, std::string> sf;
        std::map<std::string, int> nf;
        parse_flat_object(p, sf, nf);
        cb(sf, nf);
    }
}

}    // namespace

MsgBusBridge& MsgBusBridge::Instance() {
    static MsgBusBridge inst;
    return inst;
}

bool MsgBusBridge::start() {
    if (running_) {
        return true;
    }

    WSADATA wsa_data = {};
    if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
        return false;
    }
    wsa_started_ = true;

    send_sock_ = from_sock(socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP));
    if (!sock_valid(send_sock_)) {
        stop();
        return false;
    }

    memset(agent_addr_, 0, sizeof(agent_addr_));
    as_sin(agent_addr_).sin_family = AF_INET;
    as_sin(agent_addr_).sin_port = htons(static_cast<u_short>(event_port));
    as_sin(agent_addr_).sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    recv_sock_ = from_sock(socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP));
    if (!sock_valid(recv_sock_)) {
        stop();
        return false;
    }

    sockaddr_in bind_addr = {};
    bind_addr.sin_family = AF_INET;
    bind_addr.sin_port = htons(static_cast<u_short>(action_port));
    bind_addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    if (bind(to_sock(recv_sock_), reinterpret_cast<sockaddr*>(&bind_addr), sizeof(bind_addr)) == SOCKET_ERROR) {
        stop();
        return false;
    }

    u_long mode = 1;
    ioctlsocket(to_sock(recv_sock_), FIONBIO, &mode);

    running_ = true;
    return true;
}

void MsgBusBridge::stop() {
    flush_pending_events();
    if (running_) {
        send_event("shutdown");
        flush_pending_events();
    }
    running_ = false;

    if (sock_valid(send_sock_)) {
        closesocket(to_sock(send_sock_));
        send_sock_ = ~uintptr_t(0);
    }
    if (sock_valid(recv_sock_)) {
        closesocket(to_sock(recv_sock_));
        recv_sock_ = ~uintptr_t(0);
    }
    if (wsa_started_) {
        WSACleanup();
        wsa_started_ = false;
    }
}

void MsgBusBridge::send_event(const std::string& event_name,
                                                            const std::map<std::string, std::string>& payload) {
    if (!sock_valid(send_sock_)) {
        return;
    }

    int frame = (BroodwarPtr != nullptr) ? Broodwar->getFrameCount() : -1;
    const std::string msg = build_message(event_name, frame, payload_to_json(payload));
    enqueue_event_packet(msg);
}

void MsgBusBridge::send_raw_event(const std::string& event_name,
                                                                    const std::string& raw_payload_json) {
    if (!sock_valid(send_sock_)) {
        return;
    }

    int frame = (BroodwarPtr != nullptr) ? Broodwar->getFrameCount() : -1;
    const std::string msg = build_message(event_name, frame, raw_payload_json);
    enqueue_event_packet(msg);
}

void MsgBusBridge::poll_actions() {
    if (!sock_valid(recv_sock_)) {
        return;
    }

    static char buf[65507];

    while (true) {
        sockaddr_in from = {};
        int from_len = sizeof(from);
        int bytes = recvfrom(to_sock(recv_sock_),
                                                 buf,
                                                 sizeof(buf) - 1,
                                                 0,
                                                 reinterpret_cast<sockaddr*>(&from),
                                                 &from_len);
        if (bytes == SOCKET_ERROR) {
            break;
        }
        buf[bytes] = '\0';
        enqueue_action_packet(std::string(buf, bytes));
    }
}

void MsgBusBridge::flush_pending_events() {
    if (!sock_valid(send_sock_)) {
        return;
    }

    std::deque<std::string> packets;
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        packets.swap(pending_event_packets_);
    }

    for (const auto& packet : packets) {
        sendto(to_sock(send_sock_),
                     packet.c_str(),
                     static_cast<int>(packet.size()),
                     0,
                     reinterpret_cast<const sockaddr*>(agent_addr_),
                     sizeof(sockaddr_in));
    }
}

void MsgBusBridge::process_pending_actions() {
    std::deque<std::string> packets;
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        packets.swap(pending_action_packets_);
    }

    for (const auto& packet : packets) {
        apply_action_json(packet);
    }
}

std::string MsgBusBridge::escape_json(const std::string& raw) {
    std::string out;
    out.reserve(raw.size() + 8);
    for (char c : raw) {
        switch (c) {
        case '\\': out += "\\\\"; break;
        case '"': out += "\\\""; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        case '\t': out += "\\t"; break;
        default: out += c; break;
        }
    }
    return out;
}

std::string MsgBusBridge::payload_to_json(const std::map<std::string, std::string>& payload) {
    std::string json = "{";
    bool first = true;
    for (const auto& kv : payload) {
        if (!first) {
            json += ",";
        }
        first = false;
        json += "\"" + escape_json(kv.first) + "\":\"" + escape_json(kv.second) + "\"";
    }
    json += "}";
    return json;
}

std::string MsgBusBridge::build_message(const std::string& event_name,
                                                                                int frame,
                                                                                const std::string& payload_json) {
    return "{\"event\":\"" + escape_json(event_name) +
                 "\",\"frame\":" + std::to_string(frame) +
                 ",\"payload\":" + payload_json + "}";
}

void MsgBusBridge::enqueue_event_packet(const std::string& packet) {
    std::lock_guard<std::mutex> lock(queue_mutex_);
    pending_event_packets_.push_back(packet);
}

void MsgBusBridge::enqueue_action_packet(const std::string& packet) {
    std::lock_guard<std::mutex> lock(queue_mutex_);
    pending_action_packets_.push_back(packet);
}

void MsgBusBridge::apply_action_json(const std::string& json) {
    parse_action_json(
            json,
            [this](const std::map<std::string, std::string>& sf, const std::map<std::string, int>& nf) {
                auto it = sf.find("type");
                if (it == sf.end()) {
                    return;
                }
                apply_action_object(it->second, sf, nf);
            });
}

void MsgBusBridge::apply_action_object(const std::string& type,
                                                                             const std::map<std::string, std::string>& sf,
                                                                             const std::map<std::string, int>& nf) {
    if (type.empty() || type == "none") {
        return;
    }

    if (BroodwarPtr == nullptr || Broodwar->self() == nullptr) {
        return;
    }

    if (type == "send_text") {
        auto it = sf.find("text");
        if (it != sf.end() && !it->second.empty()) {
            Broodwar->sendText("%s", it->second.c_str());
        }
        return;
    }

    if (type == "leave_game") {
        Broodwar->leaveGame();
        return;
    }

    if (type == "strategy_command") {
        std::string opening;
        std::string mode;
        std::string late_game;
        std::string strategy_unit;
        auto oi = sf.find("opening");
        if (oi != sf.end()) opening = oi->second;
        auto mi = sf.find("mode");
        if (mi != sf.end()) mode = mi->second;
        auto li = sf.find("late_game_strategy");
        if (li != sf.end()) late_game = li->second;
        auto si = sf.find("strategy_unit");
        if (si != sf.end()) strategy_unit = si->second;

        return;
    }

    if (type == "build_structure") {
        auto bi = sf.find("building_type");
        if (bi == sf.end()) {
            return;
        }

        UnitType building_type = find_unit_type_by_name(bi->second);
        if (building_type == UnitTypes::None || !building_type.isBuilding()) {
            return;
        }

        Unit builder = nullptr;
        for (auto& my_unit : Broodwar->self()->getUnits()) {
            if (my_unit == nullptr || !my_unit->exists()) {
                continue;
            }
            if (!my_unit->getType().isWorker()) {
                continue;
            }
            if (my_unit->isConstructing() || my_unit->isCarryingGas() || my_unit->isCarryingMinerals()) {
                continue;
            }
            builder = my_unit;
            break;
        }

        if (builder == nullptr) {
            return;
        }

        TilePosition near_tile = builder->getTilePosition();
        TilePosition build_tile = Broodwar->getBuildLocation(building_type, near_tile, 64);
        if (!build_tile.isValid()) {
            return;
        }

        builder->build(building_type, build_tile);
        return;
    }

    if (type == "train_unit") {
        UnitType train_type = UnitTypes::None;
        auto ut = sf.find("unit_type");
        if (ut != sf.end()) {
            train_type = find_unit_type_by_name(ut->second);
        }
        if (train_type == UnitTypes::None) {
            return;
        }

        Unit trainer = nullptr;
        auto tid = nf.find("unit_id");
        if (tid != nf.end()) {
            Unit explicit_unit = Broodwar->getUnit(tid->second);
            if (explicit_unit != nullptr && explicit_unit->exists() && explicit_unit->getPlayer() == Broodwar->self()) {
                trainer = explicit_unit;
            }
        }

        if (trainer == nullptr) {
            for (auto& my_unit : Broodwar->self()->getUnits()) {
                if (my_unit == nullptr || !my_unit->exists()) {
                    continue;
                }
                if (!my_unit->isCompleted() || my_unit->isTraining()) {
                    continue;
                }
                if (!my_unit->canTrain(train_type)) {
                    continue;
                }
                trainer = my_unit;
                break;
            }
        }

        if (trainer == nullptr) {
            return;
        }

        if (trainer->canTrain(train_type)) {
            trainer->train(train_type);
        }
        return;
    }

    if (type == "research_upgrade" || type == "upgrade") {
        UpgradeType upgrade_type = UpgradeTypes::None;
        auto ui = sf.find("upgrade_type");
        if (ui != sf.end()) {
            upgrade_type = find_upgrade_type_by_name(ui->second);
        }
        if (upgrade_type == UpgradeTypes::None) {
            return;
        }

        Unit upgrader = nullptr;
        auto tid = nf.find("unit_id");
        if (tid != nf.end()) {
            Unit explicit_unit = Broodwar->getUnit(tid->second);
            if (explicit_unit != nullptr && explicit_unit->exists() && explicit_unit->getPlayer() == Broodwar->self()) {
                upgrader = explicit_unit;
            }
        }

        if (upgrader == nullptr) {
            for (auto& my_unit : Broodwar->self()->getUnits()) {
                if (my_unit == nullptr || !my_unit->exists()) {
                    continue;
                }
                if (!my_unit->isCompleted()) {
                    continue;
                }
                if (!my_unit->canUpgrade(upgrade_type)) {
                    continue;
                }
                upgrader = my_unit;
                break;
            }
        }

        if (upgrader == nullptr) {
            return;
        }

        if (upgrader->canUpgrade(upgrade_type)) {
            upgrader->upgrade(upgrade_type);
        }
        return;
    }

    if (type == "placement_policy") {
        std::string plan;
        std::string expand;
        std::string wall;
        std::string proxy;
        std::string anchor;
        auto it = sf.find("plan");
        if (it != sf.end()) plan = it->second;
        it = sf.find("expand_priority");
        if (it != sf.end()) expand = it->second;
        it = sf.find("wall_policy");
        if (it != sf.end()) wall = it->second;
        it = sf.find("proxy_policy");
        if (it != sf.end()) proxy = it->second;
        it = sf.find("defensive_anchor");
        if (it != sf.end()) anchor = it->second;

        return;
    }

    auto uid_it = nf.find("unit_id");
    if (uid_it == nf.end()) {
        return;
    }

    Unit unit = Broodwar->getUnit(uid_it->second);
    if (unit == nullptr || !unit->exists() || unit->getPlayer() != Broodwar->self()) {
        return;
    }

    if (type == "worker_gather") {
        auto xi = nf.find("target_x");
        auto yi = nf.find("target_y");
        if (xi == nf.end() || yi == nf.end() || !unit->getType().isWorker()) {
            return;
        }
        Position target_pos(xi->second, yi->second);
        Unit target = nullptr;
        int best_distance = INT_MAX;
        for (auto& mineral : Broodwar->getMinerals()) {
            if (mineral == nullptr || !mineral->exists()) {
                continue;
            }
            int distance = mineral->getPosition().getApproxDistance(target_pos);
            if (distance < best_distance) {
                best_distance = distance;
                target = mineral;
            }
        }
        if (target != nullptr) {
            unit->gather(target);
        }
        return;
    }

    if (type == "worker_return") {
        if (!unit->getType().isWorker()) {
            return;
        }
        unit->returnCargo();
        return;
    }

    if (type == "worker_train") {
        if (!unit->getType().isResourceDepot() || !unit->isCompleted() || unit->isTraining()) {
            return;
        }

        auto ei = nf.find("enabled");
        if (ei != nf.end() && ei->second == 0) {
            return;
        }

        UnitType worker_type = UnitTypes::None;
        auto wt = sf.find("worker_type");
        if (wt != sf.end()) {
            worker_type = find_unit_type_by_name(wt->second);
        }
        if (worker_type == UnitTypes::None) {
            if (unit->getPlayer() != nullptr) {
                worker_type = unit->getPlayer()->getRace().getWorker();
            }
        }
        if (worker_type == UnitTypes::None) {
            return;
        }
        if (unit->canTrain(worker_type)) {
            unit->train(worker_type);
        }
        return;
    }

    if (type == "unit_stop") {
        unit->stop();
        return;
    }

    if (type == "unit_move") {
        auto xi = nf.find("x");
        auto yi = nf.find("y");
        if (xi != nf.end() && yi != nf.end()) {
            unit->move(Position(xi->second, yi->second));
        }
        return;
    }

    if (type == "unit_attack_unit") {
        auto ti = nf.find("target_unit_id");
        if (ti != nf.end()) {
            Unit target = Broodwar->getUnit(ti->second);
            if (target != nullptr && target->exists()) {
                unit->attack(target);
            }
        }
        return;
    }

    if (type == "unit_attack_move") {
        auto xi = nf.find("x");
        auto yi = nf.find("y");
        if (xi != nf.end() && yi != nf.end()) {
            unit->attack(Position(xi->second, yi->second));
        }
        return;
    }

    if (type == "worker_build") {
        if (!unit->getType().isWorker()) {
            return;
        }

        auto bi = sf.find("building_type");
        auto txi = nf.find("tile_x");
        auto tyi = nf.find("tile_y");
        if (bi == sf.end() || txi == nf.end() || tyi == nf.end()) {
            return;
        }

        UnitType building_type = find_unit_type_by_name(bi->second);
        if (building_type == UnitTypes::None || !building_type.isBuilding()) {
            return;
        }

        TilePosition build_pos(txi->second, tyi->second);
        if (!build_pos.isValid()) {
            return;
        }

        unit->build(building_type, build_pos);
        return;
    }
}
