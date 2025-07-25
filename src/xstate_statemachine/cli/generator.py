# src/xstate_statemachine/cli/generator.py
# -----------------------------------------------------------------------------
# 📝 Code Generation
# -----------------------------------------------------------------------------
# This module is the "factory" for the CLI. It contains the functions
# responsible for generating the Python source code for both the logic and
# runner files. It takes the extracted data (actions, guards, services) and
# user-defined options to construct PEP 8-compliant, type-safe, and
# warning-free boilerplate code.
# -----------------------------------------------------------------------------
"""
Core code generation logic for the xstate-statemachine CLI.
"""
# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import keyword
from typing import Any, Dict, List, Set

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .extractor import extract_events
from .utils import camel_to_snake


def generate_logic_code(  # noqa: C901
    actions: Set[str],
    guards: Set[str],
    services: Set[str],
    style: str,
    log: bool,
    is_async: bool,
    machine_name: str,
    file_count: int,
) -> str:
    """Return the source for ``*_logic.py`` generated from a machine definition."""
    # ------------------------------------------------------------------
    # 📑  Imports & logger
    # ------------------------------------------------------------------
    file_title = (
        "# 📡 Generated Logic File"
        if file_count != 1
        else "# 📡 Generated File"
    )
    header: List[str] = [
        "# -------------------------------------------------------------------------------",
        f"{file_title}",
        "# -------------------------------------------------------------------------------",
        "",
    ]
    if is_async:
        header += ["import asyncio", "from typing import Awaitable"]

    header += [
        *(["import time"] if (services and not is_async) else []),
        "from typing import Any, Dict, Union",
        "",
        "from xstate_statemachine import Interpreter, SyncInterpreter, Event, ActionDefinition",
        "",
        "",
    ]

    if log:
        header.append("import logging")
        header.append("")
        header.append(
            "# -----------------------------------------------------------------------------"
        )
        header.append("#🧾Logger Configuration")
        header.append(
            "# -----------------------------------------------------------------------------"
        )
        header.append("logger = logging.getLogger(__name__)")
        header.append("")

    # ------------------------------------------------------------------
    # Helper – camelCase → snake_case
    # ------------------------------------------------------------------
    _snake = camel_to_snake

    # ------------------------------------------------------------------
    # Class / module boilerplate
    # ------------------------------------------------------------------
    indent_cls = ""
    body: List[str] = []

    if style == "class":
        class_name = (
            "".join(p.capitalize() for p in machine_name.split("_")) + "Logic"
        )
        body += [
            "# -----------------------------------------------------------------------------",
            "# 🧠 Class‑based Logic",
            "# -----------------------------------------------------------------------------",
            f"class {class_name}:",
        ]
        indent_cls = "    "

    # ------------------------------------------------------------------
    # ⚙️  ACTIONS
    # ------------------------------------------------------------------
    if actions:
        body.append(f"{indent_cls}# ⚙️ Actions")
        for original in sorted(actions):
            fn = _snake(original)
            async_kw = "async " if is_async else ""
            ret = "Awaitable[None]" if is_async else "None"

            body += [
                f"{indent_cls}{async_kw}def {fn}(  # noqa: ignore IDE static method warning,"
            ]
            if style == "class":
                body.append(f"{indent_cls}        self,")
            body += [
                f"{indent_cls}        interpreter: Union[Interpreter, SyncInterpreter],",
                f"{indent_cls}        context: Dict[str, Any],",
                f"{indent_cls}        event: Event,",
                f"{indent_cls}        action_def: ActionDefinition,  # noqa: D401 – lib callback",
                f"{indent_cls}) -> {ret}:  # noqa : ignore IDE return type hint warning",
                f'{indent_cls}    """Action: `{original}`."""',
            ]
            if log:
                body.append(
                    f'{indent_cls}    logger.info("Executing action {original}")'
                )
            if is_async:
                body.append(
                    f"{indent_cls}    await asyncio.sleep(0.1)  # placeholder"
                )
            body.append(f"{indent_cls}    # TODO: implement\n")

    # ------------------------------------------------------------------
    # 🛡️  GUARDS
    # ------------------------------------------------------------------
    if guards:
        body.append(f"{indent_cls}# 🛡️ Guards")
        for original in sorted(guards):
            fn = _snake(original)
            body += [
                f"{indent_cls}def {fn}(",
            ]
            if style == "class":
                body.append(f"{indent_cls}        self,")
            body += [
                f"{indent_cls}        context: Dict[str, Any],",
                f"{indent_cls}        event: Event,",
                f"{indent_cls}) -> bool:",
                f'{indent_cls}    """Guard: `{original}`."""',
            ]
            if log:
                body.append(
                    f'{indent_cls}    logger.info("Evaluating guard {original}")'
                )
            body.append(
                f"{indent_cls}    # TODO: implement guard logic\n"
                f"{indent_cls}    return True\n"
            )

    # ------------------------------------------------------------------
    # 🔄  SERVICES
    # ------------------------------------------------------------------
    if services:
        body.append(f"{indent_cls}# 🔄 Services")
        for original in sorted(services):
            fn = _snake(original)
            if keyword.iskeyword(fn):
                fn = f"{fn}_"

            async_kw = "async " if is_async else ""
            ret = "Awaitable[Dict[str, Any]]" if is_async else "Dict[str, Any]"

            body += [
                f"{indent_cls}{async_kw}def {fn}(  # noqa: ignore IDE static method warning,"
            ]
            if style == "class":
                body.append(f"{indent_cls}        self,")
            body += [
                f"{indent_cls}        interpreter: Union[Interpreter, SyncInterpreter],",
                f"{indent_cls}        context: Dict[str, Any],",
                f"{indent_cls}        event: Event,",
                f"{indent_cls}) -> {ret}:",
                f'{indent_cls}    """Service: `{original}`."""',
            ]
            if log:
                body.append(
                    f'{indent_cls}    logger.info("Running service {original}")'
                )
            if is_async:
                body.append(f"{indent_cls}    await asyncio.sleep(1)")
            else:
                body.append(f"{indent_cls}    time.sleep(1)")
            body.append(
                f"{indent_cls}    # TODO: implement service\n"
                f"{indent_cls}    return {{'result': 'done'}}  # noqa : ignore IDE return type hint warning\n"
            )
            if fn != original:
                body.append(
                    f"{indent_cls}{original} = {fn}  # alias for JSON name\n"
                )

    return "\n".join(header + body)


