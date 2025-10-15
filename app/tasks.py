import os
import json
import redis
import uuid
import datetime
from dotenv import load_dotenv
from sqlmodel import Session, select
from .celery_config import celery_app
from .models import Plan, Task
from .database import engine

# OpenAI import
try:
    import openai
except Exception:
    openai = None

load_dotenv()
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if openai and OPENAI_KEY:
    openai.api_key = OPENAI_KEY

@celery_app.task(bind=True)
def generate_plan_task(self, user_goal: str, deadline: str = None, owner_id: int = None):
    cache_key = f"plan:{user_goal.lower().strip()}"
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result)

    plan_id = str(uuid.uuid4())
    try:
        if openai and OPENAI_KEY:
            prompt = (
                "You are an expert project planner. Given a short user goal, break it into an ordered list of tasks. "
                "Return JSON: {title, generated_by, tasks:[{id,title,duration_days,dependencies,priority,notes}], created_at}.\n\n"
                f"Goal: {user_goal}\n"
            )
            if deadline:
                prompt += f"Deadline: {deadline}\n"
            prompt += "Return only JSON."

            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.2,
            )
            content = response['choices'][0]['message']['content']
            try:
                plan = json.loads(content)
            except Exception:
                import re
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    plan = json.loads(match.group(0))
                else:
                    raise
            plan.setdefault('created_at', str(datetime.datetime.utcnow()))
            plan['generated_by'] = 'openai'
        else:
            raise RuntimeError("OpenAI not configured")
    except Exception as e:
        plan = rule_based_planner(user_goal, deadline)
        plan['fallback_reason'] = str(e)

    plan_id = str(uuid.uuid4())
    _save_plan_to_db(user_goal, plan, owner_id)
    redis_client.set(cache_key, json.dumps(plan), ex=3600)
    return {"id": plan_id, "plan": plan}

def rule_based_planner(goal_text, deadline_date=None):
    canonical_steps = [
        ("Clarify goal & constraints", 1),
        ("Research & gather requirements", 2),
        ("Design solution / plan tasks", 2),
        ("Implement / execute", 5),
        ("Testing / validation", 2),
        ("Launch / deliver", 1),
        ("Monitor & iterate", 3),
    ]
    tasks = []
    current_day_offset = 0
    for i, (title, dur) in enumerate(canonical_steps, start=1):
        dur_adj = max(1, int(round(dur)))
        start_date = datetime.date.today() + datetime.timedelta(days=current_day_offset)
        end_date = start_date + datetime.timedelta(days=dur_adj - 1)
        tasks.append({
            "id": f"t{i}",
            "title": title,
            "duration_days": dur_adj,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "dependencies": [f"t{i-1}"] if i > 1 else [],
            "priority": "medium",
            "notes": f"Auto-generated from goal: {goal_text[:120]}"
        })
        current_day_offset += dur_adj
    return {
        "title": goal_text,
        "generated_by": "rule_based",
        "tasks": tasks,
        "created_at": str(datetime.datetime.utcnow())
    }

def _save_plan_to_db(user_goal: str, plan_data: dict, owner_id: int = None):
    with Session(engine) as session:
        statement = select(Plan).where(Plan.user_goal == user_goal)
        existing_plan = session.exec(statement).first()
        if existing_plan:
            return
        new_plan = Plan(user_goal=user_goal, owner_id=owner_id)
        session.add(new_plan)
        session.commit()
        session.refresh(new_plan)
        for task_data in plan_data.get("tasks", []):
            mapped_task = {
                'taskName': task_data.get('title', ''),
                'description': task_data.get('notes', ''),
                'duration': str(task_data.get('duration_days', '')),
                'dependencies': ','.join(task_data.get('dependencies', [])) if isinstance(task_data.get('dependencies', []), list) else str(task_data.get('dependencies', '')),
                'phase': '',
                'priority': task_data.get('priority', 'medium'),
                'plan_id': new_plan.id
            }
            new_task = Task.model_validate(mapped_task)
            session.add(new_task)
        session.commit()