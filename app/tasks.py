import os
import json
import redis
from dotenv import load_dotenv
from litellm import completion, RateLimitError
from sqlmodel import Session
from .celery_config import celery_app
from .models import PlanResponse, Plan, Task
from .database import engine

load_dotenv()
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

@celery_app.task(bind=True)
def generate_plan_task(self, user_goal: str):
    try:
        cache_key = f"plan:{user_goal.lower().strip()}"
        cached_result = redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

        llm_models_str = os.getenv("LLM_MODELS", "gpt-3.5-turbo")
        models_list = [model.strip() for model in llm_models_str.split(',')]
        
        prompt = f"""
        You are an expert project planner. Your goal is to break down a user's request into a detailed, actionable plan.
        The user's goal is: "{user_goal}"
        Break this down into actionable tasks. Include phases for research, design, development, and launch.
        Present the output as a single JSON object with a key named "plan" containing an array of task objects. Each task object must have keys: "taskName", "description", "duration", "dependencies", "phase", and "priority".
        """

        for model in models_list:
            try:
                print(f"--- Attempting to generate plan with model: {model} ---")
                response = completion(
                    model=model,
                    messages=[{"content": prompt, "role": "user"}],
                    response_format={"type": "json_object"},
                )
                
                print(f"--- Successfully generated plan with model: {model} ---")
                result_content = response.choices[0].message.content
                validated_result = PlanResponse.model_validate_json(result_content)
                final_output = validated_result.model_dump()

                _save_plan_to_db(user_goal, final_output)
                redis_client.set(cache_key, json.dumps(final_output), ex=3600)
                return final_output

            except RateLimitError:
                print(f"--- Model '{model}' is over quota. Trying next model... ---")
                continue # This is the failover: we just try the next model in the list
            
        # If the loop finishes without returning, it means all models failed.
        print("--- All models failed. Returning a user-friendly error. ---")
        return {"error": "All of our AI models are currently busy or over quota. Please try again in a few minutes."}

    except Exception as e:
        # This is a final safety net to catch any other unexpected errors and prevent the task from crashing.
        print(f"--- An unexpected critical error occurred in the task: {e} ---")
        return {"error": "An unexpected server error occurred. Please try again later."}


def _save_plan_to_db(user_goal: str, plan_data: dict):
    # This function remains the same
    with Session(engine) as session:
        if "error" in plan_data:
            return

        existing_plan = session.query(Plan).filter(Plan.user_goal == user_goal).first()
        if existing_plan:
            return

        new_plan = Plan(user_goal=user_goal)
        session.add(new_plan)
        session.commit()
        session.refresh(new_plan)

        for task_data in plan_data.get("plan", []):
            new_task = Task.model_validate(task_data)
            new_task.plan_id = new_plan.id
            session.add(new_task)
        
        session.commit()