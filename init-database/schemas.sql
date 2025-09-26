CREATE TABLE USER (
    user_id PRIMARY KEY SERIAL,
    login varchar(50) UNIQUE NOT NULL,
    password_hash varchar NOT NULL
)

CREATE TABLE PROJECT (
    project_id PRIMARY KEY SERIAL,
    name varchar(100) UNIQUE NOT NULL,
    description varchar(500)
)

CREATE TABLE DOCUMENT (
    document_id PRIMARY KEY SERIAL,
    s3_key varchar UNIQUE NOT NULL,
    name varchar(150) NOT NULL
)

CREATE TABLE USER2PROJECT(
    user_id integer NOT NULL,
    project_id integer NOT NULL,
    access_type varchar(12) NOT NULL,
    PRIMARY KEY(user_id, project_id)
)

CREATE TABLE PROJECT2DOCUMENT(
    project_id integer NOT NULL,
    document_id integer NOT NULL,
    PRIMARY KEY(project_id, document_id)
)