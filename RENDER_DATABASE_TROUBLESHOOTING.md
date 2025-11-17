# Render Database Connection Troubleshooting

## Error: OSError: [Errno 101] Network is unreachable

This error means your Render server cannot connect to the database. Here's how to fix it:

## 1. Verify DATABASE_URL on Render

### Check Environment Variable
1. Go to your Render dashboard
2. Navigate to your web service
3. Go to **Environment** tab
4. Verify `DATABASE_URL` is set correctly

### Correct Format
Your `DATABASE_URL` should look like:
```
postgresql+asyncpg://user:password@host:port/database
```

**Common Issues:**
- ❌ Missing `+asyncpg` driver: `postgresql://...` 
- ✅ Correct format: `postgresql+asyncpg://...`
- ❌ Wrong host (using `localhost` or `127.0.0.1`)
- ✅ Use the actual database host provided by your database service

## 2. Database Provider Specific Instructions

### If Using Supabase:

1. **Get Connection String:**
   - Go to Supabase Dashboard → Project Settings → Database
   - Find "Connection string" section
   - Use the "Connection Pooling" string (recommended for serverless)
   - Copy the **URI** format (not psql command)

2. **Connection Pooling String Format:**
   ```
   postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

3. **Convert to Async Format:**
   ```
   postgresql+asyncpg://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

4. **Enable Connection Pooling:**
   - In Supabase: Settings → Database → Connection Pooling
   - Enable "Session mode" or "Transaction mode"

### If Using Render PostgreSQL:

1. **Internal Connection:**
   - Use the **Internal Database URL** provided by Render
   - Found in: Dashboard → Database → Info → Internal Database URL

2. **Format:**
   ```
   postgresql+asyncpg://user:password@hostname.internal:5432/database
   ```

### If Using External Database (AWS RDS, etc.):

1. **Whitelist Render IPs:**
   - Render uses dynamic IPs, so you may need to:
   - Allow all IPs: `0.0.0.0/0` (less secure)
   - OR use Render's static IP addon

2. **Security Group Configuration:**
   - Open port **5432** (PostgreSQL) or **6543** (Supabase pooler)
   - Allow inbound traffic from your Render service

## 3. Test Connection from Render

### Add a Test Endpoint (Already Added)

The `/health` endpoint now tests database connectivity. After deployment:

```bash
curl https://your-app.onrender.com/api/health
```

Expected response when working:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-17T15:44:10Z",
  "database": "connected"
}
```

Expected response when database is unreachable:
```json
{
  "status": "unhealthy",
  "timestamp": "2025-11-17T15:44:10Z",
  "database": "disconnected",
  "error": "Network is unreachable"
}
```

## 4. Verify Network Connectivity (SSH into Render)

If you have Render Shell access:

```bash
# Test DNS resolution
nslookup your-database-host.com

# Test connectivity
nc -zv your-database-host.com 5432

# Test with psql (if available)
psql "$DATABASE_URL"
```

## 5. Common Solutions Checklist

- [ ] Verify `DATABASE_URL` environment variable is set on Render
- [ ] Confirm URL uses `postgresql+asyncpg://` protocol
- [ ] Check database host is accessible from internet (not localhost)
- [ ] Verify database firewall/security group allows Render's IPs
- [ ] Confirm database port is correct (5432 for direct, 6543 for Supabase pooler)
- [ ] Test with Supabase connection pooler instead of direct connection
- [ ] Check database service is running and not paused
- [ ] Verify credentials (username/password) are correct
- [ ] Try pinging `/api/health` endpoint to see detailed error

## 6. Code Improvements Made

### Better Connection Pool Configuration
- Added connection timeouts (10s connection, 60s command timeout)
- Set pool size limits (5 base, 10 overflow)
- Added connection recycling (1 hour)
- Moved `search_path` to connection level (more efficient)

### Error Logging
- Added detailed error logging in `get_db()`
- Health endpoint now shows database status

## 7. Next Steps

1. **Deploy the changes:**
   ```bash
   git add .
   git commit -m "Fix database connection handling and add health checks"
   git push
   ```

2. **Check Render logs** after deployment:
   - Look for connection attempts
   - Verify the database host being used

3. **Test health endpoint:**
   ```bash
   curl https://your-app.onrender.com/api/health
   ```

4. **If still failing:**
   - Share the health endpoint response
   - Check Render environment variables
   - Verify database provider settings

## 8. Quick Fix Commands

### Update DATABASE_URL on Render (via CLI):
```bash
render env:set DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"
```

### Test locally first:
```bash
# In your local terminal
$env:DATABASE_URL="your-database-url"
python -c "import asyncio; from app.db.session import engine; asyncio.run(engine.connect())"
```

## Need More Help?

Provide these details:
1. Database provider (Supabase, Render PostgreSQL, AWS RDS, etc.)
2. Output from `/api/health` endpoint
3. Render logs showing the connection attempt
4. Database host format (redact password): `postgresql+asyncpg://user:***@HOST:PORT/db`
