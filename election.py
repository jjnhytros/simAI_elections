# election.py
import random
import math
import time
import copy
from collections import Counter
import sys
import threading  # Non più usato direttamente qui per avviare la GUI
import uuid
import traceback  # Per logging errori più dettagliato

# Imports da altri moduli del progetto (assoluti)
import config
import data
import utils
import voting  # Contiene la maggior parte delle funzioni di simulazione specifiche
import db_manager
import generation  # Per generare candidati, elettori, rete


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

    # Usa config.CURRENT_HOT_TOPIC invece di un parametro hot_topic locale
    # per coerenza, sebbene la funzione originale avesse un parametro.
    # Qui assumiamo che config.CURRENT_HOT_TOPIC sia la fonte autorevole.
    current_hot_topic_from_config = config.CURRENT_HOT_TOPIC
    if current_hot_topic_from_config and current_hot_topic_from_config in attrs:
        lvl = attrs.get(current_hot_topic_from_config, 1)
        readable_hot = current_hot_topic_from_config.replace('_', ' ').title()
        if lvl >= 4:
            oath += f" Affronterò con decisione {readable_hot}."
        elif lvl <= 2 and random.random() < 0.5:
            oath += f" Riconosco l'importanza di {readable_hot}."
    return oath


def generate_random_event(candidates_info, elector_full_preferences_data, last_round_results=None):
    """
    Genera evento casuale applicando Motivated Reasoning e Media Literacy.
    Include Dibattiti e Rally.
    Eventi e impatti sono ora maggiormente influenzati dallo stato (es. CURRENT_HOT_TOPIC).
    """

    # --- Funzione interna per applicare impatto (invariata) ---
    def apply_event_impact(elector_id, candidate_name_event, base_impact_value):
        # ... (codice di apply_event_impact come mostrato nella risposta precedente) ...
        e_data_event = elector_full_preferences_data.get(elector_id)
        if not e_data_event or candidate_name_event not in e_data_event.get('leanings', {}):
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
        lit_score_event = e_data_event.get(
            'media_literacy', config.MEDIA_LITERACY_RANGE[0])
        min_lit, max_lit = config.MEDIA_LITERACY_RANGE
        norm_lit_event = (lit_score_event - min_lit) / \
            (max_lit - min_lit) if (max_lit - min_lit) > 0 else 0
        lit_reduction_event = norm_lit_event * config.MEDIA_LITERACY_EFFECT_FACTOR
        final_impact_event = impact_event * (1.0 - lit_reduction_event)
        e_data_event['leanings'][candidate_name_event] = max(
            0.1, e_data_event['leanings'][candidate_name_event] +
            final_impact_event
        )

    # --- Aggiornamento Hot Topic (basato sulla varianza tra candidati) ---
    previous_hot_topic = config.CURRENT_HOT_TOPIC
    if random.random() < 0.25:  # Probabilità di rivalutare l'hot topic
        candidate_attributes_list = [
            c.get('attributes', {}) for c in candidates_info]
        potential_topics = ["administrative_experience",
                            "social_vision", "mediation_ability", "ethical_integrity"]
        topic_metric = {}  # Useremo il range come misura semplice di "differenza" o varianza

        if len(candidate_attributes_list) > 1:
            for topic in potential_topics:
                values = [attrs.get(topic, None)
                          for attrs in candidate_attributes_list]
                # Filtra None se attributo manca
                valid_values = [v for v in values if v is not None]
                if len(valid_values) > 1:
                    # Usa range (max-min) come metrica semplice della differenza
                    topic_metric[topic] = max(valid_values) - min(valid_values)
                    # Alternativa se numpy è disponibile: topic_metric[topic] = np.var(valid_values)

        # Pesi basati sulla metrica (es. range al quadrato per enfatizzare differenze maggiori)
        metric_weights = [topic_metric.get(
            topic, 0.1)**1.5 for topic in potential_topics]  # Usa 1.5 come esponente
        sum_metric_weights = sum(metric_weights)

        if sum_metric_weights > 0:
            topic_probs_choice = [
                w / sum_metric_weights for w in metric_weights]
            new_hot_topic = random.choices(
                potential_topics, weights=topic_probs_choice, k=1)[0]
            # Aggiorna sempre, potrebbe rimanere lo stesso
            config.CURRENT_HOT_TOPIC = new_hot_topic
        elif random.random() < 0.1:  # Se nessuna metrica calcolabile, piccola chance di resettare
            config.CURRENT_HOT_TOPIC = None

    elif random.random() < 0.05:  # Piccola chance di resettare l'hot topic se non è stato rivalutato
        config.CURRENT_HOT_TOPIC = None

    if config.CURRENT_HOT_TOPIC != previous_hot_topic:
        if config.CURRENT_HOT_TOPIC:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, f"  Hot Topic ora è: {config.CURRENT_HOT_TOPIC.replace('_',' ').title()}")
        else:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "  Hot Topic resettato.")

    # --- Calcolo fattori di stato (come integrità diff) ---
    integrity_values = [c_info['attributes'].get('ethical_integrity', config.ATTRIBUTE_RANGE[0])
                        for c_info in candidates_info if 'attributes' in c_info]
    max_integrity_difference = 0
    if integrity_values:
        max_integrity_difference = max(
            integrity_values) - min(integrity_values) if len(integrity_values) > 1 else 0

    # --- Definizione Tipi di Evento (con probabilità base) ---
    event_type_definitions = {
        # Prob base ridotta
        "scandal": {"base_prob": 0.08, "state_factor": max_integrity_difference * config.EVENT_SCANDAL_PROB_FACTOR_INTEGRITY_DIFF},
        "policy_focus": {"base_prob": 0.15, "state_factor": 0},
        "public_opinion_shift": {"base_prob": 0.10, "state_factor": 0},
        # Prob base ridotta
        "candidate_gaffe": {"base_prob": 0.10, "state_factor": 0},
        # Prob base ridotta
        "candidate_success": {"base_prob": 0.10, "state_factor": 0},
        # Prob base ridotta
        "ethics_debate": {"base_prob": 0.06, "state_factor": max_integrity_difference * config.EVENT_ETHICS_DEBATE_PROB_FACTOR_INTEGRITY_DIFF},
        "endorsement": {"base_prob": config.EVENT_ENDORSEMENT_BASE_PROB, "state_factor": 0},
        "political_debate": {"base_prob": config.EVENT_DEBATE_BASE_PROB, "state_factor": 0},
        "candidate_rally": {"base_prob": config.EVENT_RALLY_BASE_PROB, "state_factor": 0}
    }

    # --- Modifica probabilità in base allo stato (Hot Topic) ---
    hot_topic_state = config.CURRENT_HOT_TOPIC
    if hot_topic_state == "ethical_integrity":
        # Aumenta probabilità di eventi legati all'etica se è hot topic
        if "ethics_debate" in event_type_definitions:
            event_type_definitions["ethics_debate"]["state_factor"] = event_type_definitions["ethics_debate"].get(
                "state_factor", 0) + 0.06  # Aumento più significativo
        if "scandal" in event_type_definitions:
            event_type_definitions["scandal"]["state_factor"] = event_type_definitions["scandal"].get(
                "state_factor", 0) + 0.04  # Aumento moderato
    # Si potrebbero aggiungere altre dipendenze qui (es., hot topic "experience" aumenta prob. "policy_focus"?)

    # --- Selezione Evento (calcolando probabilità effettive) ---
    event_choices = []
    event_weights = []
    for event_name, params in event_type_definitions.items():
        # Calcola probabilità finale
        effective_prob = min(
            0.5, max(0, params["base_prob"] + params.get("state_factor", 0)))
        if effective_prob > 0.001:  # Usa una soglia minima per evitare eventi quasi impossibili
            event_choices.append(event_name)
            event_weights.append(effective_prob)

    if not event_choices or not candidates_info:
        return  # Nessun evento selezionabile o nessun candidato

    chosen_event_type = random.choices(
        event_choices, weights=event_weights, k=1)[0]
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"\n--- Evento Casuale: {chosen_event_type.replace('_',' ').title()} ---")

    # Fattore generale di scrutinio se c'è un hot topic attivo
    general_scrutiny_factor = 1.15 if hot_topic_state is not None else 1.0

    # --- Applicazione Impatto Evento (con impatto modulato da Hot Topic) ---

    if chosen_event_type == "scandal":
        if random.random() < 0.7 and integrity_values:
            target_candidate = min(candidates_info, key=lambda c: c.get(
                'attributes', {}).get('ethical_integrity', config.ATTRIBUTE_RANGE[1]))
        else:
            target_candidate = random.choice(candidates_info)
        scandal_target_name = target_candidate['name']
        scandal_base_impact = config.EVENT_SCANDAL_IMPACT * \
            ((config.ATTRIBUTE_RANGE[1] + 1) - target_candidate.get(
                'attributes', {}).get('ethical_integrity', config.ATTRIBUTE_RANGE[0]))
        # Modula impatto se hot topic è integrità
        if hot_topic_state == "ethical_integrity":
            scandal_base_impact *= 1.4  # Aumento significativo
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "    (Impatto scandalo aumentato: focus su integrità)")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  Scandalo colpisce {scandal_target_name}!")
        for elector_id_event in elector_full_preferences_data:
            apply_event_impact(
                elector_id_event, scandal_target_name, -scandal_base_impact)

    elif chosen_event_type == "policy_focus":
        focused_attribute = hot_topic_state if hot_topic_state else random.choice(
            ["administrative_experience", "social_vision", "mediation_ability", "ethical_integrity"])
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  Focus politico su: {focused_attribute.replace('_',' ').title()}!")
        for elector_id_event, e_data_event_focus in elector_full_preferences_data.items():
            elector_ideal_preference = e_data_event_focus.get(
                f'preference_{focused_attribute}', config.ELECTOR_IDEAL_PREFERENCE_RANGE[0])
            for cand_info_event in candidates_info:
                cand_attr_value = cand_info_event.get('attributes', {}).get(
                    focused_attribute, config.ATTRIBUTE_RANGE[0])
                distance_focus = abs(
                    cand_attr_value - elector_ideal_preference)
                max_possible_dist = config.ELECTOR_IDEAL_PREFERENCE_RANGE[1] - \
                    config.ELECTOR_IDEAL_PREFERENCE_RANGE[0]
                if max_possible_dist == 0:
                    max_possible_dist = 1
                normalized_distance = distance_focus / max_possible_dist
                focus_impact = random.uniform(
                    0.5, 1.5) * (1.0 - normalized_distance * 1.2)
                apply_event_impact(
                    elector_id_event, cand_info_event['name'], focus_impact)

    elif chosen_event_type == "candidate_gaffe":
        gaffe_candidate = random.choice(candidates_info)
        gaffe_impact_value = random.uniform(
            0.8, 2.0) * general_scrutiny_factor  # Modula per scrutinio generale
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  Gaffe da parte di {gaffe_candidate['name']}!")
        if general_scrutiny_factor > 1.0:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "    (Impatto leggermente aumentato per scrutinio hot topic)")
        for elector_id_event in elector_full_preferences_data:
            apply_event_impact(
                elector_id_event, gaffe_candidate['name'], -gaffe_impact_value)

    elif chosen_event_type == "candidate_success":
        success_candidate = random.choice(candidates_info)
        success_impact_value = random.uniform(
            0.8, 2.0) * general_scrutiny_factor  # Modula per scrutinio generale
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  Momento di successo per {success_candidate['name']}!")
        if general_scrutiny_factor > 1.0:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "    (Impatto leggermente aumentato per scrutinio hot topic)")
        for elector_id_event in elector_full_preferences_data:
            apply_event_impact(
                elector_id_event, success_candidate['name'], success_impact_value)

    elif chosen_event_type == "ethics_debate":
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, "  Si accende un dibattito sull'etica!")
        for elector_id_event in elector_full_preferences_data:
            for cand_info_event in candidates_info:
                cand_integrity_val = cand_info_event.get('attributes', {}).get(
                    'ethical_integrity', config.ATTRIBUTE_RANGE[0])
                norm_integrity_val = (cand_integrity_val - config.ATTRIBUTE_RANGE[0]) / \
                    (config.ATTRIBUTE_RANGE[1] - config.ATTRIBUTE_RANGE[0]) if \
                    (config.ATTRIBUTE_RANGE[1] - config.ATTRIBUTE_RANGE[0]) > 0 else 0.5
                ethics_impact = (norm_integrity_val - 0.5) * \
                    config.EVENT_ETHICS_DEBATE_IMPACT * 2
                apply_event_impact(
                    elector_id_event, cand_info_event['name'], ethics_impact)

    elif chosen_event_type == "endorsement":
        endorsed_candidate = random.choice(candidates_info)
        endorsement_impact_val = random.uniform(
            *config.EVENT_ENDORSEMENT_IMPACT_RANGE)
        # Potrebbe l'endorsement essere legato all'hot topic? Es. "Endorsement per la forte esperienza (hot topic) di X"
        # Per ora, impatto generico.
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  Un importante endorsement per {endorsed_candidate['name']}!")
        for elector_id_event in elector_full_preferences_data:
            apply_event_impact(
                elector_id_event, endorsed_candidate['name'], endorsement_impact_val)

    elif chosen_event_type == "political_debate":
        if not last_round_results:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "  Dibattito annullato (mancano risultati round precedente).")
            return
        num_participants = min(len(candidates_info),
                               config.EVENT_DEBATE_NUM_PARTICIPANTS)
        if num_participants < 2:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "  Dibattito annullato (pochi candidati).")
            return
        participants_names = [
            name for name, votes in last_round_results.most_common(num_participants)]
        participants_info = [
            c for c in candidates_info if c['name'] in participants_names]
        if len(participants_info) < 2:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "  Dibattito annullato (pochi partecipanti validi).")
            return
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  Dibattito politico tra: {', '.join(participants_names)}")
        performances = {}
        for p_info in participants_info:
            perf_score = p_info.get('attributes', {}).get(
                'mediation_ability', config.ATTRIBUTE_RANGE[0]) * random.uniform(0.8, 1.2)
            # Considera hot topic nella performance del dibattito
            if hot_topic_state and hot_topic_state in p_info.get('attributes', {}):
                ht_score = p_info['attributes'][hot_topic_state]
                # Bonus se sopra 3, malus se sotto 3 sull'hot topic
                perf_score += (ht_score - 3) * 0.2
            performances[p_info['name']] = perf_score
        avg_perf = sum(performances.values()) / \
            len(performances) if performances else 0
        for elector_id_event in elector_full_preferences_data:
            e_traits = elector_full_preferences_data.get(
                elector_id_event, {}).get('traits', [])
            for p_name, p_perf in performances.items():
                relative_perf = p_perf - avg_perf
                impact = relative_perf * config.EVENT_DEBATE_IMPACT_FACTOR * \
                    random.uniform(0.8, 1.2)
                if "CharismaFocused" in e_traits:
                    impact *= 1.5
                apply_event_impact(elector_id_event, p_name, impact)

    elif chosen_event_type == "candidate_rally":
        rally_candidate_info = random.choice(candidates_info)
        rally_candidate_name = rally_candidate_info['name']
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  {rally_candidate_name} tiene un rally!")
        max_lean = config.MAX_ELECTOR_LEANING_BASE
        favor_thresh = max_lean * config.EVENT_RALLY_FAVORABLE_THRESHOLD_FACTOR
        oppose_thresh = max_lean * config.EVENT_RALLY_OPPOSED_THRESHOLD_FACTOR
        rally_base_impact = config.EVENT_RALLY_IMPACT_FACTOR * \
            random.uniform(0.7, 1.3)
        for elector_id_event, e_data_rally in elector_full_preferences_data.items():
            current_leaning = e_data_rally.get(
                'leanings', {}).get(rally_candidate_name, 0)
            e_traits_rally = e_data_rally.get('traits', [])
            impact_modifier = 1.0
            if "Confirmation Prone" in e_traits_rally and current_leaning > favor_thresh:
                impact_modifier *= 1.5
            elif "Contrarian" in e_traits_rally and current_leaning < oppose_thresh:
                impact_modifier *= -0.5
            elif current_leaning < oppose_thresh:
                impact_modifier *= 0.2
            final_rally_impact = rally_base_impact * impact_modifier
            apply_event_impact(
                elector_id_event, rally_candidate_name, final_rally_impact)
        if config.EVENT_RALLY_BUDGET_COST > 0:
            # Trova l'indice corretto per aggiornare la lista originale
            cand_index_rally = -1
            for idx, c_info in enumerate(candidates_info):
                if c_info['name'] == rally_candidate_name:
                    cand_index_rally = idx
                    break
            if cand_index_rally != -1:
                current_budget_rally = float(
                    candidates_info[cand_index_rally].get('campaign_budget', 0))
                candidates_info[cand_index_rally]['campaign_budget'] = max(
                    0, current_budget_rally - config.EVENT_RALLY_BUDGET_COST)
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, f"    (Costo rally {config.EVENT_RALLY_BUDGET_COST} dedotto da {rally_candidate_name})")

    # Fallback non necessario se tutti i tipi in event_choices sono gestiti
    # else: ...

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "--------------------")  # Fine sezione eventi


