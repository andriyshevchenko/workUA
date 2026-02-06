# Supabase Database Integration

This guide explains how to use Supabase as the database backend instead of CSV files.

## Overview

The bot now supports two database backends:
- **CSV File** (default): Simple file-based storage, no setup required
- **Supabase** (optional): Cloud PostgreSQL database with better reliability and concurrent access

The bot automatically detects which backend to use based on environment variables.

## Why Supabase?

### Benefits
- ✅ **Cloud-based**: No local files, perfect for CI/CD
- ✅ **Reliable**: PostgreSQL database with ACID guarantees
- ✅ **Concurrent**: Multiple instances can run simultaneously
- ✅ **Scalable**: Handles large number of applications
- ✅ **Query-able**: Easy to analyze your application history
- ✅ **Backed up**: Automatic backups (on paid plans)
- ✅ **Free tier**: 500MB database, 2GB bandwidth/month

### When to Use
- Running bot from GitHub Actions
- Multiple bot instances simultaneously
- Need reliable data persistence
- Want to query/analyze application history

### When CSV is Fine
- Running locally occasionally
- Single instance only
- Simple setup preferred
- Don't want external dependencies

## Setup Instructions

### Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up (free)
2. Click "New Project"
3. Fill in:
   - **Name**: `workua-bot` (or any name)
   - **Database Password**: Generate a strong password (save it!)
   - **Region**: Choose closest to you
4. Wait 2-3 minutes for project creation

### Step 2: Create Database Table

1. In your Supabase project, go to **SQL Editor**
2. Copy the contents of `supabase_schema.sql` from this repository
3. Paste and click **Run** to create the table

Alternatively, use the Table Editor:
1. Go to **Table Editor** in Supabase dashboard
2. Click **New table**
3. Name: `applied_jobs`
4. Add columns:
   - `id` - int8, primary key, auto-increment ✅
   - `url` - text, unique ✅, not null ✅
   - `date_applied` - date, not null ✅
   - `title` - text
   - `company` - text
   - `created_at` - timestamptz, default: `now()`
   - `updated_at` - timestamptz, default: `now()`

### Step 3: Get API Credentials

1. In Supabase dashboard, go to **Settings** > **API**
2. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **service_role key**: `eyJxxx...` (required - bypasses RLS)

⚠️ **Important Note**: 
- The bot does **NOT** use Supabase Auth for user authentication
- You **MUST** use the **service_role key** (not anon key) because:
  - The bot needs direct database access without Supabase Auth login
  - Service role key bypasses Row Level Security (RLS)
  - Anon key with RLS policies will fail unless you configure public access (not recommended)
- The service_role key should be treated as a secret and only used server-side (GitHub Actions)

### Step 4: Configure Row Level Security (RLS)

Since the bot uses a service_role key (which bypasses RLS), you can keep RLS policies restrictive for other access methods:

**Recommended: Keep restrictive policies**
```sql
-- Enable RLS
ALTER TABLE applied_jobs ENABLE ROW LEVEL SECURITY;

-- Only allow authenticated users (won't affect service_role key)
CREATE POLICY "Allow authenticated users" ON applied_jobs
    FOR ALL USING (auth.role() = 'authenticated');
```

The service_role key bypasses all RLS policies, so these policies only affect other clients using anon/authenticated keys.

**Option A: For authenticated use (recommended)**
```sql
-- Enable RLS
ALTER TABLE applied_jobs ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users
CREATE POLICY "Allow all for authenticated" ON applied_jobs
    FOR ALL USING (auth.role() = 'authenticated');
```

**Option B: For anonymous/service role (GitHub Actions)**
```sql
-- Enable RLS
ALTER TABLE applied_jobs ENABLE ROW LEVEL SECURITY;

-- Allow all (use service_role key in env vars)
CREATE POLICY "Allow all operations" ON applied_jobs
    FOR ALL USING (true);
```

### Step 5: Set Environment Variables

**Local Development (.env file)**
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

**GitHub Actions (Repository Secrets)**
1. Go to repository **Settings** > **Secrets and variables** > **Actions**
2. Add secrets:
   - `SUPABASE_URL`: Your project URL
   - `SUPABASE_KEY`: Your **service role key** (not anon key)

