# voting.py

import random
import math
from collections import Counter
import copy
import networkx as nx
import uuid
import json
import time
import traceback

# Import moduli del progetto
import config
import utils
import db_manager

# Importa configurazioni specifiche se necessario (es. MEDIA_OUTLETS)
try:
    # Assumendo che MEDIA_OUTLETS sia definito in config.py
    from config import MEDIA_OUTLETS
except ImportError:  # pragma: no cover
    MEDIA_OUTLETS = []
    print("Warning: MEDIA_OUTLETS not found in config.py.")

# Import opzionale numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:  # pragma: no cover
    HAS_NUMPY = False

# --- NESSUNA Configurazione o Import LLM ---

# --- Funzioni Helper e di Logica ---


def apply_elector_impact(elector_id, candidate_name, base_impact, elector_preferences_data):
    """
    Applica un impatto al leaning di un elettore verso un candidato,
    considerando tratti (Motivated Reasoning) e Media Literacy.
    Modifica direttamente il dizionario elector_preferences_data.
    """
    if not isinstance(elector_preferences_data, dict):
        return  # Safety check

    e_data = elector_preferences_data.get(elector_id)
    if not e_data or not isinstance(e_data, dict) or \
       'leanings' not in e_data or not isinstance(e_data['leanings'], dict) or \
       candidate_name not in e_data['leanings']:
        return

    impact = base_impact
    traits = e_data.get('traits', [])
    if not isinstance(traits, list):
        traits = []

    # Motivated Reasoning
    if "Motivated Reasoner" in traits:
        lean = e_data['leanings'][candidate_name]
        mid_point = config.MAX_ELECTOR_LEANING_BASE / 2.0
        is_liked = lean > mid_point
        is_positive = base_impact > 0
        is_negative = base_impact < 0
        is_incongruent = (is_negative and is_liked) or (
            is_positive and not is_liked)
        if is_incongruent:
            impact *= (1.0 - config.MOTIVATED_REASONING_FACTOR)

    # Media Literacy
    lit_score = e_data.get('media_literacy', config.MEDIA_LITERACY_RANGE[0])
    min_lit, max_lit = config.MEDIA_LITERACY_RANGE
    lit_range = max_lit - min_lit
    norm_lit = (lit_score - min_lit) / lit_range if lit_range > 0 else 0
    lit_reduction = norm_lit * config.MEDIA_LITERACY_EFFECT_FACTOR
    final_impact = impact * (1.0 - lit_reduction)

    # Applica impatto
    current_leaning = e_data['leanings'][candidate_name]
    # Assicurati che current_leaning sia numerico prima di sommare
    if isinstance(current_leaning, (int, float)):
        e_data['leanings'][candidate_name] = max(
            0.1, current_leaning + final_impact)
    # else: log warning?


def identify_key_electors(elector_preferences_data, current_results, num_top_candidates_to_consider=3):
    """Identifica elettori chiave (swing, influenzabili)."""
    key_electors_summary = []
    if not isinstance(elector_preferences_data, dict) or not isinstance(current_results, Counter):
        return key_electors_summary

    top_cand_names = [item[0] for item in current_results.most_common(
        num_top_candidates_to_consider)]

    for e_id, data in elector_preferences_data.items():
        if not isinstance(data, dict):
            continue
        traits = data.get('traits', [])
        leanings = data.get('leanings', {})
        if not isinstance(traits, list) or not isinstance(leanings, dict):
            continue

        is_key = False
        reasons = []
        if "Easily Influenced" in traits:
            is_key = True
            reasons.append("Easily Influenced")
        if "Swing Voter" in traits:
            is_key = True; reasons.append("Is a Swing Voter")

        if leanings and len(top_cand_names) >= 2:
            top_leans_data = [{'name': cn, 'leaning': leanings[cn]}
                              for cn in top_cand_names if cn in leanings and isinstance(leanings.get(cn), (int, float))]
            top_leans_sorted = sorted(
                top_leans_data, key=lambda x: x['leaning'], reverse=True)
            if len(top_leans_sorted) >= 2:
                diff = top_leans_sorted[0]['leaning'] - \
                    top_leans_sorted[1]['leaning']
                if abs(diff) < config.ELECTOR_SWING_THRESHOLD:
                    is_key = True
                    reasons.append(
                        f"Swing b/w {top_leans_sorted[0]['name']} ({top_leans_sorted[0]['leaning']:.1f}) & {top_leans_sorted[1]['name']} ({top_leans_sorted[1]['leaning']:.1f})")
        if is_key:
            key_electors_summary.append(
                {"id": e_id, "reasons": list(set(reasons))})
    return key_electors_summary


