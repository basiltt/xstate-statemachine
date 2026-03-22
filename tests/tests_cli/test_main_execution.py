# tests/tests_cli/test_main_execution.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: End-to-End CLI Execution
# -----------------------------------------------------------------------------
# This module provides full, end-to-end integration tests for the main CLI
# entry point. It simulates command-line execution by patching `sys.argv`
# and verifies the complete workflow, from argument parsing to file output.
#
# The tests are organized into classes based on functionality:
#   - TestMainExecution: Covers flat (non-hierarchical) generation,
#     error handling, and core command-line options.
#   - TestHierarchyExecution: Focuses specifically on parent-child
#     machine generation, including explicit flags and the interactive
#     heuristic detection flow.
#
# This suite aims for comprehensive coverage of the user-facing CLI,
# ensuring reliability and predictable behavior across various scenarios.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
from io import StringIO
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine.cli import __main__, main
from src.xstate_statemachine.cli.generator import (
    generate_logic_code,
    generate_runner_code,
)
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
# Configures a logger for this test module to provide detailed output.
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestMainExecution
# -----------------------------------------------------------------------------
class TestMainExecution(CLITestCaseBase):
    """
    Tests the main CLI entry point for standard, non-hierarchical scenarios.

    This class covers core functionalities such as argument validation, error
    handling, file generation for single machines, and options like `--force`
    and `--output`.
    """

    @patch("sys.argv", new_callable=list)
    def test_main_no_json_error(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures the CLI exits with an error if no JSON file is provided.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🚦 Testing error handling for a missing JSON file.")
        # 🔧 Setup: Simulate calling the CLI with no file paths.
        mock_argv[:] = ["cli.py", "generate-template"]
        # ▶️ Run & ✅ Assert: Expect a SystemExit due to the validation error.
        with (
            patch("sys.stderr", new=StringIO()) as mock_err,
            self.assertRaises(SystemExit),
        ):
            __main__.main()
        self.assertIn(
            "At least one JSON file is required.", mock_err.getvalue()
        )

    @patch("sys.argv", new_callable=list)
    def test_main_json_not_found(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures the CLI exits if a specified JSON file does not exist.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🚦 Testing error handling for a non-existent JSON file.")
        # 🔧 Setup: Provide a path to a file that does not exist.
        mock_argv[:] = ["cli.py", "generate-template", "nonexistent.json"]
        # ▶️ Run & ✅ Assert: Expect a SystemExit and a "not found" error message.
        with (
            patch("sys.stderr", new=StringIO()) as mock_err,
            self.assertRaises(SystemExit),
        ):
            __main__.main()
        self.assertIn("JSON file not found", mock_err.getvalue())

    @patch("sys.argv", new_callable=list)
    def test_main_generate_single_file(self, mock_argv: List[str]) -> None:
        """
        🧪 Verifies correct file generation for a single JSON input.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("📄 Testing file generation for a single state machine.")
        # 🔧 Setup: Create a temporary JSON config and set up CLI args.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = ["cli.py", "generate-template", str(json_path)]
        # ▶️ Run: Execute the main CLI function.
        with patch("builtins.print") as mock_print:
            __main__.main()
        # ✅ Assert: Check the output messages to confirm files were created.
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("simple_logic.py" in call for call in calls))
        self.assertTrue(any("simple_runner.py" in call for call in calls))

    @patch("sys.argv", new_callable=list)
    def test_main_force_overwrite(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures the `--force` flag correctly overwrites existing files.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("💥 Testing file overwrite with the --force flag.")
        # 🔧 Setup: Create a temp JSON and a dummy file to be overwritten.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        logic_path = Path.cwd() / "simple_logic.py"
        logic_path.write_text("existing content")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--force",
        ]
        # ▶️ Run: Execute the main CLI function.
        __main__.main()
        # ✅ Assert: Verify the file content has changed.
        self.assertNotEqual(
            logic_path.read_text(encoding="utf-8"), "existing content"
        )

    @patch("sys.argv", new_callable=list)
    def test_main_no_force_prompt_and_cancel(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Ensures execution stops if files exist and user denies overwrite.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info(
            "🚫 Testing cancellation via interactive overwrite prompt."
        )
        # 🔧 Setup: Create a temp JSON file.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = ["cli.py", "generate-template", str(json_path)]

        # ▶️ Run once to create the initial files.
        __main__.main()
        self.assertTrue(Path.cwd().joinpath("simple_logic.py").exists())
        original_content = (Path.cwd() / "simple_logic.py").read_text(
            encoding="utf-8"
        )

        # ▶️ Run a second time, simulating user input 'n' to cancel.
        with (
            patch("builtins.input", return_value="n") as mock_input,
            patch("builtins.print") as mock_print,
        ):
            __main__.main()

        # ✅ Assert: Check that the prompt was shown.
        mock_input.assert_called_with(
            "File(s) already exist. Overwrite? [Y/n] "
        )
        # ✅ Assert: Check that the cancellation message was printed.
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("Operation cancelled." in call for call in calls))
        # ✅ Assert: Check that the file was NOT overwritten.
        self.assertEqual(
            original_content,
            (Path.cwd() / "simple_logic.py").read_text(encoding="utf-8"),
        )

    @patch("sys.argv", new_callable=list)
    def test_main_combined_file_merge(self, mock_argv: List[str]) -> None:
        """
        🧪 Verifies --file-count 1 correctly merges logic and runner files.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🔀 Testing intelligent merge for combined file output.")
        # 🔧 Setup: Create a temp JSON and set args for single-file output.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--file-count",
            "1",
        ]
        # ▶️ Run: Execute the main CLI function.
        __main__.main()

        # ✅ Assert: Check the combined file exists.
        combined_file = Path("simple.py")
        self.assertTrue(combined_file.exists())
        content = combined_file.read_text(encoding="utf-8")

        # ✅ Assert: Check that key imports and sections are present only once.
        self.assertEqual(content.count("import logging"), 1)
        self.assertEqual(content.count("from pathlib import Path"), 1)
        self.assertIn("# Class-based Logic", content)
        self.assertIn("# Runner part", content)

    @patch("sys.argv", new_callable=list)
    def test_main_generate_multiple(self, mock_argv: List[str]) -> None:
        """
        🧪 Verifies correct combined filenames for multiple JSON inputs.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("📑 Testing generation from multiple JSON files.")
        # 🔧 Setup: Create two temp JSON files and simulate CLI call.
        json1 = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        json2 = create_temp_json(SAMPLE_CONFIG_NESTED)
        mock_argv[:] = ["cli.py", "generate-template", str(json1), str(json2)]
        # ▶️ Run: Execute, simulating user declining hierarchy.
        with (
            patch("builtins.input", side_effect=["n", "0"]),
            patch("builtins.print") as mock_print,
        ):
            main()
        # ✅ Assert: Verify combined filenames in the output.
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("simple_nested_logic.py" in call for call in calls)
        )
        self.assertTrue(
            any("simple_nested_runner.py" in call for call in calls)
        )

    @patch("sys.argv", new_callable=list)
    def test_main_custom_output_dir(self, mock_argv: List[str]) -> None:
        """
        🧪 Verifies files are created in the specified `--output` directory.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("📂 Testing custom output directory functionality.")
        # 🔧 Setup: Create a temp JSON and specify an output directory.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        out_dir = Path(self.temp_dir.name) / "out"
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--output",
            str(out_dir),
        ]
        # ▶️ Run: Execute the main CLI function.
        with patch("builtins.print") as mock_print:
            main()
        # ✅ Assert: Check output messages and existence of the file in the dir.
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("simple_logic.py" in call for call in calls))
        self.assertTrue(out_dir.joinpath("simple_logic.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_invalid_bool_value(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures the CLI exits when an invalid boolean-like value is given.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🚦 Testing error handling for invalid boolean argument.")
        # 🔧 Setup: Pass an invalid value to a boolean flag.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--log",
            "invalid",
        ]
        # ▶️ Run & ✅ Assert: Expect a SystemExit.
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_version(self, mock_argv: List[str]) -> None:
        """
        🧪 Verifies `--version` prints the package version and exits.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("ℹ️ Testing the --version argument.")
        # 🔧 Setup: Simulate calling the CLI with the --version flag.
        mock_argv[:] = ["cli.py", "--version"]
        from src.xstate_statemachine import __version__ as package_version

        # ▶️ Run & ✅ Assert: Check for version string in output and SystemExit.
        with (
            patch("sys.stdout", new=StringIO()) as mock_out,
            self.assertRaises(SystemExit),
        ):
            main()
        self.assertIn(package_version, mock_out.getvalue())

    @patch("sys.argv", new_callable=list)
    def test_main_help(self, mock_argv: List[str]) -> None:
        """
        🧪 Verifies the help message is displayed with `-h` or `--help`.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("❓ Testing the help message display with -h.")
        # 🔧 Setup: Simulate calling for help on a subcommand.
        mock_argv[:] = ["cli.py", "generate-template", "-h"]
        # ▶️ Run & ✅ Assert: Check for 'usage:' text and a SystemExit.
        with (
            patch("sys.stdout", new=StringIO()) as mock_out,
            self.assertRaises(SystemExit),
        ):
            main()
        self.assertIn("usage:", mock_out.getvalue())

    @patch("sys.argv", new_callable=list)
    def test_main_additional_json(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures `--json` can be used to add config files.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("➕ Testing adding JSON files via the --json argument.")
        # 🔧 Setup: Create two temp JSONs and pass them via the --json flag.
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
        # ▶️ Run: Execute, simulating user declining hierarchy.
        with (
            patch("builtins.input", side_effect=["n", "0"]),
            patch("builtins.print") as mock_print,
        ):
            main()
        # ✅ Assert: Verify combined filenames in the output.
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("simple_nested_logic.py" in call for call in calls)
        )

    @patch("sys.argv", new_callable=list)
    def test_main_invalid_style(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures the CLI exits for an invalid `--style` choice.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🚦 Testing error handling for invalid --style choice.")
        # 🔧 Setup: Pass an invalid value to the --style argument.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--style",
            "invalid",
        ]
        # ▶️ Run & ✅ Assert: Expect a SystemExit.
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_invalid_file_count(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures the CLI exits for an invalid `--file-count` choice.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🚦 Testing error handling for invalid --file-count.")
        # 🔧 Setup: Pass an invalid value to --file-count.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--file-count",
            "3",
        ]
        # ▶️ Run & ✅ Assert: Expect a SystemExit.
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_sleep_time_non_int(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures the CLI exits if `--sleep-time` is not an integer.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🚦 Testing error handling for non-integer --sleep-time.")
        # 🔧 Setup: Pass a non-integer value to --sleep-time.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--sleep-time",
            "abc",
        ]
        # ▶️ Run & ✅ Assert: Expect a SystemExit.
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_no_subcommand(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures the CLI shows an error if no subcommand is provided.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🚦 Testing error handling for missing subcommand.")
        # 🔧 Setup: Call the CLI with no arguments.
        mock_argv[:] = ["cli.py"]
        # ▶️ Run & ✅ Assert: Expect a SystemExit and a specific error message.
        with (
            patch("sys.stderr", new=StringIO()) as mock_err,
            self.assertRaises(SystemExit),
        ):
            main()
        self.assertIn(
            "the following arguments are required: subcommand",
            mock_err.getvalue(),
        )

    @patch("sys.argv", new_callable=list)
    def test_main_output_dir_not_exist_create(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Ensures that a non-existent output directory is created.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🏡 Testing creation of a non-existent output directory.")
        # 🔧 Setup: Specify an output directory that doesn't exist yet.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        out_dir = Path(self.temp_dir.name) / "new_dir"
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--output",
            str(out_dir),
        ]
        # ▶️ Run: Execute the main CLI function.
        main()
        # ✅ Assert: Verify that the directory was created.
        self.assertTrue(out_dir.exists())

    @patch("sys.argv", new_callable=list)
    def test_main_force_no_overwrite_if_not_exist(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Confirms `--force` runs without error if files don't exist.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("✅ Testing --force has no side-effects if files are new.")
        # 🔧 Setup: Use --force when no files exist to be overwritten.
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--force",
        ]
        # ▶️ Run: Execute the main CLI function.
        main()
        # ✅ Assert: Verify the output file was created successfully.
        self.assertTrue(Path.cwd().joinpath("simple_logic.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_deduplicates_paths(self, mock_argv: List[str]) -> None:
        """
        🧪 Ensures duplicate file paths from different args are handled.

        This test covers Scenario 14 from the original test plan, where the
        same file path is provided via positional, `--json`, and
        `--json-parent` arguments. The CLI should de-duplicate these and
        process the file only once.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🔄 Testing de-duplication of input JSON paths.")
        # 🔧 Setup: Provide the same JSON path multiple times via different args.
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
        # ▶️ Run: Execute the main CLI function.
        with patch("builtins.print") as mock_print:
            main()

        # ✅ Assert: The result should be a simple, single-file generation.
        # It should not trigger hierarchical mode or create mangled filenames.
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
        """
        🧪 Ensures an error is raised if multiple parents are specified.

        This covers Scenario 17, explicitly disallowing more than one
        `--json-parent` flag.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🚦 Testing error on multiple --json-parent flags.")
        # 🔧 Setup: Create two temp JSONs and pass both as --json-parent.
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
        # ▶️ Run & ✅ Assert: Expect a SystemExit and a specific error message.
        with (
            patch("sys.stderr", new=StringIO()) as mock_err,
            self.assertRaises(SystemExit),
        ):
            main()
        self.assertIn(
            "Only one --json-parent may be supplied.", mock_err.getvalue()
        )


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestHierarchyExecution
# -----------------------------------------------------------------------------
class TestHierarchyExecution(CLITestCaseBase):
    """
    Tests the main CLI for hierarchical (parent-child) machine generation.

    This class focuses on scenarios involving invoked actors, including the
    use of explicit `--json-parent`/`--json-child` flags and the interactive
    heuristic flow for detecting parent-child relationships.
    """

    def setUp(self) -> None:
        """
        Sets up the test environment before each test method.

        Extends the base setup to create shared temporary JSON config files
        for a parent and a child machine, available as instance attributes.
        """
        super().setUp()
        self.parent_path = create_temp_json(HIERARCHY_PARENT_CONFIG)
        self.child_path = create_temp_json(HIERARCHY_CHILD_CONFIG)

    @patch("sys.argv", new_callable=list)
    def test_main_explicit_parent_child_args(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Verifies generation using explicit --json-parent & --json-child.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("👨‍👧 Testing explicit parent-child flag combination.")
        # 🔧 Setup: Use explicit flags to define the hierarchy.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-parent",
            str(self.parent_path),
            "--json-child",
            str(self.child_path),
        ]
        # ▶️ Run: Execute the main CLI function.
        with patch("builtins.print"):
            __main__.main()

        # ✅ Assert: Check for correctly named hierarchical output files.
        self.assertTrue(Path("parent_machine_runner.py").exists())
        runner_content = Path("parent_machine_runner.py").read_text(
            encoding="utf-8"
        )
        # ✅ Assert: Check for hierarchical runner code constructs.
        self.assertIn("parent_cfg = json.loads", runner_content)
        self.assertIn("actor_cfgs = {", runner_content)
        self.assertIn("'child_machine': json.loads", runner_content)

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["y"])
    def test_main_heuristic_parent_detection_and_reorder(
        self, mock_input: MagicMock, mock_argv: List[str]
    ) -> None:
        """
        🧪 Ensures CLI prompts, reorders files, and generates hierarchy.

        This test specifically passes the child machine's config file before
        the parent's to verify that the heuristic detection and reordering
        logic works correctly.

        Args:
            mock_input (MagicMock): A mock for `builtins.input` to simulate
                                   user confirmation ('y').
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🤔 Testing heuristic prompt and file reordering.")
        # 🔧 Setup: Pass child first, then parent, to test reordering.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.child_path),
            str(self.parent_path),
        ]

        with patch("builtins.print") as mock_print:
            __main__.main()

        # ✅ Assert: Verify the heuristic prompt was shown to the user.
        print_calls = "".join(
            [call.args[0] for call in mock_print.call_args_list if call.args]
        )
        self.assertIn("looks like parent", print_calls)
        # ✅ Assert: Verify the output is hierarchical and correctly named.
        self.assertTrue(Path("parent_machine_logic.py").exists())
        runner_content = Path("parent_machine_runner.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("actor_cfgs = {", runner_content)
        # Suppress unused variable warning for the mock object
        _ = mock_input  # noqa: F841

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["y"])
    def test_main_heuristic_parent_detection_yes(
        self, mock_input: MagicMock, mock_argv: List[str]
    ) -> None:
        """
        🧪 Tests heuristic parent detection with user confirmation ('y').

        Args:
            mock_input (MagicMock): A mock for `builtins.input`.
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🤔 Testing heuristic parent detection (user says 'y').")
        # 🔧 Setup: Pass child then parent, simulating user 'y' to confirm.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.child_path),
            str(self.parent_path),
        ]
        with patch("builtins.print") as mock_print:
            main()
        # ✅ Assert: Verify parent is identified and used for naming.
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("parent_machine_logic.py" in call for call in calls)
        )
        self.assertTrue(
            any("parent_machine_runner.py" in call for call in calls)
        )
        # ✅ Assert: Check that the interactive prompt was shown.
        self.assertTrue(any("looks like parent" in call for call in calls))
        _ = mock_input  # noqa: F841

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["n", "0"])
    def test_main_heuristic_parent_detection_no(
        self, mock_input: MagicMock, mock_argv: List[str]
    ) -> None:
        """
        🧪 Tests heuristic with user rejection ('n'), treating as flat.

        Args:
            mock_input (MagicMock): A mock for `builtins.input`.
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🤔 Testing heuristic parent detection (user says 'n').")
        # 🔧 Setup: Pass parent and child, simulating 'n' to reject hierarchy.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_path),
            str(self.child_path),
        ]
        with patch("builtins.print") as mock_print:
            main()
        # ✅ Assert: Without hierarchy, names are combined (flat generation).
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any(
                "parent_machine_child_machine_logic.py" in call
                for call in calls
            )
        )
        _ = mock_input  # noqa: F841

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["n", "2"])
    def test_main_heuristic_manual_selection(
        self, mock_input: MagicMock, mock_argv: List[str]
    ) -> None:
        """
        🧪 Tests manual parent selection after rejecting the heuristic.

        Args:
            mock_input (MagicMock): A mock for `builtins.input`.
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🤔 Testing heuristic manual selection.")
        # 🔧 Setup: Pass child then parent. User says 'n' then selects parent.
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
        # ✅ Assert: The presence of an 'actors' dict indicates hierarchy.
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
        _ = mock_input  # noqa: F841

    def test_hierarchical_runner_event_simulation(self) -> None:
        """
        🧪 Verifies the hierarchical runner simulates events for all actors.
        """
        logger.info("🤖 Testing event simulation in hierarchical runner.")
        # 🔧 Setup: Generate runner code for a hierarchical machine.
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

        # ✅ Assert: Check for parent and child event simulation code.
        self.assertIn("parent.send('START')", runner_code)
        self.assertIn("parent.send('STOP')", runner_code)
        self.assertIn(
            "actors['childMachine'].send('CHILD_EVENT')", runner_code
        )
        self.assertIn("Simulating Actor «childMachine»", runner_code)

    def test_generate_logic_with_noqa_comments(self) -> None:
        """
        🧪 Ensures generated logic omits noqa comments for production quality.

        The strategy-based output is production-quality code that does not
        require linter suppression comments.
        """
        logger.info(
            "🤫 Testing for absence of noqa comments in generated logic."
        )
        # 🔧 Setup: Generate logic code with all construct types.
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
        # ✅ Assert: Verify noqa comments are NOT present in strategy output.
        self.assertNotIn("# noqa", logic_code)

    @patch("sys.argv", new_callable=list)
    def test_main_explicit_parent_with_positional_children(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Tests explicit parent flag with multiple positional children.

        This covers Scenario 6, where `--json-parent` is used alongside
        multiple positional arguments, which are treated as children.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info(
            "👨‍👧‍👦 Testing explicit parent with positional children."
        )
        # 🔧 Setup: Create a second child config.
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

        # ▶️ Run: No interactive input should be required.
        with patch("builtins.input") as mock_input:
            main()
            # ✅ Assert: The interactive heuristic prompt was NOT triggered.
            mock_input.assert_not_called()

        # ✅ Assert: Check that the output is hierarchical and correct.
        self.assertTrue(
            Path.cwd().joinpath("parent_machine_runner.py").exists()
        )
        runner_content = (Path.cwd() / "parent_machine_runner.py").read_text(
            encoding="utf-8"
        )

        # ✅ Assert: Verify both children are treated as actors.
        self.assertIn("'child_machine': json.loads", runner_content)
        self.assertIn("'child_machine2': json.loads", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_positional_parent_with_explicit_child(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Tests positional parent with an explicit child flag.

        This covers Scenario 13. The presence of any `--json-child` flag
        should disable the heuristic prompt.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info(
            "👨‍👧 Testing positional parent with explicit child flag."
        )
        # 🔧 Setup: Pass parent positionally and child via flag.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_path),  # Positional parent
            "--json-child",
            str(self.child_path),  # Flagged child
        ]

        # ▶️ Run: Execute CLI. The heuristic prompt should NOT be called.
        with patch("builtins.input") as mock_input:
            main()
            mock_input.assert_not_called()

        # ✅ Assert: Check for correct hierarchical output.
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
        """
        🧪 Tests hierarchical generation when a machine has no events.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🔇 Testing hierarchical generation with no events.")
        # 🔧 Setup: Create a parent config with no `states` or `events`.
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

        # ▶️ Run: Execute the main CLI function.
        main()

        # ✅ Assert: Check the generated runner file.
        runner_file = Path.cwd() / "parent_no_events_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # ✅ Assert: Verify it notes the lack of parent events.
        self.assertIn(
            "logger.info('No events declared in parent machine.')",
            runner_content,
        )
        # ✅ Assert: Verify it still simulates the child's events.
        self.assertIn("Simulating Actor «child_machine»", runner_content)
        self.assertIn(
            "await actors['child_machine'].send('CHILD_EVENT')", runner_content
        )

    @patch("sys.argv", new_callable=list)
    def test_main_hierarchy_with_function_style(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Tests hierarchical generation with function-style logic.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("ƒ Testing hierarchical generation with function style.")
        # 🔧 Setup: Specify function style for a hierarchical generation.
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
        # ▶️ Run: Execute the main CLI function.
        main()

        # ✅ Assert: Check the runner file for function-style constructs.
        runner_file = Path.cwd() / "parent_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # ✅ Assert: Verify it imports the logic module directly.
        self.assertIn("import parent_machine_logic", runner_content)
        # ✅ Assert: Verify it uses the `logic_modules` parameter.
        self.assertIn("logic_modules=[parent_machine_logic]", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_reject_then_manual_select(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Tests rejecting heuristic then manually selecting a parent.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🤔 Testing heuristic reject then manual select.")
        # 🔧 Setup: Pass parent then child. The heuristic will suggest #1.
        # We simulate the user rejecting ('n') then manually selecting #1.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_path),
            str(self.child_path),
        ]

        with (
            patch("builtins.input", side_effect=["n", "1"]),
            patch("builtins.print"),
        ):
            main()

        # ✅ Assert: Check for correct output named after the selected parent.
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
        """
        🧪 Tests that invalid manual parent selection defaults to flat mode.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🤔 Testing heuristic with invalid manual selection.")
        # 🔧 Setup: Pass parent and child.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_path),
            str(self.child_path),
        ]

        # ▶️ Run: User rejects heuristic ('n'), then enters invalid text "abc".
        with (
            patch("builtins.input", side_effect=["n", "abc"]),
            patch("builtins.print"),
        ):
            main()

        # ✅ Assert: It should default to flat mode, combining the names.
        runner_file = Path.cwd() / "parent_machine_child_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # ✅ Assert: Check that separate runner functions are created.
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
        """
        🧪 Tests that a heuristic tie is broken by the first-listed machine.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🤔 Testing heuristic tie-breaking behavior.")
        # 🔧 Setup: Create two potential parents with the same "invoke" score.
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

        # ▶️ Run: Expect it to suggest "parentOne", which we accept ('y').
        with (
            patch("builtins.input", side_effect=["y"]),
            patch("builtins.print") as mock_print,
        ):
            main()

        # ✅ Assert: Verify the prompt identified the first machine as parent.
        print_output = "".join(
            call.args[0] for call in mock_print.call_args_list if call.args
        )
        self.assertIn("parentOne (looks like parent", print_output)

        # ✅ Assert: Verify the output is named after the first machine.
        self.assertTrue(Path.cwd().joinpath("parent_one_runner.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_user_correction(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Tests the user correcting an incorrect heuristic guess.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🤔 Testing user correction of a wrong heuristic guess.")
        # 🔧 Setup: Create a "decoy" with a higher score than the real parent.
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
            str(real_path),  # Real parent
            str(decoy_path),  # Decoy with higher score
        ]

        # ▶️ Run: Heuristic will wrongly suggest "decoyParent" (index 2).
        # User says "n", then manually selects "realParent" (index 1).
        with (
            patch("builtins.input", side_effect=["n", "1"]),
            patch("builtins.print"),
        ):
            main()

        # ✅ Assert: Verify output is named after the corrected parent.
        self.assertTrue(Path.cwd().joinpath("real_parent_runner.py").exists())
        runner_content = (Path.cwd() / "real_parent_runner.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("'decoy_parent'", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_hierarchy_with_loader_disabled(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Tests hierarchical generation with the loader disabled.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🔌 Testing hierarchical generation with --loader=no.")
        # 🔧 Setup: Disable the loader via a CLI flag.
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
        # ▶️ Run: Execute the main CLI function.
        main()

        runner_file = Path.cwd() / "parent_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # ✅ Assert: Check that logic is bound explicitly via a provider.
        self.assertIn("logic_provider = LogicProvider()", runner_content)
        self.assertIn("logic_providers=[logic_provider]", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_combined_file_in_hierarchy_mode(
        self, mock_argv: List[str]
    ) -> None:
        """
        🧪 Verifies --file-count 1 works correctly in hierarchical setup.

        Args:
            mock_argv (List[str]): A mocked `sys.argv` to simulate CLI args.
        """
        logger.info("🔀 Testing combined file output in hierarchy mode.")
        # 🔧 Setup: Use --file-count 1 in a hierarchical generation.
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
        # ▶️ Run: Execute the main CLI function.
        main()

        # ✅ Assert: Check the combined file exists and has correct content.
        combined_file = Path("parent_machine.py")
        self.assertTrue(combined_file.exists())
        content = combined_file.read_text(encoding="utf-8")

        # ✅ Assert: Logic, runner, and hierarchical constructs are present.
        self.assertIn("class ParentMachineLogic:", content)
        self.assertIn("# Runner part", content)
        self.assertIn("actor_cfgs = {", content)
        self.assertIn("'child_machine': json.loads", content)
        self.assertIn("parent = Interpreter(parent_machine)", content)
