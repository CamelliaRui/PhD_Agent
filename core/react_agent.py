"""
ReAct-style Agent Implementation

This module implements the ReAct (Reasoning + Acting) pattern for agentic AI:
- Thought: Reason about the current state and next steps
- Action: Choose and execute a tool
- Observation: Capture the result of the action
- Reflection: Evaluate progress toward the goal

References:
- ReAct Paper: https://arxiv.org/abs/2210.03629
- CALM: https://arxiv.org/abs/2310.04406
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from anthropic import Anthropic
import json

logger = logging.getLogger(__name__)


@dataclass
class ReasoningStep:
    """Represents one step in the ReAct reasoning trace"""
    step_num: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    reflection: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'step': self.step_num,
            'thought': self.thought,
            'action': self.action,
            'action_input': self.action_input,
            'observation': self.observation,
            'reflection': self.reflection,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class AgentMemory:
    """Stores the agent's reasoning history and context"""
    task: str
    steps: List[ReasoningStep] = field(default_factory=list)
    final_result: Optional[str] = None
    status: str = "running"  # running, completed, failed
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: ReasoningStep):
        """Add a reasoning step to memory"""
        self.steps.append(step)

    def get_recent_context(self, last_n: int = 3) -> str:
        """Get context from recent steps for the LLM"""
        recent = self.steps[-last_n:] if len(self.steps) > last_n else self.steps
        context = f"Task: {self.task}\n\n"
        context += "Recent steps:\n"
        for step in recent:
            context += f"\nStep {step.step_num}:\n"
            context += f"  Thought: {step.thought}\n"
            if step.action:
                context += f"  Action: {step.action}({step.action_input})\n"
            if step.observation:
                context += f"  Observation: {step.observation[:200]}...\n"
        return context


