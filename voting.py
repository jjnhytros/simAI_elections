import random
import math
from collections import Counter
import copy  # Necessario per deepcopy
# Necessario per tipo grafo (anche se usato in generation.py)
import networkx as nx
# Imports da altri moduli del progetto (modificati da relativi a assoluti)
import config
import utils


# Funzioni per cittadini (rimangono semplici per ora)
def initialize_citizen_preferences(num_citizens, district_candidates):
    """Assigns random ideal preferences and traits to citizens."""
    preferences = {}
    for i in range(num_citizens):
        citizen_id = f"Citizen_{i+1}"
        assigned_traits = []
        if config.CITIZEN_TRAITS:
            assigned_traits = random.sample(
                config.CITIZEN_TRAITS,
                min(config.CITIZEN_TRAIT_COUNT, len(config.CITIZEN_TRAITS)))
        preferences[citizen_id] = {
            "preference_experience":
            random.randint(*config.CITIZEN_IDEAL_PREFERENCE_RANGE),
            "preference_social_vision":
            random.randint(*config.CITIZEN_IDEAL_PREFERENCE_RANGE),
            "preference_mediation":
            random.randint(*config.CITIZEN_IDEAL_PREFERENCE_RANGE),
            "preference_integrity":
            random.randint(*config.CITIZEN_IDEAL_PREFERENCE_RANGE),
            "traits":
            assigned_traits
        }
    return preferences


def simulate_citizen_vote(citizen_id, district_candidates_info, citizen_data):
    """Simulates the vote of a single citizen based on attribute preferences and traits."""
    candidates_dict = {c["name"]: c for c in district_candidates_info}
    candidate_names = list(candidates_dict.keys())
    if not candidate_names:
        return None

    citizen_preferences = {
        k: v
        for k, v in citizen_data.items() if k.startswith("preference_")
    }
    citizen_traits = citizen_data.get("traits", [])
    attraction_scores = {}

    for candidate_name in candidate_names:
        candidate = candidates_dict.get(candidate_name)
        if not candidate or "attributes" not in candidate:
            continue
        candidate_attrs = candidate["attributes"]
        exp_dist = abs(
            candidate_attrs.get("administrative_experience",
                                config.ATTRIBUTE_RANGE[0]) -
            citizen_preferences.get("preference_experience",
                                    config.CITIZEN_IDEAL_PREFERENCE_RANGE[0]))
        soc_dist = abs(
            candidate_attrs.get("social_vision", config.ATTRIBUTE_RANGE[0]) -
            citizen_preferences.get("preference_social_vision",
                                    config.CITIZEN_IDEAL_PREFERENCE_RANGE[0]))
        med_dist = abs(
            candidate_attrs.get("mediation_ability",
                                config.ATTRIBUTE_RANGE[0]) -
            citizen_preferences.get("preference_mediation",
                                    config.CITIZEN_IDEAL_PREFERENCE_RANGE[0]))
        int_dist = abs(
            candidate_attrs.get("ethical_integrity",
                                config.ATTRIBUTE_RANGE[0]) -
            citizen_preferences.get("preference_integrity",
                                    config.CITIZEN_IDEAL_PREFERENCE_RANGE[0]))
        total_distance = exp_dist + soc_dist + med_dist + int_dist
        score = (
            config.MAX_CITIZEN_LEANING_BASE -
            total_distance * config.CITIZEN_ATTRIBUTE_MISMATCH_PENALTY_FACTOR)

        trait_multiplier = 1.0
        random_bias = random.uniform(-0.5, 0.5)
        if "Attribute Focused" in citizen_traits:
            trait_multiplier *= config.CITIZEN_TRAIT_MULTIPLIER_ATTRIBUTE_FOCUSED
            random_bias *= 0.5
        if "Random Inclined" in citizen_traits:
            random_bias += random.uniform(
                -config.CITIZEN_TRAIT_RANDOM_INCLINED_BIAS,
                config.CITIZEN_TRAIT_RANDOM_INCLINED_BIAS)
        final_score = (score * trait_multiplier) + random_bias
        attraction_scores[candidate_name] = max(0.1, final_score)

    candidates_for_choice = list(attraction_scores.keys())
    weights_for_choice = [max(0, w) for w in attraction_scores.values()]
    if not candidates_for_choice or sum(weights_for_choice) <= 0:
        return random.choice(candidate_names) if candidate_names else None
    try:
        return random.choices(candidates_for_choice,
                              weights=weights_for_choice,
                              k=1)[0]
    except ValueError:
        return random.choice(candidate_names) if candidate_names else None


