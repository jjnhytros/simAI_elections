import random
import math
import time
import copy
from collections import Counter
import sys
import threading
import networkx as nx
# Imports da altri moduli del progetto (assoluti)
import config
import data
import utils
import generation
import voting  # Importa il modulo voting aggiornato

# Funzione per identificare elettori chiave


def identify_key_electors(elector_preferences_data, current_results, num_top_candidates_to_consider=3):
    """Identifica elettori chiave (swing, influenzabili)."""
    key_electors_summary = []
    if not elector_preferences_data or not current_results:
        return key_electors_summary
    top_cand_names = [item[0] for item in current_results.most_common(
        num_top_candidates_to_consider)]

    for e_id, data in elector_preferences_data.items():
        traits = data.get('traits', [])
        leanings = data.get('leanings', {})
        is_key = False
        reasons = []
        if "Easily Influenced" in traits:
            is_key = True
            reasons.append("Easily Influenced")
        if "Swing Voter" in traits:
            is_key = True
            reasons.append("Is a Swing Voter")
        if leanings and len(top_cand_names) >= 2:
            top_leans = sorted([{'name': cn, 'leaning': leanings[cn]}
                               for cn in top_cand_names if cn in leanings], key=lambda x: x['leaning'], reverse=True)
            if len(top_leans) >= 2:
                diff = top_leans[0]['leaning'] - top_leans[1]['leaning']
                if abs(diff) < config.ELECTOR_SWING_THRESHOLD:
                    is_key = True
                    reasons.append(
                        f"Swing b/w {top_leans[0]['name']} ({top_leans[0]['leaning']:.1f}) & {top_leans[1]['name']} ({top_leans[1]['leaning']:.1f})")
        if is_key:
            key_electors_summary.append(
                {"id": e_id, "reasons": list(set(reasons))})
    return key_electors_summary

# Funzione per generare giuramento candidato


def generate_candidate_oath(candidate_info, hot_topic=None):
    """Genera un giuramento/dichiarazione d'intenti più variata."""
    attrs = candidate_info.get("attributes", {})
    exp = attrs.get("administrative_experience", 1)
    soc = attrs.get("social_vision", 1)
    med = attrs.get("mediation_ability", 1)
    itg = attrs.get("ethical_integrity", 1)
    phrases = {
        "experience": {1: ["impegno a sviluppare esperienza"], 2: ["volontà di acquisire competenze"], 3: ["solida base gestionale"], 4: ["forte leadership"], 5: ["leadership esperta"]},
        "social_vision": {1: ["approccio pragmatico"], 2: ["attenzione alle necessità"], 3: ["equilibrio sociale"], 4: ["visione progressista"], 5: ["visione ispiratrice"]},
        "mediation": {1: ["determinazione"], 2: ["decisione"], 3: ["dialogo e compromesso"], 4: ["costruzione di ponti"], 5: ["gestione magistrale"]},
        "integrity": {1: ["flessibilità"], 2: ["approccio orientato ai risultati"], 3: ["rispetto regole"], 4: ["impegno etico"], 5: ["integrità assoluta"]}
    }
    p_exp = random.choice(phrases["experience"].get(
        exp, phrases["experience"][3]))
    p_soc = random.choice(phrases["social_vision"].get(
        soc, phrases["social_vision"][3]))
    p_med = random.choice(phrases["mediation"].get(
        med, phrases["mediation"][3]))
    p_itg = random.choice(phrases["integrity"].get(
        itg, phrases["integrity"][3]))
    structures = [f"Impegno su {p_exp} e {p_soc}. Pronto a {p_med}, agendo con {p_itg}.",
                  f"Guiderò con {p_exp} e {p_soc}. Mediazione tramite {p_med}, con {p_itg}.", f"Focus su {p_soc}, con {p_exp}. Userò {p_med}, garantendo {p_itg}."]
    oath = random.choice(structures)
    hot = config.CURRENT_HOT_TOPIC
    if hot and hot in attrs:
        lvl = attrs[hot]
        readable = hot.replace('_', ' ').title()
        if lvl >= 4:
            oath += f" Affronterò con decisione {readable}."
        elif lvl <= 2 and random.random() < 0.5:
            oath += f" Riconosco l'importanza di {readable}."
    return oath

# Funzione per generare eventi casuali


