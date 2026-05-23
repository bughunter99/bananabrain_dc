#pragma once

// NOTE: winsock2.h is intentionally NOT included here.
// Including it in a header that other TUs pull in after BWAPI.h (which already
// brings in windows.h / winsock.h via the v141_xp SDK 7.1a) causes redefinition
// errors.  All Winsock types are confined to MsgBusBridge.cpp.

#include <cstdint>
#include <string>
#include <map>

// ---------------------------------------------------------------------------
// MsgBusBridge  -  Winsock2 UDP message bus  (replaces embedded PythonBridge)
//
// C++ (ai_dc.dll) side:
//   - sends game events to AGENT_RECV_PORT (default 37000) via UDP
//   - listens on SELF_RECV_PORT (default 37001) for action datagrams
//
// External agent side (Python / any language):
//   - binds to 127.0.0.1:37000, receives events as JSON lines
//   - sends action JSON to 127.0.0.1:37001
//
// Message format (UTF-8 JSON, fits in single UDP datagram):
//   Event  : {"event":"onFrame","frame":1234,"payload":{"key":"value",...}}
//   Action : {"type":"unit_move","unit_id":11,"x":3200,"y":2400}
//          | [{"type":"unit_move",...}, {"type":"send_text","text":"hi"}]
// ---------------------------------------------------------------------------

class MsgBusBridge : public Singleton<MsgBusBridge>
{
public:
    // Ports can be overridden before calling start()
    int event_port  = 37000;   // C++ sends events TO this port (agent listens here)
    int action_port = 37001;   // C++ receives actions ON this port (agent sends here)

    bool start();
    void stop();

    // Fire-and-forget: sends event JSON to the agent via UDP.
    void send_event(const std::string& event_name,
                    const std::map<std::string, std::string>& payload = {});

    // Fire-and-forget: sends event with a pre-built raw JSON payload object/array.
    void send_raw_event(const std::string& event_name,
                        const std::string& raw_payload_json);

    // Drain incoming action datagrams and apply them; call once per frame.
    void poll_actions();

    bool running() const { return running_; }

    // Public so ai_dc.cpp can use it when building raw JSON payloads.
    static std::string escape_json(const std::string& s);

private:
    bool      running_      = false;
    bool      wsa_started_  = false;
    // SOCKET on Win32 == unsigned int; stored as uintptr_t to avoid winsock2 in header
    uintptr_t send_sock_    = ~uintptr_t(0);  // INVALID_SOCKET
    uintptr_t recv_sock_    = ~uintptr_t(0);
    char      agent_addr_[16] = {};           // opaque storage for sockaddr_in (16 bytes)
    static std::string payload_to_json(const std::map<std::string, std::string>& payload);
    static std::string build_message(const std::string& event_name,
                                     int frame,
                                     const std::string& payload_json);

    void apply_action_json(const std::string& json);
    void apply_action_object(const std::string& type,
                             const std::map<std::string, std::string>& str_fields,
                             const std::map<std::string, int>&         int_fields);

    static void bwapi_log(const std::string& text);
};