def initialize_citizen_preferences(num_citizens, district_candidates):
    """Assegna preferenze e tratti casuali ai cittadini."""
    preferences = {}
    if num_citizens <= 0:
        return preferences
    for i in range(num_citizens):
        citizen_id = f"Citizen_{i+1}"
        assigned_traits = []
        if config.CITIZEN_TRAITS:
            k_traits = min(config.CITIZEN_TRAIT_COUNT,
                           len(config.CITIZEN_TRAITS))
            if k_traits > 0:
                assigned_traits = random.sample(
                    config.CITIZEN_TRAITS, k_traits)
        preferences[citizen_id] = {
            "preference_experience": random.randint(*config.CITIZEN_IDEAL_PREFERENCE_RANGE),
            "preference_social_vision": random.randint(*config.CITIZEN_IDEAL_PREFERENCE_RANGE),
            "preference_mediation": random.randint(*config.CITIZEN_IDEAL_PREFERENCE_RANGE),
            "preference_integrity": random.randint(*config.CITIZEN_IDEAL_PREFERENCE_RANGE),
            "traits": assigned_traits}
    return preferences


def simulate_citizen_vote(citizen_id, district_candidates_info, citizen_data):
    """Simula il voto di un cittadino."""
    if not isinstance(district_candidates_info, list) or not district_candidates_info:
        return None
    candidates_dict = {c["name"]: c for c in district_candidates_info if isinstance(
        c, dict) and 'name' in c}
    candidate_names = list(candidates_dict.keys())
    if not candidate_names:
        return None
    if not isinstance(citizen_data, dict):
        return random.choice(candidate_names)

    citizen_preferences = {
        k: v for k, v in citizen_data.items() if k.startswith("preference_")}
    citizen_traits = citizen_data.get("traits", [])
    if not isinstance(citizen_traits, list):
        citizen_traits = []
    attraction_scores = {}

    for candidate_name in candidate_names:
        candidate = candidates_dict.get(candidate_name)
        if not candidate or not isinstance(candidate.get("attributes"), dict):
            continue
        candidate_attrs = candidate["attributes"]
        total_distance = 0
        default_attr_val = config.ATTRIBUTE_RANGE[0]
        default_pref_val = config.CITIZEN_IDEAL_PREFERENCE_RANGE[0]
        attr_map = {"preference_experience": "administrative_experience", "preference_social_vision": "social_vision",
                    "preference_mediation": "mediation_ability", "preference_integrity": "ethical_integrity"}
        for pref_key, attr_key in attr_map.items():
            distance = abs(candidate_attrs.get(attr_key, default_attr_val) -
                           citizen_preferences.get(pref_key, default_pref_val))
            total_distance += distance
        score = max(0.1, config.MAX_CITIZEN_LEANING_BASE - total_distance *
                    config.CITIZEN_ATTRIBUTE_MISMATCH_PENALTY_FACTOR)
        trait_multiplier = 1.0
        random_bias = random.uniform(-0.5, 0.5)
        if "Attribute Focused" in citizen_traits:
            trait_multiplier *= config.CITIZEN_TRAIT_MULTIPLIER_ATTRIBUTE_FOCUSED
            random_bias *= 0.5
        if "Random Inclined" in citizen_traits:
            random_bias += random.uniform(-config.CITIZEN_TRAIT_RANDOM_INCLINED_BIAS,
                                          config.CITIZEN_TRAIT_RANDOM_INCLINED_BIAS)
        final_score = (score * trait_multiplier) + random_bias
        attraction_scores[candidate_name] = max(0.01, final_score)

    candidates_for_choice = list(attraction_scores.keys())
    weights_for_choice = [attraction_scores[c] for c in candidates_for_choice]
    if not candidates_for_choice or sum(weights_for_choice) <= 0:
        return random.choice(candidate_names) if candidate_names else None
    try:
        return random.choices(candidates_for_choice, weights=weights_for_choice, k=1)[0]
    except ValueError:
        return random.choice(candidate_names) if candidate_names else None


