from typing import Optional, Annotated
from fastapi import FastAPI, HTTPException, Request, Depends, Header, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy import Table, MetaData
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
import typing
from typing import List, Optional
from sqlalchemy import Integer, String, ForeignKey, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column, sessionmaker
from sqlalchemy.ext.associationproxy import association_proxy
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from jose import JWTError, jwt
from dotenv import load_dotenv
import hashlib
import os

# so that aws.env file's contents will override the environment variables given to this container
load_dotenv()

# replace it with your 32 bit secret key
SECRET_KEY = "09d25e094faalp9okxvcvd28tjbaf7099f6f0f4caa6cf63b88e8d3e7"

BUCKET_NAME = "FINAL_TASK_S3_BUCKET"

# encryption algorithm
ALGORITHM = "HS256"

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

engine = create_engine(connection_url)

s3 = boto3.client('s3',
         aws_access_key_id=os.environ["aws_access_key_id"],
         aws_secret_access_key=os.environ["aws_secret_access_key"])

if BUCKET_NAME not in [x["Name"] for x in s3.list_buckets()["Buckets"]]:
    s3.create_bucket(Bucket=BUCKET_NAME)

# wait until postgres container can accept connection requests
__import__("time").sleep(5)

Base.metadata.create_all(engine)

class LoginModel(BaseModel):
    username: str
    password: str

class RegisterModel(BaseModel):
    username: str
    password: str
    repeat_password: str

class ProjectModel(BaseModel):
    name: str
    description: str

# -----------------
# 3. Routes (Endpoints)
# -----------------

Session = sessionmaker(bind=engine)
session = Session()

def extract_token(header_value):
    token = header_value.strip()
    if "Bearer" in token and " " in token:
        token = token.split(" ")[1]
    return token

def verify_token(authorization: Annotated[str | None, Header()] = None):
    try:
        if authorization:
            # try to decode the token, it will 
            # raise error if the token is not correct
            token = extract_token(authorization)
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return True
        else:
            raise JWTError()
    except JWTError as e:
        print(e)
        raise HTTPException(
            status_code=401,
            detail="Could not validate jwt token",
        )

def hash_data(strdata):
    m = hashlib.sha256()
    m.update(strdata.encode("utf-8"))
    return m.hexdigest()

# GET Endpoint: Root Path
@app.get("/")
async def read_root():
    """Returns a simple welcome message."""
    return {"message": "Welcome to the Project Management API! Please go to /auth or /login to authorize"}

# POST /auth - Create user (login, password, repeat password)
@app.post("/auth")
async def auth_method(model: RegisterModel):
    if (model.password != model.repeat_password):
        raise HTTPException(
            status_code=400,
            detail="Passwords are different!",
        )
    new_data = UserTable(login=model.username, password_hash=hash_data(model.password))
    session.add(new_data)
    session.commit()

# POST /login - Login into service (login, password)
@app.post("/login")
async def login_method(model: LoginModel):
    user_query = session.query(UserTable)
    user = user_query.filter(UserTable.login == model.username).first()
    if user and hash_data(model.password) == user.password_hash:
        to_encode = {"login": model.username}
        expire = datetime.utcnow() + timedelta(minutes=60)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return {"token": encoded_jwt}
    else:
        raise HTTPException(
            status_code=403,
            detail="Incorrect credentials!",
        )

