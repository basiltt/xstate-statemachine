# src/xstate_statemachine/cli/strategies/class_json.py
"""Strategy for class-based JSON code generation."""

import keyword
from typing import List, Set

from ..extractor import extract_events
from .base import BaseStrategy, GenerationContext
from ._shared import (
    generate_action_docstring,
    generate_error_handling,
    generate_imports,
    generate_logger_setup,
    generate_module_header,
    generate_section_header,
    pascal_case_name,
    snake_case_name,
)


class ClassJsonStrategy(BaseStrategy):
    """Generates class-based logic with JSON config loading."""

    @property
    def name(self) -> str:
        return "class-json"

    # -----------------------------------------------------------------
    # Logic generation
    # -----------------------------------------------------------------

    def generate_logic(self, ctx: GenerationContext) -> str:
        """Generate class-based logic file with production-quality output.

        Produces a Python module containing a logic provider class with
        method stubs for actions, guards, and services extracted from
        the state machine configuration.
        """
        parts: List[str] = []

        # -- imports --------------------------------------------------
        parts.append(
            generate_imports(
                is_async=ctx.is_async,
                services=ctx.services,
                template_type="class-json",
                log=ctx.log,
            )
        )

        # -- logger setup --------------------------------------------
        if ctx.log:
            parts.append(generate_logger_setup(ctx.log))

        # -- class definition -----------------------------------------
        class_name = pascal_case_name(ctx.machine_name) + "Logic"
        parts.append(generate_section_header("Class-based Logic"))
        parts.append(f"class {class_name}:")
        parts.append("")

        indent = "    "

        # -- actions --------------------------------------------------
        if ctx.actions:
            parts.append(
                self._generate_component(
                    items=ctx.actions,
                    component_type="action",
                    is_async=ctx.is_async,
                    log=ctx.log,
                    indent=indent,
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
                    indent=indent,
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
                    indent=indent,
                )
            )

        return "\n".join(parts)

    # -----------------------------------------------------------------
    # Runner generation
    # -----------------------------------------------------------------

    def generate_runner(self, ctx: GenerationContext) -> str:
        """Generate runner file that loads JSON config and runs the machine."""
        base_name = (
            ctx.machine_names[0]
            if ctx.hierarchy and len(ctx.machine_names) > 1
            else "_".join(ctx.machine_names)
        )
        logic_file_name = f"{base_name}_logic"
        class_name = pascal_case_name(base_name) + "Logic"

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
                class_name,
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

        # -- logic binding --------------------------------------------
        lines.append("    # Logic Binding")
        logic_instance = (
            f"{class_name}()" if ctx.file_count == 1 else "LogicProvider()"
        )
        lines.append(f"    logic_provider = {logic_instance}")
        lines.append(
            "    machine = create_machine("
            "config, logic_providers=[logic_provider])"
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
        indent: str,
    ) -> str:
        """Generate method stubs for one component type (action/guard/service)."""
        if not items:
            return ""

        code_lines: List[str] = []
        section_titles = {
            "action": "Actions",
            "guard": "Guards",
            "service": "Services",
        }
        code_lines.append(f"{indent}# {section_titles[component_type]}")

        for original in sorted(items):
            fn_name = snake_case_name(original)
            if keyword.iskeyword(fn_name):
                fn_name = f"{fn_name}_"

            async_kw = (
                "async " if is_async and component_type != "guard" else ""
            )

            # -- signature (no noqa comments) -------------------------
            self_arg = f"{indent}        self,"
            if component_type == "guard":
                args = [
                    f"{indent}        context: Dict[str, Any],",
                    f"{indent}        event: Event,",
                ]
            else:
                args = [
                    f"{indent}        interpreter: "
                    "Union[Interpreter, SyncInterpreter],",
                    f"{indent}        context: Dict[str, Any],",
                    f"{indent}        event: Event,",
                ]
                if component_type == "action":
                    args.append(
                        f"{indent}        action_def: ActionDefinition,"
                    )

            # -- return type (None instead of Awaitable[None]) --------
            if component_type == "guard":
                ret_type = "bool"
            elif component_type == "service":
                ret_type = (
                    "Dict[str, Any]" if not is_async else "Dict[str, Any]"
                )
            else:
                # action: always None, even for async
                ret_type = "None"

            signature_lines = [
                f"{indent}{async_kw}def {fn_name}(",
                self_arg,
                *args,
                f"{indent}) -> {ret_type}:",
            ]
            code_lines.extend(signature_lines)

            # -- rich docstring ---------------------------------------
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

            # -- body with error handling (for actions/services) ------
            if component_type == "guard":
                # Guards: no try/except, just return True
                if log:
                    code_lines.append(
                        f"{indent}    logger.info("
                        f'"Evaluating guard {original}")'
                    )
                code_lines.append(f"{indent}    # TODO: implement guard logic")
                code_lines.append(f"{indent}    return True")
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
                        original, component_type, body_lines, indent + "    "
                    )
                )

            # service alias
            if fn_name != original and component_type == "service":
                code_lines.append("")
                code_lines.append(
                    f"{indent}{original} = {fn_name}  # alias for JSON name"
                )

            code_lines.append("")

        return "\n".join(code_lines)

    @staticmethod
    def _generate_runner_imports(
        ctx: GenerationContext,
        interpreter_class: str,
        logic_file_name: str,
        class_name: str,
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
            lines.append(
                f"from {logic_file_name} import {class_name} as LogicProvider"
            )

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