def initialize_elector_preferences(electors_with_traits, candidates, preselected_candidates_info=None):
    """Inizializza preferenze Grand Electors (con media_preference_bias). SENZA LLM flag."""
    elector_full_preferences_data = {}
    if not isinstance(electors_with_traits, list) or not isinstance(candidates, list):
        return elector_full_preferences_data
    candidates_dict = {
        c["name"]: c for c in candidates if isinstance(c, dict) and 'name' in c}
    preselected_names = {c["name"] for c in preselected_candidates_info if isinstance(
        c, dict) and 'name' in c} if preselected_candidates_info else set()

    for elector_data in electors_with_traits:
        if not isinstance(elector_data, dict) or 'id' not in elector_data:
            continue
        elector_id = elector_data['id']
        elector_traits = elector_data.get('traits', [])
        if not isinstance(elector_traits, list):
            elector_traits = []

        identity_weight = random.uniform(*config.IDENTITY_WEIGHT_RANGE)
        if "Strong Partisan" in elector_traits:
            identity_weight = min(0.95, identity_weight * 1.5)
        policy_weight = 1.0 - identity_weight
        party_pref = random.choices(
            config.PARTY_IDS, weights=config.PARTY_ID_ASSIGNMENT_WEIGHTS, k=1)[0]

        elector_prefs = {
            'id': elector_id,
            'weights': {attr: random.randint(*config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE)
                        for attr in ["administrative_experience", "social_vision", "mediation_ability", "ethical_integrity"]},
            'leanings': {}, 'initial_leanings': {}, 'traits': elector_traits,
            'party_preference': party_pref,
            'identity_weight': identity_weight, 'policy_weight': policy_weight,
            'media_literacy': random.randint(*config.MEDIA_LITERACY_RANGE),
            'media_preference_bias': {'Reds': -0.6, 'Blues': 0.7, 'Greens': -0.3, 'Golds': 0.4, 'Independent': 0.0}.get(party_pref, 0.0) + random.uniform(-0.15, 0.15)
        }
        elector_ideal_prefs = {f"preference_{attr}": random.randint(
            *config.ELECTOR_IDEAL_PREFERENCE_RANGE) for attr in elector_prefs['weights']}
        elector_prefs.update(elector_ideal_prefs)

        # Calcola leaning iniziale
        for cand_name, cand in candidates_dict.items():
            cand_attrs = cand.get("attributes", {})
            cand_party = cand.get('party_id', 'Unknown')
            # Policy Score
            w_dist_sum = 0
            if elector_prefs['weights']:
                w_dist_sum = sum(abs(cand_attrs.get(attr, config.ATTRIBUTE_RANGE[0]) - elector_ideal_prefs.get(f"preference_{attr}", config.ELECTOR_IDEAL_PREFERENCE_RANGE[0])) * weight
                                  for attr, weight in elector_prefs['weights'].items())
            penalty = w_dist_sum * config.ELECTOR_ATTRIBUTE_MISMATCH_PENALTY_FACTOR
            lean_policy = max(0.1, config.MAX_ELECTOR_LEANING_BASE - penalty)
            # Identity Score
            id_score = 0.0
            if elector_prefs['party_preference'] != "Independent" and cand_party == elector_prefs['party_preference']:
                id_score = config.MAX_ELECTOR_LEANING_BASE * config.IDENTITY_MATCH_BONUS_FACTOR
            # Combine
            lean_base = (lean_policy * elector_prefs['policy_weight']) + (
                id_score * elector_prefs['identity_weight'])
            # Traits Effect
            if "Idealistic" in elector_traits and cand_attrs.get("ethical_integrity", config.ATTRIBUTE_RANGE[0]) <= 2:
                penalty_f = getattr(
                    config, "STRATEGIC_VOTING_TRAIT_PENALTY_IDEALISTIC_INTEGRITY", 1.5)
                lean_base -= config.MAX_ELECTOR_LEANING_BASE * 0.2 * penalty_f
            # Final Leaning
            init_lean = lean_base + \
                random.uniform(-config.ELECTOR_RANDOM_LEANING_VARIANCE,
                               config.ELECTOR_RANDOM_LEANING_VARIANCE)
            if cand_name in preselected_names:
                init_lean += config.PRESELECTED_CANDIDATE_BOOST
            final_lean = max(0.1, init_lean)
            elector_prefs['leanings'][cand_name] = final_lean
            elector_prefs['initial_leanings'][cand_name] = final_lean

        elector_full_preferences_data[elector_id] = elector_prefs
    return elector_full_preferences_data


