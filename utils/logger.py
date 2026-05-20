"""
Agent Trace Logger
====================
JSON-based logging system for Antigravity trace submission.
Saves structured agent execution logs to logs/agent_traces/.

Each pipeline run creates ONE trace file containing logs from all 5 agents.
The file is built incrementally — each agent appends its step log.

Log format matches the hackathon submission spec:
    {
        "trace_id": "TRACE-INC-2026-001",
        "incident_id": "INC-2026-001",
        "timestamp": "2026-05-20T14:32:00",
        "agents": {
            "agent_1_signal_collector": { ... },
            "agent_2_crisis_detector": { ... },
            ...
        },
        "total_duration_ms": 8340
    }
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Console Color Codes for Terminal Output
# ---------------------------------------------------------------------------
class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# ---------------------------------------------------------------------------
# Resolve the logs directory relative to this file's location
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent.parent
_TRACES_DIR = _BASE_DIR / "logs" / "agent_traces"


class AgentLogger:
    """
    Structured JSON logger for the CIRO agent pipeline.

    Creates and incrementally updates a single trace file per incident,
    appending each agent's step data as the pipeline progresses.

    Args:
        trace_id: Unique trace identifier (e.g., TRACE-INC-2026-001).
        incident_id: Associated incident identifier (e.g., INC-2026-001).
    """

    def __init__(self, trace_id: str, incident_id: str, console_output: bool = True) -> None:
        """
        Initialize the logger and create the trace file skeleton.

        Args:
            trace_id: Unique trace identifier.
            incident_id: Associated incident identifier.
            console_output: Enable/disable console output (default: True).
        """
        self.trace_id = trace_id
        self.incident_id = incident_id
        self.start_time = datetime.now(timezone.utc)
        self._traces_dir = _TRACES_DIR
        self.console_output = console_output

        # Ensure the output directory exists
        self._traces_dir.mkdir(parents=True, exist_ok=True)

        # Path to this trace's JSON file
        self.trace_file = self._traces_dir / f"{trace_id}.json"

        # Initialize the trace structure
        self._trace_data: dict[str, Any] = {
            "trace_id": trace_id,
            "incident_id": incident_id,
            "timestamp": self.start_time.isoformat(),
            "agents": {},
            "total_duration_ms": 0,
        }

        # Write the initial skeleton
        self._save()

        # Print initial banner to console
        if self.console_output:
            self._print_pipeline_start()

    # ------------------------------------------------------------------
    # Public Methods
    # ------------------------------------------------------------------

    def log_agent_step(
        self,
        agent_name: str,
        step: str,
        input_data: Any,
        output_data: Any,
        duration_ms: int,
        extra_data: Optional[dict] = None,
    ) -> None:
        """
        Log a single agent's execution step to the trace file.

        This appends the agent's data under the 'agents' key and
        accumulates the total pipeline duration.

        Args:
            agent_name: Agent key (e.g., 'agent_1_signal_collector').
            step: Human-readable step name (e.g., 'Signal Collection').
            input_data: What the agent received as input.
            output_data: What the agent produced as output.
            duration_ms: How long the agent took (milliseconds).
            extra_data: Optional additional key-value pairs to include.
        """
        agent_log: dict[str, Any] = {
            "step": step,
            "input": self._serialize(input_data),
            "output": self._serialize(output_data),
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Merge any extra data (e.g., sources_checked, signals_found)
        if extra_data:
            agent_log.update(extra_data)

        # Append to the agents dict
        self._trace_data["agents"][agent_name] = agent_log

        # Accumulate total duration
        self._trace_data["total_duration_ms"] += duration_ms

        # Print to console if enabled
        if self.console_output:
            self._print_agent_log(agent_name, step, output_data, duration_ms, extra_data)

        # Persist to disk
        self._save()

    def get_trace_data(self) -> dict:
        """
        Return the current in-memory trace data.

        Returns:
            Dict containing the full trace structure.
        """
        return self._trace_data

    def get_agent_logs_for_mobile(self) -> list[dict]:
        """
        Convert trace data to mobile-friendly agent log entries.

        Returns:
            List of agent log entries suitable for mobile app display.
        """
        mobile_logs = []

        for agent_name, agent_data in self._trace_data.get("agents", {}).items():
            log_entry = {
                "agent_name": agent_name,
                "step": agent_data.get("step", "Unknown Step"),
                "status": str(agent_data.get("output", "")),
                "duration_ms": agent_data.get("duration_ms", 0),
                "timestamp": agent_data.get("timestamp", ""),
                "details": {}
            }

            # Extract relevant details (exclude input/output to keep it concise)
            for key, value in agent_data.items():
                if key not in ["step", "input", "output", "duration_ms", "timestamp"]:
                    # Only include non-None values
                    if value is not None:
                        log_entry["details"][key] = value

            mobile_logs.append(log_entry)

        return mobile_logs

    @staticmethod
    def get_trace(trace_id: str) -> Optional[dict]:
        """
        Read and return a trace file by its ID.

        Args:
            trace_id: The trace identifier to look up.

        Returns:
            Parsed dict from the JSON file, or None if not found.
        """
        trace_file = _TRACES_DIR / f"{trace_id}.json"
        if not trace_file.exists():
            return None

        try:
            with open(trace_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[AgentLogger] Error reading trace {trace_id}: {e}")
            return None

    @staticmethod
    def list_traces() -> list[str]:
        """
        List all available trace IDs in the traces directory.

        Returns:
            List of trace ID strings (filenames without .json extension).
        """
        if not _TRACES_DIR.exists():
            return []

        return [
            f.stem
            for f in _TRACES_DIR.glob("*.json")
            if f.is_file()
        ]

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _print_pipeline_start(self) -> None:
        """Print pipeline start banner to console."""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}  CIRO AGENT PIPELINE STARTED{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.CYAN}  Incident ID: {Colors.BOLD}{self.incident_id}{Colors.ENDC}")
        print(f"{Colors.CYAN}  Trace ID:    {Colors.BOLD}{self.trace_id}{Colors.ENDC}")
        print(f"{Colors.CYAN}  Started:     {Colors.BOLD}{self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

    def _print_agent_log(
        self,
        agent_name: str,
        step: str,
        output_data: Any,
        duration_ms: int,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Print formatted agent log to console."""
        # Extract agent number and name
        agent_parts = agent_name.split("_", 2)
        agent_num = agent_parts[1] if len(agent_parts) > 1 else "?"
        agent_display_name = agent_parts[2].replace("_", " ").title() if len(agent_parts) > 2 else agent_name

        # Choose color based on agent number
        color_map = {
            "1": Colors.BLUE,
            "2": Colors.CYAN,
            "3": Colors.GREEN,
            "4": Colors.YELLOW,
            "5": Colors.HEADER,
        }
        agent_color = color_map.get(agent_num, Colors.ENDC)

        # Print agent header
        print(f"{Colors.BOLD}{agent_color}┌─ Agent {agent_num}: {step}{Colors.ENDC}")
        print(f"{agent_color}│{Colors.ENDC} {Colors.BOLD}Status:{Colors.ENDC} {output_data}")
        print(f"{agent_color}│{Colors.ENDC} {Colors.BOLD}Duration:{Colors.ENDC} {duration_ms}ms ({duration_ms/1000:.2f}s)")

        # Print extra data if available
        if extra_data:
            for key, value in extra_data.items():
                if value is not None and key not in ["error"]:
                    # Format key nicely
                    display_key = key.replace("_", " ").title()

                    # Handle different value types
                    if isinstance(value, (list, dict)):
                        if isinstance(value, list) and len(value) > 0:
                            print(f"{agent_color}│{Colors.ENDC} {Colors.BOLD}{display_key}:{Colors.ENDC}")
                            for item in value[:5]:  # Show first 5 items
                                print(f"{agent_color}│{Colors.ENDC}   • {item}")
                            if len(value) > 5:
                                print(f"{agent_color}│{Colors.ENDC}   ... and {len(value) - 5} more")
                        elif isinstance(value, dict) and len(value) > 0:
                            print(f"{agent_color}│{Colors.ENDC} {Colors.BOLD}{display_key}:{Colors.ENDC}")
                            for k, v in list(value.items())[:5]:
                                print(f"{agent_color}│{Colors.ENDC}   • {k}: {v}")
                            if len(value) > 5:
                                print(f"{agent_color}│{Colors.ENDC}   ... and {len(value) - 5} more")
                    else:
                        print(f"{agent_color}│{Colors.ENDC} {Colors.BOLD}{display_key}:{Colors.ENDC} {value}")

            # Show errors separately in red if present
            if "error" in extra_data and extra_data["error"]:
                print(f"{agent_color}│{Colors.ENDC} {Colors.BOLD}{Colors.RED}Error:{Colors.ENDC} {extra_data['error']}")

        print(f"{agent_color}└{'─'*78}{Colors.ENDC}\n")

    def print_pipeline_complete(self) -> None:
        """Print pipeline completion banner to console."""
        if not self.console_output:
            return

        total_duration_sec = self._trace_data["total_duration_ms"] / 1000
        print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.GREEN}  CIRO AGENT PIPELINE COMPLETED{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.ENDC}")
        print(f"{Colors.CYAN}  Incident ID:    {Colors.BOLD}{self.incident_id}{Colors.ENDC}")
        print(f"{Colors.CYAN}  Total Duration: {Colors.BOLD}{total_duration_sec:.2f}s ({self._trace_data['total_duration_ms']}ms){Colors.ENDC}")
        print(f"{Colors.CYAN}  Agents Run:     {Colors.BOLD}{len(self._trace_data['agents'])}{Colors.ENDC}")
        print(f"{Colors.CYAN}  Trace File:     {Colors.BOLD}{self.trace_file}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.ENDC}\n")

    def _save(self) -> None:
        """Persist the current trace data to disk as formatted JSON."""
        try:
            with open(self.trace_file, "w", encoding="utf-8") as f:
                json.dump(self._trace_data, f, indent=2, ensure_ascii=False, default=str)
        except OSError as e:
            print(f"[AgentLogger] Error writing trace file: {e}")

    @staticmethod
    def _serialize(data: Any) -> Any:
        """
        Safely convert data to a JSON-serializable format.

        Handles Pydantic models, datetime objects, and other complex types.

        Args:
            data: Any data to serialize.

        Returns:
            JSON-safe representation of the data.
        """
        if data is None:
            return None
        if isinstance(data, str):
            return data
        if isinstance(data, (int, float, bool)):
            return data
        if isinstance(data, datetime):
            return data.isoformat()
        if isinstance(data, (list, tuple)):
            return [AgentLogger._serialize(item) for item in data]
        if isinstance(data, dict):
            return {str(k): AgentLogger._serialize(v) for k, v in data.items()}

        # Handle Pydantic models
        if hasattr(data, "model_dump"):
            return data.model_dump()

        # Fallback: convert to string
        return str(data)
