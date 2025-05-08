# election.py
import random
import math
import time
import copy
from collections import Counter
import sys
import threading  # Importato ma non usato direttamente per avviare GUI
import uuid
import traceback  # Per logging errori più dettagliato

# Imports da altri moduli del progetto (assoluti)
import config
import data
import utils
import voting  # Contiene la maggior parte delle funzioni di simulazione specifiche
import db_manager  # Necessario per interagire con il DB (es. stats)
import generation  # Per generare candidati, elettori, rete
# Import opzionale di numpy se si vuole usare per calcoli statistici
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:  # pragma: no cover
    HAS_NUMPY = False


def generate_candidate_oath(candidate_info, hot_topic=None):
    """Genera un giuramento/dichiarazione d'intenti più variata."""
    attrs = candidate_info.get("attributes", {})
    exp = attrs.get("administrative_experience", 1)
    soc = attrs.get("social_vision", 1)
    med = attrs.get("mediation_ability", 1)
    itg = attrs.get("ethical_integrity", 1)
    phrases = {
        "experience": {
            1: ["impegno a sviluppare esperienza"],
            2: ["volontà di acquisire competenze"],
            3: ["solida base gestionale"],
            4: ["forte leadership"],
            5: ["leadership esperta"]
        },
        "social_vision": {
            1: ["approccio pragmatico"],
            2: ["attenzione alle necessità"],
            3: ["equilibrio sociale"],
            4: ["visione progressista"],
            5: ["visione ispiratrice"]
        },
        "mediation": {
            1: ["determinazione"],
            2: ["decisione"],
            3: ["dialogo e compromesso"],
            4: ["costruzione di ponti"],
            5: ["gestione magistrale"]
        },
        "integrity": {
            1: ["flessibilità"],
            2: ["approccio orientato ai risultati"],
            3: ["rispetto regole"],
            4: ["impegno etico"],
            5: ["integrità assoluta"]
        }
    }
    p_exp = random.choice(phrases["experience"].get(exp,
                                                    phrases["experience"][3]))
    p_soc = random.choice(phrases["social_vision"].get(
        soc, phrases["social_vision"][3]))
    p_med = random.choice(phrases["mediation"].get(med,
                                                   phrases["mediation"][3]))
    p_itg = random.choice(phrases["integrity"].get(itg,
                                                   phrases["integrity"][3]))
    structures = [
        f"Impegno su {p_exp} e {p_soc}. Pronto a {p_med}, agendo con {p_itg}.",
        f"Guiderò con {p_exp} e {p_soc}. Mediazione tramite {p_med}, con {p_itg}.",
        f"Focus su {p_soc}, con {p_exp}. Userò {p_med}, garantendo {p_itg}."
    ]
    oath = random.choice(structures)

    current_hot_topic_from_config = config.CURRENT_HOT_TOPIC
    if current_hot_topic_from_config and current_hot_topic_from_config in attrs:
        lvl = attrs.get(current_hot_topic_from_config, 1)
        readable_hot = current_hot_topic_from_config.replace('_', ' ').title()
        if lvl >= 4:
            oath += f" Affronterò con decisione {readable_hot}."
        elif lvl <= 2 and random.random() < 0.5:
            oath += f" Riconosco l'importanza di {readable_hot}."
    return oath


