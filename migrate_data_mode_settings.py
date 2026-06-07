#!/usr/bin/env python3
"""
Migration script to add data mode settings columns to Settings table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database.settings_db import engine, db_session
from utils.logging import get_logger

logger = get_logger(__name__)

def migrate_data_mode_settings():
    """Add data mode settings columns if they don't exist"""
    try:
        with engine.connect() as conn:
            # Check if columns exist
            result = conn.execute(text("PRAGMA table_info(settings)"))
            columns = [row[1] for row in result]
            
            # Add data_mode column if missing
            if 'data_mode' not in columns:
                logger.info("Adding data_mode column...")
                conn.execute(text("ALTER TABLE settings ADD COLUMN data_mode VARCHAR(20) DEFAULT 'live'"))
                conn.commit()
                logger.info("Added data_mode column")
            
            # Add historical_duration column if missing
            if 'historical_duration' not in columns:
                logger.info("Adding historical_duration column...")
                conn.execute(text("ALTER TABLE settings ADD COLUMN historical_duration VARCHAR(50)"))
                conn.commit()
                logger.info("Added historical_duration column")
            
            # Add historical_data_source column if missing
            if 'historical_data_source' not in columns:
                logger.info("Adding historical_data_source column...")
                conn.execute(text("ALTER TABLE settings ADD COLUMN historical_data_source VARCHAR(20) DEFAULT 'yfinance'"))
                conn.commit()
                logger.info("Added historical_data_source column")
            
            # Update existing rows to have defaults
            conn.execute(text("UPDATE settings SET data_mode = 'live' WHERE data_mode IS NULL"))
            conn.execute(text("UPDATE settings SET historical_data_source = 'yfinance' WHERE historical_data_source IS NULL"))
            conn.commit()
            
            logger.info("Migration completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n" + "="*60)
    print("DATA MODE SETTINGS MIGRATION")
    print("="*60)
    
    success = migrate_data_mode_settings()
    
    if success:
        print("\n[OK] Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n[ERROR] Migration failed!")
        sys.exit(1)






