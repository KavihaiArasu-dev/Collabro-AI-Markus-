"""
Unit and Integration Tests for Markus AI Verifier Subsystem & Tool Registry

Tests:
1. Verifier direct assertions:
   - verify_file_exists, verify_file_deleted, verify_file_moved, verify_file_contains
   - verify_command_success
   - verify_process_running and verify_process_terminated
2. ToolRouter contracts & execution:
   - Pre-condition check enforcement (blocking invalid operations before execution)
   - Handler execution + post-condition assertion verification
   - Permission manager integration (RiskLevel checks & confirmation requirement)
3. VoiceCommandProcessor verified execution
4. Planner PlanStep verification tracking
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add markus directory to sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_MARKUS_DIR = _CURRENT_DIR.parent
if str(_MARKUS_DIR) not in sys.path:
    sys.path.insert(0, str(_MARKUS_DIR))

from core.verifier import verifier, VerificationResult
from tools.tool_router import tool_router, ToolDefinition
from tools.contracts import PreCondition, PostCondition, ExecutionResult
from core.planner import planner, PlanStepStatus
from core.voice_command_processor import voice_command_processor
from security.permissions import permission_manager
from config.constants import PermissionDecision


class TestVerifierSubsystem(unittest.TestCase):
    """Test the Verifier assertions directly against real system state."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_verify_file_exists_and_size(self):
        test_file = self.dir_path / "test_sample.txt"
        test_file.write_text("Hello Markus Verifier!", encoding="utf-8")

        # Exists check
        res = verifier.verify_file_exists(str(test_file))
        self.assertTrue(res.verified)
        self.assertEqual(res.assertion, "file_exists")
        self.assertIn("verified", res.details.lower())

        # Min size pass
        res_size_ok = verifier.verify_file_exists(str(test_file), min_size=10)
        self.assertTrue(res_size_ok.verified)

        # Min size fail
        res_size_fail = verifier.verify_file_exists(str(test_file), min_size=500)
        self.assertFalse(res_size_fail.verified)
        self.assertEqual(res_size_fail.error, "file_too_small")

        # Non-existent file
        non_existent = self.dir_path / "ghost.txt"
        res_missing = verifier.verify_file_exists(str(non_existent))
        self.assertFalse(res_missing.verified)
        self.assertEqual(res_missing.error, "file_not_found")

    def test_verify_file_deleted(self):
        test_file = self.dir_path / "to_delete.txt"
        test_file.write_text("Delete me", encoding="utf-8")

        # Before deletion, should NOT be verified as deleted
        res_before = verifier.verify_file_deleted(str(test_file))
        self.assertFalse(res_before.verified)
        self.assertEqual(res_before.error, "file_still_present")

        # Perform deletion
        test_file.unlink()

        # After deletion, should be verified as deleted
        res_after = verifier.verify_file_deleted(str(test_file))
        self.assertTrue(res_after.verified)
        self.assertEqual(res_after.assertion, "file_deleted")

    def test_verify_file_moved(self):
        src = self.dir_path / "source.txt"
        dst = self.dir_path / "dest.txt"
        src.write_text("Move payload", encoding="utf-8")

        # Before move
        res_before = verifier.verify_file_moved(str(src), str(dst))
        self.assertFalse(res_before.verified)

        # Move
        src.rename(dst)

        # After move
        res_after = verifier.verify_file_moved(str(src), str(dst))
        self.assertTrue(res_after.verified)
        self.assertTrue(dst.exists())
        self.assertFalse(src.exists())

    def test_verify_file_contains(self):
        test_file = self.dir_path / "content.txt"
        test_file.write_text("OmniRoute and Markus AI integration", encoding="utf-8")

        res_match = verifier.verify_file_contains(str(test_file), "Markus AI")
        self.assertTrue(res_match.verified)

        res_miss = verifier.verify_file_contains(str(test_file), "UnrelatedString404")
        self.assertFalse(res_miss.verified)
        self.assertEqual(res_miss.error, "content_mismatch")

    def test_verify_command_success(self):
        res_ok = verifier.verify_command_success(0, "Build succeeded")
        self.assertTrue(res_ok.verified)

        res_err = verifier.verify_command_success(1, "Syntax error")
        self.assertFalse(res_err.verified)
        self.assertEqual(res_err.error, "exit_code_1")

    def test_verify_process_terminated_for_ghost(self):
        # A process name that definitely is not running
        res = verifier.verify_process_terminated("markus_non_existent_process_xyz_9999", timeout=0.2)
        self.assertTrue(res.verified)


