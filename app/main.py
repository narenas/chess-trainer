import os
import uuid
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

from .models import TaskIn, TaskDB, TaskPatch, RecoResponse
from .reco import rank_tasks

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = os.getenv("DB_NAME", "chess_trainer")

app = FastAPI(title="Chess Trainer API (Minimal)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DB:
    client: AsyncIOMotorClient | None = None


db = DB()


@app.on_event("startup")
async def _startup():
    db.client = AsyncIOMotorClient(MONGO_URI)


@app.on_event("shutdown")
async def _shutdown():
    if db.client:
        db.client.close()


def get_col(name: str):
    if not db.client:
        raise RuntimeError("DB client not initialized")
    return db.client[DB_NAME][name]


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# Simulación de usuario autenticado (MVP): fija un user_id
async def get_user_id() -> str:
    return "demo-user-1"


@app.post("/tasks")
async def create_task(task: TaskIn, user_id: str = Depends(get_user_id)):
    try:
        t = TaskDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=task.title,
            category=task.category,
            estimated_minutes=task.estimated_minutes,
            due_at=task.due_at,
            state="todo",
            created_at=datetime.utcnow(),
            priority=50,
        )
        await get_col("tasks").insert_one(t.model_dump())
        return t
    except Exception:
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/tasks", response_model=List[TaskDB])
async def list_tasks(state: str | None = None, user_id: str = Depends(get_user_id)):
    q = {"user_id": user_id}
    if state:
        q["state"] = state
    cursor = get_col("tasks").find(q).sort("created_at", 1)
    return [TaskDB(**doc) async for doc in cursor]


@app.patch("/tasks/{task_id}", response_model=TaskDB)
async def patch_task(task_id: str, patch: TaskPatch, user_id: str = Depends(get_user_id)):
    doc = await get_col("tasks").find_one({"id": task_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = {}
    if patch.state:
        updates["state"] = patch.state
        if patch.state == "done":
            updates["completed_at"] = datetime.utcnow()
    if patch.snoozed_until:
        updates["snoozed_until"] = patch.snoozed_until

    if not updates:
        return TaskDB(**doc)

    await get_col("tasks").update_one({"id": task_id}, {"$set": updates})
    doc.update(updates)
    return TaskDB(**doc)


class WeeklyDone(BaseModel):
    # Conteo simple de completadas por categoría (MVP)
    tactics: int = 0
    strategy: int = 0
    openings: int = 0
    endgames: int = 0
    analysis: int = 0


@app.get("/reco/next-best-actions", response_model=RecoResponse)
async def next_best_actions(limit: int = 3, user_id: str = Depends(get_user_id)):
    # Candidatas: tareas TODO del usuario
    cursor = get_col("tasks").find({"user_id": user_id, "state": "todo"})
    tasks = [TaskDB(**doc) async for doc in cursor]

    # Semilla: conteo naïf de completadas por categoría en últimos 7 días (MVP)
    seven_days_ago = datetime.utcnow().timestamp() - 7 * 86400
    completed = get_col("tasks").find({
        "user_id": user_id,
        "state": "done",
        "completed_at": {"$gte": datetime.utcfromtimestamp(seven_days_ago)},
    })
    counts = {"tactics": 0, "strategy": 0, "openings": 0, "endgames": 0, "analysis": 0}
    async for d in completed:
        counts[d["category"]] = counts.get(d["category"], 0) + 1

    items = rank_tasks(tasks, counts, k=limit)
    return RecoResponse(items=items)
