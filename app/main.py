from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from celery.result import AsyncResult
from sqlmodel import Session, select
from typing import Optional

from .tasks import generate_plan_task
from .database import create_db_and_tables, engine
from .models import User
from .security import (
    get_password_hash, create_access_token, verify_password, 
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from datetime import timedelta

app = FastAPI(title="Smart Task Planner")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("index.html", {"request": request, "user": current_user})

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
def handle_login(form_data: OAuth2PasswordRequestForm = Depends()):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == form_data.username)).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        
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

@app.post("/api/generate-plan")
async def post_generate_plan(request: Request, goal: str = Form(...), current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    task = generate_plan_task.delay(goal)
    return templates.TemplateResponse("polling.html", {"request": request, "task_id": task.id, "status": "PENDING"})

@app.get("/api/task-status/{task_id}")
async def get_task_status(request: Request, task_id: str, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    task_result = AsyncResult(task_id)
    if task_result.ready():
        # THIS IS THE KEY CHANGE: We no longer check if the task was "successful".
        # We just get the result (which will be a dictionary) and pass it to the template.
        return templates.TemplateResponse("result.html", {
            "request": request, 
            "plan": task_result.result
        })
    
    # If the task is not ready, we continue to show the polling template.
    return templates.TemplateResponse("polling.html", {
        "request": request, 
        "task_id": task_id, 
        "status": task_result.status
    })