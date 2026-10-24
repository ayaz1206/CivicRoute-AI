-- Enable the pgvector extension on first database initialization.
-- The pgvector/pgvector image ships the extension; this makes it available
-- in the civicroute database before any migrations run.
CREATE EXTENSION IF NOT EXISTS vector;