def run_election_simulation(election_attempt, preselected_candidates_info_gui,
                            runoff_carryover_winner_name, continue_event,
                            running_event, step_by_step_mode):
    """
    Orchestrates a single attempt of the governor election simulation.
    """
    try:
        # Ensure global event is set if utils uses it
        if running_event is None or utils.simulation_running_event is None:
            if utils.simulation_running_event is None and running_event is not None:
                utils.simulation_running_event = running_event
            elif running_event is None and utils.simulation_running_event is not None:  # Should not happen if gui sets it
                running_event = utils.simulation_running_event
            else:  # Fallback if both are None
                running_event = threading.Event()
                utils.simulation_running_event = running_event

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
        db_manager.create_tables()

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

        if not current_candidates_info:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_ERROR,
                "No candidates available to run the election.")
            running_event.clear()
            return

        for cand_info_init in current_candidates_info:
            cand_info_init['campaign_budget'] = float(
                cand_info_init.get('initial_budget',
                                   config.INITIAL_CAMPAIGN_BUDGET))
            db_manager.save_candidate(cand_info_init)
            if 'current_campaign_themes' not in cand_info_init or not cand_info_init[
                    'current_campaign_themes']:
                sorted_candidate_attrs = sorted(cand_info_init.get(
                    "attributes", {}).items(),
                    key=lambda item: item[1],
                    reverse=True)
                cand_info_init['current_campaign_themes'] = [
                    attr_tuple[0] for attr_tuple in
                    sorted_candidate_attrs[:random.randint(1, 2)]
                ] if sorted_candidate_attrs else ["social_vision"]

        elector_preferences_data = voting.initialize_elector_preferences(
            grand_electors_struct, current_candidates_info,
            preselected_candidates_info_gui)

        governor_elected_name = None
        last_round_results_counter = Counter()

        # 2. Ciclo Principale dell'Elezione (Round)
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
                    "status": "Adapting Strategies..."
                })
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

            # Identifica e invia gli elettori chiave
            if elector_preferences_data and current_results_counter:
                key_electors_list_data = voting.identify_key_electors(
                    elector_preferences_data,
                    current_results_counter,
                    num_top_candidates_to_consider=3)
                if key_electors_list_data:
                    utils.send_pygame_update(utils.UPDATE_TYPE_KEY_ELECTORS,
                                             key_electors_list_data)

            last_round_results_counter = current_results_counter  # Per il prossimo round

            # Prepara risultati per GUI
            candidate_details_map_gui = {
                c['name']: c
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
                    False  # Sarà aggiornato da verify_election
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
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"GOVERNOR {governor_elected_name.upper()} ELECTED in round {round_display_num} (Attempt {election_attempt})!"
                )
                utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE, {
                    "elected": True,
                    "governor": governor_elected_name
                })
                # TODO: Aggiornare statistiche candidati nel DB (vittorie, etc.)
                break  # Esce dal ciclo dei round

            if round_display_num >= config.MAX_NORMAL_ROUNDS and not governor_elected_name:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"Max normal rounds ({config.MAX_NORMAL_ROUNDS}) reached for attempt {election_attempt}. No winner yet."
                )
                # Qui potrebbe esserci logica per runoff o eliminazione candidati, se implementata.
                # Altrimenti, la simulazione continua fino a MAX_TOTAL_ROUNDS.

            # Gestione Modalità Step-by-Step
            if step_by_step_mode:
                utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                         {"status": "Waiting for Next Round"})
                continue_event.clear()
                if not running_event.is_set():
                    break
                continue_event.wait()  # Attende segnale dalla GUI
                if not running_event.is_set():
                    break
            else:  # Modalità continua
                if not running_event.is_set():
                    break
                time.sleep(config.GOVERNOR_PAUSE_SECONDS)

        # 3. Fine Simulazione per questo tentativo (dopo il ciclo dei round)
        if not governor_elected_name and running_event.is_set(
        ):  # Se il ciclo è terminato senza un eletto e non per stop utente
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Attempt {election_attempt}: No governor elected after {config.MAX_TOTAL_ROUNDS} rounds. Deadlock."
            )
            utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE, {
                "elected": False,
                "governor": None,
                "reason": "Deadlock"
            })
        elif not running_event.is_set(
        ) and not governor_elected_name:  # Se fermato dall'utente prima di eleggere
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                "Simulation stopped by user before a governor was elected.")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                     {"status": "Stopped by user"})

    except Exception as e_sim:
        tb_str = traceback.format_exc()
        error_message_sim = f"Critical error in simulation (Attempt {election_attempt}): {str(e_sim)}\n{tb_str}"
        utils.send_pygame_update(utils.UPDATE_TYPE_ERROR, error_message_sim)
        print(error_message_sim)  # Stampa anche sulla console per debug
    finally:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"Simulation attempt {election_attempt} thread cycle finished.")
        if running_event:  # Assicurati che running_event esista prima di chiamare clear
            running_event.clear()


# Il blocco if __name__ == "__main__": è stato rimosso da election.py
# per renderlo un modulo la cui logica è chiamata da gui.py (che ora è l'entry point).
# Per testare election.py separatamente, si potrebbe aggiungere un blocco main specifico per test.
