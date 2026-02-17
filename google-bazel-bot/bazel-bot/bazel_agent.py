from collections.abc import Sequence
import os
import asyncio
import logging
import sys
from typing import AsyncGenerator, List
from dotenv import load_dotenv
import argparse
import json
from enum import Enum
from dataclasses import dataclass
from utils import CredentialManager, LocalGitRepo, CommandProcessor
import tools

# ADK Imports
from google.adk.agents import LlmAgent, BaseAgent
from google.adk.models.google_llm import _ResourceExhaustedError
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

parser = argparse.ArgumentParser(description="Bazelbot")
parser.add_argument(
    "--llvm_git_repo", type=str, help="Absolute path to LLVM Github repo", required=True
)
parser.add_argument(
    "--commit_sha", type=str, help="Git Commit SHA to process", required=True
)

# Configuration
load_dotenv()

MAX_AGENT_ITERATIONS = 5
USER_ID = "default_user"
APP_NAME = "bazel_fixer"

MODEL = "gemini-3-pro-preview"

CODE_FIXER_PROMPT = """
## Context
You are an expert Bazel build engineer for the LLVM project.
Your goal is to fix Bazel build errors caused by a specific commit ({commit_sha}) in the llvm-project.
You are working together with a bazelbuilder agent which does bazel build on your code changes. Any errors are reported back to you for refining your fixes.

## Inputs
<COMMIT_SHA>
{commit_sha}
</COMMIT_SHA>

<REPO_PATH>
{repo_path}
</REPO_PATH>

<PAST_WRONG_FIXES>
{past_fixes}
</PAST_WRONG_FIXES>

## Guidelines
You can use following guidelines to figure out what changes needs to be made to make bazel build pass:

- You must pay close attention to past wrong fixes provided to you. These fixes were made earlier and didn't lead to a successful build. Do not attempt to make these fixes again.
- It's useful to look at the target that's failing in the error message and then map it to corresponding target definition in the BUILD.bazel file.
- Use `get_diff` tool to see what has changed for {commit_sha}. If you are not able to use this tool, it's futile to move ahead. You should just give up at that point.
- From the diff obtained above and given error message, figure out what could have caused the build error and what changes needs to be made to fix the build. If you need more context, you can use `read_file` tool to inspect any files in the repository you like. 
- Once you have a potential fix, you can use `search_and_replace` tool to modify any file on the disk. Make sure you pass exact text you want to replace, otherwise, this wouldn't succeed. 
- You can read the directory structure of utils/bazel/llvm-project-overlay/ using `directory_structure` tool if needed.
- Try to make minimal set of changes necessary to fix the build.

## Common pitfalls
1. Any BUILD.bazel or *.bzl file is going to be in the llvm-project-overlay/ directory. So it is important to append that to the given repo path to be able to read these files. Otherwise, you would get file not found errors from the `read_file` tool.
2. If in some circumstances, if you would like to read any source files, you need to remove utils/bazel suffix in the repo path before using `read_file` tool. If you don't, you would get file not found errors from the `read_file` tool.
3. You should not modify files outside of llvm-project-overlay/ directory. The `search_and_replace` tool only works when you modify files 
4. Do not make any changes to MODULE.bazel.lock file. bazel builds may modify those files but you should not attempt to make further changes to it.
"""

code_fixer = LlmAgent(
    name="code_fixer",
    description="Fixes code based on error messages and commit context.",
    model=MODEL,
    instruction=CODE_FIXER_PROMPT,
    tools=[
        tools.read_file,
        tools.search_and_replace,
        tools.get_diff,
        tools.directory_structure,
    ],
)


class BazelFixerAgent(BaseAgent):  # pytype: disable=wrong-arg-types
    """
    An orchestrator agent that runs a Bazel build for specific targets,
    and if it fails, delegates to the code_fixer agent in a loop until the build passes.

    Input parameters (commit_sha, repo_path, past_fixes) are expected to be in the session state.
    """

    fixer_agent: LlmAgent
    max_iterations: int
    logger_agent: logging.Logger
    cmd_processor: CommandProcessor

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        build_result = self.cmd_processor.run_bazel_build()
        if build_result.success:
            yield Event(
                author=self.name,
                content=Content(
                    parts=[Part(text="✅ Bazel Build already passing! Exiting loop.")]
                ),
            )
            return

        yield Event(
            author=self.name,
            content=Content(
                parts=[
                    Part(
                        text=f"Starting Fix Loop for {ctx.session.state.get('commit_sha')}"
                    )
                ]
            ),
        )
        for i in range(self.max_iterations):
            is_last_attempt = i == self.max_iterations - 1
            yield Event(
                author=self.name,
                content=Content(
                    parts=[Part(text=f"Iteration {i+1}: Running Bazel Build...")]
                ),
            )

            self.logger_agent.info(f"Build Failed. Delegating to Code Fixer...")
            fix_request = [
                "The Bazel build failed with the following error:",
                "<STDERR>" f"{build_result.stderr}" "</STDERR>",
                "<STDOUT>" f"{build_result.stdout}" "</STDOUT>",
            ]
            if i == 0:
                fix_request.append("Please fix this issue.")
            elif is_last_attempt:
                fix_request.append(
                    "This is your last chance to fix the issue. Please try again."
                )
            else:
                fix_request.append("We need more fixes.")

            self.logger_agent.info(f"Fix request from user: {'\n'.join(fix_request)}")
            ctx.session.events.append(
                Event(
                    invocation_id=ctx.invocation_id,
                    author="bazelbuilder",
                    content=Content(
                        role="user",
                        parts=[Part(text="\n".join(fix_request))],
                    ),
                )
            )

            # The main AI agent loop
            async for event in self.fixer_agent.run_async(ctx):
                yield event

            # Check if agent fixed the build for us
            build_result = self.cmd_processor.run_bazel_build()
            if build_result.success:
                yield Event(
                    author=self.name,
                    content=Content(
                        parts=[Part(text="✅ Bazel Build passed! Exiting fix loop.")]
                    ),
                )
                return
            else:
                if is_last_attempt:
                    yield Event(
                        author=self.name,
                        content=Content(
                            parts=[
                                Part(text="❌ Reached max iterations. Exiting fix loop.")
                            ]
                        ),
                    )
                else:
                    yield Event(
                        author=self.name,
                        content=Content(
                            parts=[
                                Part(
                                    text=f"Build still failing after attempt {i+1}. Continuing fix loop."
                                )
                            ]
                        ),
                    )


