-- Supabase SQL script to create the applied_jobs table
-- Run this in your Supabase SQL Editor

-- Create applied_jobs table
CREATE TABLE IF NOT EXISTS applied_jobs (
    id BIGSERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    date_applied DATE NOT NULL,
    title TEXT DEFAULT '',
    company TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on url for faster lookups
CREATE INDEX IF NOT EXISTS idx_applied_jobs_url ON applied_jobs(url);

-- Create index on date_applied for filtering
CREATE INDEX IF NOT EXISTS idx_applied_jobs_date ON applied_jobs(date_applied);

-- Enable Row Level Security (RLS)
ALTER TABLE applied_jobs ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations for authenticated users
-- Adjust this policy based on your security requirements
CREATE POLICY "Allow all for authenticated users" ON applied_jobs
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- For automation (e.g., GitHub Actions), prefer using a `service_role` key on the server side.
-- The `service_role` key bypasses RLS, so keep RLS policies restrictive and avoid broad anon access.
-- Do NOT enable anon access policies - use service_role key instead for CI/CD.

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to call the function
DROP TRIGGER IF EXISTS update_applied_jobs_updated_at ON applied_jobs;
CREATE TRIGGER update_applied_jobs_updated_at
    BEFORE UPDATE ON applied_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (if needed)
-- GRANT ALL ON applied_jobs TO authenticated;
-- GRANT ALL ON applied_jobs TO anon;

COMMENT ON TABLE applied_jobs IS 'Stores job applications history to avoid duplicate applications';
COMMENT ON COLUMN applied_jobs.url IS 'Unique job URL from work.ua';
COMMENT ON COLUMN applied_jobs.date_applied IS 'Date when the application was submitted';
COMMENT ON COLUMN applied_jobs.title IS 'Job title';
COMMENT ON COLUMN applied_jobs.company IS 'Company name';