def simulate_ai_vote(elector_id, votable_candidates_info, elector_data,
                     last_round_results=None, current_round=0, all_candidates_info=None):
    """Simula voto elettore rule-based (unica funzione di voto)."""
    # Verifica input
    if not isinstance(elector_data, dict) or not isinstance(votable_candidates_info, list):
        return None

    elector_leanings = elector_data.get('leanings', {})
    elector_initial_leanings = elector_data.get('initial_leanings', {})
    elector_traits = elector_data.get('traits', [])
    if not isinstance(elector_leanings, dict) or not isinstance(elector_initial_leanings, dict) or not isinstance(elector_traits, list):
        return None

    votable_names = {c["name"] for c in votable_candidates_info if isinstance(
        c, dict) and c.get('name')}
    if not votable_names:
        return None

    current_leanings = {n: l for n, l in elector_leanings.items(
    ) if n in votable_names and isinstance(l, (int, float))}
    if not current_leanings:
        return random.choice(list(votable_names)) if votable_names else None

    final_leanings = current_leanings.copy()

    # Applica Bias (Bandwagon/Underdog)
    total_votes_prev = sum(last_round_results.values()) if isinstance(
        last_round_results, Counter) else 0
    if isinstance(last_round_results, Counter) and total_votes_prev > 0 and current_round > 0:
        is_band = "Bandwagoner" in elector_traits
        is_under = "Underdog Supporter" in elector_traits or "Contrarian" in elector_traits
        if (is_band or is_under) and len(final_leanings) > 0:
            avg_share = 1.0 / len(final_leanings)
            for name in final_leanings.keys():
                if name not in last_round_results:
                    continue
                share = last_round_results.get(name, 0) / total_votes_prev
                adj = 0.0
                if is_band and share > avg_share * 1.1:
                    adj += (share - avg_share) * config.BANDWAGON_EFFECT_FACTOR * \
                            config.MAX_ELECTOR_LEANING_BASE
                if is_under and share < avg_share * 0.75:
                    adj += (avg_share - share) * config.UNDERDOG_EFFECT_FACTOR * \
                            config.MAX_ELECTOR_LEANING_BASE
                adj = min(adj, config.MAX_BIAS_LEANING_ADJUSTMENT) if adj > 0 else max(
                    adj, -config.MAX_BIAS_LEANING_ADJUSTMENT)
                final_leanings[name] = max(0.1, final_leanings[name] + adj)

    if not final_leanings:
        return random.choice(list(votable_names)) if votable_names else None
    most_preferred = max(final_leanings, key=final_leanings.get)

    # Logica Voto Strategico
    strategic_vote = None
    if current_round >= config.STRATEGIC_VOTING_START_ROUND and isinstance(last_round_results, Counter) and total_votes_prev > 0 and isinstance(all_candidates_info, list):
        pref_votes = last_round_results.get(most_preferred, 0)
        pref_share = pref_votes / total_votes_prev
        is_unlikely_to_win = pref_share < config.UNLIKELY_TO_WIN_THRESHOLD
        if is_unlikely_to_win:
            mod = 1.0
            if "Pragmatic" in elector_traits:
                mod *= config.STRATEGIC_VOTING_TRAIT_MULTIPLIER_PRAGMATIC
            if "Idealistic" in elector_traits:
                mod *= config.STRATEGIC_VOTING_TRAIT_MULTIPLIER_IDEALISTIC
            if elector_initial_leanings:
                votable_initial = {n: l for n, l in elector_initial_leanings.items(
                ) if n in votable_names and isinstance(l, (int, float))}
                if votable_initial:
                    disliked_init = min(
                        votable_initial, key=votable_initial.get)
                    disliked_lean_init = votable_initial.get(
                        disliked_init, config.MAX_ELECTOR_LEANING_BASE)
                    is_disliked = disliked_lean_init < config.MAX_ELECTOR_LEANING_BASE * \
                        config.STRONGLY_DISLIKED_THRESHOLD_FACTOR
                    if is_disliked and disliked_init in votable_names:
                        options = {n: l for n, l in final_leanings.items(
                        ) if n != disliked_init and n != most_preferred}
                        if options:
                            potential_choice = max(options, key=options.get)
                            disliked_votes = last_round_results.get(
                                disliked_init, 0)
                            disliked_share = disliked_votes / total_votes_prev
                            chance = (disliked_share * 0.6 +
                                      (1.0 - pref_share) * 0.4) * mod
                            if random.random() < chance:
                                strategic_vote = potential_choice

    # Decisione Finale
    if strategic_vote:
        return strategic_vote
    else:
        choices = list(final_leanings.keys())
        weights = [max(0.01, w) for w in final_leanings.values()]
        if not choices or sum(weights) <= 0:
            return random.choice(list(votable_names)) if votable_names else None
        try:
            return random.choices(choices, weights=weights, k=1)[0]
        except ValueError:
            return random.choice(list(votable_names)) if votable_names else None


