# examples/async/complex/functional_approach/with_logic_loader/ci_cd_pipeline/ci_cd_pipeline_logic.py
import asyncio
import logging
import random
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


# --- Actions ---


def set_commit_hash(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["commit_hash"] = e.payload.get("hash")
    logging.info(
        f"🚀 New pipeline triggered for commit: {ctx['commit_hash'][:7]}"
    )


def store_build_artifact(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["build_artifact"] = e.data.get("artifact_path")
    logging.info(f"✅ Build successful. Artifact at: {ctx['build_artifact']}")


def store_test_results(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["test_results"] = e.data
    logging.info(f"✔️ Tests passed: {e.data.get('passed_count')} passed.")


def store_scan_results(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["scan_results"] = e.data
    logging.info(
        f"🛡️ Security scan passed: {e.data.get('vulnerabilities')} vulnerabilities found."
    )


def store_deployment_url(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["deployment_url"] = e.data.get("url")
    logging.info(f"🎉 Deployment successful! Live at: {ctx['deployment_url']}")


async def set_error(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["error"] = str(e.data)
    logging.error(f"❌ Pipeline step failed: {ctx['error']}")
    # If a test or scan fails, we need to explicitly fail the whole validation stage
    if i.current_state_ids.intersection(
        {
            "ciCdPipeline.validating.testing.tests_failed",
            "ciCdPipeline.validating.security_scan.scan_failed",
        }
    ):
        await i.send("VALIDATION_FAILED")


# --- Services ---


async def run_build_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    logging.info("  -> 📦 Invoking service: Running build...")
    await asyncio.sleep(2.0)
    return {"artifact_path": f"/builds/{ctx['commit_hash'][:7]}.tar.gz"}


async def run_test_suite(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    logging.info("  -> 🧪 Invoking service: Running test suite...")
    await asyncio.sleep(3.0)
    if random.random() < 0.1:  # 10% chance of failure
        raise AssertionError("Unit test 'test_critical_feature' failed.")
    return {"passed_count": 128, "failed_count": 0}


async def run_security_scan(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    logging.info("  -> 🛡️ Invoking service: Running security scan...")
    await asyncio.sleep(2.5)
    return {"vulnerabilities": 0}


async def run_deployment_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    logging.info("  -> 🌍 Invoking service: Deploying to production...")
    await asyncio.sleep(2.0)
    return {"url": f"https://app-{ctx['commit_hash'][:7]}.example.com"}
