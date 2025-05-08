import random
import math
from collections import Counter
import copy
import networkx as nx
import uuid  # Import uuid for db_manager interaction
import json  # Import json for db_manager interaction
# Imports da altri moduli del progetto (modificati da relativi a assoluti)
import config
import utils
import db_manager  # Import db_manager


# Funzione per identificare elettori chiave (Spostata qui da election.py)
def identify_key_electors(elector_preferences_data,
                          current_results,
                          num_top_candidates_to_consider=3):
    """Identifica elettori chiave (swing, influenzabili)."""
    key_electors_summary = []
    if not elector_preferences_data or not current_results:
        return key_electors_summary
    top_cand_names = [
        item[0]
        for item in current_results.most_common(num_top_candidates_to_consider)
    ]

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
            top_leans = sorted([{
                'name': cn,
                'leaning': leanings[cn]
            } for cn in top_cand_names if cn in leanings],
                key=lambda x: x['leaning'],
                reverse=True)
            if len(top_leans) >= 2:
                diff = top_leans[0]['leaning'] - top_leans[1]['leaning']
                if abs(diff) < config.ELECTOR_SWING_THRESHOLD:
                    is_key = True
                    reasons.append(
                        f"Swing b/w {top_leans[0]['name']} ({top_leans[0]['leaning']:.1f}) & {top_leans[1]['name']} ({top_leans[1]['leaning']:.1f})"
                    )
        if is_key:
            key_electors_summary.append({
                "id": e_id,
                "reasons": list(set(reasons))
            })
    return key_electors_summary


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


def analyze_competition_and_adapt_strategy(candidate_info, all_candidates_info,
                                           last_round_results, current_round):
    """
    Analyzes the competitive landscape and adapts the candidate's campaign strategy.
    This is a basic rule-based adaptation.
    """
    cand_name = candidate_info['name']
    cand_attrs = candidate_info.get("attributes", {})
    current_themes = candidate_info.get('current_campaign_themes', [])

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"  {cand_name} analyzing competition (Round {current_round})...")

    # 1. Gather Info: Use last round results as simulated poll data
    if not last_round_results or sum(last_round_results.values()) == 0:
        # If no results yet, stick to initial strategy (based on attributes)
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "    No previous results to analyze.")
        # Ensure themes are initialized if not already
        if not current_themes:
            sorted_attrs = sorted(cand_attrs.items(),
                                  key=lambda i: i[1],
                                  reverse=True)
            current_themes = [
                a[0] for a in sorted_attrs[:random.randint(1, 2)]
            ]
            candidate_info['current_campaign_themes'] = current_themes
        return

    total_votes = sum(last_round_results.values())
    sorted_results = last_round_results.most_common()

    # Find own position and top opponents
    own_votes = last_round_results.get(cand_name, 0)
    own_rank = next((i + 1 for i, (name, votes) in enumerate(sorted_results)
                     if name == cand_name),
                    len(sorted_results) + 1)
    top_opponents_data = [
        (name, votes) for name, votes in
        sorted_results[:config.COMPETITIVE_ADAPTATION_TOP_OPPONENTS + 1]
        if name != cand_name
    ][:config.COMPETITIVE_ADAPTATION_TOP_OPPONENTS]
    top_opponent_names = [name for name, votes in top_opponents_data]

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"    Rank: {own_rank}/{len(sorted_results)}. Top opps: {top_opponent_names}"
    )

    # 2. Analyze & 3. Adapt Strategy
    new_themes = []
    available_attrs = list(cand_attrs.keys())

    # Strategy A: Focus on strengths (influenced by self-focus factor)
    # Pick themes where candidate has high attribute values
    sorted_cand_attrs = sorted(cand_attrs.items(),
                               key=lambda i: i[1],
                               reverse=True)
    strength_themes = [attr for attr, val in sorted_cand_attrs
                       if val >= 4]  # Focus on high attributes

    # Strategy B: Counter/Attack opponents (influenced by 1 - self-focus factor)
    # Identify themes where opponents are strong, potentially counter them
    opponent_strength_themes = {}
    for opp_name in top_opponent_names:
        opp_info = next(
            (c for c in all_candidates_info if c['name'] == opp_name), None)
        if opp_info and opp_info.get('attributes'):
            for attr, val in opp_info['attributes'].items():
                if val >= 4:  # Opponent is strong in this attribute
                    opponent_strength_themes[
                        attr] = opponent_strength_themes.get(attr, 0) + 1

    # Sort opponent themes by how many top opponents are strong in them
    sorted_opp_themes = sorted(opponent_strength_themes.items(),
                               key=lambda i: i[1],
                               reverse=True)
    counter_themes_pool = [attr for attr, count in sorted_opp_themes]

    # Combine strategies based on competitive adaptation factors
    num_themes_to_pick = random.randint(1, 2)
    picked_count = 0

    # Prioritize self-focus themes
    for theme in strength_themes:
        if picked_count < num_themes_to_pick and random.random(
        ) < config.COMPETITIVE_ADAPTATION_SELF_FOCUS_FACTOR:
            if theme in available_attrs and theme not in new_themes:  # Check if it's a valid attribute
                new_themes.append(theme)
                picked_count += 1

    # Fill remaining slots (if any) with counter themes
    if picked_count < num_themes_to_pick:
        for theme in counter_themes_pool:
            if picked_count < num_themes_to_pick and random.random() < (
                    1.0 - config.COMPETITIVE_ADAPTATION_SELF_FOCUS_FACTOR):
                if theme in available_attrs and theme not in new_themes:  # Check if it's a valid attribute
                    new_themes.append(theme)
                    picked_count += 1

    # Fallback: if strategy didn't yield enough themes, pick randomly from strengths or own high attributes
    if picked_count < num_themes_to_pick:
        fallback_pool = list(
            set(strength_themes +
                available_attrs))  # Pool of own relevant themes
        random.shuffle(fallback_pool)
        for theme in fallback_pool:
            if picked_count < num_themes_to_pick:
                if theme not in new_themes:
                    new_themes.append(theme)
                    picked_count += 1

    # Ensure themes are valid attributes
    final_themes = [t for t in new_themes if t in available_attrs]
    if not final_themes:  # If no themes were picked, default to top attribute
        if sorted_cand_attrs:
            final_themes = [sorted_cand_attrs[0][0]
                            ]  # Pick highest attribute as theme

    candidate_info['current_campaign_themes'] = final_themes
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"    Adapted themes: {', '.join(t.replace('_',' ').title() for t in final_themes)}"
    )


