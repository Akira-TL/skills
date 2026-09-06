from __future__ import annotations

import hashlib
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

    def test_linked_worktrees_share_claim_for_worktree_local_task_paths(self) -> None:
        task_relative = Path("tracker/tasks/task-17.md")
        task_in_root = self.root / task_relative
        task_in_root.parent.mkdir(parents=True)
        task_in_root.write_text("# Task 17\n", encoding="utf-8")
        self._git(self.root, "add", str(task_relative))
        self._git(self.root, "commit", "-m", "add task")

        worktree = Path(self.tempdir.name) / "worker-b-local-task"
        self._git(
            self.root,
            "worktree",
            "add",
            "-b",
            "worker-b-local-task",
            str(worktree),
            "HEAD",
        )
        task_in_worktree = worktree / task_relative

        claimed, _ = self._run(
            "claim",
            task=str(task_in_root),
            owner="worker-a",
            repo=self.root,
        )
        self.assertEqual(claimed.returncode, 0)

        competing, payload = self._run(
            "claim",
            task=str(task_in_worktree),
            owner="worker-b",
            repo=worktree,
        )
        self.assertEqual(competing.returncode, 1)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["claimed"])
        self.assertEqual(payload["owner"], "worker-a")

        status, payload = self._run(
            "status",
            task=str(task_in_worktree),
            repo=worktree,
        )
        self.assertEqual(status.returncode, 0)
        self.assertTrue(payload["claimed"])
        self.assertEqual(payload["owner"], "worker-a")

    def test_legacy_absolute_path_claim_is_visible_from_another_worktree(self) -> None:
        task_relative = Path("tracker/tasks/task-legacy.md")
        task_in_root = self.root / task_relative
        task_in_root.parent.mkdir(parents=True)
        task_in_root.write_text("# Legacy Task\n", encoding="utf-8")
        self._git(self.root, "add", str(task_relative))
        self._git(self.root, "commit", "-m", "add legacy task")

        worktree = Path(self.tempdir.name) / "worker-b-legacy-task"
        self._git(
            self.root,
            "worktree",
            "add",
            "-b",
            "worker-b-legacy-task",
            str(worktree),
            "HEAD",
        )
        task_in_worktree = worktree / task_relative

        common_dir = Path(self._git(self.root, "rev-parse", "--git-common-dir"))
        if not common_dir.is_absolute():
            common_dir = (self.root / common_dir).resolve()
        claims = common_dir / "akira-parallel" / "claims"
        claims.mkdir(parents=True)
        legacy_task = str(task_in_root)
        legacy_path = claims / f"{hashlib.sha256(legacy_task.encode('utf-8')).hexdigest()}.json"
        legacy_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "task": legacy_task,
                    "owner": "legacy-worker",
                    "claimed_at": "2026-09-06T00:00:00+00:00",
                    "hostname": "test-host",
                    "pid": 1,
                    "worktree": str(self.root),
                }
            )
            + "\n",
            encoding="utf-8",
        )

        status, payload = self._run(
            "status",
            task=str(task_in_worktree),
            repo=worktree,
        )
        self.assertEqual(status.returncode, 0)
        self.assertTrue(payload["claimed"])
        self.assertEqual(payload["owner"], "legacy-worker")

        release, payload = self._run(
            "release",
            task=str(task_in_worktree),
            owner="legacy-worker",
            repo=worktree,
        )
        self.assertEqual(release.returncode, 0)
        self.assertTrue(payload["released"])
        self.assertFalse(legacy_path.exists())

    def test_conflicting_legacy_claims_fail_closed(self) -> None:
        task_relative = Path("tracker/tasks/task-conflict.md")
        task_in_root = self.root / task_relative
        task_in_root.parent.mkdir(parents=True)
        task_in_root.write_text("# Conflict Task\n", encoding="utf-8")
        self._git(self.root, "add", str(task_relative))
        self._git(self.root, "commit", "-m", "add conflict task")

        worktree = Path(self.tempdir.name) / "worker-b-conflict-task"
        self._git(
            self.root,
            "worktree",
            "add",
            "-b",
            "worker-b-conflict-task",
            str(worktree),
            "HEAD",
        )
        task_in_worktree = worktree / task_relative

        common_dir = Path(self._git(self.root, "rev-parse", "--git-common-dir"))
        if not common_dir.is_absolute():
            common_dir = (self.root / common_dir).resolve()
        claims = common_dir / "akira-parallel" / "claims"
        claims.mkdir(parents=True)

        for task_path, owner, record_worktree in (
            (task_in_root, "legacy-worker-a", self.root),
            (task_in_worktree, "legacy-worker-b", worktree),
        ):
            task_value = str(task_path)
            claim_path = claims / f"{hashlib.sha256(task_value.encode('utf-8')).hexdigest()}.json"
            claim_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "task": task_value,
                        "owner": owner,
                        "claimed_at": "2026-09-06T00:00:00+00:00",
                        "hostname": "test-host",
                        "pid": 1,
                        "worktree": str(record_worktree),
                    }
                )
                + "\n",
                encoding="utf-8",
            )

        status, payload = self._run(
            "status",
            task=str(task_in_root),
            repo=self.root,
        )
        self.assertEqual(status.returncode, 2)
        self.assertFalse(payload["ok"])
        self.assertIsNone(payload["claimed"])
        self.assertIn("多个 active claim owner", payload["error"])

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
