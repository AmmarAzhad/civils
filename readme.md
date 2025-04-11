# Workflow Execution Service

## Overview

This project provides a service for defining, managing, and executing workflows composed of individual tasks. It offers:

* A **FastAPI (HTTP)** interface for CRUD operations on Workflows and Tasks.
* A **gRPC** interface for triggering workflow executions and receiving real-time status updates.
* Persistence using **PostgreSQL** managed via **SQLAlchemy** and **Alembic**.
* Caching for frequently accessed data using **Redis**.
* A containerized setup using **Docker** and **Docker Compose** for easy development and deployment.

## Features

* Define Workflows with multiple Tasks.
* Specify task execution order (`sequence`) and concurrency (`execution_type` as `sync` or `async` flag).
* RESTful API (FastAPI) for managing workflow/task definitions.
* gRPC API for triggering workflow runs and streaming execution status (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).
* Database persistence for workflows, tasks, and execution history.
* Redis caching for workflow definitions to improve read performance.
* Cache invalidation logic when workflows or tasks are modified.
* Fully containerized environment using Docker Compose.
* Database schema management using Alembic migrations.

## Architecture Overview

The system consists of four main containerized services orchestrated by Docker Compose:

1.  **FastAPI Application (`fastapi_app`):** Exposes a RESTful HTTP API (typically on port 8000) for managing workflow and task definitions (CRUD operations). It interacts with the PostgreSQL database for storage and Redis for caching read operations.
2.  **gRPC Server (`grpc_server`):** Exposes a gRPC API (typically on port 50051) specifically for triggering workflow executions and streaming status updates back to the client. It reads workflow/task definitions from PostgreSQL and updates execution status.
3.  **PostgreSQL Database (`db`):** The primary relational database storing workflow definitions, tasks, and execution history. Uses the official PostgreSQL Docker image.
4.  **Redis Server (`redis`):** An in-memory data store used for caching frequently accessed workflow data to reduce database load and improve API response times. Uses the official Redis Docker image.

All services communicate over a shared Docker network (`app_network`).

## Technology Stack

* **Backend Frameworks:** FastAPI, gRPC (`grpcio`)
* **Programming Language:** Python (3.11+)
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy (async with `asyncpg`)
* **Database Migrations:** Alembic
* **Caching:** Redis (`redis-py` async)
* **Data Validation/Serialization:** Pydantic (including `pydantic-settings`)
* **API Server (FastAPI):** Uvicorn
* **Containerization:** Docker, Docker Compose
* **Testing:** Pytest, `pytest-asyncio`, HTTPX (via `TestClient` or `AsyncClient`)

## Project Structure

├── alembic/                   
│   ├── versions/              
│   └── env.py               
├── app/                       
│   ├── core/                                   
│   ├── db/                    
│   ├── grpc/                 
│   │   ├── protos/            
│   │   ├── generated/         
│   │   └── server.py         
│   ├── models/               
│   ├── schemas/     
│   ├── services/         
│   ├── routes/                
│   └── main.py               
├── tests/                     
│   ├── conftest.py            
│   └── routes/    
│   └── services/            
├── .dockerignore              
├── .env.example              
├── .gitignore                 
├── alembic.ini                
├── docker-compose.yml        
├── Dockerfile.fastapi         
├── Dockerfile.grpc            
├── README.md                  
├── requirements.txt           
└── run_grpc_server.py         

## Setup and Running (Docker Compose)

This is the recommended way to run the entire application stack locally for development.

### Prerequisites

* Git
* Docker Engine
* Docker Compose (usually included with Docker Desktop)

### Steps

1.  **Configure Environment:**
    * Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    * Edit the `.env` file and set your desired `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.

2.  **Build and Run Services:**
    * From the project root directory, run:
        ```bash
        docker-compose up --build -d
        ```
    * `--build`: Builds the images for `fastapi_app` and `grpc_server` if they don't exist or if the Dockerfile/code has changed.
    * Wait for the database and redis healthchecks to pass. You can view logs using `docker-compose logs -f`.

3.  **Access Services:**
    * **FastAPI HTTP API:** `http://localhost:8000` (or your configured `FASTAPI_PORT`).
    * **FastAPI Docs:** `http://localhost:8000/docs` (Swagger UI) or `/redoc`.
    * **gRPC API:** `localhost:50051` (or your configured `GRPC_PORT`). Use a gRPC client like Postman, grpcurl, BloomRPC, or a custom client with the `workflow.proto` definition.
    * **PostgreSQL (Optional Direct Access):** `localhost:5432` (or `POSTGRES_PORT`) using the credentials from `.env`.
    * **Redis (Optional Direct Access):** `localhost:6379` (or `REDIS_PORT`).

