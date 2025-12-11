#!/usr/bin/env python3
"""
Migration script to add use_historical_data column to settings table
"""
import sys
from pathlib import Path
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Get database URL
import os
from database.settings_db import DATABASE_URL, engine

def migrate():
    """Add use_historical_data column if it doesn't exist"""
    print("Starting migration: Adding use_historical_data column...")
    
    # For SQLite, use direct connection
    if 'sqlite' in DATABASE_URL:
        db_path = DATABASE_URL.replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if column exists
            cursor.execute("PRAGMA table_info(settings)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'use_historical_data' not in columns:
                print("  Adding use_historical_data column...")
                cursor.execute("ALTER TABLE settings ADD COLUMN use_historical_data BOOLEAN DEFAULT 0")
                conn.commit()
                print("  ✅ Column added successfully")
            else:
                print("  ✅ Column already exists")
            
            # Set default value for existing rows
            cursor.execute("UPDATE settings SET use_historical_data = 0 WHERE use_historical_data IS NULL")
            conn.commit()
            print("  ✅ Default values set")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        # For other databases, use SQLAlchemy
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                # Check if column exists (PostgreSQL/MySQL)
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'settings' AND column_name = 'use_historical_data'
                """))
                if result.fetchone() is None:
                    print("  Adding use_historical_data column...")
                    conn.execute(text("ALTER TABLE settings ADD COLUMN use_historical_data BOOLEAN DEFAULT FALSE"))
                    conn.commit()
                    print("  ✅ Column added successfully")
                else:
                    print("  ✅ Column already exists")
                
                # Set default value
                conn.execute(text("UPDATE settings SET use_historical_data = FALSE WHERE use_historical_data IS NULL"))
                conn.commit()
                print("  ✅ Default values set")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                raise
    
    print("✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate()

