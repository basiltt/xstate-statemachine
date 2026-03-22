# src/xstate_statemachine/cli/strategies/function_json.py
"""Strategy for function-based JSON code generation."""

import keyword
from typing import List, Set

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


class FunctionJsonStrategy(BaseStrategy):
    """Generates function-based logic with JSON config loading.

    Unlike :class:`ClassJsonStrategy`, this strategy produces module-level
    functions without a class wrapper.  Functions do not receive a ``self``
    parameter, and the runner binds them via ``logic_modules=[module]``
    rather than ``logic_providers=[instance]``.
    """

    @property
    def name(self) -> str:
        return "function-json"

    # -----------------------------------------------------------------
    # Logic generation
    # -----------------------------------------------------------------

    def generate_logic(self, ctx: GenerationContext) -> str:
        """Generate module-level function stubs with production-quality output.

        Produces a Python module containing top-level function stubs for
        actions, guards, and services extracted from the state machine
        configuration.  No class wrapper is emitted.
        """
        parts: List[str] = []

        # -- imports --------------------------------------------------
        parts.append(
            generate_imports(
                is_async=ctx.is_async,
                services=ctx.services,
                template_type="function-json",
                log=ctx.log,
            )
        )

        # -- logger setup --------------------------------------------
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

        return "\n".join(parts)

    # -----------------------------------------------------------------
    # Runner generation
    # -----------------------------------------------------------------

    def generate_runner(self, ctx: GenerationContext) -> str:
        """Generate runner file that loads JSON config and runs the machine.

        The runner binds logic via ``logic_modules=[module]`` instead of
        ``logic_providers=[instance]`` used by the class-based strategy.
        """
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
                ctx,
                interpreter_class,
                logic_file_name,
            )
        )

        # -- logger setup ---------------------------------------------
        if ctx.log:
            lines.append(self._generate_runner_logger_setup(ctx))

        # -- main function --------------------------------------------
        run_func_name = "main"
        lines.append(f"{func_prefix}def {run_func_name}() -> None:")
        lines.append(
            f'    """Executes the simulation for the '
            f'{ctx.machine_name} machine."""'
        )
        lines.append("")

        # -- config loading -------------------------------------------
        json_filename = ctx.json_filenames[0]
        lines.append(self._generate_config_path_code(json_filename))
        lines.append("")

        # -- logic binding (module-based) -----------------------------
        lines.append("    # Logic Binding")
        if ctx.file_count == 1:
            lines.append("    import sys")
            lines.append(
                "    machine = create_machine("
                "config, logic_modules=[sys.modules[__name__]])"
            )
        else:
            lines.append(
                f"    machine = create_machine("
                f"config, logic_modules=[{logic_file_name}])"
            )
        lines.append("")

        # -- interpreter setup ----------------------------------------
        lines.append("    # Interpreter Setup")
        lines.append(f"    interpreter = {interpreter_class}(machine)")
        lines.append("    interpreter.use(LoggingInspector())")
        lines.append(f"    {await_prefix}interpreter.start()")
        if ctx.log:
            lines.append(
                "    logger.info("
                "f'Initial state: {interpreter.current_state_ids}')"
            )
        lines.append("")

        # -- event simulation -----------------------------------------
        lines.append("    # Event Simulation")
        events = sorted(extract_events(ctx.configs[0]))
        if events:
            for ev in events:
                if ctx.log:
                    lines.append(
                        f"    logger.info('Sending event: %s', '{ev}')"
                    )
                lines.append(f"    {await_prefix}interpreter.send('{ev}')")
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
        if ctx.is_async:
            lines.append("if __name__ == '__main__':")
            lines.append("    asyncio.run(main())")
        else:
            lines.append("if __name__ == '__main__':")
            lines.append("    main()")

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _generate_component(
        items: Set[str],
        component_type: str,
        is_async: bool,
        log: bool,
    ) -> str:
        """Generate module-level function stubs for one component type.

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

            async_kw = (
                "async " if is_async and component_type != "guard" else ""
            )

            # -- signature (no self, no noqa) -------------------------
            if component_type == "guard":
                args = [
                    "    context: Dict[str, Any],",
                    "    event: Event,",
                ]
            else:
                args = [
                    "    interpreter: " "Union[Interpreter, SyncInterpreter],",
                    "    context: Dict[str, Any],",
                    "    event: Event,",
                ]
                if component_type == "action":
                    args.append("    action_def: ActionDefinition,")

            # -- return type (None instead of Awaitable[None]) --------
            if component_type == "guard":
                ret_type = "bool"
            elif component_type == "service":
                ret_type = "Dict[str, Any]"
            else:
                # action: always None, even for async
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
            code_lines.append('    """')
            for doc_line in docstring_body.split("\n"):
                if doc_line:
                    code_lines.append(f"    {doc_line}")
                else:
                    code_lines.append("")
            code_lines.append('    """')

            # -- body with error handling (for actions/services) ------
            if component_type == "guard":
                # Guards: no try/except, just return True
                if log:
                    code_lines.append(
                        f"    logger.info(" f'"Evaluating guard {original}")'
                    )
                code_lines.append("    # TODO: implement guard logic")
                code_lines.append("    return True")
            else:
                # Actions & services: wrap in try/except
                body_lines: List[str] = []
                if log:
                    verb = (
                        "Executing action"
                        if component_type == "action"
                        else "Running service"
                    )
                    body_lines.append(f'logger.info("{verb} {original}")')
                if component_type == "action":
                    if is_async:
                        body_lines.append(
                            "await asyncio.sleep(0.1)  # placeholder"
                        )
                    body_lines.append("# TODO: implement")
                else:
                    # service
                    if is_async:
                        body_lines.append("await asyncio.sleep(1)")
                    else:
                        body_lines.append("time.sleep(1)")
                    body_lines.append("# TODO: implement service")
                    body_lines.append("return {'result': 'done'}")

                code_lines.append(
                    generate_error_handling(
                        original, component_type, body_lines, "    "
                    )
                )

            # service alias (module-level, no indent)
            if fn_name != original and component_type == "service":
                code_lines.append("")
                code_lines.append(
                    f"{original} = {fn_name}  # alias for JSON name"
                )

            code_lines.append("")

        return "\n".join(code_lines)

    @staticmethod
    def _generate_runner_imports(
        ctx: GenerationContext,
        interpreter_class: str,
        logic_file_name: str,
    ) -> str:
        """Generate import block for the runner file."""
        lines = [
            "from pathlib import Path",
            "import json",
            "from xstate_statemachine import LoggingInspector",
            f"from xstate_statemachine import create_machine, {interpreter_class}",
        ]
        if ctx.log:
            lines.append("import logging")
        if ctx.sleep and not ctx.is_async:
            lines.append("import time")
        if ctx.is_async:
            lines.append("import asyncio")

        if ctx.file_count == 2:
            lines.append("")
            lines.append(f"import {logic_file_name}")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _generate_runner_logger_setup(ctx: GenerationContext) -> str:
        """Generate logger setup block for the runner."""
        lines = []
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

    @staticmethod
    def _generate_config_path_code(
        json_filename: str, indent: str = "    "
    ) -> str:
        """Generate robust JSON config loading code."""
        return "\n".join(
            [
                f'{indent}config_path = Path(r"{json_filename}")',
                f"{indent}if not config_path.is_absolute() "
                f"and config_path.parent == Path('.'):",
                f"{indent}    here = Path(__file__).resolve().parent",
                f"{indent}    candidate = here / config_path.name",
                f"{indent}    config_path = ("
                f"candidate if candidate.exists() "
                f"else here.parent / config_path.name)",
                f"{indent}with open(config_path, 'r', encoding='utf-8') as f:",
                f"{indent}    config = json.load(f)",
            ]
        )
