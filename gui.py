# gui.py
import pygame
import sys
import threading
import queue
import time

# Imports da altri moduli del progetto (assoluti)
import config
import data  # Import necessario per accedere alle liste nomi in caso di necessità future
import utils
import election  # Import election module

# --- Add check here ---
if not hasattr(election, 'run_election_simulation'):
    print(
        "FATAL GUI ERROR: 'election' module does not have 'run_election_simulation' attribute."
    )
    # You might want to exit or raise an error here if this happens
    # Exiting the GUI thread if the core simulation function is missing
    sys.exit("Missing run_election_simulation in election module.")
# --- End check ---

# UI Layout Areas
STATUS_AREA = None
VISUAL_AREA = None
RESULTS_AREA = None
LOG_AREA = None
BUTTON_AREA = None

# Event per controllare la simulazione (GUI -> Simulation)
simulation_continue_event = threading.Event()
# Event per segnalare che la simulazione è in corso (Simulation -> GUI)
simulation_running_event = threading.Event()
# Flag per indicare se la simulazione è in attesa del "prossimo round" in modalità passo-passo
simulation_waiting_for_next = False

# To store (rect, candidate_info) for clickable areas in the Visual Area
# Questo ora potrebbe non più necessario se non rendiamo i nomi cliccabili,
# ma lo lasciamo per ora, memorizzerà il rect del testo.
displayed_candidate_text_rects = []


def render_text(font,
                text,
                color,
                surface,
                x,
                y,
                antialias=True):  # Aggiunto antialias
    """Renders text on a Pygame surface."""
    text_surface = font.render(str(text), antialias, color)  # Usa antialias
    rect = surface.blit(text_surface, (x, y))
    # Restituisce l'altezza e il rettangolo per potenziali interazioni
    return text_surface.get_height(), rect


def get_sprite_from_sheet(spritesheet, row, col, sprite_width, sprite_height):
    """DEPRECATO: Non più usata per estrarre sprite."""
    # Questa funzione non è più necessaria e può essere rimossa o lasciata vuota.
    return None


def draw_button(surface, rect, color, text, font, text_color, enabled=True):
    """Draws a simple button."""
    button_color = color
    text_color_actual = text_color

    if not enabled:
        button_color = config.GRAY
        text_color_actual = config.DARK_GRAY

    pygame.draw.rect(surface, button_color, rect)
    pygame.draw.rect(surface, config.WHITE, rect, 1)  # Border

    text_surface = font.render(text, True, text_color_actual)
    text_rect = text_surface.get_rect(center=rect.center)
    surface.blit(text_surface, text_rect)

    return rect


