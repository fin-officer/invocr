#!/usr/bin/env python3
"""
Database migration script for InvOCR
Handles database schema updates and data migrations
"""

import os
import sys
from pathlib import Path
import asyncio
import asyncpg
from datetime import datetime


class DatabaseMigrator:
    """Database migration manager"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent.parent / "migrations"

    async def get_connection(self):
        """Get database connection"""
        return await asyncpg.connect(self.database_url)

    async def create_migrations_table(self, conn):
        """Create migrations tracking table"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)

    async def get_applied_migrations(self, conn):
        """Get list of applied migrations"""
        rows = await conn.fetch(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
        return [row['version'] for row in rows]

    async def apply_migration(self, conn, migration_file: Path):
        """Apply a single migration"""
        version = migration_file.stem
        name = migration_file.name

        print(f"📝 Applying migration: {name}")

        # Read migration SQL
        sql = migration_file.read_text(encoding='utf-8')

        # Execute migration in transaction
        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations (version, name) VALUES ($1, $2)",
                version, name
            )

        print(f"✅ Applied migration: {name}")

    async def run_migrations(self):
        """Run all pending migrations"""
        conn = await self.get_connection()

        try:
            # Create migrations table
            await self.create_migrations_table(conn)

            # Get applied migrations
            applied = await self.get_applied_migrations(conn)

            # Find migration files
            if not self.migrations_dir.exists():
                print("📁 No migrations directory found")
                return

            migration_files = sorted(self.migrations_dir.glob("*.sql"))

            if not migration_files:
                print("📄 No migration files found")
                return

            # Apply pending migrations
            pending = [
                f for f in migration_files
                if f.stem not in applied
            ]

            if not pending:
                print("✅ All migrations are already applied")
                return

            print(f"🔄 Found {len(pending)} pending migrations")

            for migration_file in pending:
                await self.apply_migration(conn, migration_file)

            print(f"🎉 Successfully applied {len(pending)} migrations")

        finally:
            await conn.close()


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="InvOCR Database Migrator")
    parser.add_argument("--database-url",
                        default=os.environ.get("DATABASE_URL"),
                        help="Database URL")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show pending migrations without applying")

    args = parser.parse_args()

    if not args.database_url:
        print("❌ Database URL is required")
        print("Set DATABASE_URL environment variable or use --database-url")
        sys.exit(1)

    migrator = DatabaseMigrator(args.database_url)

    try:
        if args.dry_run:
            print("🔍 Dry run mode - showing pending migrations")
            # TODO: Implement dry run logic
        else:
            await migrator.run_migrations()

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


