# db_manager.py
import sqlite3
import json
import uuid
import config


def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(config.DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # Allow accessing columns by name
    return conn


def create_tables():
    """Creates the necessary tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            uuid TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            gender TEXT,
            age INTEGER,
            party_id TEXT,
            initial_budget REAL,
            current_budget REAL,
            attributes TEXT, -- Store as JSON
            traits TEXT, -- Store as JSON
            stats TEXT -- Store as JSON (e.g., wins, losses, total_votes)
        )
    ''')
    conn.commit()
    conn.close()


def save_candidate(candidate_data):
    """
    Saves or updates a candidate's data in the database.
    Expects a dictionary with candidate information, including 'uuid'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO candidates (
            uuid, name, gender, age, party_id, initial_budget, current_budget, attributes, traits, stats
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(candidate_data.get('uuid', uuid.uuid4())
            ),  # Ensure UUID is string, generate if missing
        candidate_data.get('name'),
        candidate_data.get('gender'),
        candidate_data.get('age'),
        candidate_data.get('party_id'),
        # Use initial budget if provided
        candidate_data.get('initial_budget', config.INITIAL_CAMPAIGN_BUDGET),
        candidate_data.get('current_budget', candidate_data.get(
            'initial_budget', config.INITIAL_CAMPAIGN_BUDGET)),  # Initialize current_budget
        json.dumps(candidate_data.get('attributes', {})),
        json.dumps(candidate_data.get('traits', [])),
        json.dumps(candidate_data.get('stats', {}))
    ))
    conn.commit()
    conn.close()


def get_candidate_by_name(name):
    """Retrieves a candidate's data from the database by name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates WHERE name = ?', (name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        candidate_data = dict(row)
        candidate_data['attributes'] = json.loads(
            candidate_data.get('attributes', '{}'))
        candidate_data['traits'] = json.loads(
            candidate_data.get('traits', '[]'))
        candidate_data['stats'] = json.loads(candidate_data.get('stats', '{}'))
        # Ensure UUID is a UUID object, not just string, if needed elsewhere (optional)
        # candidate_data['uuid'] = uuid.UUID(candidate_data['uuid'])
        return candidate_data
    return None


def candidate_exists(name):
    """Checks if a candidate with the given name exists in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM candidates WHERE name = ?', (name,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Optional: Call create_tables once when the module is imported
# create_tables()