def analyze_competition_and_adapt_strategy(candidate_info, all_candidates_info, last_round_results, current_round):
    """Analizza competizione e adatta temi campagna."""
    if not isinstance(candidate_info, dict) or not isinstance(all_candidates_info, list):
        return
    cand_name = candidate_info.get('name')
    cand_attrs = candidate_info.get(
        "attributes", {}); current_themes = candidate_info.get('current_campaign_themes', [])
    if not cand_name or not isinstance(cand_attrs, dict) or not isinstance(current_themes, list):
        return

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"  {cand_name} analyzing competition (Round {current_round})...")

    if not isinstance(last_round_results, Counter) or sum(last_round_results.values()) == 0:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, "    No previous results. Sticking/Initializing themes.")
        if not current_themes and cand_attrs:
            sorted_attrs = sorted(cand_attrs.items(),
                                  key=lambda i: i[1], reverse=True)
            num_themes_init = random.randint(1, min(2, len(sorted_attrs)))
            candidate_info['current_campaign_themes'] = [a[0]
                                                         for a in sorted_attrs[:num_themes_init]]
        return

    total_votes = sum(last_round_results.values())
    sorted_results_tuples = last_round_results.most_common()
    own_rank = next((i + 1 for i, (name, votes) in enumerate(sorted_results_tuples)
                    if name == cand_name), len(sorted_results_tuples) + 1)
    top_opponents_data = [(name, votes) for name, votes in sorted_results_tuples[:config.COMPETITIVE_ADAPTATION_TOP_OPPONENTS + 1]
                          if name != cand_name][:config.COMPETITIVE_ADAPTATION_TOP_OPPONENTS]
    top_opponent_names = [name for name, votes in top_opponents_data]
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"    Rank: {own_rank}/{len(sorted_results_tuples)}. Top opps: {top_opponent_names}")

    new_themes = []
    available_attrs_list = list(cand_attrs.keys())
    sorted_cand_attrs = sorted(
        cand_attrs.items(), key=lambda i: i[1], reverse=True)
    strength_themes = [
        attr for attr, val in sorted_cand_attrs if val >= 4 and attr in available_attrs_list]
    opponent_strength_themes_count = Counter()
    for opp_name in top_opponent_names:
        opp_info = next((c for c in all_candidates_info if isinstance(
            c, dict) and c.get('name') == opp_name), None)
        if opp_info and isinstance(opp_info.get('attributes'), dict):
            for attr, val in opp_info['attributes'].items():
                if val >= 4 and attr in available_attrs_list:
                    opponent_strength_themes_count[attr] += 1
    counter_themes_pool = [attr for attr, count in opponent_strength_themes_count.most_common(
    ) if attr in available_attrs_list]

    num_themes_to_pick = random.randint(1, 2)
    picked_count = 0
    for theme in strength_themes:
        if picked_count < num_themes_to_pick and random.random() < config.COMPETITIVE_ADAPTATION_SELF_FOCUS_FACTOR:
            if theme not in new_themes:
                new_themes.append(theme)
                picked_count += 1
    if picked_count < num_themes_to_pick:
        for theme in counter_themes_pool:
            if picked_count < num_themes_to_pick and random.random() < (1.0 - config.COMPETITIVE_ADAPTATION_SELF_FOCUS_FACTOR):
                if theme not in new_themes:
                    new_themes.append(theme)
                    picked_count += 1
    if picked_count < num_themes_to_pick and available_attrs_list:
        fallback_pool = list(set(strength_themes + available_attrs_list))
        random.shuffle(fallback_pool)
        for theme in fallback_pool:
            if picked_count < num_themes_to_pick and theme not in new_themes:
                new_themes.append(theme)
                picked_count += 1

    final_themes = [t for t in new_themes if t in available_attrs_list]
    if not final_themes and available_attrs_list:
        best_attr = sorted_cand_attrs[0][0] if sorted_cand_attrs and sorted_cand_attrs[0][0] in available_attrs_list else None
        if best_attr:
            final_themes = [best_attr]
        else:
            final_themes = [random.choice(available_attrs_list)]

    candidate_info['current_campaign_themes'] = final_themes
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"    Adapted themes: {', '.join(t.replace('_',' ').title() for t in final_themes if t)}")


