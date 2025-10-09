import os
import json
import redis
from dotenv import load_dotenv
from litellm import completion
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
        return parsed_result

    prompt = f"""
    You are an expert project planner. Your goal is to break down a user's request into a detailed, actionable plan.
    The user's goal is: "{user_goal}"
    Break this down into actionable tasks. Include phases for research, design, development, and launch.
    Present the output as a single JSON object with a key named "plan" containing an array of task objects. Each task object must have keys: "taskName", "description", "duration", "dependencies", "phase", and "priority".
    """
    
    try:
        response = completion(
            model="gpt-3.5-turbo",
            messages=[{"content": prompt, "role": "user"}],
            response_format={"type": "json_object"},
        )
        
        result_content = response.choices[0].message.content
        validated_result = PlanResponse.model_validate_json(result_content)
        
        with Session(engine) as session:
            new_plan = Plan(user_goal=user_goal)
            session.add(new_plan)
            session.commit()
            session.refresh(new_plan)

            for task_data in validated_result.plan:
                new_task = Task.model_validate(task_data)
                new_task.plan_id = new_plan.id
                session.add(new_task)
            
            session.commit()
        
        final_output = validated_result.model_dump()
        redis_client.set(cache_key, json.dumps(final_output), ex=3600) # Cache for 1 hour
        return final_output

    except Exception as e:
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise e