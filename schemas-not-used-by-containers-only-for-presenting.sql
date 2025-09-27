CREATE TABLE user_table (
    user_id SERIAL PRIMARY KEY,
    login varchar(50) UNIQUE NOT NULL,
    password_hash varchar NOT NULL
);

CREATE TABLE project (
    project_id SERIAL PRIMARY KEY,
    name varchar(100) UNIQUE NOT NULL,
    description varchar(500)
);

CREATE TABLE document (
    document_id SERIAL PRIMARY KEY,
    s3_key varchar UNIQUE NOT NULL,
    name varchar(150) NOT NULL
);

CREATE TABLE user2project (
    user_id integer NOT NULL,
    project_id integer NOT NULL,
    access_type varchar(12) NOT NULL,
    PRIMARY KEY(user_id, project_id)
);

CREATE TABLE project2document (
    project_id integer NOT NULL,
    document_id integer NOT NULL,
    PRIMARY KEY(project_id, document_id)
);