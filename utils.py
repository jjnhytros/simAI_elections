# utils.py

import queue
# import pygame # Importa pygame qui se non lo fai già e se serve per get_init

# --- Pygame Output Handling ---
pygame_update_queue = queue.Queue()
simulation_running_event = None  # Sarà impostato da gui.py


def send_pygame_update(update_type, data=None):
    """Sends an update message to the Pygame queue."""
    try:
        # Questa parte serve per evitare errori se Pygame non è inizializzato
        # o se si esegue la logica di simulazione senza una GUI attiva (es. per test)
        import pygame  # Importazione locale per ridurre dipendenze a livello di modulo
        if pygame.display.get_init():  # Controlla se il modulo display di Pygame è inizializzato
            pygame_update_queue.put((update_type, data))
        # else:
            # print(f"Pygame not init. Update not sent: {update_type}") # Opzionale: Log se non inviato
    except ImportError:  # pragma: no cover
        # print(f"Pygame not imported. Update not sent: {update_type}") # Opzionale
        pass
    except Exception:  # pragma: no cover
        # print(f"Error sending Pygame update ({update_type}): {e}") # Opzionale
        pass


# Update types for Pygame queue
UPDATE_TYPE_MESSAGE = "message"
UPDATE_TYPE_STATUS = "status"
UPDATE_TYPE_RESULTS = "results"
UPDATE_TYPE_FLAG = "flag"
UPDATE_TYPE_COMPLETE = "complete"
UPDATE_TYPE_ERROR = "error"
UPDATE_TYPE_WARNING = "warning"  # Aggiunto per coerenza con gui.py
UPDATE_TYPE_KEY_ELECTORS = "key_electors"  # Decommentato o aggiunto