# Funzioni per elettori del collegio
def initialize_elector_preferences(electors_with_traits,
                                   candidates,
                                   preselected_candidates_info=None):
    """
    Initializes elector preferences including policy/identity weights and media literacy.
    Calculates initial leanings based on policy and identity alignment.
    """
    elector_full_preferences_data = {}
    candidates_dict = {c["name"]: c for c in candidates}
    preselected_names = {c["name"]
                         for c in preselected_candidates_info
                         } if preselected_candidates_info else set()

    for elector_data in electors_with_traits:
        elector_id = elector_data['id']
        elector_traits = elector_data['traits']
        elector_prefs = {
            'weights': {
                attr: random.randint(*config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE)
                for attr in [
                    "administrative_experience", "social_vision",
                    "mediation_ability", "ethical_integrity"
                ]
            },
            'leanings': {},
            'initial_leanings': {},
            'traits':
            elector_traits,
            'party_preference':
            random.choices(config.PARTY_IDS,
                           weights=config.PARTY_ID_ASSIGNMENT_WEIGHTS,
                           k=1)[0],
            'identity_weight':
            random.uniform(*config.IDENTITY_WEIGHT_RANGE),
            'media_literacy':
            random.randint(
                *config.MEDIA_LITERACY_RANGE)  # Aggiunta Media Literacy
        }
        if "Strong Partisan" in elector_traits:
            elector_prefs['identity_weight'] = min(
                0.95, elector_prefs['identity_weight'] * 1.5)
        elector_prefs['policy_weight'] = 1.0 - elector_prefs['identity_weight']

        elector_ideal_prefs = {
            f"preference_{attr}":
            random.randint(*config.ELECTOR_IDEAL_PREFERENCE_RANGE)
            for attr in elector_prefs['weights']
        }
        elector_prefs.update(elector_ideal_prefs)

        for cand_name, cand in candidates_dict.items():
            cand_attrs = cand.get("attributes", {})
            cand_party = cand.get('party_id', 'Unknown')
            # Policy Score
            w_dist_sum = sum(
                abs(
                    cand_attrs.get(attr, config.ATTRIBUTE_RANGE[0]) -
                    elector_ideal_prefs[f"preference_{attr}"]) * weight
                for attr, weight in elector_prefs['weights'].items()
                if f"preference_{attr}" in elector_ideal_prefs)
            penalty = w_dist_sum * config.ELECTOR_ATTRIBUTE_MISMATCH_PENALTY_FACTOR
            lean_policy = max(0.1, config.MAX_ELECTOR_LEANING_BASE - penalty)
            # Identity Score
            id_score = 0.0
            if elector_prefs[
                    'party_preference'] != "Independent" and cand_party == elector_prefs[
                        'party_preference']:
                id_score = config.MAX_ELECTOR_LEANING_BASE * config.IDENTITY_MATCH_BONUS_FACTOR
            # Combine
            lean_base = (lean_policy * elector_prefs['policy_weight']) + (
                id_score * elector_prefs['identity_weight'])
            # Trait Effects
            if "Idealistic" in elector_traits and cand_attrs.get(
                    "ethical_integrity", config.ATTRIBUTE_RANGE[0]) <= 2:
                penalty_f = getattr(
                    config,
                    "STRATEGIC_VOTING_TRAIT_PENALTY_IDEALISTIC_INTEGRITY", 1.5)
                lean_base -= config.MAX_ELECTOR_LEANING_BASE * 0.2 * penalty_f
            # Final Initial Leaning
            init_lean = lean_base + random.uniform(
                -config.ELECTOR_RANDOM_LEANING_VARIANCE,
                config.ELECTOR_RANDOM_LEANING_VARIANCE)
            if cand_name in preselected_names:
                init_lean += config.PRESELECTED_CANDIDATE_BOOST
            elector_prefs['leanings'][cand_name] = max(0.1, init_lean)
            elector_prefs['initial_leanings'][cand_name] = elector_prefs[
                'leanings'][cand_name]

        elector_full_preferences_data[elector_id] = elector_prefs
    return elector_full_preferences_data


