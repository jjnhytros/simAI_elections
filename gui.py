# gui.py
import pygame
import sys
import threading
import queue
import time

# Imports da altri moduli del progetto (assoluti)
import config
import data
import utils
import election  # Import election module
import db_manager  # Import db_manager per create_tables

# --- Add check here ---
if not hasattr(election, 'run_election_simulation'):
    print(
        "FATAL GUI ERROR: 'election' module does not have 'run_election_simulation' attribute."
    )
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
simulation_running_event = threading.Event()  # Usato in utils.py e election.py
# Rendi accessibile globalmente se necessario per utils
utils.simulation_running_event = simulation_running_event

# Flag per indicare se la simulazione è in attesa del "prossimo round" in modalità passo-passo
simulation_waiting_for_next = False

displayed_candidate_text_rects = []
current_simulation_attempt = 0  # Tiene traccia del tentativo corrente


def render_text(font, text, color, surface, x, y, antialias=True):
    text_surface = font.render(str(text), antialias, color)
    rect = surface.blit(text_surface, (x, y))
    return text_surface.get_height(), rect


def draw_button(surface, rect, color, text, font, text_color, enabled=True):
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
    global STATUS_AREA, VISUAL_AREA, RESULTS_AREA, LOG_AREA, BUTTON_AREA
    global simulation_waiting_for_next, displayed_candidate_text_rects, current_simulation_attempt

    pygame.init()
    infoObject = pygame.display.Info()
    SCREEN_WIDTH = int(infoObject.current_w *
                       0.95)  # Usa 95% per evitare problemi di fullscreen
    SCREEN_HEIGHT = int(infoObject.current_h * 0.95)
    # screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SRCALPHA)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                                     pygame.RESIZABLE | pygame.SRCALPHA)

    pygame.display.set_caption(config.WINDOW_TITLE)

    try:
        font = pygame.font.SysFont("DejaVu Sans", config.PIXEL_FONT_SIZE)
        small_font = pygame.font.SysFont("DejaVu Sans",
                                         config.PIXEL_FONT_SIZE - 4)
        title_font = pygame.font.SysFont("DejaVu Sans",
                                         config.PIXEL_FONT_SIZE + 2,
                                         bold=True)
    except pygame.error:
        font = pygame.font.SysFont("monospace", config.PIXEL_FONT_SIZE)
        small_font = pygame.font.SysFont("monospace",
                                         config.PIXEL_FONT_SIZE - 2)
        title_font = pygame.font.SysFont("monospace",
                                         config.PIXEL_FONT_SIZE + 2,
                                         bold=True)
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "Warning: DejaVu Sans font not found, using monospace.")

    clock = pygame.time.Clock()

    STATUS_AREA = pygame.Rect(20, 20, SCREEN_WIDTH - 40, 80)
    VISUAL_AREA_HEIGHT = 150
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

    current_status_dict = {
        "attempt": 0,
        "phase": "Initializing...",
        "round": 0,
        "status": "Idle",
        "governor": None
    }
    current_results_data = [
    ]  # Lista di dizionari per i candidati e i loro voti
    log_messages = ["Welcome to simAI Elections!"]

    log_line_height = small_font.get_linesize()
    if log_line_height <= 0:
        log_line_height = config.PIXEL_FONT_SIZE - 2
    max_log_lines = (
        LOG_AREA.height // log_line_height
    ) - 2 if LOG_AREA.height > 0 and log_line_height > 0 else 10

    flag_state = None
    simulation_thread = None
    step_by_step_mode = config.STEP_BY_STEP_MODE_DEFAULT

    # Per passare i candidati tra tentativi
    preselected_candidates_for_next_attempt = None
    # Per passare il vincitore di un eventuale runoff
    runoff_winner_for_next_attempt = None

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        tooltip_text = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Buttons
                    if 'start_button_rect' in locals(
                    ) and start_button_rect.collidepoint(event.pos):
                        if not simulation_running_event.is_set():
                            current_simulation_attempt += 1
                            if current_simulation_attempt > config.MAX_ELECTION_ATTEMPTS:
                                utils.send_pygame_update(
                                    utils.UPDATE_TYPE_MESSAGE,
                                    "Max election attempts reached. Resetting."
                                )
                                current_simulation_attempt = 1
                                # Resetta per un nuovo ciclo completo
                                preselected_candidates_for_next_attempt = None
                                runoff_winner_for_next_attempt = None

                            current_status_dict = {
                                "attempt": current_simulation_attempt,
                                "phase": "Starting...",
                                "round": 0,
                                "status": "Initializing",
                                "governor": None
                            }
                            current_results_data = []
                            log_messages = [
                                f"Attempt {current_simulation_attempt} starting..."
                            ]
                            flag_state = None
                            simulation_waiting_for_next = False
                            displayed_candidate_text_rects = []

                            simulation_continue_event.clear()
                            simulation_running_event.clear(
                            )  # Assicurati sia clear prima di start

                            simulation_thread = threading.Thread(
                                target=election.run_election_simulation,
                                kwargs={
                                    'election_attempt':
                                    current_simulation_attempt,
                                    'preselected_candidates_info_gui':
                                    preselected_candidates_for_next_attempt,
                                    'runoff_carryover_winner_name':
                                    runoff_winner_for_next_attempt,
                                    'continue_event':
                                    simulation_continue_event,
                                    'running_event': simulation_running_event,
                                    'step_by_step_mode': step_by_step_mode
                                })
                            simulation_thread.daemon = True
                            simulation_thread.start()
                            # simulation_running_event viene settato da run_election_simulation
                            if not step_by_step_mode:
                                simulation_continue_event.set()
                            preselected_candidates_for_next_attempt = None  # Resetta dopo averlo passato
                            runoff_winner_for_next_attempt = None

                    if step_by_step_mode and 'next_round_button_rect' in locals(
                    ) and next_round_button_rect.collidepoint(event.pos):
                        if simulation_running_event.is_set(
                        ) and simulation_waiting_for_next:
                            simulation_continue_event.set()
                            simulation_waiting_for_next = False

                    if 'quit_button_rect' in locals(
                    ) and quit_button_rect.collidepoint(event.pos):
                        running = False

                    # Click su nomi candidati per tooltip/info (logica spostata in fase di disegno per hover)

        # Process updates from simulation thread
        while not utils.pygame_update_queue.empty():
            try:
                update_type, update_data = utils.pygame_update_queue.get_nowait(
                )
            except queue.Empty:
                break

            if update_type == utils.UPDATE_TYPE_MESSAGE:
                log_messages.append(str(update_data))
            elif update_type == utils.UPDATE_TYPE_STATUS:
                current_status_dict.update(update_data)
                if step_by_step_mode and current_status_dict.get(
                        "status") == "Waiting for Next Round":
                    simulation_waiting_for_next = True
                else:
                    simulation_waiting_for_next = False  # Anche se diventa "Error" o altro
            elif update_type == utils.UPDATE_TYPE_RESULTS:
                if update_data and "results" in update_data:
                    current_results_data = update_data["results"]
            elif update_type == utils.UPDATE_TYPE_FLAG:
                flag_state = update_data
            elif update_type == utils.UPDATE_TYPE_COMPLETE:
                current_status_dict["status"] = "Simulation Complete"
                simulation_running_event.clear(
                )  # La simulazione (o tentativo) è finita
                simulation_waiting_for_next = False
                if update_data:
                    if update_data.get("elected"):
                        governor_name = update_data.get("governor", "Unknown")
                        current_status_dict["governor"] = governor_name
                        log_messages.append(
                            f"\n*** GOVERNOR {governor_name.upper()} ELECTED! (Attempt {current_status_dict['attempt']}) ***\n"
                        )
                        current_simulation_attempt = 0  # Resetta per un nuovo ciclo di elezioni
                        preselected_candidates_for_next_attempt = None
                    else:  # Deadlock for this attempt
                        log_messages.append(
                            f"\n--- ELECTORAL DEADLOCK (Attempt {current_status_dict['attempt']}) ---"
                        )
                        # Prepara per il prossimo tentativo, se ce ne sono ancora
                        if current_status_dict[
                                'attempt'] < config.MAX_ELECTION_ATTEMPTS:
                            log_messages.append("   Ready for next attempt.")
                            # Potresti voler passare i candidati attuali al prossimo tentativo
                            # preselected_candidates_for_next_attempt = copy.deepcopy(current_results_data) # o current_candidates_info dalla simulazione
                        else:
                            log_messages.append(
                                f"   Max attempts ({config.MAX_ELECTION_ATTEMPTS}) reached. No Governor elected."
                            )
                            current_simulation_attempt = 0  # Resetta
                            preselected_candidates_for_next_attempt = None

            elif update_type == utils.UPDATE_TYPE_ERROR:
                log_messages.append(
                    f"\n!!! SIMULATION ERROR (Attempt {current_status_dict.get('attempt','N/A')}) !!!\n!!! {update_data} !!!\n"
                )
                current_status_dict["status"] = "Error"
                simulation_running_event.clear()
                simulation_waiting_for_next = False

            if len(log_messages) > max_log_lines:
                log_messages = log_messages[-max_log_lines:]

        # Drawing
        screen.fill(config.BG_COLOR)

        # Status Area
        status_bg_surface = pygame.Surface(STATUS_AREA.size, pygame.SRCALPHA)
        status_bg_surface.fill((64, 64, 64, 192))
        screen.blit(status_bg_surface, STATUS_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, STATUS_AREA, 1)
        status_y = STATUS_AREA.top + 5
        status_x_left = STATUS_AREA.left + 10
        status_x_right = STATUS_AREA.right - 250  # Spazio per status e governatore

        h1, _ = render_text(
            font,
            f"Attempt: {current_status_dict.get('attempt', '-')}/{config.MAX_ELECTION_ATTEMPTS}",
            config.WHITE, screen, status_x_left, status_y)
        h2, _ = render_text(
            font, f"Phase: {current_status_dict.get('phase', 'N/A')}",
            config.WHITE, screen, status_x_left, status_y + h1 + 2)
        render_text(font, f"Round: {current_status_dict.get('round', '-')}",
                    config.WHITE, screen, status_x_right, status_y)
        status_text_val = current_status_dict.get("status", "")
        render_text(font, f"Status: {status_text_val}", config.WHITE, screen,
                    status_x_left, status_y + h1 + h2 + 4)
        if current_status_dict.get("governor"):
            render_text(font, f"Governor: {current_status_dict['governor']}",
                        config.GREEN, screen, status_x_right,
                        status_y + h1 + 2)

        mode_text = "Mode: Step-by-Step" if step_by_step_mode else "Mode: Continuous"
        render_text(small_font, mode_text, config.WHITE, screen, status_x_left,
                    STATUS_AREA.bottom - small_font.get_linesize() - 5)

        # Visual Area
        visual_bg_surface = pygame.Surface(VISUAL_AREA.size, pygame.SRCALPHA)
        visual_bg_surface.fill((32, 32, 32, 160))
        screen.blit(visual_bg_surface, VISUAL_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, VISUAL_AREA, 1)
        displayed_candidate_text_rects.clear()

        display_items_visual = current_results_data[:
                                                    12]  # Mostra fino a 12 candidati
        if display_items_visual:
            num_columns = 3
            col_width = VISUAL_AREA.width // num_columns
            row_height_visual = small_font.get_linesize() + 4
            start_x_visual, start_y_visual = VISUAL_AREA.left + 10, VISUAL_AREA.top + 10

            for i, item in enumerate(display_items_visual):
                cand_name_visual = item.get('name', 'N/A')
                gender_visual = item.get('gender', 'unknown')
                text_color_visual = config.PINK if gender_visual == "female" else config.LIGHT_BLUE if gender_visual == "male" else config.WHITE

                col_idx = i % num_columns
                row_idx = i // num_columns
                text_x_visual = start_x_visual + col_idx * col_width
                text_y_visual = start_y_visual + row_idx * row_height_visual

                if text_y_visual + row_height_visual < VISUAL_AREA.bottom - 5:  # Check bounds
                    _, text_rect_visual = render_text(small_font,
                                                      cand_name_visual,
                                                      text_color_visual,
                                                      screen, text_x_visual,
                                                      text_y_visual)
                    displayed_candidate_text_rects.append(
                        (text_rect_visual, item))
                    if text_rect_visual.collidepoint(mouse_pos):
                        attrs_visual = item.get('attributes', {})
                        attrs_str_visual = ", ".join([
                            f"{k.replace('_',' ').title()}: {v}"
                            for k, v in attrs_visual.items()
                        ])
                        tooltip_text = (
                            f"{cand_name_visual} ({item.get('party_id','N/A')})\n"
                            f"Age: {item.get('age','N/A')}, Gender: {gender_visual.title()}\n"
                            f"Attributes: {attrs_str_visual if attrs_str_visual else 'N/A'}"
                        )

        # Results Area
        results_bg_surface = pygame.Surface(RESULTS_AREA.size, pygame.SRCALPHA)
        results_bg_surface.fill((48, 48, 48, 192))
        screen.blit(results_bg_surface, RESULTS_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, RESULTS_AREA, 1)
        render_text(title_font, "Latest Results:", config.WHITE, screen,
                    RESULTS_AREA.left + 10, RESULTS_AREA.top + 5)

        if current_results_data:
            relevant_results = [
                item for item in current_results_data
                if item.get('votes', 0) > 0
            ]
            max_votes = max(
                item['votes']
                for item in relevant_results) if relevant_results else 1
            bar_area_width_results = RESULTS_AREA.width - 20
            bar_height_results = 15
            bar_spacing_results = 5
            bar_start_y_results = RESULTS_AREA.top + 5 + title_font.get_linesize(
            ) + 10
            total_votes_this_round = sum(
                item['votes']
                for item in relevant_results) if relevant_results else 0

            for i, item_res in enumerate(
                    sorted(relevant_results,
                           key=lambda x: x.get('votes', 0),
                           reverse=True)):
                if bar_start_y_results + i * (
                        bar_height_results + bar_spacing_results
                ) + bar_height_results > RESULTS_AREA.bottom - 5:
                    render_text(
                        small_font, "...", config.WHITE, screen,
                        RESULTS_AREA.left + 10, bar_start_y_results + i *
                        (bar_height_results + bar_spacing_results))
                    break

                cand_name_res, votes_res = item_res['name'], item_res['votes']
                is_overall_elected = (current_status_dict.get("governor")
                                      == cand_name_res
                                      and current_status_dict.get("status")
                                      == "Simulation Complete")

                vote_percentage = (votes_res / total_votes_this_round *
                                   100) if total_votes_this_round > 0 else 0
                bar_width_val = max(1, (votes_res / max_votes) *
                                    bar_area_width_results
                                    ) if votes_res > 0 and max_votes > 0 else 0
                bar_color_val = config.GREEN if is_overall_elected else config.GRAY

                bar_rect_item = pygame.Rect(
                    RESULTS_AREA.left + 10, bar_start_y_results + i *
                    (bar_height_results + bar_spacing_results), bar_width_val,
                    bar_height_results)
                pygame.draw.rect(screen, bar_color_val, bar_rect_item)
                pygame.draw.rect(screen, config.WHITE, bar_rect_item, 1)

                name_text_res = f"{cand_name_res}: {votes_res} ({vote_percentage:.1f}%)"
                name_surface_res = small_font.render(name_text_res, True,
                                                     config.WHITE)
                text_x_res = bar_rect_item.left + 5
                if bar_width_val < name_surface_res.get_width() + 10:
                    text_x_res = bar_rect_item.right + 5
                text_x_res = min(
                    text_x_res,
                    RESULTS_AREA.right - 10 - name_surface_res.get_width())
                screen.blit(name_surface_res,
                            (text_x_res, bar_rect_item.centery -
                             name_surface_res.get_height() // 2))

        # Log Area
        log_bg_surface = pygame.Surface(LOG_AREA.size, pygame.SRCALPHA)
        log_bg_surface.fill((48, 48, 48, 192))
        screen.blit(log_bg_surface, LOG_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, LOG_AREA, 1)
        render_text(title_font, "Log:", config.WHITE, screen,
                    LOG_AREA.left + 10, LOG_AREA.top + 5)

        log_y_start = LOG_AREA.top + 5 + title_font.get_linesize() + 5
        for msg_idx, msg_log in enumerate(
                reversed(log_messages)):  # Show newest first
            if log_y_start + msg_idx * log_line_height > LOG_AREA.bottom - 5 - log_line_height:
                break  # Stop if no more space

            # Simple word wrap
            words = msg_log.split(' ')
            lines_for_msg = []
            current_line_log = ""
            max_width_log = LOG_AREA.width - 20

            for word_log in words:
                test_line_log = current_line_log + word_log + " "
                if small_font.size(test_line_log)[0] < max_width_log:
                    current_line_log = test_line_log
                else:
                    lines_for_msg.append(current_line_log)
                    current_line_log = word_log + " "
            lines_for_msg.append(current_line_log)

            # Initial y for this message block
            temp_y_log = log_y_start + msg_idx * log_line_height
            for line_idx, line_log in enumerate(lines_for_msg):
                if temp_y_log + line_idx * log_line_height > LOG_AREA.bottom - 5 - log_line_height:
                    break
                render_text(small_font, line_log.strip(), config.WHITE, screen,
                            LOG_AREA.left + 10,
                            temp_y_log + line_idx * log_line_height)

        # Flag Area (placeholder)
        flag_area_rect = pygame.Rect(STATUS_AREA.right - 70,
                                     STATUS_AREA.top + 5, 60,
                                     STATUS_AREA.height - 10)
        # ... (disegno bandiera come prima) ...

        # Button Area
        BUTTON_WIDTH, BUTTON_HEIGHT = 150, BUTTON_AREA.height - 10
        button_padding = 20

        buttons_to_draw = []
        start_button_rect = pygame.Rect(0, 0, 0, 0)  # Init
        next_round_button_rect = pygame.Rect(0, 0, 0, 0)  # Init

        start_button_enabled = not simulation_running_event.is_set()
        buttons_to_draw.append(
            lambda surf: draw_button(surf,
                                     start_button_rect,
                                     config.GREEN,
                                     "Start Election",
                                     font,
                                     config.WHITE,
                                     enabled=start_button_enabled))

        if step_by_step_mode:
            next_round_button_enabled = simulation_running_event.is_set(
            ) and simulation_waiting_for_next
            buttons_to_draw.append(
                lambda surf: draw_button(surf,
                                         next_round_button_rect,
                                         config.BLUE,
                                         "Next Round",
                                         font,
                                         config.WHITE,
                                         enabled=next_round_button_enabled))

        buttons_to_draw.append(lambda surf: draw_button(surf,
                                                        quit_button_rect,
                                                        config.RED,
                                                        "Quit",
                                                        font,
                                                        config.WHITE,
                                                        enabled=True))

        total_buttons_width = BUTTON_WIDTH * len(
            buttons_to_draw) + button_padding * (
                len(buttons_to_draw) - 1 if len(buttons_to_draw) > 1 else 0)
        button_start_x = BUTTON_AREA.left + (BUTTON_AREA.width -
                                             total_buttons_width) // 2
        button_y_pos = BUTTON_AREA.top + 5

        current_button_x = button_start_x
        # Assegna rects e disegna
        start_button_rect = pygame.Rect(current_button_x, button_y_pos,
                                        BUTTON_WIDTH, BUTTON_HEIGHT)
        draw_button(screen,
                    start_button_rect,
                    config.GREEN,
                    "Start Election",
                    font,
                    config.WHITE,
                    enabled=start_button_enabled)
        current_button_x += BUTTON_WIDTH + button_padding

        if step_by_step_mode:
            next_round_button_rect = pygame.Rect(current_button_x,
                                                 button_y_pos, BUTTON_WIDTH,
                                                 BUTTON_HEIGHT)
            next_round_button_enabled = simulation_running_event.is_set(
            ) and simulation_waiting_for_next
            draw_button(screen,
                        next_round_button_rect,
                        config.BLUE,
                        "Next Round",
                        font,
                        config.WHITE,
                        enabled=next_round_button_enabled)
            current_button_x += BUTTON_WIDTH + button_padding

        quit_button_rect = pygame.Rect(current_button_x, button_y_pos,
                                       BUTTON_WIDTH, BUTTON_HEIGHT)
        draw_button(screen,
                    quit_button_rect,
                    config.RED,
                    "Quit",
                    font,
                    config.WHITE,
                    enabled=True)

        # Tooltip
        if tooltip_text:
            tooltip_lines = tooltip_text.split('\n')
            max_tt_width = 0
            tt_surfaces = []
            total_tt_height = 0
            for line in tooltip_lines:
                surf = small_font.render(line, True, config.BLACK)
                tt_surfaces.append(surf)
                max_tt_width = max(max_tt_width, surf.get_width())
                total_tt_height += surf.get_height() + 2

            tt_rect = pygame.Rect(0, 0, max_tt_width + 10, total_tt_height + 5)
            tt_rect.topleft = (mouse_pos[0] + 15, mouse_pos[1] + 10)
            tt_rect.clamp_ip(screen.get_rect())  # Keep in screen
            pygame.draw.rect(screen, config.YELLOW, tt_rect)
            pygame.draw.rect(screen, config.BLACK, tt_rect, 1)
            current_tt_y = tt_rect.top + 5
            for surf in tt_surfaces:
                screen.blit(surf, (tt_rect.left + 5, current_tt_y))
                current_tt_y += surf.get_height() + 2

        pygame.display.flip()
        clock.tick(30)  # FPS

    # Fine del ciclo while running
    if simulation_running_event.is_set():
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "GUI is closing, signaling simulation to stop.")
        simulation_running_event.clear(
        )  # Segnala al thread di simulazione di terminare
        if simulation_thread and simulation_thread.is_alive():
            simulation_continue_event.set()  # Sblocca eventuali attese
            simulation_thread.join(2.0)  # Attendi max 2 secondi
            if simulation_thread.is_alive():
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    "Warning: Simulation thread did not terminate gracefully.")

    pygame.quit()
    print("Pygame GUI closed.")
    # sys.exit() # Non necessario se questo è il thread principale che termina


if __name__ == "__main__":
    print("Application starting...")
    db_manager.create_tables()  # Assicura che le tabelle DB esistano
    print(f"Database tables ensured in {config.DATABASE_FILE}")

    # Avvia la GUI principale
    main_pygame_gui()

    print("Application finished.")
    sys.exit()
