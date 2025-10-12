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
    cache_key = f"plan:{user_goal.lower().strip()}"
    cached_result = redis_client.get(cache_key)
    if cached_result:
        parsed_result = json.loads(cached_result)
        _save_plan_to_db(user_goal, parsed_result)
        return parsed_result

    llm_models_str = os.getenv("LLM_MODELS", "gpt-3.5-turbo")
    models_list = [model.strip() for model in llm_models_str.split(',')]

    prompt = f"""
    You are an expert project planner. Your goal is to break down a user's request into a detailed, actionable plan.
    The user's goal is: "{user_goal}"
    Break this down into actionable tasks. Include phases for research, design, development, and launch.
    Present the output as a single JSON object with a key named "plan" containing an array of task objects. Each task object must have keys: "taskName", "description", "duration", "dependencies", "phase", and "priority".
    """
    
    try:
        response = completion(
            model=models_list,
            messages=[{"content": prompt, "role": "user"}],
            response_format={"type": "json_object"},
        )
        
        result_content = response.choices[0].message.content
        validated_result = PlanResponse.model_validate_json(result_content)
        final_output = validated_result.model_dump()

        _save_plan_to_db(user_goal, final_output)
        redis_client.set(cache_key, json.dumps(final_output), ex=3600)
        return final_output

    except RateLimitError as e:
        return {"error": "All our AI models are currently busy or over quota. Please try again in a few minutes."}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

def _save_plan_to_db(user_goal: str, plan_data: dict):
    with Session(engine) as session:
        existing_plan = session.query(Plan).filter(Plan.user_goal == user_goal).first()
        if existing_plan or "error" in plan_data:
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

