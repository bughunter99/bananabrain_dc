#include "BananaBrain.h"
#include "PythonBridge.h"

namespace {
template <typename T>
bool load_symbol(HMODULE module, const char* name, T& out_fn)
{
    out_fn = reinterpret_cast<T>(GetProcAddress(module, name));
    return out_fn != nullptr;
}

std::string make_python36_user_path()
{
    char local_app_data[MAX_PATH] = {};
    DWORD len = GetEnvironmentVariableA("LOCALAPPDATA", local_app_data, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) return "";
    return std::string(local_app_data) + "\\Programs\\Python\\Python36-32\\python36.dll";
}

void bwapi_log(const std::string& text)
{
    if (BroodwarPtr != nullptr) {
        Broodwar->printf("[PythonBridge] %s", text.c_str());
    }
}
}

bool PythonEventBridge::start()
{
    if (running_) return true;

    if (!load_python_36()) {
        bwapi_log("python36.dll not found");
        close_python();
        return false;
    }

    if (!load_api()) {
        bwapi_log("Failed to resolve Python C API symbols");
        close_python();
        return false;
    }

    // Set Python home to the directory where python36.dll was loaded from,
    // so Py_Initialize can find the standard library (avoids abort on Windows 7).
    {
        char dll_path[MAX_PATH] = {};
        if (GetModuleFileNameA(python_dll_, dll_path, MAX_PATH) > 0) {
            char* last_slash = strrchr(dll_path, '\\');
            if (last_slash) *last_slash = '\0';
            MultiByteToWideChar(CP_ACP, 0, dll_path, -1, python_home_, MAX_PATH);
            api_.Py_SetPythonHome(python_home_);
        }
    }

    api_.Py_Initialize();
    if (api_.Py_IsInitialized() == 0) {
        bwapi_log("Py_Initialize failed");
        close_python();
        return false;
    }

    // Set up sys.path: relative paths for standard BWAPI layout + absolute path from DLL location
    api_.PyRun_SimpleStringFlags("import sys", nullptr);
    api_.PyRun_SimpleStringFlags("sys.path.append('bwapi-data/AI/python')", nullptr);
    api_.PyRun_SimpleStringFlags("sys.path.append('AI/python')", nullptr);
    {
        char bot_dll_path[MAX_PATH] = {};
        HMODULE bot_module = GetModuleHandleA("BananaBrain.dll");
        if (bot_module && GetModuleFileNameA(bot_module, bot_dll_path, MAX_PATH) > 0) {
            char* last_slash = strrchr(bot_dll_path, '\\');
            if (last_slash) {
                *last_slash = '\0';
                std::string abs_path = std::string(bot_dll_path) + "\\python";
                std::string py_cmd = std::string("sys.path.append('") + abs_path + "')";
                for (char& c : py_cmd) { if (c == '\\') c = '/'; }
                api_.PyRun_SimpleStringFlags(py_cmd.c_str(), nullptr);
                bwapi_log(std::string("Bot DLL dir: ") + bot_dll_path);
            }
        }
    }

    PyObject* module = api_.PyImport_ImportModule("embedded_agent");
    if (module == nullptr) {
        if (api_.PyErr_Fetch && api_.PyObject_Str && api_.PyUnicode_AsUTF8) {
            PyObject *ptype = nullptr, *pvalue = nullptr, *ptb = nullptr;
            api_.PyErr_Fetch(&ptype, &pvalue, &ptb);
            if (pvalue) {
                PyObject* pstr = api_.PyObject_Str(pvalue);
                if (pstr) {
                    const char* msg = api_.PyUnicode_AsUTF8(pstr);
                    if (msg) bwapi_log(std::string("Python: ") + msg);
                    api_.Py_DecRef(pstr);
                }
                api_.Py_DecRef(pvalue);
            }
            if (ptype) api_.Py_DecRef(ptype);
            if (ptb) api_.Py_DecRef(ptb);
        }
        bwapi_log("Cannot import embedded_agent from AI/python");
        close_python();
        return false;
    }

    handler_ = api_.PyObject_GetAttrString(module, "handle_event");
    api_.Py_DecRef(module);

    if (handler_ == nullptr || api_.PyCallable_Check(handler_) == 0) {
        if (handler_ != nullptr) {
            api_.Py_DecRef(handler_);
            handler_ = nullptr;
        }
        bwapi_log("embedded_agent.handle_event is missing or not callable");
        close_python();
        return false;
    }

    running_ = true;
    return true;
}

void PythonEventBridge::stop()
{
    if (!running_) {
        close_python();
        return;
    }

    send_event("shutdown");
    close_python();
    running_ = false;
}

