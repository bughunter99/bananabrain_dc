// winsock2.h MUST come before windows.h / ai_dc.h to prevent
// winsock.h (pulled in by SDK 7.1a windows.h) from being included first.
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#include "ai_dc.h"

// Verify our opaque sockaddr_in storage is the right size.
static_assert(sizeof(sockaddr_in) == 16, "sockaddr_in size mismatch - update agent_addr_ array");

// Helpers to convert our opaque handles to SOCKET (unsigned int on Win32).
static inline SOCKET     to_sock(uintptr_t h)  { return static_cast<SOCKET>(h); }
static inline uintptr_t  from_sock(SOCKET s)   { return static_cast<uintptr_t>(s); }
static inline bool       sock_valid(uintptr_t h){ return h != ~uintptr_t(0); }
static inline sockaddr_in& as_sin(char (&b)[16]) { return *reinterpret_cast<sockaddr_in*>(b); }

// ---------------------------------------------------------------------------
// Minimal JSON tokenizer used only for parsing incoming action datagrams.
// We need to extract string and integer values from flat JSON objects/arrays.
// ---------------------------------------------------------------------------
namespace {

// Skip whitespace
static const char* skip_ws(const char* p) {
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') ++p;
    return p;
}

// Parse a JSON string token (cursor must be on '"').
// Returns true and sets out_value; advances *pp past the closing '"'.
static bool parse_json_string(const char** pp, std::string& out_value) {
    const char* p = *pp;
    if (*p != '"') return false;
    ++p;
    out_value.clear();
    while (*p && *p != '"') {
        if (*p == '\\') {
            ++p;
            switch (*p) {
            case '"':  out_value += '"';  break;
            case '\\': out_value += '\\'; break;
            case '/':  out_value += '/';  break;
            case 'n':  out_value += '\n'; break;
            case 'r':  out_value += '\r'; break;
            case 't':  out_value += '\t'; break;
            default:   out_value += *p;   break;
            }
        } else {
            out_value += *p;
        }
        ++p;
    }
    if (*p == '"') ++p;
    *pp = p;
    return true;
}

// Parse a JSON number (integer, possibly negative).
// Returns true; advances *pp past the number.
static bool parse_json_int(const char** pp, int& out_value) {
    const char* p = *pp;
    bool neg = false;
    if (*p == '-') { neg = true; ++p; }
    if (*p < '0' || *p > '9') return false;
    int v = 0;
    while (*p >= '0' && *p <= '9') { v = v * 10 + (*p - '0'); ++p; }
    out_value = neg ? -v : v;
    *pp = p;
    return true;
}

// Parse a flat JSON object into string and int fields.
// Nested objects/arrays are skipped.
static void parse_flat_object(const char* p,
                               std::map<std::string, std::string>& str_fields,
                               std::map<std::string, int>&         int_fields)
{
    p = skip_ws(p);
    if (*p != '{') return;
    ++p;

    while (true) {
        p = skip_ws(p);
        if (*p == '}' || *p == '\0') break;
        if (*p == ',') { ++p; continue; }

        // Key
        std::string key;
        if (!parse_json_string(&p, key)) break;
        p = skip_ws(p);
        if (*p != ':') break;
        ++p;
        p = skip_ws(p);

        // Value
        if (*p == '"') {
            std::string val;
            if (parse_json_string(&p, val)) str_fields[key] = val;
        } else if (*p == '-' || (*p >= '0' && *p <= '9')) {
            int val = 0;
            if (parse_json_int(&p, val)) int_fields[key] = val;
        } else {
            // skip nested object / array / boolean / null
            int depth = 0;
            while (*p) {
                if (*p == '{' || *p == '[') ++depth;
                else if (*p == '}' || *p == ']') { if (depth == 0) break; --depth; }
                else if ((*p == ',' || *p == '}') && depth == 0) break;
                ++p;
            }
        }
    }
}

// Parse a JSON value that is either a single object or an array of objects.
// Calls callback for each object found.
static void parse_action_json(const std::string& json,
                               std::function<void(const std::map<std::string,std::string>&,
                                                  const std::map<std::string,int>&)> cb)
{
    const char* p = skip_ws(json.c_str());

    if (*p == '[') {
        ++p;
        while (true) {
            p = skip_ws(p);
            if (*p == ']' || *p == '\0') break;
            if (*p == ',') { ++p; continue; }
            if (*p == '{') {
                // find matching '}'
                int depth = 1;
                const char* start = p;
                ++p;
                while (*p && depth > 0) {
                    if (*p == '{') ++depth;
                    else if (*p == '}') --depth;
                    else if (*p == '"') {
                        ++p;
                        while (*p && *p != '"') { if (*p == '\\') ++p; ++p; }
                    }
                    if (depth > 0 || *p == '}') ++p;
                    else break;
                }
                // p is now past the closing '}'
                std::string obj_str(start, p);
                std::map<std::string,std::string> sf;
                std::map<std::string,int> nf;
                parse_flat_object(obj_str.c_str(), sf, nf);
                cb(sf, nf);
            } else {
                ++p;
            }
        }
    } else if (*p == '{') {
        std::map<std::string,std::string> sf;
        std::map<std::string,int> nf;
        parse_flat_object(p, sf, nf);
        cb(sf, nf);
    }
}

// Convert a CP_ACP (CP949 on Korean Windows) string to UTF-8.
// Pure-ASCII strings pass through unchanged (no-op).
static std::string ansi_to_utf8(const std::string& s)
{
    if (s.empty()) return s;
    bool has_high = false;
    for (unsigned char c : s) if (c >= 0x80) { has_high = true; break; }
    if (!has_high) return s;
    int wlen = MultiByteToWideChar(CP_ACP, 0, s.c_str(), static_cast<int>(s.size()), nullptr, 0);
    if (wlen <= 0) return s;
    std::wstring wstr(wlen, L'\0');
    MultiByteToWideChar(CP_ACP, 0, s.c_str(), static_cast<int>(s.size()), &wstr[0], wlen);
    int ulen = WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), wlen, nullptr, 0, nullptr, nullptr);
    if (ulen <= 0) return s;
    std::string utf8(ulen, '\0');
    WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), wlen, &utf8[0], ulen, nullptr, nullptr);
    return utf8;
}