def generate_random_event(candidates_info, elector_full_preferences_data, last_round_results=None):
    """Genera evento casuale applicando Motivated Reasoning e Media Literacy."""
    def apply_event_impact(elector_id, candidate_name, base_impact_value):
        e_data = elector_full_preferences_data.get(elector_id)
        if not e_data or candidate_name not in e_data.get('leanings', {}):
            return
        impact = base_impact_value
        traits = e_data.get('traits', [])
        # Motivated Reasoning
        if "Motivated Reasoner" in traits:
            lean = e_data['leanings'][candidate_name]
            mid = config.MAX_ELECTOR_LEANING_BASE / 2.0
            liked = lean > mid
            pos = base_impact_value > 0
            neg = base_impact_value < 0
            incongruent = (neg and liked) or (pos and not liked)
            if incongruent:
                impact *= (1.0 - config.MOTIVATED_REASONING_FACTOR)
        # Media Literacy
        lit_score = e_data.get(
            'media_literacy', config.MEDIA_LITERACY_RANGE[0])
        min_l, max_l = config.MEDIA_LITERACY_RANGE
        norm_lit = (lit_score - min_l) / \
            (max_l - min_l) if (max_l - min_l) > 0 else 0
        lit_reduc = norm_lit * config.MEDIA_LITERACY_EFFECT_FACTOR
        final_impact = impact * (1.0 - lit_reduc)
        # Apply
        e_data['leanings'][candidate_name] = max(
            0.1, e_data['leanings'][candidate_name] + final_impact)

    # Hot Topic & Event Selection
    if random.random() < 0.15:
        config.CURRENT_HOT_TOPIC = random.choice(
            ["administrative_experience", "social_vision", "mediation_ability", "ethical_integrity"])
    elif random.random() < 0.05:
        config.CURRENT_HOT_TOPIC = None
    integrity_vals = [c['attributes'].get(
        'ethical_integrity', 1) for c in candidates_info]
    max_integ_diff = max(
        integrity_vals) - min(integrity_vals) if integrity_vals and len(integrity_vals) > 1 else 0
    event_types = {  # Probabilità riviste
        "scandal": {"base_prob": 0.10, "state_factor": max_integ_diff * config.EVENT_SCANDAL_PROB_FACTOR_INTEGRITY_DIFF},
        "policy_focus": {"base_prob": 0.15, "state_factor": 0},
        "public_opinion_shift": {"base_prob": 0.10, "state_factor": 0},
        "candidate_gaffe": {"base_prob": 0.12, "state_factor": 0},
        "candidate_success": {"base_prob": 0.12, "state_factor": 0},
        "ethics_debate": {"base_prob": 0.08, "state_factor": max_integ_diff * config.EVENT_ETHICS_DEBATE_PROB_FACTOR_INTEGRITY_DIFF},
        "endorsement": {"base_prob": config.EVENT_ENDORSEMENT_BASE_PROB, "state_factor": 0}
    }
    choices = []
    weights = []
    for et, params in event_types.items():
        prob = min(
            0.5, max(0, params["base_prob"] + params.get("state_factor", 0)))
        if prob > 0:
            choices.append(et)
            weights.append(prob)
    if not choices:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, "Nessun evento casuale.")
        return
    chosen_event = random.choices(choices, weights=weights, k=1)[0]
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"\n--- Evento Casuale: {chosen_event.replace('_',' ').title()} ---")

    # Apply Event Impact
    if chosen_event == "scandal" and candidates_info:
        # ... (scegli scandalized_name) ...
        # Calcola base_neg_impact = -scandal_impact
        # for e_id in elector_full_preferences_data: apply_event_impact(e_id, scandalized_name, base_neg_impact)
        pass  # Logica dettagliata omessa per brevità, ma usa apply_event_impact
    elif chosen_event == "policy_focus" and candidates_info:
        # ... (scegli attr_focused) ...
        # for e_id in elector_full_preferences_data:
        #    for cand in candidates_info:
        #        if (...condizioni...): base_pos_impact = ... ; apply_event_impact(e_id, cand['name'], base_pos_impact)
        pass  # Logica dettagliata omessa
    elif chosen_event == "public_opinion_shift" and candidates_info:
        # ... (scegli attr_shifted, shift_dir) ...
        # for e_id in elector_full_preferences_data:
        #    for cand in candidates_info: base_impact = ... ; apply_event_impact(e_id, cand['name'], base_impact)
        pass  # Logica dettagliata omessa
    elif chosen_event == "candidate_gaffe" and candidates_info:
        # ... (scegli gaffe_name) ...
        # base_neg_impact = -gaffe_impact
        # for e_id in elector_full_preferences_data: apply_event_impact(e_id, gaffe_name, base_neg_impact)
        pass  # Logica dettagliata omessa
    elif chosen_event == "candidate_success" and candidates_info:
        # ... (scegli success_name) ...
        # for e_id in elector_full_preferences_data: impact_adj = ... ; apply_event_impact(e_id, success_name, impact_adj)
        pass  # Logica dettagliata omessa
    elif chosen_event == "ethics_debate" and candidates_info:
        # ... (calcola base_impact per ogni cand/elettore) ...
        # for e_id in elector_full_preferences_data:
        #     for cand in candidates_info: base_impact = ... ; apply_event_impact(e_id, cand['name'], base_impact)
        pass  # Logica dettagliata omessa
    elif chosen_event == "endorsement" and candidates_info:
        # ... (scegli endorsed_name) ...
        # for e_id in elector_full_preferences_data: impact_adj = ... ; apply_event_impact(e_id, endorsed_name, impact_adj)
        pass  # Logica dettagliata omessa

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "--------------------")

