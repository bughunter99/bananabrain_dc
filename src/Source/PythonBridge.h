#pragma once

#include <Windows.h>
#include <string>
#include <map>

struct _object;
using PyObject = _object;

class PythonEventBridge : public Singleton<PythonEventBridge>
{
public:
    bool start();
    void stop();

    void send_event(const std::string& event_name, const std::map<std::string, std::string>& payload = {});
    bool running() const { return running_; }

private:
    bool running_ = false;
    HMODULE python_dll_ = nullptr;
    PyObject* handler_ = nullptr;
    wchar_t python_home_[MAX_PATH] = {};

    struct PythonApi {
        void (__cdecl* Py_Initialize)(void) = nullptr;
        void (__cdecl* Py_SetPythonHome)(wchar_t*) = nullptr;
        int (__cdecl* Py_FinalizeEx)(void) = nullptr;
        int (__cdecl* Py_IsInitialized)(void) = nullptr;
        int (__cdecl* PyRun_SimpleStringFlags)(const char*, void*) = nullptr;

        PyObject* (__cdecl* PyImport_ImportModule)(const char*) = nullptr;
        PyObject* (__cdecl* PyObject_GetAttrString)(PyObject*, const char*) = nullptr;
        int (__cdecl* PyCallable_Check)(PyObject*) = nullptr;
        PyObject* (__cdecl* PyObject_CallObject)(PyObject*, PyObject*) = nullptr;

        PyObject* (__cdecl* PyTuple_New)(int) = nullptr;
        int (__cdecl* PyTuple_SetItem)(PyObject*, int, PyObject*) = nullptr;
        PyObject* (__cdecl* PyUnicode_FromString)(const char*) = nullptr;
        const char* (__cdecl* PyUnicode_AsUTF8)(PyObject*) = nullptr;
        PyObject* (__cdecl* PyLong_FromLong)(long) = nullptr;
        long (__cdecl* PyLong_AsLong)(PyObject*) = nullptr;

        int (__cdecl* PyObject_IsInstance)(PyObject*, PyObject*) = nullptr;
        PyObject* PyDict_Type_ = nullptr;
        PyObject* PyList_Type_ = nullptr;
        PyObject* (__cdecl* PyDict_GetItemString)(PyObject*, const char*) = nullptr;

        int (__cdecl* PyList_Size)(PyObject*) = nullptr;
        PyObject* (__cdecl* PyList_GetItem)(PyObject*, int) = nullptr;

        void (__cdecl* Py_DecRef)(PyObject*) = nullptr;
        void (__cdecl* PyErr_Print)(void) = nullptr;
            void (__cdecl* PyErr_Fetch)(PyObject**, PyObject**, PyObject**) = nullptr;
            PyObject* (__cdecl* PyObject_Str)(PyObject*) = nullptr;
    } api_;

    static std::string escape_json(const std::string& s);
    bool load_python_36();
    bool load_api();
    void close_python();

    bool dispatch_to_python(const std::string& event_name, int frame, const std::string& payload_json);
    std::string payload_to_json(const std::map<std::string, std::string>& payload) const;

    bool apply_action_object(PyObject* action_obj);
    bool apply_action_dict(PyObject* action_dict);
    bool read_dict_string(PyObject* dict_obj, const char* key, std::string& out_value) const;
    bool read_dict_int(PyObject* dict_obj, const char* key, int& out_value) const;
};