class TestToolRegistryWithVerifier(unittest.TestCase):
    """Test ToolRouter execution with pre-conditions and verifier post-conditions."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_and_verify_file(self):
        target = str(self.dir_path / "written.txt")
        res = tool_router.execute_sync("write_file", {"path": target, "content": "Autonomous Agent Data"})
        self.assertTrue(res["success"])
        self.assertTrue(res["verified"])
        self.assertIsNotNone(res["verification"])
        self.assertTrue(Path(target).exists())

    def test_precondition_blocks_invalid_delete(self):
        ghost_file = str(self.dir_path / "ghost_file.txt")
        # Trying to delete a non-existent file should be rejected by pre-condition
        res = tool_router.execute_sync("delete_file", {"path": ghost_file})
        self.assertFalse(res["success"])
        self.assertFalse(res["verified"])
        self.assertIn("Pre-condition failed", res["error"])

    def test_delete_and_verify_file(self):
        target = str(self.dir_path / "to_be_deleted.txt")
        Path(target).write_text("Temp file content")
        self.assertTrue(Path(target).exists())

        # Allow delete_file for test execution
        permission_manager.set_override("delete_file", PermissionDecision.ALLOW)
        try:
            res = tool_router.execute_sync("delete_file", {"path": target})
            self.assertTrue(res["success"])
            self.assertTrue(res["verified"])
            self.assertFalse(Path(target).exists())
        finally:
            permission_manager._custom_overrides.pop("delete_file", None)

    def test_move_and_verify_file(self):
        src = str(self.dir_path / "src_agent.txt")
        dst = str(self.dir_path / "dst_agent.txt")
        Path(src).write_text("Data moving")

        res = tool_router.execute_sync("move_file", {"src": src, "dst": dst})
        self.assertTrue(res["success"])
        self.assertTrue(res["verified"])
        self.assertFalse(Path(src).exists())
        self.assertTrue(Path(dst).exists())

    def test_high_risk_tool_requires_confirmation(self):
        res = tool_router.execute_sync("system_shutdown", {})
        self.assertFalse(res["success"])
        self.assertTrue(res.get("requires_confirmation", False))
        self.assertEqual(res["error"], "Waiting for user confirmation")


class TestPlannerAndVoiceIntegration(unittest.TestCase):
    """Test Planner and Voice Command fast path verification integration."""

    def test_planner_step_verification(self):
        plan = planner.create_plan("Test Verifier Plan", [
            {"description": "Write log file", "tool_name": "write_file"},
            {"description": "Read log file", "tool_name": "read_file"},
        ])
        self.assertEqual(len(plan.steps), 2)
        step_1 = plan.steps[0]
        self.assertEqual(step_1.status, PlanStepStatus.PENDING)

        # Advance step with verification details
        next_step = planner.advance_step(
            plan.id,
            result="Wrote log successfully",
            verified=True,
            verification_details={"assertion": "file_exists", "status": "ok"},
        )
        self.assertEqual(step_1.status, PlanStepStatus.COMPLETED)
        self.assertTrue(step_1.verified)
        self.assertIsNotNone(step_1.verification_details)
        self.assertIsNotNone(next_step)
        assert next_step is not None
        self.assertEqual(next_step.description, "Read log file")

    def test_voice_command_unmatched(self):
        res = voice_command_processor.try_execute("solve quantum electrodynamics equations")
        self.assertFalse(res.matched)


if __name__ == "__main__":
    unittest.main()
