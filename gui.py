# gui.py
import pygame
import sys
import threading
import queue
import time
import traceback
import config
import data
import utils
import election
import db_manager  # Importa db_manager

# --- Controllo Esistenza Funzione Simulazione ---
if not hasattr(election, 'run_election_simulation'):  # pragma: no cover
    print("FATAL GUI ERROR: 'election' module does not have 'run_election_simulation' attribute.")
    sys.exit("Missing run_election_simulation in election module.")

# --- Variabili Globali GUI ---
STATUS_AREA, VISUAL_AREA, RESULTS_AREA, LOG_AREA, BUTTON_AREA = None, None, None, None, None
simulation_continue_event = threading.Event()
simulation_running_event = threading.Event()
utils.simulation_running_event = simulation_running_event
simulation_waiting_for_next = False
displayed_candidate_text_rects = []
current_simulation_attempt = 0
preselected_candidates_for_next_attempt = None
runoff_winner_for_next_attempt = None
log_line_height = 16
max_log_lines = 10

# --- Funzioni Helper GUI ---


def render_text(font, text, color, surface, x, y, antialias=True):
    """Renders text and returns height and bounding rect."""
    try:
        if not font:
            return 0, pygame.Rect(x, y, 0, 0)
        text_surface = font.render(str(text), antialias, color)
        int_x, int_y = int(x), int(y)
        rect = surface.blit(text_surface, (int_x, int_y))
        return text_surface.get_height(), rect
    except Exception as e_render:  # pragma: no cover
        print(f"ERROR rendering text '{str(text)[:50]}...': {e_render}")
        return 0, pygame.Rect(int(x), int(y), 0, 0)


def draw_button(surface, rect, color, text, font, text_color, enabled=True):
    """Draws a button and returns its rect."""
    try:
        if not isinstance(rect, pygame.Rect):
            print(f"ERROR: draw_button received invalid rect: {rect}")
            return rect
        button_color = color if enabled else config.GRAY
        text_color_actual = text_color if enabled else config.DARK_GRAY
        pygame.draw.rect(surface, button_color, rect)
        pygame.draw.rect(surface, config.WHITE, rect, 1)
        if font and text:
            text_surface = font.render(text, True, text_color_actual)
            text_rect = text_surface.get_rect(center=rect.center)
            surface.blit(text_surface, text_rect)
    except Exception as e_button:  # pragma: no cover
        print(f"ERROR drawing button '{text}': {e_button}")
    return rect

# --- Funzione per Calcolare Aree UI ---


