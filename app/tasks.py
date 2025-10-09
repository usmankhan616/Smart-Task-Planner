import os
import json
import redis
from dotenv import load_dotenv
from litellm import completion
from sqlmodel import Session
from .celery_config import celery_app
from .models import PlanResponse, Plan, Task
from .database import engine

# Load environment variables from .env file
load_dotenv()

# --- Feature: Redis for Caching and Task Brokering ---
# This client is used for both Celery's backend and our manual caching.
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


# --- Feature: Celery for Background Tasks ---
# The `@celery_app.task` decorator turns this Python function into a background task.
# When the API calls `.delay()`, Celery picks it up and runs it on a separate worker.
@celery_app.task(bind=True)
def generate_plan_task(self, user_goal: str):
    
    # --- Feature: Redis for Caching ---
    # We create a unique key based on the user's goal to check if we've seen this request before.
    cache_key = f"plan:{user_goal.lower().strip()}"
    cached_result = redis_client.get(cache_key)
    
    # If a result is found in the cache, we return it immediately without calling the LLM.
    if cached_result:
        parsed_result = json.loads(cached_result)
        # We still save it to the DB in case it was a cached-only result
        # This part could be enhanced to check DB first, but this ensures data integrity.
        _save_plan_to_db(user_goal, parsed_result)
        return parsed_result

    # --- Feature: LLM Abstraction with LiteLLM ---
    # Instead of hardcoding "gpt-3.5-turbo", we read the model name from your .env file.
    # Now you can switch models without touching the code.
    llm_model_to_use = os.getenv("LLM_MODEL")

    prompt = f"""
    You are an expert project planner. Your goal is to break down a user's request into a detailed, actionable plan.
    The user's goal is: "{user_goal}"
    Break this down into actionable tasks. Include phases for research, design, development, and launch.
    Present the output as a single JSON object with a key named "plan" containing an array of task objects. Each task object must have keys: "taskName", "description", "duration", "dependencies", "phase", and "priority".
    """
    
    try:
        # LiteLLM uses the model specified in `llm_model_to_use` to make the API call.
        response = completion(
            model=llm_model_to_use,
            messages=[{"content": prompt, "role": "user"}],
            response_format={"type": "json_object"},
        )
        
        result_content = response.choices[0].message.content
        validated_result = PlanResponse.model_validate_json(result_content)
        final_output = validated_result.model_dump()

        # Save the new result to the database.
        _save_plan_to_db(user_goal, final_output)
        
        # --- Feature: Redis for Caching ---
        # Store the new, valid result in the Redis cache for 1 hour (3600 seconds).
        redis_client.set(cache_key, json.dumps(final_output), ex=3600)
        
        return final_output

    except Exception as e:
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise e

def _save_plan_to_db(user_goal: str, plan_data: dict):
    """Helper function to save a plan to the database."""
    with Session(engine) as session:
        # Check if a plan with this exact goal already exists to avoid duplicates
        existing_plan = session.query(Plan).filter(Plan.user_goal == user_goal).first()
        if existing_plan:
            return # Don't save a duplicate

        new_plan = Plan(user_goal=user_goal)
        session.add(new_plan)
        session.commit()
        session.refresh(new_plan)

        for task_data in plan_data.get("plan", []):
            new_task = Task.model_validate(task_data)
            new_task.plan_id = new_plan.id
            session.add(new_task)
        
        session.commit()
