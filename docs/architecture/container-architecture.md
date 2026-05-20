# Container Architecture

## Purpose

This document describes the local container architecture used for POC development.

## POC Scope

The POC runs entirely on Docker Compose for local development. No cloud deployment, no Kubernetes, no production container registry.

## Services

| Service | Image | Purpose |
|---|---|---|
| `postgres` | `postgres:16` | Primary database — source of truth |
| `redis` | `redis:7` | Celery broker and cache |
| `api` | Custom (FastAPI) | Backend API server |
| `worker` | Custom (Celery) | Background job worker |

## Docker Compose Overview

All services are defined in `docker-compose.yml` at the root of the repository.

Environment variables are loaded from `.env` (created from `.env.example`).

## Service Responsibilities

### postgres

- Hosts all POC tables
- Seeded by a seed script during development
- Exposed on `localhost:5432` for local tooling

### redis

- Acts as the Celery broker
- Used for short-lived task state
- Not used for durable storage
- Exposed on `localhost:6379`

### api

- Runs the FastAPI application
- Hot-reloads in development
- Exposed on `localhost:8000`

### worker

- Runs the Celery worker
- Processes background queues
- Connects to Redis (broker) and PostgreSQL (state)

## Networking

All services share a single Docker Compose network (`eventsales-net`) for local development.

## Frontend

The frontend (React/Next.js) runs separately outside Docker Compose during POC development using `npm run dev`.

## POC Limitations

- No production Docker images
- No image scanning or hardening
- No secrets management beyond `.env.example`
- No CI/CD pipeline during POC
