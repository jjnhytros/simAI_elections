import random
import math
import time
import copy
from collections import Counter
import sys
import threading
import networkx as nx
import uuid

# Imports da altri moduli del progetto (assoluti)
import config
import data  # Per accedere alle liste di nomi, etc.
import utils
import voting  # Contiene la maggior parte delle funzioni di simulazione specifiche
import db_manager
import generation  # Per generare candidati, elettori, rete

# Le funzioni come generate_random_event, generate_candidate_oath
# e le versioni precedenti di initialize_elector_preferences, simulate_ai_vote etc.
# sono state spostate in voting.py o rifattorizzate.
# Qui manteniamo solo ciò che è specifico per l'orchestrazione dell'elezione.


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
    hot = config.CURRENT_HOT_TOPIC
    if hot and hot in attrs:  # Assicurati che hot sia una chiave valida per attrs
        lvl = attrs.get(hot, 1)  # Default a 1 se hot non è in attrs
        readable_hot = hot.replace('_', ' ').title()
        if lvl >= 4:
            oath += f" Affronterò con decisione {readable_hot}."
        elif lvl <= 2 and random.random() < 0.5:
            oath += f" Riconosco l'importanza di {readable_hot}."
    return oath


def generate_random_event(candidates_info,
                          elector_full_preferences_data,
                          last_round_results=None):
    """Genera evento casuale applicando Motivated Reasoning e Media Literacy."""

    def apply_event_impact(elector_id, candidate_name, base_impact_value):
        e_data = elector_full_preferences_data.get(elector_id)
        if not e_data or candidate_name not in e_data.get('leanings', {}):
            return
        impact = base_impact_value
        traits = e_data.get('traits', [])
        if "Motivated Reasoner" in traits:
            lean = e_data['leanings'][candidate_name]
            mid = config.MAX_ELECTOR_LEANING_BASE / 2.0
            liked = lean > mid
            pos_event = base_impact_value > 0
            neg_event = base_impact_value < 0
            incongruent = (neg_event and liked) or (pos_event and not liked)
            if incongruent:
                impact *= (1.0 - config.MOTIVATED_REASONING_FACTOR)

        lit_score = e_data.get('media_literacy',
                               config.MEDIA_LITERACY_RANGE[0])
        min_l, max_l = config.MEDIA_LITERACY_RANGE
        norm_lit = (lit_score - min_l) / (max_l - min_l) if (max_l -
                                                             min_l) > 0 else 0
        lit_reduc = norm_lit * config.MEDIA_LITERACY_EFFECT_FACTOR
        final_impact = impact * (1.0 - lit_reduc)

        e_data['leanings'][candidate_name] = max(
            0.1, e_data['leanings'][candidate_name] + final_impact)

    if random.random() < 0.15:
        config.CURRENT_HOT_TOPIC = random.choice([
            "administrative_experience", "social_vision", "mediation_ability",
            "ethical_integrity"
        ])
    elif random.random() < 0.05:
        config.CURRENT_HOT_TOPIC = None

    integrity_vals = [
        c['attributes'].get('ethical_integrity', 1) for c in candidates_info
        if 'attributes' in c
    ]
    max_integ_diff = 0
    if integrity_vals:
        max_integ_diff = max(integrity_vals) - min(integrity_vals) if len(
            integrity_vals) > 1 else 0

    event_types = {
        "scandal": {
            "base_prob":
            0.10,
            "state_factor":
            max_integ_diff * config.EVENT_SCANDAL_PROB_FACTOR_INTEGRITY_DIFF
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
            "base_prob": 0.12,
            "state_factor": 0
        },
        "candidate_success": {
            "base_prob": 0.12,
            "state_factor": 0
        },
        "ethics_debate": {
            "base_prob":
            0.08,
            "state_factor":
            max_integ_diff *
            config.EVENT_ETHICS_DEBATE_PROB_FACTOR_INTEGRITY_DIFF
        },
        "endorsement": {
            "base_prob": config.EVENT_ENDORSEMENT_BASE_PROB,
            "state_factor": 0
        }
    }
    choices = []
    weights = []
    for et, params in event_types.items():
        prob = min(0.5,
                   max(0, params["base_prob"] + params.get("state_factor", 0)))
        if prob > 0:
            choices.append(et)
            weights.append(prob)

    if not choices or not candidates_info:  # Aggiunto controllo candidates_info
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "Nessun evento casuale generabile o nessun candidato.")
        return

    chosen_event = random.choices(choices, weights=weights, k=1)[0]
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"\n--- Evento Casuale: {chosen_event.replace('_',' ').title()} ---")

    if chosen_event == "scandal":
        scandalized_cand = min(
            candidates_info,
            key=lambda c: c.get('attributes', {}).get('ethical_integrity', 5))
        scandalized_name = scandalized_cand['name']
        scandal_impact_value = random.uniform(1.0, 3.0) * (
            6 -
            scandalized_cand.get('attributes', {}).get('ethical_integrity', 5))
        if random.random() < 0.3:  # Chance it hits a random candidate instead
            scandalized_name = random.choice(candidates_info)['name']
            scandal_impact_value = random.uniform(1.0, 2.0)

        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 f"  Scandalo su {scandalized_name}!")
        base_neg_impact = -scandal_impact_value
        for e_id in elector_full_preferences_data:
            apply_event_impact(e_id, scandalized_name, base_neg_impact)

    elif chosen_event == "policy_focus":
        attr_focused = random.choice([
            "administrative_experience", "social_vision", "mediation_ability",
            "ethical_integrity"
        ])
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  Focus su {attr_focused.replace('_',' ').title()}!")
        for e_id, e_data in elector_full_preferences_data.items():
            if not e_data:
                continue
            e_ideal_pref = e_data.get(f'preference_{attr_focused}',
                                      config.ELECTOR_IDEAL_PREFERENCE_RANGE[0])
            for cand in candidates_info:
                cand_attr_val = cand.get('attributes',
                                         {}).get(attr_focused,
                                                 config.ATTRIBUTE_RANGE[0])
                distance = abs(cand_attr_val - e_ideal_pref)
                max_dist = config.ELECTOR_IDEAL_PREFERENCE_RANGE[
                    1] - config.ELECTOR_IDEAL_PREFERENCE_RANGE[0]
                if max_dist == 0:
                    max_dist = 1
                norm_dist = distance / max_dist
                base_impact = random.uniform(0.5,
                                             1.5) * (1.0 - norm_dist * 1.5)
                apply_event_impact(e_id, cand['name'], base_impact)

    # Aggiungere logica per altri tipi di eventi come "public_opinion_shift", "candidate_gaffe", etc.
    # ... (implementazione simile per altri eventi) ...

    else:  # Fallback per eventi non completamente implementati sopra
        target_cand_name = random.choice(candidates_info)['name']
        impact_sign = random.choice([-1, 1])
        base_impact = impact_sign * random.uniform(0.5, 1.5)
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  Evento generico per {target_cand_name} (impatto: {base_impact:.2f})"
        )
        for e_id in elector_full_preferences_data:
            apply_event_impact(e_id, target_cand_name, base_impact)

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "--------------------")