# Funzione per simulare la campagna distrettuale


def simulate_district_campaigning(district_candidates_info, citizen_data):
    """Simula le campagne dei candidati distrettuali."""
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulazione Campagna Distrettuale ---")
    if not district_candidates_info or not citizen_data:
        return
    total_attempts, successful_impacts = 0, 0
    citizen_ids = list(citizen_data.keys())
    if not citizen_ids:
        return
    for cand in district_candidates_info:
        attrs = cand.get("attributes", {})
        abil = (attrs.get('med', 1) + attrs.get('soc', 1)) / 2.0
        n_inf = min(config.INFLUENCE_CITIZENS_PER_CANDIDATE, len(citizen_ids))
        if n_inf <= 0:
            continue
        targets = random.sample(citizen_ids, n_inf)
        for c_id in targets:
            total_attempts += 1
            c_info = citizen_data[c_id]
            traits = c_info.get('traits', [])
            sus = config.CITIZEN_SUSCEPTIBILITY_BASE + \
                random.uniform(-0.1, 0.1)
            if "RI" in traits:
                sus *= config.CITIZEN_TRAIT_MULTIPLIER_RANDOM_INCLINED  # Abbreviazione esempio
            if "AF" in traits:
                sus *= config.CITIZEN_TRAIT_MULTIPLIER_ATTRIBUTE_FOCUSED
            sus = max(0.1, min(1.0, sus))
            chance = (abil / config.ATTRIBUTE_RANGE[1]) * sus
            if random.random() < chance:
                successful_impacts += 1
                inf = getattr(config, "CAMPIGN_INF_STR_CIT",
                              0.05)*random.uniform(0.8, 1.2)
                for attr, val in attrs.items():
                    pk = f"preference_{attr}"
                    if pk in c_info:
                        curr = c_info[pk]
                        adj = (val-curr)*inf
                        c_info[pk] = max(1, min(5, curr+adj))
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"  Riepilogo Campagna Distr.: Tentativi {total_attempts}, Impatti {successful_impacts}")

# Esecuzione elezione distrettuale


