import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import litellm
from litellm import completion
import logging
from dataclasses import dataclass
from .models import Task, TaskStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TaskBreakdown:
    task_name: str
    description: str
    duration: str
    dependencies: str
    phase: str
    priority: str

class LLMService:
    def __init__(self):
        self.providers = []
        self._setup_providers()
        
    def _setup_providers(self):
        """Setup multiple LLM providers based on available API keys"""
        
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            self.providers.append({
                "model": os.getenv("LLM_OPENAI_MODEL", "gpt-3.5-turbo"),
                "api_key": os.getenv("OPENAI_API_KEY"),
                "provider": "openai"
            })
            logger.info("✓ OpenAI provider configured")
        
        # Anthropic Claude
        if os.getenv("ANTHROPIC_API_KEY"):
            self.providers.append({
                "model": os.getenv("LLM_ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "provider": "anthropic"
            })
            logger.info("✓ Anthropic provider configured")
        
        # Google Gemini
        if os.getenv("GEMINI_API_KEY"):
            gemini_model = os.getenv("LLM_GEMINI_MODEL", "gemini/gemini-1.5-flash")
            # Normalize model name for litellm gemini adapter
            if not gemini_model.startswith("gemini/"):
                gemini_model = f"gemini/{gemini_model.lstrip('models/')}"
            self.providers.append({
                "model": gemini_model,
                "api_key": os.getenv("GEMINI_API_KEY"),
                "provider": "gemini"
            })
            logger.info(f"✓ Gemini provider configured ({gemini_model})")
        
        if not self.providers:
            logger.warning("⚠️ No LLM providers configured! Check your .env file.")

    def _set_api_key_for_provider(self, provider: Dict[str, str]):
        if provider['provider'] == 'openai':
            os.environ["OPENAI_API_KEY"] = provider['api_key']
        elif provider['provider'] == 'anthropic':
            os.environ["ANTHROPIC_API_KEY"] = provider['api_key']
        elif provider['provider'] == 'gemini':
            os.environ["GEMINI_API_KEY"] = provider['api_key']

    async def _call_completion(self, provider: Dict[str, str], messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        self._set_api_key_for_provider(provider)
        # Ensure correct gemini model prefix
        model_name = provider['model']
        if provider['provider'] == 'gemini' and not model_name.startswith('gemini/'):
            model_name = f"gemini/{model_name.lstrip('models/')}"
        response = await asyncio.to_thread(
            completion,
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        return content

    def _select_primary_secondary(self):
        """Select primary/secondary providers based on env vars.
        LLM_PRIMARY_PROVIDER and LLM_SECONDARY_PROVIDER can be one of: openai, anthropic, gemini
        If unset or unavailable, fall back to available providers order.
        """
        if not self.providers:
            return None, None
        name_to_provider = {p['provider']: p for p in self.providers}
        primary_name = os.getenv("LLM_PRIMARY_PROVIDER")
        secondary_name = os.getenv("LLM_SECONDARY_PROVIDER")

        primary = name_to_provider.get(primary_name) if primary_name else None
        primary = primary or (self.providers[0] if self.providers else None)

        secondary = name_to_provider.get(secondary_name) if secondary_name else None
        if not secondary:
            # pick a different provider than primary if possible
            secondary = next((p for p in self.providers if p is not primary), primary)
        return primary, secondary
    
    async def generate_tasks(self, user_goal: str) -> List[TaskBreakdown]:
        """Generate tasks using multi-model workflow: one model drafts, another elaborates each task."""
        if not self.providers:
            logger.warning("No providers configured, using fallback")
            return self._get_fallback_tasks(user_goal)
        
        primary, secondary = self._select_primary_secondary()
        if not primary:
            logger.warning("No providers configured, using fallback")
            return self._get_fallback_tasks(user_goal)

        draft_system = (
            "You are an expert project manager. Return ONLY a JSON array of task stubs for the goal, "
            "where each item has: task_name (string only). 5-8 tasks."
        )
        draft_user = f"Goal: {user_goal}\nReturn only the JSON array of objects: [{{\"task_name\": \"...\"}}, ...]"

        try:
            logger.info(f"Drafting tasks with {primary['provider']} -> {primary['model']}")
            draft_json = await self._call_completion(
                primary,
                messages=[
                    {"role": "system", "content": draft_system},
                    {"role": "user", "content": draft_user}
                ],
                temperature=0.4,
                max_tokens=400
            )
            draft_items = json.loads(draft_json)
            if not isinstance(draft_items, list):
                raise ValueError("Draft response is not a JSON array")
            task_names = [item.get("task_name", "Unnamed Task") for item in draft_items if isinstance(item, dict)]
            task_names = [name for name in task_names if name]
            if not task_names:
                raise ValueError("No task names produced in draft stage")
        except Exception as e:
            logger.error(f"Draft stage failed: {e}")
            # Fall back to single-shot generation below
            task_names = []

        tasks: List[TaskBreakdown] = []
        if task_names:
            # Elaborate each task with secondary model so each step is distinct
            for idx, name in enumerate(task_names, start=1):
                try:
                    logger.info(f"Elaborating task {idx}/{len(task_names)} with {secondary['provider']}")
                    elaborate_system = (
                        "You are a senior project planner. Expand the provided task into a detailed, unique specification. "
                        "Return ONLY JSON with keys: description, duration, dependencies, phase, priority."
                    )
                    elaborate_user = (
                        f"Goal: {user_goal}\n"
                        f"Task: {name}\n"
                        "Constraints:\n"
                        "- Provide realistic duration (e.g., '2 days', '1 week').\n"
                        "- If no blocking work, set dependencies to 'None'.\n"
                        "- Phase must be one of: Planning, Research, Design, Implementation, Testing, Launch, Maintenance.\n"
                        "- Priority must be one of: high, medium, low.\n"
                        "Respond with only JSON: {\"description\":..., \"duration\":..., \"dependencies\":..., \"phase\":..., \"priority\":...}"
                    )
                    details_json = await self._call_completion(
                        secondary,
                        messages=[
                            {"role": "system", "content": elaborate_system},
                            {"role": "user", "content": elaborate_user}
                        ],
                        temperature=0.7,
                        max_tokens=600
                    )
                    details = json.loads(details_json)
                    tasks.append(TaskBreakdown(
                        task_name=name,
                        description=details.get("description", f"Detailed work for {name}"),
                        duration=details.get("duration", "2 days"),
                        dependencies=details.get("dependencies", "None"),
                        phase=details.get("phase", "Planning"),
                        priority=details.get("priority", "medium"),
                    ))
                except Exception as e:
                    logger.error(f"Elaboration failed for '{name}': {e}")
                    # Reasonable fallback per-task to avoid identical outputs
                    default_phase = "Planning" if idx == 1 else "Implementation"
                    tasks.append(TaskBreakdown(
                        task_name=name,
                        description=f"Plan and execute: {name} for goal '{user_goal[:80]}...'",
                        duration="2-3 days",
                        dependencies="None" if idx == 1 else task_names[idx-2],
                        phase=default_phase,
                        priority="medium",
                    ))
            logger.info(f"✅ Generated and elaborated {len(tasks)} tasks (multi-model)")
            return tasks

        # Single-shot generation fallback using first available provider loop (original logic)
        system_prompt = """You are an expert project manager and task planning AI. Your job is to break down user goals into actionable tasks with realistic timelines.

IMPORTANT: You must respond with ONLY a valid JSON array. No other text, explanations, or markdown formatting.

The JSON should contain an array of task objects, each with these exact fields:
- task_name: string (concise task title)
- description: string (detailed description of what needs to be done)
- duration: string (e.g., "2 days", "1 week", "3 hours")
- dependencies: string (what must be completed before this task, or "None")
- phase: string (project phase: Planning, Research, Design, Implementation, Testing, Launch, or Maintenance)
- priority: string ("high", "medium", or "low")

Consider:
- Logical task dependencies and sequencing
- Realistic time estimates
- Proper project phases
- Risk mitigation and planning tasks
- Testing and quality assurance
- Documentation and handover"""

        user_prompt = f"""Break down this goal into 5-8 actionable tasks with dependencies and timelines:

Goal: {user_goal}

Respond with only the JSON array of tasks."""

        for i, provider in enumerate(self.providers):
            try:
                logger.info(f"Attempting task generation with {provider['provider']} (attempt {i+1}/{len(self.providers)})")
                content = await self._call_completion(
                    provider,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                logger.info(f"Raw response from {provider['provider']}: {content[:200]}...")
                tasks_data = json.loads(content)
                if not isinstance(tasks_data, list):
                    raise ValueError("Response is not a JSON array")
                tasks = []
                for task_data in tasks_data:
                    required_fields = ['task_name', 'description', 'duration', 'dependencies', 'phase', 'priority']
                    if not all(field in task_data for field in required_fields):
                        logger.warning(f"Task missing required fields: {task_data}")
                        continue
                    tasks.append(TaskBreakdown(
                        task_name=task_data['task_name'],
                        description=task_data['description'],
                        duration=task_data['duration'],
                        dependencies=task_data['dependencies'],
                        phase=task_data['phase'],
                        priority=task_data['priority']
                    ))
                logger.info(f"✅ Successfully generated {len(tasks)} tasks using {provider['provider']}")
                return tasks
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error with {provider['provider']}: {e}")
                logger.error(f"Raw content: {content}")
                continue
            except Exception as e:
                logger.error(f"Error with {provider['provider']}: {str(e)}")
                continue

        logger.warning("All LLM providers failed, using fallback task generation")
        return self._get_fallback_tasks(user_goal)
    
    def _get_fallback_tasks(self, user_goal: str) -> List[TaskBreakdown]:
        """Fallback task generation when all LLM providers fail"""
        return [
            TaskBreakdown(
                task_name="Define Requirements & Constraints",
                description=f"Clarify specific requirements, constraints, and success criteria for: {user_goal[:100]}...",
                duration="1-2 days",
                dependencies="None",
                phase="Planning",
                priority="high"
            ),
            TaskBreakdown(
                task_name="Research & Analysis",
                description="Conduct necessary research, competitive analysis, and gather required information",
                duration="2-3 days",
                dependencies="Define Requirements & Constraints",
                phase="Research",
                priority="high"
            ),
            TaskBreakdown(
                task_name="Create Implementation Plan",
                description="Design detailed approach, architecture, and step-by-step implementation strategy",
                duration="1-2 days",
                dependencies="Research & Analysis",
                phase="Design",
                priority="medium"
            ),
            TaskBreakdown(
                task_name="Execute Core Implementation",
                description="Execute the main development/implementation work according to the plan",
                duration="5-7 days",
                dependencies="Create Implementation Plan",
                phase="Implementation",
                priority="high"
            ),
            TaskBreakdown(
                task_name="Testing & Quality Assurance",
                description="Thoroughly test implementation, fix bugs, and ensure quality standards",
                duration="2-3 days",
                dependencies="Execute Core Implementation",
                phase="Testing",
                priority="medium"
            ),
            TaskBreakdown(
                task_name="Launch & Deployment",
                description="Deploy, launch, and make the solution live with proper monitoring",
                duration="1 day",
                dependencies="Testing & Quality Assurance",
                phase="Launch",
                priority="high"
            )
        ]

# Singleton instance
llm_service = LLMService()