def calculate_ui_areas(width, height, current_log_line_height):
    """Calcola le aree UI e il numero massimo di linee di log."""
    min_width = 300
    min_height = 400
    width = max(min_width, width)
    height = max(min_height, height)
    padding = 10
    status_rect = pygame.Rect(
        padding, padding, max(100, width - 2*padding), 80)
    visual_h = 150
    visual_rect = pygame.Rect(
        padding, status_rect.bottom + padding, max(100, width - 2*padding), visual_h)
    button_h = 50
    remaining_h = max(100, height - visual_rect.bottom -
                      (padding * 3) - button_h - padding)
    results_w = max(100, (width - (padding * 3)) // 2)
    log_w = max(100, width - (padding * 3) - results_w)
    results_rect = pygame.Rect(
        padding, visual_rect.bottom + padding, results_w, remaining_h)
    log_rect = pygame.Rect(results_rect.right + padding,
                           visual_rect.bottom + padding, log_w, remaining_h)
    button_y = max(results_rect.bottom, log_rect.bottom) + padding
    button_rect = pygame.Rect(padding, button_y, max(
        100, width - (padding * 2)), button_h)
    calculated_max_lines = 10
    if log_rect.height > 0 and current_log_line_height > 0:
        calculated_max_lines = max(
            1, (log_rect.height // current_log_line_height) - 2)
    return status_rect, visual_rect, results_rect, log_rect, button_rect, calculated_max_lines

# --- Funzione Principale GUI ---


def main_pygame_gui():
    global STATUS_AREA, VISUAL_AREA, RESULTS_AREA, LOG_AREA, BUTTON_AREA
    global simulation_waiting_for_next, displayed_candidate_text_rects, current_simulation_attempt
    global preselected_candidates_for_next_attempt, runoff_winner_for_next_attempt
    global log_line_height, max_log_lines

    pygame.init()
    try:
        pygame.font.init()
    except Exception as e_font_init:
        print(f"FATAL ERROR: Pygame font init failed: {e_font_init}")
        pygame.quit()
        sys.exit(1)

    infoObject = pygame.display.Info()
    screen_w_init = int(infoObject.current_w * 0.90)
    screen_h_init = int(infoObject.current_h * 0.90)
    try:
        screen = pygame.display.set_mode(
            (screen_w_init, screen_h_init), pygame.RESIZABLE | pygame.SRCALPHA)
    except Exception as e_screen:
        print(f"FATAL ERROR: Could not set display mode: {e_screen}")
        pygame.quit()
        sys.exit(1)
    pygame.display.set_caption(config.WINDOW_TITLE)

    font, small_font, title_font = None, None, None
    try:
        font = pygame.font.SysFont("DejaVu Sans", config.PIXEL_FONT_SIZE)
        small_font = pygame.font.SysFont(
            "DejaVu Sans", config.PIXEL_FONT_SIZE - 4)
        title_font = pygame.font.SysFont(
            "DejaVu Sans", config.PIXEL_FONT_SIZE + 2, bold=True)
        print("DEBUG: Custom font loaded.")
    except Exception:
        try:
            font = pygame.font.SysFont("monospace", config.PIXEL_FONT_SIZE)
            small_font = pygame.font.SysFont(
                "monospace", config.PIXEL_FONT_SIZE - 2)
            title_font = pygame.font.SysFont(
                "monospace", config.PIXEL_FONT_SIZE + 2, bold=True)
            print("DEBUG: Monospace font loaded.")
        except Exception as e_font_fallback:
            print(f"FATAL ERROR: Could not load any font: {e_font_fallback}")
            pygame.quit()
            sys.exit(1)
    if not font or not small_font or not title_font:
        print("FATAL ERROR: Fonts are None.")
        pygame.quit()
        sys.exit(1)

    clock = pygame.time.Clock()
    log_line_height = small_font.get_linesize()
    if log_line_height <= 0:
        log_line_height = 16

    SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
    STATUS_AREA, VISUAL_AREA, RESULTS_AREA, LOG_AREA, BUTTON_AREA, max_log_lines = calculate_ui_areas(
        SCREEN_WIDTH, SCREEN_HEIGHT, log_line_height)

    current_status_dict = {"attempt": 0, "phase": "Idle",
                           "round": 0, "status": "Ready", "governor": None}
    current_results_data = []
    log_messages = ["Welcome! Click 'Start Election'."]
    flag_state = None
    simulation_thread = None
    step_by_step_mode = config.STEP_BY_STEP_MODE_DEFAULT

    # --- CICLO PRINCIPALE ---
    running = True
    while running:
        try:
            mouse_pos = pygame.mouse.get_pos()
            tooltip_text = None

            # --- Gestione Eventi ---
            _start_rect_click, _next_rect_click, _quit_rect_click = None, None, None
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                if event.type == pygame.VIDEORESIZE:
                    SCREEN_WIDTH, SCREEN_HEIGHT = event.size
                    try:
                        screen = pygame.display.set_mode(
                            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SRCALPHA)
                        STATUS_AREA, VISUAL_AREA, RESULTS_AREA, LOG_AREA, BUTTON_AREA, max_log_lines = calculate_ui_areas(
                            SCREEN_WIDTH, SCREEN_HEIGHT, log_line_height)
                    except pygame.error as e_resize:
                        print(
                            f"Warning: Could not resize screen: {e_resize}")  # pragma: no cover

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Calcola Rects bottoni per click handling
                    if BUTTON_AREA:
                        BUTTON_WIDTH_CLICK, BUTTON_HEIGHT_CLICK = 150, BUTTON_AREA.height - 10
                        button_padding_click = 20
                        visible_buttons_count_click = 2 + \
                            (1 if step_by_step_mode else 0)
                        total_visible_buttons_width_click = BUTTON_WIDTH_CLICK * visible_buttons_count_click + \
                            button_padding_click * \
                            (visible_buttons_count_click -
                             1 if visible_buttons_count_click > 1 else 0)
                        button_start_x_click = BUTTON_AREA.left + \
                            max(0, (BUTTON_AREA.width -
                                total_visible_buttons_width_click) // 2)
                        button_y_pos_click = BUTTON_AREA.top + 5
                        _start_rect_click = pygame.Rect(
                            button_start_x_click, button_y_pos_click, BUTTON_WIDTH_CLICK, BUTTON_HEIGHT_CLICK)
                        _next_x_click = _start_rect_click.right + button_padding_click
                        _next_rect_click = pygame.Rect(
                            _next_x_click, button_y_pos_click, BUTTON_WIDTH_CLICK, BUTTON_HEIGHT_CLICK) if step_by_step_mode else None
                        _quit_x_click = _next_rect_click.right + \
                            button_padding_click if _next_rect_click else _start_rect_click.right + \
                            button_padding_click
                        _quit_rect_click = pygame.Rect(
                            _quit_x_click, button_y_pos_click, BUTTON_WIDTH_CLICK, BUTTON_HEIGHT_CLICK)

                        # Controllo Click
                        if _start_rect_click and _start_rect_click.collidepoint(event.pos):
                            # DEBUG
                            print("\nDEBUG: Start Button Click Detected!")
                            # DEBUG
                            print(
                                f"DEBUG: Checking simulation_running_event.is_set(): {simulation_running_event.is_set()}")
                            if not simulation_running_event.is_set():
                                # DEBUG
                                print(
                                    "DEBUG: Event not set, proceeding to start simulation...")
                                current_simulation_attempt += 1
                                if current_simulation_attempt > config.MAX_ELECTION_ATTEMPTS:
                                    utils.send_pygame_update(
                                        utils.UPDATE_TYPE_MESSAGE, "Max election attempts reached. Resetting.")
                                    current_simulation_attempt = 1
                                    preselected_candidates_for_next_attempt = None
                                    runoff_winner_for_next_attempt = None
                                current_status_dict = {
                                    "attempt": current_simulation_attempt, "phase": "Starting...", "round": 0, "status": "Initializing", "governor": None}
                                current_results_data = []
                                log_messages = [
                                    f"Attempt {current_simulation_attempt} starting..."]
                                flag_state = None
                                simulation_waiting_for_next = False
                                displayed_candidate_text_rects = []
                                simulation_continue_event.clear()
                                simulation_running_event.clear()
                                # DEBUG
                                print("DEBUG: Creating simulation thread...")
                                simulation_thread = threading.Thread(target=election.run_election_simulation, kwargs={
                                    'election_attempt': current_simulation_attempt, 'preselected_candidates_info_gui': preselected_candidates_for_next_attempt,
                                    'runoff_carryover_winner_name': runoff_winner_for_next_attempt, 'continue_event': simulation_continue_event,
                                    'running_event': simulation_running_event, 'step_by_step_mode': step_by_step_mode})
                                simulation_thread.daemon = True
                                simulation_thread.start()
                                # DEBUG
                                print("DEBUG: Simulation thread start() called.")
                                if not step_by_step_mode:
                                    simulation_continue_event.set()
                                preselected_candidates_for_next_attempt = None
                                runoff_winner_for_next_attempt = None
                            else:
                                # DEBUG
                                print(
                                    "DEBUG: Simulation already running (event was set), start button ignored.")

                        elif _next_rect_click and _next_rect_click.collidepoint(event.pos):
                            if simulation_running_event.is_set() and simulation_waiting_for_next:
                                # DEBUG
                                print(
                                    "DEBUG: Next Round Button Clicked and condition met.")
                                simulation_continue_event.set()
                                simulation_waiting_for_next = False
                            else:
                                # DEBUG
                                print(
                                    "DEBUG: Next Round Button Clicked but conditions not met.")
                        elif _quit_rect_click and _quit_rect_click.collidepoint(event.pos):
                            print("DEBUG: Quit Button Clicked.")  # DEBUG
                            running = False

            # --- Processa Coda Aggiornamenti ---
            while not utils.pygame_update_queue.empty():
                try:
                    update_type, update_data = utils.pygame_update_queue.get_nowait()
                    # print(f"DEBUG: Received update from queue: Type={update_type}") # DEBUG intensivo coda
                    if update_type == utils.UPDATE_TYPE_STATUS:
                        current_status_dict.update(update_data)
                        simulation_waiting_for_next = step_by_step_mode and current_status_dict.get(
                            "status") == "Waiting for Next Round"
                    elif update_type == utils.UPDATE_TYPE_RESULTS:
                        current_results_data = update_data.get(
                            "results", []) if isinstance(update_data, dict) else []
                    elif update_type == utils.UPDATE_TYPE_FLAG:
                        flag_state = update_data
                    elif update_type == utils.UPDATE_TYPE_MESSAGE:
                        log_messages.append(str(update_data))
                    elif update_type == utils.UPDATE_TYPE_WARNING:
                        log_messages.append(
                            f"\n--- WARNING --- \n{update_data}\n-------------")
                    elif update_type == utils.UPDATE_TYPE_ERROR:
                        log_messages.append(
                            f"\n!!! SIMULATION ERROR (Att {current_status_dict.get('attempt','?')}) !!!\n!!! {update_data} !!!\n")
                        current_status_dict["status"] = "Error"
                        simulation_running_event.clear()
                        simulation_waiting_for_next = False
                    elif update_type == utils.UPDATE_TYPE_COMPLETE:
                        current_status_dict["status"] = "Simulation Complete"
                        simulation_running_event.clear()
                        simulation_waiting_for_next = False
                        if isinstance(update_data, dict):
                            if update_data.get("elected"):
                                governor_name = update_data.get(
                                    "governor", "?")
                                current_status_dict["governor"] = governor_name
                                log_messages.append(
                                    f"\n*** GOVERNOR {governor_name.upper()} ELECTED! (Attempt {current_status_dict['attempt']}) ***\n")
                                current_simulation_attempt = 0
                                preselected_candidates_for_next_attempt = None
                            else:
                                log_messages.append(
                                    f"\n--- ELECTORAL DEADLOCK (Attempt {current_status_dict['attempt']}) ---")
                            if current_status_dict['attempt'] < config.MAX_ELECTION_ATTEMPTS:
                                log_messages.append(
                                    "   Ready for next attempt.")
                            else:
                                log_messages.append(
                                    f"   Max attempts ({config.MAX_ELECTION_ATTEMPTS}) reached.")
                                current_simulation_attempt = 0
                                preselected_candidates_for_next_attempt = None
                    elif update_type == utils.UPDATE_TYPE_KEY_ELECTORS:
                        if isinstance(update_data, list) and update_data:
                            log_messages.append(
                                "\n--- Key Electors Identified ---")
                            for i, ke_info in enumerate(update_data):
                                if i < 5:
                                    reasons_str = ", ".join(
                                        ke_info.get("reasons", ["N/A"]))
                                    log_messages.append(
                                        f"  ID: {ke_info.get('id', 'N/A')}, Reasons: {reasons_str}")
                                else:
                                    log_messages.append(
                                        f"  ...and {len(update_data) - 5} more.")
                                    break
                        # else: log messaggio 'nessun elettore chiave'? Opzionale
                    # Tronca log
                    if len(log_messages) > max_log_lines:
                        log_messages = log_messages[-max_log_lines:]
                except queue.Empty:
                    break
                except Exception as e_queue:
                    # Debug
                    print(
                        f"Error processing queue item {update_type}: {e_queue}")

            # --- Disegno Interfaccia ---
            screen.fill(config.BG_COLOR)

            # Aree (con controlli base per esistenza)
            if STATUS_AREA:
                try:
                    # Semplice rect senza Surface
                    pygame.draw.rect(screen, (64, 64, 64, 192), STATUS_AREA)
                    pygame.draw.rect(screen, config.WHITE, STATUS_AREA, 1)
                    status_y = STATUS_AREA.top + 5
                    status_x_left = STATUS_AREA.left + 10
                    status_x_right = STATUS_AREA.right - 250
                    h1, _ = render_text(
                        font, f"Attempt: {current_status_dict.get('attempt', '-')}/{config.MAX_ELECTION_ATTEMPTS}", config.WHITE, screen, status_x_left, status_y)
                    h2, _ = render_text(
                        font, f"Phase: {current_status_dict.get('phase', 'N/A')}", config.WHITE, screen, status_x_left, status_y + h1 + 2)
                    render_text(font, f"Round: {current_status_dict.get('round', '-')}",
                                config.WHITE, screen, status_x_right, status_y)
                    status_text_val = current_status_dict.get("status", "")
                    render_text(font, f"Status: {status_text_val}", config.WHITE,
                                screen, status_x_left, status_y + h1 + h2 + 4)
                    if current_status_dict.get("governor"):
                        render_text(
                            font, f"Governor: {current_status_dict['governor']}", config.GREEN, screen, status_x_right, status_y + h1 + 2)
                    mode_text = "Mode: Step-by-Step" if step_by_step_mode else "Mode: Continuous"
                    render_text(
                        small_font, mode_text, config.WHITE, screen, status_x_left, STATUS_AREA.bottom - small_font.get_linesize() - 5)
                except Exception as e:
                    print(
                        f"Error drawing Status Area: {e}")  # pragma: no cover

            if VISUAL_AREA:
                try:
                    pygame.draw.rect(screen, (32, 32, 32, 160), VISUAL_AREA)
                    pygame.draw.rect(screen, config.WHITE, VISUAL_AREA, 1)
                    displayed_candidate_text_rects.clear()
                    display_items_visual = current_results_data[:12]
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
                            if text_y_visual + row_height_visual < VISUAL_AREA.bottom - 5:
                                _, text_rect_visual = render_text(
                                    small_font, cand_name_visual, text_color_visual, screen, text_x_visual, text_y_visual)
                                displayed_candidate_text_rects.append(
                                    (text_rect_visual, item))
                                if text_rect_visual.collidepoint(mouse_pos):
                                    attrs_visual = item.get(
                                        'attributes', {})
                                    attrs_str_visual = ", ".join(
                                        [f"{k.replace('_',' ').title()}: {v}" for k, v in attrs_visual.items()])
                                    tooltip_text = (f"{cand_name_visual} ({item.get('party_id','N/A')})\n" +
                                                    f"Age: {item.get('age','N/A')}, Gender: {gender_visual.title()}\n" + f"Attributes: {attrs_str_visual if attrs_str_visual else 'N/A'}")
                except Exception as e:
                    print(
                        f"Error drawing Visual Area: {e}")  # pragma: no cover

            if RESULTS_AREA:
                try:
                    pygame.draw.rect(screen, (48, 48, 48, 192), RESULTS_AREA)
                    pygame.draw.rect(screen, config.WHITE, RESULTS_AREA, 1)
                    render_text(title_font, "Latest Results:", config.WHITE,
                                screen, RESULTS_AREA.left + 10, RESULTS_AREA.top + 5)
                    if current_results_data:
                        relevant_results = [item for item in current_results_data if isinstance(
                            item, dict) and item.get('votes', 0) > 0]
                        max_votes = max(
                            item['votes'] for item in relevant_results) if relevant_results else 1
                        bar_area_width_results = RESULTS_AREA.width - 20
                        bar_height_results = 15
                        bar_spacing_results = 5
                        bar_start_y_results = RESULTS_AREA.top + 5 + title_font.get_linesize() + 10
                        total_votes_this_round = sum(
                            item['votes'] for item in relevant_results) if relevant_results else 0
                        for i, item_res in enumerate(sorted(relevant_results, key=lambda x: x.get('votes', 0), reverse=True)):
                            if bar_start_y_results + i * (bar_height_results + bar_spacing_results) + bar_height_results > RESULTS_AREA.bottom - 5:
                                render_text(small_font, "...", config.WHITE, screen, RESULTS_AREA.left +
                                            10, bar_start_y_results + i * (bar_height_results + bar_spacing_results))
                            break
                            cand_name_res, votes_res = item_res['name'], item_res['votes']
                            is_overall_elected = (current_status_dict.get(
                                "governor") == cand_name_res and current_status_dict.get("status") == "Simulation Complete")
                            vote_percentage = (
                                votes_res / total_votes_this_round * 100) if total_votes_this_round > 0 else 0
                            bar_width_val = max(
                                1, (votes_res / max_votes) * bar_area_width_results) if votes_res > 0 and max_votes > 0 else 0
                            bar_color_val = config.GREEN if is_overall_elected else config.GRAY
                            bar_rect_item = pygame.Rect(RESULTS_AREA.left + 10, bar_start_y_results + i * (
                                bar_height_results + bar_spacing_results), bar_width_val, bar_height_results)
                            pygame.draw.rect(
                                screen, bar_color_val, bar_rect_item)
                            pygame.draw.rect(
                                screen, config.WHITE, bar_rect_item, 1)
                            name_text_res = f"{cand_name_res}: {votes_res} ({vote_percentage:.1f}%)"
                            name_surface_res = small_font.render(
                                name_text_res, True, config.WHITE)
                            text_x_res = bar_rect_item.left + 5
                            text_y_res = bar_rect_item.centery - name_surface_res.get_height() // 2
                            if bar_width_val < name_surface_res.get_width() + 10:
                                text_x_res = bar_rect_item.right + 5
                            text_x_res = min(
                                text_x_res, RESULTS_AREA.right - 10 - name_surface_res.get_width())
                            screen.blit(name_surface_res,
                                        (text_x_res, text_y_res))
                except Exception as e:
                    print(
                        f"Error drawing Results Area: {e}")  # pragma: no cover

            if LOG_AREA:
                try:
                    pygame.draw.rect(screen, (48, 48, 48, 192), LOG_AREA)
                    pygame.draw.rect(screen, config.WHITE, LOG_AREA, 1)
                    render_text(title_font, "Log:", config.WHITE,
                                screen, LOG_AREA.left + 10, LOG_AREA.top + 5)
                    log_y_start = LOG_AREA.top + 5 + title_font.get_linesize() + 5
                    # Disegna messaggi dal basso verso l'alto (o alto verso basso, ma solo i più recenti)
                    start_index = max(0, len(log_messages) - max_log_lines)
                    for i, msg_log in enumerate(log_messages[start_index:]):
                        current_y = log_y_start + i * log_line_height
                        if current_y + log_line_height > LOG_AREA.bottom - 5:
                            break  # Non entra più

                        # Word wrap semplice (potrebbe essere migliorato)
                        # Converti a str per sicurezza
                        words = str(msg_log).split(' ')
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

                        # Renderizza linee wrappate
                        temp_y_log = current_y
                        for line_log in lines_for_msg:
                            if temp_y_log + log_line_height <= LOG_AREA.bottom - 5:
                                render_text(small_font, line_log.strip(
                                ), config.WHITE, screen, LOG_AREA.left + 10, temp_y_log)
                                temp_y_log += log_line_height
                            else:
                                break  # Spazio finito nel box per questo messaggio
                except Exception as e:
                    print(f"Error drawing Log Area: {e}")  # pragma: no cover

            # Button Area
            # Resetta per disegno
            start_button_rect, next_round_button_rect, quit_button_rect = None, None, None
            if BUTTON_AREA:
                try:
                    BUTTON_WIDTH, BUTTON_HEIGHT = 150, BUTTON_AREA.height - 10
                    button_padding = 20
                    visible_buttons_count = 2 + (1 if step_by_step_mode else 0)
                    total_visible_buttons_width = BUTTON_WIDTH * visible_buttons_count + \
                        button_padding * \
                        (visible_buttons_count -
                         1 if visible_buttons_count > 1 else 0)
                    button_start_x = BUTTON_AREA.left + \
                        max(0, (BUTTON_AREA.width - total_visible_buttons_width) // 2)
                    button_y_pos = BUTTON_AREA.top + 5

                    # Disegna Start
                    start_button_enabled = not simulation_running_event.is_set()
                    start_button_rect = pygame.Rect(
                        button_start_x, button_y_pos, BUTTON_WIDTH, BUTTON_HEIGHT)
                    draw_button(screen, start_button_rect, config.GREEN, "Start Election",
                                font, config.WHITE, enabled=start_button_enabled)
                    current_button_x_draw = start_button_rect.right + button_padding

                    # Disegna Next
                    if step_by_step_mode:
                        next_round_button_enabled = simulation_running_event.is_set(
                        ) and simulation_waiting_for_next
                        next_round_button_rect = pygame.Rect(
                            current_button_x_draw, button_y_pos, BUTTON_WIDTH, BUTTON_HEIGHT)
                        draw_button(screen, next_round_button_rect, config.BLUE, "Next Round",
                                    font, config.WHITE, enabled=next_round_button_enabled)
                        current_button_x_draw = next_round_button_rect.right + button_padding

                    # Disegna Quit
                    quit_button_rect = pygame.Rect(
                        current_button_x_draw, button_y_pos, BUTTON_WIDTH, BUTTON_HEIGHT)
                    draw_button(screen, quit_button_rect, config.RED,
                                "Quit", font, config.WHITE, enabled=True)
                except Exception as e:
                    print(
                        f"Error drawing Button Area: {e}")  # pragma: no cover

            # Tooltip
            if tooltip_text:
                try:
                    # ... (Codice disegno tooltip come prima) ...
                    pass
                except Exception as e:
                    print(f"Error drawing Tooltip: {e}")  # pragma: no cover

            pygame.display.flip()
            clock.tick(30)

        # Gestione Errore Loop Principale
        except Exception as loop_error:  # pragma: no cover
            print("\n" + "="*30 +
                  "\n!!! UNHANDLED ERROR IN MAIN GUI LOOP !!!\n" + "="*30)
            print(f"ERROR TYPE: {type(loop_error).__name__}")
            print(f"ERROR DETAILS: {loop_error}")
            print("-" * 30 + " TRACEBACK " + "-" * 30)
            traceback.print_exc()
            print("="*70 + "\n")
            running = False

    # --- Pulizia Uscita ---
    if simulation_running_event.is_set():
        print("GUI closing, signaling simulation thread to stop...")
        simulation_running_event.clear()
        if simulation_thread and simulation_thread.is_alive():
            simulation_continue_event.set()
            simulation_thread.join(2.0)
            if simulation_thread.is_alive():
                print("Warning: Simulation thread did not terminate gracefully.")
            else:
                print("DEBUG: Simulation thread joined.")
    pygame.quit()
    print("Pygame GUI closed.")


# --- Punto di Ingresso Principale ---
if __name__ == "__main__":
    print("Application starting...")
    try:
        db_manager.create_tables()
        print(f"Database tables ensured in '{config.DATABASE_FILE}'")
    except Exception as e_db_init:
        print(f"FATAL ERROR: Could not ensure database tables: {e_db_init}")
        sys.exit(1)  # pragma: no cover
    main_pygame_gui()
    print("Application finished.")
    sys.exit(0)
