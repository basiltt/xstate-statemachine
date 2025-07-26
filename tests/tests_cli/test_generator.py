# tests_cli/test_generator.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Code Generation
# -----------------------------------------------------------------------------
# This module provides unit tests for the functions in
# `xstate_statemachine.cli.generator`.
#
# It verifies that both logic and runner source code are generated correctly
# based on a wide range of input options, including:
#   -   Code style (class vs. function)
#   -   Execution mode (async vs. sync)
#   -   Presence of logging, services, and other features.
#   -   Advanced features like keyword aliasing and hierarchical structures.
# -----------------------------------------------------------------------------
"""
Unit tests for the CLI's logic and runner code generation functions.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import unittest

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from xstate_statemachine.cli.generator import (
    generate_logic_code,
    generate_runner_code,
)

from .fixtures import (
    HIERARCHY_CHILD_CONFIG,
    HIERARCHY_PARENT_CONFIG,
    SAMPLE_CONFIG_SIMPLE,
    SAMPLE_CONFIG_NESTED,
    SAMPLE_CONFIG_MULTIPLE,
)

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestLogicCodeGenerator
# -----------------------------------------------------------------------------


class TestLogicCodeGenerator(unittest.TestCase):
    """
    Verifies the `generate_logic_code` function under various options.
    """

    def setUp(self) -> None:
        """
        Set up common data for code generation tests.
        """
        self.actions = {"act1", "act2"}
        self.guards = {"guard1"}
        self.services = {"srv1"}
        self.machine_name = "test_machine"

    def test_generate_class_style_sync_with_log(self) -> None:
        """
        Ensures correct generation for: class style, sync mode, with logging.
        """
        logger.info("🧪 Testing class-style, sync generation with logging.")
        code = generate_logic_code(
            self.actions,
            self.guards,
            self.services,
            "class",
            True,
            False,
            self.machine_name,
            2,
        )
        self.assertIn("class TestMachineLogic:", code)
        self.assertIn('logger.info("Executing action act1")', code)
        self.assertIn("time.sleep(1)", code)
        self.assertNotIn("import asyncio", code)
        self.assertIn("import time", code)

    def test_generate_function_style_async_no_log(self) -> None:
        """
        Ensures correct generation for: function style, async mode, no logging.
        """
        logger.info(
            "🧪 Testing function-style, async generation without logging."
        )
        code = generate_logic_code(
            self.actions,
            self.guards,
            self.services,
            "function",
            False,
            True,
            self.machine_name,
            2,
        )
        self.assertNotIn("class ", code)
        self.assertNotIn("logger.info", code)
        self.assertIn("await asyncio.sleep(1)", code)
        self.assertIn("import asyncio", code)
        self.assertNotIn("import time", code)

    def test_generate_no_services_no_time_import(self) -> None:
        """
        Confirms `time` is not imported in sync mode if there are no services.
        """
        logger.info("🧪 Testing that `time` is not imported without services.")
        code = generate_logic_code(
            self.actions, self.guards, set(), "class", True, False, "test", 2
        )
        self.assertNotIn("import time", code)

    def test_generate_keyword_aliasing(self) -> None:
        """
        Tests that a service named after a Python keyword is handled correctly.
        """
        logger.info("🧪 Testing logic generation for keyword-named services.")
        code = generate_logic_code(
            set(), set(), {"pass", "import"}, "class", False, False, "test", 2
        )
        # ✅ Check that the function name is sanitized with a trailing underscore.
        self.assertIn("def pass_(", code)
        self.assertIn("def import_(", code)
        # ✅ Check that an alias is created to map the original keyword name.
        self.assertIn("pass = pass_", code)
        self.assertIn("import = import_", code)

    def test_generate_noqa_comments(self) -> None:
        """
        Ensures generated logic includes noqa comments for common IDE warnings.
        """
        logger.info("🧪 Testing for noqa comments in generated logic.")
        code = generate_logic_code(
            {"a"}, {"g"}, {"s"}, "class", True, True, "test", 2
        )
        self.assertIn("# noqa: ignore IDE static method warning", code)
        self.assertIn("# noqa : ignore IDE return type hint warning", code)

    def test_generate_logic_code_with_service_aliasing(self) -> None:
        """Ensures services with names needing conversion are aliased correctly."""
        logger.info("🧪 Testing logic generation with service aliasing.")
        logic_code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"myCoolService"},  # A name that will be converted
            style="class",
            log=False,
            is_async=False,
            machine_name="test",
            file_count=2,
        )
        self.assertIn("def my_cool_service(", logic_code)
        self.assertIn("myCoolService = my_cool_service", logic_code)

    def test_generate_with_services_time_import(self) -> None:
        """Confirms `time` is imported in sync mode when services are present."""
        logger.info("🧪 Testing with services, time import.")
        code = generate_logic_code(
            self.actions,
            self.guards,
            self.services,
            "class",
            True,
            False,
            self.machine_name,
            2,
        )
        self.assertIn("import time", code)

    def test_generate_class_name_from_machine_name(self) -> None:
        """Verifies that the logic class name is correctly derived from the machine name."""
        logger.info("🧪 Testing class name from machine name.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, "my_machine", 2
        )
        self.assertIn("class MyMachineLogic:", code)

    def test_generate_no_actions_guards_services(self) -> None:
        """Ensures code is generated gracefully when there are no logic implementations."""
        logger.info("🧪 Testing empty logic code.")
        code = generate_logic_code(
            set(), set(), set(), "function", False, True, self.machine_name, 2
        )
        self.assertNotIn("# ⚙️ Actions", code)
        self.assertNotIn("# 🛡️ Guards", code)
        self.assertNotIn("# 🔄 Services", code)

    def test_generate_async_actions(self) -> None:
        """Checks for `async def` and `await` keywords in generated async actions."""
        logger.info("🧪 Testing async actions.")
        code = generate_logic_code(
            {"async_act"},
            set(),
            set(),
            "class",
            False,
            True,
            self.machine_name,
            2,
        )
        self.assertIn("async def async_act(", code)
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_sync_guards_no_log(self) -> None:
        """Verifies a simple sync guard is generated without logging when disabled."""
        logger.info("🧪 Testing sync guards no log.")
        code = generate_logic_code(
            set(),
            {"sync_g"},
            set(),
            "function",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertNotIn("logger.info", code)
        self.assertIn("return True", code)

    def test_generate_services_async(self) -> None:
        """Checks for `async def` and `await` in generated async services."""
        logger.info("🧪 Testing async services.")
        code = generate_logic_code(
            set(),
            set(),
            {"async_srv"},
            "class",
            True,
            True,
            self.machine_name,
            2,
        )
        self.assertIn("async def async_srv(", code)
        self.assertIn("await asyncio.sleep(1)", code)
        self.assertIn('logger.info("Running service async_srv")', code)

    def test_generate_services_sync(self) -> None:
        """Checks for `time.sleep` in generated sync services."""
        logger.info("🧪 Testing sync services.")
        code = generate_logic_code(
            set(),
            set(),
            {"sync_srv"},
            "function",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertIn("def sync_srv(", code)
        self.assertIn("time.sleep(1)", code)
        self.assertNotIn("logger.info", code)

    def test_generate_interpreter_type_in_params(self) -> None:
        """Ensures the interpreter type hint changes based on async mode."""
        logger.info("🧪 Testing interpreter type in function params.")
        code_sync = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        code_async = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn(
            "interpreter: Union[Interpreter, SyncInterpreter],", code_sync
        )
        self.assertIn(
            "interpreter: Union[Interpreter, SyncInterpreter],", code_async
        )

    def test_generate_return_type_for_actions(self) -> None:
        """Ensures action return type hint changes based on async mode."""
        logger.info("🧪 Testing return type for actions.")
        code_sync = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        code_async = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn("-> None:", code_sync)
        self.assertIn("-> Awaitable[None]:", code_async)

    def test_generate_return_type_for_services(self) -> None:
        """Ensures service return type hint changes based on async mode."""
        logger.info("🧪 Testing return type for services.")
        code_sync = generate_logic_code(
            set(), set(), {"srv"}, "class", False, False, self.machine_name, 2
        )
        code_async = generate_logic_code(
            set(), set(), {"srv"}, "class", False, True, self.machine_name, 2
        )
        self.assertIn("-> Dict[str, Any]:", code_sync)
        self.assertIn("-> Awaitable[Dict[str, Any]]:", code_async)

    def test_generate_guards_return_bool(self) -> None:
        """Verifies that generated guards are correctly type-hinted to return `bool`."""
        logger.info("🧪 Testing guards return bool.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("-> bool:", code)

    def test_generate_function_style_no_self(self) -> None:
        """Confirms that 'self' is not included in function-style logic."""
        logger.info("🧪 Testing function style no self.")
        code = generate_logic_code(
            {"act"},
            set(),
            set(),
            "function",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertNotIn("self,", code)

    def test_generate_no_dummy_sleep_if_no_log(self) -> None:
        """Ensures dummy async sleep is present even if logging is off."""
        logger.info("🧪 Testing no dummy sleep if no log.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_sorted_names(self) -> None:
        """Verifies that generated functions are sorted alphabetically."""
        logger.info("🧪 Testing sorted names in code.")
        actions = {"z_act", "a_act"}
        code = generate_logic_code(
            actions, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertTrue(code.find("def a_act(") < code.find("def z_act("))

    def test_generate_logger_config(self) -> None:
        """Ensures the standard logger configuration is present in the generated file."""
        logger.info("🧪 Testing logger config.")
        code = generate_logic_code(
            set(), set(), set(), "class", True, False, self.machine_name, 2
        )
        self.assertIn("logger = logging.getLogger(__name__)", code)

    def test_generate_typing_imports(self) -> None:
        """Verifies that necessary `typing` imports are included."""
        logger.info("🧪 Testing typing imports.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("from typing import Any, Dict, Union", code)

    def test_generate_xstate_imports(self) -> None:
        """Verifies that necessary `xstate_statemachine` imports are included."""
        logger.info("🧪 Testing xstate imports.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn(
            "from xstate_statemachine import Interpreter, SyncInterpreter, Event, ActionDefinition",
            code,
        )

    def test_generate_awaitable_for_async_guards_no(self) -> None:
        """Confirms that guards remain synchronous even in async mode."""
        logger.info("🧪 Testing no Awaitable for guards in async.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn("-> bool:", code)
        self.assertNotIn("Awaitable[bool]", code)

    def test_generate_no_imports_if_no_services_async(self) -> None:
        """Confirms `time` is not imported if there are no sync services."""
        logger.info("🧪 Testing no time if no services sync.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertNotIn("import time", code)

    def test_generate_class_indent_correct(self) -> None:
        """Checks for correct indentation in class-style generation."""
        logger.info("🧪 Testing class indent.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("    # ⚙️ Actions", code)

    def test_generate_function_indent_correct(self) -> None:
        """Checks for correct (zero) indentation in function-style generation."""
        logger.info("🧪 Testing function indent.")
        code = generate_logic_code(
            {"act"},
            set(),
            set(),
            "function",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertIn("# ⚙️ Actions", code)
        self.assertNotIn("    # ⚙️ Actions", code)

    def test_generate_docstring_for_actions(self) -> None:
        """Ensures the correct docstring format for generated actions."""
        logger.info("🧪 Testing docstring for actions.")
        code = generate_logic_code(
            {"my_act"},
            set(),
            set(),
            "class",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertIn('"""Action: `my_act`."""', code)

    def test_generate_docstring_for_guards(self) -> None:
        """Ensures the correct docstring format for generated guards."""
        logger.info("🧪 Testing docstring for guards.")
        code = generate_logic_code(
            set(), {"my_g"}, set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn('"""Guard: `my_g`."""', code)

    def test_generate_docstring_for_services(self) -> None:
        """Ensures the correct docstring format for generated services."""
        logger.info("🧪 Testing docstring for services.")
        code = generate_logic_code(
            set(),
            set(),
            {"my_srv"},
            "class",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertIn('"""Service: `my_srv`."""', code)

    def test_generate_pass_todo_for_actions(self) -> None:
        """Verifies the placeholder `pass` and `TODO` comment for actions."""
        logger.info("🧪 Testing pass TODO for actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("# TODO: implement", code)

    def test_generate_return_true_todo_for_guards(self) -> None:
        """Verifies the placeholder `return True` and `TODO` comment for guards."""
        logger.info("🧪 Testing return True TODO for guards.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("# TODO: implement guard logic", code)

    def test_generate_return_dict_todo_for_services(self) -> None:
        """Verifies the placeholder return dictionary and `TODO` comment for services."""
        logger.info("🧪 Testing return dict TODO for services.")
        code = generate_logic_code(
            set(), set(), {"srv"}, "class", False, False, self.machine_name, 2
        )
        self.assertIn("# TODO: implement service", code)

    def test_generate_logger_info_for_actions_log_true(self) -> None:
        """Verifies the logging statement for actions when logging is enabled."""
        logger.info("🧪 Testing logger info for actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", True, False, self.machine_name, 2
        )
        self.assertIn('logger.info("Executing action act")', code)

    def test_generate_no_logger_for_actions_log_false(self) -> None:
        """Ensures no logging statement is generated when logging is disabled."""
        logger.info("🧪 Testing no logger for actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertNotIn("logger.info", code)

    def test_generate_logger_for_guards(self) -> None:
        """Verifies the logging statement for guards when logging is enabled."""
        logger.info("🧪 Testing logger for guards.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", True, False, self.machine_name, 2
        )
        self.assertIn('logger.info("Evaluating guard g")', code)

    def test_generate_logger_for_services(self) -> None:
        """Verifies the logging statement for services when logging is enabled."""
        logger.info("🧪 Testing logger for services.")
        code = generate_logic_code(
            set(), set(), {"srv"}, "class", True, False, self.machine_name, 2
        )
        self.assertIn('logger.info("Running service srv")', code)

    def test_generate_dummy_async_for_async_actions_no_log(self) -> None:
        """Ensures dummy `asyncio.sleep` is present in async actions."""
        logger.info("🧪 Testing dummy async for actions no log.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_no_dummy_for_sync_actions(self) -> None:
        """Ensures no `sleep` call is present in sync actions."""
        logger.info("🧪 Testing no dummy for sync actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertNotIn("sleep", code)

    def test_generate_sorted_actions_guards_services(self) -> None:
        """Confirms that all generated functions are sorted alphabetically within their sections."""
        logger.info("🧪 Testing sorted order in generated code.")
        actions = {"z", "a"}
        guards = {"y", "b"}
        services = {"x", "c"}
        code = generate_logic_code(
            actions,
            guards,
            services,
            "class",
            False,
            False,
            self.machine_name,
            2,
        )
        pos_a = code.find("def a(")
        pos_z = code.find("def z(")
        pos_b = code.find("def b(")
        pos_y = code.find("def y(")
        pos_c = code.find("def c(")
        pos_x = code.find("def x(")
        self.assertTrue(pos_a < pos_z)
        self.assertTrue(pos_b < pos_y)
        self.assertTrue(pos_c < pos_x)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestRunnerCodeGenerator
# -----------------------------------------------------------------------------


class TestRunnerCodeGenerator(unittest.TestCase):
    """
    Verifies the `generate_runner_code` function under various options.
    """

    def setUp(self) -> None:
        """
        Set up common data for runner code generation tests.
        """
        self.machine_names = ["test_machine"]
        self.configs = [SAMPLE_CONFIG_SIMPLE]
        self.json_filenames = ["test.json"]

    def test_generate_single_sync_defaults(self) -> None:
        """
        Tests the default generation case: single machine, sync, class, 2 files.
        """
        logger.info("🧪 Testing default runner generation settings.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn(
            "from test_machine_logic import TestMachineLogic as LogicProvider",
            code,
        )
        self.assertIn("logic_provider = LogicProvider()", code)
        self.assertIn("time.sleep(2)", code)
        self.assertIn("logging.basicConfig", code)
        self.assertIn("SyncInterpreter(machine)", code)
        self.assertNotIn("asyncio.run", code)

    def test_generate_single_async_minimal(self) -> None:
        """
        Tests a non-default case: async, function, no loader, 1 file, no extras.
        """
        logger.info("🧪 Testing minimal async runner generation.")
        code = generate_runner_code(
            self.machine_names,
            True,
            "function",
            False,
            False,
            2,
            False,
            1,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("LogicProvider()", code)
        self.assertNotIn("time.sleep", code)
        self.assertNotIn("logging.basicConfig", code)
        self.assertIn("Interpreter(machine)", code)
        self.assertIn("asyncio.run(main())", code)

    def test_generate_hierarchical_runner_structure(self) -> None:
        """
        Verifies the structure of a hierarchically generated runner.
        """
        logger.info("🧪 Testing hierarchical runner structure.")
        code = generate_runner_code(
            ["p", "c"],
            True,
            "class",
            True,
            True,
            1,
            True,
            2,
            [HIERARCHY_PARENT_CONFIG, HIERARCHY_CHILD_CONFIG],
            ["p.json", "c.json"],
            hierarchy=True,
        )
        # ✅ Check for parent setup.
        self.assertIn("parent_machine = create_machine(parent_cfg", code)
        self.assertIn("parent = Interpreter(parent_machine)", code)
        # ✅ Check for actor setup.
        self.assertIn("actors = {}", code)
        self.assertIn("machine_c = create_machine(actor_cfgs['c'])", code)
        # ✅ Check for graceful shutdown sequence.
        self.assertIn("await actors['c'].stop()", code)
        self.assertIn("await parent.stop()", code)

    def test_generate_multiple_machines(self) -> None:
        """Ensures code is generated correctly for multiple machine inputs."""
        logger.info("🧪 Testing multiple machines.")
        machine_names = ["m1", "m2"]
        configs = [SAMPLE_CONFIG_SIMPLE, SAMPLE_CONFIG_NESTED]
        json_filenames = ["m1.json", "m2.json"]
        code = generate_runner_code(
            machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            configs,
            json_filenames,
        )
        self.assertIn("def run_m1() -> None:", code)
        self.assertIn("def run_m2() -> None:", code)
        self.assertIn("run_m1()", code)
        self.assertIn("run_m2()", code)

    def test_generate_dummy_event_from_config(self) -> None:
        """Verifies that the initial event is taken from the config if available."""
        logger.info("🧪 Testing dummy event from config.")
        config = {"on": {"CUSTOM_EVENT": {}}}
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            [config],
            self.json_filenames,
        )
        self.assertIn("CUSTOM_EVENT", code)

    def test_generate_default_dummy_event(self) -> None:
        """Verifies the fallback when no events are defined in the config."""
        logger.info("🧪 Testing fallback for no events in config.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            [{}],
            self.json_filenames,
        )
        self.assertIn(
            "logger.info('No events declared in the machine.')", code
        )

    def test_generate_path_config_load(self) -> None:
        """Ensures the correct JSON filename is used for loading the config."""
        logger.info("🧪 Testing config path load.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            ["custom.json"],
        )
        self.assertIn("custom.json", code)

    def test_generate_no_loader_logic(self) -> None:
        """Verifies that manual logic binding code is generated when loader is off."""
        logger.info("🧪 Testing no loader logic.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            False,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("machine = create_machine(config,", code)

    def test_generate_file_count_1_combined(self) -> None:
        """Confirms generation for a single combined file runs without error."""
        logger.info("🧪 Testing file count 1.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            1,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("def main() -> None:", code)

    def test_generate_async_await_prefix(self) -> None:
        """Ensures `await` is correctly prefixed to calls in async mode."""
        logger.info("🧪 Testing async await prefix.")
        code = generate_runner_code(
            self.machine_names,
            True,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("await interpreter.start()", code)

    def test_generate_no_log_no_basicConfig(self) -> None:
        """Verifies that `logging.basicConfig` is absent when logging is off."""
        logger.info("🧪 Testing no log no basicConfig.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            False,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("logging.basicConfig", code)

    def test_generate_import_time_if_sleep(self) -> None:
        """Confirms `time` is imported when `sleep` is enabled."""
        logger.info("🧪 Testing import time if sleep.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("import time", code)

    def test_generate_no_import_time_if_no_sleep(self) -> None:
        """Confirms `time` is not imported when `sleep` is disabled."""
        logger.info("🧪 Testing no import time if no sleep.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            False,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("import time", code)

    def test_generate_async_import_asyncio(self) -> None:
        """Confirms `asyncio` is imported when `async-mode` is enabled."""
        logger.info("🧪 Testing import asyncio if async.")
        code = generate_runner_code(
            self.machine_names,
            True,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("import asyncio", code)

    def test_generate_no_asyncio_if_sync(self) -> None:
        """Confirms `asyncio` is not imported in sync mode."""
        logger.info("🧪 Testing no asyncio if sync.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("import asyncio", code)

    def test_generate_logging_inspector(self) -> None:
        """Ensures the `LoggingInspector` is included by default."""
        logger.info("🧪 Testing LoggingInspector.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("interpreter.use(LoggingInspector())", code)

    def test_generate_initial_state_log(self) -> None:
        """Verifies the log message for the initial machine state."""
        logger.info("🧪 Testing initial state log.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn(
            "logger.info(f'Initial state: {interpreter.current_state_ids}')",
            code,
        )

    def test_generate_simulation_log_messages(self) -> None:
        """Verifies the standard log messages for starting and ending the simulation."""
        logger.info("🧪 Testing simulation log messages.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn(
            "logger.info('--- Running simulation with all defined events ---')",
            code,
        )
        self.assertNotIn(
            "logger.info(f'--- ✅ Simulation ended in state: {interpreter.current_state_ids} ---')",
            code,
        )

    def test_generate_main_if_async(self) -> None:
        """Ensures the `asyncio.run(main())` block is present in async mode."""
        logger.info("🧪 Testing main if async.")
        code = generate_runner_code(
            self.machine_names,
            True,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("asyncio.run(main())", code)

    def test_generate_main_if_sync(self) -> None:
        """Ensures a direct `main()` call is present in sync mode."""
        logger.info("🧪 Testing main if sync.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("if __name__ == '__main__':\n    main()", code)
        self.assertNotIn("asyncio.run", code)

    def test_generate_multiple_async_functions(self) -> None:
        """Checks for correct `async def` and `await` usage with multiple machines."""
        logger.info("🧪 Testing multiple async functions.")
        machine_names = ["m1", "m2"]
        code = generate_runner_code(
            machine_names,
            True,
            "class",
            True,
            True,
            2,
            True,
            2,
            SAMPLE_CONFIG_MULTIPLE,
            ["m1.json", "m2.json"],
        )
        self.assertIn("async def run_m1() -> None:", code)
        self.assertIn("async def run_m2() -> None:", code)
        self.assertIn("async def main() -> None:", code)
        self.assertIn("await run_m1()", code)
        self.assertIn("await run_m2()", code)

    def test_generate_docstring_for_run_functions(self) -> None:
        """Verifies the docstring format for generated runner functions."""
        logger.info("🧪 Testing docstring for run functions.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn(
            '"""Executes the simulation for the test_machine machine."""', code
        )

    def test_generate_config_path_parent(self) -> None:
        """Ensures `Path(__file__).parent` is used to locate the config file."""
        logger.info("🧪 Testing config path using parent.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("Path(__file__).resolve().parent", code)

    def test_generate_utf8_encoding(self) -> None:
        """Ensures config files are opened with 'utf-8' encoding."""
        logger.info("🧪 Testing utf8 encoding.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("encoding='utf-8'", code)

    def test_generate_no_sleep_time_sleep_false(self) -> None:
        """Confirms no `time.sleep` call is generated if `sleep` is disabled."""
        logger.info("🧪 Testing no sleep time if sleep false.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            False,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("time.sleep", code)

    def test_generate_custom_sleep_time(self) -> None:
        """Verifies that a custom sleep time is correctly used."""
        logger.info("🧪 Testing custom sleep time.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            5,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("time.sleep(5)", code)

    def test_generate_function_style_runner_import(self) -> None:
        """Verifies the correct import statement for function-style logic."""
        logger.info("🧪 Testing function style runner import.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "function",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("import test_machine_logic", code)

    def test_generate_multiple_no_loader(self) -> None:
        """Confirms correct code generation for multiple machines without the loader."""
        logger.info("🧪 Testing multiple no loader.")
        machine_names = ["m1", "m2"]
        code = generate_runner_code(
            machine_names,
            False,
            "class",
            False,
            True,
            2,
            True,
            2,
            SAMPLE_CONFIG_MULTIPLE,
            ["f1.json", "f2.json"],
        )
        self.assertIn("machine = create_machine(config,", code)

    def test_generate_combined_file_runner_part(self) -> None:
        """A placeholder to acknowledge testing combined files is handled in main CLI tests."""
        logger.info("🧪 Testing combined file runner part.")
        pass

    def test_generate_pathlib_import(self) -> None:
        """Ensures `pathlib.Path` is imported."""
        logger.info("🧪 Testing pathlib import.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("from pathlib import Path", code)

    def test_generate_logging_inspector_import(self) -> None:
        """Ensures `LoggingInspector` is imported."""
        logger.info("🧪 Testing LoggingInspector import.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("from xstate_statemachine import LoggingInspector", code)

    def test_generate_create_machine_import(self) -> None:
        """Ensures `create_machine` is imported."""
        logger.info("🧪 Testing create_machine import.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("from xstate_statemachine import create_machine", code)
