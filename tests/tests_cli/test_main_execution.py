# tests_cli/test_main_execution.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: End-to-End CLI Execution
# -----------------------------------------------------------------------------
# This module provides full, end-to-end integration tests for the main CLI
# entry point. It simulates command-line execution by patching `sys.argv`
# and verifies the complete workflow, from argument parsing to file output.
#
# The tests are organized into classes based on functionality:
#   -   `TestMainExecution`: Covers flat (non-hierarchical) generation,
#       error handling, and core command-line options.
#   -   `TestHierarchyExecution`: Focuses specifically on parent-child
#       machine generation, including explicit flags and the interactive
#       heuristic detection flow.
# -----------------------------------------------------------------------------
"""
End-to-end integration tests for the main CLI workflow.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import unittest
from io import StringIO
from pathlib import Path
from typing import List
from unittest.mock import patch, MagicMock

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine.cli import main
from src.xstate_statemachine.cli.generator import (
    generate_runner_code,
    generate_logic_code,
)
from xstate_statemachine.cli import __main__

from .base import CLITestCaseBase
from .fixtures import (
    HIERARCHY_CHILD_CONFIG,
    HIERARCHY_PARENT_CONFIG,
    SAMPLE_CONFIG_NESTED,
    SAMPLE_CONFIG_SIMPLE,
    create_temp_json,
)

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestMainExecution
# -----------------------------------------------------------------------------


class TestMainExecution(CLITestCaseBase):
    """
    Tests the main CLI entry point for standard, non-hierarchical scenarios.
    """

    @patch("sys.argv", new_callable=list)
    def test_main_no_json_error(self, mock_argv: List[str]) -> None:
        """
        Ensures the CLI exits with an error if no JSON file is provided.
        """
        logger.info("🧪 Testing error handling for missing JSON file.")
        mock_argv[:] = ["cli.py", "generate-template"]
        with patch(
            "sys.stderr", new=StringIO()
        ) as mock_err, self.assertRaises(SystemExit):
            __main__.main()
        self.assertIn(
            "At least one JSON file is required.", mock_err.getvalue()
        )

    @patch("sys.argv", new_callable=list)
    def test_main_json_not_found(self, mock_argv: List[str]) -> None:
        """
        Ensures the CLI exits if a specified JSON file does not exist.
        """
        logger.info("🧪 Testing error handling for a non-existent JSON file.")
        mock_argv[:] = ["cli.py", "generate-template", "nonexistent.json"]
        with patch(
            "sys.stderr", new=StringIO()
        ) as mock_err, self.assertRaises(SystemExit):
            __main__.main()
        self.assertIn("JSON file not found", mock_err.getvalue())

    @patch("sys.argv", new_callable=list)
    def test_main_generate_single_file(self, mock_argv: List[str]) -> None:
        """
        Verifies that the correct files are generated for a single JSON input.
        """
        logger.info("🧪 Testing file generation for a single machine.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = ["cli.py", "generate-template", str(json_path)]
        with patch("builtins.print") as mock_print:
            __main__.main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("simple_logic.py" in call for call in calls))
        self.assertTrue(any("simple_runner.py" in call for call in calls))

    @patch("sys.argv", new_callable=list)
    def test_main_force_overwrite(self, mock_argv: List[str]) -> None:
        """
        Ensures that the `--force` flag correctly overwrites existing files.
        """
        logger.info("🧪 Testing file overwrite with the --force flag.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        logic_path = Path.cwd() / "simple_logic.py"
        logic_path.write_text("existing content")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--force",
        ]
        __main__.main()
        self.assertNotEqual(
            logic_path.read_text(encoding="utf-8"), "existing content"
        )

    @patch("sys.argv", new_callable=list)
    def test_main_no_force_prompt_and_cancel(
        self, mock_argv: List[str]
    ) -> None:
        """
        Ensures execution stops if files exist and user denies the overwrite prompt.
        """
        logger.info(
            "🧪 Testing cancellation via the interactive overwrite prompt."
        )
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = ["cli.py", "generate-template", str(json_path)]

        # 👟 Run once to create the file.
        __main__.main()
        self.assertTrue(Path.cwd().joinpath("simple_logic.py").exists())
        original_content = (Path.cwd() / "simple_logic.py").read_text(
            encoding="utf-8"
        )

        # 🔄 On the second run, mock the `input` to return 'n' for 'no'.
        with patch("builtins.input", return_value="n") as mock_input, patch(
            "builtins.print"
        ) as mock_print:
            __main__.main()

        # 🕵️ Assert that the prompt was shown.
        mock_input.assert_called_with(
            "File(s) already exist. Overwrite? [Y/n] "
        )
        # 🕵️ Assert that the cancellation message was printed.
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("Operation cancelled." in call for call in calls))
        # 🕵️ Assert that the file was NOT overwritten.
        self.assertEqual(
            original_content,
            (Path.cwd() / "simple_logic.py").read_text(encoding="utf-8"),
        )

    @patch("sys.argv", new_callable=list)
    def test_main_combined_file_merge(self, mock_argv: List[str]) -> None:
        """
        Verifies --file-count 1 correctly merges logic and runner files.
        """
        logger.info("🧪 Testing intelligent merge for combined file output.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--file-count",
            "1",
        ]
        __main__.main()

        combined_file = Path("simple.py")
        self.assertTrue(combined_file.exists())
        content = combined_file.read_text(encoding="utf-8")

        # ✅ Check that key imports and sections are present only once.
        self.assertEqual(content.count("import logging"), 1)
        self.assertEqual(content.count("from pathlib import Path"), 1)
        self.assertIn("# 🧠 Class‑based Logic", content)
        self.assertIn("# Runner part", content)

    @patch("sys.argv", new_callable=list)
    def test_main_generate_multiple(self, mock_argv: List[str]) -> None:
        """Verifies correct combined filenames for multiple JSON inputs."""
        logger.info("🧪 Testing generate multiple.")
        json1 = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        json2 = create_temp_json(SAMPLE_CONFIG_NESTED)
        mock_argv[:] = ["cli.py", "generate-template", str(json1), str(json2)]
        with patch("builtins.input", side_effect=["n", "0"]), patch(
            "builtins.print"
        ) as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("simple_nested_logic.py" in call for call in calls)
        )
        self.assertTrue(
            any("simple_nested_runner.py" in call for call in calls)
        )

    @patch("sys.argv", new_callable=list)
    def test_main_custom_output_dir(self, mock_argv: List[str]) -> None:
        """Verifies that files are created in the specified `--output` directory."""
        logger.info("🧪 Testing custom output dir.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        out_dir = Path(self.temp_dir.name) / "out"
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--output",
            str(out_dir),
        ]
        with patch("builtins.print") as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("simple_logic.py" in call for call in calls))
        self.assertTrue(out_dir.joinpath("simple_logic.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_invalid_bool_value(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits when an invalid boolean-like value is provided."""
        logger.info("🧪 Testing invalid bool value.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--log",
            "invalid",
        ]
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_version(self, mock_argv: List[str]) -> None:
        """Verifies the `--version` argument prints the package version and exits."""
        logger.info("🧪 Testing version arg.")
        mock_argv[:] = ["cli.py", "--version"]
        from src.xstate_statemachine import __version__ as package_version

        with patch(
            "sys.stdout", new=StringIO()
        ) as mock_out, self.assertRaises(SystemExit):
            main()
        self.assertIn(package_version, mock_out.getvalue())

    @patch("sys.argv", new_callable=list)
    def test_main_help(self, mock_argv: List[str]) -> None:
        """Verifies the help message is displayed with `-h` or `--help`."""
        logger.info("🧪 Testing help.")
        mock_argv[:] = ["cli.py", "generate-template", "-h"]
        with patch(
            "sys.stdout", new=StringIO()
        ) as mock_out, self.assertRaises(SystemExit):
            main()
        self.assertIn("usage:", mock_out.getvalue())

    @patch("sys.argv", new_callable=list)
    def test_main_additional_json(self, mock_argv: List[str]) -> None:
        """Ensures the `--json` argument can be used to add config files."""
        logger.info("🧪 Testing --json arg.")
        json1 = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        json2 = create_temp_json(SAMPLE_CONFIG_NESTED)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json",
            str(json1),
            "--json",
            str(json2),
        ]
        with patch("builtins.input", side_effect=["n", "0"]), patch(
            "builtins.print"
        ) as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("simple_nested_logic.py" in call for call in calls)
        )

    @patch("sys.argv", new_callable=list)
    def test_main_invalid_style(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits for an invalid `--style` choice."""
        logger.info("🧪 Testing invalid style.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--style",
            "invalid",
        ]
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_invalid_file_count(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits for an invalid `--file-count` choice."""
        logger.info("🧪 Testing invalid file count.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--file-count",
            "3",
        ]
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_sleep_time_non_int(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits if `--sleep-time` is not an integer."""
        logger.info("🧪 Testing non int sleep time.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--sleep-time",
            "abc",
        ]
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_no_subcommand(self, mock_argv: List[str]) -> None:
        """Ensures the CLI shows an error if no subcommand is provided."""
        logger.info("🧪 Testing no subcommand.")
        mock_argv[:] = ["cli.py"]
        with patch(
            "sys.stderr", new=StringIO()
        ) as mock_err, self.assertRaises(SystemExit):
            main()
        self.assertIn(
            "the following arguments are required: subcommand",
            mock_err.getvalue(),
        )

    @patch("sys.argv", new_callable=list)
    def test_main_output_dir_not_exist_create(
        self, mock_argv: List[str]
    ) -> None:
        """Ensures that a non-existent output directory is created."""
        logger.info("🧪 Testing output dir create.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        out_dir = Path(self.temp_dir.name) / "new_dir"
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--output",
            str(out_dir),
        ]
        main()
        self.assertTrue(out_dir.exists())

    @patch("sys.argv", new_callable=list)
    def test_main_force_no_overwrite_if_not_exist(
        self, mock_argv: List[str]
    ) -> None:
        """Confirms `--force` runs without error when files don't already exist."""
        logger.info("🧪 Testing force no effect if not exist.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--force",
        ]
        main()
        self.assertTrue(Path.cwd().joinpath("simple_logic.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_deduplicates_paths(self, mock_argv: List[str]) -> None:
        """SCENARIO 14: Ensures duplicate file paths are handled correctly."""
        logger.info(
            "🧪 Testing de-duplication of input JSON paths (Scenario 14)."
        )
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),  # Positional
            "--json",
            str(json_path),  # Via --json flag
            "--json-parent",
            str(json_path),  # Via --json-parent flag
        ]

        with patch("builtins.print") as mock_print:
            main()

        # The result should be a simple, single-file generation, not hierarchical.
        # It should NOT create a runner named "simple_simple_runner.py" etc.
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any(
                "Generated logic file: " in call and "simple_logic.py" in call
                for call in calls
            )
        )
        self.assertTrue(
            any(
                "Generated runner file: " in call
                and "simple_runner.py" in call
                for call in calls
            )
        )
        self.assertFalse(
            Path.cwd().joinpath("simple_simple_logic.py").exists()
        )

    @patch("sys.argv", new_callable=list)
    def test_main_multiple_parents_error(self, mock_argv: List[str]) -> None:
        """SCENARIO 17: Ensures an error is raised if multiple parents are specified."""
        logger.info(
            "🧪 Testing error on multiple --json-parent flags (Scenario 17)."
        )
        json1 = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        json2 = create_temp_json(SAMPLE_CONFIG_NESTED)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-parent",
            str(json1),
            "--json-parent",
            str(json2),
        ]

        # This test will pass once cli.py is updated to manually check for this error.
        with patch(
            "sys.stderr", new=StringIO()
        ) as mock_err, self.assertRaises(SystemExit):
            main()

        # Assert the specific error message that your script should raise.
        self.assertIn(
            "Only one --json-parent may be supplied.", mock_err.getvalue()
        )


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestHierarchyExecution
# -----------------------------------------------------------------------------