def simulate_ai_vote(elector_id,
                     votable_candidates_info,
                     elector_data,
                     last_round_results=None,
                     current_round=0,
                     all_candidates_info=None):
    """Simulates elector vote considering leanings, biases (Bandwagon/Underdog), and strategy."""
    elector_leanings = elector_data.get('leanings', {})
    elector_initial_leanings = elector_data.get('initial_leanings', {})
    elector_traits = elector_data.get('traits', [])
    votable_names = {c["name"] for c in votable_candidates_info}
    current_leanings = {
        n: l
        for n, l in elector_leanings.items() if n in votable_names
    }
    if not current_leanings:
        votable_list = list(votable_names)
        return random.choice(votable_list) if votable_list else None

    # Apply Biases
    final_leanings = current_leanings.copy()
    total_votes_prev = sum(
        last_round_results.values()) if last_round_results else 0
    if last_round_results and total_votes_prev > 0 and current_round > 0:
        is_band = "Bandwagoner" in elector_traits
        is_under = "Underdog Supporter" in elector_traits or "Contrarian" in elector_traits
        if is_band or is_under:
            avg_share = 1.0 / len(final_leanings) if final_leanings else 0.1
            for name in final_leanings.keys():
                if name not in last_round_results:
                    continue
                share = last_round_results.get(name, 0) / total_votes_prev
                adj = 0.0
                if is_band and share > avg_share:
                    adj += (
                        share - avg_share
                    ) * config.BANDWAGON_EFFECT_FACTOR * config.MAX_ELECTOR_LEANING_BASE
                if is_under and share < avg_share * 0.75:
                    adj += (
                        avg_share - share
                    ) * config.UNDERDOG_EFFECT_FACTOR * config.MAX_ELECTOR_LEANING_BASE
                adj = min(adj, config.MAX_BIAS_LEANING_ADJUSTMENT)
                final_leanings[name] = max(0.1, final_leanings[name] + adj)

    if not final_leanings:
        votable_list = list(votable_names)
        return random.choice(votable_list) if votable_list else None
    most_preferred = max(final_leanings, key=final_leanings.get)

    # Strategic Vote Logic
    strategic_vote = None
    if current_round >= config.STRATEGIC_VOTING_START_ROUND and last_round_results and all_candidates_info:
        pref_votes = last_round_results.get(most_preferred, 0)
        pref_share = pref_votes / total_votes_prev if total_votes_prev > 0 else 0
        is_unlikely = pref_share < config.UNLIKELY_TO_WIN_THRESHOLD
        if is_unlikely:
            mod = 1.0
            if "Pragmatic" in elector_traits:
                mod *= config.STRATEGIC_VOTING_TRAIT_MULTIPLIER_PRAGMATIC
            if "Idealistic" in elector_traits:
                mod *= config.STRATEGIC_VOTING_TRAIT_MULTIPLIER_IDEALISTIC
            if elector_initial_leanings:
                votable_init = {
                    n: l
                    for n, l in elector_initial_leanings.items()
                    if n in votable_names
                }
                if votable_init:
                    disliked_init = min(votable_init, key=votable_init.get)
                    disliked_lean = votable_init.get(
                        disliked_init, config.MAX_ELECTOR_LEANING_BASE)
                    is_disliked = disliked_lean < config.MAX_ELECTOR_LEANING_BASE * \
                        config.STRONGLY_DISLIKED_THRESHOLD_FACTOR
                    if is_disliked and disliked_init in votable_names:
                        options = {
                            n: l
                            for n, l in final_leanings.items()
                            if n != disliked_init and n != most_preferred
                        }
                        if options:
                            pot_choice = max(options, key=options.get)
                            disliked_votes = last_round_results.get(
                                disliked_init, 0)
                            disliked_share = disliked_votes / total_votes_prev if total_votes_prev > 0 else 0
                            chance = (disliked_share * 0.8 +
                                      (1.0 - pref_share) * 0.2) * mod
                            if random.random() < chance:
                                strategic_vote = pot_choice

    # Final Decision
    if strategic_vote:
        return strategic_vote
    else:
        choices = list(final_leanings.keys())
        weights = [max(0.01, w) for w in final_leanings.values()]
        if not choices or sum(weights) <= 0:
            votable_list = list(votable_names)
            return random.choice(votable_list) if votable_list else None
        try:
            return random.choices(choices, weights=weights, k=1)[0]
        except ValueError:
            votable_list = list(votable_names)
            return random.choice(votable_list) if votable_list else None


