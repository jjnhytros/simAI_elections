import pygame
import sys
import threading
import queue
import time

# Imports da altri moduli del progetto (assoluti)
import config
import data  # Import necessario per accedere alle liste nomi in caso di necessità future
import utils
import election

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
# Questo ora potrebbe non essere più necessario se non rendiamo i nomi cliccabili,
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

    pygame.init()

    infoObject = pygame.display.Info()
    SCREEN_WIDTH = infoObject.current_w
    SCREEN_HEIGHT = infoObject.current_h
    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN
        | pygame.SRCALPHA)  # Aggiunto SRCALPHA per trasparenza se necessaria

    pygame.display.set_caption(config.WINDOW_TITLE)

    try:
        # Usiamo un font più leggibile se disponibile
        font = pygame.font.SysFont("DejaVu Sans", config.PIXEL_FONT_SIZE)
        small_font = pygame.font.SysFont(
            "DejaVu Sans", config.PIXEL_FONT_SIZE - 4)  # Ridotto un po' di più
        title_font = pygame.font.SysFont("DejaVu Sans",
                                         config.PIXEL_FONT_SIZE + 2,
                                         bold=True)
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
                            simulation_running_event.set()
                            if not step_by_step_mode:
                                simulation_continue_event.set()

                    if step_by_step_mode and 'next_round_button_rect' in locals(
                    ) and next_round_button_rect.collidepoint(event.pos):
                        if simulation_running_event.is_set(
                        ) and simulation_waiting_for_next:
                            simulation_continue_event.set()
                            # Resetta subito in attesa della prossima attesa
                            simulation_waiting_for_next = False

                    if 'quit_button_rect' in locals(
                    ) and quit_button_rect.collidepoint(event.pos):
                        running = False

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
        while not utils.pygame_update_queue.empty():
            try:
                update_type, update_data = (
                    utils.pygame_update_queue.get_nowait())
            except queue.Empty:
                break

            if update_type == utils.UPDATE_TYPE_MESSAGE:
                log_messages.append(str(update_data))
                if len(log_messages) > max_log_lines:
                    log_messages = log_messages[-max_log_lines:]
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
                # Aggiorna solo le chiavi presenti in update_data
                for key, value in update_data.items():
                    if key in current_status:
                        current_status[key] = value
                    # Aggiorna il tentativo se fornito
                    elif key == "attempt":
                        current_status['attempt'] = value

                # Gestione stato attesa
                if step_by_step_mode and current_status.get(
                        "status") == "Waiting for Next Round":
                    simulation_waiting_for_next = True
                else:
                    simulation_waiting_for_next = False

            elif update_type == utils.UPDATE_TYPE_RESULTS:
                if update_data and "results" in update_data:
                    current_results_data = update_data["results"]

            elif update_type == utils.UPDATE_TYPE_FLAG:
                flag_state = update_data

            elif update_type == utils.UPDATE_TYPE_COMPLETE:
                current_status["status"] = "Simulation Complete"
                if update_data and update_data.get("elected"):
                    governor_name = update_data.get("governor", "Unknown")
                    current_status["governor"] = governor_name
                    log_messages.append(
                        f"\n{'*' * 30}\n*** GOVERNOR {governor_name.upper()} ELECTED! ***\n{'*' * 30}\n"
                    )
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
                    log_messages.append(
                        f"\n{'=' * 30}\n--- ELECTORAL DEADLOCK ---\n--- No Governor elected after {config.MAX_ELECTION_ATTEMPTS} attempts ---\n{'=' * 30}\n"
                    )
                simulation_running_event.clear()
                simulation_waiting_for_next = False
                if len(log_messages) > max_log_lines:
                    log_messages = log_messages[-max_log_lines:]

            elif update_type == utils.UPDATE_TYPE_ERROR:
                log_messages.append(
                    f"\n{'!' * 30}\n!!! SIMULATION ERROR !!!\n!!! {update_data} !!!\n{'!' * 30}\n"
                )
                current_status["status"] = "Error"
                simulation_running_event.clear()
                simulation_waiting_for_next = False
                if len(log_messages) > max_log_lines:
                    log_messages = log_messages[-max_log_lines:]

        # --- Drawing ---
        screen.fill(config.BG_COLOR)

        # Draw Status Area (come prima)
        status_bg_surface = pygame.Surface(STATUS_AREA.size, pygame.SRCALPHA)
        status_bg_surface.fill((64, 64, 64, 192))
        screen.blit(status_bg_surface, STATUS_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, STATUS_AREA, 1)

        status_y = STATUS_AREA.top + 5
        status_x_left = STATUS_AREA.left + 10
        status_x_right = STATUS_AREA.left + 300  # Spostato un po' a destra

        if 'font' in locals() and font:
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
            if current_status_text == "Governor Elected!" and "governor" in current_status:
                render_text(font, f"Governor: {current_status['governor']}",
                            config.GREEN, screen, status_x_right,
                            status_y + h1 + 2)  # Allineato con Round
            mode_text = "Mode: Step-by-Step" if step_by_step_mode else "Mode: Continuous"
            render_text(small_font, mode_text, config.WHITE, screen,
                        status_x_left,
                        STATUS_AREA.bottom - small_font.get_linesize() - 5)
        # ... (fallback else)

        # --- Draw Visual Area (MODIFICATO) ---
        visual_bg_surface = pygame.Surface(VISUAL_AREA.size, pygame.SRCALPHA)
        visual_bg_surface.fill((32, 32, 32, 160))
        screen.blit(visual_bg_surface, VISUAL_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, VISUAL_AREA, 1)

        # Disegna i nomi dei candidati con colori basati sul genere
        displayed_candidate_text_rects = [
        ]  # Resetta la lista per questo frame

        # Assumiamo che current_results_data abbia candidati con 'name', 'gender', 'attributes'
        display_items = current_results_data
        max_visual_candidates = 12  # Possiamo mostrare più nomi che sprite
        displayed_visual_items = display_items[:max_visual_candidates]

        num_display_visual = len(displayed_visual_items)
        if num_display_visual > 0 and 'small_font' in locals() and small_font:
            num_columns = 3  # Numero di colonne per i nomi
            col_width = VISUAL_AREA.width // num_columns
            row_height = small_font.get_linesize() + 4  # Spazio tra le righe
            start_x = VISUAL_AREA.left + 10
            start_y = VISUAL_AREA.top + 10
            current_col = 0
            current_row = 0

            for item in displayed_visual_items:
                candidate_name = item.get('name', 'N/A')
                gender = item.get('gender', 'unknown')
                attributes = item.get('attributes',
                                      {})  # Per tooltip se necessario

                # Determina colore
                text_color = config.WHITE  # Default
                if gender == "female":
                    text_color = config.PINK
                elif gender == "male":
                    text_color = config.LIGHT_BLUE

                # Calcola posizione
                text_x = start_x + current_col * col_width
                text_y = start_y + current_row * row_height

                # Renderizza il testo
                h, text_rect = render_text(small_font, candidate_name,
                                           text_color, screen, text_x, text_y)
                displayed_candidate_text_rects.append(
                    (text_rect, item))  # Salva rect e info

                # Controlla se il nome è sotto il mouse per tooltip
                if text_rect.collidepoint(mouse_pos):
                    clicked_candidate = item
                    attributes = item.get('attributes', {})
                    age = item.get('age', 'N/A')  # Recupera l'età
                    gender = item.get('gender', 'unknown')
                    attributes_str = ", ".join(
                        [f"{k.replace('_',' ').title()}: {v}" for k, v in attributes.items()])
                    # AGGIUNGI ETA' AL TOOLTIP
                    tooltip_text = f"{candidate_name} (Age: {age}, Gender: {gender.title()})\nAttributes: {attributes_str if attributes_str else 'N/A'}"

                # Aggiorna posizione per il prossimo nome
                current_row += 1
                if start_y + (current_row +
                              1) * row_height > VISUAL_AREA.bottom - 10:
                    current_row = 0
                    current_col += 1
                    if current_col >= num_columns:
                        break  # Non ci stanno più colonne

        # --- Draw Results Area (con barre, come prima) ---
        results_bg_surface = pygame.Surface(RESULTS_AREA.size, pygame.SRCALPHA)
        results_bg_surface.fill((48, 48, 48, 192))
        screen.blit(results_bg_surface, RESULTS_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, RESULTS_AREA, 1)
        if 'font' in locals() and font:
            _, _ = render_text(title_font, "Latest Results:", config.WHITE,
                               screen, RESULTS_AREA.left + 10,
                               RESULTS_AREA.top + 5)
            if current_results_data:
                # Calcola max voti tra i risultati *correnti*
                relevant_results = [
                    item for item in current_results_data
                    if item.get('votes', 0) > 0
                ]  # Considera solo chi ha voti
                max_votes = max(
                    item['votes']
                    for item in relevant_results) if relevant_results else 1

                bar_area_width = RESULTS_AREA.width - 20
                bar_height = 15
                bar_spacing = 5
                bar_start_y = RESULTS_AREA.top + 5 + title_font.get_linesize(
                ) + 10

                sorted_results = sorted(relevant_results,
                                        key=lambda x: x.get('votes', 0),
                                        reverse=True)
                total_votes_this_round = sum(
                    item['votes']
                    for item in relevant_results) if relevant_results else 0

                for i, item in enumerate(sorted_results):
                    if bar_start_y + i * (
                            bar_height + bar_spacing
                    ) + bar_height <= RESULTS_AREA.bottom - 5:
                        candidate_name = item['name']
                        votes = item['votes']
                        is_elected_this_round = item.get(
                            'elected_this_round', False)
                        is_overall_elected = (
                            current_status.get("status") == "Governor Elected!"
                            and candidate_name
                            == current_status.get("governor"))

                        vote_percentage = (
                            votes / total_votes_this_round
                        ) * 100 if total_votes_this_round > 0 else 0

                        bar_width = (votes / max_votes
                                     ) * bar_area_width if max_votes > 0 else 0
                        bar_width = max(
                            1,
                            bar_width)  # Larghezza minima 1 pixel se ha voti

                        bar_color = config.GRAY
                        if is_elected_this_round or is_overall_elected:
                            bar_color = config.GREEN  # Verde se eletto nel round o governatore finale

                        bar_rect = pygame.Rect(
                            RESULTS_AREA.left + 10,
                            bar_start_y + i * (bar_height + bar_spacing),
                            bar_width, bar_height)
                        pygame.draw.rect(screen, bar_color, bar_rect)
                        pygame.draw.rect(screen, config.WHITE, bar_rect,
                                         1)  # Bordo

                        if 'small_font' in locals() and small_font:
                            name_text = f"{candidate_name}: {votes} ({vote_percentage:.1f}%)"
                            name_surface = small_font.render(
                                name_text, True, config.WHITE)
                            text_x = bar_rect.left + 5
                            # Se la barra è troppo stretta, scrivi a destra
                            if bar_width < name_surface.get_width() + 10:
                                text_x = bar_rect.right + 5

                            name_y = bar_rect.centery - name_surface.get_height(
                            ) // 2
                            # Limita la x per non uscire dall'area
                            text_x = min(
                                text_x, RESULTS_AREA.right - 10 -
                                name_surface.get_width())
                            screen.blit(name_surface, (text_x, name_y))
                    else:
                        if 'small_font' in locals() and small_font:
                            render_text(
                                small_font, "...", config.WHITE, screen,
                                RESULTS_AREA.left + 10,
                                bar_start_y + i * (bar_height + bar_spacing))
                        break  # Esce dal loop se non c'è più spazio verticale
        # ... (fallback else)

        # Draw Log Area (come prima)
        log_bg_surface = pygame.Surface(LOG_AREA.size, pygame.SRCALPHA)
        log_bg_surface.fill((48, 48, 48, 192))
        screen.blit(log_bg_surface, LOG_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, LOG_AREA, 1)
        if 'small_font' in locals() and small_font:
            _, _ = render_text(title_font, "Log:", config.WHITE, screen,
                               LOG_AREA.left + 10, LOG_AREA.top + 5)
            log_y = LOG_AREA.top + 5 + title_font.get_linesize() + 5
            # Mostra i messaggi dal più recente al più vecchio
            for msg in reversed(log_messages):
                if log_y + small_font.get_linesize() <= LOG_AREA.bottom - 5:
                    # Word wrap manuale semplice
                    words = msg.split(' ')
                    lines = []
                    current_line = ""
                    max_width = LOG_AREA.width - 20  # Larghezza massima testo
                    for word in words:
                        test_line = current_line + word + " "
                        test_surface = small_font.render(
                            test_line, True, config.WHITE)
                        if test_surface.get_width() < max_width:
                            current_line = test_line
                        else:
                            lines.append(current_line)
                            current_line = word + " "
                    lines.append(current_line)  # Aggiunge l'ultima linea

                    # Renderizza le linee wrappate
                    temp_y = log_y
                    for line in lines:
                        if temp_y + small_font.get_linesize(
                        ) <= LOG_AREA.bottom - 5:
                            render_text(small_font, line.strip(), config.WHITE,
                                        screen, LOG_AREA.left + 10, temp_y)
                            temp_y += small_font.get_linesize()
                        else:
                            break  # Non c'è più spazio verticale nel log
                    log_y = temp_y  # Aggiorna y per il prossimo messaggio
                    if log_y >= LOG_AREA.bottom - 5:
                        break  # Esce se l'area log è piena
                else:
                    break  # Esce se l'area log è piena
        # ... (fallback else)

        # Draw Flag Area (come prima)
        # ... (logica flag esistente) ...
        flag_area_rect = pygame.Rect(
            STATUS_AREA.right - 70,
            STATUS_AREA.top + 5,
            60,
            STATUS_AREA.height - 10,
        )
        if flag_state is True:
            stripe_width = flag_area_rect.width // 3
            stripe_height = flag_area_rect.height
            pygame.draw.rect(screen, config.LIGHT_BLUE,
                             (flag_area_rect.left, flag_area_rect.top,
                              stripe_width, stripe_height))
            pygame.draw.rect(screen, config.BLUE,
                             (flag_area_rect.left + stripe_width,
                              flag_area_rect.top, stripe_width, stripe_height))
            pygame.draw.rect(screen, config.LIGHT_BLUE,
                             (flag_area_rect.left + 2 * stripe_width,
                              flag_area_rect.top, stripe_width, stripe_height))
        elif flag_state is False:
            pygame.draw.rect(screen, config.BLACK, flag_area_rect)
        pygame.draw.rect(screen, config.WHITE, flag_area_rect, 1)

        # Draw Button Area (come prima)
        BUTTON_WIDTH = 150
        BUTTON_HEIGHT = BUTTON_AREA.height - 10
        button_padding = 20
        visible_buttons_count = 2 + (1 if step_by_step_mode else 0)
        total_visible_buttons_width = BUTTON_WIDTH * visible_buttons_count + button_padding * (
            visible_buttons_count - 1 if visible_buttons_count > 1 else 0)
        button_start_x = BUTTON_AREA.left + (BUTTON_AREA.width -
                                             total_visible_buttons_width) // 2
        button_y = BUTTON_AREA.top + 5

        start_button_enabled = not simulation_running_event.is_set()
        start_button_rect = draw_button(screen,
                                        pygame.Rect(button_start_x, button_y,
                                                    BUTTON_WIDTH,
                                                    BUTTON_HEIGHT),
                                        config.GREEN,
                                        "Start Election",
                                        font,
                                        config.WHITE,
                                        enabled=start_button_enabled)
        current_button_x = start_button_rect.right + button_padding

        if step_by_step_mode:
            next_round_button_enabled = simulation_running_event.is_set(
            ) and simulation_waiting_for_next
            next_round_button_rect = draw_button(
                screen,
                pygame.Rect(current_button_x, button_y, BUTTON_WIDTH,
                            BUTTON_HEIGHT),
                config.BLUE,
                "Next Round",
                font,
                config.WHITE,
                enabled=next_round_button_enabled)
            current_button_x = next_round_button_rect.right + button_padding

        quit_button_rect = draw_button(screen,
                                       pygame.Rect(current_button_x, button_y,
                                                   BUTTON_WIDTH,
                                                   BUTTON_HEIGHT),
                                       config.RED,
                                       "Quit",
                                       font,
                                       config.WHITE,
                                       enabled=True)

        # --- Tooltip Drawing ---
        if tooltip_text:
            tooltip_lines = tooltip_text.split('\n')
            max_tooltip_width = 0
            tooltip_surfaces = []
            total_tooltip_height = 0
            line_spacing = 2

            for line in tooltip_lines:
                surf = small_font.render(line, True, config.BLACK)
                tooltip_surfaces.append(surf)
                max_tooltip_width = max(max_tooltip_width, surf.get_width())
                total_tooltip_height += surf.get_height() + line_spacing

            tooltip_rect = pygame.Rect(0, 0, max_tooltip_width + 10,
                                       total_tooltip_height + 5)
            tooltip_rect.topleft = (mouse_pos[0] + 15, mouse_pos[1] + 10
                                    )  # Offset da mouse

            # Assicura che il tooltip rimanga nello schermo
            tooltip_rect.clamp_ip(screen.get_rect())

            # Disegna sfondo e testo
            pygame.draw.rect(screen, config.YELLOW,
                             tooltip_rect)  # Sfondo giallo
            pygame.draw.rect(screen, config.BLACK, tooltip_rect,
                             1)  # Bordo nero
            current_tooltip_y = tooltip_rect.top + 5
            for surf in tooltip_surfaces:
                screen.blit(surf, (tooltip_rect.left + 5, current_tooltip_y))
                current_tooltip_y += surf.get_height() + line_spacing

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    simulation_continue_event.set(
    )  # Segnala al thread di terminare se in attesa
    if simulation_thread and simulation_thread.is_alive():
        print("Pygame quit, attempting to join simulation thread...")
        simulation_thread.join(0.5)  # Attendi un po' che il thread termini


# Entry point (modificato per rimuovere check divisibilità)
if __name__ == "__main__":
    num_district_winners_needed_check = (config.NUM_GRAND_ELECTORS -
                                         config.NUM_PRESELECTED_CANDIDATES)
    if num_district_winners_needed_check < 0:
        print(
            f"Configuration Error: Negative district winners needed ({num_district_winners_needed_check})."
        )
        sys.exit()

    main_pygame_gui()