4.  **Stopping Services:**
    * To stop the running services:
        ```bash
        docker-compose down
        ```
    * To stop and remove the data volumes (deleting all PostgreSQL and Redis data):
        ```bash
        docker-compose down -v
        ```

## API Usage

* **FastAPI:** Interact with the REST API documented via Swagger UI at `http://localhost:8000/docs`. Use standard HTTP methods (GET, POST, PUT, DELETE) for managing Workflows and Tasks.
* **gRPC:**
    * Use a gRPC client.
    * Load the `app/grpc/protos/workflow.proto` definition.
    * Connect to `localhost:50051`.
    * Call `WorkflowService.ExecuteWorkflow` with a `workflow_id` to start execution and receive status streams.
    * Call `WorkflowService.GetWorkflowStatus` with an `execution_id` to get the final status of a run.

## Testing

* Tests are written using `pytest`.
* Ensure you have a separate test database configured. Set the `TEST_DATABASE_URL` environment variable before running tests:
    ```bash
    export TEST_DATABASE_URL="postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"
    # Make sure the test DB exists and the user has permissions (GRANT ... in psql)
    ```
* Run tests from the project root directory:
    ```bash
    pytest -v
    ```
* Tests use fixtures defined in `tests/conftest.py` to set up a test database (creating/dropping tables per session), provide isolated database sessions per test (via transaction rollback), and configure a test client (`httpx.AsyncClient`) to interact with the application endpoints.

## Key Architectural Decisions

* **Separate FastAPI & gRPC Interfaces:** Using FastAPI for synchronous-style CRUD/management APIs leverages its excellent developer experience, tooling, and auto-documentation. Using gRPC for the performance-sensitive workflow execution task leverages its efficiency and built-in support for streaming, which is ideal for progress updates.
* **Asynchronous Python:** Using `asyncio` with FastAPI, SQLAlchemy (`asyncpg`), Redis (`redis-py` async), and gRPC (`grpc.aio`) allows for high concurrency and efficient handling of I/O-bound operations (database access, network calls).
* **SQLAlchemy ORM & PostgreSQL:** Provides a robust, relational data store with the benefits of an ORM for database interaction, reducing boilerplate SQL. PostgreSQL offers features like native ENUMs and JSON support.
* **Alembic Migrations:** Ensures safe, repeatable, and version-controlled database schema management, essential for evolving the application over time. Avoids the limitations of `create_all`.
* **Redis Caching (Cache-Aside):** Improves read performance for frequently accessed, relatively static data (like workflow definitions) by reducing direct database hits. Includes explicit cache invalidation logic triggered by relevant data modifications. TTL provides a fallback.
* **Pydantic for Validation & Serialization:** Enforces data consistency at API boundaries (both request validation and response serialization) and within the application (e.g., settings management). Provides type safety. Schemas are kept separate from DB models (`app/schemas/` vs `app/models/`) to decouple the API contract from the internal storage representation.
* **Layered Directory Structure:** Organizes code by feature/responsibility (core, db, models, schemas, crud/repositories, routes, grpc, tests) promoting modularity and maintainability.
* **Docker Compose for Development:** Provides a consistent, isolated, and easy-to-start development environment encompassing all service dependencies. Simplifies setup for new developers.
* **Environment Variables for Configuration:** Externalizes configuration (database URLs, secrets, ports) using `.env` files and environment variables, following 12-factor app principles.

## Future Improvements / TODOs

* Add Authentication/Authorization (e.g., JWT/OAuth2 for FastAPI, gRPC Interceptors).
* Implement more sophisticated task execution logic within `execute_task_logic`.
* Add more robust error handling and reporting.
* Implement distributed tracing across services.
* Consider a more advanced task queue (e.g., Celery with Redis/RabbitMQ) if tasks become very long-running or require complex retry logic.
* Add more comprehensive tests, including integration tests.
* Develop Kubernetes deployment manifests.
