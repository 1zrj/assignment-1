"""The Part 1 coding agent: fix a software issue and submit a git patch."""

from __future__ import annotations

import json
from typing import Any

from assignment.agent.base import (
    DEFAULT_COMPACTION_KEEP_RECENT_STEPS,
    DEFAULT_COMPACTION_MAX_TOKENS,
    Agent,
    format_tool_output
)
from assignment.agent.tools import EXECUTE_TOOL, SEND_MESSAGE_TOOL
from assignment.env import Environment

class CodeAgent(Agent):
    """An agent that fixes a software issue and submits a git patch."""

    def __init__(
        self,
        task: str,
        environment: Environment,
        model: str | None = None,
        logs_save_path: str | None = None,
        step_limit: int = 100,
        skills_path: str | None = None,
        auto_stop_environment: bool = True,
        compact_threshold_tokens: int | None = None,
        compaction_keep_recent_steps: int = DEFAULT_COMPACTION_KEEP_RECENT_STEPS,
        compaction_max_tokens: int = DEFAULT_COMPACTION_MAX_TOKENS,
    ):
        super().__init__(
            environment=environment,
            model=model,
            logs_save_path=logs_save_path,
            step_limit=step_limit,
            skills_path=skills_path,
            auto_stop_environment=auto_stop_environment,
            compact_threshold_tokens=compact_threshold_tokens,
            compaction_keep_recent_steps=compaction_keep_recent_steps,
            compaction_max_tokens=compaction_max_tokens,
        )
        self.task = task
        self.submitted_patch = ""

        # TODO(Part 1.3): Make the `execute` and `send_message` tools available
        # to the agent.
        self.tools.extend([EXECUTE_TOOL, SEND_MESSAGE_TOOL])
        # TODO(1.1.b): Construct the system prompt and task_prompt. These
        # should be usable by the `Agent.build_prompt` method.
        import platform

        self.system_prompt = f"""You are a software engineering agent
            <system_information>
            {{
            "machine": "{platform.machine()}",
            "release": "{platform.release()}",
            "system": "{platform.system()}",
            "version": "{platform.version()}"
            }}
            </system_information>
        """
        self.task_prompt = task
        # TODO(1.4): If any skills are available to the agent, make their
        # descriptions/metadata available to the agent in the prompt.
        if self.skills:
            skill_catalog = "\n".join(
                skill["metadata"] for skill in self.skills.values()
            )
            self.system_prompt += f"\n\nAvailable skills:\n{skill_catalog}"

    def execute_tool_calls(
        self, tool_calls: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Execute ``execute`` and ``send_message`` calls in the code sandbox."""

        # TODO(Part 1.3): Parse each call, execute recognized tools, and return
        # one message per call (there may be multiple tool calls in one agent
        # response!). Malformed JSON and unknown tools must become recoverable
        # observations relayed to the agent instead of exceptions.
        observations: list[dict[str, str]] = []

        for call in tool_calls:
            call_id = call.get("id", "")
            function_info = call.get("function", {})
            name = function_info.get("name", "")
            raw_args = function_info.get("arguments", "{}")

            # ── 1. 解析 JSON 参数 ──
            try:
                args = json.loads(raw_args)
                if not isinstance(args, dict):
                    raise ValueError("arguments must be a JSON object")
            except (json.JSONDecodeError, ValueError) as exc:
                observations.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": f"Error: invalid JSON arguments: {exc}",
                })
                continue

            # ── 2. 根据工具名分发 ──
            if name == "execute":
                result = self.env.execute(
                    command=args["command"],
                    shell=args.get("shell"),
                    cwd=args.get("cwd"),
                    timeout=args.get("timeout"),
                    env=args.get("env"),
                )
                content = format_tool_output(result)

            elif name == "send_message":
                self.finished = True
                self.submitted_patch = ...  # 从 env 读取 patch（后续实现）
                content = args.get("summary", "")

            elif name == "invoke_skill":
                skill_name = args.get("name", "")
                skill = self.skills.get(skill_name)
                if skill:
                    content = skill["content"]
                else:
                    content = f"Error: unknown skill '{skill_name}'"

            else:
                # 未知工具：可恢复错误
                content = f"Error: unknown tool '{name}'"

            observations.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": content,
            })

        return observations
