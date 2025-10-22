# Database Migrations

This directory contains SQL migration files that set up and modify the database schema.

## Migration Files

- `001_init.sql` - Base schema: bills, votes, legislators, sponsors, actions, texts, rollcall votes
- `002_analysis_tables.sql` - Advanced analysis tables: embeddings, sentiment, NLP, bias detection

## Running Migrations

Migrations are automatically applied when using the `--postprocess` flag:

```bash
python cbw_main.py --db "postgresql://user:pass@localhost:5432/congress" --postprocess
```

Or using the DatabaseManager:

```python
from cbw_db_adapter import DatabaseManager

db_manager = DatabaseManager(config_path="config/database.yaml")
adapter = db_manager.get_adapter("postgresql")
adapter.connect()

# Run migration SQL here
```

## Creating New Migrations

1. Create a new `.sql` file with sequential numbering: `003_your_feature.sql`
2. Wrap your SQL in a transaction:
   ```sql
   BEGIN;
   
   -- Your schema changes
   CREATE TABLE IF NOT EXISTS new_table (
     id SERIAL PRIMARY KEY,
     name TEXT NOT NULL
   );
   
   COMMIT;
   ```
3. Test the migration on a development database first

## Database-Specific Migrations

Some SQL syntax varies between database systems. Here are common differences:

### Auto-Incrementing Primary Keys

**PostgreSQL:**
```sql
CREATE TABLE example (
  id SERIAL PRIMARY KEY,
  name TEXT
);
```

**MySQL:**
```sql
CREATE TABLE example (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name TEXT
);
```

**SQLite:**
```sql
CREATE TABLE example (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT
);
```

### Timestamps

**PostgreSQL:**
```sql
inserted_at TIMESTAMP DEFAULT now()
```

**MySQL:**
```sql
inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

**SQLite:**
```sql
inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### JSON Support

**PostgreSQL:**
```sql
metadata JSONB
```

**MySQL (8.0+):**
```sql
metadata JSON
```

**SQLite (3.9+):**
```sql
metadata TEXT  -- Store JSON as text
```

## Migration Best Practices

1. **Always use transactions** - Wrap migrations in BEGIN/COMMIT
2. **Use IF NOT EXISTS** - Make migrations idempotent
3. **Test first** - Run on dev/staging before production
4. **Backup before migrating** - Always have a backup
5. **Document changes** - Add comments explaining complex migrations
6. **Version control** - Keep all migrations in git
7. **Never modify old migrations** - Create new ones instead
8. **Handle rollbacks** - Document how to reverse changes

## Troubleshooting

### Migration Fails to Apply

1. Check database logs for detailed error
2. Verify user has DDL permissions
3. Check for syntax errors specific to your database
4. Test migration manually:
   ```bash
   psql -U congress -d congress -f 001_init.sql
   ```

### Schema Already Exists

- Migrations use `IF NOT EXISTS` to be idempotent
- If migration still fails, check if a partial migration occurred
- May need to manually clean up and re-run

### Permission Denied

Grant appropriate permissions:

**PostgreSQL:**
```sql
GRANT ALL PRIVILEGES ON DATABASE congress TO congress;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO congress;
```

**MySQL:**
```sql
GRANT ALL PRIVILEGES ON congress.* TO 'congress'@'localhost';
FLUSH PRIVILEGES;
```
