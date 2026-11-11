#!/usr/bin/env python3
"""Demo: fakes a Claude Code session to watch the cat react.

    python3 demo.py          plays a full scenario (about 40 seconds)
    python3 demo.py question sends a single state: idle, work, agents,
                             question, done, end
"""

import json
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION = "demo-" + (os.environ.get("DEMO_SESSION") or "1")


def send(event, **fields):
    message = {"hook_event_name": event, "session_id": SESSION, "cwd": "/demo/my-project"}
    message.update(fields)
    subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "hook.py")],
        input=json.dumps(message).encode(),
        check=False,
    )


def tool(name, pause=2.0, **tool_input):
    send("PreToolUse", tool_name=name, tool_input=tool_input)
    time.sleep(pause)
    send("PostToolUse", tool_name=name, tool_input=tool_input)


STATES = {
    "idle": lambda: send("SessionStart"),
    "work": lambda: send("PreToolUse", tool_name="Edit", tool_input={"file_path": "/demo/model.py"}),
    "agents": lambda: (
        send("SubagentStart", agent_id="a1", agent_type="Explore"),
        send("SubagentStart", agent_id="a2", agent_type="reviewer"),
        send("PreToolUse", agent_id="a1", agent_type="Explore", tool_name="Grep", tool_input={}),
    ),
    "question": lambda: send(
        "Notification", notification_type="permission_prompt", message="permission"
    ),
    "done": lambda: send("Stop"),
    "end": lambda: send("SessionEnd"),
}


def scenario():
    send("SessionStart")
    time.sleep(3)
    send("UserPromptSubmit")
    time.sleep(2)
    tool("Read", file_path="/demo/model.py")
    tool("Grep", pattern="def compute")
    tool("Edit", 3, file_path="/demo/model.py")
    tool("Bash", 3, command="pytest", description="run the tests")
    STATES["agents"]()
    time.sleep(5)
    send("SubagentStop", agent_id="a1")
    time.sleep(2)
    send("SubagentStop", agent_id="a2")
    STATES["question"]()
    time.sleep(7)
    tool("WebSearch", query="documentation")
    send("Stop")
    time.sleep(10)
    send("SessionEnd")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        STATES[sys.argv[1]]()
    else:
        scenario()
