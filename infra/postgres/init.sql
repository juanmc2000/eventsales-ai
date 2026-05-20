-- EventSales AI — PostgreSQL Initialisation Script
-- This script runs once when the PostgreSQL container is first created.
-- It sets up the POC database with the eventsales schema.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for password hashing utilities (optional)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Schema ownership comment
COMMENT ON DATABASE eventsales IS 'EventSales AI POC database. Source of truth for all persistent data.';
