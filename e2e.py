import json, time
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic, __version__
cfg=json.load(open("mc.json"))
class Logic(MachineLogic):
    def show_spinner(s,i,c,e,a): c["log"].append("show")
    def reset_error(s,i,c,e,a): c["log"].append("reset")
    def log_http_status(s,i,c,e,a): c["log"].append("http")
    def set_data(s,i,c,e,a): c["data"]=e.data
    def can_retry(s,c,e): return True
    def fetch_data(s,i,c,e): return {"ok":True}
it=SyncInterpreter(create_machine(cfg, logic=Logic())).start(); it.send("FETCH")
for _ in range(100):
    if it.matches("success"): break
    time.sleep(0.01)
assert it.matches("success") and it.context["log"]==["show","reset","http"] and it.context["data"]=={"ok":True}, (it.value, it.context)
print("E2E OK", __version__, it.value, it.context["log"])
