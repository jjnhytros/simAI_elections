# election.py
import random
import math
import time
import copy
from collections import Counter
import sys
import threading  # Importato ma non usato direttamente
import uuid
import traceback

# Imports da altri moduli del progetto (assoluti)
import config
import data
import utils
import voting  # Contiene le funzioni di simulazione specifiche
import db_manager
import generation
# Import opzionale di numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:  # pragma: no cover
    HAS_NUMPY = False


def generate_candidate_oath(candidate_info, hot_topic=None):
    """Genera un giuramento/dichiarazione d'intenti più variata."""
    # ... (Codice completo come mostrato prima) ...
    return "Giuramento placeholder"  # Placeholder


def generate_random_event(candidates_info, elector_full_preferences_data, last_round_results=None):
    """Genera evento casuale. USA voting.apply_elector_impact."""
    # ... (Codice completo come mostrato prima, assicurandosi che usi voting.apply_elector_impact) ...
    pass  # Placeholder


def run_election_simulation(election_attempt, preselected_candidates_info_gui, runoff_carryover_winner_name, continue_event, running_event, step_by_step_mode):
    """
    Orchestra un tentativo di simulazione. Aggiorna statistiche. SENZA LLM.
    Include debug dettagliato e controlli robustezza.
    """
    governor_elected_name = None
    if running_event is None:
        running_event = threading.Event()
    if utils.simulation_running_event is None:
        utils.simulation_running_event = running_event

    # DEBUG
    print(
        f"\nDEBUG: +++ Entered run_election_simulation for Attempt {election_attempt} +++")

    try:
        # DEBUG
        print(f"DEBUG: Attempt {election_attempt}: Setting running_event...")
        running_event.set()

        # DEBUG
        print(
            f"DEBUG: Attempt {election_attempt}: Sending initial status updates via queue...")
        utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                 "attempt": election_attempt, "phase": "Initializing", "round": 0, "status": "Starting..."})
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"Attempt {election_attempt} starting...")
        # DEBUG
        print(
            f"DEBUG: Attempt {election_attempt}: Initial updates supposedly sent.")

        # 1. Inizializzazione
        # DEBUG
        print(f"DEBUG: Attempt {election_attempt}: Initializing DB...")
        db_manager.create_tables()
        # DEBUG
        print(f"DEBUG: Attempt {election_attempt}: Generating electors...")
        grand_electors_struct = generation.generate_grand_electors(
            config.NUM_GRAND_ELECTORS)
        elector_ids = [e_struct['id'] for e_struct in grand_electors_struct]
        social_network_graph = None
        if config.USE_SOCIAL_NETWORK:
            social_network_graph = generation.create_elector_network(
                elector_ids)

        # Gestione Candidati e STATS Iniziali
        current_candidates_info = []
        # ... (Logica popolazione current_candidates_info come prima) ...
        if preselected_candidates_info_gui:
            # etc.
            current_candidates_info = copy.deepcopy(
                preselected_candidates_info_gui)
        else:
            # etc.
            current_candidates_info = generation.generate_candidates(...);
        if not current_candidates_info:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_ERROR, "No candidates available.")
            running_event.clear(); return

        participating_uuids_in_attempt = []
        # ... (Logica aggiornamento stats partecipazione e init budget/stats come prima) ...

        # Inizializza preferenze elettori
        # DEBUG
        print(
            f"DEBUG: Attempt {election_attempt}: Initializing elector preferences...")
        elector_preferences_data = voting.initialize_elector_preferences(
            grand_electors_struct, current_candidates_info, preselected_candidates_info_gui)
        # Controllo Robusto 1
        if elector_preferences_data is None:  # pragma: no cover
            error_msg = f"Critical Error: Failed to initialize elector preferences (Attempt {election_attempt})."
            utils.send_pygame_update(utils.UPDATE_TYPE_ERROR, error_msg)
            print(f"ERROR: {error_msg}"); running_event.clear(); return
        # DEBUG
        print(
            f"DEBUG: Attempt {election_attempt}: Initialization complete. Prefs type: {type(elector_preferences_data)}, Num prefs: {len(elector_preferences_data)}")

        last_round_results_counter = Counter()

        # --- Ciclo Principale dell'Elezione ---
        # DEBUG
        print(
            f"DEBUG: Attempt {election_attempt}: Entering main round loop...")
        for current_round_num in range(config.MAX_TOTAL_ROUNDS):
            round_display_num = current_round_num + 1
            # DEBUG
            print(
                f"\n----- DEBUG: Attempt {election_attempt}: Starting Round {round_display_num} -----")
            if not running_event.is_set():
                print("DEBUG: Stop signal received at round start.")
                break

            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                     "phase": "Governor Election", "round": round_display_num, "status": "Processing Round..."})

            # STATS: Aggiorna partecipazione al round
            # DEBUG
            print(
                f"DEBUG Rd {round_display_num}: Updating round participation stats...")
            for c_info_round_start in current_candidates_info:
                c_uuid_round_start = c_info_round_start.get('uuid')
                if c_uuid_round_start and c_uuid_round_start in participating_uuids_in_attempt:
                     db_manager.update_candidate_stats(
                         c_uuid_round_start, {'rounds_participated_all_time': 1})

            # FASE: Strategie Candidati
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Adapting Strategies...")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                     "status": "Adapting Strategies..."})
            if hasattr(voting, 'analyze_competition_and_adapt_strategy'):
                for cand_info_strat in current_candidates_info:
                    if not running_event.is_set():
                        break
                    voting.analyze_competition_and_adapt_strategy(
                        cand_info_strat, current_candidates_info, last_round_results_counter, round_display_num)
            if not running_event.is_set():
                print("DEBUG: Stop signal after strategy.")
                break
            # DEBUG
            print(
                f"DEBUG Rd {round_display_num}: Finished Adapting Strategies.")

            # FASE: Campagna
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Simulating Campaigning...")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                     "status": "Campaigning..."})
            if hasattr(voting, 'simulate_campaigning'):
                voting.simulate_campaigning(
                    current_candidates_info, grand_electors_struct, elector_preferences_data, last_round_results_counter)
            if not running_event.is_set():
                print("DEBUG: Stop signal after campaigning.")
                break
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Finished Campaigning.")

            # FASE: Eventi Casuali
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Generating Random Event...")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                     "status": "Processing Random Events..."})
            generate_random_event(
                current_candidates_info, elector_preferences_data, last_round_results_counter)
            if not running_event.is_set():
                print("DEBUG: Stop signal after random events.")
                break
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Finished Random Event.")

            # FASE: Media Influence
            # DEBUG
            print(
                f"DEBUG Rd {round_display_num}: Simulating Media Influence...")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                     "status": "Simulating Media Influence..."})
            if hasattr(voting, 'simulate_media_influence'):
                voting.simulate_media_influence(
                    current_candidates_info, elector_preferences_data)
            if not running_event.is_set():
                print("DEBUG: Stop signal after media influence.")
                break
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Finished Media Influence.")

            # FASE: Influenza Sociale
            # DEBUG
            print(
                f"DEBUG Rd {round_display_num}: Simulating Social Influence...")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                     "status": "Simulating Social Influence..."})
            if config.USE_SOCIAL_NETWORK and social_network_graph:
                # DEBUG
                print(
                    f"DEBUG Rd {round_display_num}: Calling simulate_social_influence. Prefs type before: {type(elector_preferences_data)}")
                try:
                     if hasattr(voting, 'simulate_social_influence'):
                         result_social_influence = voting.simulate_social_influence(
                              social_network_graph, elector_preferences_data)
                          # DEBUG
                          print(
                              f"DEBUG Rd {round_display_num}: simulate_social_influence returned type: {type(result_social_influence)}")
                          # Controllo Robusto 2
                          if result_social_influence is None:  # pragma: no cover
                              error_msg = f"Critical Error: Social influence returned None in Round {round_display_num} (Attempt {election_attempt})."
                              utils.send_pygame_update(
                                  utils.UPDATE_TYPE_ERROR, error_msg)
                              print(f"ERROR: {error_msg}"); running_event.clear(); return
                          else:
                              elector_preferences_data = result_social_influence
                      # else: warning?
                 except Exception as e_social:  # pragma: no cover
                     tb_social = traceback.format_exc()
                      error_msg = f"Error during social influence call: {e_social}\n{tb_social}"
                      utils.send_pygame_update(utils.UPDATE_TYPE_ERROR, error_msg); print(f"ERROR: {error_msg}"); running_event.clear(); return
            else:
                print(f"DEBUG Rd {round_display_num}: Social influence skipped (disabled or no graph).")  # DEBUG
            if not running_event.is_set():
                print("DEBUG: Stop signal after social influence."); break
            print(f"DEBUG Rd {round_display_num}: Finished Social Influence.")  # DEBUG

            # --- Fase di Voto ---
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Starting Voting Phase...")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                     "status": "Electors Voting..."})
            current_round_votes_list = []
            # Controllo Robusto 3
            if elector_preferences_data is None:  # pragma: no cover
                error_msg = f"Critical Error: elector_preferences_data is None before voting in Round {round_display_num}!"
                utils.send_pygame_update(utils.UPDATE_TYPE_ERROR, error_msg)
                print(f"ERROR: {error_msg}"); running_event.clear(); return
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: elector_preferences_data type before voting loop: {type(elector_preferences_data)}")

            for elector_struct_vote in grand_electors_struct:
                if not running_event.is_set():
                    break
                elector_id_vote = elector_struct_vote['id']
                elector_data_vote = elector_preferences_data.get(
                    elector_id_vote)
                if elector_data_vote:
                    # Chiama SEMPRE simulate_ai_vote (versione senza LLM)
                    vote_cast = voting.simulate_ai_vote(
                        elector_id_vote, current_candidates_info, elector_data_vote,
                        last_round_results_counter, round_display_num, current_candidates_info)
                    if vote_cast:
                        current_round_votes_list.append(vote_cast)
            if not running_event.is_set():
                print("DEBUG: Stop signal during voting loop."); break
            print(f"DEBUG Rd {round_display_num}: Finished Voting Loop.")  # DEBUG
            # --- Fine Fase di Voto ---

            # Conteggio Voti e Aggiornamento Stats Voti
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Counting votes and updating stats...")
            current_results_counter = voting.count_votes(
                current_round_votes_list)
            if current_results_counter:
                for cand_name_round, votes_round in current_results_counter.items():
                    cand_uuid_round_vote = next((c.get('uuid') for c in current_candidates_info if c.get(
                         'name') == cand_name_round), None)
                     if cand_uuid_round_vote:
                         db_manager.update_candidate_stats(
                             cand_uuid_round_vote, {'total_votes_received_all_time': votes_round})
            print(f"DEBUG Rd {round_display_num}: Finished counting votes. Results: {current_results_counter.most_common(3)}")  # DEBUG

            # Identifica Elettori Chiave
            if elector_preferences_data and current_results_counter and hasattr(voting, 'identify_key_electors'):
                key_electors_list_data = voting.identify_key_electors(
                    elector_preferences_data, current_results_counter)
                if key_electors_list_data:
                     utils.send_pygame_update(
                         utils.UPDATE_TYPE_KEY_ELECTORS, key_electors_list_data)

            last_round_results_counter = current_results_counter

            # Invia Risultati a GUI
            # ... (come prima) ...

            # Verifica Elezione
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Verifying election...")
            governor_elected_name = None
            if hasattr(voting, 'verify_election'):
                current_majority_threshold = config.REQUIRED_MAJORITY if election_attempt < 3 else config.REQUIRED_MAJORITY_ATTEMPT_4
                governor_elected_name, _, _ = voting.verify_election(
                     current_results_counter, config.NUM_GRAND_ELECTORS, current_majority_threshold)
                 # DEBUG
                 print(f"DEBUG Rd {round_display_num}: Verification result - Governor Elected: {governor_elected_name}")
                 if governor_elected_name:
                     break
            # else: log errore?

            # Controllo max round normali
            # ... (come prima) ...

            # Gestione Step-by-Step / Pausa
            # DEBUG
            print(f"DEBUG Rd {round_display_num}: Reached end of round logic (step/pause).")
            if step_by_step_mode:
                utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                         "status": "Waiting for Next Round"})
                continue_event.clear()
                if not running_event.is_set():
                    break
                continue_event.wait()
                if not running_event.is_set():
                    break
            else:
                if not running_event.is_set():
                    break
                time.sleep(config.GOVERNOR_PAUSE_SECONDS)

            # DEBUG
            print(f"DEBUG: Attempt {election_attempt}: Finished Round {round_display_num}.")
        # --- Fine Ciclo dei Round ---

        # DEBUG
        print(f"DEBUG: Attempt {election_attempt}: Exited main round loop.")

        # --- STATS: Aggiorna Vittorie/Sconfitte ---
        # DEBUG
        print(f"DEBUG: Attempt {election_attempt}: Updating Win/Loss stats...")
        if running_event.is_set():  # Solo se non fermato
            if governor_elected_name:
                # ... (Logica stats vittoria/sconfitta come prima) ...
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, f"GOVERNOR {governor_elected_name.upper()} ELECTED! (Attempt {election_attempt})")
                utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE, {
                                          "elected": True, "governor": governor_elected_name})
                 # ... (aggiorna DB stats) ...
            else:  # Deadlock
                # ... (Logica stats sconfitta per tutti come prima) ...
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, f"Attempt {election_attempt}: Deadlock after {current_round_num + 1} rounds.")
                utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE, {
                                          "elected": False, "governor": None, "reason": "Deadlock"})
                 # ... (aggiorna DB stats) ...
        elif not governor_elected_name:  # Fermato dall'utente
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "Simulation stopped by user.")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                      "status": "Stopped by user"})
        # DEBUG
        print(f"DEBUG: Attempt {election_attempt}: Finished updating Win/Loss stats.")

    except Exception as e_sim:  # pragma: no cover
        tb_str = traceback.format_exc()
        error_message_sim = f"CRITICAL error in run_election_simulation (Attempt {election_attempt}): {str(e_sim)}\n{tb_str}"
        utils.send_pygame_update(utils.UPDATE_TYPE_ERROR, error_message_sim)
        print(error_message_sim)
    finally:
        # DEBUG
        print(f"DEBUG: Attempt {election_attempt}: run_election_simulation finally block reached. Clearing running_event.")
        if running_event:
            running_event.clear()