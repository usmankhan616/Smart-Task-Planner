from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from celery.result import AsyncResult
from .tasks import generate_plan_task
from .database import create_db_and_tables

app = FastAPI(title="Smart Task Planner")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/generate-plan")
async def post_generate_plan(request: Request):
    form_data = await request.form()
    goal = form_data.get("goal")
    if not goal:
        return HTMLResponse("Goal is required.", status_code=400)
    
    task = generate_plan_task.delay(goal)
    return templates.TemplateResponse("polling.html", {
        "request": request,
        "task_id": task.id,
        "status": "PENDING"
    })

@app.get("/api/task-status/{task_id}")
async def get_task_status(request: Request, task_id: str):
    task_result = AsyncResult(task_id)
    
    if task_result.ready():
        if task_result.successful():
            return templates.TemplateResponse("result.html", {
                "request": request,
                "plan": task_result.result
            })
        else:
            return HTMLResponse(f"<p class='text-red-500'>Task failed: {task_result.result}</p>")
    
    return templates.TemplateResponse("polling.html", {
        "request": request,
        "task_id": task_id,
        "status": task_result.status
    })