def simulate_campaigning(candidates_info, electors, elector_full_preferences_data, last_round_results):
    """Simula campagna con rendimenti decrescenti e apprendimento agenti."""
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulating Candidate Campaigning (with Diminishing Returns) ---")
    if not candidates_info or not electors:
        return

    elector_map = {e['id']: e for e in electors if isinstance(
        e, dict) and 'id' in e}
    elector_ids = list(elector_map.keys())
    if not elector_ids:
        return  # No electors

    key_electors_summary = identify_key_electors(
        elector_full_preferences_data, last_round_results)
    key_elector_ids = {ke['id'] for ke in key_electors_summary}

    # Calcola potenziali e pesi elettori
    elector_potentials = {}
    for e_obj in electors:
        if not isinstance(e_obj, dict) or 'id' not in e_obj:
            continue
        e_id = e_obj['id']; e_traits = e_obj.get('traits', [])
        elector_potential_score = config.ELECTOR_SUSCEPTIBILITY_BASE
        if "Easily Influenced" in e_traits:
            elector_potential_score *= config.INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED
        if e_id in key_elector_ids:
            elector_potential_score *= config.TARGETING_KEY_ELECTOR_BONUS_FACTOR
        elector_potentials[e_id] = max(0.05, min(5.0, elector_potential_score))
    total_potential_sum = sum(elector_potentials.values())
    num_electors_calc = len(elector_potentials)
    elector_allocation_weights = {}
    if total_potential_sum > 0:
        elector_allocation_weights = {
            e_id: pot / total_potential_sum for e_id, pot in elector_potentials.items()}
    elif num_electors_calc > 0:
        equal_weight = 1.0 / num_electors_calc; elector_allocation_weights = {
            e_id: equal_weight for e_id in elector_potentials.keys()}

    # Ciclo sui candidati
    for cand_idx, cand_data_ref in enumerate(candidates_info):
        if not isinstance(cand_data_ref, dict):
            continue  # Salta dati candidato non validi
        if hasattr(utils, 'simulation_running_event') and not utils.simulation_running_event.is_set():
            return

        cand_name = cand_data_ref.get('name', f'Unknown_{cand_idx}')
        cand_attrs = cand_data_ref.get("attributes", {})
        cand_med = cand_attrs.get(
            'mediation_ability', config.ATTRIBUTE_RANGE[0])
        themes = cand_data_ref.get('current_campaign_themes', [])
        current_candidate_budget = float(
            cand_data_ref.get('campaign_budget', 0.0))
        min_cost_per_elector = float(
            config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[0])
        max_alloc_per_attempt = float(
            config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1])

        # Seleziona target (logica campionamento pesato semplificata)
        num_electors_to_target = config.INFLUENCE_ELECTORS_PER_CANDIDATE
        target_ids = []
        if num_electors_to_target > 0 and elector_ids and elector_allocation_weights:
            population = list(elector_allocation_weights.keys())
             weights = list(elector_allocation_weights.values())
             sum_weights = sum(weights)
             if sum_weights <= 0 and len(weights) > 0:
                 weights = [1.0 / len(weights)] * len(weights)
                 sum_weights = 1.0
             elif sum_weights != 1.0 and sum_weights > 0:
                 weights = [w / sum_weights for w in weights]
             if population and sum(weights) > 0:
                 try:
                     num_to_sample_unique = min(
                         num_electors_to_target, len(population))
                     sampled_ids = random.choices(
                         population, weights=weights, k=num_to_sample_unique)  # Semplificato
                     target_ids = list(set(sampled_ids))
                     while len(target_ids) < num_to_sample_unique:  # Simple fill
                         additional_sample = random.choices(
                             population, weights=weights, k=1)
                         if additional_sample[0] not in target_ids:
                             target_ids.append(additional_sample[0])
                 except Exception:
                     target_ids = random.sample(elector_ids, min(
                         num_electors_to_target, len(elector_ids)))
             else:
                 target_ids = random.sample(elector_ids, min(
                     num_electors_to_target, len(elector_ids)))
        elif elector_ids:
            target_ids = random.sample(elector_ids, min(
                num_electors_to_target, len(elector_ids)))

        # Ciclo sugli elettori target
        successful_influences_this_candidate = 0
        electors_targeted_this_candidate = 0
        for e_id in target_ids:
            if hasattr(utils, 'simulation_running_event') and not utils.simulation_running_event.is_set():
                # Salva budget prima di uscire
                candidates_info[cand_idx]['campaign_budget'] = current_candidate_budget
                db_manager.save_candidate(candidates_info[cand_idx])
                 return

            if current_candidate_budget < min_cost_per_elector and min_cost_per_elector > 0:
                break

            electors_targeted_this_candidate += 1
            e_info = elector_map.get(e_id)
            e_prefs = elector_full_preferences_data.get(e_id)
            if not e_info or not e_prefs or not isinstance(e_prefs, dict):
                continue
            e_traits = e_info.get('traits', [])
            if not isinstance(e_traits, list): e_traits = []

            # Calcola Allocazione Budget
            elector_weight = elector_allocation_weights.get(e_id, 0)
            alloc_range_size = max(
                0, max_alloc_per_attempt - min_cost_per_elector)
            alloc_for_this_elector = min_cost_per_elector + elector_weight * alloc_range_size
            alloc_for_this_elector = min(
                current_candidate_budget, alloc_for_this_elector)
            if current_candidate_budget >= min_cost_per_elector and min_cost_per_elector > 0:
                alloc_for_this_elector = max(
                    min_cost_per_elector, alloc_for_this_elector)
            elif min_cost_per_elector > 0:
                alloc_for_this_elector = 0
            elif alloc_for_this_elector == 0 and current_candidate_budget > 0 and max_alloc_per_attempt > 0:
                alloc_for_this_elector = min(current_candidate_budget, random.uniform(
                    0.01, max(0.01, max_alloc_per_attempt * elector_weight)))
            if alloc_for_this_elector <= 0:
                continue  # Salta se non si spende nulla
            current_candidate_budget -= alloc_for_this_elector

            # Calcola Suscettibilità Elettore
            # ... (logica tratti Loyal/EasilyInfluenced) ...
            base_susceptibility = config.ELECTOR_SUSCEPTIBILITY_BASE + \
                random.uniform(-0.2, 0.2)
            lit_score = e_prefs.get(
                'media_literacy', config.MEDIA_LITERACY_RANGE[0])
            min_lit, max_lit = config.MEDIA_LITERACY_RANGE
            lit_range = max_lit - min_lit
            norm_lit = (lit_score - min_lit) / \
                        lit_range if lit_range > 0 else 0
            lit_reduction = norm_lit * config.MEDIA_LITERACY_EFFECT_FACTOR
            final_susceptibility = max(
                0.05, min(0.95, base_susceptibility * (1.0 - lit_reduction)))

            # Calcola Chance Successo (con Rendimenti Decrescenti)
            base_success_chance = (
                cand_med / config.ATTRIBUTE_RANGE[1]) * final_susceptibility
            allocation_success_bonus = 0.0
            if max_alloc_per_attempt > 0:
                normalized_allocation_ratio = min(
                    1.0, alloc_for_this_elector / max_alloc_per_attempt)
                effective_norm_alloc_success = normalized_allocation_ratio ** config.DIMINISHING_RETURNS_EXPONENT_PER_ATTEMPT
                allocation_success_bonus = effective_norm_alloc_success * \
                    config.CAMPAIGN_ALLOCATION_SUCCESS_CHANCE_FACTOR
            final_success_chance = max(
                0.05, min(1.0, base_success_chance + allocation_success_bonus))

            # Simula Tentativo Influenza
            if random.random() < final_success_chance:
                successful_influences_this_candidate += 1
                # Calcola Forza Influenza (con Rendimenti Decrescenti)
                base_influence_strength = config.INFLUENCE_STRENGTH_FACTOR * \
                    config.MAX_ELECTOR_LEANING_BASE * random.uniform(0.8, 1.2)
                allocation_influence_bonus = 0.0
                if max_alloc_per_attempt > 0:
                    normalized_allocation_ratio_inf = min(
                        1.0, alloc_for_this_elector / max_alloc_per_attempt)
                    effective_norm_alloc_inf = normalized_allocation_ratio_inf ** config.DIMINISHING_RETURNS_EXPONENT_PER_ATTEMPT
                    allocation_influence_bonus = effective_norm_alloc_inf * \
                        config.CAMPAIGN_ALLOCATION_INFLUENCE_FACTOR
                total_influence = min(
                    base_influence_strength + allocation_influence_bonus, config.MAX_CAMPAIGN_INFLUENCE_PER_ATTEMPT)
                # Bonus Tema
                theme_match_bonus = 0.0
                elector_weights = e_prefs.get('weights', {})
                if themes and elector_weights:
                    for theme_item in themes:
                        weight_for_theme = elector_weights.get(theme_item, 0)
                        if weight_for_theme > config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE[0]:
                            max_weight_range = config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE[1]
                            normalized_weight = weight_for_theme / \
                                 max_weight_range if max_weight_range > 0 else 0.5
                             theme_match_bonus += config.CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE * \
                                 normalized_weight * random.uniform(1.0, 1.2)
                total_influence += theme_match_bonus
                # Bias Conferma
                confirmation_modifier = 1.0
                if "Confirmation Prone" in e_traits:
                    current_leaning_conf = e_prefs.get(
                        'leanings', {}).get(cand_name, 0)
                    midpoint_leaning_conf = config.MAX_ELECTOR_LEANING_BASE / 2.0
                    bias_strength = config.CONFIRMATION_BIAS_FACTOR
                    if current_leaning_conf > midpoint_leaning_conf:
                        confirmation_modifier = bias_strength
                    elif current_leaning_conf < midpoint_leaning_conf * 0.8:
                        confirmation_modifier = 1.0 / bias_strength
                adjusted_influence = total_influence * confirmation_modifier
                # Applica Influenza
                # Usa la funzione helper
                apply_elector_impact(
                    e_id, cand_name, adjusted_influence, elector_full_preferences_data)
                # Apprendimento Agente
                if adjusted_influence > 0.1:
                    learning_rate_factor = config.ELECTOR_LEARNING_RATE * \
                        config.CAMPAIGN_EXPOSURE_LEARNING_EFFECT
                    learn_direction = 0.0
                    elector_party_pref_learn = e_prefs.get(
                        'party_preference', 'Independent')
                    candidate_party_learn = cand_data_ref.get(
                        'party_id', 'Unknown')
                    if elector_party_pref_learn != "Independent" and candidate_party_learn == elector_party_pref_learn:
                        learn_direction = random.uniform(0.2, 0.7)
                    elif candidate_party_learn != elector_party_pref_learn or elector_party_pref_learn == "Independent":
                        learn_direction = random.uniform(-0.7, -0.2)
                    learning_adjustment_value = learning_rate_factor * learn_direction
                    current_identity_weight_learn = e_prefs.get(
                        'identity_weight', 0.5)
                    new_identity_weight_learn = current_identity_weight_learn + learning_adjustment_value
                    e_prefs['identity_weight'] = max(
                        0.05, min(0.95, new_identity_weight_learn))
                    e_prefs['policy_weight'] = 1.0 - e_prefs['identity_weight']

        # Fine ciclo elettori target
        # Aggiorna e salva budget candidato
        candidates_info[cand_idx]['campaign_budget'] = current_candidate_budget
        candidate_to_save = candidates_info[cand_idx]
        try:
            candidate_to_save['current_budget'] = float(
                candidate_to_save['campaign_budget'])
        except (ValueError, TypeError):
            candidate_to_save['current_budget'] = 0.0
        if 'uuid' not in candidate_to_save:
            candidate_to_save['uuid'] = str(uuid.uuid4())
        if 'initial_budget' not in candidate_to_save:
            candidate_to_save['initial_budget'] = config.INITIAL_CAMPAIGN_BUDGET
        db_manager.save_candidate(candidate_to_save)
        # Log
        themes_string = ", ".join([t.replace('_', ' ').title()
                                  for t in themes if t]) if themes else "N/A"
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"  Campaign {cand_name} (Themes: {themes_string}): Targeted {electors_targeted_this_candidate} electors ({successful_influences_this_candidate} succ.). Budget left: {current_candidate_budget:.2f}")
    # Fine ciclo candidati