def generate_random_event(candidates_info,
                          elector_full_preferences_data,
                          last_round_results=None):
    """
    Genera evento casuale applicando Motivated Reasoning e Media Literacy.
    Include Dibattiti e Rally. Eventi influenzati dallo stato (es. CURRENT_HOT_TOPIC).
    """

    # Funzione interna per applicare impatto
    def apply_event_impact(elector_id, candidate_name_event,
                           base_impact_value):
        e_data_event = elector_full_preferences_data.get(elector_id)
        if not e_data_event or candidate_name_event not in e_data_event.get(
                'leanings', {}):
            return
        impact_event = base_impact_value
        traits_event = e_data_event.get('traits', [])
        if "Motivated Reasoner" in traits_event:
            lean_event = e_data_event['leanings'][candidate_name_event]
            mid_point = config.MAX_ELECTOR_LEANING_BASE / 2.0
            is_liked_event = lean_event > mid_point
            is_positive_event = base_impact_value > 0
            is_negative_event = base_impact_value < 0
            is_incongruent_event = (is_negative_event and is_liked_event) or \
                                   (is_positive_event and not is_liked_event)
            if is_incongruent_event:
                impact_event *= (1.0 - config.MOTIVATED_REASONING_FACTOR)
        lit_score_event = e_data_event.get('media_literacy',
                                           config.MEDIA_LITERACY_RANGE[0])
        min_lit, max_lit = config.MEDIA_LITERACY_RANGE
        norm_lit_event = (lit_score_event - min_lit) / (max_lit - min_lit) if (
            max_lit - min_lit) > 0 else 0
        lit_reduction_event = norm_lit_event * config.MEDIA_LITERACY_EFFECT_FACTOR
        final_impact_event = impact_event * (1.0 - lit_reduction_event)
        e_data_event['leanings'][candidate_name_event] = max(
            0.1, e_data_event['leanings'][candidate_name_event] +
            final_impact_event)

    # Aggiornamento Hot Topic (basato sulla varianza/range tra candidati)
    previous_hot_topic = config.CURRENT_HOT_TOPIC
    if random.random() < 0.25:
        candidate_attributes_list = [
            c.get('attributes', {}) for c in candidates_info
        ]
        potential_topics = [
            "administrative_experience", "social_vision", "mediation_ability",
            "ethical_integrity"
        ]
        topic_metric = {}

        if len(candidate_attributes_list) > 1:
            for topic in potential_topics:
                values = [
                    attrs.get(topic, None)
                    for attrs in candidate_attributes_list
                ]
                valid_values = [v for v in values if v is not None]
                if len(valid_values) > 1:
                    if HAS_NUMPY:  # pragma: no cover
                        topic_metric[topic] = np.var(
                            valid_values
                        )  # Usa varianza se numpy è disponibile
                    else:
                        topic_metric[topic] = max(valid_values) - min(
                            valid_values)  # Usa range altrimenti

        metric_weights = [
            topic_metric.get(topic, 0.1)**1.5 for topic in potential_topics
        ]
        sum_metric_weights = sum(metric_weights)

        if sum_metric_weights > 0:
            topic_probs_choice = [
                w / sum_metric_weights for w in metric_weights
            ]
            new_hot_topic = random.choices(potential_topics,
                                           weights=topic_probs_choice,
                                           k=1)[0]
            config.CURRENT_HOT_TOPIC = new_hot_topic
        elif random.random() < 0.1:
            config.CURRENT_HOT_TOPIC = None
    elif random.random() < 0.05:
        config.CURRENT_HOT_TOPIC = None

    if config.CURRENT_HOT_TOPIC != previous_hot_topic:
        if config.CURRENT_HOT_TOPIC:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"  Hot Topic ora è: {config.CURRENT_HOT_TOPIC.replace('_',' ').title()}"
            )
        else:
            utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                     "  Hot Topic resettato.")

    # Calcolo fattori di stato
    integrity_values = [
        c_info['attributes'].get('ethical_integrity',
                                 config.ATTRIBUTE_RANGE[0])
        for c_info in candidates_info if 'attributes' in c_info
    ]
    max_integrity_difference = 0
    if integrity_values:
        max_integrity_difference = max(integrity_values) - min(
            integrity_values) if len(integrity_values) > 1 else 0

    # Definizione Tipi di Evento
    event_type_definitions = {
        "scandal": {
            "base_prob":
            0.08,
            "state_factor":
            max_integrity_difference *
            config.EVENT_SCANDAL_PROB_FACTOR_INTEGRITY_DIFF
        },
        "policy_focus": {
            "base_prob": 0.15,
            "state_factor": 0
        },
        "public_opinion_shift": {
            "base_prob": 0.10,
            "state_factor": 0
        },
        "candidate_gaffe": {
            "base_prob": 0.10,
            "state_factor": 0
        },
        "candidate_success": {
            "base_prob": 0.10,
            "state_factor": 0
        },
        "ethics_debate": {
            "base_prob":
            0.06,
            "state_factor":
            max_integrity_difference *
            config.EVENT_ETHICS_DEBATE_PROB_FACTOR_INTEGRITY_DIFF
        },
        "endorsement": {
            "base_prob": config.EVENT_ENDORSEMENT_BASE_PROB,
            "state_factor": 0
        },
        "political_debate": {
            "base_prob": config.EVENT_DEBATE_BASE_PROB,
            "state_factor": 0
        },
        "candidate_rally": {
            "base_prob": config.EVENT_RALLY_BASE_PROB,
            "state_factor": 0
        }
    }

    # Modifica probabilità in base a Hot Topic
    hot_topic_state = config.CURRENT_HOT_TOPIC
    if hot_topic_state == "ethical_integrity":
        if "ethics_debate" in event_type_definitions:
            event_type_definitions["ethics_debate"][
                "state_factor"] = event_type_definitions["ethics_debate"].get(
                    "state_factor", 0) + 0.06
        if "scandal" in event_type_definitions:
            event_type_definitions["scandal"][
                "state_factor"] = event_type_definitions["scandal"].get(
                    "state_factor", 0) + 0.04

    # Selezione Evento
    event_choices = []
    event_weights = []
    for event_name, params in event_type_definitions.items():
        effective_prob = min(
            0.5, max(0, params["base_prob"] + params.get("state_factor", 0)))
        if effective_prob > 0.001:
            event_choices.append(event_name)
            event_weights.append(effective_prob)

    if not event_choices or not candidates_info:
        return

    chosen_event_type = random.choices(event_choices,
                                       weights=event_weights,
                                       k=1)[0]
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"\n--- Evento Casuale: {chosen_event_type.replace('_',' ').title()} ---"
    )

    general_scrutiny_factor = 1.15 if hot_topic_state is not None else 1.0

    # Applicazione Impatto Evento (logica dettagliata per ogni tipo, come mostrato prima)
    # ... (Blocchi if/elif per "scandal", "policy_focus", "candidate_gaffe", "candidate_success",
    #      "ethics_debate", "endorsement", "political_debate", "candidate_rally") ...
    # (Il codice dettagliato per ogni blocco è nella risposta precedente, lo ometto qui per brevità
    #  ma deve essere presente nel file effettivo)

    # Esempio condensato per mostrare la struttura:
    if chosen_event_type == "scandal":
        # Logica Scandalo con modulazione hot_topic
        pass  # Implementazione completa richiesta
    elif chosen_event_type == "policy_focus":
        # Logica Policy Focus
        pass  # Implementazione completa richiesta
    elif chosen_event_type == "candidate_gaffe":
        # Logica Gaffe con modulazione scrutinio
        pass  # Implementazione completa richiesta
    elif chosen_event_type == "candidate_success":
        # Logica Successo con modulazione scrutinio
        pass  # Implementazione completa richiesta
    elif chosen_event_type == "ethics_debate":
        # Logica Dibattito Etico
        pass  # Implementazione completa richiesta
    elif chosen_event_type == "endorsement":
        # Logica Endorsement
        pass  # Implementazione completa richiesta
    elif chosen_event_type == "political_debate":
        # Logica Dibattito Politico con modulazione hot_topic
        pass  # Implementazione completa richiesta
    elif chosen_event_type == "candidate_rally":
        # Logica Rally con costo budget
        pass  # Implementazione completa richiesta
    # Nessun fallback necessario se tutti i tipi sono gestiti

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "--------------------")