def simulate_campaigning(candidates_info, electors,
                         elector_full_preferences_data, last_round_results):
    """Simulates campaigning considering Media Literacy and Confirmation Bias."""
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulating Candidate Campaigning ---")
    if not candidates_info or not electors:
        return

    total_attempts, succ_attempts = 0, 0
    elector_map = {e['id']: e for e in electors}

    for cand in candidates_info:
        cand_name = cand['name']
        cand_attrs = cand.get("attributes", {})
        cand_med = cand_attrs.get('mediation_ability',
                                  config.ATTRIBUTE_RANGE[0])
        themes = cand.get('current_campaign_themes', [])
        budget = cand.get('campaign_budget', 0)
        min_cost = config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[0]

        # Targeting
        target_potentials = []
        for e_obj in electors:
            e_id = e_obj['id']
            e_prefs = elector_full_preferences_data.get(e_id, {})
            e_leans = e_prefs.get('leanings', {})
            e_ideals = {
                k.replace('preference_', ''): v
                for k, v in e_prefs.items() if k.startswith('preference_')
            }
            e_traits = e_obj.get('traits', [])
            e_weights = e_prefs.get('weights', {})
            lean_cand = e_leans.get(cand_name, 0)
            potential = 0.0
            sus_f = 1.0
            if "Easily Influenced" in e_traits:
                sus_f *= config.INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED
            if "Loyal" in e_traits and lean_cand > config.MAX_ELECTOR_LEANING_BASE * 0.6:
                sus_f *= config.INFLUENCE_TRAIT_MULTIPLIER_LOYAL
            potential += sus_f * getattr(config, "TARGETING_TRAIT_BASE_SCORE",
                                         1.0)
            opt_range = (config.MAX_ELECTOR_LEANING_BASE * 0.25,
                         config.MAX_ELECTOR_LEANING_BASE * 0.75)
            if opt_range[0] <= lean_cand <= opt_range[1]:
                potential += getattr(config, "TARGETING_OPTIMAL_LEANING_BONUS",
                                     2.0)
            w_dist, max_w_dist = 0.0, 0.0
            if e_ideals and e_weights and cand_attrs:
                for attr, w in e_weights.items():
                    if attr in cand_attrs and attr in e_ideals:
                        w_dist += abs(cand_attrs[attr] - e_ideals[attr]) * w
                    max_w_dist += (config.ATTRIBUTE_RANGE[1] -
                                   config.ATTRIBUTE_RANGE[0]) * w
            align_f = max(0, 1.0 -
                          (w_dist / max_w_dist)) if max_w_dist > 0 else 0
            potential += align_f * getattr(
                config, "TARGETING_ALIGNMENT_BONUS_FACTOR", 3.0)
            target_potentials.append((e_id, potential))

        target_potentials.sort(key=lambda i: i[1], reverse=True)
        targets = target_potentials[:config.INFLUENCE_ELECTORS_PER_CANDIDATE]
        succ_cand, influenced_cnt = 0, 0

        # Execution
        for e_id, potential in targets:
            if budget >= min_cost:
                max_alloc = min(
                    budget, config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1])
                if min_cost > max_alloc:
                    break
                # Budget Allocation
                norm_pot = min(
                    potential / config.MAX_TARGETING_POTENTIAL_SCORE,
                    1.0) if config.MAX_TARGETING_POTENTIAL_SCORE > 0 else 0.5
                alloc_perc = random.uniform(0.6, 1.0) if norm_pot > 0.75 else (
                    random.uniform(0.3, 0.7)
                    if norm_pot > 0.4 else random.uniform(0.1, 0.4))
                alloc = max(
                    min_cost,
                    min(int(min_cost + (max_alloc - min_cost) * alloc_perc),
                        max_alloc))
                budget -= alloc
                influenced_cnt += 1
                total_attempts += 1

                e_info = elector_map.get(e_id)
                e_prefs = elector_full_preferences_data.get(e_id)
                if not e_info or not e_prefs:
                    continue
                e_traits = e_info.get('traits', [])

                # Susceptibility (with Media Literacy)
                base_sus = config.ELECTOR_SUSCEPTIBILITY_BASE + random.uniform(
                    -0.2, 0.2)
                if "Easily Influenced" in e_traits:
                    base_sus *= config.INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED
                if "Loyal" in e_traits:
                    base_sus *= config.INFLUENCE_TRAIT_MULTIPLIER_LOYAL
                lit_score = e_prefs.get('media_literacy',
                                        config.MEDIA_LITERACY_RANGE[0])
                min_l, max_l = config.MEDIA_LITERACY_RANGE
                norm_lit = (lit_score - min_l) / (max_l - min_l) if (
                    max_l - min_l) > 0 else 0
                lit_reduc = norm_lit * config.MEDIA_LITERACY_EFFECT_FACTOR
                final_sus = max(0.05, min(0.95, base_sus * (1.0 - lit_reduc)))

                # Success Chance
                base_chance = (cand_med /
                               config.ATTRIBUTE_RANGE[1]) * final_sus
                alloc_bonus = (
                    alloc - min_cost
                ) * config.CAMPAIGN_ALLOCATION_SUCCESS_CHANCE_FACTOR
                final_chance = max(0.05, min(1.0, base_chance + alloc_bonus))

                # If successful
                if random.random() < final_chance:
                    succ_cand += 1
                    # Influence Amount
                    base_inf = config.INFLUENCE_STRENGTH_FACTOR * config.MAX_ELECTOR_LEANING_BASE * random.uniform(
                        0.8, 1.2)
                    alloc_inf_bonus = (
                        alloc -
                        min_cost) * config.CAMPAIGN_ALLOCATION_INFLUENCE_FACTOR
                    total_inf = min(base_inf + alloc_inf_bonus,
                                    config.MAX_CAMPAIGN_INFLUENCE_PER_ATTEMPT)
                    theme_bonus = 0.0
                    e_weights = e_prefs.get('weights', {})
                    if themes and e_weights:
                        for t in themes:
                            w = e_weights.get(t, 0)
                        if w > config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE[0]:
                            max_w = config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE[1]
                            norm_w = w / max_w if max_w > 0 else 0.5
                            theme_bonus += config.CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE * norm_w
                    total_inf += theme_bonus
                    # Confirmation Bias
                    conf_mod = 1.0
                    if "Confirmation Prone" in e_traits:
                        curr_l = e_prefs.get('leanings', {}).get(cand_name, 0)
                        mid = config.MAX_ELECTOR_LEANING_BASE / 2.0
                        bias_f = config.CONFIRMATION_BIAS_FACTOR
                        if curr_l > mid:
                            conf_mod = bias_f
                        elif curr_l < mid * 0.8:
                            conf_mod = 1.0 / bias_f
                    adj_inf = total_inf * conf_mod
                    # Apply
                    if cand_name in e_prefs['leanings']:
                        e_prefs['leanings'][cand_name] = max(
                            0.1, e_prefs['leanings'][cand_name] + adj_inf)
            else:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"  {cand_name} budget low. Campaign ended.")
                break

        # Update budget & Log
        for c in candidates_info:
            if c['name'] == cand_name:
                c['campaign_budget'] = budget
                break
        themes_str = ", ".join([t.replace('_', ' ').title()
                                for t in themes]) if themes else "N/A"
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  Campaign {cand_name} (Themes: {themes_str}): {influenced_cnt} attempts ({succ_cand} succ.). Budget left: {budget:.2f}"
        )
        succ_attempts += succ_cand

    # Summary Log
    if total_attempts > 0:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  Campaign Summary: Attempts={total_attempts}, Successes={succ_attempts}"
        )
    else:
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "  No campaign attempts.")


