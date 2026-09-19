import asyncio, threading, warnings
from xstate_statemachine import Interpreter, MachineLogic, create_machine
warnings.simplefilter("ignore")
async def main():
    i = Interpreter(create_machine({"id":"m","initial":"a","states":{"a":{"on":{"F":"b"}},"b":{}}})); await i.start()
    loop = asyncio.get_running_loop(); res = {}
    def w():
        try: asyncio.run_coroutine_threadsafe(i.send("F"), loop).result(1); res["37"]="ok"
        except Exception as e: res["37"]=f"raised {type(e).__name__}"
    t=threading.Thread(target=w); t.start()
    for _ in range(20): await asyncio.sleep(0.01)
    t.join(); print("37 run_coroutine_threadsafe(send):", res["37"]); await i.stop()
    # 51-2: strict typo inside raise under default continue
    cfg={"id":"s","initial":"a","strict":True,"states":{"a":{"on":{"GO":{"target":"b","actions":[{"type":"raise","params":{"event":"TYPO"}}]}}},"b":{}}}
    j = Interpreter(create_machine(cfg), strict=True); await j.start()
    try:
        await j.send("GO"); await asyncio.sleep(0.05)
        print("51-2 typo'd raise under continue:", f"state={sorted(j.current_state_ids)} status={j.status} last_ok={j.last_transition_ok}")
    except Exception as e: print("51-2 raised", type(e).__name__)
    await j.stop()
asyncio.run(main())
