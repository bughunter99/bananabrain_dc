#pragma once

#include <BWAPI.h>
#include <cstdint>
#include <map>
#include <string>

class MsgBusBridge
{
public:
  static MsgBusBridge& Instance();

  int event_port = 37000;
  int action_port = 37001;

  bool start();
  void stop();
  bool running() const { return running_; }

  void send_event(const std::string& event_name,
                  const std::map<std::string, std::string>& payload = {});
  void send_raw_event(const std::string& event_name,
                      const std::string& raw_payload_json);
  void poll_actions();

  static std::string escape_json(const std::string& s);

private:
  MsgBusBridge() = default;
  MsgBusBridge(const MsgBusBridge&) = delete;
  MsgBusBridge& operator=(const MsgBusBridge&) = delete;

  bool running_ = false;
  bool wsa_started_ = false;
  uintptr_t send_sock_ = ~uintptr_t(0);
  uintptr_t recv_sock_ = ~uintptr_t(0);
  char agent_addr_[16] = {};

  static std::string payload_to_json(const std::map<std::string, std::string>& payload);
  static std::string build_message(const std::string& event_name,
                                   int frame,
                                   const std::string& payload_json);

  void apply_action_json(const std::string& json);
  void apply_action_object(const std::string& type,
                           const std::map<std::string, std::string>& str_fields,
                           const std::map<std::string, int>& int_fields);
};