def simulate_campaigning(candidates_info, electors,
                         elector_full_preferences_data, last_round_results):
    """Simulates campaigning considering Media Literacy and Confirmation Bias,
       using dynamically adapted themes and strategic budget allocation."""
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulating Candidate Campaigning ---")
    if not candidates_info or not electors:
        return

    elector_map = {e['id']: e for e in electors}
    elector_ids = list(elector_map.keys())

    key_electors_summary = identify_key_electors(elector_full_preferences_data,
                                                 last_round_results)
    key_elector_ids = {ke['id'] for ke in key_electors_summary}

    elector_potentials = {}
    for e_obj in electors:
        e_id = e_obj['id']
        e_prefs = elector_full_preferences_data.get(e_id, {})
        e_traits = e_obj.get('traits', [])
        elector_potential_score = config.ELECTOR_SUSCEPTIBILITY_BASE
        if "Easily Influenced" in e_traits:
            elector_potential_score *= config.INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED
        if e_id in key_elector_ids:
            elector_potential_score *= config.TARGETING_KEY_ELECTOR_BONUS_FACTOR
        elector_potentials[e_id] = max(0.1, min(5.0, elector_potential_score))

    total_potential_sum = sum(
        elector_potentials.values()) if elector_potentials else 1.0
    elector_allocation_weights = {
        e_id: pot / total_potential_sum
        for e_id, pot in elector_potentials.items()
    }

    for cand_idx, cand_data in enumerate(candidates_info):
        if not utils.pygame_update_queue.empty():  # Process queue to allow stop signals
            if utils.pygame_update_queue.get_nowait() == utils.UPDATE_TYPE_FLAG and not utils.simulation_running_event.is_set():  # Simplified check
                return

        cand_name = cand_data['name']
        cand_attrs = cand_data.get("attributes", {})
        cand_med = cand_attrs.get(
            'mediation_ability', config.ATTRIBUTE_RANGE[0])
        themes = cand_data.get('current_campaign_themes', [])
        current_candidate_budget = float(cand_data.get(
            'campaign_budget', 0))  # Budget per QUESTO candidato
        min_cost_per_elector = float(
            config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[0])

        num_electors_to_target = config.INFLUENCE_ELECTORS_PER_CANDIDATE
        if num_electors_to_target <= 0 or not elector_ids:
            continue

        target_ids = []
        if total_potential_sum > 0:
            # Simplified weighted sampling for brevity (consider more robust methods if needed)
            # This is a placeholder, use a proper weighted random sampling
            if elector_ids:
                target_ids = random.sample(elector_ids, min(
                    num_electors_to_target, len(elector_ids)))

        else:
            if elector_ids:
                target_ids = random.sample(elector_ids, min(
                    num_electors_to_target, len(elector_ids)))

        successful_influences_this_candidate = 0
        electors_targeted_this_candidate = 0
        # total_budget_spent_this_candidate_this_round = 0 # Not strictly needed if only updating current_candidate_budget

        for e_id in target_ids:
            if not utils.pygame_update_queue.empty():  # Process queue
                if utils.pygame_update_queue.get_nowait() == utils.UPDATE_TYPE_FLAG and not utils.simulation_running_event.is_set():  # Simplified check
                    # Before breaking, save the current state of this candidate's budget
                    candidates_info[cand_idx]['campaign_budget'] = current_candidate_budget
                    db_manager.save_candidate({
                        'uuid': cand_data.get('uuid', str(uuid.uuid4())), 'name': cand_name,
                        'current_budget': current_candidate_budget, 'gender': cand_data.get('gender'),
                        'age': cand_data.get('age'), 'party_id': cand_data.get('party_id'),
                        'initial_budget': cand_data.get('initial_budget', config.INITIAL_CAMPAIGN_BUDGET),
                        'attributes': cand_attrs, 'traits': cand_data.get('traits', []),
                        'stats': cand_data.get('stats', {})
                    })
                    return

            # check min_cost > 0 to avoid issues if it's 0
            if current_candidate_budget < min_cost_per_elector and min_cost_per_elector > 0:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"  {cand_name} budget low ({current_candidate_budget:.2f}). Campaigning for this elector skipped."
                )
                break

            electors_targeted_this_candidate += 1
            e_info = elector_map.get(e_id)
            e_prefs = elector_full_preferences_data.get(e_id)
            if not e_info or not e_prefs:
                continue
            e_traits = e_info.get('traits', [])

            elector_weight = elector_allocation_weights.get(e_id, 0)
            alloc_range_size = float(
                config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1]) - min_cost_per_elector

            # Ensure alloc_range_size is not negative
            alloc_range_size = max(0, alloc_range_size)

            alloc_for_this_elector = min_cost_per_elector + elector_weight * alloc_range_size
            alloc_for_this_elector = min(
                current_candidate_budget, alloc_for_this_elector)
            alloc_for_this_elector = max(
                min_cost_per_elector, alloc_for_this_elector) if current_candidate_budget >= min_cost_per_elector and min_cost_per_elector > 0 else 0

            # If couldn't meet min_cost, but has budget
            if alloc_for_this_elector == 0 and current_candidate_budget > 0 and min_cost_per_elector > 0:
                alloc_for_this_elector = min(
                    current_candidate_budget, min_cost_per_elector) if current_candidate_budget >= min_cost_per_elector else 0

            current_candidate_budget -= alloc_for_this_elector
            # total_budget_spent_this_candidate_this_round += alloc_for_this_elector # If tracking total spent

            base_sus = config.ELECTOR_SUSCEPTIBILITY_BASE + \
                random.uniform(-0.2, 0.2)
            if "Easily Influenced" in e_traits:
                base_sus *= config.INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED
            if "Loyal" in e_traits:
                cand_party = cand_data.get('party_id', 'Unknown')
                elector_party = e_prefs.get('party_preference', 'Independent')
                if cand_party != 'Independent' and elector_party != 'Independent' and cand_party != elector_party:
                    base_sus *= config.INFLUENCE_TRAIT_MULTIPLIER_LOYAL

            lit_score = e_prefs.get(
                'media_literacy', config.MEDIA_LITERACY_RANGE[0])
            min_l, max_l = config.MEDIA_LITERACY_RANGE
            norm_lit = (lit_score - min_l) / \
                (max_l - min_l) if (max_l - min_l) > 0 else 0
            lit_reduc = norm_lit * config.MEDIA_LITERACY_EFFECT_FACTOR
            final_sus = max(0.05, min(0.95, base_sus * (1.0 - lit_reduc)))

            base_chance = (cand_med / config.ATTRIBUTE_RANGE[1]) * final_sus

            alloc_success_bonus = 0
            # Avoid division by zero
            if config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1] > 0:
                alloc_success_bonus = (
                    alloc_for_this_elector / config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1]) * config.CAMPAIGN_ALLOCATION_SUCCESS_CHANCE_FACTOR

            final_chance = max(
                0.05, min(1.0, base_chance + alloc_success_bonus))

            if random.random() < final_chance:
                successful_influences_this_candidate += 1
                base_inf = config.INFLUENCE_STRENGTH_FACTOR * \
                    config.MAX_ELECTOR_LEANING_BASE * random.uniform(0.8, 1.2)

                alloc_inf_bonus = 0
                # Avoid division by zero
                if config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1] > 0:
                    alloc_inf_bonus = (
                        alloc_for_this_elector / config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1]) * config.CAMPAIGN_ALLOCATION_INFLUENCE_FACTOR

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
                            theme_bonus += config.CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE * norm_w * \
                                random.uniform(
                                    1.0, 1.5 if t in themes else 0.8)  # Simplified
                total_inf += theme_bonus

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

                if cand_name in e_prefs['leanings']:
                    e_prefs['leanings'][cand_name] = max(
                        0.1, e_prefs['leanings'][cand_name] + adj_inf)

                learning_adj = config.ELECTOR_LEARNING_RATE * \
                    config.CAMPAIGN_EXPOSURE_LEARNING_EFFECT * \
                    random.uniform(-0.5, 0.5)
                e_prefs['identity_weight'] = max(
                    0.1, min(0.9, e_prefs.get('identity_weight', 0.5) + learning_adj))
                e_prefs['policy_weight'] = 1.0 - e_prefs['identity_weight']

        # --- Fine ciclo sugli elettori target per questo candidato ---

        # Aggiorna il budget del candidato nella lista originale (che viene passata per riferimento)
        candidates_info[cand_idx]['campaign_budget'] = current_candidate_budget

        # Salva i dati aggiornati del candidato (incluso il budget) nel DB
        db_manager.save_candidate({
            'uuid': cand_data.get('uuid', str(uuid.uuid4())),
            'name': cand_name,
            # Salva il budget aggiornato specifico di questo candidato
            'current_budget': current_candidate_budget,
            'gender': cand_data.get('gender', 'Unknown'),
            'age': cand_data.get('age', 0),
            'party_id': cand_data.get('party_id', 'Unknown'),
            'initial_budget': cand_data.get('initial_budget', config.INITIAL_CAMPAIGN_BUDGET),
            'attributes': cand_attrs,  # Usa gli attributi del candidato corrente
            # Usa i tratti del candidato corrente
            'traits': cand_data.get('traits', []),
            # Usa le stats del candidato corrente
            'stats': cand_data.get('stats', {})
        })

        themes_str = ", ".join([t.replace('_', ' ').title()
                               for t in themes]) if themes else "N/A"
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  Campaign {cand_name} (Themes: {themes_str}): Targeted {electors_targeted_this_candidate} electors ({successful_influences_this_candidate} succ.). Budget left: {current_candidate_budget:.2f}"
        )
    # --- Fine ciclo su candidates_info ---


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
    # Get all unique candidate names that electors have leanings towards
    all_cands = set().union(*(d.get('leanings', {}).keys()
                              for d in current_preferences.values()))
    if not all_cands:
        return current_preferences

    next_prefs = copy.deepcopy(
        current_preferences
    )  # Create a deep copy to store next round preferences
    # Iterate for the specified number of influence iterations
    for _ in range(iterations):
        curr_iter_prefs = copy.deepcopy(
            next_prefs
        )  # Work on a copy of the current iteration's preferences
        # Iterate through each elector
        for e_id, e_data in curr_iter_prefs.items():
            if e_id not in network_graph:
                continue  # Skip if elector is not in the network graph

            neighbors = list(
                network_graph.neighbors(e_id))  # Get list of neighbors
            n_count = len(neighbors)  # Number of neighbors
            e_leans = e_data.get('leanings', {})  # Current elector's leanings

            if n_count > 0:
                # Calculate the average leaning of neighbors for each candidate
                avg_neigh_leans = {c: 0.0 for c in all_cands}
                neigh_counted = {c: 0 for c in all_cands}
                for n_id in neighbors:
                    n_leans = curr_iter_prefs.get(n_id, {}).get(
                        'leanings', {})  # Neighbor's leanings
                    for c in all_cands:
                        if c in n_leans:
                            avg_neigh_leans[c] += n_leans[c]
                            neigh_counted[c] += 1
                # Calculate the average leaning for each candidate, using elector's own leaning as the average
                for c in all_cands:
                    if neigh_counted[c] > 0:
                        avg_neigh_leans[c] /= neigh_counted[c]
                    else:
                        # If no neighbors have a leaning for this candidate, use the elector's own leaning as the average
                        avg_neigh_leans[c] = e_leans.get(c, 0)

                # Update the elector's leanings based on their current leaning and the average neighbor leaning
                target_leans = next_prefs[e_id].get(
                    'leanings',
                    {})  # Get the leanings to be updated in the next state

                for c in all_cands:
                    curr_l = e_leans.get(c, 0)  # Current leaning
                    avg_n = avg_neigh_leans[c]  # Average neighbor leaning

                    # Apply influence on leaning using the alpha factor (Deffuant-Weisbuch like update)
                    # This updates the leaning in the next_prefs for the *next* iteration
                    next_prefs[e_id]['leanings'][c] = max(
                        0.1, (1 - alpha) * curr_l +
                        alpha * avg_n)  # Ensure leaning stays above 0.1

                    # --- Elector Learning: Social Influence Exposure ---
                    # Elector learns/adopts the importance of identity vs policy based on exposure to social influence
                    # Exposure to influence (especially strong influence) might make them more or less identity-focused.
                    influence_magnitude = abs(
                        avg_n - curr_l)  # Magnitude of influence received

                    # Trigger learning based on influence magnitude and learning effect threshold
                    if influence_magnitude > config.SOCIAL_INFLUENCE_LEARNING_EFFECT * 2:  # If influence is significant

                        learning_adj = config.ELECTOR_LEARNING_RATE * config.SOCIAL_INFLUENCE_LEARNING_EFFECT * influence_magnitude * random.uniform(
                            -1.0, 1.0
                        )  # Adjustment proportional to influence magnitude and randomness

                        # Apply learning adjustment to identity_weight (and update policy_weight)
                        next_prefs[e_id]['identity_weight'] = max(
                            0.1,
                            min(
                                0.9,
                                next_prefs[e_id].get('identity_weight', 0.5) +
                                learning_adj)
                        )  # Get identity weight from the next_prefs (updated in previous influence step if iterations > 1)
                        next_prefs[e_id][
                            'policy_weight'] = 1.0 - next_prefs[e_id][
                                'identity_weight']  # Ensure policy weight is complementary

    # The final 'next_prefs' after all iterations is returned, containing updated leanings and weights.
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
        return None, votes_needed, votes_needed  # No results, no winner
    votes_needed = math.ceil(num_electors * required_majority_percentage)
    sorted_res = current_results.most_common()  # Get results sorted by votes
    if sorted_res:
        top_cand, top_votes = sorted_res[
            0]  # Get the top candidate and their votes

        # Check if top candidate has enough votes
        if top_votes >= votes_needed:
            # Check for ties with the top candidate
            if len(sorted_res) > 1 and sorted_res[1][1] == top_votes:
                return None, votes_needed, votes_needed  # It's a tie, no single winner
            else:
                return top_cand, votes_needed, votes_needed  # Top candidate wins

    # If no one reached the majority or there was a tie at the top
    return None, votes_needed, votes_needed


def count_votes(votes):
    """Counts votes for each candidate."""
    return Counter(
        votes
    )  # Use Counter to count occurrences of each vote (candidate name)