def simulate_social_influence(network_graph, current_preferences):
    """Simula influenza sociale con apprendimento agenti e debug interno."""
    func_name = "simulate_social_influence"
    if not config.USE_SOCIAL_NETWORK or network_graph is None:
        return current_preferences
    alpha = config.SOCIAL_INFLUENCE_STRENGTH
    iterations = config.SOCIAL_INFLUENCE_ITERATIONS
    if not isinstance(current_preferences, dict) or not current_preferences or alpha <= 0:
        return current_preferences

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulating Social Network Influence ---")
    print(f"DEBUG {func_name}: Starting. Prefs type: {type(current_preferences)}, Num electors: {len(current_preferences)}")  # DEBUG

    next_prefs_social = None
    try:
        all_candidate_names = set()
        # ... (logica estrazione all_candidate_names come prima) ...
        if not all_candidate_names:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_WARNING, "Social influence skipped: No candidates.")
            print(f"DEBUG {func_name}: Ret original (No cands)."); return current_preferences
        try:  # Deepcopy
            next_prefs_social = copy.deepcopy(current_preferences)
            if not isinstance(next_prefs_social, dict):
                 raise TypeError(
                     f"deepcopy returned {type(next_prefs_social)}")
        except Exception as e_copy:
            print(f"ERROR {func_name}: deepcopy failed: {e_copy}"); utils.send_pygame_update(utils.UPDATE_TYPE_ERROR, f"SI deepcopy failed: {e_copy}"); print(f"DEBUG {func_name}: Ret original (deepcopy fail)."); return current_preferences
        # Iterazioni
        for iter_num in range(iterations):
            if hasattr(utils, 'simulation_running_event') and not utils.simulation_running_event.is_set():
                print(f"DEBUG {func_name}: Ret current (stop signal).")
                return next_prefs_social if isinstance(next_prefs_social, dict) else current_preferences
            current_iteration_prefs = copy.deepcopy(next_prefs_social)
            # Ciclo Elettori
            for elector_id_social, elector_data_social in current_iteration_prefs.items():
                # ... (Controlli e calcolo media vicini come prima) ...
                # Aggiorna leanings e pesi in next_prefs_social
                if elector_id_social in next_prefs_social and isinstance(next_prefs_social[elector_id_social], dict):
                    # ... (Logica aggiornamento leaning e apprendimento agente come prima) ...
                    pass  # Placeholder per logica interna
            # print(f"DEBUG {func_name}: Iteration {iter_num + 1}/{iterations} complete.")

        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE, f"Social influence computed ({iterations} iter, strength={alpha:.2f}).")
        # DEBUG
        print(
            f"DEBUG {func_name}: Finished successfully. Returning type: {type(next_prefs_social)}")
        if not isinstance(next_prefs_social, dict):
            print(
                f"CRITICAL DEBUG {func_name}: Not dict before final return! Type: {type(next_prefs_social)}.")
            return current_preferences  # Fallback
        return next_prefs_social  # Ritorno Normale

    except Exception as e_inner:  # Cattura errori interni
        tb_inner = traceback.format_exc()
        error_msg_inner = f"CRITICAL ERROR INSIDE {func_name}: {e_inner}\n{tb_inner}"
        print(error_msg_inner); utils.send_pygame_update(
            utils.UPDATE_TYPE_ERROR, error_msg_inner)
        # DEBUG
        print(f"DEBUG {func_name}: Returning None due to internal exception.")
        return None  # Ritorno Esplicito None in caso di errore interno


def verify_election(current_results, num_electors, required_majority_percentage):
    """Verifica se un candidato è stato eletto."""
    # ... (Codice completo come mostrato prima) ...
    votes_needed = math.ceil(
         num_electors * required_majority_percentage) if num_electors > 0 else 1
     return None, votes_needed, 0  # Placeholder


def count_votes(votes_list):
    """Conta i voti per ogni candidato da una lista, filtrando None."""
    # ... (Codice completo come mostrato prima) ...
    if not isinstance(votes_list, list):
         return Counter()
     valid_votes = [vote for vote in votes_list if vote is not None]
     return Counter(valid_votes)
