# db_manager.py
import sqlite3
import json
import uuid
import config


DATABASE_FILE = config.DATABASE_FILE


def get_db_connection():
    """Establishes a connection to the SQLite database."""
    # Ora DATABASE_FILE è definita correttamente in questo scope
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """Creates the necessary tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Modificato per usare TEXT per UUID e JSON per campi complessi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            uuid TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL COLLATE NOCASE, -- COLLATE NOCASE per unicità case-insensitive
            gender TEXT,
            age INTEGER,
            party_id TEXT,
            initial_budget REAL DEFAULT 0,
            current_budget REAL DEFAULT 0,
            attributes TEXT, -- Store as JSON text
            traits TEXT,     -- Store as JSON text
            stats TEXT       -- Store as JSON text (e.g., wins, losses, total_votes)
        )
    ''')
    # Si potrebbero aggiungere indici per ricerche più veloci su 'name' o 'party_id'
    # cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidate_name ON candidates(name)")
    conn.commit()
    conn.close()


def save_candidate(candidate_data):
    """
    Saves or updates a candidate's data in the database.
    Expects a dictionary with candidate information, including 'uuid'.
    Uses INSERT OR REPLACE for simplicity (overwrites existing).
    """
    if not candidate_data or 'name' not in candidate_data:
        print("Error: Cannot save candidate without data or name.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # Assicura UUID e valori di default
    candidate_uuid = str(candidate_data.get('uuid', uuid.uuid4()))
    initial_budget = float(candidate_data.get(
        'initial_budget', config.INITIAL_CAMPAIGN_BUDGET))
    current_budget = float(candidate_data.get(
        'current_budget', initial_budget))  # Default current to initial

    # Prepara dati JSON, assicurandosi che siano stringhe valide
    attributes_json = json.dumps(candidate_data.get('attributes', {}))
    traits_json = json.dumps(candidate_data.get('traits', []))
    # Inizializza stats se non presenti prima del salvataggio
    stats_data = candidate_data.get('stats', {  # Default a struttura vuota se non esiste
        "total_elections_participated": 0,
        "governor_wins": 0,
        "election_losses": 0,
        "total_votes_received_all_time": 0,
        "rounds_participated_all_time": 0
    })
    stats_json = json.dumps(stats_data)

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO candidates (
                uuid, name, gender, age, party_id, initial_budget, current_budget, attributes, traits, stats
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            candidate_uuid,
            candidate_data.get('name'),
            candidate_data.get('gender'),
            candidate_data.get('age'),
            candidate_data.get('party_id'),
            initial_budget,
            current_budget,
            attributes_json,
            traits_json,
            stats_json
        ))
        conn.commit()
    except sqlite3.IntegrityError as e:  # pragma: no cover
        print(
            f"Database Integrity Error saving candidate {candidate_data.get('name')}: {e}")
    except sqlite3.Error as e:  # pragma: no cover
        print(
            f"Database Error saving candidate {candidate_data.get('name')}: {e}")
    finally:
        conn.close()


def get_candidate_by_name(name):
    """Retrieves a candidate's data from the database by name (case-insensitive)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT * FROM candidates WHERE name = ? COLLATE NOCASE', (name,))
        row = cursor.fetchone()
        if row:
            candidate_data = dict(row)
            # Carica JSON, gestendo errori o valori null/vuoti
            try:
                candidate_data['attributes'] = json.loads(
                    candidate_data.get('attributes') or '{}')
            except (json.JSONDecodeError, TypeError):  # pragma: no cover
                candidate_data['attributes'] = {}
            try:
                candidate_data['traits'] = json.loads(
                    candidate_data.get('traits') or '[]')
            except (json.JSONDecodeError, TypeError):  # pragma: no cover
                candidate_data['traits'] = []
            try:
                candidate_data['stats'] = json.loads(
                    candidate_data.get('stats') or '{}')
            except (json.JSONDecodeError, TypeError):  # pragma: no cover
                # Default a dict vuoto in caso di errore
                candidate_data['stats'] = {}

            # Assicura che la struttura base delle stats esista
            default_stats = {
                "total_elections_participated": 0, "governor_wins": 0,
                "election_losses": 0, "total_votes_received_all_time": 0,
                "rounds_participated_all_time": 0
            }
            for key, default_value in default_stats.items():
                if key not in candidate_data['stats']:
                    candidate_data['stats'][key] = default_value

            return candidate_data

    except sqlite3.Error as e:  # pragma: no cover
        print(f"Database Error getting candidate by name {name}: {e}")
        return None
    finally:
        conn.close()
    return None


