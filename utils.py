import queue

# --- Pygame Output Handling ---

# Use a queue to send messages/state updates from the simulation thread to the main Pygame thread
pygame_update_queue = queue.Queue()


def send_pygame_update(update_type, data=None):
    """Sends an update message to the Pygame queue."""
    try:
        import pygame
        if pygame.display.get_init():
            pygame_update_queue.put((update_type, data))
    except ImportError:
        pass
    except Exception as e:
        print(f"Error sending Pygame update: {e}")


# Update types for Pygame queue
UPDATE_TYPE_MESSAGE = "message"
UPDATE_TYPE_STATUS = "status"
UPDATE_TYPE_RESULTS = "results"
UPDATE_TYPE_FLAG = "flag"
UPDATE_TYPE_COMPLETE = "complete"
UPDATE_TYPE_ERROR = "error"
# UPDATE_TYPE_KEY_ELECTORS = "key_electors" # Opzionale
