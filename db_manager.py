# db_manager.py
import sqlite3
import json
import uuid
import config

# Definizione a livello di modulo per il nome del file DB
DATABASE_FILE = config.DATABASE_FILE


def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    # conn.execute("PRAGMA foreign_keys = ON") # Opzionale
    return conn


def create_tables():
    """Creates the necessary tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            uuid TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL COLLATE NOCASE,
            gender TEXT,
            age INTEGER,
            party_id TEXT,
            initial_budget REAL DEFAULT 0,
            current_budget REAL DEFAULT 0,
            attributes TEXT, -- JSON text
            traits TEXT,     -- JSON text
            stats TEXT       -- JSON text
        )
    ''')
    # cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidate_name ON candidates(name)") # Opzionale
    conn.commit()
    conn.close()


def save_candidate(candidate_data):
    """Saves or updates a candidate's data in the database."""
    if not candidate_data or 'name' not in candidate_data:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    candidate_uuid = str(candidate_data.get('uuid', uuid.uuid4()))
    initial_budget = float(
        candidate_data.get('initial_budget', config.INITIAL_CAMPAIGN_BUDGET))
    current_budget = float(candidate_data.get('current_budget',
                                              initial_budget))
    attributes_json = json.dumps(candidate_data.get('attributes', {}))
    traits_json = json.dumps(candidate_data.get('traits', []))
    stats_data = candidate_data.get('stats', {})
    if not isinstance(stats_data, dict):
        stats_data = {}
    base_stats = {
        "total_elections_participated": 0,
        "governor_wins": 0,
        "election_losses": 0,
        "total_votes_received_all_time": 0,
        "rounds_participated_all_time": 0
    }
    for k, v in base_stats.items():
        stats_data.setdefault(k, v)
    stats_json = json.dumps(stats_data)

    try:
        cursor.execute(
            '''
            INSERT OR REPLACE INTO candidates (uuid, name, gender, age, party_id, initial_budget, current_budget, attributes, traits, stats)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (candidate_uuid, candidate_data.get('name'),
              candidate_data.get('gender'), candidate_data.get('age'),
              candidate_data.get('party_id'), initial_budget, current_budget,
              attributes_json, traits_json, stats_json))
        conn.commit()
    except sqlite3.Error as e:  # pragma: no cover
        print(
            f"Database Error saving candidate {candidate_data.get('name')}: {e}"
        )
    finally:
        conn.close()


def get_candidate_by_name(name):
    """Retrieves a candidate's data by name (case-insensitive)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT * FROM candidates WHERE name = ? COLLATE NOCASE', (name, ))
        row = cursor.fetchone()
        if row:
            candidate_data = dict(row)

            # --- CORREZIONE PARSING JSON ---
            try:
                # Usa or '{}' per fornire una stringa JSON valida se il campo è None o vuoto
                candidate_data['attributes'] = json.loads(
                    candidate_data.get('attributes') or '{}')
            except json.JSONDecodeError:  # pragma: no cover
                print(
                    f"Warning: Invalid JSON in 'attributes' for candidate {name}. Defaulting to {{}}."
                )
                candidate_data['attributes'] = {}
            try:
                candidate_data['traits'] = json.loads(
                    candidate_data.get('traits') or '[]')
            except json.JSONDecodeError:  # pragma: no cover
                print(
                    f"Warning: Invalid JSON in 'traits' for candidate {name}. Defaulting to []."
                )
                candidate_data['traits'] = []
            try:
                candidate_data['stats'] = json.loads(
                    candidate_data.get('stats') or '{}')
            except json.JSONDecodeError:  # pragma: no cover
                print(
                    f"Warning: Invalid JSON in 'stats' for candidate {name}. Defaulting to {{}}."
                )
                candidate_data['stats'] = {}
            # --- FINE CORREZIONE ---

            # Assicura struttura stats base
            base_stats = {
                "total_elections_participated": 0,
                "governor_wins": 0,
                "election_losses": 0,
                "total_votes_received_all_time": 0,
                "rounds_participated_all_time": 0
            }
            # Usa setdefault per aggiungere chiavi mancanti con valore 0
            for k, v in base_stats.items():
                candidate_data['stats'].setdefault(k, v)

            return candidate_data

    except sqlite3.Error as e:  # pragma: no cover
        print(f"Database Error getting candidate by name {name}: {e}")
        return None
    finally:
        conn.close()
    return None  # Ritorna None se 'row' non viene trovato


def candidate_exists(name):
    """Checks if a candidate with the given name exists (case-insensitive)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    exists = False
    try:
        cursor.execute(
            'SELECT 1 FROM candidates WHERE name = ? COLLATE NOCASE', (name, ))
        exists = cursor.fetchone() is not None
    except sqlite3.Error as e:  # pragma: no cover
        print(f"Database Error checking if candidate exists {name}: {e}")
    finally:
        conn.close()
    return exists


def update_candidate_stats(candidate_uuid, stats_to_increment):
    """Incrementally updates statistics for a given candidate UUID."""
    if not candidate_uuid or not stats_to_increment:
        return

    conn = get_db_connection()
    cursor = conn.cursor()  # Muovi la creazione del cursore qui
    try:
        # Approccio Fetch-Modify-Update (più semplice)
        cursor.execute("SELECT stats FROM candidates WHERE uuid = ?",
                       (str(candidate_uuid), ))
        row = cursor.fetchone()
        if row:
            try:
                current_stats_str = row['stats'] if row['stats'] else '{}'
                current_stats = json.loads(current_stats_str)
            except (json.JSONDecodeError, TypeError):  # pragma: no cover
                current_stats = {}

            # Aggiorna statistiche
            for key, increment_value in stats_to_increment.items():
                try:
                    numeric_increment = int(increment_value)
                    current_stats[key] = current_stats.get(
                        key, 0) + numeric_increment
                except (ValueError, TypeError):  # pragma: no cover
                    print(
                        f"Warning: Non-numeric increment value '{increment_value}' for key '{key}' on UUID {candidate_uuid}. Skipping."
                    )

            # Salva JSON aggiornato
            updated_stats_json = json.dumps(current_stats)
            cursor.execute("UPDATE candidates SET stats = ? WHERE uuid = ?",
                           (updated_stats_json, str(candidate_uuid)))
            conn.commit()
        # else: Candidato non trovato, nessun log necessario qui, forse nel chiamante se importante

    except sqlite3.Error as e:  # pragma: no cover
        print(f"Database error updating stats for {candidate_uuid}: {e}")
        # Considera conn.rollback() se usi transazioni esplicite
    except Exception as e:  # pragma: no cover
        print(f"Generic error updating stats for {candidate_uuid}: {e}")
    finally:
        conn.close()
