
import os
import json
import redis
from dotenv import load_dotenv
from litellm import completion, RateLimitError, APIConnectionError, AuthenticationError
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

        prompt = (
            f"Break down the following goal into a list of actionable tasks as JSON. "
            f'Goal: "{user_goal}" '
            "Each task should have: taskName, description, duration, dependencies, phase, priority. "
            "Return only a JSON object with a 'plan' key containing the tasks."
        )


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
                print(f"LLM raw response: {result_content}")  # Log raw response

                from pydantic import ValidationError
                try:
                    validated_result = PlanResponse.model_validate_json(result_content)
                except ValidationError as ve:
                    print(f"Validation error: {ve}")  # Log validation error
                    return {"error": "AI response format error. Please try a simpler goal or contact support."}

                final_output = validated_result.model_dump()

                _save_plan_to_db(user_goal, final_output)
                redis_client.set(cache_key, json.dumps(final_output), ex=3600)
                return final_output

            except RateLimitError as e:
                print(f"Rate limit hit for model '{model}': {e}")
                return {"error": "The AI service is currently busy due to too many requests. Please wait a moment and try again."}
            except APIConnectionError as e:
                print(f"API connection error for model '{model}': {e}")
                continue
            except AuthenticationError as e:
                print(f"Authentication error for model '{model}': {e}")
                continue
            except Exception as e:
                # Handle NotFoundError and other unexpected errors
                if hasattr(e, 'message') and 'NOT_FOUND' in str(e):
                    print(f"Model not found error for model '{model}': {e}")
                    return {"error": f"The model '{model}' is not available for your API key or region. Please check your .env and use only supported models."}
                print(f"Unexpected error for model '{model}': {e}")
                continue

        print("--- All models failed. Returning a user-friendly error. ---")
        return {"error": "All of our AI models are currently busy or unavailable. Please try again in a few minutes."}

    except Exception as e:
        print(f"--- An unexpected critical error occurred in the task: {e} ---")
        return {"error": "An unexpected server error occurred. Please try again later."}

def _save_plan_to_db(user_goal: str, plan_data: dict):
    with Session(engine) as session:
        if "error" in plan_data:
            return

        existing_plan = session.exec(
            Plan.select().where(Plan.user_goal == user_goal)
        ).first()
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