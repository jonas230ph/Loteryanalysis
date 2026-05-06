#!/usr/bin/env python3
"""Run the PCSO scrape-and-analysis pipeline reliably.

The pipeline:
  1. Acquires an exclusive lock so only one pipeline runs at a time.
  2. Runs the configured synchronize command.
  3. Deletes stale pcso_results.json and files inside analysis_outputs/.
  4. Runs the scraper command, or optionally waits for an external scraper.
  5. Waits until pcso_results.json exists and its size is stable.
  6. Runs analyze_pcso_results.py.
  7. Runs analyze_pcso_results.py --suggestions-per-game 5.

Concurrency behavior:
  A new run waits for the lock. This queues work and avoids overlapping
  analysis processes. It does not abort an in-flight analysis.

Usage:
  ./scripts/auto_pipeline.py
  PROJECT_ROOT=/path/to/repo ./scripts/auto_pipeline.py
  ./scripts/auto_pipeline.py --watch-only
  ./scripts/auto_pipeline.py --suggestions-per-game 5
"""

from __future__ import annotations

import argparse
import fcntl
import logging
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PipelineConfig:
    project_root: Path
    python_bin: str
    scraper_cmd: str
    synchronize_cmd: str
    analyzer_path: Path
    results_file: Path
    analysis_dir: Path
    log_file: Path
    file_poll_interval: float
    stability_seconds: float
    wait_timeout: float
    lock_file: Path
    suggestions_per_game: int
    watch_only: bool
    retries: int
    retry_delay: float


class PipelineError(RuntimeError):
    pass