// Convert a UTF-8 string to CP_ACP (CP949 on Korean Windows).
// Used before passing user-supplied text to Broodwar->sendText().
static std::string utf8_to_ansi(const std::string& s)
{
    if (s.empty()) return s;
    bool has_high = false;
    for (unsigned char c : s) if (c >= 0x80) { has_high = true; break; }
    if (!has_high) return s;
    int wlen = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()), nullptr, 0);
    if (wlen <= 0) return s;
    std::wstring wstr(wlen, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()), &wstr[0], wlen);
    int alen = WideCharToMultiByte(CP_ACP, 0, wstr.c_str(), wlen, nullptr, 0, nullptr, nullptr);
    if (alen <= 0) return s;
    std::string ansi(alen, '\0');
    WideCharToMultiByte(CP_ACP, 0, wstr.c_str(), wlen, &ansi[0], alen, nullptr, nullptr);
    return ansi;
}

} // anonymous namespace

// ---------------------------------------------------------------------------
// unit_type_by_name: look up a BWAPI UnitType by its getName() string.
// UnitType has no built-in getUnitType(string) in BWAPI 4.x, so we iterate.
static UnitType unit_type_by_name(const std::string& name)
{
    for (auto& ut : UnitTypes::allUnitTypes()) {
        if (ut.getName() == name) return ut;
    }
    return UnitTypes::Unknown;
}

void MsgBusBridge::bwapi_log(const std::string& text)
{
    if (BroodwarPtr != nullptr) {
        Broodwar->printf("[MsgBus] %s", text.c_str());
    }
}

bool MsgBusBridge::start()
{
    if (running_) return true;

    // Initialise Winsock
    WSADATA wsa_data = {};
    if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
        bwapi_log("WSAStartup failed");
        return false;
    }
    wsa_started_ = true;

    // -- Send socket (used to deliver events to the external agent) ----------
    send_sock_ = from_sock(socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP));
    if (!sock_valid(send_sock_)) {
        bwapi_log("send socket creation failed");
        stop();
        return false;
    }

    // Destination: loopback:event_port
    memset(agent_addr_, 0, sizeof(agent_addr_));
    as_sin(agent_addr_).sin_family      = AF_INET;
    as_sin(agent_addr_).sin_port        = htons(static_cast<u_short>(event_port));
    as_sin(agent_addr_).sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    // -- Receive socket (listens for action datagrams from the agent) --------
    recv_sock_ = from_sock(socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP));
    if (!sock_valid(recv_sock_)) {
        bwapi_log("recv socket creation failed");
        stop();
        return false;
    }

    sockaddr_in bind_addr = {};
    bind_addr.sin_family      = AF_INET;
    bind_addr.sin_port        = htons(static_cast<u_short>(action_port));
    bind_addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    if (bind(to_sock(recv_sock_), reinterpret_cast<sockaddr*>(&bind_addr), sizeof(bind_addr)) == SOCKET_ERROR) {
        bwapi_log("bind failed on action_port " + std::to_string(action_port));
        stop();
        return false;
    }

    // Make recv_sock non-blocking so poll_actions() never stalls the game loop
    u_long mode = 1;
    ioctlsocket(to_sock(recv_sock_), FIONBIO, &mode);

    running_ = true;
    bwapi_log("UDP bridge started  event->" + std::to_string(event_port) +
              "  action<-" + std::to_string(action_port));
    return true;
}