**In workflow file:**
```yaml
env:
  SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
  SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```
1. Go to repository **Settings** > **Secrets and variables** > **Actions**
2. Add secrets:
   - `SUPABASE_URL`: Your project URL
   - `SUPABASE_KEY`: Your service role key

**In workflow file:**
```yaml
env:
  SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
  SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```

## Usage

### Automatic Detection

The bot automatically detects which database to use:

```python
# In your code, it just works!
from database import VacancyDatabase

# Auto-detects: Supabase if env vars set, otherwise CSV
db = VacancyDatabase.create()
```

**Detection Logic:**
1. If `SUPABASE_URL` and `SUPABASE_KEY` are set → Use Supabase
2. Otherwise → Use CSV file

### Explicit Selection

You can force a specific backend:

```python
# Force CSV
db = VacancyDatabase.create('csv')

# Force Supabase
db = VacancyDatabase.create('supabase')
```

### Testing Both Backends

```bash
# Test with CSV (default)
unset SUPABASE_URL SUPABASE_KEY
python3 bot.py

# Test with Supabase
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_KEY=eyJxxx...
python3 bot.py
```

## Database Schema

### Table: `applied_jobs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | bigint | PRIMARY KEY, AUTO | Unique record ID |
| url | text | UNIQUE, NOT NULL | Job URL (unique identifier) |
| date_applied | date | NOT NULL | Application date (YYYY-MM-DD) |
| title | text | | Job title |
| company | text | | Company name |
| created_at | timestamptz | DEFAULT NOW() | Record creation timestamp |
| updated_at | timestamptz | DEFAULT NOW() | Last update timestamp |

### Indexes
- `idx_applied_jobs_url` on `url` (for fast lookups)
- `idx_applied_jobs_date` on `date_applied` (for filtering)

### Example Data
```
id | url                              | date_applied | title             | company
---|----------------------------------|--------------|-------------------|----------
1  | https://work.ua/jobs/12345/      | 2024-01-15   | Python Developer  | Tech Corp
2  | https://work.ua/jobs/67890/      | 2024-01-20   | Backend Engineer  | StartupCo
```

## Querying Your Data

You can query your application history using Supabase SQL Editor:

```sql
-- Count total applications
SELECT COUNT(*) FROM applied_jobs;

-- Applications by month
SELECT 
    DATE_TRUNC('month', date_applied) as month,
    COUNT(*) as applications
FROM applied_jobs
GROUP BY month
ORDER BY month DESC;

-- Recent applications
SELECT * FROM applied_jobs 
ORDER BY date_applied DESC 
LIMIT 10;

-- Applications by company
SELECT company, COUNT(*) as count
FROM applied_jobs
WHERE company != ''
GROUP BY company
ORDER BY count DESC;

-- Find old applications you can reapply to
SELECT url, title, company, date_applied,
       AGE(NOW(), date_applied::timestamp) as time_passed
FROM applied_jobs
WHERE date_applied < NOW() - INTERVAL '2 months'
ORDER BY date_applied;
```

## Migration from CSV to Supabase

### Export CSV Data

```python
import csv
from datetime import datetime

# Read CSV
with open('applied_jobs.csv', 'r') as f:
    reader = csv.DictReader(f)
    jobs = list(reader)

print(f"Found {len(jobs)} applications")
```

### Import to Supabase

**Option 1: Using Supabase Dashboard**
1. Go to **Table Editor** > `applied_jobs`
2. Click **Insert** > **Insert row**
3. Manually add records (good for small datasets)

**Option 2: Using Python Script**
```python
from supabase import create_client
import csv
import os

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Read CSV
with open('applied_jobs.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        data = {
            'url': row['url'],
            'date_applied': row['date_applied'],
            'title': row['title'],
            'company': row['company']
        }
        try:
            supabase.table('applied_jobs').insert(data).execute()
            print(f"✓ Imported: {row['title']}")
        except Exception as e:
            print(f"✗ Failed: {row['url']} - {e}")
```

**Option 3: Using SQL Import**
```sql
-- In Supabase SQL Editor, insert all at once
INSERT INTO applied_jobs (url, date_applied, title, company) VALUES
  ('https://work.ua/jobs/1/', '2024-01-01', 'Job 1', 'Company 1'),
  ('https://work.ua/jobs/2/', '2024-01-02', 'Job 2', 'Company 2');
```

