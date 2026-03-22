# tests/tests_cli/test_generator.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Code Generation
# -----------------------------------------------------------------------------
# This module provides a comprehensive suite of unit tests for the functions
# in the `xstate_statemachine.cli.generator` module.
#
# It meticulously verifies that both the logic and runner source code are
# generated correctly based on a wide range of input options and configurations.
# The tests cover various dimensions, including:
#   - Code Style: Class-based vs. function-based generation.
#   - Execution Mode: Asynchronous vs. synchronous code.
#   - Feature Flags: Presence of logging, services, and other features.
#   - Edge Cases: Handling of Python keywords, empty logic sets, etc.
#   - Hierarchical Structures: Correct generation for parent-child machines.
#
# This ensures the code generation engine is robust, predictable, and produces
# high-quality, ready-to-use boilerplate code for developers.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import unittest
from typing import Any, Dict, List, Set

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine.cli.generator import (
    generate_logic_code,
    generate_runner_code,
)

from .fixtures import (
    HIERARCHY_CHILD_CONFIG,
    HIERARCHY_PARENT_CONFIG,
    SAMPLE_CONFIG_MULTIPLE,
    SAMPLE_CONFIG_NESTED,
    SAMPLE_CONFIG_SIMPLE,
)

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
# Set up a logger for detailed output during test execution.
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestLogicCodeGenerator
# -----------------------------------------------------------------------------
class TestLogicCodeGenerator(unittest.TestCase):
    """
    🧪 Verifies the `generate_logic_code` function under various scenarios.

    This test class ensures that the logic file (containing actions, guards,
    and services) is generated correctly according to user-specified options
    like style (class/function), mode (async/sync), and logging.
    """

    def setUp(self) -> None:
        """
         GIVEN common data for the code generation tests.

        This method runs before each test, setting up a consistent baseline
        of actions, guards, services, and a machine name to ensure that
        tests are isolated and repeatable.
        """
        self.actions: Set[str] = {"act1", "act2"}
        self.guards: Set[str] = {"guard1"}
        self.services: Set[str] = {"srv1"}
        self.machine_name: str = "test_machine"

    def test_generate_class_style_sync_with_log(self) -> None:
        """
        ✅ Tests correct generation for: class style, sync mode, with logging.
        """
        logger.info("🧪 Testing class-style, sync generation with logging.")
        # 🎬 ACT: Generate the code with specific options.
        code = generate_logic_code(
            actions=self.actions,
            guards=self.guards,
            services=self.services,
            style="class",
            log=True,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Verify the output contains the correct constructs.
        self.assertIn("class TestMachineLogic:", code)
        self.assertIn('logger.info("Executing action act1")', code)
        self.assertIn("time.sleep(1)", code)
        self.assertNotIn("import asyncio", code)
        self.assertIn("import time", code)

    def test_generate_function_style_async_no_log(self) -> None:
        """
        ✅ Tests correct generation for: function style, async mode, no logging.
        """
        logger.info(
            "🧪 Testing function-style, async generation without logging."
        )
        # 🎬 ACT: Generate the code.
        code = generate_logic_code(
            actions=self.actions,
            guards=self.guards,
            services=self.services,
            style="function",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for function-style and async patterns.
        self.assertNotIn("class ", code)
        self.assertNotIn("logger.info", code)
        self.assertIn("await asyncio.sleep(1)", code)
        self.assertIn("import asyncio", code)
        self.assertNotIn("import time", code)

    def test_generate_no_services_no_time_import(self) -> None:
        """
        ✅ Confirms `time` is not imported in sync mode if there are no services.
        """
        logger.info("🧪 Testing that `time` is not imported without services.")
        # 🎬 ACT: Generate code without any services.
        code = generate_logic_code(
            actions=self.actions,
            guards=self.guards,
            services=set(),
            style="class",
            log=True,
            is_async=False,
            machine_name="test",
            file_count=2,
        )
        # 🧐 ASSERT: Ensure the time module is not imported.
        self.assertNotIn("import time", code)

    def test_generate_keyword_aliasing(self) -> None:
        """
        ✅ Tests that a service named after a Python keyword is handled correctly.
        """
        logger.info("🧪 Testing logic generation for keyword-named services.")
        # 🎬 ACT: Generate code with services named after Python keywords.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"pass", "import"},
            style="class",
            log=False,
            is_async=False,
            machine_name="test",
            file_count=2,
        )
        # 🧐 ASSERT: Check that function names are sanitized and aliased.
        self.assertIn("def pass_(", code)
        self.assertIn("def import_(", code)
        self.assertIn("pass = pass_", code)
        self.assertIn("import = import_", code)

    def test_generate_noqa_comments(self) -> None:
        """
        ✅ Ensures generated logic omits noqa comments for production quality.

        The strategy-based output is production-quality code that does not
        require linter suppression comments. Instead, proper signatures
        avoid the warnings entirely.
        """
        logger.info(
            "🧪 Testing for absence of noqa comments in generated logic."
        )
        # 🎬 ACT: Generate a standard logic file.
        code = generate_logic_code(
            actions={"a"},
            guards={"g"},
            services={"s"},
            style="class",
            log=True,
            is_async=True,
            machine_name="test",
            file_count=2,
        )
        # 🧐 ASSERT: Verify that linter-suppressing comments are NOT present
        # in the production-quality strategy output.
        self.assertNotIn("# noqa", code)

    def test_generate_logic_code_with_service_aliasing(self) -> None:
        """
        ✅ Ensures services with names needing conversion are aliased correctly.
        """
        logger.info("🧪 Testing logic generation with service aliasing.")
        # 🎬 ACT: Generate logic with a camelCase service name.
        logic_code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"myCoolService"},  # A name that will be converted.
            style="class",
            log=False,
            is_async=False,
            machine_name="test",
            file_count=2,
        )
        # 🧐 ASSERT: Verify the name was converted to snake_case and aliased.
        self.assertIn("def my_cool_service(", logic_code)
        self.assertIn("myCoolService = my_cool_service", logic_code)

    def test_generate_with_services_time_import(self) -> None:
        """
        ✅ Confirms `time` is imported in sync mode when services are present.
        """
        logger.info("🧪 Testing `time` import when sync services are present.")
        # 🎬 ACT: Generate sync code with services.
        code = generate_logic_code(
            actions=self.actions,
            guards=self.guards,
            services=self.services,
            style="class",
            log=True,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Ensure the time module is imported for `time.sleep`.
        self.assertIn("import time", code)

    def test_generate_class_name_from_machine_name(self) -> None:
        """
        ✅ Verifies the logic class name is correctly derived from the machine name.
        """
        logger.info("🧪 Testing class name derivation from machine name.")
        # 🎬 ACT: Generate class-style logic with a snake_case machine name.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name="my_machine",
            file_count=2,
        )
        # 🧐 ASSERT: Ensure the machine name is converted to PascalCase for the class.
        self.assertIn("class MyMachineLogic:", code)

    def test_generate_no_actions_guards_services(self) -> None:
        """
        ✅ Ensures code is generated gracefully when there are no logic items.
        """
        logger.info("🧪 Testing graceful generation for empty logic sets.")
        # 🎬 ACT: Generate code with empty action, guard, and service sets.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services=set(),
            style="function",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Verify that the section headers are omitted.
        self.assertNotIn("# ⚙️ Actions", code)
        self.assertNotIn("# 🛡️ Guards", code)
        self.assertNotIn("# 🔄 Services", code)

    def test_generate_async_actions(self) -> None:
        """
        ✅ Checks for `async def` and `await` in generated async actions.
        """
        logger.info("🧪 Testing async action generation.")
        # 🎬 ACT: Generate async code with a single action.
        code = generate_logic_code(
            actions={"async_act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for async keywords.
        self.assertIn("async def async_act(", code)
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_sync_guards_no_log(self) -> None:
        """
        ✅ Verifies a simple sync guard is generated without logging when disabled.
        """
        logger.info("🧪 Testing sync guard generation without logging.")
        # 🎬 ACT: Generate a sync guard with logging disabled.
        code = generate_logic_code(
            actions=set(),
            guards={"sync_g"},
            services=set(),
            style="function",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Ensure no logging call is present and it returns a boolean.
        self.assertNotIn("logger.info", code)
        self.assertIn("return True", code)

    def test_generate_services_async(self) -> None:
        """
        ✅ Checks for `async def` and `await` in generated async services.
        """
        logger.info("🧪 Testing async service generation.")
        # 🎬 ACT: Generate an async service with logging.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"async_srv"},
            style="class",
            log=True,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for async keywords and logging.
        self.assertIn("async def async_srv(", code)
        self.assertIn("await asyncio.sleep(1)", code)
        self.assertIn('logger.info("Running service async_srv")', code)

    def test_generate_services_sync(self) -> None:
        """
        ✅ Checks for `time.sleep` in generated sync services.
        """
        logger.info("🧪 Testing sync service generation.")
        # 🎬 ACT: Generate a sync service without logging.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"sync_srv"},
            style="function",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for sync implementation details.
        self.assertIn("def sync_srv(", code)
        self.assertIn("time.sleep(1)", code)
        self.assertNotIn("logger.info", code)

    def test_generate_interpreter_type_in_params(self) -> None:
        """
        ✅ Ensures the interpreter type hint includes both sync and async variants.
        """
        logger.info("🧪 Testing interpreter type hint in function parameters.")
        # 🎬 ACT: Generate code for both sync and async modes.
        code_sync = generate_logic_code(  # noqa: ignore=E501
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        code_async = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Verify the Union type hint is present in both cases.
        expected_hint = "interpreter: Union[Interpreter, SyncInterpreter],"
        self.assertIn(expected_hint, code_sync)
        self.assertIn(expected_hint, code_async)

    def test_generate_return_type_for_actions(self) -> None:
        """
        ✅ Ensures action return type hint is `None` for both sync and async.

        The strategy-based output uses `-> None:` for all actions (even async),
        because async functions implicitly return a coroutine and the return
        type annotation should reflect the unwrapped type.
        """
        logger.info("🧪 Testing return type hints for actions.")
        # 🎬 ACT: Generate both sync and async actions.
        code_sync = generate_logic_code(  # noqa: ignore=E501
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        code_async = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Both sync and async actions return None.
        self.assertIn("-> None:", code_sync)
        self.assertIn("-> None:", code_async)

    def test_generate_return_type_for_services(self) -> None:
        """
        ✅ Ensures service return type is `Dict[str, Any]` for both sync and async.

        The strategy-based output uses `-> Dict[str, Any]:` for all services
        (even async), because async functions implicitly return a coroutine
        and the return type annotation should reflect the unwrapped type.
        """
        logger.info("🧪 Testing return type hints for services.")
        # 🎬 ACT: Generate both sync and async services.
        code_sync = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"srv"},
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        code_async = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"srv"},
            style="class",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Both sync and async services return Dict[str, Any].
        self.assertIn("-> Dict[str, Any]:", code_sync)
        self.assertIn("-> Dict[str, Any]:", code_async)

    def test_generate_guards_return_bool(self) -> None:
        """
        ✅ Verifies that generated guards are correctly type-hinted to return `bool`.
        """
        logger.info("🧪 Testing boolean return type hint for guards.")
        # 🎬 ACT: Generate a guard function.
        code = generate_logic_code(
            actions=set(),
            guards={"g"},
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Ensure the return type is bool.
        self.assertIn("-> bool:", code)

    def test_generate_function_style_no_self(self) -> None:
        """
        ✅ Confirms that 'self' is not included in function-style logic.
        """
        logger.info("🧪 Testing for absence of `self` in function-style.")
        # 🎬 ACT: Generate function-style code.
        code = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="function",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Ensure 'self' is not in the function signature.
        self.assertNotIn("self,", code)

    def test_generate_dummy_sleep_if_no_log(self) -> None:
        """
        ✅ Ensures dummy `asyncio.sleep` is present in async actions even if logging is off.
        """
        logger.info("🧪 Testing for dummy async sleep without logging.")
        # 🎬 ACT: Generate an async action with logging disabled.
        code = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: The placeholder sleep should still be present to make it awaitable.
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_sorted_names(self) -> None:
        """
        ✅ Verifies that generated functions are sorted alphabetically.
        """
        logger.info("🧪 Testing alphabetical sorting of generated functions.")
        # 🎬 ACT: Generate code with unsorted action names.
        actions = {"z_act", "a_act"}
        code = generate_logic_code(
            actions=actions,
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check that 'a_act' appears before 'z_act' in the output.
        self.assertTrue(code.find("def a_act(") < code.find("def z_act("))

    def test_generate_logger_config(self) -> None:
        """
        ✅ Ensures the standard logger configuration is present when logging is enabled.
        """
        logger.info("🧪 Testing for logger configuration presence.")
        # 🎬 ACT: Generate code with logging enabled.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services=set(),
            style="class",
            log=True,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: The standard logger setup line must be present.
        self.assertIn("logger = logging.getLogger(__name__)", code)

    def test_generate_typing_imports(self) -> None:
        """
        ✅ Verifies that necessary `typing` imports are included for type hints.
        """
        logger.info("🧪 Testing for presence of necessary `typing` imports.")
        # 🎬 ACT: Generate logic code for an async machine, which requires more types.
        code = generate_logic_code(
            actions={"a"},
            guards={"g"},
            services={"s"},
            style="class",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )

        # 🧐 ASSERT: Check that all required typing components are imported.
        # The strategy-based output no longer uses Awaitable (async functions
        # annotate their return type directly), but still needs the other types.
        self.assertIn("from typing import", code)
        self.assertIn("Any", code)
        self.assertIn("Dict", code)
        self.assertIn("Union", code)

    def test_generate_xstate_imports(self) -> None:
        """
        ✅ Verifies that necessary `xstate_statemachine` imports are included.
        """
        logger.info(
            "🧪 Testing for presence of `xstate_statemachine` imports."
        )
        # 🎬 ACT: Generate any logic code.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for core library imports.
        self.assertIn(
            "from xstate_statemachine import Interpreter, SyncInterpreter, Event, ActionDefinition",
            code,
        )

    def test_generate_awaitable_for_async_guards_no(self) -> None:
        """
        ✅ Confirms that guards remain synchronous (no Awaitable) even in async mode.
        """
        logger.info(
            "🧪 Testing that guards are always sync, even in async mode."
        )
        # 🎬 ACT: Generate a guard in async mode.
        code = generate_logic_code(
            actions=set(),
            guards={"g"},
            services=set(),
            style="class",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: The return type must be `bool`, not `Awaitable[bool]`.
        self.assertIn("-> bool:", code)
        self.assertNotIn("Awaitable[bool]", code)

    def test_generate_no_imports_if_no_services_async(self) -> None:
        """
        ✅ Confirms `time` is not imported if there are no sync services.
        """
        logger.info("🧪 Testing `time` is not imported without sync services.")
        # 🎬 ACT: Generate code without services in sync mode.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: `time` should not be imported.
        self.assertNotIn("import time", code)

    def test_generate_class_indent_correct(self) -> None:
        """
        ✅ Checks for correct indentation in class-style generation.
        """
        logger.info("🧪 Testing indentation for class-style generation.")
        # 🎬 ACT: Generate class-style code.
        code = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Content within the class should be indented.
        # Strategy output uses plain section titles without emojis.
        self.assertIn("    # Actions", code)

    def test_generate_function_indent_correct(self) -> None:
        """
        ✅ Checks for correct (zero) indentation in function-style generation.
        """
        logger.info("🧪 Testing indentation for function-style generation.")
        # 🎬 ACT: Generate function-style code.
        code = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="function",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Section header should be at module level (no leading indent).
        # Strategy output uses a section header block with "# Actions" title.
        self.assertIn("# Actions", code)
        self.assertNotIn("    # Actions", code)

    def test_generate_docstring_for_actions(self) -> None:
        """
        ✅ Ensures the correct docstring format for generated actions.
        """
        logger.info("🧪 Testing docstring format for actions.")
        # 🎬 ACT: Generate an action.
        code = generate_logic_code(
            actions={"my_act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for the rich docstring format from the strategy.
        self.assertIn("Execute the ``my_act`` action.", code)

    def test_generate_docstring_for_guards(self) -> None:
        """
        ✅ Ensures the correct docstring format for generated guards.
        """
        logger.info("🧪 Testing docstring format for guards.")
        # 🎬 ACT: Generate a guard.
        code = generate_logic_code(
            actions=set(),
            guards={"my_g"},
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for the rich docstring format from the strategy.
        self.assertIn("Evaluate the ``my_g`` guard.", code)

    def test_generate_docstring_for_services(self) -> None:
        """
        ✅ Ensures the correct docstring format for generated services.
        """
        logger.info("🧪 Testing docstring format for services.")
        # 🎬 ACT: Generate a service.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"my_srv"},
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for the rich docstring format from the strategy.
        self.assertIn("Run the ``my_srv`` service.", code)

    def test_generate_pass_todo_for_actions(self) -> None:
        """
        ✅ Verifies the placeholder `pass` and `TODO` comment for actions.
        """
        logger.info("🧪 Testing placeholder content for actions.")
        # 🎬 ACT: Generate an action.
        code = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for the TODO comment.
        self.assertIn("# TODO: implement", code)

    def test_generate_return_true_todo_for_guards(self) -> None:
        """
        ✅ Verifies the placeholder `return True` and `TODO` comment for guards.
        """
        logger.info("🧪 Testing placeholder content for guards.")
        # 🎬 ACT: Generate a guard.
        code = generate_logic_code(
            actions=set(),
            guards={"g"},
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for the TODO comment and default return.
        self.assertIn("# TODO: implement guard logic", code)

    def test_generate_return_dict_todo_for_services(self) -> None:
        """
        ✅ Verifies the placeholder return dict and `TODO` comment for services.
        """
        logger.info("🧪 Testing placeholder content for services.")
        # 🎬 ACT: Generate a service.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"srv"},
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for the TODO comment and default return.
        self.assertIn("# TODO: implement service", code)

    def test_generate_logger_info_for_actions_log_true(self) -> None:
        """
        ✅ Verifies the logging statement for actions when logging is enabled.
        """
        logger.info("🧪 Testing logger info statement for actions.")
        # 🎬 ACT: Generate an action with logging on.
        code = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=True,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for the specific log message.
        self.assertIn('logger.info("Executing action act")', code)

    def test_generate_no_logger_for_actions_log_false(self) -> None:
        """
        ✅ Ensures no logging statement is generated when logging is disabled.
        """
        logger.info("🧪 Testing for absence of logger statement for actions.")
        # 🎬 ACT: Generate an action with logging off.
        code = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Ensure no logging calls are present.
        self.assertNotIn("logger.info", code)

    def test_generate_logger_for_guards(self) -> None:
        """
        ✅ Verifies the logging statement for guards when logging is enabled.
        """
        logger.info("🧪 Testing logger info statement for guards.")
        # 🎬 ACT: Generate a guard with logging on.
        code = generate_logic_code(
            actions=set(),
            guards={"g"},
            services=set(),
            style="class",
            log=True,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for the specific log message.
        self.assertIn('logger.info("Evaluating guard g")', code)

    def test_generate_logger_for_services(self) -> None:
        """
        ✅ Verifies the logging statement for services when logging is enabled.
        """
        logger.info("🧪 Testing logger info statement for services.")
        # 🎬 ACT: Generate a service with logging on.
        code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"srv"},
            style="class",
            log=True,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Check for the specific log message.
        self.assertIn('logger.info("Running service srv")', code)

    def test_generate_dummy_async_for_async_actions_no_log(self) -> None:
        """
        ✅ Ensures dummy `asyncio.sleep` is present in async actions without logging.
        """
        logger.info("🧪 Testing dummy async sleep in actions without logs.")
        # 🎬 ACT: Generate an async action with logging off.
        code = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=True,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: The placeholder sleep makes the function awaitable.
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_no_dummy_for_sync_actions(self) -> None:
        """
        ✅ Ensures no `sleep` call is present in sync actions by default.
        """
        logger.info("🧪 Testing for absence of sleep call in sync actions.")
        # 🎬 ACT: Generate a sync action.
        code = generate_logic_code(
            actions={"act"},
            guards=set(),
            services=set(),
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: No sleep call should be present as it's not needed.
        self.assertNotIn("sleep", code)

    def test_generate_sorted_actions_guards_services(self) -> None:
        """
        ✅ Confirms all logic functions are sorted alphabetically within sections.
        """
        logger.info("🧪 Testing alphabetical sorting across all logic types.")
        # 🎬 ACT: Generate code with unsorted names for all logic types.
        actions = {"z", "a"}
        guards = {"y", "b"}
        services = {"x", "c"}
        code = generate_logic_code(
            actions=actions,
            guards=guards,
            services=services,
            style="class",
            log=False,
            is_async=False,
            machine_name=self.machine_name,
            file_count=2,
        )
        # 🧐 ASSERT: Verify the alphabetical order within each section.
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
    🧪 Verifies the `generate_runner_code` function under various scenarios.

    This test class ensures the runner file (the executable entry point) is
    generated correctly, handling single vs. multiple machines, hierarchical
    setups, async vs. sync modes, and other command-line options.
    """

    def setUp(self) -> None:
        """
        GIVEN common data for the runner code generation tests.

        This method prepares baseline data including machine names, configurations,
        and filenames to ensure tests are consistent and independent.
        """
        self.machine_names: List[str] = ["test_machine"]
        self.configs: List[Dict[str, Any]] = [SAMPLE_CONFIG_SIMPLE]
        self.json_filenames: List[str] = ["test.json"]

    def test_generate_single_sync_defaults(self) -> None:
        """
        ✅ Tests the default generation case: single machine, sync, class, 2 files.
        """
        logger.info("🧪 Testing default runner generation settings.")
        # 🎬 ACT: Generate the runner code with default-like settings.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: Verify key elements for a default sync runner.
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
        ✅ Tests a non-default case: async, function, no loader, 1 file, no extras.
        """
        logger.info("🧪 Testing minimal async runner generation.")
        # 🎬 ACT: Generate with minimal async settings.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=True,
            style="function",
            loader=False,
            sleep=False,
            sleep_time=2,
            log=False,
            file_count=1,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: Check for async, function-style, minimal features.
        self.assertNotIn("LogicProvider()", code)
        self.assertNotIn("time.sleep", code)
        self.assertNotIn("logging.basicConfig", code)
        self.assertIn("Interpreter(machine)", code)
        self.assertIn("asyncio.run(main())", code)

    def test_generate_hierarchical_runner_structure(self) -> None:
        """
        ✅ Verifies the structure of a hierarchically generated runner.
        """
        logger.info("🧪 Testing hierarchical runner structure.")
        # 🎬 ACT: Generate a runner for a parent machine with a child actor.
        code = generate_runner_code(
            machine_names=["p", "c"],
            is_async=True,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=1,
            log=True,
            file_count=2,
            configs=[HIERARCHY_PARENT_CONFIG, HIERARCHY_CHILD_CONFIG],
            json_filenames=["p.json", "c.json"],
            hierarchy=True,
        )
        # 🧐 ASSERT: Check for parent setup, actor spawning, and graceful shutdown.
        self.assertIn("parent_machine = create_machine(parent_cfg", code)
        self.assertIn("parent = Interpreter(parent_machine)", code)
        self.assertIn("actors = {}", code)
        self.assertIn("machine_c = create_machine(actor_cfgs['c'])", code)
        self.assertIn("await actors['c'].stop()", code)
        self.assertIn("await parent.stop()", code)

    def test_generate_multiple_machines(self) -> None:
        """
        ✅ Ensures code is generated correctly for multiple, separate machine inputs.
        """
        logger.info("🧪 Testing generation for multiple machines.")
        # 🎬 ACT: Generate a runner for two independent machines.
        code = generate_runner_code(
            machine_names=["m1", "m2"],
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=[SAMPLE_CONFIG_SIMPLE, SAMPLE_CONFIG_NESTED],
            json_filenames=["m1.json", "m2.json"],
        )
        # 🧐 ASSERT: Check for separate run functions and calls in main.
        self.assertIn("def run_m1() -> None:", code)
        self.assertIn("def run_m2() -> None:", code)
        self.assertIn("run_m1()", code)
        self.assertIn("run_m2()", code)

    def test_generate_dummy_event_from_config(self) -> None:
        """
        ✅ Verifies the initial event is taken from the config if available.
        """
        logger.info("🧪 Testing that the dummy event is derived from config.")
        # 🎬 ACT: Generate with a config that has a clear initial event.
        config = {"on": {"CUSTOM_EVENT": {}}}
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=[config],
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: Ensure the custom event is used in the simulation.
        self.assertIn("CUSTOM_EVENT", code)

    def test_generate_default_dummy_event(self) -> None:
        """
        ✅ Verifies the fallback behavior when no events are defined in the config.
        """
        logger.info("🧪 Testing fallback behavior for eventless configs.")
        # 🎬 ACT: Generate with a config that has no top-level 'on' events.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=[{}],
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: Ensure the code logs a message about the absence of events.
        self.assertIn(
            "logger.info('No events declared in the machine.')", code
        )

    def test_generate_path_config_load(self) -> None:
        """
        ✅ Ensures the correct JSON filename is used for loading the config.
        """
        logger.info("🧪 Testing that the correct config file path is used.")
        # 🎬 ACT: Generate with a custom JSON filename.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=["custom.json"],
        )
        # 🧐 ASSERT: The custom filename should be in the file loading logic.
        self.assertIn("custom.json", code)

    def test_generate_no_loader_logic(self) -> None:
        """
        ✅ Verifies manual logic binding code is generated when loader is off.
        """
        logger.info("🧪 Testing generation without the dynamic loader.")
        # 🎬 ACT: Generate with `loader=False`.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=False,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: Logic should be passed directly to `create_machine`.
        self.assertIn("machine = create_machine(config,", code)

    def test_generate_file_count_1_combined(self) -> None:
        """
        ✅ Confirms generation for a single combined file runs without error.
        """
        logger.info("🧪 Testing single-file generation mode.")
        # 🎬 ACT: Generate with `file_count=1`.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=1,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: A main function should be present, indicating a runnable script.
        self.assertIn("def main() -> None:", code)

    def test_generate_async_await_prefix(self) -> None:
        """
        ✅ Ensures `await` is correctly prefixed to calls in async mode.
        """
        logger.info("🧪 Testing for `await` prefixes in async mode.")
        # 🎬 ACT: Generate an async runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=True,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: Interpreter calls should be awaited.
        self.assertIn("await interpreter.start()", code)

    def test_generate_no_log_no_basic_config(self) -> None:
        """
        ✅ Verifies `logging.basicConfig` is absent when logging is off.
        """
        logger.info(
            "🧪 Testing for absence of `basicConfig` when logging is off."
        )
        # 🎬 ACT: Generate a runner with `log=False`.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=False,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The logging setup call should not be present.
        self.assertNotIn("logging.basicConfig", code)

    def test_generate_import_time_if_sleep(self) -> None:
        """
        ✅ Confirms `time` is imported when `sleep` is enabled.
        """
        logger.info("🧪 Testing for `time` import when sleep is enabled.")
        # 🎬 ACT: Generate a sync runner with `sleep=True`.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The time module must be imported.
        self.assertIn("import time", code)

    def test_generate_no_import_time_if_no_sleep(self) -> None:
        """
        ✅ Confirms `time` is not imported when `sleep` is disabled.
        """
        logger.info(
            "🧪 Testing for absence of `time` import when sleep is disabled."
        )
        # 🎬 ACT: Generate a sync runner with `sleep=False`.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=False,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The time module should not be imported.
        self.assertNotIn("import time", code)

    def test_generate_async_import_asyncio(self) -> None:
        """
        ✅ Confirms `asyncio` is imported when `async-mode` is enabled.
        """
        logger.info("🧪 Testing for `asyncio` import in async mode.")
        # 🎬 ACT: Generate an async runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=True,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The asyncio module must be imported.
        self.assertIn("import asyncio", code)

    def test_generate_no_asyncio_if_sync(self) -> None:
        """
        ✅ Confirms `asyncio` is not imported in sync mode.
        """
        logger.info("🧪 Testing for absence of `asyncio` import in sync mode.")
        # 🎬 ACT: Generate a sync runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The asyncio module should not be imported.
        self.assertNotIn("import asyncio", code)

    def test_generate_logging_inspector(self) -> None:
        """
        ✅ Ensures the `LoggingInspector` is included when logging is enabled.
        """
        logger.info("🧪 Testing for `LoggingInspector` usage.")
        # 🎬 ACT: Generate a runner with logging enabled.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The inspector should be attached to the interpreter.
        self.assertIn("interpreter.use(LoggingInspector())", code)

    def test_generate_initial_state_log(self) -> None:
        """
        ✅ Verifies the log message for the initial machine state.
        """
        logger.info("🧪 Testing for the initial state log message.")
        # 🎬 ACT: Generate a runner with logging enabled.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The log message reporting the initial state should be present.
        self.assertIn(
            "logger.info(f'Initial state: {interpreter.current_state_ids}')",
            code,
        )

    def test_generate_simulation_log_messages(self) -> None:
        """
        ✅ Verifies the absence of old simulation log messages.
        """
        logger.info("🧪 Testing that old simulation log messages are removed.")
        # 🎬 ACT: Generate a standard runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: Ensure outdated, verbose log messages are no longer generated.
        self.assertNotIn(
            "logger.info('--- Running simulation with all defined events ---')",
            code,
        )
        self.assertNotIn(
            "logger.info(f'--- ✅ Simulation ended in state: {interpreter.current_state_ids} ---')",
            code,
        )

    def test_generate_main_if_async(self) -> None:
        """
        ✅ Ensures the `asyncio.run(main())` block is present in async mode.
        """
        logger.info("🧪 Testing for `asyncio.run(main())` in async mode.")
        # 🎬 ACT: Generate an async runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=True,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The standard async entry point should be used.
        self.assertIn("asyncio.run(main())", code)

    def test_generate_main_if_sync(self) -> None:
        """
        ✅ Ensures a direct `main()` call is present in sync mode.
        """
        logger.info("🧪 Testing for direct `main()` call in sync mode.")
        # 🎬 ACT: Generate a sync runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The standard script entry point should call main directly.
        self.assertIn("if __name__ == '__main__':\n    main()", code)
        self.assertNotIn("asyncio.run", code)

    def test_generate_multiple_async_functions(self) -> None:
        """
        ✅ Checks for correct `async def` and `await` with multiple machines.
        """
        logger.info("🧪 Testing async generation for multiple machines.")
        # 🎬 ACT: Generate an async runner for two machines.
        code = generate_runner_code(
            machine_names=["m1", "m2"],
            is_async=True,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=SAMPLE_CONFIG_MULTIPLE,
            json_filenames=["m1.json", "m2.json"],
        )
        # 🧐 ASSERT: All generated functions should be async and correctly awaited.
        self.assertIn("async def run_m1() -> None:", code)
        self.assertIn("async def run_m2() -> None:", code)
        self.assertIn("async def main() -> None:", code)
        self.assertIn("await run_m1()", code)
        self.assertIn("await run_m2()", code)

    def test_generate_docstring_for_run_functions(self) -> None:
        """
        ✅ Verifies the docstring format for generated runner functions.
        """
        logger.info("🧪 Testing docstring format for runner functions.")
        # 🎬 ACT: Generate a standard runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: Check for the specific docstring format.
        self.assertIn(
            '"""Executes the simulation for the test_machine machine."""', code
        )

    def test_generate_config_path_parent(self) -> None:
        """
        ✅ Ensures `Path(__file__).parent` is used to locate the config file.
        """
        logger.info("🧪 Testing that config path is relative to the file.")
        # 🎬 ACT: Generate a standard runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The code should use pathlib to build a robust path.
        self.assertIn("Path(__file__).resolve().parent", code)

    def test_generate_utf8_encoding(self) -> None:
        """
        ✅ Ensures config files are opened with 'utf-8' encoding.
        """
        logger.info("🧪 Testing for 'utf-8' encoding when opening files.")
        # 🎬 ACT: Generate a standard runner that loads a JSON file.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The open call must specify UTF-8 encoding.
        self.assertIn("encoding='utf-8'", code)

    def test_generate_no_sleep_time_sleep_false(self) -> None:
        """
        ✅ Confirms no `time.sleep` call is generated if `sleep` is disabled.
        """
        logger.info("🧪 Testing for absence of `time.sleep` when disabled.")
        # 🎬 ACT: Generate a runner with `sleep=False`.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=False,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The sleep call should not be present.
        self.assertNotIn("time.sleep", code)

    def test_generate_custom_sleep_time(self) -> None:
        """
        ✅ Verifies that a custom sleep time is correctly used.
        """
        logger.info("🧪 Testing that a custom sleep time is applied.")
        # 🎬 ACT: Generate a runner with a custom `sleep_time`.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=5,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The sleep call should use the specified custom time.
        self.assertIn("time.sleep(5)", code)

    def test_generate_function_style_runner_import(self) -> None:
        """
        ✅ Verifies the correct import statement for function-style logic.
        """
        logger.info("🧪 Testing logic import for function-style runners.")
        # 🎬 ACT: Generate a function-style runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="function",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The logic should be imported as a module, not a class.
        self.assertIn("import test_machine_logic", code)

    def test_generate_multiple_no_loader(self) -> None:
        """
        ✅ Confirms correct code for multiple machines without the loader.
        """
        logger.info("🧪 Testing multiple machines without the dynamic loader.")
        # 🎬 ACT: Generate for multiple machines with `loader=False`.
        code = generate_runner_code(
            machine_names=["m1", "m2"],
            is_async=False,
            style="class",
            loader=False,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=SAMPLE_CONFIG_MULTIPLE,
            json_filenames=["f1.json", "f2.json"],
        )
        # 🧐 ASSERT: Logic should be passed directly to `create_machine`.
        self.assertIn("machine = create_machine(config,", code)

    def test_generate_combined_file_runner_part(self) -> None:
        """Runner part of combined file includes main guard and interpreter."""
        logger.info("🧪 Verifying combined-file runner generation path.")
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=1,
            configs=self.configs,
            json_filenames=["test.json"],
        )
        self.assertIn("if __name__ == '__main__':", code)
        self.assertIn("SyncInterpreter", code)

    def test_generate_pathlib_import(self) -> None:
        """
        ✅ Ensures `pathlib.Path` is imported for robust file path handling.
        """
        logger.info("🧪 Testing for `pathlib.Path` import.")
        # 🎬 ACT: Generate a standard runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The Path class must be imported.
        self.assertIn("from pathlib import Path", code)

    def test_generate_logging_inspector_import(self) -> None:
        """
        ✅ Ensures `LoggingInspector` is imported when needed.
        """
        logger.info("🧪 Testing for `LoggingInspector` import.")
        # 🎬 ACT: Generate a runner with logging enabled.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The inspector class must be imported.
        self.assertIn("from xstate_statemachine import LoggingInspector", code)

    def test_generate_create_machine_import(self) -> None:
        """
        ✅ Ensures `create_machine` is imported.
        """
        logger.info("🧪 Testing for `create_machine` import.")
        # 🎬 ACT: Generate any standard runner.
        code = generate_runner_code(
            machine_names=self.machine_names,
            is_async=False,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=2,
            log=True,
            file_count=2,
            configs=self.configs,
            json_filenames=self.json_filenames,
        )
        # 🧐 ASSERT: The factory function must be imported.
        self.assertIn("from xstate_statemachine import create_machine", code)