class PcsoPipeline:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.logger = logging.getLogger("pcso_pipeline")

    def run(self) -> None:
        self.config.project_root.mkdir(parents=True, exist_ok=True)
        self.config.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.config.log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config.lock_file, "w", encoding="utf-8") as lock:
            self.logger.info("Waiting for exclusive pipeline lock: %s", self.config.lock_file)
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.logger.info("Acquired exclusive pipeline lock")
            self._run_locked()

    def _run_locked(self) -> None:
        if not self.config.analyzer_path.exists():
            raise PipelineError(f"Analyzer not found: {self.config.analyzer_path}")

        self.run_command("synchronize", self.config.synchronize_cmd, shell=True)
        self.cleanup_outputs()

        if self.config.watch_only:
            self.logger.info("Watch-only mode: waiting for an external scraper to produce results")
        else:
            self.run_command("scraper", self.config.scraper_cmd, shell=True)

        self.wait_for_stable_file(self.config.results_file)
        self.run_with_retries(
            "analysis-default",
            [self.config.python_bin, str(self.config.analyzer_path)],
        )
        self.run_with_retries(
            "analysis-suggestions-5",
            [
                self.config.python_bin,
                str(self.config.analyzer_path),
                "--suggestions-per-game",
                str(self.config.suggestions_per_game),
            ],
        )
        self.logger.info("Pipeline completed successfully")

    def cleanup_outputs(self) -> None:
        self.logger.info("Cleaning stale output: %s", self.config.results_file)
        self.config.results_file.unlink(missing_ok=True)

        self.logger.info("Deleting files inside analysis directory: %s", self.config.analysis_dir)
        self.config.analysis_dir.mkdir(parents=True, exist_ok=True)
        for child in self.config.analysis_dir.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()

    def wait_for_stable_file(self, path: Path) -> None:
        self.logger.info(
            "Waiting for stable file: %s stability_seconds=%s timeout=%s",
            path,
            self.config.stability_seconds,
            self.config.wait_timeout,
        )
        started = time.monotonic()
        previous_size = None
        stable_since = None

        while True:
            elapsed = time.monotonic() - started
            if elapsed > self.config.wait_timeout:
                raise PipelineError(f"Timed out waiting for stable file: {path}")

            if path.exists():
                size = path.stat().st_size
                if size > 0 and size == previous_size:
                    if stable_since is None:
                        stable_since = time.monotonic()
                    if time.monotonic() - stable_since >= self.config.stability_seconds:
                        self.logger.info("File is stable: %s size=%s", path, size)
                        return
                else:
                    previous_size = size
                    stable_since = None

            time.sleep(self.config.file_poll_interval)

    def run_with_retries(self, label: str, command: list[str]) -> None:
        last_error = None
        for attempt in range(1, self.config.retries + 2):
            try:
                self.run_command(label, command)
                return
            except PipelineError as exc:
                last_error = exc
                if attempt > self.config.retries:
                    break
                self.logger.warning(
                    "%s failed on attempt %s/%s; retrying in %.1fs",
                    label,
                    attempt,
                    self.config.retries + 1,
                    self.config.retry_delay,
                )
                time.sleep(self.config.retry_delay)
        raise PipelineError(f"{label} failed after retries: {last_error}")

    def run_command(self, label: str, command: str | list[str], shell: bool = False) -> None:
        display = command if isinstance(command, str) else " ".join(shlex.quote(part) for part in command)
        self.logger.info("Starting %s: %s", label, display)
        started = time.monotonic()

        process = subprocess.Popen(
            command,
            cwd=self.config.project_root,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert process.stdout is not None
        for line in process.stdout:
            self.logger.info("%s | %s", label, line.rstrip())

        exit_code = process.wait()
        duration = time.monotonic() - started
        self.logger.info("Finished %s exit_code=%s duration=%.2fs", label, exit_code, duration)

        if exit_code != 0:
            raise PipelineError(f"{label} failed with exit code {exit_code}")


def default_python_bin(project_root: Path) -> str:
    venv_path = Path(os.getenv("VENV_PATH", project_root / "pcso_env"))
    venv_python = venv_path / "bin" / "python"
    if os.getenv("PYTHON_BIN"):
        return os.environ["PYTHON_BIN"]
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def build_config(args: argparse.Namespace) -> PipelineConfig:
    script_dir = Path(__file__).resolve().parent
    project_root = Path(os.getenv("PROJECT_ROOT", script_dir.parent)).resolve()
    python_bin = args.python_bin or default_python_bin(project_root)

    return PipelineConfig(
        project_root=project_root,
        python_bin=python_bin,
        scraper_cmd=os.getenv("SCRAPER_CMD", f"{shlex.quote(python_bin)} pcso_lottery_scraper.py"),
        synchronize_cmd=os.getenv("SYNCHRONIZE_CMD", "synchronize"),
        analyzer_path=Path(os.getenv("PATH_TO_ANALYZER", project_root / "analyze_pcso_results.py")).resolve(),
        results_file=Path(os.getenv("RESULTS_FILE", project_root / "pcso_results.json")).resolve(),
        analysis_dir=Path(os.getenv("ANALYSIS_DIR", project_root / "analysis_outputs")).resolve(),
        log_file=Path(os.getenv("LOG_FILE", project_root / "logs" / "pipeline.log")).resolve(),
        file_poll_interval=env_float("FILE_POLL_INTERVAL", args.file_poll_interval),
        stability_seconds=env_float("STABILITY_SECONDS", args.stability_seconds),
        wait_timeout=env_float("WAIT_TIMEOUT", args.wait_timeout),
        lock_file=Path(os.getenv("LOCK_FILE", project_root / ".pipeline.lock")).resolve(),
        suggestions_per_game=env_int("SUGGESTIONS_PER_GAME", args.suggestions_per_game),
        watch_only=args.watch_only or os.getenv("WATCH_ONLY", "0") == "1",
        retries=env_int("ANALYSIS_RETRIES", args.retries),
        retry_delay=env_float("RETRY_DELAY", args.retry_delay),
    )


def configure_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PCSO scraper and analysis pipeline.")
    parser.add_argument("--python-bin", help="Python interpreter used for analyzer and default scraper command.")
    parser.add_argument("--watch-only", action="store_true", help="Do not run scraper; wait for external pcso_results.json.")
    parser.add_argument("--file-poll-interval", type=float, default=2.0)
    parser.add_argument("--stability-seconds", type=float, default=5.0)
    parser.add_argument("--wait-timeout", type=float, default=600.0)
    parser.add_argument("--suggestions-per-game", type=int, default=5)
    parser.add_argument("--retries", type=int, default=1, help="Retries for each analysis step.")
    parser.add_argument("--retry-delay", type=float, default=10.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = build_config(args)
    configure_logging(config.log_file)
    logger = logging.getLogger("pcso_pipeline")
    logger.info("Pipeline requested project_root=%s", config.project_root)

    try:
        PcsoPipeline(config).run()
        return 0
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
