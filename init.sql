-- =============================================================================
-- CityEstate PostgreSQL Initialization
# ====================================
-- Run on first container startup
-- =============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance
-- (These will be created by SQLAlchemy/Alembic, but we add useful ones here)

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE cityestate TO cityestate;
GRANT ALL PRIVILEGES ON SCHEMA public TO cityestate;

-- Set default search path
ALTER DATABASE cityestate SET search_path TO public, cityestate;