class ReactAgent:
    """
    ReAct-style agent that reasons about tasks and uses tools to accomplish them.

    The agent follows this loop:
    1. Think: Generate reasoning about current state and next step
    2. Act: Choose and execute a tool based on reasoning
    3. Observe: Capture the result of the action
    4. Reflect: Evaluate if progress is being made
    5. Decide: Continue or finish based on task completion
    """

    def __init__(
        self,
        api_key: str,
        tools: Dict[str, Callable],
        model: str = "claude-3-5-sonnet-20241022",
        max_steps: int = 10,
        verbose: bool = True
    ):
        """
        Initialize ReAct agent.

        Args:
            api_key: Anthropic API key
            tools: Dictionary of available tools {name: callable}
            model: Claude model to use
            max_steps: Maximum reasoning steps before forced termination
            verbose: Print reasoning traces to console
        """
        self.client = Anthropic(api_key=api_key)
        self.tools = tools
        self.model = model
        self.max_steps = max_steps
        self.verbose = verbose
        self.memory: Optional[AgentMemory] = None

    def run(self, task: str) -> Dict[str, Any]:
        """
        Execute a task using the ReAct loop.

        Args:
            task: The task to accomplish

        Returns:
            Dictionary with final result, reasoning trace, and metadata
        """
        self.memory = AgentMemory(task=task)
        step_num = 0

        if self.verbose:
            print(f"\n{'='*70}")
            print(f"🎯 Task: {task}")
            print(f"{'='*70}\n")

        while step_num < self.max_steps:
            step_num += 1

            # Step 1: Generate thought
            thought = self._generate_thought(step_num)

            if self.verbose:
                print(f"💭 Step {step_num} - Thought:")
                print(f"   {thought}\n")

            # Step 2: Decide if task is complete (or choose action)
            should_continue, completion_reason = self._assess_task_completion(thought)

            if not should_continue:
                # Task is complete
                final_step = ReasoningStep(
                    step_num=step_num,
                    thought=thought,
                    observation=f"Task completed: {completion_reason}"
                )
                self.memory.add_step(final_step)
                self.memory.status = "completed"
                self.memory.final_result = completion_reason

                if self.verbose:
                    print(f"✅ Task Complete!")
                    print(f"   {completion_reason}\n")

                break

            # Step 3: Choose and execute action
            action, action_input = self._choose_action(thought)

            if self.verbose:
                print(f"🔧 Action: {action}")
                print(f"   Input: {action_input}\n")

            observation = self._execute_action(action, action_input)

            if self.verbose:
                print(f"👁️  Observation:")
                obs_preview = observation[:200] + "..." if len(observation) > 200 else observation
                print(f"   {obs_preview}\n")

            # Step 4: Reflect on progress
            reflection = self._reflect_on_progress(thought, action, observation)

            if self.verbose:
                print(f"🤔 Reflection:")
                print(f"   {reflection}\n")
                print(f"{'-'*70}\n")

            # Store the step
            step = ReasoningStep(
                step_num=step_num,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
                reflection=reflection
            )
            self.memory.add_step(step)

        # If we hit max steps without completion
        if step_num >= self.max_steps and self.memory.status == "running":
            self.memory.status = "max_steps_reached"
            self.memory.final_result = "Task did not complete within maximum steps"

            if self.verbose:
                print(f"⚠️  Max steps ({self.max_steps}) reached without completion\n")

        return self._format_result()

    def _generate_thought(self, step_num: int) -> str:
        """
        Generate reasoning about the current state and what to do next.

        Uses the LLM to think about:
        - What has been done so far
        - What information is available
        - What the next logical step should be
        """
        context = self.memory.get_recent_context() if self.memory.steps else f"Task: {self.memory.task}"

        prompt = f"""You are a ReAct agent working on a task. Think step-by-step about what to do next.

{context}

Available tools: {', '.join(self.tools.keys())}

Think about:
1. What is the current state of the task?
2. What information do we have so far?
3. What is the next logical step?
4. Which tool (if any) should we use?

Provide your reasoning in 2-3 sentences. Be concise and action-oriented."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    def _assess_task_completion(self, current_thought: str) -> tuple[bool, Optional[str]]:
        """
        Assess whether the task is complete or should continue.

        This is a critical decision point in the ReAct loop. The agent must determine:
        - Has the original task been fully accomplished?
        - Is there enough information to provide a final answer?
        - Should we continue gathering more information?

        Args:
            current_thought: The agent's current reasoning

        Returns:
            Tuple of (should_continue, completion_reason)
            - should_continue: False if task is done, True if more steps needed
            - completion_reason: Explanation of why task is complete (or None if continuing)
        """
        # Step 1: Quick keyword-based check for obvious completion signals
        completion_keywords = [
            "found the answer", "task is complete", "task completed", "final answer",
            "solution is", "result is", "accomplished", "successfully", "solved",
            "no further action needed", "this completes", "finished", "done",
            "in conclusion", "therefore", "clearly", "definitely"
        ]
        
        thought_lower = current_thought.lower()
        for keyword in completion_keywords:
            if keyword in thought_lower:
                # Found a completion signal - but let's verify with LLM
                break
        else:
            # No obvious completion keywords, but still check with LLM for nuanced cases
            pass
        
        # Step 2: Use LLM to make a thorough assessment
        context = self.memory.get_recent_context() if self.memory.steps else f"Task: {self.memory.task}"
        
        prompt = f"""You are evaluating whether a ReAct agent has completed its task.

{context}

Current thought: {current_thought}

CRITICAL EVALUATION CRITERIA:
1. Has the original task been fully satisfied?
2. Is there a clear, actionable answer or result?
3. Would a reasonable person consider this task complete based on what's been accomplished?

Look for these completion signals:
- Explicit statements of completion ("found the answer", "task is complete")
- Provision of specific answers or solutions
- Confidence expressions ("I'm confident that", "clearly", "definitely")
- Conclusion indicators ("therefore", "in conclusion", "final answer")
- Success indicators ("successfully", "accomplished", "solved")

RESPOND WITH EXACTLY ONE OF THESE:
- "COMPLETE: [brief reason why task is complete]" 
- "CONTINUE: [brief reason why more work is needed]"

