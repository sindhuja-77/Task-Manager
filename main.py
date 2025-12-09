#imports 
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from dotenv import load_dotenv
import os
from openai import OpenAI
import json

load_dotenv()
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

client=OpenAI(api_key=OPENAI_API_KEY)
DATABASE_URL = "sqlite:///./tasks.db"

# Database setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# DB model
class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, default="")
    completed = Column(Boolean, default=False)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic schemas
class Task(BaseModel):
    title: str
    description: str = ""
    completed: bool = False

class TaskDB(Task):
    id: int
    class Config:
        from_attributes = True

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/tasks", response_model=List[TaskDB])
def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(TaskModel).all()
    return tasks

@app.post("/tasks", response_model=TaskDB)
def create_task(task: Task, db: Session = Depends(get_db)):
    db_task = TaskModel(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.put("/tasks/{task_id}", response_model=TaskDB)
def update_task(task_id: int, task: Task, db: Session = Depends(get_db)):
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.title = task.title
    db_task.description = task.description
    db_task.completed = task.completed
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted"}


#LLM based recommendations 

@app.get("/recommendations")
def get_task_recommendations(db: Session = Depends(get_db)):
    tasks = db.query(TaskModel).all()

    if not tasks:
        return {"message": "No tasks available for recommendations."}

    task_summary = "\n".join(
        [f"- {t.title} (Completed: {t.completed})" for t in tasks]
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful task management assistant."},
            {
                "role": "user",
                "content": (
                     f"Here are my current tasks:\n{task_summary}\n\n"
                    "Please provide recommendations on which tasks to prioritize and next steps. "
                    "Format your response clearly: "
                    "- Use numbered tasks. "
                    "- Use bold text for priorities. "
                    "- Include bullet points for actionable next steps. "
                    "- Add a short final recommendation. "
                    "Return as plain text with line breaks so it's easy to read."
                )
            },
        ],
    )

    return {"recommendation": response.choices[0].message.content}

#creating a task using LLM 

class TaskPrompt(BaseModel):
    prompt: str

@app.post("/generate_task")
def generate_task(task_prompt: TaskPrompt, db: Session = Depends(get_db)):
    prompt_text = task_prompt.prompt

    # Call LLM
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a task creation assistant. Generate concise tasks."},
            {"role": "user", "content": f"Create a task from this request: {prompt_text}. Respond only in JSON like {{\"title\":\"...\", \"description\":\"...\"}}"}
        ]
    )

    # Get raw content
    content_str = response.choices[0].message.content

    # Convert string to JSON safely
    try:
        task_data = json.loads(content_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"LLM response is not valid JSON: {content_str}")

    # Save task in DB
    db_task = TaskModel(
        title=task_data.get("title", "Untitled Task"),
        description=task_data.get("description", ""),
        completed=False
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return db_task