def run_election_simulation(election_attempt, preselected_candidates_info_gui,
                            runoff_carryover_winner_name, continue_event,
                            running_event, step_by_step_mode):
    try:
        running_event.set()  # Segnala alla GUI che la simulazione è partita
        utils.send_pygame_update(
            utils.UPDATE_TYPE_STATUS, {
                "attempt": election_attempt,
                "phase": "Initializing",
                "round": 0,
                "status": "Starting..."
            })
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 f"Attempt {election_attempt} starting...")

        # 1. Inizializzazione
        db_manager.create_tables()

        grand_electors_struct = generation.generate_grand_electors(
            config.NUM_GRAND_ELECTORS)
        elector_ids = [e['id'] for e in grand_electors_struct]

        social_network_graph = None
        if config.USE_SOCIAL_NETWORK:
            social_network_graph = generation.create_elector_network(
                elector_ids)

        current_candidates_info = []
        if preselected_candidates_info_gui:  # Dati passati dalla GUI
            current_candidates_info = copy.deepcopy(
                preselected_candidates_info_gui)  # Usa una copia
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Using {len(current_candidates_info)} preselected candidates for attempt {election_attempt}."
            )
        else:
            # Usiamo questo come numero base di candidati per il governatore
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
            return

        # Inizializza/resetta temi e budget per i candidati all'inizio di un nuovo tentativo
        for cand_info in current_candidates_info:
            cand_info['campaign_budget'] = float(
                cand_info.get('initial_budget', config.INITIAL_CAMPAIGN_BUDGET)
            )  # Resetta al budget iniziale
            db_manager.save_candidate(
                cand_info
            )  # Salva per assicurare che il budget sia aggiornato nel DB
            if 'current_campaign_themes' not in cand_info or not cand_info[
                    'current_campaign_themes']:
                sorted_attrs = sorted(cand_info.get("attributes", {}).items(),
                                      key=lambda i: i[1],
                                      reverse=True)
                cand_info['current_campaign_themes'] = [
                    a[0] for a in sorted_attrs[:random.randint(1, 2)]
                ] if sorted_attrs else ["social_vision"]

        elector_preferences_data = voting.initialize_elector_preferences(
            grand_electors_struct,
            current_candidates_info,
            # Questo serve per il boost iniziale se i candidati sono pre-selezionati
            preselected_candidates_info_gui
        )

        governor_elected = None
        last_round_results_counter = Counter()

        # 2. Ciclo Principale dell'Elezione
        for current_round in range(config.MAX_TOTAL_ROUNDS):
            if not running_event.is_set():
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    "Simulation stopped by user request.")
                break

            utils.send_pygame_update(
                utils.UPDATE_TYPE_STATUS, {
                    "phase": "Governor Election",
                    "round": current_round + 1,
                    "status": "Adapting Strategies..."
                })
            for cand_info in current_candidates_info:
                if not running_event.is_set():
                    break
                voting.analyze_competition_and_adapt_strategy(
                    cand_info, current_candidates_info,
                    last_round_results_counter, current_round)
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
                                     {"status": "Random Events..."})
            generate_random_event(current_candidates_info,
                                  elector_preferences_data,
                                  last_round_results_counter)
            if not running_event.is_set():
                break

            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                     {"status": "Social Influence..."})
            if config.USE_SOCIAL_NETWORK and social_network_graph:
                elector_preferences_data = voting.simulate_social_influence(
                    social_network_graph, elector_preferences_data)
            if not running_event.is_set():
                break

            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                     {"status": "Voting..."})
            round_votes = []
            for elector_struct in grand_electors_struct:
                if not running_event.is_set():
                    break
                e_id = elector_struct['id']
                e_data = elector_preferences_data.get(e_id)
                if e_data:
                    vote = voting.simulate_ai_vote(e_id,
                                                   current_candidates_info,
                                                   e_data,
                                                   last_round_results_counter,
                                                   current_round,
                                                   current_candidates_info)
                    if vote:
                        round_votes.append(vote)
            if not running_event.is_set():
                break

            current_results_counter = voting.count_votes(round_votes)
            last_round_results_counter = current_results_counter

            candidate_details_map = {
                c['name']: c
                for c in current_candidates_info
            }
            formatted_results_for_gui = []
            for name, num_votes in current_results_counter.most_common():
                details = candidate_details_map.get(name, {})
                formatted_results_for_gui.append({
                    "name":
                    name,
                    "votes":
                    num_votes,
                    "gender":
                    details.get('gender', 'N/A'),
                    "party_id":
                    details.get('party_id', 'N/A'),
                    "attributes":
                    details.get('attributes', {}),
                    "age":
                    details.get('age', 'N/A'),
                    "elected_this_round":
                    False
                })
            utils.send_pygame_update(utils.UPDATE_TYPE_RESULTS,
                                     {"results": formatted_results_for_gui})
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Round {current_round + 1} results: {current_results_counter.most_common(5)}"
            )

            majority_threshold = config.REQUIRED_MAJORITY
            # Tentativi 3, 4, 5, 6 (se MAX_ATTEMPTS è 6)
            if election_attempt >= 3:
                majority_threshold = config.REQUIRED_MAJORITY_ATTEMPT_4  # Soglia ridotta

            governor_elected, votes_needed, _ = voting.verify_election(
                current_results_counter, config.NUM_GRAND_ELECTORS,
                majority_threshold)

            if governor_elected:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"GOVERNOR {governor_elected} ELECTED in round {current_round + 1} (Attempt {election_attempt})!"
                )
                utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE, {
                    "elected": True,
                    "governor": governor_elected
                })
                # Qui potresti aggiornare le stats dei candidati nel DB
                break

            if current_round + 1 >= config.MAX_NORMAL_ROUNDS and not governor_elected:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"Max normal rounds ({config.MAX_NORMAL_ROUNDS}) reached for attempt {election_attempt}."
                )
                # Implementa logica di spareggio o eliminazione candidati se necessario
                # Per ora, si continua fino a MAX_TOTAL_ROUNDS o elezione

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

        # 3. Fine Simulazione per questo tentativo
        if not governor_elected and running_event.is_set():
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Attempt {election_attempt}: No governor elected after {config.MAX_TOTAL_ROUNDS} rounds. Deadlock."
            )
            utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE, {
                "elected": False,
                "governor": None,
                "reason": "Deadlock"
            })
        elif not running_event.is_set() and not governor_elected:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                "Simulation stopped by user before completion.")
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS,
                                     {"status": "Stopped by user"})

    except Exception as e:
        import traceback
        error_message = f"Critical error in simulation (Attempt {election_attempt}): {str(e)}\n{traceback.format_exc()}"
        utils.send_pygame_update(utils.UPDATE_TYPE_ERROR, error_message)
        print(error_message)
    finally:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"Simulation attempt {election_attempt} thread cycle ended.")
        running_event.clear()  # Assicura che running_event sia clear alla fine


# Rimosso il blocco if __name__ == "__main__" che avviava la GUI da qui.
# election.py ora è un modulo che fornisce la logica di simulazione.
# L'avvio dell'applicazione avverrà da gui.py.