def candidate_exists(name):
    """Checks if a candidate with the given name exists (case-insensitive)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    exists = False
    try:
        cursor.execute(
            'SELECT 1 FROM candidates WHERE name = ? COLLATE NOCASE', (name,))
        exists = cursor.fetchone() is not None
    except sqlite3.Error as e:  # pragma: no cover
        print(f"Database Error checking if candidate exists {name}: {e}")
    finally:
        conn.close()
    return exists


def update_candidate_stats(candidate_uuid, stats_to_increment):
    """
    Incrementally updates statistics for a given candidate UUID using JSON functions.

    Args:
        candidate_uuid (str): The UUID of the candidate to update.
        stats_to_increment (dict): A dictionary where keys are stat names
                                   (e.g., 'governor_wins') and values are the
                                   amounts to increment by (e.g., 1).
    """
    if not candidate_uuid or not stats_to_increment:
        return  # Non fare nulla se non c'è UUID o non ci sono stats da aggiornare

    conn = get_db_connection()
    try:
        # Usiamo le funzioni JSON di SQLite per aggiornare direttamente il campo JSON
        # Questo è generalmente più sicuro per la concorrenza rispetto a fetch-modify-update
        # Requires SQLite 3.38.0+ for json_patch

        # Costruisci un json_patch per incrementare i valori
        # Esempio: per {'governor_wins': 1, 'total_votes': 50}
        # json_patch dovrebbe essere simile a:
        # '{"governor_wins": current_value + 1, "total_votes": current_value + 50}'
        # Questo è complesso da costruire dinamicamente in SQL puro senza conoscere i valori correnti.

        # Approccio Fetch-Modify-Update (più semplice da implementare qui, ma meno sicuro per concorrenza)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stats FROM candidates WHERE uuid = ?", (str(candidate_uuid),))
        row = cursor.fetchone()

        if row:
            try:
                # Usa un dizionario vuoto come default se row['stats'] è None o vuoto
                current_stats_str = row['stats'] if row['stats'] else '{}'
                current_stats = json.loads(current_stats_str)
            except (json.JSONDecodeError, TypeError):  # pragma: no cover
                current_stats = {}  # Inizializza se JSON non valido

            # Aggiorna le statistiche, inizializzando a 0 se la chiave non esiste
            for key, increment_value in stats_to_increment.items():
                # Assicurati che l'incremento sia numerico
                try:
                    # O float se necessario
                    numeric_increment = int(increment_value)
                    current_stats[key] = current_stats.get(
                        key, 0) + numeric_increment
                except (ValueError, TypeError):  # pragma: no cover
                    print(
                        f"Warning: Non-numeric increment value '{increment_value}' for key '{key}' on UUID {candidate_uuid}. Skipping.")

            # Aggiorna il campo stats nel database
            updated_stats_json = json.dumps(current_stats)
            cursor.execute("UPDATE candidates SET stats = ? WHERE uuid = ?",
                           (updated_stats_json, str(candidate_uuid)))
            conn.commit()
        # else: Candidate non trovato, nessun aggiornamento

    except sqlite3.Error as e:  # pragma: no cover
        print(f"Database error updating stats for {candidate_uuid}: {e}")
        # Considera conn.rollback() qui se usi transazioni esplicite
    except Exception as e:  # pragma: no cover
        print(f"Generic error updating stats for {candidate_uuid}: {e}")
        # Considera conn.rollback()
    finally:
        conn.close()

# Optional: Call create_tables once when the module is imported?
# Potrebbe essere meglio chiamarla esplicitamente all'avvio dell'applicazione principale (es. in gui.py)
# create_tables()
