from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "parallel_claim.py"


class ParallelClaimCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.root.mkdir()
        self._git(self.root, "init")
        self._git(self.root, "config", "user.name", "Parallel Claim Tests")
        self._git(self.root, "config", "user.email", "parallel-claim@example.invalid")
        (self.root / "README.md").write_text("test\n", encoding="utf-8")
        self._git(self.root, "add", "README.md")
        self._git(self.root, "commit", "-m", "initial")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _git(self, cwd: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=True,
        )
        return completed.stdout.strip()

    def _run(
        self,
        command: str,
        *,
        task: str,
        owner: str | None = None,
        repo: Path | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        args = [
            sys.executable,
            str(SCRIPT),
            command,
            "--task",
            task,
            "--repo",
            str(repo or self.root),
        ]
        if owner is not None:
            args.extend(["--owner", owner])
        completed = subprocess.run(args, text=True, capture_output=True, check=False)
        payload = json.loads(completed.stdout)
        return completed, payload

    def test_claim_status_release_round_trip(self) -> None:
        claim, payload = self._run("claim", task="task-17", owner="worker-a")
        self.assertEqual(claim.returncode, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["claimed"])
        self.assertEqual(payload["task"], "task-17")
        self.assertEqual(payload["owner"], "worker-a")

        status, payload = self._run("status", task="task-17")
        self.assertEqual(status.returncode, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["claimed"])
        self.assertEqual(payload["owner"], "worker-a")

        release, payload = self._run("release", task="task-17", owner="worker-a")
        self.assertEqual(release.returncode, 0)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["released"])

        status, payload = self._run("status", task="task-17")
        self.assertEqual(status.returncode, 0)
        self.assertFalse(payload["claimed"])
        self.assertIsNone(payload["owner"])

    def test_claim_is_idempotent_for_the_same_owner(self) -> None:
        first, first_payload = self._run("claim", task="task-17", owner="worker-a")
        second, second_payload = self._run("claim", task="task-17", owner="worker-a")

        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertTrue(second_payload["ok"])
        self.assertEqual(second_payload["owner"], "worker-a")
        self.assertEqual(first_payload["common_dir"], second_payload["common_dir"])

    def test_second_owner_cannot_claim_an_active_task(self) -> None:
        first, _ = self._run("claim", task="task-17", owner="worker-a")
        self.assertEqual(first.returncode, 0)

        second, payload = self._run("claim", task="task-17", owner="worker-b")
        self.assertEqual(second.returncode, 1)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["claimed"])
        self.assertEqual(payload["owner"], "worker-a")

    def test_wrong_owner_cannot_release_claim(self) -> None:
        claimed, _ = self._run("claim", task="task-17", owner="worker-a")
        self.assertEqual(claimed.returncode, 0)

        release, payload = self._run("release", task="task-17", owner="worker-b")
        self.assertEqual(release.returncode, 1)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["claimed"])
        self.assertEqual(payload["owner"], "worker-a")

        status, payload = self._run("status", task="task-17")
        self.assertEqual(status.returncode, 0)
        self.assertTrue(payload["claimed"])
        self.assertEqual(payload["owner"], "worker-a")

    def test_linked_worktrees_share_the_same_claim_store(self) -> None:
        worktree = Path(self.tempdir.name) / "worker-b"
        self._git(self.root, "worktree", "add", "-b", "worker-b", str(worktree), "HEAD")

        claimed, first_payload = self._run(
            "claim", task="issue:https://example.invalid/42", owner="worker-a", repo=self.root
        )
        self.assertEqual(claimed.returncode, 0)

        status, second_payload = self._run(
            "status", task="issue:https://example.invalid/42", repo=worktree
        )
        self.assertEqual(status.returncode, 0)
        self.assertTrue(second_payload["claimed"])
        self.assertEqual(second_payload["owner"], "worker-a")
        self.assertEqual(first_payload["common_dir"], second_payload["common_dir"])

        competing, payload = self._run(
            "claim", task="issue:https://example.invalid/42", owner="worker-b", repo=worktree
        )
        self.assertEqual(competing.returncode, 1)
        self.assertEqual(payload["owner"], "worker-a")

    def test_status_before_claim_does_not_write_git_common_directory(self) -> None:
        common_dir = Path(self._git(self.root, "rev-parse", "--git-common-dir"))
        if not common_dir.is_absolute():
            common_dir = (self.root / common_dir).resolve()
        namespace = common_dir / "akira-parallel"
        self.assertFalse(namespace.exists())

        status, payload = self._run("status", task="task-17")

        self.assertEqual(status.returncode, 0)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["claimed"])
        self.assertFalse(namespace.exists())

    def test_claims_are_scoped_by_task_identity(self) -> None:
        first, _ = self._run("claim", task="gate-1/task-1", owner="worker-a")
        second, payload = self._run("claim", task="gate-1/task-2", owner="worker-b")

        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(payload["owner"], "worker-b")

    def test_concurrent_claims_have_exactly_one_winner(self) -> None:
        processes: list[tuple[str, subprocess.Popen[str]]] = []
        for index in range(8):
            owner = f"worker-{index}"
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(SCRIPT),
                    "claim",
                    "--task",
                    "concurrent-task",
                    "--owner",
                    owner,
                    "--repo",
                    str(self.root),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            processes.append((owner, process))

        results: list[tuple[str, int, dict[str, Any]]] = []
        for owner, process in processes:
            stdout, _ = process.communicate(timeout=10)
            results.append((owner, process.returncode, json.loads(stdout)))

        winners = [(owner, payload) for owner, code, payload in results if code == 0]
        self.assertEqual(len(winners), 1)
        winner = winners[0][0]
        self.assertTrue(winners[0][1]["ok"])

        for _, code, payload in results:
            if code == 0:
                continue
            self.assertEqual(code, 1)
            self.assertEqual(payload["owner"], winner)

    def test_non_git_directory_fails_closed(self) -> None:
        outside = Path(self.tempdir.name) / "outside"
        outside.mkdir()

        completed, payload = self._run(
            "claim", task="task-17", owner="worker-a", repo=outside
        )
        self.assertEqual(completed.returncode, 2)
        self.assertFalse(payload["ok"])
        self.assertIsNone(payload["claimed"])
        self.assertIn("Git", payload["error"])


if __name__ == "__main__":
    unittest.main()
