"""Agent chaining for multi-step workflows."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.agents.question_creator import QuestionCreatorAgent, QuestionSpec
from src.agents.test_creator import TestCreatorAgent
from src.config.schemas import ClassConfig
from src.agents.spawner import ClaudeSpawner
from src.tools.vault import VaultTool

logger = logging.getLogger(__name__)


@dataclass
class ChainStep:
    """Record of a single step in an agent chain.

    Attributes:
        agent_name: Name of the agent that ran.
        input_summary: Brief description of what was sent.
        output_summary: Brief description of the result.
        success: Whether the step completed successfully.
    """

    agent_name: str
    input_summary: str
    output_summary: str = ""
    success: bool = True


@dataclass
class ChainResult:
    """Result of a complete agent chain execution.

    Attributes:
        steps: List of ChainStep records.
        final_output: The final result dict from the last agent.
    """

    steps: list[ChainStep] = field(default_factory=list)
    final_output: dict = field(default_factory=dict)


def run_test_creation_chain(
    class_config: ClassConfig,
    vault: VaultTool,
    spawner: ClaudeSpawner,
    model: str,
    topics: list[str],
    question_count: int = 10,
    difficulty: str = "medium",
    message: str = "Create a practice test",
) -> ChainResult:
    """Run the question-creation -> test-assembly chain.

    Step 1: Generate questions via QuestionCreatorAgent.
    Step 2: Assemble into a test via TestCreatorAgent.

    Args:
        class_config: Class configuration.
        vault: VaultTool scoped to the class.
        spawner: ClaudeSpawner instance.
        model: Model identifier.
        topics: List of topics for question generation.
        question_count: Number of questions to generate.
        difficulty: Difficulty level.
        message: Message for the test creator.

    Returns:
        ChainResult with steps and final output.
    """
    chain = ChainResult()

    # Step 1: Generate questions
    step1 = _run_question_step(
        class_config, vault, spawner, model,
        topics, question_count, difficulty,
    )
    chain.steps.append(step1.step)
    if not step1.step.success:
        return chain

    # Step 2: Assemble test
    step2 = _run_test_step(
        class_config, vault, spawner, model,
        message, step1.questions,
    )
    chain.steps.append(step2)
    chain.final_output = step2.output if step2.success else {}
    return chain


@dataclass
class _QuestionStepResult:
    """Internal result from the question generation step."""

    step: ChainStep
    questions: list[dict] = field(default_factory=list)


def _run_question_step(
    class_config: ClassConfig,
    vault: VaultTool,
    spawner: ClaudeSpawner,
    model: str,
    topics: list[str],
    count: int,
    difficulty: str,
) -> _QuestionStepResult:
    """Run the question generation step of the chain.

    Args:
        class_config: Class configuration.
        vault: VaultTool scoped to the class.
        spawner: ClaudeSpawner instance.
        model: Model identifier.
        topics: Topics for question generation.
        count: Number of questions.
        difficulty: Difficulty level.

    Returns:
        _QuestionStepResult with step record and questions.
    """
    spec = QuestionSpec(
        topics=topics, count=count, difficulty=difficulty
    )
    step = ChainStep(
        agent_name="question-creator",
        input_summary=f"{count} {difficulty} questions on {topics}",
    )
    try:
        qc = QuestionCreatorAgent(
            class_config=class_config,
            vault=vault,
            spawner=spawner,
            model=model,
        )
        questions = qc.run_spec(spec)
        step.output_summary = f"Generated {len(questions)} questions"
        step.success = len(questions) > 0
        return _QuestionStepResult(step=step, questions=questions)
    except Exception as exc:
        logger.error("Question generation failed: %s", exc)
        step.output_summary = f"Error: {exc}"
        step.success = False
        return _QuestionStepResult(step=step)


@dataclass
class _TestStepResult:
    """Internal result from the test assembly step."""

    success: bool
    output: dict = field(default_factory=dict)


def _run_test_step(
    class_config: ClassConfig,
    vault: VaultTool,
    spawner: ClaudeSpawner,
    model: str,
    message: str,
    questions: list[dict],
) -> ChainStep:
    """Run the test assembly step of the chain.

    Args:
        class_config: Class configuration.
        vault: VaultTool scoped to the class.
        spawner: ClaudeSpawner instance.
        model: Model identifier.
        message: Message for the test creator.
        questions: Pre-generated questions.

    Returns:
        ChainStep record for this step.
    """
    step = ChainStep(
        agent_name="test-creator",
        input_summary=f"Assemble test from {len(questions)} questions",
    )
    try:
        tc = TestCreatorAgent(
            class_config=class_config,
            vault=vault,
            spawner=spawner,
            model=model,
        )
        result = tc.run(message, questions=questions)
        step.output_summary = (
            f"Test saved to {result.get('vault_path', 'unknown')}"
        )
        step.success = True
        step.output = result  # type: ignore[attr-defined]
        return step
    except Exception as exc:
        logger.error("Test assembly failed: %s", exc)
        step.output_summary = f"Error: {exc}"
        step.success = False
        return step
