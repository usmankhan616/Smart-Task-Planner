from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import Optional
from datetime import timedelta
from .database import create_db_and_tables, engine
from .models import User
from .security import (
    get_password_hash, create_access_token, verify_password, 
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Smart Task Planner")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    # Retry DB init on cold starts or transient network issues
    create_db_and_tables(retries=5, delay=2.0)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("index.html", {"request": request, "user": current_user, "plan": None})

@app.get("/signup", response_class=HTMLResponse)
def get_signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup", response_class=HTMLResponse)
def handle_signup(request: Request, email: str = Form(...), password: str = Form(...)):
    with Session(engine) as session:
        existing_user = session.exec(select(User).where(User.email == email)).first()
        if existing_user:
            return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered"})
        
        hashed_password = get_password_hash(password)
        new_user = User(email=email, hashed_password=hashed_password)
        session.add(new_user)
        session.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/login", response_class=HTMLResponse)
def get_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...)):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == username)).first()
        if not user or not verify_password(password, user.hashed_password):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Incorrect email or password"}, status_code=status.HTTP_401_UNAUTHORIZED)
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
        return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="access_token")
    return response

@app.get("/tasks")
def tasks_redirect():
    return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)


@app.get("/profile", response_class=HTMLResponse)
async def view_profile(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    from .models import Plan, Task, TaskProgress
    with Session(engine) as session:
        # Get all plans for the current user ordered by creation date
        user_plans = session.exec(
            select(Plan)
            .where(Plan.owner_id == current_user.id)
            .order_by(Plan.created_at.desc())
        ).all()
        
        # Get all tasks for tracking with their progress
        all_user_tasks = []
        for plan in user_plans:
            for task in plan.tasks:
                # Get latest progress for each task
                latest_progress = session.exec(
                    select(TaskProgress)
                    .where(TaskProgress.task_id == task.id)
                    .order_by(TaskProgress.timestamp.desc())
                ).first()
                all_user_tasks.append({
                    'task': task,
                    'plan': plan,
                    'latest_progress': latest_progress
                })
        
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": current_user, 
        "plans": user_plans,
        "task_progress": all_user_tasks
    })

@app.post("/api/generate-plan")
async def post_generate_plan(request: Request, goal: str = Form(...), current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from .models import Plan, Task, TaskStatus
    from .llm_service import llm_service
    import logging
    from fastapi.responses import HTMLResponse
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Generating plan for goal: {goal[:100]}...")
        
        # Generate tasks using AI (multi-model)
        task_breakdowns = await llm_service.generate_tasks(goal)
        
        # Save to database
        with Session(engine) as session:
            # Create new plan (don't check for existing to allow multiple plans)
            new_plan = Plan(user_goal=goal, owner_id=current_user.id)
            session.add(new_plan)
            session.commit()
            session.refresh(new_plan)
            
            plan_tasks = []
            for breakdown in task_breakdowns:
                new_task = Task(
                    taskName=breakdown.task_name,
                    description=breakdown.description,
                    duration=breakdown.duration,
                    dependencies=breakdown.dependencies,
                    phase=breakdown.phase,
                    priority=breakdown.priority,
                    status=TaskStatus.REJECTED,  # Start as not submitted
                    plan_id=new_plan.id
                )
                session.add(new_task)
                plan_tasks.append(new_task)
            
            session.commit()
            
            # Refresh tasks to ensure they have IDs
            for task in plan_tasks:
                session.refresh(task)
            
            logger.info(f"✅ Created plan with {len(plan_tasks)} tasks")
            plan_data = {"tasks": plan_tasks}

        # Render the result fragment first, then auto-redirect to profile after a short delay
        html_fragment = templates.get_template("result.html").render({
            "request": request,
            "plan": plan_data
        })
        redirect_script = """
<script>
  setTimeout(function(){ window.location.href = '/profile'; }, 2000);
</script>
"""
        return HTMLResponse(content=html_fragment + redirect_script)
        
    except Exception as e:
        logger.error(f"Error generating plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")

@app.post("/api/toggle-task/{task_id}")
async def toggle_task_completion(task_id: int, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from .models import Task
    with Session(engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        from .models import TaskStatus
        # Toggle between SUBMITTED and COMPLETED
        if task.status == TaskStatus.COMPLETED:
            task.status = TaskStatus.SUBMITTED
        else:
            task.status = TaskStatus.COMPLETED
        
        session.commit()
        return {"status": "success", "new_status": task.status}

@app.post("/api/submit-task/{task_id}")
async def toggle_task_submission(task_id: int, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from .models import Task
    with Session(engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        from .models import TaskStatus
        # Toggle between REJECTED (not submitted) and SUBMITTED (submitted for review)
        if task.status == TaskStatus.SUBMITTED:
            task.status = TaskStatus.REJECTED  # Unsubmit
        else:
            task.status = TaskStatus.SUBMITTED  # Submit
        
        session.commit()
        return {"status": "success", "new_status": task.status}