void MsgBusBridge::stop()
{
    if (running_) {
        send_event("shutdown");
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

// ---------------------------------------------------------------------------
// send_event  -  fire-and-forget UDP sendto
// ---------------------------------------------------------------------------
void MsgBusBridge::send_event(const std::string& event_name,
                               const std::map<std::string, std::string>& payload)
{
    if (!sock_valid(send_sock_)) return;

    int frame = (BroodwarPtr != nullptr) ? Broodwar->getFrameCount() : -1;
    const std::string msg = build_message(event_name, frame, payload_to_json(payload));

    sendto(to_sock(send_sock_),
           msg.c_str(),
           static_cast<int>(msg.size()),
           0,
           reinterpret_cast<const sockaddr*>(agent_addr_),
           sizeof(sockaddr_in));
    // Ignore WSAEWOULDBLOCK / errors - fire-and-forget
}

// ---------------------------------------------------------------------------
// send_raw_event  -  like send_event but payload is already serialised JSON
// ---------------------------------------------------------------------------
void MsgBusBridge::send_raw_event(const std::string& event_name,
                                   const std::string& raw_payload_json)
{
    if (!sock_valid(send_sock_)) return;

    int frame = (BroodwarPtr != nullptr) ? Broodwar->getFrameCount() : -1;
    const std::string msg = build_message(event_name, frame, raw_payload_json);

    sendto(to_sock(send_sock_),
           msg.c_str(),
           static_cast<int>(msg.size()),
           0,
           reinterpret_cast<const sockaddr*>(agent_addr_),
           sizeof(sockaddr_in));
}

// ---------------------------------------------------------------------------
// poll_actions  -  drain all pending action datagrams (non-blocking)
//                 Call once per frame, e.g. at the start of onFrame().
// ---------------------------------------------------------------------------
void MsgBusBridge::poll_actions()
{
    if (!sock_valid(recv_sock_)) return;

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
        if (bytes == SOCKET_ERROR) break;  // WSAEWOULDBLOCK -> no more data
        buf[bytes] = '\0';
        apply_action_json(std::string(buf, bytes));
    }
}

// ---------------------------------------------------------------------------
// JSON helpers
// ---------------------------------------------------------------------------
std::string MsgBusBridge::escape_json(const std::string& raw)
{
    // Ensure any CP949 bytes from game events are emitted as valid UTF-8.
    const std::string s = ansi_to_utf8(raw);
    std::string out;
    out.reserve(s.size() + 8);
    for (char c : s) {
        switch (c) {
        case '\\': out += "\\\\"; break;
        case '"':  out += "\\\""; break;
        case '\n': out += "\\n";  break;
        case '\r': out += "\\r";  break;
        case '\t': out += "\\t";  break;
        default:   out += c;      break;
        }
    }
    return out;
}

std::string MsgBusBridge::payload_to_json(const std::map<std::string, std::string>& payload)
{
    std::string json = "{";
    bool first = true;
    for (const auto& kv : payload) {
        if (!first) json += ",";
        first = false;
        json += "\"" + escape_json(kv.first) + "\":\"" + escape_json(kv.second) + "\"";
    }
    json += "}";
    return json;
}

std::string MsgBusBridge::build_message(const std::string& event_name,
                                         int frame,
                                         const std::string& payload_json)
{
    return "{\"event\":\"" + escape_json(event_name) +
           "\",\"frame\":"  + std::to_string(frame) +
           ",\"payload\":"  + payload_json + "}";
}

// ---------------------------------------------------------------------------
// Action parsing + application
// ---------------------------------------------------------------------------
void MsgBusBridge::apply_action_json(const std::string& json)
{
    parse_action_json(json,
        [this](const std::map<std::string,std::string>& sf,
               const std::map<std::string,int>& nf) {
            auto it = sf.find("type");
            if (it == sf.end()) return;
            apply_action_object(it->second, sf, nf);
        });
}

void MsgBusBridge::apply_action_object(const std::string& type,
                                        const std::map<std::string, std::string>& sf,
                                        const std::map<std::string, int>&         nf)
{
    if (type.empty() || type == "none") return;
    if (BroodwarPtr == nullptr || Broodwar->self() == nullptr) return;

    if (type == "send_text") {
        auto it = sf.find("text");
        if (it != sf.end() && !it->second.empty()) {
            // Text arrives as UTF-8 from Python; convert to ANSI (CP949) for StarCraft.
            Broodwar->sendText("%s", utf8_to_ansi(it->second).c_str());
        }
        return;
    }

    if (type == "leave_game") {
        Broodwar->leaveGame();
        return;
    }

    if (type == "gather_minerals") {
        set_manual_mode(true);  // ensure AI does not override worker orders
        gather_workers_minerals();
        bwapi_log("gather_minerals command applied");
        return;
    }

    if (type == "scout") {
        set_manual_mode(true);
        scout_with_worker();
        bwapi_log("scout command applied");
        return;
    }

    if (type == "block_entrance") {
        set_manual_mode(true);
        block_entrance_with_workers();
        bwapi_log("block_entrance command applied");
        return;
    }

    if (type == "set_auto_play") {
        set_manual_mode(false);
        Broodwar->sendText("%s", utf8_to_ansi("[ai_dc] 자율 플레이 시작").c_str());
        bwapi_log("auto play enabled");
        return;
    }

    if (type == "set_manual") {
        set_manual_mode(true);
        Broodwar->sendText("%s", utf8_to_ansi("[ai_dc] 수동 제어 모드").c_str());
        bwapi_log("manual mode enabled");
        return;
    }

    if (type == "set_opening") {
        auto it = sf.find("opening");
        if (it != sf.end() && !it->second.empty()) {
            bool applied = force_strategy_opening(it->second);
            if (applied) {
                Broodwar->sendText("%s", utf8_to_ansi("Switch opening: " + it->second).c_str());
                bwapi_log("opening set to " + it->second);
            } else {
                bwapi_log("failed to set opening " + it->second);
            }
        }
        return;
    }

    auto uid_it = nf.find("unit_id");
    if (uid_it == nf.end()) return;
    Unit unit = Broodwar->getUnit(uid_it->second);
    if (unit == nullptr || !unit->exists() || unit->getPlayer() != Broodwar->self()) return;

    if (type == "unit_stop") {
        unit->stop();
        return;
    }

    if (type == "unit_move") {
        auto xi = nf.find("x"), yi = nf.find("y");
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
        auto xi = nf.find("x"), yi = nf.find("y");
        if (xi != nf.end() && yi != nf.end()) {
            unit->attack(Position(xi->second, yi->second));
        }
        return;
    }

    // ----- New Python-control commands -----

    if (type == "train_unit") {
        auto type_it = sf.find("unit_type");
        if (type_it != sf.end()) {
            UnitType ut = unit_type_by_name(type_it->second);
            if (ut != UnitTypes::Unknown) {
                unit->train(ut);
                bwapi_log("train_unit: " + type_it->second);
            } else {
                bwapi_log("train_unit: unknown type " + type_it->second);
            }
        }
        return;
    }

    if (type == "build") {
        auto btype_it = sf.find("building_type");
        auto tx_it = nf.find("tile_x"), ty_it = nf.find("tile_y");
        if (btype_it != sf.end() && tx_it != nf.end() && ty_it != nf.end()) {
            UnitType bt = unit_type_by_name(btype_it->second);
            if (bt != UnitTypes::Unknown) {
                unit->build(bt, TilePosition(tx_it->second, ty_it->second));
                bwapi_log("build: " + btype_it->second + " at tile " +
                          std::to_string(tx_it->second) + "," + std::to_string(ty_it->second));
            } else {
                bwapi_log("build: unknown type " + btype_it->second);
            }
        }
        return;
    }

    if (type == "gather_unit") {
        auto tgt_it = nf.find("target_id");
        if (tgt_it != nf.end()) {
            Unit target = Broodwar->getUnit(tgt_it->second);
            if (target != nullptr && target->exists()) {
                unit->gather(target);
            }
        }
        return;
    }

    if (type == "set_rally_point") {
        auto xi = nf.find("x"), yi = nf.find("y");
        if (xi != nf.end() && yi != nf.end()) {
            unit->setRallyPoint(Position(xi->second, yi->second));
        }
        return;
    }

    if (type == "find_build_location") {
        auto btype_it = sf.find("building_type");
        if (btype_it != sf.end()) {
            UnitType bt = unit_type_by_name(btype_it->second);
            if (bt != UnitTypes::Unknown) {
                auto nx_it = nf.find("near_tile_x"), ny_it = nf.find("near_tile_y");
                TilePosition near_pos = (nx_it != nf.end() && ny_it != nf.end())
                    ? TilePosition(nx_it->second, ny_it->second)
                    : Broodwar->self()->getStartLocation();
                TilePosition result = Broodwar->getBuildLocation(bt, near_pos, 40, false);
                bool ok = result.isValid();
                send_raw_event("build_location_result",
                    "{\"building_type\":\"" + escape_json(btype_it->second) + "\"" +
                    ",\"tile_x\":" + std::to_string(ok ? result.x : -1) +
                    ",\"tile_y\":" + std::to_string(ok ? result.y : -1) +
                    ",\"ok\":" + (ok ? "true" : "false") + "}");
            }
        }
        return;
    }
}
