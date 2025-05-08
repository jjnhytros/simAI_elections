# utils.py
import queue
import threading  # Importa threading se usi simulation_running_event qui

# --- Pygame Output Handling ---
pygame_update_queue = queue.Queue()
# Evento per segnalare se la simulazione è attiva (impostato da gui.py)
# Rimosso: simulation_running_event = None # Viene gestito direttamente in gui.py


def send_pygame_update(update_type, data=None):
    """Sends an update message to the Pygame queue if Pygame display is active."""
    try:
        import pygame
        # Controlla se Pygame e il suo modulo display sono inizializzati
        if pygame.get_init() and pygame.display.get_init():
            pygame_update_queue.put((update_type, data))
    except (ImportError, pygame.error):  # pragma: no cover
        # Pygame non disponibile o non inizializzato, ignora l'invio
        pass
    except Exception as e:  # pragma: no cover # Altre eccezioni impreviste
        print(f"Error sending Pygame update ({update_type}): {e}")


# Update types for Pygame queue
UPDATE_TYPE_MESSAGE = "message"
UPDATE_TYPE_STATUS = "status"
UPDATE_TYPE_RESULTS = "results"
UPDATE_TYPE_FLAG = "flag"
UPDATE_TYPE_COMPLETE = "complete"
UPDATE_TYPE_ERROR = "error"
UPDATE_TYPE_WARNING = "warning"
UPDATE_TYPE_KEY_ELECTORS = "key_electors"