void PythonEventBridge::send_event(const std::string& event_name, const std::map<std::string, std::string>& payload)
{
    if (!running_ || handler_ == nullptr) return;

    int frame = -1;
    if (BroodwarPtr != nullptr) {
        frame = Broodwar->getFrameCount();
    }

    const std::string payload_json = payload_to_json(payload);
    if (!dispatch_to_python(event_name, frame, payload_json)) {
        api_.PyErr_Print();
        bwapi_log("Python callback failed, bridge stopped");
        running_ = false;
        close_python();
    }
}

std::string PythonEventBridge::escape_json(const std::string& s)
{
    std::string out;
    out.reserve(s.size() + 8);

    for (char c : s) {
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

bool PythonEventBridge::load_python_36()
{
    const std::vector<std::string> dll_candidates = {
        "python36.dll",
        make_python36_user_path()
    };

    for (const auto& candidate : dll_candidates) {
        if (candidate.empty()) continue;
        HMODULE module = LoadLibraryA(candidate.c_str());
        if (module != nullptr) {
            python_dll_ = module;
            return true;
        }
    }

    return false;
}

bool PythonEventBridge::load_api()
{
    if (python_dll_ == nullptr) return false;

    const bool ok =
        load_symbol(python_dll_, "Py_Initialize", api_.Py_Initialize) &&
        load_symbol(python_dll_, "Py_SetPythonHome", api_.Py_SetPythonHome) &&
        load_symbol(python_dll_, "Py_FinalizeEx", api_.Py_FinalizeEx) &&
        load_symbol(python_dll_, "Py_IsInitialized", api_.Py_IsInitialized) &&
        load_symbol(python_dll_, "PyRun_SimpleStringFlags", api_.PyRun_SimpleStringFlags) &&
        load_symbol(python_dll_, "PyImport_ImportModule", api_.PyImport_ImportModule) &&
        load_symbol(python_dll_, "PyObject_GetAttrString", api_.PyObject_GetAttrString) &&
        load_symbol(python_dll_, "PyCallable_Check", api_.PyCallable_Check) &&
        load_symbol(python_dll_, "PyObject_CallObject", api_.PyObject_CallObject) &&
        load_symbol(python_dll_, "PyTuple_New", api_.PyTuple_New) &&
        load_symbol(python_dll_, "PyTuple_SetItem", api_.PyTuple_SetItem) &&
        load_symbol(python_dll_, "PyUnicode_FromString", api_.PyUnicode_FromString) &&
        load_symbol(python_dll_, "PyUnicode_AsUTF8", api_.PyUnicode_AsUTF8) &&
        load_symbol(python_dll_, "PyLong_FromLong", api_.PyLong_FromLong) &&
        load_symbol(python_dll_, "PyLong_AsLong", api_.PyLong_AsLong) &&
        load_symbol(python_dll_, "PyObject_IsInstance", api_.PyObject_IsInstance) &&
        load_symbol(python_dll_, "PyDict_GetItemString", api_.PyDict_GetItemString) &&
        load_symbol(python_dll_, "PyList_Size", api_.PyList_Size) &&
        load_symbol(python_dll_, "PyList_GetItem", api_.PyList_GetItem) &&
    load_symbol(python_dll_, "Py_DecRef", api_.Py_DecRef) &&
    load_symbol(python_dll_, "PyErr_Print", api_.PyErr_Print) &&
    load_symbol(python_dll_, "PyErr_Fetch", api_.PyErr_Fetch) &&
    load_symbol(python_dll_, "PyObject_Str", api_.PyObject_Str);

    if (!ok) return false;

    // PyDict_Type and PyList_Type are data symbols (not functions) - load as raw pointers
    api_.PyDict_Type_ = reinterpret_cast<PyObject*>(GetProcAddress(python_dll_, "PyDict_Type"));
    api_.PyList_Type_ = reinterpret_cast<PyObject*>(GetProcAddress(python_dll_, "PyList_Type"));
    if (api_.PyDict_Type_ == nullptr || api_.PyList_Type_ == nullptr) return false;

    return true;
}

void PythonEventBridge::close_python()
{
    if (handler_ != nullptr && api_.Py_DecRef != nullptr) {
        api_.Py_DecRef(handler_);
        handler_ = nullptr;
    }

    if (api_.Py_IsInitialized != nullptr && api_.Py_IsInitialized() != 0 && api_.Py_FinalizeEx != nullptr) {
        api_.Py_FinalizeEx();
    }

    api_ = {};

    if (python_dll_ != nullptr) {
        FreeLibrary(python_dll_);
        python_dll_ = nullptr;
    }
}

std::string PythonEventBridge::payload_to_json(const std::map<std::string, std::string>& payload) const
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

bool PythonEventBridge::dispatch_to_python(const std::string& event_name, int frame, const std::string& payload_json)
{
    PyObject* args = api_.PyTuple_New(3);
    if (args == nullptr) return false;

    PyObject* py_event = api_.PyUnicode_FromString(event_name.c_str());
    PyObject* py_frame = api_.PyLong_FromLong(frame);
    PyObject* py_payload = api_.PyUnicode_FromString(payload_json.c_str());

    if (py_event == nullptr || py_frame == nullptr || py_payload == nullptr) {
        if (py_event != nullptr) api_.Py_DecRef(py_event);
        if (py_frame != nullptr) api_.Py_DecRef(py_frame);
        if (py_payload != nullptr) api_.Py_DecRef(py_payload);
        api_.Py_DecRef(args);
        return false;
    }

    api_.PyTuple_SetItem(args, 0, py_event);
    api_.PyTuple_SetItem(args, 1, py_frame);
    api_.PyTuple_SetItem(args, 2, py_payload);

    PyObject* result = api_.PyObject_CallObject(handler_, args);
    api_.Py_DecRef(args);

    if (result == nullptr) return false;

    const bool ok = apply_action_object(result);
    api_.Py_DecRef(result);
    return ok;
}

bool PythonEventBridge::apply_action_object(PyObject* action_obj)
{
    if (action_obj == nullptr) return true;

    if (api_.PyObject_IsInstance(action_obj, api_.PyDict_Type_) != 0) {
        return apply_action_dict(action_obj);
    }

    if (api_.PyObject_IsInstance(action_obj, api_.PyList_Type_) != 0) {
        int count = api_.PyList_Size(action_obj);
        for (int i = 0; i < count; ++i) {
            PyObject* item = api_.PyList_GetItem(action_obj, i);
            if (item != nullptr && api_.PyObject_IsInstance(item, api_.PyDict_Type_) != 0) {
                if (!apply_action_dict(item)) return false;
            }
        }
        return true;
    }

    return true;
}

bool PythonEventBridge::read_dict_string(PyObject* dict_obj, const char* key, std::string& out_value) const
{
    PyObject* value = api_.PyDict_GetItemString(dict_obj, key);
    if (value == nullptr) return false;

    const char* text = api_.PyUnicode_AsUTF8(value);
    if (text == nullptr) return false;

    out_value = text;
    return true;
}

bool PythonEventBridge::read_dict_int(PyObject* dict_obj, const char* key, int& out_value) const
{
    PyObject* value = api_.PyDict_GetItemString(dict_obj, key);
    if (value == nullptr) return false;

    out_value = static_cast<int>(api_.PyLong_AsLong(value));
    return true;
}

bool PythonEventBridge::apply_action_dict(PyObject* action_dict)
{
    if (BroodwarPtr == nullptr || Broodwar->self() == nullptr) return true;

    std::string type;
    if (!read_dict_string(action_dict, "type", type) || type.empty() || type == "none") {
        return true;
    }

    if (type == "send_text") {
        std::string text;
        if (read_dict_string(action_dict, "text", text) && !text.empty()) {
            Broodwar->sendText("%s", text.c_str());
        }
        return true;
    }

    if (type == "leave_game") {
        Broodwar->leaveGame();
        return true;
    }

    int unit_id = -1;
    if (!read_dict_int(action_dict, "unit_id", unit_id)) return true;

    Unit unit = Broodwar->getUnit(unit_id);
    if (unit == nullptr || !unit->exists() || unit->getPlayer() != Broodwar->self()) {
        return true;
    }

    if (type == "unit_stop") {
        unit->stop();
        return true;
    }

    if (type == "unit_move") {
        int x = 0;
        int y = 0;
        if (!read_dict_int(action_dict, "x", x) || !read_dict_int(action_dict, "y", y)) return true;
        unit->move(Position(x, y));
        return true;
    }

    if (type == "unit_attack_unit") {
        int target_id = -1;
        if (!read_dict_int(action_dict, "target_unit_id", target_id)) return true;

        Unit target = Broodwar->getUnit(target_id);
        if (target != nullptr && target->exists()) {
            unit->attack(target);
        }
        return true;
    }

    if (type == "unit_attack_move") {
        int x = 0;
        int y = 0;
        if (!read_dict_int(action_dict, "x", x) || !read_dict_int(action_dict, "y", y)) return true;
        unit->attack(Position(x, y));
        return true;
    }

    return true;
}