def main_pygame_gui():
    global STATUS_AREA, VISUAL_AREA, RESULTS_AREA, LOG_AREA, BUTTON_AREA, simulation_waiting_for_next, displayed_candidate_text_rects

    print("DEBUG: Entering main_pygame_gui function.")  # DEBUG PRINT

    pygame.init()
    print("DEBUG: Pygame initialized.")  # DEBUG PRINT

    infoObject = pygame.display.Info()
    SCREEN_WIDTH = infoObject.current_w
    SCREEN_HEIGHT = infoObject.current_h
    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN
        | pygame.SRCALPHA)  # Aggiunto SRCALPHA per trasparenza se necessaria
    print(
        f"DEBUG: Pygame display set to {SCREEN_WIDTH}x{SCREEN_HEIGHT} fullscreen."
    )  # DEBUG PRINT

    pygame.display.set_caption(config.WINDOW_TITLE)

    try:
        # Usiamo un font più leggibile se disponibile
        font = pygame.font.SysFont("DejaVu Sans", config.PIXEL_FONT_SIZE)
        small_font = pygame.font.SysFont(
            "DejaVu Sans", config.PIXEL_FONT_SIZE - 4)  # Ridotto un po' di più
        title_font = pygame.font.SysFont("DejaVu Sans",
                                         config.PIXEL_FONT_SIZE + 2,
                                         bold=True)
        print("DEBUG: Custom font loaded.")  # DEBUG PRINT
    except pygame.error as e:
        print(
            f"Warning, could not load 'DejaVu Sans' font: {e}. Falling back to monospace."
        )
        font = pygame.font.SysFont("monospace", config.PIXEL_FONT_SIZE)
        small_font = pygame.font.SysFont("monospace",
                                         config.PIXEL_FONT_SIZE - 2)
        title_font = pygame.font.SysFont("monospace",
                                         config.PIXEL_FONT_SIZE + 2,
                                         bold=True)
        print("DEBUG: Monospace font loaded.")  # DEBUG PRINT

    clock = pygame.time.Clock()

    # --- RIMOZIONE CARICAMENTO IMMAGINI E SPRITE ---
    # assets = {}
    # sprites = {}
    # for name, path in config.IMAGE_PATHS.items(): ... (rimosso)
    # if data.SPRITE_MAPPING: ... (rimosso)
    # --- FINE RIMOZIONE ---

    # --- UI Layout Areas (come prima) ---
    STATUS_AREA = pygame.Rect(20, 20, SCREEN_WIDTH - 40, 80)
    VISUAL_AREA_HEIGHT = 150  # Altezza ridotta, non servono più gli sprite alti
    VISUAL_AREA = pygame.Rect(20, STATUS_AREA.bottom + 10, SCREEN_WIDTH - 40,
                              VISUAL_AREA_HEIGHT)
    AREA_PADDING = 10
    BUTTON_AREA_HEIGHT = 50
    REMAINING_HEIGHT = SCREEN_HEIGHT - VISUAL_AREA.bottom - (
        AREA_PADDING * 3) - BUTTON_AREA_HEIGHT - 20

    RESULTS_AREA_WIDTH = (SCREEN_WIDTH - (AREA_PADDING * 3)) // 2
    LOG_AREA_WIDTH = SCREEN_WIDTH - (AREA_PADDING * 3) - RESULTS_AREA_WIDTH

    RESULTS_AREA = pygame.Rect(AREA_PADDING, VISUAL_AREA.bottom + AREA_PADDING,
                               RESULTS_AREA_WIDTH, REMAINING_HEIGHT)
    LOG_AREA = pygame.Rect(RESULTS_AREA.right + AREA_PADDING,
                           VISUAL_AREA.bottom + AREA_PADDING, LOG_AREA_WIDTH,
                           REMAINING_HEIGHT)
    BUTTON_AREA = pygame.Rect(AREA_PADDING, LOG_AREA.bottom + AREA_PADDING,
                              SCREEN_WIDTH - (AREA_PADDING * 2),
                              BUTTON_AREA_HEIGHT)

    # Simulation state variables for GUI display (come prima)
    current_status = {
        "attempt": 0,
        "phase": "Initializing...",
        "round": 0,
        "status": "Idle",
    }
    current_results_data = []
    log_messages = []
    current_status_text = ""
    key_electors_log = []  # Lista per log elettori chiave

    log_line_height = small_font.get_linesize()
    if log_line_height <= 0:
        log_line_height = config.PIXEL_FONT_SIZE - 2
    max_log_lines = (LOG_AREA.height // log_line_height) - 2

    flag_state = None

    simulation_thread = None
    simulation_started = False
    step_by_step_mode = config.STEP_BY_STEP_MODE_DEFAULT

    running = True
    print("DEBUG: Entering Pygame main loop.")  # DEBUG PRINT
    while running:
        # --- Event Handling ---
        mouse_pos = pygame.mouse.get_pos()
        clicked_candidate = None  # Per tooltip/info
        tooltip_text = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check button clicks
                    # ... (logica pulsanti Start, Next Round, Quit come prima) ...
                    if 'start_button_rect' in locals(
                    ) and start_button_rect.collidepoint(event.pos):
                        # ... (logica start)
                        if not simulation_running_event.is_set():
                            simulation_started = True
                            current_status = {
                                "attempt": 1,
                                "phase": "Initializing...",
                                "round": 0,
                                "status": "Idle"
                            }  # Resetta tentativo a 1
                            current_results_data = []
                            log_messages = ["Simulation started..."]
                            key_electors_log = []
                            flag_state = None
                            simulation_waiting_for_next = False
                            displayed_candidate_text_rects = []
                            simulation_continue_event.clear()
                            # Start the simulation thread
                            simulation_thread = threading.Thread(
                                target=election.run_election_simulation,
                                kwargs={
                                    'election_attempt': current_status[
                                        'attempt'],  # Usa tentativo corrente
                                    'preselected_candidates_info':
                                    None,  # Resetta sempre all'inizio da GUI
                                    'runoff_carryover_winner_name':
                                    None,  # Resetta sempre
                                    'continue_event':
                                    simulation_continue_event,
                                    'running_event': simulation_running_event,
                                    'step_by_step_mode': step_by_step_mode
                                })
                            simulation_thread.daemon = True
                            simulation_thread.start()
                            simulation_running_event.set(
                            )  # Signal simulation is running
                            if not step_by_step_mode:
                                simulation_continue_event.set(
                                )  # Automatically continue if not step-by-step

                    if step_by_step_mode and 'next_round_button_rect' in locals(
                    ) and next_round_button_rect.collidepoint(event.pos):
                        if simulation_running_event.is_set(
                        ) and simulation_waiting_for_next:
                            simulation_continue_event.set(
                            )  # Signal simulation to continue
                            # Resetta subito in attesa della prossima attesa
                            simulation_waiting_for_next = False

                    if 'quit_button_rect' in locals(
                    ) and quit_button_rect.collidepoint(event.pos):
                        running = False  # Exit the GUI loop

                    # Controlla click sui nomi dei candidati (se vogliamo ripristinare questa funzione)
                    # for rect, candidate_info in displayed_candidate_text_rects:
                    #     if rect.collidepoint(event.pos):
                    #         # Visualizza gli attributi del candidato nel log
                    #         utils.send_pygame_update(
                    #             utils.UPDATE_TYPE_MESSAGE,
                    #             f"\n--- Attributes for {candidate_info['name']} ---"
                    #         )
                    #         attributes_str = ", ".join([
                    #             f"{key.replace('_', ' ').title()}: {value}"
                    #             for key, value in
                    #             candidate_info.get('attributes', {}).items() # Usa .get per sicurezza
                    #         ])
                    #         utils.send_pygame_update(
                    #             utils.UPDATE_TYPE_MESSAGE,
                    #             f"  Gender: {candidate_info.get('gender', 'N/A').title()}") # Mostra anche genere
                    #         utils.send_pygame_update(
                    #             utils.UPDATE_TYPE_MESSAGE,
                    #             f"  Attributes: {attributes_str if attributes_str else 'N/A'}")
                    #         utils.send_pygame_update(
                    #             utils.UPDATE_TYPE_MESSAGE,
                    #             "--------------------------------------")
                    #         break

        # --- Process updates from simulation thread ---
        # Check the queue for updates from the simulation thread
        while not utils.pygame_update_queue.empty():
            try:
                update_type, update_data = (
                    utils.pygame_update_queue.get_nowait())
            except queue.Empty:
                break  # Exit if queue is empty

            # Process different update types
            if update_type == utils.UPDATE_TYPE_MESSAGE:
                log_messages.append(str(update_data))
                if len(log_messages) > max_log_lines:
                    log_messages = log_messages[
                        -max_log_lines:]  # Keep only the most recent messages
            # --- Gestione Elettori Chiave (se si usasse un tipo dedicato) ---
            # elif update_type == utils.UPDATE_TYPE_KEY_ELECTORS:
            #     key_electors_log = update_data # Salva i dati per potenziale visualizzazione
            #     # Logga anche i primi N
            #     log_messages.append("\n--- Key Electors Identified ---")
            #     for ke_idx, ke_info in enumerate(update_data):
            #         if ke_idx < 5:
            #              log_messages.append(f"  ID: {ke_info['id']}, Reasons: {', '.join(ke_info['reasons'])}")
            #     if len(update_data) > 5:
            #          log_messages.append("  ...")
            #     if len(log_messages) > max_log_lines:
            #         log_messages = log_messages[-max_log_lines:]
            # --- Fine Gestione Elettori Chiave ---

            elif update_type == utils.UPDATE_TYPE_STATUS:
                # Update only the keys present in update_data
                for key, value in update_data.items():
                    if key in current_status:
                        current_status[key] = value
                    # Update the attempt number if provided
                    elif key == "attempt":
                        current_status['attempt'] = value

                # Handle waiting status for step-by-step mode
                if step_by_step_mode and current_status.get(
                        "status") == "Waiting for Next Round":
                    simulation_waiting_for_next = True
                else:
                    simulation_waiting_for_next = False

            elif update_type == utils.UPDATE_TYPE_RESULTS:
                if update_data and "results" in update_data:
                    current_results_data = update_data[
                        "results"]  # Update the results data

            elif update_type == utils.UPDATE_TYPE_FLAG:
                flag_state = update_data  # Update flag state

            elif update_type == utils.UPDATE_TYPE_COMPLETE:
                # Simulation is complete (elected or deadlock)
                current_status["status"] = "Simulation Complete"
                if update_data and update_data.get("elected"):
                    # Governor was elected
                    governor_name = update_data.get("governor", "Unknown")
                    current_status[
                        "governor"] = governor_name  # Store governor name
                    log_messages.append(
                        f"\n{'*' * 30}\n*** GOVERNOR {governor_name.upper()} ELECTED! ***\n{'*' * 30}\n"
                    )
                    # Find the elected candidate's full info to display attributes in log
                    elected_candidate_info = next(
                        (item for item in current_results_data
                         if item.get('name') == governor_name), None)
                    if elected_candidate_info and elected_candidate_info.get(
                            'attributes'):
                        log_messages.append(
                            f"Governor Attributes {governor_name}:")
                        attributes_str = ", ".join([
                            f"{key.replace('_', ' ').title()}: {value}"
                            for key, value in
                            elected_candidate_info['attributes'].items()
                        ])
                        log_messages.append(f"  {attributes_str}")
                        log_messages.append("-" * 30)
                else:
                    # Simulation ended in deadlock
                    log_messages.append(
                        f"\n{'=' * 30}\n--- ELECTORAL DEADLOCK ---\n--- No Governor elected after {config.MAX_ELECTION_ATTEMPTS} attempts ---\n{'=' * 30}\n"
                    )
                simulation_running_event.clear(
                )  # Signal simulation is no longer running
                simulation_waiting_for_next = False  # No longer waiting for next round
                if len(log_messages) > max_log_lines:
                    log_messages = log_messages[-max_log_lines:]

            elif update_type == utils.UPDATE_TYPE_ERROR:
                # An error occurred in the simulation thread
                log_messages.append(
                    f"\n{'!' * 30}\n!!! SIMULATION ERROR !!!\n!!! {update_data} !!!\n{'!' * 30}\n"
                )
                current_status[
                    "status"] = "Error"  # Update status to indicate error
                simulation_running_event.clear(
                )  # Signal simulation is no longer running
                simulation_waiting_for_next = False
                if len(log_messages) > max_log_lines:
                    log_messages = log_messages[-max_log_lines:]
            elif update_type == utils.UPDATE_TYPE_WARNING:  # Handle warnings from simulation
                log_messages.append(
                    f"\n--- WARNING --- \n{update_data}\n-------------")
                if len(log_messages) > max_log_lines:
                    log_messages = log_messages[-max_log_lines:]

        # --- Drawing ---
        screen.fill(config.BG_COLOR)  # Fill background

        # Draw Status Area
        status_bg_surface = pygame.Surface(STATUS_AREA.size, pygame.SRCALPHA)
        status_bg_surface.fill(
            (64, 64, 64, 192))  # Dark gray with some transparency
        screen.blit(status_bg_surface, STATUS_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, STATUS_AREA, 1)  # White border

        status_y = STATUS_AREA.top + 5
        status_x_left = STATUS_AREA.left + 10
        # Position of right-aligned status info
        status_x_right = STATUS_AREA.left + 300

        if 'font' in locals() and font:
            # Render status text
            h1, _ = render_text(
                font,
                f"Attempt: {current_status.get('attempt', '-')}/{config.MAX_ELECTION_ATTEMPTS}",
                config.WHITE, screen, status_x_left, status_y)
            h2, _ = render_text(
                font, f"Phase: {current_status.get('phase', 'N/A')}",
                config.WHITE, screen, status_x_left, status_y + h1 + 2)
            render_text(font, f"Round: {current_status.get('round', '-')}",
                        config.WHITE, screen, status_x_right, status_y)
            current_status_text = current_status.get("status", "")
            h3, _ = render_text(font, f"Status: {current_status_text}",
                                config.WHITE, screen, status_x_left,
                                status_y + h1 + h2 + 4)
            # Display elected governor's name if simulation is complete and elected
            if current_status_text == "Governor Elected!" and "governor" in current_status:
                render_text(font, f"Governor: {current_status['governor']}",
                            config.GREEN, screen, status_x_right,
                            status_y + h1 + 2)  # Align with Round
            # Display current mode (step-by-step or continuous)
            mode_text = "Mode: Step-by-Step" if step_by_step_mode else "Mode: Continuous"
            render_text(small_font, mode_text, config.WHITE, screen,
                        status_x_left,
                        STATUS_AREA.bottom - small_font.get_linesize() - 5)
        # ... (fallback else if font loading failed)

        # --- Draw Visual Area (MODIFIED) ---
        visual_bg_surface = pygame.Surface(VISUAL_AREA.size, pygame.SRCALPHA)
        visual_bg_surface.fill(
            (32, 32, 32, 160))  # Darker gray with more transparency
        screen.blit(visual_bg_surface, VISUAL_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, VISUAL_AREA, 1)  # White border

        # Draw candidate names with gender-based colors
        displayed_candidate_text_rects = []  # Reset the list for this frame

        # Get the items to display (usually candidates from the last results update)
        display_items = current_results_data
        max_visual_candidates = 12  # Limit the number of names displayed in the visual area
        displayed_visual_items = display_items[:max_visual_candidates]

        num_display_visual = len(displayed_visual_items)
        if num_display_visual > 0 and 'small_font' in locals() and small_font:
            num_columns = 3  # Number of columns to arrange names
            col_width = VISUAL_AREA.width // num_columns
            row_height = small_font.get_linesize() + 4  # Spacing between rows
            start_x = VISUAL_AREA.left + 10
            start_y = VISUAL_AREA.top + 10
            current_col = 0
            current_row = 0

            # Iterate through the candidates to display
            for item in displayed_visual_items:
                candidate_name = item.get('name', 'N/A')
                gender = item.get('gender', 'unknown')
                party_id = item.get('party_id', 'N/A')  # Get party_id
                attributes = item.get('attributes',
                                      {})  # Get attributes dictionary
                age = item.get('age', 'N/A')  # Get age

                # Determine text color based on gender
                text_color = config.WHITE  # Default color
                if gender == "female":
                    text_color = config.PINK
                elif gender == "male":
                    text_color = config.LIGHT_BLUE
                # You could add party-based colors here if desired

                # Calcola posizione
                text_x = start_x + current_col * col_width
                text_y = start_y + current_row * row_height

                # Render the candidate name
                h, text_rect = render_text(small_font, candidate_name,
                                           text_color, screen, text_x, text_y)
                # Store the text rectangle and candidate info for tooltip collision detection
                displayed_candidate_text_rects.append((text_rect, item))

                # Check if mouse is hovering over the candidate name for tooltip
                if text_rect.collidepoint(mouse_pos):
                    # Store clicked candidate info (for potential future interaction)
                    clicked_candidate = item

                    # Format attributes string from the attributes dictionary
                    attributes_str = ", ".join([
                        f"{k.replace('_',' ').title()}: {v}"
                        for k, v in attributes.items()
                    ])

                    # Construct the tooltip text
                    tooltip_text = (
                        f"{candidate_name} ({party_id})\n"  # Add Party ID
                        f"Age: {age}, Gender: {gender.title()}\n"
                        # Display formatted attributes or N/A
                        f"Attributes: {attributes_str if attributes_str else 'N/A'}"
                    )

                    # --- Debugging: Log if attributes are N/A in the tooltip ---
                    if attributes_str == 'N/A':
                        print(
                            f"DEBUG: Attributes shown as N/A for {candidate_name}. Item data received by GUI: {item}"
                        )
                    # --- End Debugging ---

                # Update position for the next name in this column
                current_row += 1
                # Move to the next column if the current column is full
                if start_y + (
                        current_row) * row_height > VISUAL_AREA.bottom - 10:
                    current_row = 0
                    current_col += 1
                    # Stop if we've filled all columns
                    if current_col >= num_columns:
                        break

        # --- Draw Results Area (with bars, as before) ---
        results_bg_surface = pygame.Surface(RESULTS_AREA.size, pygame.SRCALPHA)
        results_bg_surface.fill(
            (48, 48, 48, 192))  # Slightly darker gray with transparency
        screen.blit(results_bg_surface, RESULTS_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, RESULTS_AREA, 1)  # White border

        if 'font' in locals() and font:
            # Render section title
            _, _ = render_text(title_font, "Latest Results:", config.WHITE,
                               screen, RESULTS_AREA.left + 10,
                               RESULTS_AREA.top + 5)

            # Draw result bars if results data is available
            if current_results_data:
                # Filter results to only include candidates with votes for bar calculation
                relevant_results = [
                    item for item in current_results_data
                    if item.get('votes', 0) > 0
                ]
                # Calculate maximum votes among relevant results for scaling bars
                max_votes = max(
                    item['votes']
                    for item in relevant_results) if relevant_results else 1

                bar_area_width = RESULTS_AREA.width - 20  # Area width for bars
                bar_height = 15  # Height of each bar
                bar_spacing = 5  # Space between bars
                bar_start_y = RESULTS_AREA.top + 5 + title_font.get_linesize(
                ) + 10  # Starting Y position for the first bar

                # Sort relevant results by votes received (descending)
                sorted_results = sorted(relevant_results,
                                        key=lambda x: x.get('votes', 0),
                                        reverse=True)
                # Calculate total votes in this round for percentage calculation
                total_votes_this_round = sum(
                    item['votes']
                    for item in relevant_results) if relevant_results else 0

                # Draw bars for each candidate in the sorted results
                for i, item in enumerate(sorted_results):
                    # Check if there is enough vertical space to draw the bar
                    if bar_start_y + i * (
                            bar_height + bar_spacing
                    ) + bar_height <= RESULTS_AREA.bottom - 5:
                        candidate_name = item['name']
                        votes = item['votes']
                        is_elected_this_round = item.get(
                            'elected_this_round', False)
                        # Check if this candidate is the final elected Governor
                        is_overall_elected = (
                            current_status.get("status") == "Governor Elected!"
                            and candidate_name
                            == current_status.get("governor"))

                        # Calculate vote percentage
                        vote_percentage = (
                            votes / total_votes_this_round
                        ) * 100 if total_votes_this_round > 0 else 0

                        # Calculate bar width (at least 1 pixel if votes > 0)
                        bar_width = (votes / max_votes
                                     ) * bar_area_width if max_votes > 0 else 0
                        bar_width = max(
                            1, bar_width
                        ) if votes > 0 else 0  # Ensure at least 1px width if votes > 0

                        # Determine bar color
                        bar_color = config.GRAY  # Default color
                        if is_elected_this_round or is_overall_elected:
                            bar_color = config.GREEN  # Green if elected in this round or final Governor

                        # Create bar rectangle
                        bar_rect = pygame.Rect(
                            RESULTS_AREA.left + 10,
                            bar_start_y + i * (bar_height + bar_spacing),
                            bar_width, bar_height)
                        # Draw bar and border
                        pygame.draw.rect(screen, bar_color, bar_rect)
                        pygame.draw.rect(screen, config.WHITE, bar_rect,
                                         1)  # Border

                        # Render candidate name and vote count/percentage
                        if 'small_font' in locals() and small_font:
                            name_text = f"{candidate_name}: {votes} ({vote_percentage:.1f}%)"
                            name_surface = small_font.render(
                                name_text, True, config.WHITE)

                            # Position text relative to the bar (inside if space, otherwise outside)
                            text_x = bar_rect.left + 5
                            # If the bar is too narrow, place the text to the right of the bar
                            if bar_width < name_surface.get_width() + 10:
                                text_x = bar_rect.right + 5

                            name_y = bar_rect.centery - name_surface.get_height(
                            ) // 2  # Center text vertically in the bar
                            # Clamp text position to the results area bounds
                            text_x = min(
                                text_x, RESULTS_AREA.right - 10 -
                                name_surface.get_width())
                            screen.blit(name_surface, (text_x, name_y))
                    else:
                        # If no more vertical space, indicate truncation
                        if 'small_font' in locals() and small_font:
                            render_text(
                                small_font, "...", config.WHITE, screen,
                                RESULTS_AREA.left + 10,
                                bar_start_y + i * (bar_height + bar_spacing))
                        break  # Exit the loop if no more vertical space
        # ... (fallback else if font loading failed)

        # Draw Log Area (as before)
        log_bg_surface = pygame.Surface(LOG_AREA.size, pygame.SRCALPHA)
        log_bg_surface.fill((48, 48, 48, 192))  # Darker gray with transparency
        screen.blit(log_bg_surface, LOG_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, LOG_AREA, 1)  # White border

        if 'small_font' in locals() and small_font:
            # Render section title
            _, _ = render_text(title_font, "Log:", config.WHITE, screen,
                               LOG_AREA.left + 10, LOG_AREA.top + 5)

            log_y = LOG_AREA.top + 5 + title_font.get_linesize(
            ) + 5  # Starting Y position for log messages
            # Display log messages from the most recent to the oldest (reversed list)
            for msg in reversed(log_messages):
                # Check if there is enough vertical space for the message line(s)
                if log_y + small_font.get_linesize() <= LOG_AREA.bottom - 5:
                    # Simple word wrap logic
                    words = msg.split(' ')
                    lines = []
                    current_line = ""
                    max_width = LOG_AREA.width - 20  # Maximum text width within the log area

                    for word in words:
                        test_line = current_line + word + " "
                        # Check if adding the next word exceeds the max width
                        test_surface = small_font.render(
                            test_line, True, config.WHITE)
                        if test_surface.get_width() < max_width:
                            current_line = test_line
                        else:
                            # If it exceeds, add the current line (without the new word) and start a new line with the word
                            lines.append(current_line)
                            current_line = word + " "  # Start new line with the current word

                    lines.append(
                        current_line)  # Add the last line after the loop

                    # Render the wrapped lines for the current log message
                    temp_y = log_y
                    for line in lines:
                        if temp_y + small_font.get_linesize(
                        ) <= LOG_AREA.bottom - 5:
                            render_text(
                                small_font,
                                line.strip(),
                                config.
                                # Render the line (strip leading/trailing spaces)
                                WHITE,
                                screen,
                                LOG_AREA.left + 10,
                                temp_y)
                            temp_y += small_font.get_linesize(
                            )  # Move down for the next line
                        else:
                            break  # No more vertical space for this message

                    log_y = temp_y  # Update the starting Y for the next log message
                    # If the log area is full, stop drawing messages
                    if log_y >= LOG_AREA.bottom - 5:
                        break
                else:
                    # If not even space for the first line of the next message, stop
                    break
        # ... (fallback else if font loading failed)

        # Draw Flag Area (as before)
        flag_area_rect = pygame.Rect(
            STATUS_AREA.right - 70,
            STATUS_AREA.top + 5,
            60,
            STATUS_AREA.height - 10,
        )
        # Draw flag based on flag_state (True for green, False for black)
        if flag_state is True:
            stripe_width = flag_area_rect.width // 3
            stripe_height = flag_area_rect.height
            # Draw three vertical stripes for the flag (assuming a simple flag design)
            pygame.draw.rect(
                screen,
                config.LIGHT_BLUE,  # Left stripe
                (flag_area_rect.left, flag_area_rect.top, stripe_width,
                 stripe_height))
            pygame.draw.rect(
                screen,
                config.BLUE,  # Middle stripe
                (flag_area_rect.left + stripe_width, flag_area_rect.top,
                 stripe_width, stripe_height))
            pygame.draw.rect(
                screen,
                config.LIGHT_BLUE,  # Right stripe
                (flag_area_rect.left + 2 * stripe_width, flag_area_rect.top,
                 stripe_width, stripe_height))
        elif flag_state is False:
            pygame.draw.rect(
                screen, config.BLACK,
                flag_area_rect)  # Black rectangle if flag is False
        pygame.draw.rect(screen, config.WHITE, flag_area_rect,
                         1)  # White border for the flag area

        # Draw Button Area (as before)
        BUTTON_WIDTH = 150  # Width of buttons
        BUTTON_HEIGHT = BUTTON_AREA.height - 10  # Height of buttons
        button_padding = 20  # Space between buttons

        # Calculate the number of buttons to display based on mode
        visible_buttons_count = 2 + (
            1 if step_by_step_mode else 0
        )  # Start, Quit, plus Next Round if step-by-step

        # Calculate total width needed for buttons and padding
        total_visible_buttons_width = BUTTON_WIDTH * visible_buttons_count + button_padding * (
            visible_buttons_count - 1 if visible_buttons_count > 1 else 0)

        # Calculate starting X position to center the buttons
        button_start_x = BUTTON_AREA.left + (BUTTON_AREA.width -
                                             total_visible_buttons_width) // 2
        button_y = BUTTON_AREA.top + 5  # Y position for buttons

        # Draw Start Election button
        start_button_enabled = not simulation_running_event.is_set(
        )  # Enabled if simulation is not running
        start_button_rect = draw_button(
            screen,
            pygame.Rect(button_start_x, button_y, BUTTON_WIDTH, BUTTON_HEIGHT),
            config.GREEN,  # Green color
            "Start Election",
            font,
            config.WHITE,
            enabled=start_button_enabled)
        current_button_x = start_button_rect.right + \
            button_padding  # Position for the next button

        # Draw Next Round button (only in step-by-step mode)
        if step_by_step_mode:
            next_round_button_enabled = simulation_running_event.is_set(
            ) and simulation_waiting_for_next  # Enabled if simulation is running and waiting
            next_round_button_rect = draw_button(
                screen,
                pygame.Rect(current_button_x, button_y, BUTTON_WIDTH,
                            BUTTON_HEIGHT),
                config.BLUE,  # Blue color
                "Next Round",
                font,
                config.WHITE,
                enabled=next_round_button_enabled)
            current_button_x = next_round_button_rect.right + \
                button_padding  # Position for the next button

        # Draw Quit button
        quit_button_rect = draw_button(
            screen,
            pygame.Rect(current_button_x, button_y, BUTTON_WIDTH,
                        BUTTON_HEIGHT),
            config.RED,  # Red color
            "Quit",
            font,
            config.WHITE,
            enabled=True)  # Always enabled

        # --- Tooltip Drawing ---
        # Draw the tooltip if tooltip_text is set (meaning mouse is hovering over a candidate name)
        if tooltip_text:
            # Split tooltip text by newline for multi-line display
            tooltip_lines = tooltip_text.split('\n')
            max_tooltip_width = 0
            tooltip_surfaces = []
            total_tooltip_height = 0
            line_spacing = 2  # Space between lines

            # Render each line of the tooltip text to get dimensions
            for line in tooltip_lines:
                surf = small_font.render(line, True,
                                         config.BLACK)  # Render text in black
                tooltip_surfaces.append(surf)
                max_tooltip_width = max(
                    max_tooltip_width,
                    surf.get_width())  # Find the widest line
                total_tooltip_height += surf.get_height(
                ) + line_spacing  # Calculate total height

            # Calculate the rectangle for the tooltip background
            tooltip_rect = pygame.Rect(0, 0, max_tooltip_width + 10,
                                       total_tooltip_height +
                                       5)  # Add padding around the text

            # Position tooltip relative to mouse cursor with a small offset
            tooltip_rect.topleft = (mouse_pos[0] + 15, mouse_pos[1] + 10
                                    )  # Offset from mouse

            # Clamp the tooltip rectangle to screen bounds to prevent it from going off-screen
            tooltip_rect.clamp_ip(screen.get_rect())

            # Draw tooltip background and border
            pygame.draw.rect(screen, config.YELLOW,
                             tooltip_rect)  # Yellow background
            pygame.draw.rect(screen, config.BLACK, tooltip_rect,
                             1)  # Black border

            # Draw the text lines onto the tooltip background
            current_tooltip_y = tooltip_rect.top + 5  # Starting Y position for text lines
            for surf in tooltip_surfaces:
                screen.blit(surf,
                            (tooltip_rect.left + 5,
                             current_tooltip_y))  # Draw line with padding
                current_tooltip_y += surf.get_height(
                ) + line_spacing  # Move down for the next line

        pygame.display.flip()  # Update the full screen
        clock.tick(60)  # Limit frame rate to 60 FPS

    pygame.quit()  # Uninitialize Pygame modules when the main loop exits
    print("DEBUG: Pygame quit.")  # DEBUG PRINT

    # Signal the simulation thread to terminate if it's still running
    if simulation_running_event.is_set(
    ):  # Check if the simulation thread is expected to be running
        simulation_running_event.clear(
        )  # Signal the simulation thread to stop
        if simulation_thread and simulation_thread.is_alive(
        ):  # Check if the thread object exists and is alive
            simulation_continue_event.set(
            )  # Set continue event to unblock any waits in the thread
            print("DEBUG: Pygame quit, attempting to join simulation thread."
                  )  # DEBUG PRINT
            # Attempt to join the simulation thread to wait for it to finish
            simulation_thread.join(
                2.0)  # Wait for a maximum of 2 seconds for the thread to join
            if simulation_thread.is_alive():
                print(
                    "DEBUG: Simulation thread did not terminate gracefully within timeout."
                )
            else:
                print("DEBUG: Simulation thread joined successfully.")
        else:
            print(
                "DEBUG: Simulation thread was not running or already finished."
            )


# Entry point
# This __main__ block should remain in election.py as it's the primary entry point
# if __name__ == "__main__":
#    # Ensure DB tables are created when the script starts
#    import db_manager
#    db_manager.create_tables()
#    print(f"Database tables ensured in {config.DATABASE_FILE}") # Log DB file name

#    # Initialize Pygame and start the GUI thread
#    import gui
#    gui_thread = threading.Thread(target=gui.main_pygame_gui)
#    gui_thread.daemon = True # Allow the main program to exit even if this thread is running
#    gui_thread.start()

#    # The main thread keeps running to keep the GUI alive.
#    try:
#        while gui_thread.is_alive():
#            time.sleep(0.1) # Sleep briefly
#        print("GUI thread finished.")
#    except KeyboardInterrupt:
#        print("Keyboard interrupt received in main thread.")
#        pass
#    print("Main thread exiting.")
#    sys.exit()
