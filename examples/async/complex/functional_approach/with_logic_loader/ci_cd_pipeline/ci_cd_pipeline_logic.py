# -------------------------------------------------------------------------------
# 🚀 CI/CD Pipeline Logic
# examples/async/complex/functional_approach/with_logic_loader/ci_cd_pipeline/ci_cd_pipeline_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for simulating a CI/CD pipeline with parallel stages.
"""

import asyncio
import logging
import random
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def set_commit_hash(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🚀 Record the new commit hash in context."""
    commit = event.payload.get("hash", "")
    context["commit_hash"] = commit
    logger.info(f"🚀 Pipeline triggered for commit {commit[:7]}")


def store_build_artifact(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✅ Save build artifact path."""
    path = event.data.get("artifact_path", "")
    context["build_artifact"] = path
    logger.info(f"✅ Build artifact stored: {path}")


def store_test_results(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✔️ Record number of passed tests."""
    results = event.data
    context["test_results"] = results
    passed = results.get("passed_count", 0)
    logger.info(f"✔️ Tests passed: {passed}")


def store_scan_results(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🛡️ Save security scan results."""
    scan = event.data
    context["scan_results"] = scan
    vulns = scan.get("vulnerabilities", 0)
    logger.info(f"🛡️ Vulnerabilities found: {vulns}")


def store_deployment_url(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🎉 Record deployment URL."""
    url = event.data.get("url", "")
    context["deployment_url"] = url
    logger.info(f"🎉 Deployed at: {url}")


async def set_error(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """❌ Handle step failure and trigger validation fail if needed."""
    error_msg = str(event.data)
    context["error"] = error_msg
    logger.error(f"❌ Pipeline step failed: {error_msg}")
    # Trigger overall validation failure if in a validation substate
    states = interpreter.current_state_ids
    fail_states = {
        "ciCdPipeline.validating.testing.tests_failed",
        "ciCdPipeline.validating.security_scan.scan_failed",
    }
    if states & fail_states:
        await interpreter.send("VALIDATION_FAILED")


# -------------------------------------------------------------------------------
# 🚀 CI/CD Pipeline Services
# -------------------------------------------------------------------------------


async def run_build_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """📦 Build service returns an artifact path."""
    logger.info("📦 Running build service...")
    await asyncio.sleep(2.0)
    return {"artifact_path": f"/builds/{context['commit_hash'][:7]}.tar.gz"}


async def run_test_suite(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
) -> Dict[str, Any]:
    """🧪 Test suite service returns pass/fail counts."""
    logger.info("🧪 Running test suite...")
    await asyncio.sleep(3.0)
    if random.random() < 0.1:
        raise AssertionError("Critical test failed.")
    return {"passed_count": 128, "failed_count": 0}


async def run_security_scan(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
) -> Dict[str, Any]:
    """🔒 Security scan service returns vulnerability count."""
    logger.info("🔒 Running security scan...")
    await asyncio.sleep(2.5)
    return {"vulnerabilities": 0}


async def run_deployment_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """🌍 Deployment service returns live URL."""
    logger.info("🌍 Deploying to production...")
    await asyncio.sleep(2.0)
    return {"url": f"https://app-{context['commit_hash'][:7]}.example.com"}
