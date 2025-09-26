from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy import Table, MetaData
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
import typing
from typing import List, Optional
from sqlalchemy import Integer, String, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column, sessionmaker
from sqlalchemy.ext.associationproxy import association_proxy
# ... (rest of your imports)
import os

# -----------------
# 1. Pydantic Models (Data Structure/Validation)
# -----------------

# Base class for the declarative models
Base = declarative_base()

# --- Association Tables ---

# 1. user2project Association Table
# This is typically an independent model to hold the 'access_type' data
class UserToProject(Base):
    __tablename__ = 'user2project'
    
    user_id: Mapped[int] = mapped_column(ForeignKey('user_table.user_id'), primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('project.project_id'), primary_key=True)
    
    access_type: Mapped[str] = mapped_column(String(12), nullable=False)
    
    # Relationships to core models
    # The string references are required since the classes are defined later
    user: Mapped["UserTable"] = relationship(back_populates="projects_link")
    project: Mapped["Project"] = relationship(back_populates="users_link")


class ProjectToDocument(Base):
    __tablename__ = 'project2document'
    
    project_id: Mapped[int] = mapped_column(ForeignKey('project.project_id'), primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('document.document_id'), primary_key=True)
    
    # Relationships to core models
    project: Mapped["Project"] = relationship(back_populates="documents_link")
    document: Mapped["Document"] = relationship(back_populates="projects_link")


# -----------------------------------------------------------------
# 3. CORE MODELS
# -----------------------------------------------------------------

class UserTable(Base):
    __tablename__ = 'user_table'

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 1. One-to-Many Relationship to the Association Object
    projects_link: Mapped[List[UserToProject]] = relationship(back_populates="user")
    
    # 2. Many-to-Many Relationship via association_proxy for direct access
    projects: Mapped[List["Project"]] = association_proxy(
        "projects_link", "project", creator=lambda proj: UserToProject(project=proj)
    )


class Project(Base):
    __tablename__ = 'project'

    project_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Use Optional for Python typing of nullable column
    description: Mapped[Optional[str]] = mapped_column(String(500)) 
    
    # User Relationships
    users_link: Mapped[List[UserToProject]] = relationship(back_populates="project")
    users: Mapped[List["UserTable"]] = association_proxy(
        "users_link", "user", creator=lambda user: UserToProject(user=user)
    )
    
    # Document Relationships
    documents_link: Mapped[List[ProjectToDocument]] = relationship(back_populates="project")
    documents: Mapped[List["Document"]] = association_proxy(
        "documents_link", "document", creator=lambda doc: ProjectToDocument(document=doc)
    )


class Document(Base):
    __tablename__ = 'document'

    document_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    s3_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    
    # Project Relationships
    projects_link: Mapped[List[ProjectToDocument]] = relationship(back_populates="document")
    projects: Mapped[List[Project]] = association_proxy(
        "projects_link", "project", creator=lambda proj: ProjectToDocument(project=proj)
    )
# -----------------
# 2. Application Setup
# -----------------

# Create the FastAPI application instance
app = FastAPI(
    title="Final Task",
    description="Project management api",
    version="1.0.0"
)

connection_url = URL.create(
    drivername="postgresql",
    username=os.environ["DB_USER"],
    host=os.environ["DB_HOST"],
    database=os.environ["DB_NAME"],
    password=os.environ["DB_PASSWORD"]
)

engine = create_engine(connection_url, pool_pre_ping=True)

# wait until postgres container can accept connection requests
__import__("time").sleep(5)

Base.metadata.create_all(engine)

# -----------------
# 3. Routes (Endpoints)
# -----------------

# GET Endpoint: Root Path
@app.get("/")
async def read_root():
    """Returns a simple welcome message."""
    return {"message": "Welcome to the Project Management API! Please go to /auth or /login to authorize"}

# POST /auth - Create user (login, password, repeat password)
@app.post("/auth")
async def auth_method():
    pass

# POST /login - Login into service (login, password)
@app.post("/login")
async def login_method():
    pass

# POST /projects - Create project from details (name, description).
# Automatically gives access to created project to user, making him the owner (admin of the project).
@app.post("/projects")
async def post_project():
    pass

# GET /projects - Get all projects, accessible for a user. Returns list of projects full info(details + documents).
@app.get("/projects")
async def get_projects():
    pass

# GET /project/<project_id>/info - Return project’s details, if user has access
@app.get("/projects/{project_id}/info")
async def get_project(project_id: int):
    pass

# PUT /project/<project_id>/info - Update projects details - name, description. Returns the updated project’s info
@app.put("/projects/{project_id}/info")
async def put_project(project_id: int): # needs to get a project model from request body
    pass

# DELETE /project/<project_id>- Delete project, can only be performed by the projects’ owner. Deletes the corresponding documents
@app.delete("/project/{project_id}")
async def delete_project(project_id: int):
    pass

# GET /project/<project_id>/documents- Return all of the project's documents
@app.get("/project/{project_id}/documents")
async def get_documents(project_id: int):
    pass

# POST /project/<project_id>/documents - Upload document/documents for a specific project
@app.post("/project/{project_id}/documents")
async def post_document(project_id: int):
    pass

# GET /document/<document_id> - Download document, if the user has access to the corresponding project
@app.get("/document/{document_id}")
async def get_document(document_id: int):
    pass

# PUT /document/<document_id> - Update document
@app.put("/document/{document_id}")
async def put_document(document_id: int):
    pass

# DELETE /document/<document_id> - Delete document and remove it from the corresponding project
@app.delete("/document/{document_id}")
async def delete_document(document_id: int):
    pass

# POST /project/<project_id>/invite?user= - Grant access to the project for a specific user.
# If the request is not coming from the owner of the project, results in error.,
# Granting access gives participant permissions to receiving user
@app.post("/project/{project_id}/invite?user={username}")
async def invite_to_project(project_id: int, username: str):
    pass

# Run with: uvicorn app.main:app --reload