class AgentErrors(Enum):
    SUCCESS = 0
    AGENT_RESOURCE_EXHAUSTED = 1
    FAILURE = 2


@dataclass
class AgentResult:
    status: AgentErrors
    summary: Sequence[str]


async def query_agent(
    commit_sha: str, cmd_processor: CommandProcessor, past_fixes: List[str]
) -> AgentResult:
    """
    A self-contained method to invoke the BazelFixerAgent from external modules.
    Args:
        commit_sha: The Git SHA of the commit to fix/analyze.
        cmd_processor: The CommandProcessor instance for running commands.
        past_fixes: list of incorrect past fixes that agent made.

    Returns:
        AgentResult: Dataclass containing status and summary.
    """
    logging_id = commit_sha
    logger_agent = logging.getLogger(logging_id)
    logger_agent.setLevel(logging.INFO)
    if not logger_agent.handlers:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        fh = logging.FileHandler(f"bot_agent.{logging_id}.log")
        fh.setFormatter(formatter)
        logger_agent.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger_agent.addHandler(sh)
        logger_agent.propagate = False

    session_service = InMemorySessionService()
    bazel_agent = BazelFixerAgent(
        name="bazel_fixer_agent",
        fixer_agent=code_fixer,
        max_iterations=MAX_AGENT_ITERATIONS,
        logger_agent=logger_agent,
        cmd_processor=cmd_processor,
    )

    runner = Runner(
        app_name=APP_NAME, agent=bazel_agent, session_service=session_service
    )

    # Create a new session
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={
            "repo_path": cmd_processor.bazel_path,
            "commit_sha": commit_sha,
            "past_fixes": json.dumps(past_fixes),
        },
    )

    content = Content(
        role="user",
        parts=[Part(text="Please fix the build for me.")],
    )
    # Execute the agent synchronously
    logger_agent.info(f"--- Invoking Agent for {commit_sha} ---")
    logger_agent.info(f"Past Fixes: {past_fixes}")
    messages = list()
    try:
        async for event in runner.run_async(
            user_id=USER_ID, session_id=session.id, new_message=content
        ):
            if event.get_function_calls():
                logger_agent.info(
                    f"Function Calls: {[fn_call.name for fn_call in event.get_function_calls()]}"
                )
            elif event.get_function_responses():
                logger_agent.info(
                    f"Function Responses: {[fn_resp.name for fn_resp in event.get_function_responses()]}"
                )
            elif event.content and event.content.parts:
                message = "\n\n".join(
                    part.text for part in event.content.parts if part.text
                )
                logger_agent.info(message)
                if event.is_final_response():
                    messages.append(message)
    except _ResourceExhaustedError:
        logger_agent.exception("Resource exhausted while running Agent")
        return AgentResult(
            status=AgentErrors.AGENT_RESOURCE_EXHAUSTED, summary="Resource exhausted"
        )

    # Check if build succeeds now
    build_result = cmd_processor.run_bazel_build()
    return AgentResult(
        status=AgentErrors.SUCCESS if build_result.success else AgentErrors.FAILURE,
        summary=messages,
    )


# main function is present to test bazel_agent.py independently.
async def main():
    args = parser.parse_args(sys.argv[1:])
    print("Simulating external call to query_agent...")

    cmd_processor = CommandProcessor(args.llvm_git_repo)
    git_repo = LocalGitRepo(args.llvm_git_repo, CredentialManager(), False)
    git_repo.create_branch_for_fix(args.commit_sha)
    final_output = await query_agent(
        commit_sha=args.commit_sha,
        cmd_processor=cmd_processor,
        past_fixes=[],
    )

    print(f"\nFinal Result:\n{final_output}")


if __name__ == "__main__":
    asyncio.run(main())