def generate_runner_code(  # noqa: C901 – function is long but readable
    machine_names: List[str],
    is_async: bool,
    style: str,
    loader: bool,
    sleep: bool,
    sleep_time: int,
    log: bool,
    file_count: int,
    configs: List[Dict[str, Any]],
    json_filenames: List[str],
    hierarchy: bool = False,  # NEW ▸ treat first machine as parent
) -> str:
    """Generates the runner file content to execute the state machine(s).

    The function builds the code for the runner module (``*_runner.py``).
    It now supports two operating modes:

    * **Flat / legacy** – every JSON is an independent machine (old behaviour).
    * **Hierarchy** – the *first* machine in *machine_names* is considered the
      **parent**; all remaining machines are actor definitions that can be
      spawned by the parent (selected when *hierarchy* is ``True``).

    Args:
        machine_names:     snake‑cased machine identifiers (order matters).
        is_async:          generate an asynchronous runner if ``True``.
        style:             'class' or 'function' logic style.
        loader:            use auto‑discovery logic loader when ``True``.
        sleep:             insert ``time.sleep`` / ``asyncio.sleep`` calls?
        sleep_time:        seconds to sleep between simulated events.
        log:               configure basic logging output.
        file_count:        1 → combined file, 2 → separate logic/runner files.
        configs:           list with the parsed JSON machine configs.
        json_filenames:    filenames of the original JSON files (same order).
        hierarchy:         **NEW**; when ``True`` treat list as parent+actors.

    Returns:
        The generated Python source code as a single string.
    """
    # ------------------------------------------------------------------
    # 📄  Preamble & imports
    # ------------------------------------------------------------------

    # 📛 Runner imports must match the file names chosen in `main()`
    if hierarchy and len(machine_names) > 1:
        base_name = machine_names[0]  # parent only
    else:
        base_name = (
            "_".join(machine_names)
            if len(machine_names) > 1
            else machine_names[0]
        )
    logic_file_name = f"{base_name}_logic"  # defined unconditionally

    class_name = (
        "".join(word.capitalize() for word in base_name.split("_")) + "Logic"
    )

    code_lines = [
        "# -------------------------------------------------------------------------------",
        "# 📡 Generated Runner File",
        "# -------------------------------------------------------------------------------",
        "from pathlib import Path",
        "from xstate_statemachine import LoggingInspector",
        # add MachineLogic **only** when we plan to emit the stub (loader disabled *and* function‑style)
        "from xstate_statemachine import create_machine, "
        + ("Interpreter" if is_async else "SyncInterpreter")
        + (", MachineLogic" if (not loader and style == "function") else ""),
        "import json",
    ]
    if log:
        code_lines.append("import logging")
    if sleep and not is_async:
        code_lines.append("import time")
    if is_async:
        code_lines.append("import asyncio")
    code_lines.append("")

    if log:
        if file_count != 1:
            code_lines.append("")
            code_lines.append(
                "# -----------------------------------------------------------------------------"
            )
            code_lines.append("# 🧾 Logger Configuration")
            code_lines.append(
                "# -----------------------------------------------------------------------------"
            )
            code_lines.append("")

        code_lines.extend(
            [
                "logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')",
                "logger = logging.getLogger(__name__)",
                "",
            ]
        )

    # ------------------------------------------------------------------
    # 🧩  Import generated *logic* module (when we have two files)
    # ------------------------------------------------------------------
    if file_count == 2:
        if style == "class":
            code_lines.append(
                f"from {logic_file_name} import {class_name} as LogicProvider"
            )
        else:
            code_lines.append(f"import {logic_file_name}")
        code_lines.append("")
        code_lines.append("")

    func_prefix = "async " if is_async else ""
    await_prefix = "await " if is_async else ""
    sleep_cmd = "await asyncio.sleep" if is_async else "time.sleep"

    # ==================================================================
    # 👑  MODE 1 – Hierarchical (parent + actors)
    # ==================================================================
    if hierarchy and len(machine_names) > 1:
        parent_name, *actor_names = machine_names
        parent_json, *actor_jsons = json_filenames
        parent_cfg = configs[0]

        code_lines.extend(
            [
                f"{func_prefix}def main() -> None:",
                '    """Run the *parent* machine together with all actor machines.\n\n'
                "    The runner will:\n"
                "      1. load every JSON config,\n"
                "      2. start the parent interpreter (with logic bound if requested),\n"
                "      3. start an interpreter for **each** actor,\n"
                "      4. replay *all* events discovered in every machine to exercise\n"
                "         every transition path (best‑effort 100 % coverage),\n"
                "      5. stop all interpreters gracefully.\n"
                '    """',
                "",
                "    root_dir = Path(__file__).parent",
                f"    parent_cfg = json.loads((root_dir / '{parent_json}').read_text())",
                "    actor_cfgs = {",
            ]
            + [
                f"        '{actor_names[idx]}': json.loads((root_dir / '{jfn}').read_text()),"
                for idx, jfn in enumerate(actor_jsons)
            ]
            + [
                "    }",
                "",
                "    # -----------------------------------------------------------------------",
                "    # 🧠 Parent machine + logic binding",
                "    # -----------------------------------------------------------------------",
            ]
        )

        # FIX: Ensure logic is always bound in class-style hierarchy mode,
        # regardless of the --loader flag.
        if style == "class":
            if file_count == 1:
                code_lines.append(f"    logic_provider = {class_name}()")
            else:
                code_lines.append("    logic_provider = LogicProvider()")
            code_lines.append(
                "    parent_machine = create_machine(parent_cfg, logic_providers=[logic_provider])"
            )
        else:  # function style – ALWAYS bind the logic module explicitly
            if file_count == 2:
                code_lines.append(
                    f"    parent_machine = create_machine(parent_cfg, logic_modules=[{logic_file_name}])"
                )
            else:  # file_count == 1
                code_lines.append("    import sys")
                code_lines.append(
                    "    parent_machine = create_machine(parent_cfg, logic_modules=[sys.modules[__name__]])"
                )

        parent_ctor = "Interpreter" if is_async else "SyncInterpreter"
        code_lines.extend(
            [
                f"    parent = {parent_ctor}(parent_machine)",
                "    parent.use(LoggingInspector())",
                f"    {await_prefix}parent.start()",
                "    logger.info('Parent started – initial state(s): %s', parent.current_state_ids)",
                "",
                "    # -------------------------------------------------------------------",
                "    # 🎭 Spawn & start every actor interpreter",
                "    # -------------------------------------------------------------------",
                f"    actor_ctor = {parent_ctor}  # same sync/async flavour",
                "    actors = {}  # id → interpreter",
            ]
        )

        for a_name in actor_names:
            code_lines.extend(
                [
                    f"    machine_{a_name} = create_machine(actor_cfgs['{a_name}'])",
                    f"    ai_{a_name} = actor_ctor(machine_{a_name})",
                    f"    ai_{a_name}.use(LoggingInspector())",
                    f"    {await_prefix}ai_{a_name}.start()",
                    f"    actors['{a_name}'] = ai_{a_name}",
                ]
            )

        # ---------------------------------------------------------------- Events replay – parent
        code_lines.extend(
            [
                "",
                "    # -------------------------------------------------------------------",
                "    # 🚀 Simulating Parent Machine",
                "    # -------------------------------------------------------------------",
            ]
        )
        parent_events = sorted(extract_events(parent_cfg))
        if parent_events:
            for ev in parent_events:
                human = ev.replace("_", " ").title()
                code_lines.append(f"    # {human}")
                if log:
                    code_lines.append(
                        f"    logger.info('Parent → sending %s', '{ev}')"
                    )
                code_lines.append(f"    {await_prefix}parent.send('{ev}')")
                if sleep:
                    code_lines.append(f"    {sleep_cmd}({sleep_time})")
                code_lines.append("")
        else:
            code_lines.append(
                "    logger.info('No events declared in parent machine.')"
            )
            code_lines.append("")

        # ---------------------------------------------------------------- Events replay – actors
        for idx, a_name in enumerate(actor_names):
            actor_events = sorted(extract_events(configs[idx + 1]))
            code_lines.extend(
                [
                    "    # -------------------------------------------------------------------",
                    f"    # 🚀 Simulating Actor «{a_name}»",
                    "    # -------------------------------------------------------------------",
                ]
            )
            if actor_events:
                for ev in actor_events:
                    human = ev.replace("_", " ").title()
                    code_lines.append(f"    # {human}")
                    if log:
                        code_lines.append(
                            f"    logger.info('{a_name} → sending %s', '{ev}')"
                        )
                    code_lines.append(
                        f"    {await_prefix}actors['{a_name}'].send('{ev}')"
                    )
                    if sleep:
                        code_lines.append(f"    {sleep_cmd}({sleep_time})")
                    code_lines.append("")
            else:
                code_lines.append(
                    f"    logger.info('No events declared in actor \"{a_name}\".')"
                )
                code_lines.append("")

        # ---------------------------------------------------------------- Shutdown
        code_lines.extend(
            [
                "    # -------------------------------------------------------------------",
                "    # 🛑 Graceful shutdown of actors then parent",
                "    # -------------------------------------------------------------------",
            ]
        )
        for a_name in actor_names:
            code_lines.append(f"    {await_prefix}actors['{a_name}'].stop()")
        code_lines.append(f"    {await_prefix}parent.stop()")
        code_lines.append("")
        if is_async:
            code_lines.extend(
                [
                    "if __name__ == '__main__':",
                    "    asyncio.run(main())",
                ]
            )
        else:
            code_lines.extend(
                [
                    "if __name__ == '__main__':",
                    "    main()",
                ]
            )

        return "\n".join(code_lines)

    # ==================================================================
    # 🟰  MODE 2 – Flat / legacy
    # ==================================================================
    if len(machine_names) == 1:
        # ------------------------------------------------------------------
        # 🐟  Single‑machine runner
        # ------------------------------------------------------------------
        name = machine_names[0]
        config = configs[0]
        json_filename = json_filenames[0]
        events = sorted(extract_events(config))

        code_lines.append(f"{func_prefix}def main() -> None:")
        inner_indent = "    "

        cfg_lines = [
            f'{inner_indent}config_path = Path(r"{json_filename}")',
            f"{inner_indent}if not config_path.is_absolute() and config_path.parent == Path('.'):",
            f"{inner_indent}    here = Path(__file__).resolve().parent",
            f"{inner_indent}    candidate = here / config_path.name",
            f"{inner_indent}    config_path = candidate if candidate.exists() else here.parent / config_path.name",
        ]

        code_lines += [
            f'{inner_indent}"""Executes the simulation for the {name} machine."""',
            "",
            f"{inner_indent}# ---------------------------------------------------------------------------",
            f"{inner_indent}# 📂 1. Configuration Loading",
            f"{inner_indent}# ---------------------------------------------------------------------------",
            *cfg_lines,
            f"{inner_indent}with open(config_path, 'r', encoding='utf-8') as f:",
            f"{inner_indent}    config = json.load(f)",
            "",
            f"{inner_indent}# ---------------------------------------------------------------------------",
            f"{inner_indent}# 🧠 2. Logic Binding",
            f"{inner_indent}# ---------------------------------------------------------------------------",
        ]

        # ------------------------ logic binding ---------------------------------
        if loader:  # 🔍 auto‑discovery ON
            if style == "class":
                # → class provider instance (auto‑loader inspects it)
                if file_count == 1:
                    code_lines.append(
                        f"{inner_indent}logic_provider = {class_name}()"
                    )
                else:
                    code_lines.append(
                        f"{inner_indent}logic_provider = LogicProvider()"
                    )
                code_lines.append(
                    f"{inner_indent}machine = create_machine(config, logic_providers=[logic_provider])"
                )
            else:  # function style  – auto‑loader inspects module(s)
                if file_count == 1:
                    code_lines += [
                        f"{inner_indent}import sys",
                        f"{inner_indent}machine = create_machine(config, logic_modules=[sys.modules[__name__]])",
                    ]
                else:
                    code_lines.append(
                        f"{inner_indent}machine = create_machine(config, logic_modules=[{logic_file_name}])"
                    )
        else:  # 📴 auto‑discovery OFF → bind logic **explicitly**
            if style == "class":
                if file_count == 1:
                    code_lines.append(
                        f"{inner_indent}logic_provider = {class_name}()"
                    )
                else:
                    code_lines.append(
                        f"{inner_indent}logic_provider = LogicProvider()"
                    )
                code_lines.append(
                    f"{inner_indent}machine = create_machine(config, logic_providers=[logic_provider])"
                )
            else:  # function style – pass the module explicitly
                if file_count == 1:
                    code_lines += [
                        f"{inner_indent}import sys",
                        f"{inner_indent}machine = create_machine(config, logic_modules=[sys.modules[__name__]])",
                    ]
                else:
                    code_lines.append(
                        f"{inner_indent}machine = create_machine(config, logic_modules=[{logic_file_name}])"
                    )

        # ------------------------ interpreter setup -----------------------------
        code_lines += [
            "",
            f"{inner_indent}# ---------------------------------------------------------------------------",
            f"{inner_indent}# ⚙️  3. Interpreter Setup",
            f"{inner_indent}# ---------------------------------------------------------------------------",
        ]
        interp_type = (
            "Interpreter(machine)" if is_async else "SyncInterpreter(machine)"
        )
        code_lines += [
            f"{inner_indent}interpreter = {interp_type}",
            f"{inner_indent}interpreter.use(LoggingInspector())",
            f"{inner_indent}{await_prefix}interpreter.start()",
        ]

        if log:
            code_lines.append(
                f"{inner_indent}logger.info(f'Initial state: {{interpreter.current_state_ids}}')",
            )

        code_lines += [
            "",
            f"{inner_indent}# ---------------------------------------------------------------------------",
            f"{inner_indent}# 🚀 4. Simulation Scenario",
            f"{inner_indent}# ---------------------------------------------------------------------------",
        ]

        if events:
            for ev in events:
                human = ev.replace("_", " ").title()
                code_lines.append(f"{inner_indent}# {human}")
                if log:
                    code_lines.append(
                        f"{inner_indent}logger.info('→ Sending %s', '{ev}')"
                    )
                code_lines.append(
                    f"{inner_indent}{await_prefix}interpreter.send('{ev}')"
                )

                if sleep:
                    code_lines.append(
                        f"{inner_indent}{sleep_cmd}({sleep_time})"
                    )
                code_lines.append("")
        else:
            code_lines += [
                f"{inner_indent}logger.info('No events declared in the machine.')",
                "",
            ]

        code_lines += [
            f"{inner_indent}{await_prefix}interpreter.stop()",
            "",
        ]

        # ------------------------ bootstrap guard -------------------------------
        if is_async:
            code_lines += [
                "if __name__ == '__main__':",
                "    asyncio.run(main())",
            ]
        else:
            code_lines += [
                "if __name__ == '__main__':",
                "    main()",
            ]

    else:
        # ------------------------------------------------------------------
        # 🐙  Multiple independent machines (flat mode)
        # ------------------------------------------------------------------
        for idx, name in enumerate(machine_names):
            config = configs[idx]
            json_filename = json_filenames[idx]
            events = sorted(extract_events(config))

            code_lines.append(f"{func_prefix}def run_{name}() -> None:")
            inner_indent = "    "

            cfg_lines = [
                f'{inner_indent}config_path = Path(r"{json_filename}")',
                f"{inner_indent}if not config_path.is_absolute() and config_path.parent == Path('.'):",
                f"{inner_indent}    here = Path(__file__).resolve().parent",
                f"{inner_indent}    candidate = here / config_path.name",
                f"{inner_indent}    config_path = candidate if candidate.exists() else here.parent / config_path.name",
            ]

            code_lines += [
                f'{inner_indent}"""Executes the simulation for the {name} machine."""',
                "",
                f"{inner_indent}# ---------------------------------------------------------------------------",
                f"{inner_indent}# 📂 1. Configuration Loading",
                f"{inner_indent}# ---------------------------------------------------------------------------",
                *cfg_lines,
                f"{inner_indent}with open(config_path, 'r', encoding='utf-8') as f:",
                f"{inner_indent}    config = json.load(f)",
                "",
                f"{inner_indent}# ---------------------------------------------------------------------------",
                f"{inner_indent}# 🧠 2. Logic Binding",
                f"{inner_indent}# ---------------------------------------------------------------------------",
            ]

            # ------------------ logic binding (per machine) --------------------
            if loader:
                if style == "class":
                    if file_count == 1:
                        code_lines.append(
                            f"{inner_indent}logic_provider = {class_name}()"
                        )
                    else:
                        code_lines.append(
                            f"{inner_indent}logic_provider = LogicProvider()"
                        )
                    code_lines.append(
                        f"{inner_indent}machine = create_machine(config, logic_providers=[logic_provider])"
                    )
                else:
                    if file_count == 1:
                        code_lines += [
                            f"{inner_indent}import sys",
                            f"{inner_indent}machine = create_machine(config, logic_modules=[sys.modules[__name__]])",
                        ]
                    else:
                        code_lines.append(
                            f"{inner_indent}machine = create_machine(config, logic_modules=[{logic_file_name}])"
                        )
            else:  # loader OFF
                if style == "class":
                    if file_count == 1:
                        code_lines.append(
                            f"{inner_indent}logic_provider = {class_name}()"
                        )
                    else:
                        code_lines.append(
                            f"{inner_indent}logic_provider = LogicProvider()"
                        )
                    code_lines.append(
                        f"{inner_indent}machine = create_machine(config, logic_providers=[logic_provider])"
                    )
                else:
                    if file_count == 1:
                        code_lines += [
                            f"{inner_indent}import sys",
                            f"{inner_indent}machine = create_machine(config, logic_modules=[sys.modules[__name__]])",
                        ]
                    else:
                        code_lines.append(
                            f"{inner_indent}machine = create_machine(config, logic_modules=[{logic_file_name}])"
                        )

            # ------------------ interpreter setup ------------------------------
            code_lines += [
                "",
                f"{inner_indent}# ---------------------------------------------------------------------------",
                f"{inner_indent}# ⚙️  3. Interpreter Setup",
                f"{inner_indent}# ---------------------------------------------------------------------------",
            ]
            interp_type = (
                "Interpreter(machine)"
                if is_async
                else "SyncInterpreter(machine)"
            )
            code_lines += [
                f"{inner_indent}interpreter = {interp_type}",
                f"{inner_indent}interpreter.use(LoggingInspector())",
                f"{inner_indent}{await_prefix}interpreter.start()",
                "",
                f"{inner_indent}# ---------------------------------------------------------------------------",
                f"{inner_indent}# 🚀 4. Simulation Scenario",
                f"{inner_indent}# ---------------------------------------------------------------------------",
            ]

            if log:
                code_lines.append(
                    f'{inner_indent}logger.info(f"Initial state: {{interpreter.current_state_ids}}")'
                )

            if events:
                for ev in events:
                    human = ev.replace("_", " ").title()
                    code_lines += [
                        f"{inner_indent}# {human}",
                        *(  # first line only when logging is enabled
                            [
                                f"{inner_indent}logger.info('→ Sending %s', '{ev}')"
                            ]
                            if log
                            else []
                        ),
                        f"{inner_indent}{await_prefix}interpreter.send('{ev}')",
                    ]
                    if sleep:
                        code_lines.append(
                            f"{inner_indent}{sleep_cmd}({sleep_time})"
                        )
                    code_lines.append("")
            else:
                code_lines += [
                    f"{inner_indent}logger.info('No events declared in this machine.')",
                    "",
                ]

            code_lines += [
                f"{inner_indent}{await_prefix}interpreter.stop()",
                "",
            ]

        # --------------- top‑level dispatcher (multiple machines) --------------
        code_lines.append(f"{func_prefix}def main() -> None:")
        inner_indent = "    "
        for name in machine_names:
            code_lines.append(f"{inner_indent}{await_prefix}run_{name}()")
        code_lines.append("")
        if is_async:
            code_lines += [
                "if __name__ == '__main__':",
                "    asyncio.run(main())",
            ]
        else:
            code_lines += [
                "if __name__ == '__main__':",
                "    main()",
            ]

    return "\n".join(code_lines)