## Troubleshooting

### Connection Errors

**Error**: `Failed to initialize Supabase client`

**Solutions**:
1. Check `SUPABASE_URL` format: `https://xxxxx.supabase.co`
2. Verify `SUPABASE_KEY` is correct (no spaces/newlines)
3. Check project is not paused (Supabase free tier pauses after 7 days inactivity)
4. Test connection: `curl $SUPABASE_URL/rest/v1/`

### Permission Errors

**Error**: `permission denied for table applied_jobs`

**Solutions**:
1. Check RLS policies are configured correctly
2. Use **service_role key** instead of anon key
3. Verify the table exists: `SELECT * FROM applied_jobs LIMIT 1;`

### Missing supabase Library

**Error**: `No module named 'supabase'`

**Solution**:
```bash
pip install supabase
# Or
pip install -r requirements.txt
```

### Unique Constraint Violation

**Error**: `duplicate key value violates unique constraint`

**Solution**: This is expected when trying to re-add existing application
- The bot handles this by checking first with `get_application()`
- If you see this error, it means you're trying to insert duplicate URL

### Bot Not Using Supabase

**Problem**: Bot still uses CSV even though env vars are set

**Check**:
```python
from config import config
print(f"SUPABASE_URL: {config.SUPABASE_URL}")
print(f"SUPABASE_KEY: {config.SUPABASE_KEY and 'SET' or 'NOT SET'}")
```

**Solutions**:
1. Make sure env vars are in `.env` file or exported
2. Restart bot after setting env vars
3. Check `.env` file is in the same directory
4. Try: `python-dotenv` reads `.env` automatically

## Performance Considerations

### CSV Advantages
- Faster for small datasets (< 1000 records)
- No network latency
- Works offline
- No external dependencies

### Supabase Advantages
- Scales better with large datasets (> 1000 records)
- Concurrent access from multiple instances
- Automatic backups
- Can query and analyze data easily
- Works in cloud/CI/CD environments

### Best Practices
1. Use indexes on frequently queried columns (already created in schema)
2. Use batch operations for bulk inserts (future improvement)
3. Connection pooling is handled by Supabase SDK
4. Monitor your Supabase usage in dashboard

## Security Best Practices

1. ✅ **Use secrets for credentials**: Never commit SUPABASE_KEY
2. ✅ **Enable RLS**: Protect your data with Row Level Security
3. ✅ **Use service_role key carefully**: Only for trusted environments
4. ✅ **Rotate keys regularly**: Generate new keys in Supabase settings
5. ✅ **Monitor access**: Check Supabase logs for unusual activity
6. ✅ **Limit API access**: Use RLS policies to restrict operations
7. ✅ **Backup data**: Export your data regularly (SQL dump)

## Cost Considerations

### Supabase Free Tier
- 500 MB database storage
- 2 GB bandwidth per month
- 50,000 monthly active users
- 500 MB file storage
- Pauses after 7 days inactivity

### Typical Usage (WorkUA Bot)
- **Storage**: ~1 KB per application = 500,000 applications in free tier
- **Bandwidth**: ~2 KB per operation = 1,000,000 operations/month
- **Conclusion**: Free tier is more than enough!

### Going Over Limits
If you exceed free tier limits:
1. Upgrade to Pro ($25/month) - 8 GB database, 50 GB bandwidth
2. Clean old data: `DELETE FROM applied_jobs WHERE date_applied < NOW() - INTERVAL '1 year'`
3. Export and archive old data

## Support

### Supabase Support
- [Documentation](https://supabase.com/docs)
- [Discord Community](https://discord.supabase.com/)
- [GitHub Issues](https://github.com/supabase/supabase/issues)

### Bot Support
- Check `test_database.py` for usage examples
- See `database.py` for implementation details
- Open an issue in this repository

## Next Steps

1. ✅ Create Supabase project
2. ✅ Run SQL schema
3. ✅ Get API credentials
4. ✅ Set environment variables
5. ✅ Test connection
6. ✅ Migrate existing CSV data (optional)
7. ✅ Run bot with Supabase
8. ✅ Monitor dashboard for usage

Enjoy reliable, cloud-based job application tracking! 🚀
