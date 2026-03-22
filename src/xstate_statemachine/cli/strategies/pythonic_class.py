# src/xstate_statemachine/cli/strategies/pythonic_class.py
"""Strategy for pythonic class-based code generation.

Converts JSON state machine configurations into a ``StateMachine`` subclass
using the declarative Pythonic API with ``State`` instances, ``.to()``
transitions, and ``@action`` / ``@guard`` / ``@service`` decorators.
"""

import keyword
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from ..extractor import extract_events
from .base import BaseStrategy, GenerationContext
from ._shared import (
    generate_action_docstring,
    generate_error_handling,
    generate_imports,
    generate_logger_setup,
    generate_section_header,
    pascal_case_name,
    safe_identifier,
    snake_case_name,
)


class PythonicClassStrategy(BaseStrategy):
    """Generates pythonic class-based state machine code.

    Produces a ``StateMachine`` subclass with:
    - ``State()`` class attributes for each state
    - ``.to()`` transition chains grouped by event
    - ``@action``, ``@guard``, ``@service`` decorated methods
    """

    @property
    def name(self) -> str:
        return "pythonic-class"

    # -----------------------------------------------------------------
    # Logic generation
    # -----------------------------------------------------------------

    def generate_logic(self, ctx: GenerationContext) -> str:
        """Generate a StateMachine subclass from a JSON config.

        Produces a Python module containing a declarative StateMachine
        subclass with State objects, transition chains, and decorated
        action/guard/service methods.
        """
        config = ctx.configs[0]
        parts: List[str] = []

        # -- module header / imports ----------------------------------
        parts.append(
            generate_imports(
                is_async=ctx.is_async,
                services=ctx.services,
                template_type="pythonic-class",
                log=ctx.log,
            )
        )

        # -- logger setup ---------------------------------------------
        if ctx.log:
            parts.append(generate_logger_setup(ctx.log))

        # -- class definition -----------------------------------------
        class_name = pascal_case_name(ctx.machine_name) + "Machine"
        parts.append("")
        parts.append(f"class {class_name}(StateMachine):")

        indent = "    "
        machine_id = config.get("id", ctx.machine_id)
        parts.append(
            f'{indent}"""'
            f"{pascal_case_name(ctx.machine_name)} state machine "
            f'using the declarative class-based API."""'
        )
        parts.append("")

        # -- machine_id -----------------------------------------------
        parts.append(f'{indent}machine_id = "{machine_id}"')

        # -- initial_context ------------------------------------------
        initial_context = config.get("context")
        if initial_context is not None:
            parts.append(f"{indent}initial_context = {initial_context!r}")

        parts.append("")

        # -- state objects --------------------------------------------
        states_config = config.get("states", {})
        initial_state = config.get("initial", "")
        parts.append(
            self._generate_state_declarations(
                states_config, initial_state, indent
            )
        )
        parts.append("")

        # -- transitions ----------------------------------------------
        parts.append(f"{indent}# Transitions")
        parts.append(self._generate_transitions(states_config, indent))
        parts.append("")

        # -- actions --------------------------------------------------
        if ctx.actions:
            parts.append(f"{indent}# Actions")
            parts.append(
                self._generate_decorated_methods(
                    items=ctx.actions,
                    component_type="action",
                    is_async=ctx.is_async,
                    log=ctx.log,
                    indent=indent,
                )
            )

        # -- guards ---------------------------------------------------
        if ctx.guards:
            parts.append(f"{indent}# Guards")
            parts.append(
                self._generate_decorated_methods(
                    items=ctx.guards,
                    component_type="guard",
                    is_async=ctx.is_async,
                    log=ctx.log,
                    indent=indent,
                )
            )

        # -- services -------------------------------------------------
        if ctx.services:
            parts.append(f"{indent}# Services")
            parts.append(
                self._generate_decorated_methods(
                    items=ctx.services,
                    component_type="service",
                    is_async=ctx.is_async,
                    log=ctx.log,
                    indent=indent,
                )
            )

        return "\n".join(parts)

    # -----------------------------------------------------------------
    # Runner generation
    # -----------------------------------------------------------------

    def generate_runner(self, ctx: GenerationContext) -> str:
        """Generate runner file that instantiates and runs the machine."""
        config = ctx.configs[0]
        base_name = (
            ctx.machine_names[0]
            if ctx.hierarchy and len(ctx.machine_names) > 1
            else "_".join(ctx.machine_names)
        )
        logic_file_name = f"{base_name}_logic"
        class_name = pascal_case_name(base_name) + "Machine"

        interpreter_class = (
            "Interpreter" if ctx.is_async else "SyncInterpreter"
        )
        func_prefix = "async " if ctx.is_async else ""
        await_prefix = "await " if ctx.is_async else ""
        sleep_cmd = "await asyncio.sleep" if ctx.is_async else "time.sleep"

        lines: List[str] = []

        # -- imports --------------------------------------------------
        lines.append(
            self._generate_runner_imports(
                ctx, interpreter_class, logic_file_name, class_name
            )
        )

        # -- logger setup ---------------------------------------------
        if ctx.log:
            lines.append(self._generate_runner_logger_setup(ctx))

        # -- hierarchy mode -------------------------------------------
        if ctx.hierarchy and len(ctx.machine_names) > 1:
            lines.extend(
                self._generate_hierarchy_runner(
                    ctx,
                    class_name,
                    func_prefix,
                    await_prefix,
                    sleep_cmd,
                    interpreter_class,
                    logic_file_name,
                )
            )
        else:
            # -- flat / single machine mode ---------------------------
            lines.extend(
                self._generate_flat_runner(
                    ctx,
                    config,
                    class_name,
                    func_prefix,
                    await_prefix,
                    sleep_cmd,
                    interpreter_class,
                )
            )

        return "\n".join(lines)

    def _generate_flat_runner(
        self,
        ctx: GenerationContext,
        config: Dict[str, Any],
        class_name: str,
        func_prefix: str,
        await_prefix: str,
        sleep_cmd: str,
        interpreter_class: str,
    ) -> List[str]:
        """Generate flat (non-hierarchy) runner body."""
        lines: List[str] = []

        # -- main function --------------------------------------------
        lines.append(f"{func_prefix}def main() -> None:")
        lines.append(
            f'    """Executes the simulation for the '
            f'{ctx.machine_name} machine."""'
        )
        lines.append("")

        # -- machine creation -----------------------------------------
        lines.append(f"    machine = {class_name}.create_machine()")
        lines.append("")

        # -- interpreter setup ----------------------------------------
        lines.append("    # Interpreter Setup")
        lines.append(f"    interpreter = {interpreter_class}(machine)")
        lines.append(f"    {await_prefix}interpreter.start()")
        if ctx.log:
            lines.append(
                "    logger.info("
                "f'Initial state: {interpreter.current_state_ids}')"
            )
        lines.append("")

        # -- event simulation -----------------------------------------
        lines.append("    # Event Simulation")
        events = sorted(extract_events(config))
        if events:
            for ev in events:
                if ctx.log:
                    lines.append(
                        f"    logger.info('Sending event: %s', '{ev}')"
                    )
                lines.append(f'    {await_prefix}interpreter.send("{ev}")')
                if ctx.sleep:
                    lines.append(f"    {sleep_cmd}({ctx.sleep_time})")
                lines.append("")
        else:
            lines.append(
                "    logger.info('No events declared in the machine.')"
            )
            lines.append("")

        # -- stop -----------------------------------------------------
        lines.append(f"    {await_prefix}interpreter.stop()")
        lines.append("")

        # -- main guard -----------------------------------------------
        lines.append('if __name__ == "__main__":')
        if ctx.is_async:
            lines.append("    asyncio.run(main())")
        else:
            lines.append("    main()")

        return lines

    def _generate_hierarchy_runner(
        self,
        ctx: GenerationContext,
        class_name: str,
        func_prefix: str,
        await_prefix: str,
        sleep_cmd: str,
        interpreter_class: str,
        logic_file_name: str,
    ) -> List[str]:
        """Generate hierarchical (parent + actors) runner body."""
        lines: List[str] = []

        parent_name, *actor_names = ctx.machine_names
        parent_json, *actor_jsons = ctx.json_filenames
        parent_cfg = ctx.configs[0]

        lines.append(f"{func_prefix}def main() -> None:")
        lines.append(
            '    """Run the parent machine and spawn actor machines."""'
        )
        lines.append("    root_dir = Path(__file__).parent")
        lines.append("")

        # -- load child configs from JSON -----------------------------
        for name, jfn in zip(actor_names, actor_jsons):
            lines.append(
                f"    with open(root_dir / '{jfn}', 'r', "
                f"encoding='utf-8') as f:"
            )
            lines.append(f"        {name}_cfg = json.load(f)")
        lines.append("")

        # -- parent machine via Pythonic API --------------------------
        lines.append(
            "    # -------------------------------------------"
            "----------------------------"
        )
        lines.append("    # 🧠 Parent machine via Pythonic API")
        lines.append(
            "    # -------------------------------------------"
            "----------------------------"
        )
        lines.append(f"    parent_machine = {class_name}.create_machine()")
        lines.append(f"    parent = {interpreter_class}(parent_machine)")
        lines.append(f"    {await_prefix}parent.start()")
        if ctx.log:
            lines.append(
                "    logger.info("
                "'👑 Parent started. Initial state(s): %s', "
                "parent.current_state_ids)"
            )
        lines.append("")

        # -- spawn actors from JSON -----------------------------------
        lines.append(
            "    # -------------------------------------------"
            "------------------------"
        )
        lines.append("    # 🎭 Spawn & start every actor interpreter")
        lines.append(
            "    # -------------------------------------------"
            "------------------------"
        )
        lines.append("    actors = {}")

        for a_name in actor_names:
            lines.append(
                f"    machine_{a_name} = create_machine(" f"{a_name}_cfg)"
            )
            lines.append(
                f"    ai_{a_name} = {interpreter_class}(machine_{a_name})"
            )
            lines.append(f"    {await_prefix}ai_{a_name}.start()")
            lines.append(f"    actors['{a_name}'] = ai_{a_name}")
        lines.append("")

        # -- parent event simulation ----------------------------------
        parent_events = sorted(extract_events(parent_cfg))
        lines.append(
            "    # -------------------------------------------"
            "------------------------"
        )
        lines.append("    # 🚀 Simulating Parent Machine")
        lines.append(
            "    # -------------------------------------------"
            "------------------------"
        )
        if parent_events:
            for ev in parent_events:
                if ctx.log:
                    lines.append(
                        f"    logger.info(" f"'Parent → sending %s', '{ev}')"
                    )
                lines.append(f"    {await_prefix}parent.send('{ev}')")
                if ctx.sleep:
                    lines.append(f"    {sleep_cmd}({ctx.sleep_time})")
                lines.append("")
        else:
            if ctx.log:
                lines.append(
                    "    logger.info("
                    "'No events declared in parent machine.')"
                )
            else:
                lines.append(
                    "    pass  # No events declared in parent machine"
                )
            lines.append("")

        # -- actor event simulation -----------------------------------
        for idx, a_name in enumerate(actor_names):
            actor_events = sorted(extract_events(ctx.configs[idx + 1]))
            lines.append(
                "    # -------------------------------------------"
                "------------------------"
            )
            lines.append(f"    # 🚀 Simulating Actor «{a_name}»")
            lines.append(
                "    # -------------------------------------------"
                "------------------------"
            )
            if actor_events:
                for ev in actor_events:
                    if ctx.log:
                        lines.append(
                            f"    logger.info("
                            f"'{a_name} → sending %s', '{ev}')"
                        )
                    lines.append(
                        f"    {await_prefix}actors['{a_name}'].send('{ev}')"
                    )
                    if ctx.sleep:
                        lines.append(f"    {sleep_cmd}({ctx.sleep_time})")
                    lines.append("")
            else:
                if ctx.log:
                    lines.append(
                        f"    logger.info("
                        f"'No events declared in actor \"{a_name}\".')"
                    )
                else:
                    lines.append(
                        f"    pass  # No events declared"
                        f' in actor "{a_name}"'
                    )
                lines.append("")

        # -- shutdown -------------------------------------------------
        lines.append(
            "    # -------------------------------------------"
            "------------------------"
        )
        lines.append("    # 🛑 Graceful shutdown of actors then parent")
        lines.append(
            "    # -------------------------------------------"
            "------------------------"
        )
        for a_name in actor_names:
            lines.append(f"    {await_prefix}actors['{a_name}'].stop()")
        lines.append(f"    {await_prefix}parent.stop()")
        lines.append("")

        # -- main guard -----------------------------------------------
        if ctx.is_async:
            lines.append("if __name__ == '__main__':")
            lines.append("    asyncio.run(main())")
        else:
            lines.append("if __name__ == '__main__':")
            lines.append("    main()")

        return lines

    # -----------------------------------------------------------------
    # Private helpers – State declarations
    # -----------------------------------------------------------------

    @staticmethod
    def _generate_state_declarations(
        states_config: Dict[str, Any],
        initial_state: str,
        indent: str,
    ) -> str:
        """Generate ``State()`` class attribute declarations.

        Each key in ``states_config`` becomes a ``State()`` instance.
        The initial state gets ``initial=True``. Entry actions and
        invoke configs are passed as keyword arguments.
        """
        lines: List[str] = []
        for state_name, state_def in states_config.items():
            if not isinstance(state_def, dict):
                state_def = {}

            attr_name = safe_identifier(state_name)
            kwargs: List[str] = []

            # initial
            if state_name == initial_state:
                kwargs.append("initial=True")

            # entry actions
            entry = state_def.get("entry")
            if entry is not None:
                if isinstance(entry, str):
                    kwargs.append(f'entry=["{entry}"]')
                elif isinstance(entry, list):
                    entry_repr = ", ".join(f'"{a}"' for a in entry)
                    kwargs.append(f"entry=[{entry_repr}]")

            # invoke
            invoke = state_def.get("invoke")
            if invoke is not None:
                kwargs.append(f"invoke={invoke!r}")

            # Build the State(...) call
            if kwargs:
                args_str = ", ".join(kwargs)
                lines.append(f"{indent}{attr_name} = State({args_str})")
            else:
                lines.append(f"{indent}{attr_name} = State()")

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Private helpers – Transitions
    # -----------------------------------------------------------------

    @staticmethod
    def _generate_transitions(
        states_config: Dict[str, Any],
        indent: str,
    ) -> str:
        """Generate ``.to()`` transition chains grouped by event name.

        Parses the ``"on"`` blocks from each state and groups transitions
        by event. Same-event transitions from multiple sources are chained
        with the ``|`` operator.
        """
        # Collect: event_name -> [(source, target, actions, guard)]
        event_transitions: Dict[str, List[Tuple[str, str, Optional[str], Optional[str]]]] = defaultdict(list)  # type: ignore[arg-type]

        for state_name, state_def in states_config.items():
            if not isinstance(state_def, dict):
                continue
            on_block = state_def.get("on", {})
            if not isinstance(on_block, dict):
                continue

            for event_name, transition_data in on_block.items():
                transitions = (
                    transition_data
                    if isinstance(transition_data, list)
                    else [transition_data]
                )
                for trans in transitions:
                    if isinstance(trans, str):
                        # Simple target string
                        event_transitions[event_name].append(
                            (state_name, trans, None, None)
                        )
                    elif isinstance(trans, dict):
                        target = trans.get("target", "")
                        actions_val = trans.get("actions")
                        guard_val = trans.get("cond") or trans.get("guard")
                        event_transitions[event_name].append(
                            (state_name, target, actions_val, guard_val)
                        )

        lines: List[str] = []
        for event_name, trans_list in event_transitions.items():
            safe_event = safe_identifier(event_name)
            to_calls: List[str] = []
            for source, target, actions_val, guard_val in trans_list:
                safe_src = safe_identifier(source)
                safe_tgt = safe_identifier(target)
                parts: List[str] = [safe_tgt]
                parts.append(f'event="{event_name}"')
                if actions_val is not None:
                    if isinstance(actions_val, str):
                        parts.append(f'actions="{actions_val}"')
                    elif isinstance(actions_val, list):
                        act_repr = ", ".join(f'"{a}"' for a in actions_val)
                        parts.append(f"actions=[{act_repr}]")
                if guard_val is not None:
                    parts.append(f'guard="{guard_val}"')

                args_str = ", ".join(parts)
                to_calls.append(f"{safe_src}.to({args_str})")

            if len(to_calls) == 1:
                lines.append(f"{indent}{safe_event} = {to_calls[0]}")
            else:
                # Multi-source: chain with |
                chain = f"\n{indent}    | ".join(to_calls)
                lines.append(
                    f"{indent}{safe_event} = (\n"
                    f"{indent}    {chain}\n"
                    f"{indent})"
                )

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Private helpers – Decorated methods
    # -----------------------------------------------------------------

    @staticmethod
    def _generate_decorated_methods(
        items: Set[str],
        component_type: str,
        is_async: bool,
        log: bool,
        indent: str,
    ) -> str:
        """Generate ``@action`` / ``@guard`` / ``@service`` decorated methods.

        Each item becomes a method on the ``StateMachine`` subclass with
        the appropriate decorator, type-annotated signature, rich
        docstring, and error handling.
        """
        if not items:
            return ""

        decorator_map = {
            "action": "action",
            "guard": "guard",
            "service": "service",
        }
        decorator = decorator_map[component_type]

        code_lines: List[str] = []

        for original in sorted(items):
            fn_name = snake_case_name(original)
            if keyword.iskeyword(fn_name):
                fn_name = f"{fn_name}_"

            # -- decorator ------------------------------------------------
            code_lines.append(f"{indent}@{decorator}")

            # -- signature ------------------------------------------------
            # Guards are never async; actions/services may be
            async_kw = (
                "async " if is_async and component_type != "guard" else ""
            )

            self_arg = f"{indent}        self,"
            if component_type == "guard":
                args = [
                    f"{indent}        context: Dict[str, Any],",
                    f"{indent}        event: Any,",
                ]
                ret_type = "bool"
            elif component_type == "service":
                args = [
                    f"{indent}        interpreter: "
                    "Union[Interpreter, SyncInterpreter],",
                    f"{indent}        context: Dict[str, Any],",
                    f"{indent}        event: Any,",
                ]
                ret_type = "Dict[str, Any]"
            else:
                # action
                args = [
                    f"{indent}        interpreter: "
                    "Union[Interpreter, SyncInterpreter],",
                    f"{indent}        context: Dict[str, Any],",
                    f"{indent}        event: Any,",
                    f"{indent}        action_def: Any,",
                ]
                ret_type = "None"

            signature_lines = [
                f"{indent}{async_kw}def {fn_name}(",
                self_arg,
                *args,
                f"{indent}) -> {ret_type}:",
            ]
            code_lines.extend(signature_lines)

            # -- rich docstring -------------------------------------------
            docstring_body = generate_action_docstring(
                original, component_type
            )
            code_lines.append(f'{indent}    """')
            for doc_line in docstring_body.split("\n"):
                if doc_line:
                    code_lines.append(f"{indent}    {doc_line}")
                else:
                    code_lines.append("")
            code_lines.append(f'{indent}    """')

            # -- body with error handling ---------------------------------
            if component_type == "guard":
                if log:
                    code_lines.append(
                        f"{indent}    logger.info("
                        f'"Evaluating guard: {original}")'
                    )
                code_lines.append(f"{indent}    # TODO: implement guard logic")
                code_lines.append(f"{indent}    return True")
            else:
                body_lines: List[str] = []
                if log:
                    verb = (
                        "Executing action"
                        if component_type == "action"
                        else "Running service"
                    )
                    body_lines.append(f'logger.info("{verb}: {original}")')
                if component_type == "action":
                    body_lines.append("# TODO: implement action logic")
                    body_lines.append("pass")
                else:
                    # service
                    body_lines.append("# TODO: implement service logic")
                    body_lines.append('return {"result": "done"}')

                code_lines.append(
                    generate_error_handling(
                        original,
                        component_type,
                        body_lines,
                        indent + "    ",
                        log=log,
                    )
                )

            code_lines.append("")

        return "\n".join(code_lines)

    # -----------------------------------------------------------------
    # Private helpers – Runner
    # -----------------------------------------------------------------

    @staticmethod
    def _generate_runner_imports(
        ctx: GenerationContext,
        interpreter_class: str,
        logic_file_name: str,
        class_name: str,
    ) -> str:
        """Generate import block for the runner file."""
        lines: List[str] = []

        is_hierarchy = ctx.hierarchy and len(ctx.machine_names) > 1

        if is_hierarchy:
            lines.append("from pathlib import Path")
            lines.append("import json")
        if ctx.log:
            lines.append("import logging")
        if ctx.sleep and not ctx.is_async:
            lines.append("import time")
        if ctx.is_async:
            lines.append("import asyncio")

        if is_hierarchy:
            lines.append(
                f"from xstate_statemachine import "
                f"create_machine, {interpreter_class}"
            )
        else:
            lines.append(
                f"from xstate_statemachine import {interpreter_class}"
            )

        if ctx.file_count == 2:
            lines.append("")
            lines.append(f"from {logic_file_name} import {class_name}")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _generate_runner_logger_setup(ctx: GenerationContext) -> str:
        """Generate logger setup block for the runner."""
        lines: List[str] = []
        if ctx.file_count > 1:
            lines.append(generate_section_header("Logger Configuration"))
        lines.extend(
            [
                "logging.basicConfig("
                "level=logging.INFO, "
                "format='%(asctime)s [%(levelname)s] %(message)s')",
                "logger = logging.getLogger(__name__)",
                "",
            ]
        )
        return "\n".join(lines)
