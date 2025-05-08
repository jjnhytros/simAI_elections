import queue

# --- Pygame Output Handling ---

# Use a queue to send messages/state updates from the simulation thread to the main Pygame thread
pygame_update_queue = queue.Queue()


def send_pygame_update(update_type, data=None):
    """Sends an update message to the Pygame queue."""
    # Check if Pygame is initialized before putting items on the queue
    # This prevents errors if the simulation thread tries to send updates after Pygame has quit
    try:
        import pygame
        if pygame.display.get_init():
            pygame_update_queue.put((update_type, data))
        # else: print("Pygame not initialized, skipping queue update.") # Optional debug
    except ImportError:
        # Pygame not installed or accessible, can't send updates
        # print("Pygame not imported, skipping queue update.") # Optional debug
        pass
    except Exception as e:
        # Handle other potential errors during queue put
        print(f"Error sending Pygame update: {e}")


# Update types for Pygame queue
UPDATE_TYPE_MESSAGE = "message"
UPDATE_TYPE_STATUS = "status"
UPDATE_TYPE_RESULTS = "results"
UPDATE_TYPE_FLAG = "flag"
UPDATE_TYPE_COMPLETE = (
    "complete"  # Simulation finished (elected or deadlocked)
)
UPDATE_TYPE_ERROR = "error"  # Simulation error