def execute_district_election(district_id, winners_to_elect, continue_event=None, running_event=None, step_by_step_mode=False):
    """Simulates the election in a single district."""
    if continue_event and step_by_step_mode:
        utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                 "phase": "District Election", "round": district_id, "status": f"District {district_id} - Waiting..."})
        time.sleep(0.05)
        continue_event.wait()
        continue_event.clear()
    try:  # Check Pygame
        import pygame
        if running_event and not pygame.display.get_init():
            running_event.clear()
            return []
    except ImportError:
        pass

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"\n--- District {district_id} Election ---")
    utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                             "phase": "District Elections", "round": district_id, "status": f"Distr {district_id} Voting"})
    dist_cands = generation.generate_candidates(
        config.CANDIDATES_PER_DISTRICT, data.MALE_FIRST_NAMES, data.FEMALE_FIRST_NAMES, data.SURNAMES)
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"  Cands in Distr {district_id}: {len(dist_cands)}")
    citizens = voting.initialize_citizen_preferences(
        config.CITIZENS_PER_DISTRICT, dist_cands)
    # Esegui campagna distrettuale
    simulate_district_campaigning(dist_cands, citizens)
    dist_votes = [voting.simulate_citizen_vote(
        cid, dist_cands, cinfo) for cid, cinfo in citizens.items()]
    dist_votes = [v for v in dist_votes if v is not None]
    dist_results = voting.count_votes(dist_votes)
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"  Distr {district_id} Vote Results:")
    winners_info = []
    winners_names = set()
    if dist_results:
        if winners_to_elect > 0:
            actual_elected = min(winners_to_elect, len(dist_results))
            if actual_elected < winners_to_elect:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, f"    Warn: Only {actual_elected}/{winners_to_elect} elected in Distr {district_id}.")
            winners_names = set(c[0]
                                for c in dist_results.most_common(actual_elected))
            winners_info = [
                c for c in dist_cands if c["name"] in winners_names]
        else:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, f"    Distr {district_id} elects 0.")
    else:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"    No valid votes in Distr {district_id}.")
    # GUI Results
    gui_res = []
    cand_dict = {c["name"]: c for c in dist_cands}
    for name, votes in dist_results.most_common():
        info = cand_dict.get(name, {})
        gui_res.append({"name": name, "votes": votes, "elected": name in winners_names,
                       "gender": info.get('gender', '?'), "age": info.get('age', '?')})
    utils.send_pygame_update(utils.UPDATE_TYPE_RESULTS, {
                             "type": "district", "district_id": district_id, "results": gui_res})
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"  Distr {district_id} Winners: {[w['name'] for w in winners_info]}")
    return winners_info

# Esecuzione round di voto del collegio


def execute_voting_round(current_voting_electors_ids, votable_candidates_info, elector_prefs_data, last_results=None, num_electors_base=0, req_maj_perc=0.6, current_round=0, all_cands_info=None, carryover_name=None, continue_event=None, running_event=None, step_mode=False):
    """Executes a single AI voting round for the College."""
    if continue_event and step_mode:
        utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                                 "phase": "College Election", "round": current_round, "status": "Waiting..."})
        time.sleep(0.05)
        continue_event.wait()
        continue_event.clear()
    try:  # Check Pygame
        import pygame
        if running_event and not pygame.display.get_init():
            running_event.clear()
            return None, Counter(), elector_prefs_data, 0
    except ImportError:
        pass

    utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                             "phase": "College Election", "round": current_round, "status": "Voting..."})
    round_votes = []
    local_prefs = copy.deepcopy(elector_prefs_data)

    # Momentum
    if last_results and num_electors_base > 0 and current_round > 0:
        ref_key = next(iter(local_prefs), None)
        cands = list(local_prefs[ref_key]
                     ['leanings'].keys()) if ref_key else []
        if cands:
            avg = 1.0/len(cands)
        for e_id in local_prefs:
            d = local_prefs[e_id]
            l = d.get(
                'l', {})
            t = d.get('t', [])
            mod = 1.0
        if "SV" in t:
            mod *= 1.5  # Abbreviazioni esempio
        if "L" in t:
            mod *= 0.5
        if "C" in t:
            mod *= -0.5
        for cn in cands:
            p = last_results.get(cn, 0)/num_electors_base
            adj = (p-avg) * config.ELECTOR_MOMENTUM_FACTOR * \
                config.MAX_ELECTOR_LEANING_BASE*mod
        if cn in l:
            l[cn] = max(0.1, l[cn]+adj)

    # Carryover Bonus
    if current_round == 1 and carryover_name is not None:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"\nApplying +{config.RUNOFF_CARRYOVER_LEANING_BONUS:.1f} bonus to {carryover_name}.")
        for e_id in local_prefs:
            l = local_prefs[e_id].get('l', {})
        if carryover_name in l:
            l[carryover_name] = max(
                0.1, l[carryover_name]+config.RUNOFF_CARRYOVER_LEANING_BONUS)

    # Simulate votes
    for e_id in current_voting_electors_ids:
        e_data = local_prefs.get(e_id, {})
        if not e_data:
            continue
        vote = voting.simulate_ai_vote(
            e_id, votable_candidates_info, e_data, last_results, current_round, all_cands_info)
        if vote is not None:
            round_votes.append(vote)

    results = voting.count_votes(round_votes)
    gov_elected, v_needed, disp_v_needed = voting.verify_election(
        results, num_electors_base, req_maj_perc)
    return gov_elected, results, local_prefs, v_needed