class TestHierarchyExecution(CLITestCaseBase):
    """
    Tests the main CLI for hierarchical (parent-child) machine generation.
    """

    def setUp(self) -> None:
        """
        Extends the base setup to create shared hierarchical config files.
        """
        super().setUp()
        self.parent_path = create_temp_json(HIERARCHY_PARENT_CONFIG)
        self.child_path = create_temp_json(HIERARCHY_CHILD_CONFIG)

    @patch("sys.argv", new_callable=list)
    def test_main_explicit_parent_child_args(
        self, mock_argv: List[str]
    ) -> None:
        """
        Verifies generation using explicit --json-parent and --json-child flags.
        """
        logger.info("🧪 Testing explicit parent-child flag combination.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-parent",
            str(self.parent_path),
            "--json-child",
            str(self.child_path),
        ]
        with patch("builtins.print"):
            __main__.main()

        # ✅ Check for correctly named output files.
        self.assertTrue(Path("parent_machine_runner.py").exists())
        runner_content = Path("parent_machine_runner.py").read_text(
            encoding="utf-8"
        )
        # ✅ Check for hierarchical runner code constructs.
        self.assertIn("parent_cfg = json.loads", runner_content)
        self.assertIn("actor_cfgs = {", runner_content)
        self.assertIn("'child_machine': json.loads", runner_content)

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["y"])
    def test_main_heuristic_parent_detection_and_reorder(
        self, mock_input: MagicMock, mock_argv: List[str]
    ) -> None:
        """
        Ensures the CLI prompts, reorders files, and generates hierarchical code.
        """
        logger.info("🧪 Testing heuristic prompt and file reordering.")
        # 🔀 Pass child first to test the reordering logic.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.child_path),
            str(self.parent_path),
        ]

        with patch("builtins.print") as mock_print:
            __main__.main()

        # ✅ Verify the heuristic prompt was shown to the user.
        print_calls = "".join(
            [call.args[0] for call in mock_print.call_args_list if call.args]
        )
        self.assertIn("looks like parent", print_calls)
        # ✅ Verify the output is hierarchical and correctly named.
        self.assertTrue(Path("parent_machine_logic.py").exists())
        runner_content = Path("parent_machine_runner.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("actor_cfgs = {", runner_content)

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["y"])
    def test_main_heuristic_parent_detection_yes(
        self, mock_input: unittest.mock.MagicMock, mock_argv: List[str]
    ) -> None:
        """Tests heuristic parent detection with user confirmation ('y')."""
        logger.info("🧪 Testing heuristic parent detection (user says 'y').")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.child_path),
            str(self.parent_path),
        ]
        with patch("builtins.print") as mock_print:
            main()
        # Verify the parent machine is correctly identified and used for naming
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("parent_machine_logic.py" in call for call in calls)
        )
        self.assertTrue(
            any("parent_machine_runner.py" in call for call in calls)
        )
        # Check that the interactive prompt was shown
        self.assertTrue(any("looks like parent" in call for call in calls))

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["n", "0"])
    def test_main_heuristic_parent_detection_no(
        self, mock_input: unittest.mock.MagicMock, mock_argv: List[str]
    ) -> None:
        """Tests heuristic parent detection with user rejection ('n'), treating them as flat."""
        logger.info("🧪 Testing heuristic parent detection (user says 'n').")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_path),
            str(self.child_path),
        ]
        with patch("builtins.print") as mock_print:
            main()
        # Without hierarchy, names are combined
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any(
                "parent_machine_child_machine_logic.py" in call
                for call in calls
            )
        )

    @patch("sys.argv", new_callable=list)
    @patch(
        "builtins.input", side_effect=["n", "2"]
    )  # Select the second machine (parent)
    def test_main_heuristic_manual_selection(
        self, mock_input: unittest.mock.MagicMock, mock_argv: List[str]
    ) -> None:
        """Tests manual parent selection when the heuristic is rejected."""
        logger.info("🧪 Testing heuristic manual selection.")
        # Provide child first, then parent
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.child_path),
            str(self.parent_path),
        ]
        with patch("builtins.print"):
            main()

        runner_content = (Path.cwd() / "parent_machine_runner.py").read_text(
            encoding="utf-8"
        )
        # FIX: Check for the *effect* of hierarchy, not an implementation detail.
        # The presence of an 'actors' dictionary is a reliable indicator.
        self.assertIn(
            "actors = {}",
            runner_content,
            "Runner should be in hierarchical mode",
        )
        self.assertIn(
            "Spawn & start every actor interpreter",
            runner_content,
            "Runner should spawn actors",
        )

    def test_hierarchical_runner_event_simulation(self) -> None:
        """Verifies the hierarchical runner simulates events for both parent and actors."""
        logger.info("🧪 Testing event simulation in hierarchical runner.")
        runner_code = generate_runner_code(
            machine_names=["parentMachine", "childMachine"],
            is_async=False,
            style="class",
            loader=True,
            sleep=False,
            sleep_time=0,
            log=True,
            file_count=2,
            configs=[HIERARCHY_PARENT_CONFIG, HIERARCHY_CHILD_CONFIG],
            json_filenames=[
                str(self.parent_path),
                str(self.child_path),
            ],
            hierarchy=True,
        )

        self.assertIn("parent.send('START')", runner_code)
        self.assertIn("parent.send('STOP')", runner_code)
        self.assertIn(
            "actors['childMachine'].send('CHILD_EVENT')", runner_code
        )
        self.assertIn("Simulating Actor «childMachine»", runner_code)

    def test_generate_logic_with_noqa_comments(self) -> None:
        """Ensures generated logic includes noqa comments for IDE warnings."""
        logger.info("🧪 Testing for noqa comments in generated logic.")
        logic_code = generate_logic_code(
            actions={"myAction"},
            guards={"myGuard"},
            services={"myService"},
            style="class",
            log=True,
            is_async=True,
            machine_name="test",
            file_count=2,
        )
        self.assertIn("# noqa: ignore IDE static method warning", logic_code)
        self.assertIn(
            "# noqa : ignore IDE return type hint warning", logic_code
        )

    @patch("sys.argv", new_callable=list)
    def test_main_explicit_parent_with_positional_children(
        self, mock_argv: List[str]
    ) -> None:
        """SCENARIO 6: Tests explicit parent flag with positional children."""
        logger.info(
            "🧪 Testing explicit parent with positional children (Scenario 6)."
        )
        # Create a second child to test with
        child2_config = {
            "id": "childMachine2",
            "initial": "idle",
            "states": {"idle": {}},
        }
        child2_path = create_temp_json(child2_config)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-parent",
            str(self.parent_path),
            str(self.child_path),  # Positional child 1
            str(child2_path),  # Positional child 2
        ]

        # No interactive input should be required
        with patch("builtins.input") as mock_input:
            main()
            # Assert that the interactive prompt was NOT triggered
            mock_input.assert_not_called()

        # Check that the output is hierarchical and named after the parent
        self.assertTrue(
            Path.cwd().joinpath("parent_machine_runner.py").exists()
        )
        runner_content = (Path.cwd() / "parent_machine_runner.py").read_text(
            encoding="utf-8"
        )

        # Verify both children are treated as actors
        self.assertIn("'child_machine': json.loads", runner_content)
        # FIX: The snake_case conversion of "childMachine2" is "child_machine2".
        self.assertIn("'child_machine2': json.loads", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_positional_parent_with_explicit_child(
        self, mock_argv: List[str]
    ) -> None:
        """SCENARIO 13: Tests positional parent with an explicit child flag."""
        logger.info(
            "🧪 Testing positional parent with explicit child (Scenario 13)."
        )
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_path),  # Positional parent
            "--json-child",
            str(self.child_path),  # Flagged child
        ]

        # This test correctly expects that the heuristic prompt will NOT be called.
        with patch("builtins.input") as mock_input:
            main()
            mock_input.assert_not_called()

        # This assertion will pass once the bugs in cli.py are fixed.
        self.assertTrue(
            Path.cwd().joinpath("parent_machine_runner.py").exists()
        )
        runner_content = (Path.cwd() / "parent_machine_runner.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("actor_cfgs = {", runner_content)
        self.assertIn("'child_machine'", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_hierarchy_with_no_events(self, mock_argv: List[str]) -> None:
        """Tests hierarchical generation when parent or child has no events."""
        logger.info("🧪 Testing hierarchical generation with no events.")
        parent_no_events_config = {
            "id": "parentNoEvents",
            "invoke": {"src": "childMachine"},
        }
        parent_no_events_path = create_temp_json(parent_no_events_config)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-parent",
            str(parent_no_events_path),
            "--json-child",
            str(self.child_path),
        ]

        main()

        runner_file = Path.cwd() / "parent_no_events_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # Verify it correctly notes the lack of parent events
        self.assertIn(
            "logger.info('No events declared in parent machine.')",
            runner_content,
        )
        # Verify it still includes simulation for the child with events
        self.assertIn("Simulating Actor «child_machine»", runner_content)
        # FIX: Add 'await' to the assertion to match the async runner code
        self.assertIn(
            "await actors['child_machine'].send('CHILD_EVENT')", runner_content
        )

    @patch("sys.argv", new_callable=list)
    def test_main_hierarchy_with_function_style(
        self, mock_argv: List[str]
    ) -> None:
        """Tests hierarchical generation with function-style logic."""
        logger.info("🧪 Testing hierarchical generation with function style.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--style",
            "function",
            "--json-parent",
            str(self.parent_path),
            "--json-child",
            str(self.child_path),
        ]

        main()

        runner_file = Path.cwd() / "parent_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # Verify it imports the logic module directly
        self.assertIn("import parent_machine_logic", runner_content)
        # Verify it uses the logic_modules parameter for create_machine
        self.assertIn("logic_modules=[parent_machine_logic]", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_reject_then_manual_select(
        self, mock_argv: List[str]
    ) -> None:
        """Tests rejecting heuristic suggestion then manually selecting a parent."""
        logger.info("🧪 Testing heuristic reject then manual select.")
        # We present parent then child, so the heuristic will correctly guess #1
        # We will reject it and manually select #1 anyway.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_path),
            str(self.child_path),
        ]

        with patch("builtins.input", side_effect=["n", "1"]), patch(
            "builtins.print"
        ) as mock_print:  # noqa: F841
            main()

        # Check for correct hierarchical output named after the manually selected parent
        runner_file = Path.cwd() / "parent_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")
        self.assertIn(
            "actor_cfgs = {",
            runner_content,
            "Runner should be in hierarchical mode",
        )
        self.assertIn("'child_machine'", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_invalid_manual_selection(
        self, mock_argv: List[str]
    ) -> None:
        """Tests that invalid manual parent selection defaults to flat mode."""
        logger.info("🧪 Testing heuristic with invalid manual selection.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_path),
            str(self.child_path),
        ]

        # User rejects heuristic, then enters invalid text "abc"
        with patch("builtins.input", side_effect=["n", "abc"]), patch(
            "builtins.print"
        ) as mock_print:  # noqa: F841
            main()

        # It should default to flat mode, combining the names
        runner_file = Path.cwd() / "parent_machine_child_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # FIX: Make the assertion more flexible by checking for 'in' instead of 'startswith'
        # This correctly handles both 'def ...' and 'async def ...'
        self.assertTrue(
            any(
                "def run_parent_machine" in line
                for line in runner_content.splitlines()
            ),
            "'run_parent_machine' function not found in runner.",
        )
        self.assertTrue(
            any(
                "def run_child_machine" in line
                for line in runner_content.splitlines()
            ),
            "'run_child_machine' function not found in runner.",
        )

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_tie_breaking(self, mock_argv: List[str]) -> None:
        """Tests that a heuristic tie is broken by the first-listed machine."""
        logger.info("🧪 Testing heuristic tie-breaking behavior.")
        # Create two potential parents with the exact same invoke score
        p1_config = {"id": "parentOne", "invoke": {"src": "someActor"}}
        p2_config = {"id": "parentTwo", "invoke": {"src": "someOtherActor"}}
        p1_path = create_temp_json(p1_config)
        p2_path = create_temp_json(p2_config)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(p1_path),  # parentOne is listed first
            str(p2_path),
        ]

        # We expect it to suggest "parentOne" and we will accept.
        with patch("builtins.input", side_effect=["y"]), patch(
            "builtins.print"
        ) as mock_print:
            main()

        # Verify that the prompt correctly identified the first machine as the parent
        print_output = "".join(
            call.args[0] for call in mock_print.call_args_list if call.args
        )
        self.assertIn("parentOne (looks like parent", print_output)

        # Verify the output is named after the first machine
        self.assertTrue(Path.cwd().joinpath("parent_one_runner.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_user_correction(
        self, mock_argv: List[str]
    ) -> None:
        """Tests the user correcting an incorrect heuristic guess."""
        logger.info("🧪 Testing user correction of a wrong heuristic guess.")
        # Create a "decoy" parent that has more invokes than the real one
        decoy_config = {
            "id": "decoyParent",
            "invoke": [{"src": "a"}, {"src": "b"}],
        }
        real_parent_config = {
            "id": "realParent",
            "invoke": {"src": "decoyParent"},
        }
        decoy_path = create_temp_json(decoy_config)
        real_path = create_temp_json(real_parent_config)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(real_path),  # real parent is first
            str(decoy_path),  # decoy is second, but has higher score
        ]

        # Heuristic will wrongly suggest "decoyParent" (index 2).
        # User says "n", then manually selects the correct parent "realParent" (index 1).
        with patch("builtins.input", side_effect=["n", "1"]), patch(
            "builtins.print"
        ) as mock_print:  # noqa: F841
            main()

        # Verify the output is named after the manually corrected parent
        self.assertTrue(Path.cwd().joinpath("real_parent_runner.py").exists())
        runner_content = (Path.cwd() / "real_parent_runner.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "'decoy_parent'", runner_content
        )  # Check that the decoy is an actor

    @patch("sys.argv", new_callable=list)
    def test_main_hierarchy_with_loader_disabled(
        self, mock_argv: List[str]
    ) -> None:
        """Tests hierarchical generation with the auto-discovery loader disabled."""
        logger.info("🧪 Testing hierarchical generation with --loader=no.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--loader",
            "no",
            "--json-parent",
            str(self.parent_path),
            "--json-child",
            str(self.child_path),
        ]

        main()

        runner_file = Path.cwd() / "parent_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # With the loader off, it should still bind the provider explicitly
        self.assertIn("logic_provider = LogicProvider()", runner_content)
        self.assertIn("logic_providers=[logic_provider]", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_combined_file_in_hierarchy_mode(
        self, mock_argv: List[str]
    ) -> None:
        """Verifies --file-count 1 works correctly in a hierarchical setup."""
        logger.info("🧪 Testing combined file output in hierarchy mode.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--file-count",
            "1",
            "--json-parent",
            str(self.parent_path),
            "--json-child",
            str(self.child_path),
        ]

        main()

        combined_file = Path("parent_machine.py")
        self.assertTrue(combined_file.exists())
        content = combined_file.read_text(encoding="utf-8")

        # Check for logic class definition
        self.assertIn("class ParentMachineLogic:", content)
        # Check for runner part and hierarchical constructs
        self.assertIn("# Runner part", content)
        self.assertIn("actor_cfgs = {", content)
        self.assertIn("'child_machine': json.loads", content)
        self.assertIn("parent = Interpreter(parent_machine)", content)