# POST /projects - Create project from details (name, description).
# Automatically gives access to created project to user, making him the owner (admin of the project).
@app.post("/projects")
async def post_project(model: ProjectModel, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        # create a project
        new_project = Project(name=model.name, description=model.description)
        session.add(new_project)
        session.commit()
        # get user id from username, get username from jwt
        token = extract_token(authorization)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
        user_id = user.user_id
        # add user2project, userid, projectid as owner access
        new_relation = UserToProject(user_id=user_id, project_id=new_project.project_id, access_type="owner")
        session.add(new_relation)
        session.commit()

# GET /projects - Get all projects, accessible for a user. Returns list of projects full info(details + documents).
@app.get("/projects")
async def get_projects(authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        # get user id
        token = extract_token(authorization)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
        if not user:
            return []
        user_id = user.user_id
        # get all projects with that user_id
        project_ids = session.query(UserToProject).filter(UserToProject.user_id == user_id).all()
        project_ids = [x.project_id for x in project_ids]
        projects = session.query(Project).filter(Project.project_id.in_(project_ids)).all()
        return projects

# GET /project/<project_id>/info - Return project’s details, if user has access
@app.get("/projects/{project_id}/info")
async def get_project(project_id: int, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        # get user id
        token = extract_token(authorization)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
        if not user:
            raise HTTPException(
                status_code=403,
                detail="User couldn't find!",
            )
        user_id = user.user_id
        # check access
        relation = session.query(UserToProject).filter(UserToProject.user_id == user_id and UserToProject.project_id == project_id).first()
        if not relation:
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this project!",
            )
        # 
        return session.query(Project).filter(Project.project_id == project_id).first()

# PUT /project/<project_id>/info - Update projects details - name, description. Returns the updated project’s info
@app.put("/projects/{project_id}/info")
async def put_project(model: ProjectModel, project_id: int, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None): # needs to get a project model from request body
    if authorized:
        # get user id
        token = extract_token(authorization)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
        if not user:
            raise HTTPException(
                status_code=403,
                detail="User couldn't find!",
            )
        user_id = user.user_id
        # check access
        relation = session.query(UserToProject).filter(UserToProject.user_id == user_id and UserToProject.project_id == project_id).first()
        if not relation:
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this project!",
            )
        # get project and update
        project = session.query(Project).filter(Project.project_id == project_id).first()
        project.name = model.name
        project.description = model.description
        session.commit()

# DELETE /project/<project_id>- Delete project, can only be performed by the projects’ owner. Deletes the corresponding documents
@app.delete("/project/{project_id}")
async def delete_project(project_id: int, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        # get user id
        token = extract_token(authorization)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
        if not user:
            raise HTTPException(
                status_code=403,
                detail="User couldn't find!",
            )
        user_id = user.user_id
        # check access
        relation = session.query(UserToProject).filter(UserToProject.user_id == user_id and UserToProject.project_id == project_id).first()
        if not relation or relation.access_type != "owner":
            raise HTTPException(
                status_code=403,
                detail="You don't have owner access to this project!",
            )
            return
        # get and delete the project
        project = session.query(Project).filter(Project.project_id == project_id).first()
        session.delete(project)
        # get document ids related to this project
        document_relations = session.query(ProjectToDocument).filter(ProjectToDocument.project_id == project_id).all()
        document_ids = [x.document_id for x in document_relations]
        documents = session.query(Document).filter(Document.document_id.in_(document_ids)).all()
        # delete documents and document relations since documents are tighted to projects
        documents.delete()
        document_relations.delete()
        # get user relations related to this project and delete
        session.query(UserToProject).filter(UserToProject.project_id == project_id).all().delete()
        session.commit()

# GET /project/<project_id>/documents- Return all of the project's documents
@app.get("/project/{project_id}/documents")
async def get_documents(project_id: int, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        # get user id
        token = extract_token(authorization)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
        if not user:
            raise HTTPException(
                status_code=403,
                detail="User couldn't find!",
            )
        user_id = user.user_id
        # check access
        relation = session.query(UserToProject).filter(UserToProject.user_id == user_id and UserToProject.project_id == project_id).first()
        if not relation:
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this project!",
            )
        # get documents
        relations = session.query(ProjectToDocument).filter(ProjectToDocument.project_id == project_id).all()
        document_ids = [x.document_id for x in relations]
        return session.query(Document).filter(Document.document_id.in_(document_ids)).all()

# POST /project/<project_id>/documents - Upload document/documents for a specific project
@app.post("/project/{project_id}/documents")
async def post_document(file: Annotated[bytes, File()], project_id: int, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        try:
            # get user id
            token = extract_token(authorization)
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
            if not user:
                raise HTTPException(
                    status_code=403,
                    detail="User couldn't find!",
                )
            user_id = user.user_id
            # check access
            relation = session.query(UserToProject).filter(UserToProject.user_id == user_id and UserToProject.project_id == project_id).first()
            if not relation or relation.access_type != "owner":
                raise HTTPException(
                    status_code=403,
                    detail="You don't have access to this project!",
                )
            # upload document
            digestable = file.name + datetime.utcnow()
            response = s3_client.upload_fileobj(file, bucket, hash_data(digestable))
            session.add(Document(name=file.name,s3_key=hash_data(digestable)))
            session.commit()
            doc_id = session.query(Document).filter(Document.name == file.name and Document.s3_key == hash_data(digestable)).first().document_id
            relation = ProjectToDocument(document_id=doc_id, project_id=project_id)
            session.add(relation)
            session.commit()
            return {"success":True, "document_id":doc_id}
        except ClientError as e:
            print(e)
            raise HTTPException(
                status_code=500,
                detail="Couldn't upload it to AWS!"
            )
        except HTTPException as e:
            raise e

# GET /document/<document_id> - Download document, if the user has access to the corresponding project
@app.get("/document/{document_id}")
async def download_document(document_id: int, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        try:
            # get user id
            token = extract_token(authorization)
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
            if not user:
                raise HTTPException(
                    status_code=403,
                    detail="User couldn't find!",
                )
            user_id = user.user_id
            # check access
            temp = session.query(ProjectToDocument).filter(ProjectToDocument.document_id == document_id).first()
            if not temp:
                raise HTTPException(
                    status_code=400,
                    detail="Document doesn't exist!",
                )
            project_id = temp.project_id
            relation = session.query(UserToProject).filter(UserToProject.user_id == user_id and UserToProject.project_id == project_id).first()
            if not relation:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have access to this project!",
                )
            # upload document
            document_sql_record = session.query(Document).filter(Document.document_id == relation.document_id).first()
            with open("tempfile", 'wb') as f:
                s3.download_fileobj(BUCKET_NAME, document_sql_record.s3_key, f)
            return FileResponse(path="./tempfile", media_type='application/octet-stream', filename=document_sql_record.name)
        except ClientError as e:
            print(e)
            raise HTTPException(
                status_code=500,
                detail="Couldn't upload it to AWS!"
            )
        except HTTPException as e:
            raise e

# PUT /document/<document_id> - Update document
@app.put("/document/{document_id}")
async def put_document(file: Annotated[bytes, File()], document_id: int, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        relation = session.query(ProjectToDocument).filter(ProjectToDocument.document_id == document_id).first()
        if not relation:
            raise HTTPException(
                status_code=400,
                detail="Document doesn't exist!"
            )
        project_id = relation.project_id
        delete_document(document_id)
        post_document(file, project_id)

# DELETE /document/<document_id> - Delete document and remove it from the corresponding project
@app.delete("/document/{document_id}")
async def delete_document(document_id: int, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        try:
            # get user id
            token = extract_token(authorization)
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
            if not user:
                raise HTTPException(
                    status_code=403,
                    detail="User couldn't find!",
                )
            user_id = user.user_id
            # check access
            temp = session.query(ProjectToDocument).filter(ProjectToDocument.document_id == document_id).first()
            if not temp:
                raise HTTPException(
                    status_code=400,
                    detail="Document doesn't exist!",
                )
            project_id = temp.project_id
            relation = session.query(UserToProject).filter(UserToProject.user_id == user_id and UserToProject.project_id == project_id).first()
            if not relation or relation.access_type != "owner":
                raise HTTPException(
                    status_code=403,
                    detail="You don't have access to this project!",
                )
            # delete document
            document_sql_record = session.query(Document).filter(Document.document_id == document_id).first()
            document_relation = session.query(ProjectToDocument).filter(ProjectToDocument.document_id == document_id).first()
            session.delete(document_sql_record)
            session.delete(document_relation)
            session.commit()
            s3.delete_object(Bucket=BUCKET_NAME, Key=document_sql_record.s3_key)
            return {"success": True}
        except ClientError as e:
            print(e)
            raise HTTPException(
                status_code=500,
                detail="Couldn't upload it to AWS!"
            )
        except HTTPException as e:
            raise e

# POST /project/<project_id>/invite?user= - Grant access to the project for a specific user.
# If the request is not coming from the owner of the project, results in error.,
# Granting access gives participant permissions to receiving user
@app.post("/project/{project_id}/invite?user={username}")
async def invite_to_project(project_id: int, username: str, authorized: bool = Depends(verify_token), authorization: Annotated[str | None, Header()] = None):
    if authorized:
        # get user id
        token = extract_token(authorization)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = session.query(UserTable).filter(UserTable.login == payload["login"]).first()
        if not user:
            raise HTTPException(
                status_code=403,
                detail="User couldn't find!",
            )
        user_id = user.user_id
        # check access
        relation = session.query(UserToProject).filter(UserToProject.user_id == user_id and UserToProject.project_id == project_id).first()
        if not relation or relation.access_type != "owner":
            raise HTTPException(
                status_code=403,
                detail="You don't have owner access to this project!",
            )
        # invite implementation
        # Step 1 - Get user id of the invited user
        invited_user = session.query(UserTable).filter(UserTable.login == username).first()
        new_relation = UserToProject(user_id=invited_user.user_id,project_id=project_id,access_type="participant")
        session.add(new_relation)
        session.commit()

# Run with: uvicorn app.main:app --reload