# --- Main Simulation Function ---
def run_election_simulation(election_attempt=1, preselected_candidates_info=None, runoff_carryover_winner_name=None, continue_event=None, running_event=None, step_by_step_mode=False):
    """Runs the entire electoral process simulation."""
    current_attempt_prefs = {}  # Local preferences for this attempt
    elector_network = None     # Social network graph

    if running_event:
        running_event.set()
    try:  # Check Pygame
        import pygame
        if not pygame.display.get_init():
            if running_event:
                running_event.clear()
                return
    except ImportError:
        pass

    # --- Start Simulation ---
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"\n{'='*50}\n--- Starting Attempt {election_attempt}/{config.MAX_ELECTION_ATTEMPTS} ---\n{'='*50}")
    utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                             "attempt": election_attempt, "phase": "Init", "round": 0, "status": "Starting"})
    if not step_by_step_mode and continue_event:
        continue_event.set()

    governor_cands_info = []
    district_winners_info = []
    num_preselected = len(
        preselected_candidates_info) if preselected_candidates_info else 0

    # --- Determine Candidates Needed from Districts ---
    if num_preselected > 0:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"\nRestart: {num_preselected} pre-selected.")
        governor_cands_info.extend(preselected_candidates_info)
        needed_from_districts = config.NUM_GRAND_ELECTORS - num_preselected
        if needed_from_districts < 0:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_ERROR, "Config Error: Neg winners needed")
            utils.send_pygame_update(
                utils.UPDATE_TYPE_COMPLETE, {"elected": False})
            if running_event:
                running_event.clear()
                return
        winners_base = needed_from_districts // config.NUM_DISTRICTS
        winners_extra = needed_from_districts % config.NUM_DISTRICTS
        if needed_from_districts > 0:
            if winners_extra > 0:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, f"{winners_extra} D elect {winners_base+1}, {config.NUM_DISTRICTS-winners_extra} elect {winners_base}.")
            else:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, f"Each D elects {winners_base}.")
        else:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "Phase 1 skipped.")
    else:
        needed_from_districts = config.NUM_GRAND_ELECTORS
        winners_base = needed_from_districts // config.NUM_DISTRICTS
        winners_extra = needed_from_districts % config.NUM_DISTRICTS
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"\nAttempt {election_attempt}: All {config.NUM_GRAND_ELECTORS} from districts.")
        if winners_extra > 0:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, f"{winners_extra} D elect {winners_base+1}, {config.NUM_DISTRICTS-winners_extra} elect {winners_base}.")
        else:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, f"Each D elects {winners_base}.")

    # --- PHASE 1: District Elections ---
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"\n{'*'*40}\n--- PHASE 1: District Elections ---")
    utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
        "phase": "District Elections", "round": 0, "status": "Running"})
    if needed_from_districts > 0:
        for i in range(1, config.NUM_DISTRICTS + 1):
            try:  # Check Pygame
                import pygame
                if running_event and not pygame.display.get_init():
                    running_event.clear()
                    return
            except ImportError:
                pass
            winners_this_dist = winners_base + (1 if i <= winners_extra else 0)
            dist_winners = execute_district_election(
                i, winners_this_dist, continue_event, running_event, step_by_step_mode)
            district_winners_info.extend(dist_winners)
            try:  # Check Pygame after
                import pygame
                if running_event and not pygame.display.get_init():
                    running_event.clear()
                    return
            except ImportError:
                pass
            if continue_event and not step_by_step_mode:
                continue_event.set()
    else:
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "Phase 1 skipped.")

    governor_cands_info.extend(district_winners_info)
    if len(governor_cands_info) != config.NUM_GRAND_ELECTORS:  # Final Check
        utils.send_pygame_update(
            utils.UPDATE_TYPE_ERROR, f"Internal Error: Final cands ({len(governor_cands_info)}) != NUM_GRAND_ELECTORS ({config.NUM_GRAND_ELECTORS}).")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_COMPLETE, {"elected": False})
        if running_event:
            running_event.clear()
            return
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"\n--- Phase 1 Completed: {len(governor_cands_info)} candidates proceed. ---")

    # --- PHASE 2: Governor Election ---
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"\n{'*'*40}\n--- PHASE 2: Governor Election by College ---")
    if continue_event:  # Pause Entering Palace
        utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
            "phase": "College", "round": 0, "status": "Entering Palace..."})
        if step_by_step_mode:
            continue_event.wait()
            continue_event.clear()
        else:
            time.sleep(config.GOVERNOR_PAUSE_SECONDS * 1.5)
            continue_event.set()

    # Generate Electors and Preferences for this attempt
    grand_electors = generation.generate_grand_electors(
        config.NUM_GRAND_ELECTORS)
    grand_electors_ids = [e['id'] for e in grand_electors]
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"\nTotal Grand Electors: {len(grand_electors_ids)}")
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"Governor candidates: {len(governor_cands_info)}")
    current_attempt_prefs = voting.initialize_elector_preferences(
        grand_electors, governor_cands_info, preselected_candidates_info)

    # Create Social Network
    if config.USE_SOCIAL_NETWORK:
        elector_network = generation.create_elector_network(grand_electors_ids)

    # Init Budgets
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Init Campaign Budgets ---")
    for cand in governor_cands_info:
        cand['campaign_budget'] = config.INITIAL_CAMPAIGN_BUDGET
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  {cand['name']}: Budget {cand['campaign_budget']:.2f}")
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "-"*35)

    # Oath Ceremony Pause
    if continue_event:
        utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
            "status": "Taking Oath..."})
    if step_by_step_mode:
        continue_event.wait()
        continue_event.clear()
    else:
        time.sleep(config.GOVERNOR_PAUSE_SECONDS)
        if continue_event:
            continue_event.set()
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "\nOath Ceremony...")
    time.sleep(config.GOVERNOR_PAUSE_SECONDS / 2)

    # Candidate Presentation Pause & Log
    if continue_event:
        utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
            "status": "Presenting Cands..."})
    if step_by_step_mode:
        continue_event.wait()
        continue_event.clear()
    else:
        time.sleep(config.GOVERNOR_PAUSE_SECONDS)
        if continue_event:
            continue_event.set()
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Candidate Presentation ---")
    gov_cands_sorted = sorted(governor_cands_info, key=lambda x: x["name"])
    preselected_set = {
        c["name"] for c in preselected_candidates_info} if preselected_candidates_info else set()
    for i, cand in enumerate(gov_cands_sorted):
        status = "(Pre-sel)" if cand["name"] in preselected_set else ""
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"\nCand {i+1}: {cand['name']} {status} ({cand.get('party_id', 'N/A')})")
        attrs = cand.get("attributes", {})
        attrs_str = ", ".join(
            [f"{k[:3]}:{v}" for k, v in attrs.items()])  # Abbreviato
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  Age: {cand.get('age','?')} | Attrs: {attrs_str if attrs_str else 'N/A'}")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f'  Stmt: "{generate_candidate_oath(cand, config.CURRENT_HOT_TOPIC)}"')
        time.sleep(config.GOVERNOR_PAUSE_SECONDS / 5)
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "-" * 40)

    # --- College Voting Loop ---
    current_round = 0
    governor_elected = None
    runoff_mode = False
    runoff_cand_names = []
    last_results = Counter()
    last_normal_results = Counter()
    current_req_maj = config.REQUIRED_MAJORITY
    if election_attempt >= 4:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"\n--- Att {election_attempt}: Majority 50% ---")
        current_req_maj = 0.5
    carryover_name_round = runoff_carryover_winner_name  # Per round 1

    while governor_elected is None and current_round < config.MAX_TOTAL_ROUNDS:
        current_round += 1
        votable_cands = list(governor_cands_info)  # Default
        current_voters = list(grand_electors_ids)  # Default

        # --- Pre-Vote Events ---
        # 1. Campaigning (after round 1)
        if current_round > 1:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, f"\n--- Campaign Phase (Before R{current_round}) ---")
            votable_now = runoff_cand_names if runoff_mode else [
                c['name'] for c in governor_cands_info]
            campaign_cands = [
                c for c in governor_cands_info if c['name'] in votable_now]
            if campaign_cands:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, " - Theme Selection -")
                for cand in campaign_cands:
                    attrs = cand['attributes']
                    sorted_attrs = sorted(
                        attrs.items(), key=lambda i: i[1], reverse=True)
                    themes = [a[0]
                              for a in sorted_attrs[:random.randint(1, 2)]]
                    cand['current_campaign_themes'] = themes
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE, f"  {cand['name']}: {', '.join(t.replace('_',' ').title() for t in themes)}")
                # Log budget pre
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, " Budget Pre-Campaign:")
                for cd in governor_cands_info:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE, f"  {cd['name']}: {cd.get('campaign_budget', 0):.2f}")
                # Run campaign
                voting.simulate_campaigning(
                    campaign_cands, grand_electors, current_attempt_prefs, last_results)
                # Log budget post
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, "\n Budget Post-Campaign:")
                for cd in governor_cands_info:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE, f"  {cd['name']}: {cd.get('campaign_budget', 0):.2f}")
                utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "-"*25)
                time.sleep(config.GOVERNOR_PAUSE_SECONDS / 2)

        # 2. Random Event (chance based)
        event_cands = votable_cands if runoff_mode else governor_cands_info
        if current_round > 0 and random.random() < 0.45:
            generate_random_event(
                event_cands, current_attempt_prefs, last_results)
            time.sleep(config.GOVERNOR_PAUSE_SECONDS / 3)

        # 3. Social Influence (if active)
        if config.USE_SOCIAL_NETWORK and elector_network is not None and current_round > 0:
            current_attempt_prefs = voting.simulate_social_influence(
                elector_network, current_attempt_prefs)
            time.sleep(config.GOVERNOR_PAUSE_SECONDS / 3)

        # --- Execute Voting Round ---
        if runoff_mode:
            votable_cands = [
                c for c in governor_cands_info if c["name"] in runoff_cand_names]
        else:
            votable_cands = list(governor_cands_info)

        round_gov, results_count, updated_prefs, votes_needed = execute_voting_round(
            current_voters, votable_cands, current_attempt_prefs, last_results,
            config.NUM_GRAND_ELECTORS, current_req_maj, current_round,
            governor_cands_info, carryover_name_round,
            continue_event, running_event, step_by_step_mode)

        current_attempt_prefs = updated_prefs
        governor_elected = round_gov
        if current_round == 1:
            carryover_name_round = None  # Bonus used

        if not runoff_mode:
            last_normal_results = copy.deepcopy(results_count)
        last_results = copy.deepcopy(results_count)

        try:  # Check Pygame
            import pygame
            if running_event and not pygame.display.get_init():
                running_event.clear()
                return
            if continue_event and not step_by_step_mode:
                time.sleep(config.GOVERNOR_PAUSE_SECONDS / 2)
        except ImportError:
            pass

        # --- Log & Update GUI ---
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"\n--- College Round {current_round} Results ---")
        gui_results = []
        cand_dict = {c["name"]: c for c in governor_cands_info}
        total_v = sum(results_count.values())
        for name, votes in results_count.most_common():
            elected = (governor_elected == name)
            info = cand_dict.get(name, {})
            perc = (votes / total_v * 100) if total_v > 0 else 0
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, f"  - {name}: {votes} votes ({perc:.1f}%)")
            gui_results.append({"name": name, "votes": votes, "elected_this_round": elected, "sprite_key": None,
                                "attributes": info.get('attributes', {}), "gender": info.get('gender', '?'), "age": info.get('age', '?'), "party_id": info.get('party_id', '?')})
        utils.send_pygame_update(utils.UPDATE_TYPE_RESULTS, {
            "type": "college", "round": current_round, "results": gui_results})
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"Votes needed: {votes_needed} ({current_req_maj*100:.0f}%)")

        # --- Handle Outcome ---
        if governor_elected:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, f"MAJORITY REACHED! {governor_elected} elected.")
            utils.send_pygame_update(utils.UPDATE_TYPE_FLAG, True)
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                "status": "Governor Elected!"})
            break
        else:
            utils.send_pygame_update(utils.UPDATE_TYPE_FLAG, False)
            status_gui = "Waiting..." if step_by_step_mode else "No Election Yet"
            utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                "status": status_gui})
            # Check for Runoff Transition
            if not runoff_mode and current_round >= config.MAX_NORMAL_ROUNDS:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, f"\nReached {config.MAX_NORMAL_ROUNDS} rounds. Proceeding to runoff.")
                if not last_normal_results:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_ERROR, "No normal round votes. Cannot runoff.")
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_COMPLETE, {"elected": False})
                    if running_event:
                        running_event.clear()
                        return
                cands_in = {c['name'] for c in governor_cands_info}
                filtered_res = {
                    c: v for c, v in last_normal_results.items() if c in cands_in}
                if len(filtered_res) < 2:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_ERROR, "<2 cands with votes. Cannot runoff.")
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_COMPLETE, {"elected": False})
                    if running_event:
                        running_event.clear()
                        return
                runoff_cands = [c[0]
                                for c in Counter(filtered_res).most_common(2)]
                runoff_cand_names = runoff_cands
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, f"Runoff Candidates: {runoff_cands[0]} & {runoff_cands[1]}")
                runoff_mode = True
                if not step_by_step_mode:
                    utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
                        "status": "Runoff Prep"})
                    time.sleep(config.GOVERNOR_PAUSE_SECONDS)
                    if continue_event:
                        continue_event.set()

            # Identify Key Electors (intermittently)
            if current_round < config.MAX_TOTAL_ROUNDS and current_round % 3 == 0:
                key_electors = identify_key_electors(
                    current_attempt_prefs, last_results)
                if key_electors:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE, "\n--- Key Electors Identified ---")
                for idx, ke in enumerate(key_electors):
                    if idx < 5:
                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_MESSAGE, f"  ID: {ke['id']}, Reasons: {', '.join(ke['reasons'])}")
                    if idx == 5:
                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_MESSAGE, "  ...")

            # Signal next round (continuous mode)
            if continue_event and not step_by_step_mode and current_round < config.MAX_TOTAL_ROUNDS:
                continue_event.set()
    # --- End College Voting Loop ---

    # --- Simulation Conclusion ---
    if governor_elected:
        # ... (Logica annuncio governatore come prima) ...
        utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE, {
            "elected": True, "governor": governor_elected})
        if running_event:
            running_event.clear()
    else:  # Stallo dopo MAX_TOTAL_ROUNDS
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"\n{'='*50}\n--- Attempt {election_attempt} Concluded with DEADLOCK ---\n{'='*50}")
        utils.send_pygame_update(utils.UPDATE_TYPE_STATUS, {
            "status": "DEADLOCK"})
        next_preselected = []
        next_carryover_name = None
        if election_attempt < config.MAX_ELECTION_ATTEMPTS:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, "\nStatutory Steps: Preparing next attempt...")
            results_carry = last_results if last_results else last_normal_results
            if results_carry:
                # Runoff deadlock logic
                if runoff_mode and len(runoff_cand_names) == 2:
                    runoff_res = {c: results_carry.get(
                        c, 0) for c in runoff_cand_names}
                    sorted_runoff = sorted(
                        runoff_res.items(), key=lambda i: i[1], reverse=True)
                    if sorted_runoff:
                        winner = sorted_runoff[0][0]
                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_MESSAGE, f"Runoff Winner: {winner} ({sorted_runoff[0][1]})")
                    if len(sorted_runoff) > 1:
                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_MESSAGE, f"Runoff Loser: {sorted_runoff[1][0]} ({sorted_runoff[1][1]})")
                    winner_info = next(
                        (c for c in governor_cands_info if c['name'] == winner), None)
                    if winner_info:
                        next_preselected = [winner_info]
                        next_carryover_name = winner
                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_MESSAGE, f"{winner} carried over w/ bonus.")
                    else:
                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_ERROR, f"Info not found for {winner}. No carry.")
                else:  # General deadlock logic
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE, "\nGeneral deadlock. Carrying over top(s).")
                    num_carry = max(1, getattr(
                        config, "NUM_PRESELECTED_CANDIDATES", 1))
                    num_carry = min(num_carry, len(results_carry))
                    top_voted = Counter(results_carry).most_common(num_carry)
                    top_names = [c[0] for c in top_voted]
                    next_preselected = [
                        c for c in governor_cands_info if c["name"] in top_names]
                if next_preselected:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE, f"Carried over: {[c['name'] for c in next_preselected]}")
                else:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE, "No cands carried over.")
            else:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE, "No results for carryover.")
            # --- Recursion ---
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, f"Initiating Attempt {election_attempt + 1}...")
            time.sleep(1.5)
            run_election_simulation(election_attempt + 1, next_preselected,
                                    next_carryover_name, continue_event, running_event, step_by_step_mode)
        else:  # Max attempts reached
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE, f"\n{'='*50}\nMax attempts ({config.MAX_ELECTION_ATTEMPTS}) reached. No Governor.\n{'='*50}")
            utils.send_pygame_update(
                utils.UPDATE_TYPE_COMPLETE, {"elected": False})
            if running_event:
                running_event.clear()
