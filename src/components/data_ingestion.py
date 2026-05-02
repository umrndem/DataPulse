import os
import sys
from typing import List

import pandas as pd

# Add the project root to the python path so we can import src.utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.config import get_config
from src.utils import get_db_connection

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names for PostgreSQL compatibility.

    Args:
        df: Raw dataframe with original column names.

    Returns:
        Dataframe with normalized column names.
    """
    df.columns = [c.lower().replace(' ', '_').replace('-', '_').replace('.', '_') for c in df.columns]
    return df

def ingest_data() -> None:
    """Read CSV files from data/raw and upload them to Supabase.

    Returns:
        None.
    """
    # 1. Connect to Database
    engine = get_db_connection()
    if not engine:
        print("Failed to connect to database. Exiting.")
        return

    resolved_config = get_config()

    # 2. Define the path to raw data
    raw_data_path = os.path.join("data", "raw")
    
    # 3. List all CSV files
    try:
        files: List[str] = [f for f in os.listdir(raw_data_path) if f.endswith('.csv')]
        print(f"Found {len(files)} CSV files to process.")
    except FileNotFoundError:
        print(f"Error: The folder '{raw_data_path}' does not exist.")
        return

    # 4. Loop through files and upload
    for file_name in files:
        table_name = resolved_config.resolve_source_table_name(file_name)
        file_path = os.path.join(raw_data_path, file_name)
        
        print(f"Processing {file_name} -> Table: {table_name}...")
        
        try:
            # Read CSV
            df = pd.read_csv(file_path)
            
            # Clean header
            df = clean_column_names(df)
            
            # Upload to SQL (if_exists='replace' overwrites old data)
            # chunksize=1000 sends data in batches to prevent timeouts
            df.to_sql(name=table_name, con=engine, if_exists='replace', index=False, chunksize=1000)
            
            print(f"Successfully uploaded {len(df)} rows to '{table_name}'")
            
        except Exception as e:
            print(f"Failed to upload {file_name}: {e}")

    print("\nAll Data Ingestion Complete!")

if __name__ == "__main__":
    ingest_data()