Be decisive. If there's a reasonable answer or the core task has been addressed, mark it COMPLETE."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )
            
            evaluation = response.content[0].text.strip()
            
            if evaluation.startswith("COMPLETE:"):
                completion_reason = evaluation[9:].strip()  # Remove "COMPLETE: " prefix
                return False, completion_reason
            elif evaluation.startswith("CONTINUE:"):
                return True, None
            else:
                # Fallback: parse for completion indicators
                if any(word in evaluation.lower() for word in ["complete", "done", "finished", "accomplished"]):
                    return False, "Task appears to be complete based on evaluation"
                else:
                    return True, None
                    
        except Exception as e:
            logger.warning(f"Error in completion assessment: {e}")
            # Step 3: Fallback logic if LLM call fails
            return self._fallback_completion_check(current_thought)
    
    def _fallback_completion_check(self, current_thought: str) -> tuple[bool, Optional[str]]:
        """
        Fallback completion check using simple heuristics when LLM evaluation fails.
        """
        thought_lower = current_thought.lower()
        
        # Strong completion indicators
        strong_indicators = [
            "found the answer", "task is complete", "final answer is",
            "solution is", "accomplished", "successfully completed"
        ]
        
        for indicator in strong_indicators:
            if indicator in thought_lower:
                return False, f"Completion detected: {indicator}"
        
        # Weak indicators (need multiple or longer thoughts)
        weak_indicators = ["done", "finished", "complete", "solved"]
        weak_count = sum(1 for indicator in weak_indicators if indicator in thought_lower)
        
        if weak_count >= 2 or len(current_thought) > 200:
            return False, "Multiple completion indicators detected"
        
        # Default: continue working
        return True, None

    def _choose_action(self, thought: str) -> tuple[str, Dict[str, Any]]:
        """
        Choose which tool to use based on current reasoning.

        The LLM decides which action best serves the next step.
        """
        context = self.memory.get_recent_context()
        tools_desc = "\n".join([f"- {name}: {func.__doc__}" for name, func in self.tools.items()])

        prompt = f"""{context}

Current thought: {thought}

Available tools:
{tools_desc}

Based on your thought, which tool should you use next?
Respond in JSON format:
{{
    "tool": "tool_name",
    "input": {{"param1": "value1", "param2": "value2"}}
}}

If no tool is needed (task is complete), respond with:
{{
    "tool": "finish",
    "input": {{"result": "final answer"}}
}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            action_json = json.loads(response.content[0].text.strip())
            return action_json['tool'], action_json.get('input', {})
        except:
            # Fallback if JSON parsing fails
            return "error", {"message": "Failed to parse action from LLM"}

    def _execute_action(self, action: str, action_input: Dict[str, Any]) -> str:
        """
        Execute the chosen tool and return the observation.
        """
        if action == "finish":
            return action_input.get('result', 'Task completed')

        if action == "error":
            return f"Error: {action_input.get('message', 'Unknown error')}"

        if action not in self.tools:
            return f"Error: Tool '{action}' not found. Available tools: {list(self.tools.keys())}"

        try:
            tool_func = self.tools[action]
            result = tool_func(**action_input)
            return str(result)
        except Exception as e:
            return f"Error executing {action}: {str(e)}"

    def _reflect_on_progress(self, thought: str, action: str, observation: str) -> str:
        """
        Reflect on whether the action moved us closer to the goal.

        This meta-reasoning helps the agent learn from its actions.
        """
        prompt = f"""Reflect on this reasoning step:

Task: {self.memory.task}
Thought: {thought}
Action taken: {action}
Result observed: {observation[:200]}

Did this action move us closer to completing the task? Why or why not?
Be brief (1-2 sentences)."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    def _format_result(self) -> Dict[str, Any]:
        """Format the final result with full reasoning trace"""
        return {
            'task': self.memory.task,
            'status': self.memory.status,
            'final_result': self.memory.final_result,
            'steps_taken': len(self.memory.steps),
            'reasoning_trace': [step.to_dict() for step in self.memory.steps],
            'metadata': self.memory.metadata
        }

    def get_reasoning_trace_text(self) -> str:
        """Get human-readable reasoning trace"""
        if not self.memory:
            return "No task executed yet"

        trace = f"Task: {self.memory.task}\n"
        trace += f"Status: {self.memory.status}\n\n"

        for step in self.memory.steps:
            trace += f"--- Step {step.step_num} ---\n"
            trace += f"Thought: {step.thought}\n"
            if step.action:
                trace += f"Action: {step.action}({step.action_input})\n"
            if step.observation:
                trace += f"Observation: {step.observation[:150]}...\n"
            if step.reflection:
                trace += f"Reflection: {step.reflection}\n"
            trace += "\n"

        trace += f"Final Result: {self.memory.final_result}\n"
        return trace
