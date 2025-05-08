import pygame
import sys
import threading
import queue
import time

# Imports da altri moduli del progetto (assoluti)
import config
import data
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
displayed_candidate_sprites = []


def render_text(font, text, color, surface, x, y):
    """Renders text on a Pygame surface."""
    text_surface = font.render(str(text), True, color)
    surface.blit(text_surface, (x, y))
    return text_surface.get_height()


def get_sprite_from_sheet(spritesheet, row, col, sprite_width, sprite_height):
    """Extracts a single sprite surface from a spritesheet."""
    if spritesheet is None:
        return None

    sheet_width, sheet_height = spritesheet.get_size()
    x = col * sprite_width
    y = row * sprite_height

    if x + sprite_width <= sheet_width and y + sprite_height <= sheet_height:
        sprite_surface = pygame.Surface((sprite_width, sprite_height),
                                        pygame.SRCALPHA, 32)
        sprite_surface = sprite_surface.convert_alpha()
        sprite_surface.blit(spritesheet, (0, 0),
                            (x, y, sprite_width, sprite_height))
        return sprite_surface
    else:
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
    global STATUS_AREA, VISUAL_AREA, RESULTS_AREA, LOG_AREA, BUTTON_AREA, simulation_waiting_for_next, displayed_candidate_sprites

    pygame.init()

    infoObject = pygame.display.Info()
    SCREEN_WIDTH = infoObject.current_w
    SCREEN_HEIGHT = infoObject.current_h
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                                     pygame.FULLSCREEN)

    pygame.display.set_caption(config.WINDOW_TITLE)

    try:
        font = pygame.font.SysFont("monospace", config.PIXEL_FONT_SIZE)
        small_font = pygame.font.SysFont("monospace",
                                         config.PIXEL_FONT_SIZE - 2)
    except pygame.error as e:
        print(f"Warning, could not load font: {e}")
        font = pygame.font.SysFont("monospace", config.PIXEL_FONT_SIZE)
        small_font = pygame.font.SysFont("monospace",
                                         config.PIXEL_FONT_SIZE - 2)

    clock = pygame.time.Clock()

    # --- Load Images and Extract Sprites ---
    assets = {}
    sprites = {}

    for name, path in config.IMAGE_PATHS.items():
        if name.startswith("character_"):
            try:
                loaded_image = pygame.image.load(path).convert_alpha()
                assets[name] = loaded_image
            except pygame.error as e:
                print(f"Warning: Could not load image {path}: {e}")
                assets[name] = None

    if data.SPRITE_MAPPING:
        for sprite_name, (sheet_asset_key, row,
                          col) in data.SPRITE_MAPPING.items():
            spritesheet = assets.get(sheet_asset_key)

            if spritesheet:
                sprite_surface = get_sprite_from_sheet(spritesheet, row, col,
                                                       config.SPRITE_WIDTH,
                                                       config.SPRITE_HEIGHT)
                if sprite_surface:
                    sprites[sprite_name] = sprite_surface
            else:
                pass

    else:
        print(
            "Warning: SPRITE_MAPPING is empty. No character sprites will be available."
        )

    # --- UI Layout Areas (Defined dynamically based on screen size) ---
    STATUS_AREA = pygame.Rect(20, 20, SCREEN_WIDTH - 40, 80)
    VISUAL_AREA_HEIGHT = 200
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

    # Simulation state variables for GUI display
    current_status = {
        "attempt": 0,
        "phase": "Initializing...",
        "round": 0,
        "status": "Idle",
    }
    current_results_data = []
    log_messages = []
    current_status_text = ""

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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check button clicks

                    # Controllo pulsante Start
                    # Usa simulation_running_event per verificare se la simulazione è attiva
                    if 'start_button_rect' in locals(
                    ) and start_button_rect.collidepoint(event.pos):
                        if not simulation_running_event.is_set(
                        ):  # Check if not already running
                            simulation_started = True
                            # Reset state for a new simulation
                            current_status = {
                                "attempt": 0,
                                "phase": "Initializing...",
                                "round": 0,
                                "status": "Idle",
                            }
                            current_results_data = []
                            log_messages = []
                            flag_state = None
                            simulation_waiting_for_next = False
                            displayed_candidate_sprites = [
                            ]  # Clear clickable sprites list

                            # Clear the event before starting the new thread
                            simulation_continue_event.clear(
                            )  # Ensure it's clear before starting

                            # Start the simulation thread
                            simulation_thread = threading.Thread(
                                target=election.run_election_simulation,
                                kwargs={
                                    'election_attempt': 1,
                                    'preselected_candidates_info': None,
                                    'runoff_carryover_winner_name': None,
                                    'continue_event':
                                    simulation_continue_event,
                                    'running_event': simulation_running_event,
                                    'step_by_step_mode': step_by_step_mode
                                })
                            simulation_thread.daemon = True
                            simulation_thread.start()
                            simulation_running_event.set()  # Set running event
                            # In modalità continua, settiamo l'evento qui per farlo partire
                            # In modalità passo passo, non lo settiamo, aspetterà il primo click di "Next Round"
                            if not step_by_step_mode:
                                simulation_continue_event.set()

                    # Controllo pulsante Next Round (visibile/attivo solo in modalità passo-passo)
                    if step_by_step_mode and 'next_round_button_rect' in locals(
                    ) and next_round_button_rect.collidepoint(event.pos):
                        # Only allow "Next Round" if the simulation is running AND waiting
                        if simulation_running_event.is_set(
                        ) and simulation_waiting_for_next:
                            simulation_continue_event.set(
                            )  # Signal simulation thread to proceed
                            # simulation_waiting_for_next will be cleared by the thread itself when it proceeds

                    # Controllo pulsante Quit
                    # Usa 'quit_button_rect' in locals() per sicurezza
                    if 'quit_button_rect' in locals(
                    ) and quit_button_rect.collidepoint(event.pos):
                        running = False  # Exit the main loop

                    # Controlla i click sugli sprite dei candidati visualizzati
                    for rect, candidate_info in displayed_candidate_sprites:
                        if rect.collidepoint(event.pos):
                            # Visualizza gli attributi del candidato nel log
                            utils.send_pygame_update(
                                utils.UPDATE_TYPE_MESSAGE,
                                f"\n--- Attributi per {candidate_info['name']} ---"
                            )
                            attributes_str = ", ".join([
                                f"{key.replace('_', ' ').title()}: {value}"
                                for key, value in
                                candidate_info['attributes'].items()
                            ])
                            utils.send_pygame_update(
                                utils.UPDATE_TYPE_MESSAGE,
                                f"  Attributi: {attributes_str}")
                            utils.send_pygame_update(
                                utils.UPDATE_TYPE_MESSAGE,
                                "--------------------------------------")
                            break  # Esci dal ciclo dopo aver trovato uno sprite cliccato

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

            elif update_type == utils.UPDATE_TYPE_STATUS:
                current_status.update(update_data)
                # Check if the status indicates waiting for the next round
                # MODIFICATO QUI: Controlla esplicitamente lo stato di attesa
                if step_by_step_mode and update_data.get(
                        "status") == "Waiting for Next Round":
                    simulation_waiting_for_next = True
                else:
                    # Reset waiting flag if status is not "Waiting for Next Round"
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
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        f"\n{'*' * 30}\n*** GOVERNATORE {governor_name.upper()} ELETTO! ***\n{'*' * 30}\n",
                    )
                    # Prova a trovare le informazioni complete del candidato eletto per mostrare gli attributi
                    # Assumiamo che current_results_data contenga gli attributi dall'ultimo round del collegio
                    elected_candidate_info = next(
                        (item for item in current_results_data
                         if item.get('name') == governor_name), None)
                    if elected_candidate_info and elected_candidate_info.get(
                            'attributes'):
                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_MESSAGE,
                            f"Attributi del Governatore {governor_name}:")
                        attributes_str = ", ".join([
                            f"{key.replace('_', ' ').title()}: {value}"
                            for key, value in
                            elected_candidate_info['attributes'].items()
                        ])
                        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                                 f"  {attributes_str}")
                        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                                 "-" * 30)

                else:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        f"\n{'=' * 30}\n--- STALLO ELETTORALE ---\n--- Nessun Governatore eletto dopo {config.MAX_ELECTION_ATTEMPTS} tentativi ---\n{'=' * 30}\n"
                    )
                # Simulation finished
                simulation_running_event.clear()
                simulation_waiting_for_next = False

            elif update_type == utils.UPDATE_TYPE_ERROR:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"\n{'!' * 30}\n!!! ERRORE SIMULAZIONE !!!\n!!! {update_data} !!!\n{'!' * 30}\n"
                )
                current_status["status"] = "Error"
                # Simulation errored
                simulation_running_event.clear()
                simulation_waiting_for_next = False

        # --- Drawing ---
        screen.fill(config.BG_COLOR)

        # Draw Status Area
        status_bg_surface = pygame.Surface(STATUS_AREA.size, pygame.SRCALPHA)
        status_bg_surface.fill((64, 64, 64, 192))
        screen.blit(status_bg_surface, STATUS_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, STATUS_AREA, 1)

        status_y = STATUS_AREA.top + 5
        status_x_left = STATUS_AREA.left + 10
        status_x_right = STATUS_AREA.left + 250

        if 'font' in locals() and font:
            status_y += render_text(
                font,
                f"Attempt: {current_status.get('attempt', '-')}/{config.MAX_ELECTION_ATTEMPTS}",
                config.WHITE,
                screen,
                status_x_left,
                status_y,
            )
            phase_line_y = status_y
            status_y += render_text(
                font,
                f"Phase: {current_status.get('phase', 'N/A')}",
                config.WHITE,
                screen,
                status_x_left,
                status_y,
            )
            render_text(
                font,
                f"Round: {current_status.get('round', '-')}",
                config.WHITE,
                screen,
                status_x_right,
                phase_line_y,
            )

            status_text_y = status_y
            current_status_text = current_status.get("status", "")
            status_y += render_text(
                font,
                f"Status: {current_status_text}",
                config.WHITE,
                screen,
                status_x_left,
                status_y,
            )
            if current_status_text == "Governor Elected!" and "governor" in current_status:
                render_text(
                    font,
                    f"Governor: {current_status['governor']}",
                    config.GREEN,
                    screen,
                    status_x_right,
                    status_text_y,
                )
            mode_text = "Mode: Step-by-Step" if step_by_step_mode else "Mode: Continuous"
            render_text(
                small_font,
                mode_text,
                config.WHITE,
                screen,
                status_x_left,
                status_y + small_font.get_linesize() + 2,
            )

        else:
            screen.blit(
                pygame.font.Font(None, config.PIXEL_FONT_SIZE).render(
                    "Loading...", True, config.WHITE),
                (STATUS_AREA.left + 10, STATUS_AREA.top + 10))

        # Draw Visual Area
        visual_bg_surface = pygame.Surface(VISUAL_AREA.size, pygame.SRCALPHA)
        visual_bg_surface.fill((32, 32, 32, 160))
        screen.blit(visual_bg_surface, VISUAL_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, VISUAL_AREA, 1)

        # --- Draw Characters/Sprites in Visual Area ---
        # Clear the list for the new frame
        displayed_candidate_sprites = []

        # Assuming current_results_data has candidates with sprite_key and name
        display_items = current_results_data
        max_visual_candidates = 8
        displayed_visual_items = display_items[:max_visual_candidates]

        num_display_visual = len(displayed_visual_items)
        if num_display_visual > 0:
            min_spacing = config.SPRITE_WIDTH + 10
            total_required_width = num_display_visual * min_spacing
            available_width = VISUAL_AREA.width - 20

            if total_required_width > available_width:
                sprite_spacing = available_width // num_display_visual if num_display_visual > 0 else 0
            else:
                sprite_spacing = min_spacing

            start_x = VISUAL_AREA.left + 10

            for i in range(num_display_visual):
                item = displayed_visual_items[i]
                candidate_name = item['name']
                sprite_key = item.get('sprite_key')
                candidate_attributes = item.get(
                    'attributes', {})  # Assume attributes are in the item

                sprite_surface = None
                if sprite_key and sprite_key in sprites:
                    sprite_surface = sprites[sprite_key]

                if sprite_surface:
                    sprite_x = start_x + i * sprite_spacing + (
                        sprite_spacing - sprite_surface.get_width()) // 2
                    sprite_y = VISUAL_AREA.top + 10

                    sprite_draw_x = max(VISUAL_AREA.left + 2, sprite_x)
                    sprite_draw_y = max(VISUAL_AREA.top + 2, sprite_y)
                    sprite_rect = screen.blit(sprite_surface,
                                              (sprite_draw_x, sprite_draw_y))

                    # Store the clickable area and candidate info
                    displayed_candidate_sprites.append((sprite_rect, {
                        'name':
                        candidate_name,
                        'attributes':
                        candidate_attributes
                    }))

                    if 'small_font' in locals() and small_font:
                        text_y = sprite_draw_y + sprite_surface.get_height(
                        ) + 2
                        text_surface = small_font.render(
                            candidate_name, True, config.WHITE)
                        text_x = sprite_x + (sprite_surface.get_width() -
                                             text_surface.get_width()) // 2
                        text_rect = text_surface.get_rect(topleft=(text_x,
                                                                   text_y))
                        text_rect.left = max(text_rect.left,
                                             VISUAL_AREA.left + 2)
                        text_rect.right = min(text_rect.right,
                                              VISUAL_AREA.right - 2)
                        if text_rect.left < text_rect.right:
                            screen.blit(text_surface, text_rect.topleft)

                else:
                    # Placeholder drawing logic
                    placeholder_size = 30
                    placeholder_y_offset = (
                        config.SPRITE_HEIGHT - placeholder_size
                    ) // 2 if 'SPRITE_HEIGHT' in dir(config) else 0
                    placeholder_x = start_x + i * sprite_spacing + (
                        sprite_spacing - placeholder_size) // 2
                    placeholder_y = VISUAL_AREA.top + 10 + placeholder_y_offset

                    placeholder_draw_x = max(VISUAL_AREA.left + 2,
                                             placeholder_x)
                    placeholder_draw_y = max(VISUAL_AREA.top + 2,
                                             placeholder_y)

                    placeholder_rect = pygame.draw.rect(
                        screen, config.GRAY,
                        (placeholder_draw_x, placeholder_draw_y,
                         placeholder_size, placeholder_size))

                    # Store the clickable area and candidate info (even for placeholders)
                    displayed_candidate_sprites.append((placeholder_rect, {
                        'name':
                        candidate_name,
                        'attributes':
                        candidate_attributes
                    }))

                    if 'small_font' in locals() and small_font:
                        text_y = VISUAL_AREA.top + 10 + (
                            config.SPRITE_HEIGHT
                            if 'SPRITE_HEIGHT' in dir(config) else 40) + 2
                        text_surface = small_font.render(
                            candidate_name, True, config.WHITE)
                        text_x = start_x + i * sprite_spacing + (
                            sprite_spacing - text_surface.get_width()) // 2
                        text_rect = text_surface.get_rect(topleft=(text_x,
                                                                   text_y))
                        text_rect.left = max(text_rect.left,
                                             VISUAL_AREA.left + 2)
                        text_rect.right = min(text_rect.right,
                                              VISUAL_AREA.right - 2)
                        if text_rect.left < text_rect.right:
                            screen.blit(text_surface, text_rect.topleft)

        # Draw Results Area (with bars)
        results_bg_surface = pygame.Surface(RESULTS_AREA.size, pygame.SRCALPHA)
        results_bg_surface.fill((48, 48, 48, 192))
        screen.blit(results_bg_surface, RESULTS_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, RESULTS_AREA, 1)
        if 'font' in locals() and font:
            render_text(
                font,
                "Latest Results:",
                config.WHITE,
                screen,
                RESULTS_AREA.left + 10,
                RESULTS_AREA.top + 5,
            )
            if current_results_data:
                max_votes = max(
                    item['votes'] for item in
                    current_results_data) if current_results_data else 1
                bar_area_width = RESULTS_AREA.width - 20  # Padding for bars
                bar_height = 15
                bar_spacing = 5
                bar_start_y = RESULTS_AREA.top + 5 + font.get_linesize() + 10

                sorted_results = sorted(current_results_data,
                                        key=lambda x: x.get('votes', 0),
                                        reverse=True)

                for i, item in enumerate(sorted_results):
                    if bar_start_y + i * (
                            bar_height + bar_spacing
                    ) + bar_height <= RESULTS_AREA.bottom - 5:
                        candidate_name = item['name']
                        votes = item['votes']
                        is_elected_this_round = item.get(
                            'elected_this_round', False)
                        is_overall_elected = (
                            current_status_text == "Governor Elected!"
                            and "governor" in current_status
                            and candidate_name == current_status["governor"])

                        # Calcola la percentuale di voti
                        total_votes_this_round = sum(
                            item['votes'] for item in current_results_data
                        ) if current_results_data else 0
                        vote_percentage = (
                            votes / total_votes_this_round
                        ) * 100 if total_votes_this_round > 0 else 0

                        bar_width = (votes / max_votes
                                     ) * bar_area_width if max_votes > 0 else 0

                        bar_color = config.GRAY
                        if is_elected_this_round:
                            bar_color = config.GREEN
                        elif is_overall_elected:
                            bar_color = config.BLUE

                        bar_rect = pygame.Rect(
                            RESULTS_AREA.left + 10,
                            bar_start_y + i * (bar_height + bar_spacing),
                            bar_width, bar_height)
                        pygame.draw.rect(screen, bar_color, bar_rect)
                        pygame.draw.rect(screen, config.WHITE, bar_rect, 1)

                        if 'small_font' in locals() and small_font:
                            # Includi la percentuale nel testo
                            name_surface = small_font.render(
                                f"{candidate_name}: {votes} ({vote_percentage:.1f}%)",
                                True, config.WHITE)
                            # Posiziona il testo sulla barra (se abbastanza larga) o a destra
                            text_x = bar_rect.right + 5  # Posizione iniziale a destra
                            if bar_width > name_surface.get_width(
                            ) + 10:  # Spazio sufficiente sulla barra
                                text_x = bar_rect.left + 5  # Posizione sulla barra

                            name_y = bar_rect.top + (
                                bar_height - name_surface.get_height()
                            ) // 2  # Centratura verticale
                            text_x = min(text_x, RESULTS_AREA.right - 10 -
                                         name_surface.get_width()
                                         )  # Evita overflow a destra
                            screen.blit(name_surface, (text_x, name_y))

                    else:
                        if 'small_font' in locals() and small_font:
                            render_text(
                                small_font, "...", config.WHITE, screen,
                                RESULTS_AREA.left + 10,
                                bar_start_y + i * (bar_height + bar_spacing))
                        break

        else:
            screen.blit(
                pygame.font.Font(None, config.PIXEL_FONT_SIZE).render(
                    "Results Loading...", True, config.WHITE),
                (RESULTS_AREA.left + 10, RESULTS_AREA.top + 10))

        # Draw Log Area
        log_bg_surface = pygame.Surface(LOG_AREA.size, pygame.SRCALPHA)
        log_bg_surface.fill((48, 48, 48, 192))
        screen.blit(log_bg_surface, LOG_AREA.topleft)
        pygame.draw.rect(screen, config.WHITE, LOG_AREA, 1)
        if 'small_font' in locals() and small_font:
            render_text(small_font, "Log:", config.WHITE, screen,
                        LOG_AREA.left + 10, LOG_AREA.top + 5)
            log_y = LOG_AREA.top + 5 + small_font.get_linesize() + 5
            for msg in log_messages:
                if log_y + small_font.get_linesize() <= LOG_AREA.bottom - 5:
                    render_text(small_font, msg, config.WHITE, screen,
                                LOG_AREA.left + 10, log_y)
                    log_y += small_font.get_linesize()
                else:
                    break
        else:
            screen.blit(
                pygame.font.Font(None, config.PIXEL_FONT_SIZE).render(
                    "Log Loading...", True, config.WHITE),
                (LOG_AREA.left + 10, LOG_AREA.top + 10))

        # Draw Flag Area
        flag_area_rect = pygame.Rect(
            STATUS_AREA.left + 300,
            STATUS_AREA.top + 5,
            60,
            STATUS_AREA.height - 10,
        )

        if flag_state is True:
            stripe_width = flag_area_rect.width // 3
            stripe_height = flag_area_rect.height
            pygame.draw.rect(
                screen,
                config.LIGHT_BLUE,
                (
                    flag_area_rect.left,
                    flag_area_rect.top,
                    stripe_width,
                    stripe_height,
                ),
            )
            pygame.draw.rect(
                screen,
                config.BLUE,
                (
                    flag_area_rect.left + stripe_width,
                    flag_area_rect.top,
                    stripe_width,
                    stripe_height,
                ),
            )
            pygame.draw.rect(
                screen,
                config.LIGHT_BLUE,
                (
                    flag_area_rect.left + 2 * stripe_width,
                    flag_area_rect.top,
                    stripe_width,
                    stripe_height,
                ),
            )
        elif flag_state is False:
            pygame.draw.rect(screen, config.BLACK, flag_area_rect)
        pygame.draw.rect(screen, config.WHITE, flag_area_rect, 1)

        # Draw Button Area Background already done before button drawing

        # Draw Buttons
        BUTTON_WIDTH = 150
        BUTTON_HEIGHT = BUTTON_AREA.height - 10
        button_padding = 20
        visible_buttons_count = 2
        if step_by_step_mode:
            visible_buttons_count += 1

        total_visible_buttons_width = BUTTON_WIDTH * visible_buttons_count + button_padding * (
            visible_buttons_count - 1 if visible_buttons_count > 1 else 0)

        button_start_x = BUTTON_AREA.left + (BUTTON_AREA.width -
                                             total_visible_buttons_width) // 2
        button_y = BUTTON_AREA.top + 5

        # Start Button
        start_button_rect = pygame.Rect(button_start_x, button_y, BUTTON_WIDTH,
                                        BUTTON_HEIGHT)
        start_button_enabled = not simulation_running_event.is_set()
        draw_button(screen,
                    start_button_rect,
                    config.GREEN,
                    "Start Election",
                    font,
                    config.WHITE,
                    enabled=start_button_enabled)

        # Next Round Button (Conditional visibility based on step_by_step_mode)
        current_button_x = start_button_rect.right + button_padding
        if step_by_step_mode:
            next_round_button_rect = pygame.Rect(current_button_x, button_y,
                                                 BUTTON_WIDTH, BUTTON_HEIGHT)
            # Enable Next Round button only if simulation is running AND waiting for input
            next_round_button_enabled = simulation_running_event.is_set(
            ) and simulation_waiting_for_next
            draw_button(screen,
                        next_round_button_rect,
                        config.BLUE,
                        "Next Round",
                        font,
                        config.WHITE,
                        enabled=next_round_button_enabled)
            current_button_x = next_round_button_rect.right + button_padding

        # Quit Button
        quit_button_rect = pygame.Rect(current_button_x, button_y,
                                       BUTTON_WIDTH, BUTTON_HEIGHT)
        draw_button(screen,
                    quit_button_rect,
                    config.RED,
                    "Quit",
                    font,
                    config.WHITE,
                    enabled=True)

        pygame.display.flip()

        clock.tick(60)

    pygame.quit()
    # Signal simulation thread to stop
    simulation_continue_event.set()
    if simulation_thread and simulation_thread.is_alive():
        print("Pygame quit, attempting to signal simulation thread to stop...")
        simulation_thread.join(0.5)


# --- Run the Pygame GUI ---
if __name__ == "__main__":
    # Initial configuration checks
    num_district_winners_needed_check = (config.NUM_GRAND_ELECTORS -
                                         config.NUM_PRESELECTED_CANDIDATES)
    if (num_district_winners_needed_check < 0
            or num_district_winners_needed_check % config.NUM_DISTRICTS != 0):
        print(
            f"Configuration Error: With NUM_PRESELECTED_CANDIDATES={config.NUM_PRESELECTED_CANDIDATES}, the number of district winners needed ({num_district_winners_needed_check}) is not compatible with NUM_DISTRICTS={config.NUM_DISTRICTS}. This means the remaining candidates cannot be evenly distributed among districts."
        )
        print(
            "Adjust NUM_GRAND_ELECTORS, NUM_DISTRICTS, or NUM_PRESELECTED_CANDIDATES to make (NUM_GRAND_ELECTORS - NUM_PRESELECTED_CANDIDATES) divisible by NUM_DISTRICTS."
        )
        sys.exit()

    main_pygame_gui()
