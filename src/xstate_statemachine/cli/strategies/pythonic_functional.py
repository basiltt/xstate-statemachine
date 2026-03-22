# src/xstate_statemachine/cli/strategies/pythonic_functional.py
"""Strategy for pythonic functional code generation.

Converts JSON state machine configurations into module-level decorated
functions and a ``build()`` function that uses ``State`` objects,
``.to()`` transitions, and the ``build_machine()`` API to assemble
the machine.
"""

import keyword
from typing import Any, Dict, List, Set

from ..extractor import extract_events
from .base import BaseStrategy, GenerationContext
from ._shared import (
    generate_action_docstring,
    generate_error_handling,
    generate_imports,
    generate_logger_setup,
    generate_section_header,
    snake_case_name,
)


class PythonicFunctionalStrategy(BaseStrategy):
    """Generates pythonic functional state machine code.

    Produces module-level ``@action``, ``@guard``, ``@service`` decorated
    functions (no ``self``) and a ``build()`` function that constructs
    the machine via ``State()`` objects, ``.to()`` transitions, and
    ``build_machine(id=..., states=[...], ...)``.
    """

    @property
    def name(self) -> str:
        return "pythonic-functional"

    # -----------------------------------------------------------------
    # Logic generation
    # -----------------------------------------------------------------

    def generate_logic(self, ctx: GenerationContext) -> str:
        """Generate module-level functions and a build_machine() build() fn.

        Produces a Python module containing:
        - ``@action`` / ``@guard`` / ``@service`` decorated functions
        - A ``build()`` function using State objects and build_machine()
        """
        config = ctx.configs[0]
        parts: List[str] = []

        # -- imports --------------------------------------------------
        parts.append(
            generate_imports(
                is_async=ctx.is_async,
                services=ctx.services,
                template_type="pythonic-functional",
                log=ctx.log,
            )
        )

        # -- logger setup ---------------------------------------------
        if ctx.log:
            parts.append(generate_logger_setup(ctx.log))

        # -- actions --------------------------------------------------
        if ctx.actions:
            parts.append(
                self._generate_component(
                    items=ctx.actions,
                    component_type="action",
                    is_async=ctx.is_async,
                    log=ctx.log,
                )
            )

        # -- guards ---------------------------------------------------
        if ctx.guards:
            parts.append(
                self._generate_component(
                    items=ctx.guards,
                    component_type="guard",
                    is_async=ctx.is_async,
                    log=ctx.log,
                )
            )

        # -- services -------------------------------------------------
        if ctx.services:
            parts.append(
                self._generate_component(
                    items=ctx.services,
                    component_type="service",
                    is_async=ctx.is_async,
                    log=ctx.log,
                )
            )

        # -- build function -------------------------------------------
        parts.append(self._generate_build_function(config, ctx))

        return "\n".join(parts)

    # -----------------------------------------------------------------
    # Runner generation
    # -----------------------------------------------------------------

    def generate_runner(self, ctx: GenerationContext) -> str:
        """Generate runner file that calls build() and runs the machine."""
        config = ctx.configs[0]
        base_name = (
            ctx.machine_names[0]
            if ctx.hierarchy and len(ctx.machine_names) > 1
            else "_".join(ctx.machine_names)
        )
        logic_file_name = f"{base_name}_logic"

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
                ctx, interpreter_class, logic_file_name
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
                    func_prefix,
                    await_prefix,
                    sleep_cmd,
                    interpreter_class,
                    logic_file_name,
                )
            )

        return "\n".join(lines)

    def _generate_flat_runner(
        self,
        ctx: GenerationContext,
        config: Dict[str, Any],
        func_prefix: str,
        await_prefix: str,
        sleep_cmd: str,
        interpreter_class: str,
        logic_file_name: str,
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

        # -- machine creation via build() -----------------------------
        if ctx.file_count == 1:
            lines.append("    machine = build()")
        else:
            lines.append(f"    machine = {logic_file_name}.build()")
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

        # -- parent machine via build() -------------------------------
        lines.append(
            "    # -------------------------------------------"
            "----------------------------"
        )
        lines.append("    # 🧠 Parent machine via build()")
        lines.append(
            "    # -------------------------------------------"
            "----------------------------"
        )
        if ctx.file_count == 1:
            lines.append("    parent_machine = build()")
        else:
            lines.append(f"    parent_machine = {logic_file_name}.build()")
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
            lines.append(
                "    logger.info(" "'No events declared in parent machine.')"
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
                lines.append(
                    f"    logger.info("
                    f"'No events declared in actor \"{a_name}\".')"
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
    # Private helpers – Component generation (module-level functions)
    # -----------------------------------------------------------------

    @staticmethod
    def _generate_component(
        items: Set[str],
        component_type: str,
        is_async: bool,
        log: bool,
    ) -> str:
        """Generate module-level decorated function stubs.

        Unlike the class-based strategy, functions are emitted at the
        module level (no indent) and without a ``self`` parameter.
        """
        if not items:
            return ""

        code_lines: List[str] = []
        section_titles = {
            "action": "Actions",
            "guard": "Guards",
            "service": "Services",
        }
        code_lines.append(
            generate_section_header(section_titles[component_type])
        )

        for original in sorted(items):
            fn_name = snake_case_name(original)
            if keyword.iskeyword(fn_name):
                fn_name = f"{fn_name}_"

            # -- decorator --------------------------------------------
            code_lines.append(f"@{component_type}")

            # -- signature (no self) ----------------------------------
            async_kw = (
                "async " if is_async and component_type != "guard" else ""
            )

            interpreter_type = "Interpreter" if is_async else "SyncInterpreter"

            if component_type == "guard":
                args = [
                    "    context: Dict[str, Any],",
                    "    event: Any,",
                ]
                ret_type = "bool"
            elif component_type == "service":
                args = [
                    f"    interpreter: {interpreter_type},",
                    "    context: Dict[str, Any],",
                    "    event: Any,",
                ]
                ret_type = "Dict[str, Any]"
            else:
                # action
                args = [
                    f"    interpreter: {interpreter_type},",
                    "    context: Dict[str, Any],",
                    "    event: Any,",
                    "    action_def: Any,",
                ]
                ret_type = "None"

            signature_lines = [
                f"{async_kw}def {fn_name}(",
                *args,
                f") -> {ret_type}:",
            ]
            code_lines.extend(signature_lines)

            # -- rich docstring ---------------------------------------
            docstring_body = generate_action_docstring(
                original, component_type
            )
            doc_parts = docstring_body.split("\n")
            code_lines.append(f'    """{doc_parts[0]}')
            for doc_line in doc_parts[1:]:
                if doc_line:
                    code_lines.append(f"    {doc_line}")
                else:
                    code_lines.append("")
            code_lines.append('    """')

            # -- body with error handling -----------------------------
            if component_type == "guard":
                if log:
                    code_lines.append(
                        f"    logger.info(" f'"Evaluating guard: {original}")'
                    )
                code_lines.append("    # TODO: implement guard logic")
                code_lines.append("    return True")
            else:
                body_lines: List[str] = []
                if log:
                    verb = (
                        "Executing action"
                        if component_type == "action"
                        else "Running service"
                    )
                    # Emit BEFORE the try/except block
                    code_lines.append(f'    logger.info("{verb}: {original}")')
                if component_type == "action":
                    body_lines.append("# TODO: implement action logic")
                    body_lines.append("pass")
                else:
                    # service
                    body_lines.append("# TODO: implement service logic")
                    body_lines.append('return {"result": "done"}')

                code_lines.append(
                    generate_error_handling(
                        original, component_type, body_lines, "    "
                    )
                )

            code_lines.append("")

        return "\n".join(code_lines)

    # -----------------------------------------------------------------
    # Private helpers – Build function
    # -----------------------------------------------------------------

    @staticmethod
    def _generate_build_function(
        config: Dict[str, Any],
        ctx: GenerationContext,
    ) -> str:
        """Generate the ``build()`` function using State objects and build_machine().

        Produces a function that creates named ``State`` objects, calls
        ``.to()`` for transitions, then calls ``build_machine()`` with
        ``id``, ``states``, ``context``, ``actions``, ``guards``, and
        ``services`` keyword arguments.
        """
        machine_id = config.get("id", ctx.machine_id)
        states_config = config.get("states", {})
        initial_state = config.get("initial", "")
        initial_context = config.get("context")

        lines: List[str] = []
        lines.append("")
        lines.append("def build() -> Any:")
        lines.append(
            f'    """Build the {machine_id} machine '
            f'using build_machine()."""'
        )

        # -- State object creation ------------------------------------
        state_names: List[str] = []
        for state_name, state_def in states_config.items():
            if not isinstance(state_def, dict):
                state_def = {}

            state_names.append(state_name)
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

            if kwargs:
                args_str = ", ".join(kwargs)
                lines.append(
                    f"    {state_name} = State(" f'"{state_name}", {args_str})'
                )
            else:
                lines.append(f'    {state_name} = State("{state_name}")')

        lines.append("")

        # -- .to() transition calls -----------------------------------
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
                        lines.append(
                            f"    {state_name}.to("
                            f'{trans}, event="{event_name}")'
                        )
                    elif isinstance(trans, dict):
                        target = trans.get("target", "")
                        t_kwargs: List[str] = [
                            f'event="{event_name}"',
                        ]

                        # actions
                        actions_val = trans.get("actions")
                        if actions_val is not None:
                            if isinstance(actions_val, str):
                                t_kwargs.append(f'actions="{actions_val}"')
                            elif isinstance(actions_val, list):
                                act_repr = ", ".join(
                                    f'"{a}"' for a in actions_val
                                )
                                t_kwargs.append(f"actions=[{act_repr}]")

                        # guard
                        guard_val = trans.get("cond") or trans.get("guard")
                        if guard_val is not None:
                            t_kwargs.append(f'guard="{guard_val}"')

                        extra = ", ".join(t_kwargs)
                        lines.append(
                            f"    {state_name}.to(" f"{target}, {extra})"
                        )

        lines.append("")

        # -- build_machine() call -------------------------------------
        bm_args: List[str] = []
        bm_args.append(f'id="{machine_id}"')
        bm_args.append(f"states=[{', '.join(state_names)}]")

        if initial_context is not None:
            bm_args.append(f"context={initial_context!r}")

        # action function references
        if ctx.actions:
            action_refs: List[str] = []
            for original in sorted(ctx.actions):
                fn_name = snake_case_name(original)
                if keyword.iskeyword(fn_name):
                    fn_name = f"{fn_name}_"
                action_refs.append(fn_name)
            bm_args.append(f"actions=[{', '.join(action_refs)}]")

        # guard function references
        if ctx.guards:
            guard_refs: List[str] = []
            for original in sorted(ctx.guards):
                fn_name = snake_case_name(original)
                if keyword.iskeyword(fn_name):
                    fn_name = f"{fn_name}_"
                guard_refs.append(fn_name)
            bm_args.append(f"guards=[{', '.join(guard_refs)}]")

        # service function references
        if ctx.services:
            service_refs: List[str] = []
            for original in sorted(ctx.services):
                fn_name = snake_case_name(original)
                if keyword.iskeyword(fn_name):
                    fn_name = f"{fn_name}_"
                service_refs.append(fn_name)
            bm_args.append(f"services=[{', '.join(service_refs)}]")

        lines.append("    machine = build_machine(")
        for arg in bm_args:
            lines.append(f"        {arg},")
        lines.append("    )")
        lines.append("    return machine")

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Private helpers – Runner
    # -----------------------------------------------------------------

    @staticmethod
    def _generate_runner_imports(
        ctx: GenerationContext,
        interpreter_class: str,
        logic_file_name: str,
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
            lines.append(f"import {logic_file_name}")

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