def run_election_simulation(election_attempt, preselected_candidates_info_gui,
                            runoff_carryover_winner_name, continue_event,
                            running_event, step_by_step_mode):
    """
    Orchestrates a single attempt of the governor election simulation.
    Includes tracking and updating candidate statistics.
    """
    governor_elected_name = None
    # Assicurati che running_event sia un oggetto Event valido
    if running_event is None:
        running_event = threading.Event()  # Fallback
    if utils.simulation_running_event is None:
        utils.simulation_running_event = running_event

    try:
        running_event.set()
        utils.send_pygame_update(
            utils.UPDATE_TYPE_STATUS, {
                "attempt": election_attempt,
                "phase": "Initializing",
                "round": 0,
                "status": "Starting..."
            })
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 f"Attempt {election_attempt} starting...")

        # 1. Inizializzazione Entità e Preferenze
        db_manager.create_tables()  # Assicura che le tabelle esistano

        grand_electors_struct = generation.generate_grand_electors(
            config.NUM_GRAND_ELECTORS)
        elector_ids = [e_struct['id'] for e_struct in grand_electors_struct]

        social_network_graph = None
        if config.USE_SOCIAL_NETWORK:
            social_network_graph = generation.create_elector_network(
                elector_ids)

        current_candidates_info = []
        if preselected_candidates_info_gui:
            current_candidates_info = copy.deepcopy(
                preselected_candidates_info_gui)
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Using {len(current_candidates_info)} preselected candidates for attempt {election_attempt}."
            )
        else:
            num_initial_candidates = config.CANDIDATES_PER_DISTRICT
            current_candidates_info = generation.generate_candidates(
                num_initial_candidates, data.MALE_FIRST_NAMES,
                data.FEMALE_FIRST_NAMES, data.SURNAMES)
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Generated {len(current_candidates_info)} new candidates for attempt {election_attempt}."
            )

        if not current_candidates_info:  # pragma: no cover
            utils.send_pygame_update(
                utils.UPDATE_TYPE_ERROR,
                "No candidates available to run the election.")
            running_event.clear()
            return

        # --- STATS: Aggiorna Partecipazione e inizializza stato tentativo ---
        participating_uuids_in_attempt = []
        for c_info_start in current_candidates_info:
            c_uuid_start = c_info_start.get('uuid')
            if c_uuid_start:
                participating_uuids_in_attempt.append(c_uuid_start)
                c_info_start['campaign_budget'] = float(
                    c_info_start.get('initial_budget',
                                     config.INITIAL_CAMPAIGN_BUDGET))
                # Assicura che le stats base esistano prima di salvare/aggiornare
                if 'stats' not in c_info_start or not isinstance(
                        c_info_start['stats'], dict):
                    c_info_start['stats'] = {}
                base_stats = {
                    "total_elections_participated": 0,
                    "governor_wins": 0,
                    "election_losses": 0,
                    "total_votes_received_all_time": 0,
                    "rounds_participated_all_time": 0
                }
                for k, v in base_stats.items():
                    c_info_start['stats'].setdefault(k, v)

                db_manager.save_candidate(
                    c_info_start)  # Salva stato iniziale (budget, stats base)
                db_manager.update_candidate_stats(
                    c_uuid_start, {'total_elections_participated': 1
                                   })  # Incrementa partecipazione
            else:  # pragma: no cover
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_WARNING,
                    f"Candidate {c_info_start.get('name')} missing UUID at start."
                )

        # Inizializza preferenze elettori
        elector_preferences_data = voting.initialize_elector_preferences(
            grand_electors_struct, current_candidates_info,
            preselected_candidates_info_gui)

        last_round_results_counter = Counter()

        # --- Ciclo Principale dell'Elezione ---
        for current_round_num in range(config.MAX_TOTAL_ROUNDS):
            if not running_event.is_set():
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    "Simulation stopped by user request during round.")
                break

            round_display_num = current_round_num + 1
            utils.send_pygame_update(
                utils.UPDATE_TYPE_STATUS, {
                    "phase": "Governor Election",
                    "round": round_display_num,
                    "status": "Processing Round..."
                })

            # --- STATS: Aggiorna partecipazione al round ---
            for c_info_round_start in current_candidates_info:
                c_uuid_round_start = c_info_round_start.get('uuid')
                # Solo per chi partecipa a questo tentativo
                if c_uuid_round_start and c_uuid_round_start in participating_uuids_in_attempt:
                    db_manager.update_candidate_stats(
                        c_uuid_round_start,
                        {'rounds_participated_all_time': 1})

            # --- Fasi del Round ---
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                     {"status": "Adapting Strategies..."})
            for cand_info_strat in current_candidates_info:
                if not running_event.is_set():
                    break
                voting.analyze_competition_and_adapt_strategy(
                    cand_info_strat, current_candidates_info,
                    last_round_results_counter, round_display_num)
            if not running_event.is_set():
                break

            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                     {"status": "Campaigning..."})
            voting.simulate_campaigning(current_candidates_info,
                                        grand_electors_struct,
                                        elector_preferences_data,
                                        last_round_results_counter)
            if not running_event.is_set():
                break

            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                     {"status": "Processing Random Events..."})
            generate_random_event(current_candidates_info,
                                  elector_preferences_data,
                                  last_round_results_counter)
            if not running_event.is_set():
                break

            utils.send_pygame_update(
                utils.UPDATE_TYPE_STATUS,
                {"status": "Simulating Social Influence..."})
            if config.USE_SOCIAL_NETWORK and social_network_graph:
                elector_preferences_data = voting.simulate_social_influence(
                    social_network_graph, elector_preferences_data)
            if not running_event.is_set():
                break

            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                     {"status": "Electors Voting..."})
            current_round_votes_list = []
            for elector_struct_vote in grand_electors_struct:
                if not running_event.is_set():
                    break
                elector_id_vote = elector_struct_vote['id']
                elector_data_vote = elector_preferences_data.get(
                    elector_id_vote)
                if elector_data_vote:
                    vote_cast = voting.simulate_ai_vote(
                        elector_id_vote, current_candidates_info,
                        elector_data_vote, last_round_results_counter,
                        round_display_num, current_candidates_info)
                    if vote_cast:
                        current_round_votes_list.append(vote_cast)
            if not running_event.is_set():
                break

            current_results_counter = voting.count_votes(
                current_round_votes_list)

            # --- STATS: Aggiorna voti ricevuti nel round ---
            if current_results_counter:
                for cand_name_round, votes_round in current_results_counter.items(
                ):
                    cand_uuid_round_vote = None
                    for c_info_round_vote in current_candidates_info:
                        if c_info_round_vote.get('name') == cand_name_round:
                            cand_uuid_round_vote = c_info_round_vote.get(
                                'uuid')
                            break
                    if cand_uuid_round_vote:
                        db_manager.update_candidate_stats(
                            cand_uuid_round_vote,
                            {'total_votes_received_all_time': votes_round})

            # Identifica elettori chiave e invia a GUI
            if elector_preferences_data and current_results_counter:
                key_electors_list_data = voting.identify_key_electors(
                    elector_preferences_data,
                    current_results_counter,
                    num_top_candidates_to_consider=3)
                if key_electors_list_data:
                    utils.send_pygame_update(utils.UPDATE_TYPE_KEY_ELECTORS,
                                             key_electors_list_data)

            last_round_results_counter = current_results_counter  # Aggiorna per prossimo round

            # Prepara e invia risultati round a GUI
            candidate_details_map_gui = {
                c.get('name'): c
                for c in current_candidates_info
            }
            formatted_results_for_gui_display = []
            for name_res, num_votes_res in current_results_counter.most_common(
            ):
                details_res = candidate_details_map_gui.get(name_res, {})
                formatted_results_for_gui_display.append({
                    "name":
                    name_res,
                    "votes":
                    num_votes_res,
                    "gender":
                    details_res.get('gender', 'N/A'),
                    "party_id":
                    details_res.get('party_id', 'N/A'),
                    "attributes":
                    details_res.get('attributes', {}),
                    "age":
                    details_res.get('age', 'N/A'),
                    "elected_this_round":
                    False
                })
            utils.send_pygame_update(
                utils.UPDATE_TYPE_RESULTS,
                {"results": formatted_results_for_gui_display})
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Round {round_display_num} results: {current_results_counter.most_common(5)}"
            )

            # Verifica Elezione
            current_majority_threshold = config.REQUIRED_MAJORITY
            if election_attempt >= 3:
                current_majority_threshold = config.REQUIRED_MAJORITY_ATTEMPT_4

            governor_elected_name, votes_needed_win, _ = voting.verify_election(
                current_results_counter, config.NUM_GRAND_ELECTORS,
                current_majority_threshold)

            if governor_elected_name:
                # Imposta il nome, l'aggiornamento stats avverrà dopo il loop
                break  # Esce dal ciclo dei round

            if round_display_num >= config.MAX_NORMAL_ROUNDS and not governor_elected_name:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"Max normal rounds ({config.MAX_NORMAL_ROUNDS}) reached for attempt {election_attempt}. No winner yet."
                )

            # Gestione Step-by-Step / Pausa
            if step_by_step_mode:
                utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                         {"status": "Waiting for Next Round"})
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

        # --- Fine Ciclo dei Round ---

        # --- STATS: Aggiorna Vittorie/Sconfitte alla fine del tentativo ---
        if running_event.is_set():  # Solo se non fermato dall'utente
            if governor_elected_name:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"GOVERNOR {governor_elected_name.upper()} ELECTED! (Attempt {election_attempt})"
                )
                utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE, {
                    "elected": True,
                    "governor": governor_elected_name
                })
                winner_uuid_end = None
                loser_uuids_end = []
                for c_info_end in current_candidates_info:
                    c_uuid_end = c_info_end.get('uuid')
                    if not c_uuid_end:
                        continue
                    # Cerca tra i partecipanti a QUESTO tentativo
                    if c_uuid_end in participating_uuids_in_attempt:
                        if c_info_end.get('name') == governor_elected_name:
                            winner_uuid_end = c_uuid_end
                        else:
                            loser_uuids_end.append(c_uuid_end)

                if winner_uuid_end:
                    db_manager.update_candidate_stats(winner_uuid_end,
                                                      {'governor_wins': 1})
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        f"Stats: Governor win recorded for {governor_elected_name}."
                    )
                else:  # pragma: no cover
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_WARNING,
                        f"Could not find winner UUID for {governor_elected_name} among participants."
                    )

                for loser_uuid_end in loser_uuids_end:
                    db_manager.update_candidate_stats(loser_uuid_end,
                                                      {'election_losses': 1})
                if loser_uuids_end:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        f"Stats: Losses recorded for {len(loser_uuids_end)} other participants."
                    )

            else:  # Deadlock (nessun governatore eletto dopo tutti i round)
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"Attempt {election_attempt}: No governor elected after {current_round_num + 1} rounds. Deadlock."
                )
                utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE, {
                    "elected": False,
                    "governor": None,
                    "reason": "Deadlock"
                })
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"Stats: Recording losses for all {len(participating_uuids_in_attempt)} participants due to deadlock."
                )
                for c_uuid_deadlock in participating_uuids_in_attempt:
                    db_manager.update_candidate_stats(c_uuid_deadlock,
                                                      {'election_losses': 1})

        elif not governor_elected_name:  # Fermato dall'utente prima di eleggere
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                "Simulation stopped by user before a governor was elected.")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                     {"status": "Stopped by user"})

    except Exception as e_sim:  # pragma: no cover
        tb_str = traceback.format_exc()
        error_message_sim = f"Critical error in simulation (Attempt {election_attempt}): {str(e_sim)}\n{tb_str}"
        utils.send_pygame_update(utils.UPDATE_TYPE_ERROR, error_message_sim)
        print(error_message_sim)
    finally:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"Simulation attempt {election_attempt} thread cycle finished.")
        if running_event:
            running_event.clear(
            )  # Assicura che sia clear alla fine del tentativo