def simulate_social_influence(network_graph, current_preferences):
    """Simulates social influence using weighted averaging."""
    if not config.USE_SOCIAL_NETWORK or network_graph is None:
        return current_preferences
    alpha = config.SOCIAL_INFLUENCE_STRENGTH
    iterations = config.SOCIAL_INFLUENCE_ITERATIONS
    if not current_preferences or alpha <= 0:
        return current_preferences

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulating Social Network Influence ---")
    all_cands = set().union(*(d.get('leanings', {}).keys()
                              for d in current_preferences.values()))
    if not all_cands:
        return current_preferences

    next_prefs = copy.deepcopy(current_preferences)
    for _ in range(iterations):
        curr_iter_prefs = copy.deepcopy(next_prefs)
        for e_id, e_data in curr_iter_prefs.items():
            if e_id not in network_graph:
                continue
            neighbors = list(network_graph.neighbors(e_id))
            n_count = len(neighbors)
            e_leans = e_data.get('leanings', {})
            if n_count > 0:
                avg_neigh_leans = {c: 0.0 for c in all_cands}
                neigh_counted = {
                    c: 0
                    for c in all_cands
                }
                for n_id in neighbors:
                    n_leans = curr_iter_prefs.get(n_id, {}).get('leanings', {})
                    for c in all_cands:
                        if c in n_leans:
                            avg_neigh_leans[c] += n_leans[c]
                            neigh_counted[c] += 1
                for c in all_cands:
                    if neigh_counted[c] > 0:
                        avg_neigh_leans[c] /= neigh_counted[c]
                    else:
                        avg_neigh_leans[c] = e_leans.get(c, 0)

                target_leans = next_prefs[e_id].get('leanings', {})
                for c in all_cands:
                    curr_l = e_leans.get(c, 0)
                    avg_n = avg_neigh_leans[c]
                    target_leans[c] = max(0.1,
                                          (1 - alpha) * curr_l + alpha * avg_n)
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"Social influence computed ({iterations} iter, strength={alpha:.2f})."
    )
    return next_prefs


def verify_election(current_results, num_electors,
                    required_majority_percentage):
    """Verifies if a candidate has been elected."""
    if not current_results:
        votes_needed = math.ceil(num_electors * required_majority_percentage)
        return None, votes_needed, votes_needed
    votes_needed = math.ceil(num_electors * required_majority_percentage)
    sorted_res = current_results.most_common()
    if sorted_res:
        top_cand, top_votes = sorted_res[0]
    if top_votes >= votes_needed:
        if len(sorted_res) > 1 and sorted_res[1][1] == top_votes:
            return None, votes_needed, votes_needed
        else:
            return top_cand, votes_needed, votes_needed
    return None, votes_needed, votes_needed


def count_votes(votes):
    """Counts votes for each candidate."""
    return Counter(votes)
