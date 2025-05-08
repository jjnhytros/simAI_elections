# voting.py

import random
import math
from collections import Counter
import copy
import networkx as nx
import uuid
import json

import config
import utils
import db_manager  # Assicurati che sia importato se simulate_campaigning lo usa ancora per caricare/salvare candidati


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
    except ValueError:  # pragma: no cover
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

        # Initialize identity_weight and policy_weight once
        identity_weight = random.uniform(*config.IDENTITY_WEIGHT_RANGE)
        if "Strong Partisan" in elector_traits:
            identity_weight = min(
                0.95, identity_weight *
                1.5)  # Max 0.95 to leave some room for policy
        policy_weight = 1.0 - identity_weight

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
            identity_weight,
            'policy_weight':
            policy_weight,  # Store policy_weight as well
            'media_literacy':
            random.randint(*config.MEDIA_LITERACY_RANGE)
        }

        elector_ideal_prefs = {
            f"preference_{attr}":
            random.randint(*config.ELECTOR_IDEAL_PREFERENCE_RANGE)
            for attr in elector_prefs['weights']
        }
        elector_prefs.update(elector_ideal_prefs)

        for cand_name, cand in candidates_dict.items():
            cand_attrs = cand.get("attributes", {})
            cand_party = cand.get('party_id', 'Unknown')

            w_dist_sum = sum(
                abs(
                    cand_attrs.get(attr, config.ATTRIBUTE_RANGE[0]) -
                    elector_ideal_prefs[f"preference_{attr}"]) * weight
                for attr, weight in elector_prefs['weights'].items()
                if f"preference_{attr}" in elector_ideal_prefs)
            penalty = w_dist_sum * config.ELECTOR_ATTRIBUTE_MISMATCH_PENALTY_FACTOR
            lean_policy = max(0.1, config.MAX_ELECTOR_LEANING_BASE - penalty)

            id_score = 0.0
            if elector_prefs[
                    'party_preference'] != "Independent" and cand_party == elector_prefs[
                        'party_preference']:
                id_score = config.MAX_ELECTOR_LEANING_BASE * config.IDENTITY_MATCH_BONUS_FACTOR

            lean_base = (lean_policy * elector_prefs['policy_weight']) + (
                id_score * elector_prefs['identity_weight'])

            if "Idealistic" in elector_traits and cand_attrs.get(
                    "ethical_integrity", config.ATTRIBUTE_RANGE[0]) <= 2:
                penalty_f = getattr(
                    config,
                    "STRATEGIC_VOTING_TRAIT_PENALTY_IDEALISTIC_INTEGRITY", 1.5)
                lean_base -= config.MAX_ELECTOR_LEANING_BASE * 0.2 * penalty_f

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

    final_leanings = current_leanings.copy()
    total_votes_prev = sum(
        last_round_results.values()) if last_round_results else 0
    if last_round_results and total_votes_prev > 0 and current_round > 0:
        is_band = "Bandwagoner" in elector_traits
        is_under = "Underdog Supporter" in elector_traits or "Contrarian" in elector_traits
        if is_band or is_under:
            avg_share = 1.0 / len(final_leanings) if final_leanings else 0.1
            for name in final_leanings.keys():
                if name not in last_round_results:  # pragma: no cover
                    continue
                share = last_round_results.get(name, 0) / total_votes_prev
                adj = 0.0
                if is_band and share > avg_share:
                    adj += (
                        share - avg_share
                    ) * config.BANDWAGON_EFFECT_FACTOR * config.MAX_ELECTOR_LEANING_BASE
                if is_under and share < avg_share * 0.75:  # Support if significantly underdog
                    adj += (
                        avg_share - share
                    ) * config.UNDERDOG_EFFECT_FACTOR * config.MAX_ELECTOR_LEANING_BASE
                adj = min(adj,
                          config.MAX_BIAS_LEANING_ADJUSTMENT)  # Cap adjustment
                final_leanings[name] = max(0.1, final_leanings[name] + adj)

    if not final_leanings:  # pragma: no cover
        votable_list = list(votable_names)
        return random.choice(votable_list) if votable_list else None

    most_preferred = max(final_leanings, key=final_leanings.get)

    strategic_vote = None
    if current_round >= config.STRATEGIC_VOTING_START_ROUND and last_round_results and all_candidates_info and total_votes_prev > 0:
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
                votable_initial_leanings = {
                    n: l
                    for n, l in elector_initial_leanings.items()
                    if n in votable_names
                }
                if votable_initial_leanings:
                    # Identify most disliked among votable based on *initial* leanings
                    # This helps avoid strategic vote for someone initially very disliked
                    disliked_init_cand_name = min(
                        votable_initial_leanings,
                        key=votable_initial_leanings.get)
                    disliked_init_cand_lean = votable_initial_leanings.get(
                        disliked_init_cand_name,
                        config.MAX_ELECTOR_LEANING_BASE)

                    is_strongly_disliked = disliked_init_cand_lean < (
                        config.MAX_ELECTOR_LEANING_BASE *
                        config.STRONGLY_DISLIKED_THRESHOLD_FACTOR)

                    if is_strongly_disliked and disliked_init_cand_name in votable_names:
                        # Consider alternatives to most_preferred, excluding the strongly_disliked one
                        alternative_options = {
                            n: l
                            for n, l in final_leanings.items()
                            if n != disliked_init_cand_name
                            and n != most_preferred and n in votable_names
                        }
                        if alternative_options:
                            potential_strategic_choice = max(
                                alternative_options,
                                key=alternative_options.get)

                            # Check viability of the disliked candidate
                            disliked_votes_prev = last_round_results.get(
                                disliked_init_cand_name, 0)
                            disliked_share_prev = disliked_votes_prev / \
                                total_votes_prev if total_votes_prev > 0 else 0

                            # Chance to vote strategically: higher if disliked is viable and preferred is not
                            # Simplified chance calculation
                            strategic_chance = (disliked_share_prev * 0.7 +
                                                (1.0 - pref_share) * 0.3) * mod
                            if random.random() < strategic_chance:
                                strategic_vote = potential_strategic_choice

    if strategic_vote:
        return strategic_vote
    else:
        choices = list(final_leanings.keys())
        weights = [max(0.01, w)
                   for w in final_leanings.values()]  # Ensure positive weights
        if not choices or sum(weights) <= 0:  # pragma: no cover
            votable_list = list(votable_names)
            return random.choice(votable_list) if votable_list else None
        try:
            return random.choices(choices, weights=weights, k=1)[0]
        except ValueError:  # pragma: no cover
            # Fallback if weights are problematic (e.g. all zero after clamping, though unlikely)
            votable_list = list(votable_names)
            return random.choice(votable_list) if votable_list else None


def analyze_competition_and_adapt_strategy(candidate_info, all_candidates_info,
                                           last_round_results, current_round):
    """
    Analyzes the competitive landscape and adapts the candidate's campaign strategy.
    """
    cand_name = candidate_info['name']
    cand_attrs = candidate_info.get("attributes", {})
    current_themes = candidate_info.get('current_campaign_themes', [])

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"  {cand_name} analyzing competition (Round {current_round})...")

    if not last_round_results or sum(last_round_results.values()) == 0:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "    No previous results to analyze. Sticking to initial themes.")
        if not current_themes and cand_attrs:  # Ensure themes are initialized if not already
            sorted_attrs = sorted(cand_attrs.items(),
                                  key=lambda i: i[1],
                                  reverse=True)
            current_themes = [
                a[0] for a in sorted_attrs[:random.randint(1, 2)]
            ]
            candidate_info['current_campaign_themes'] = current_themes
        return

    total_votes = sum(last_round_results.values())
    sorted_results_tuples = last_round_results.most_common()

    own_votes = last_round_results.get(cand_name, 0)
    own_rank = next((i + 1
                     for i, (name, votes) in enumerate(sorted_results_tuples)
                     if name == cand_name),
                    len(sorted_results_tuples) + 1)

    top_opponents_data = [
        (name, votes) for name, votes in
        sorted_results_tuples[:config.COMPETITIVE_ADAPTATION_TOP_OPPONENTS + 1]
        if name != cand_name
    ][:config.COMPETITIVE_ADAPTATION_TOP_OPPONENTS]
    top_opponent_names = [name for name, votes in top_opponents_data]

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"    Rank: {own_rank}/{len(sorted_results_tuples)}. Top opps: {top_opponent_names}"
    )

    new_themes = []
    available_attrs_list = list(cand_attrs.keys())  # Ensure it's a list

    # Strategy A: Focus on strengths
    sorted_cand_attrs = sorted(cand_attrs.items(),
                               key=lambda i: i[1],
                               reverse=True)
    strength_themes = [
        attr for attr, val in sorted_cand_attrs
        if val >= 4 and attr in available_attrs_list
    ]

    # Strategy B: Counter/Attack opponents
    opponent_strength_themes_count = Counter()
    for opp_name in top_opponent_names:
        opp_info = next(
            (c for c in all_candidates_info if c['name'] == opp_name), None)
        if opp_info and opp_info.get('attributes'):
            for attr, val in opp_info['attributes'].items():
                if val >= 4 and attr in available_attrs_list:  # Opponent is strong in this valid attribute
                    opponent_strength_themes_count[attr] += 1

    # Sort opponent themes by how many top opponents are strong in them
    counter_themes_pool = [
        attr for attr, count in opponent_strength_themes_count.most_common()
        if attr in available_attrs_list
    ]

    num_themes_to_pick = random.randint(1, 2)
    picked_count = 0

    # Prioritize self-focus themes
    for theme in strength_themes:
        if picked_count < num_themes_to_pick and random.random(
        ) < config.COMPETITIVE_ADAPTATION_SELF_FOCUS_FACTOR:
            if theme not in new_themes:
                new_themes.append(theme)
                picked_count += 1

    # Fill remaining slots with counter themes
    if picked_count < num_themes_to_pick:
        for theme in counter_themes_pool:
            if picked_count < num_themes_to_pick and random.random() < (
                    1.0 - config.COMPETITIVE_ADAPTATION_SELF_FOCUS_FACTOR):
                if theme not in new_themes:
                    new_themes.append(theme)
                    picked_count += 1

    # Fallback: if strategy didn't yield enough themes
    if picked_count < num_themes_to_pick:
        fallback_pool = list(
            set(strength_themes +
                available_attrs_list))  # Pool of own relevant themes
        random.shuffle(fallback_pool)
        for theme in fallback_pool:
            if picked_count < num_themes_to_pick and theme not in new_themes:
                new_themes.append(theme)
                picked_count += 1

    # Ensure themes are valid attributes and at least one theme
    final_themes = [t for t in new_themes if t in available_attrs_list]
    if not final_themes and sorted_cand_attrs:
        final_themes = [
            sorted_cand_attrs[0][0]
        ] if sorted_cand_attrs[0][0] in available_attrs_list else []
        if not final_themes and available_attrs_list:  # Ultimate fallback
            final_themes = [random.choice(available_attrs_list)]

    candidate_info['current_campaign_themes'] = final_themes
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"    Adapted themes: {', '.join(t.replace('_',' ').title() for t in final_themes if t)}"
    )


def simulate_campaigning(candidates_info, electors,
                         elector_full_preferences_data, last_round_results):
    """Simulates campaigning considering Media Literacy and Confirmation Bias,
       using dynamically adapted themes and strategic budget allocation.
       Includes AGENT LEARNING for identity_weight based on campaign exposure.
    """
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulating Candidate Campaigning ---")
    if not candidates_info or not electors:  # pragma: no cover
        return

    elector_map = {e['id']: e for e in electors}
    elector_ids = list(elector_map.keys())

    key_electors_summary = identify_key_electors(elector_full_preferences_data,
                                                 last_round_results)
    key_elector_ids = {ke['id'] for ke in key_electors_summary}

    elector_potentials = {}
    for e_obj in electors:
        e_id = e_obj['id']
        # e_prefs = elector_full_preferences_data.get(e_id, {}) # Not needed for potential score here
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
        e_id: (pot / total_potential_sum if total_potential_sum > 0 else 1.0 /
               len(elector_potentials) if elector_potentials else 0)
        for e_id, pot in elector_potentials.items()
    }

    for cand_idx, cand_data_original in enumerate(candidates_info):
        # Create a copy to modify locally if needed, then update original list
        cand_data = copy.deepcopy(cand_data_original)

        # Check for stop signal from GUI
        if hasattr(
                utils, 'simulation_running_event'
        ) and not utils.simulation_running_event.is_set():  # pragma: no cover
            return

        cand_name = cand_data['name']
        cand_attrs = cand_data.get("attributes", {})
        cand_med = cand_attrs.get('mediation_ability',
                                  config.ATTRIBUTE_RANGE[0])
        themes = cand_data.get('current_campaign_themes', [])
        current_candidate_budget = float(cand_data.get('campaign_budget', 0))
        min_cost_per_elector = float(
            config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[0])
        max_alloc_per_attempt = float(
            config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1])

        num_electors_to_target = config.INFLUENCE_ELECTORS_PER_CANDIDATE
        if num_electors_to_target <= 0 or not elector_ids:  # pragma: no cover
            continue

        target_ids = []
        if total_potential_sum > 0 and elector_ids and elector_allocation_weights:
            # Weighted random sampling (simplified)
            # For a more robust approach, consider `numpy.random.choice` if numpy is available,
            # or a more careful implementation of weighted sampling without replacement.
            # This simplification might over/under sample.
            population = list(elector_allocation_weights.keys())
            weights = list(elector_allocation_weights.values())
            if sum(weights) == 0 and len(
                    weights) > 0:  # handle all zero weights
                weights = [1.0 / len(weights)] * len(weights)

            if population and sum(
                    weights) > 0:  # Ensure population and positive weights
                try:
                    # Attempt to sample with replacement then make unique, or sample without if num_to_sample is small
                    # This is still a simplification of true weighted sampling without replacement.
                    num_to_sample_unique = min(num_electors_to_target,
                                               len(population))
                    sampled_with_replacement = random.choices(
                        population,
                        weights=weights,
                        k=num_to_sample_unique * 2)  # Sample more
                    target_ids = list(
                        set(sampled_with_replacement))[:num_to_sample_unique]
                    # Fill if not enough unique samples
                    while len(target_ids) < num_to_sample_unique:
                        remaining_electors = [
                            eid for eid in population if eid not in target_ids
                        ]
                        if not remaining_electors:
                            break
                        target_ids.append(random.choice(remaining_electors))

                except Exception:  # pragma: no cover # Fallback for any error in choices
                    if elector_ids:
                        target_ids = random.sample(
                            elector_ids,
                            min(num_electors_to_target, len(elector_ids)))
            elif elector_ids:  # Fallback if weights sum to 0
                target_ids = random.sample(
                    elector_ids, min(num_electors_to_target, len(elector_ids)))

        elif elector_ids:  # Fallback if no potential sum
            target_ids = random.sample(
                elector_ids, min(num_electors_to_target, len(elector_ids)))

        successful_influences_this_candidate = 0
        electors_targeted_this_candidate = 0

        for e_id in target_ids:
            if hasattr(utils, 'simulation_running_event'
                       ) and not utils.simulation_running_event.is_set(
            ):  # pragma: no cover
                # Save current candidate's budget before exiting this campaign round due to stop signal
                candidates_info[cand_idx][
                    'campaign_budget'] = current_candidate_budget
                db_manager.save_candidate(
                    candidates_info[cand_idx])  # Save the original dict item
                return

            if current_candidate_budget < min_cost_per_elector and min_cost_per_elector > 0:
                break

            electors_targeted_this_candidate += 1
            e_info = elector_map.get(e_id)
            e_prefs = elector_full_preferences_data.get(e_id)
            if not e_info or not e_prefs:  # pragma: no cover
                continue
            e_traits = e_info.get('traits', [])

            elector_weight = elector_allocation_weights.get(
                e_id, 1.0 / len(elector_allocation_weights)
                if elector_allocation_weights else 0)
            alloc_range_size = max_alloc_per_attempt - min_cost_per_elector
            alloc_range_size = max(0, alloc_range_size)  # Ensure non-negative

            alloc_for_this_elector = min_cost_per_elector + elector_weight * alloc_range_size
            alloc_for_this_elector = min(current_candidate_budget,
                                         alloc_for_this_elector)
            if current_candidate_budget >= min_cost_per_elector and min_cost_per_elector > 0:
                alloc_for_this_elector = max(min_cost_per_elector,
                                             alloc_for_this_elector)
            elif min_cost_per_elector > 0:  # Not enough budget for min_cost
                alloc_for_this_elector = 0
            # If min_cost_per_elector is 0, alloc_for_this_elector could be 0 if elector_weight * alloc_range_size is 0
            # Ensure some spending if budget allows and min_cost is 0 but max_alloc > 0
            if alloc_for_this_elector == 0 and current_candidate_budget > 0 and max_alloc_per_attempt > 0 and min_cost_per_elector == 0:
                alloc_for_this_elector = min(
                    current_candidate_budget,
                    random.uniform(0.01,
                                   max_alloc_per_attempt * elector_weight))

            current_candidate_budget -= alloc_for_this_elector

            base_sus = config.ELECTOR_SUSCEPTIBILITY_BASE + random.uniform(
                -0.2, 0.2)
            if "Easily Influenced" in e_traits:
                base_sus *= config.INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED
            if "Loyal" in e_traits:
                cand_party = cand_data.get('party_id', 'Unknown')
                elector_party = e_prefs.get('party_preference', 'Independent')
                if cand_party != 'Independent' and elector_party != 'Independent' and cand_party != elector_party:
                    base_sus *= config.INFLUENCE_TRAIT_MULTIPLIER_LOYAL

            lit_score = e_prefs.get('media_literacy',
                                    config.MEDIA_LITERACY_RANGE[0])
            min_l, max_l = config.MEDIA_LITERACY_RANGE
            norm_lit = (lit_score - min_l) / (max_l - min_l) if (
                max_l - min_l) > 0 else 0
            lit_reduc = norm_lit * config.MEDIA_LITERACY_EFFECT_FACTOR
            final_sus = max(0.05, min(0.95, base_sus * (1.0 - lit_reduc)))

            base_chance = (cand_med / config.ATTRIBUTE_RANGE[1]) * final_sus
            alloc_success_bonus = 0
            if max_alloc_per_attempt > 0:
                alloc_success_bonus = (
                    alloc_for_this_elector / max_alloc_per_attempt
                ) * config.CAMPAIGN_ALLOCATION_SUCCESS_CHANCE_FACTOR
            final_chance = max(0.05, min(1.0,
                                         base_chance + alloc_success_bonus))

            if random.random() < final_chance:
                successful_influences_this_candidate += 1
                base_inf = config.INFLUENCE_STRENGTH_FACTOR * config.MAX_ELECTOR_LEANING_BASE * random.uniform(
                    0.8, 1.2)
                alloc_inf_bonus = 0
                if max_alloc_per_attempt > 0:
                    alloc_inf_bonus = (
                        alloc_for_this_elector / max_alloc_per_attempt
                    ) * config.CAMPAIGN_ALLOCATION_INFLUENCE_FACTOR
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
                            theme_bonus += config.CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE * norm_w * (
                                1.2 if t in themes else 0.8
                            )  # Boost if current theme
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

                # --- Elector Learning: Campaign Exposure (MODIFIED) ---
                if adj_inf > 0.1:  # Only learn from significant positive influence
                    learning_factor = config.ELECTOR_LEARNING_RATE * \
                        config.CAMPAIGN_EXPOSURE_LEARNING_EFFECT

                    direction = 0.0
                    elector_party_pref = e_prefs.get('party_preference',
                                                     'Independent')
                    candidate_party = cand_data.get('party_id', 'Unknown')

                    if elector_party_pref != "Independent" and candidate_party == elector_party_pref:
                        # Successfully influenced by own party candidate -> reinforce identity focus
                        direction = random.uniform(
                            0.2, 0.7)  # Positive shift towards identity
                    elif candidate_party != elector_party_pref or elector_party_pref == "Independent":
                        # Successfully influenced by other party or is Independent (likely on policy/merit) -> reduce identity focus
                        direction = random.uniform(
                            -0.7, -0.2
                        )  # Negative shift towards identity (i.e. more policy)

                    actual_learning_adjustment = learning_factor * direction

                    current_identity_weight = e_prefs.get(
                        'identity_weight',
                        0.5)  # Default to 0.5 if not present
                    new_identity_weight = current_identity_weight + actual_learning_adjustment

                    # Clamp between 0.05 and 0.95
                    e_prefs['identity_weight'] = max(
                        0.05, min(0.95, new_identity_weight))
                    e_prefs['policy_weight'] = 1.0 - e_prefs['identity_weight']

        # --- Fine ciclo sugli elettori target per questo candidato ---

        # Aggiorna il budget del candidato nella lista originale (candidates_info)
        # e nel dizionario cand_data che potrebbe essere una copia.
        candidates_info[cand_idx]['campaign_budget'] = current_candidate_budget
        cand_data[
            'campaign_budget'] = current_candidate_budget  # Se cand_data è una copia, aggiornala anche

        # Salva i dati aggiornati del candidato (incluso il budget) nel DB
        # Assicurati che cand_data contenga tutti i campi necessari per save_candidate
        # o usa candidates_info[cand_idx]
        db_manager.save_candidate({
            'uuid':
            candidates_info[cand_idx].get('uuid', str(uuid.uuid4(
            ))),  # Usa l'originale per UUID e altri dati non modificati qui
            'name':
            candidates_info[cand_idx]['name'],
            'current_budget':
            current_candidate_budget,
            'gender':
            candidates_info[cand_idx].get('gender', 'Unknown'),
            'age':
            candidates_info[cand_idx].get('age', 0),
            'party_id':
            candidates_info[cand_idx].get('party_id', 'Unknown'),
            'initial_budget':
            candidates_info[cand_idx].get('initial_budget',
                                          config.INITIAL_CAMPAIGN_BUDGET),
            'attributes':
            candidates_info[cand_idx].get('attributes', {}),
            'traits':
            candidates_info[cand_idx].get('traits', []),
            'stats':
            candidates_info[cand_idx].get('stats', {})
        })

        themes_str = ", ".join(
            [t.replace('_', ' ').title() for t in themes
             if t]) if themes else "N/A"
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  Campaign {cand_name} (Themes: {themes_str}): Targeted {electors_targeted_this_candidate} electors ({successful_influences_this_candidate} succ.). Budget left: {current_candidate_budget:.2f}"
        )
    # --- Fine ciclo su candidates_info ---


def simulate_social_influence(network_graph, current_preferences):
    """Simulates social influence using weighted averaging.
       Includes AGENT LEARNING for identity_weight based on social exposure.
    """
    if not config.USE_SOCIAL_NETWORK or network_graph is None:  # pragma: no cover
        return current_preferences

    alpha = config.SOCIAL_INFLUENCE_STRENGTH
    iterations = config.SOCIAL_INFLUENCE_ITERATIONS
    if not current_preferences or alpha <= 0:  # pragma: no cover
        return current_preferences

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulating Social Network Influence ---")

    all_candidate_names = set()
    for e_data_loop in current_preferences.values():
        all_candidate_names.update(e_data_loop.get('leanings', {}).keys())

    if not all_candidate_names:  # pragma: no cover
        return current_preferences

    next_prefs_social = copy.deepcopy(current_preferences)

    for _ in range(iterations):
        if hasattr(
                utils, 'simulation_running_event'
        ) and not utils.simulation_running_event.is_set():  # pragma: no cover
            return next_prefs_social  # Return current state if stopped

        current_iteration_prefs = copy.deepcopy(next_prefs_social)

        for elector_id_social, elector_data_social in current_iteration_prefs.items(
        ):
            if elector_id_social not in network_graph:  # pragma: no cover
                continue

            neighbors_list = list(network_graph.neighbors(elector_id_social))
            num_neighbors = len(neighbors_list)
            elector_leanings_social = elector_data_social.get('leanings', {})

            if num_neighbors > 0:
                avg_neighbor_leanings = {
                    c_name: 0.0
                    for c_name in all_candidate_names
                }
                num_neighbors_with_leaning_for_cand = {
                    c_name: 0
                    for c_name in all_candidate_names
                }

                for neighbor_id in neighbors_list:
                    neighbor_leanings = current_iteration_prefs.get(
                        neighbor_id, {}).get('leanings', {})
                    for c_name_loop in all_candidate_names:
                        if c_name_loop in neighbor_leanings:
                            avg_neighbor_leanings[
                                c_name_loop] += neighbor_leanings[c_name_loop]
                            num_neighbors_with_leaning_for_cand[
                                c_name_loop] += 1

                for c_name_calc in all_candidate_names:
                    if num_neighbors_with_leaning_for_cand[c_name_calc] > 0:
                        avg_neighbor_leanings[
                            c_name_calc] /= num_neighbors_with_leaning_for_cand[
                                c_name_calc]
                    else:  # pragma: no cover
                        avg_neighbor_leanings[
                            c_name_calc] = elector_leanings_social.get(
                                c_name_calc,
                                0)  # Use own if no neighbor has it

                # Update leanings in next_prefs_social
                target_leanings_update = next_prefs_social[
                    elector_id_social].get('leanings', {})
                for c_name_update in all_candidate_names:
                    current_leaning_val = elector_leanings_social.get(
                        c_name_update, 0)
                    avg_neighbor_val = avg_neighbor_leanings[c_name_update]

                    new_leaning = max(0.1, (1 - alpha) * current_leaning_val +
                                      alpha * avg_neighbor_val)
                    target_leanings_update[c_name_update] = new_leaning

                    # --- Elector Learning: Social Influence Exposure (MODIFIED) ---
                    influence_magnitude_val = abs(avg_neighbor_val -
                                                  current_leaning_val)

                    if influence_magnitude_val > config.SOCIAL_INFLUENCE_LEARNING_EFFECT * 0.5:  # Lowered threshold slightly
                        learning_adj_factor = config.ELECTOR_LEARNING_RATE * \
                            config.SOCIAL_INFLUENCE_LEARNING_EFFECT * influence_magnitude_val

                        # Current mechanism: random adjustment, magnitude based on influence strength
                        # This reflects that strong social push can make one re-evaluate, but direction is complex
                        random_direction_factor = random.uniform(
                            -0.5, 0.5)  # Make it less extreme than -1 to 1

                        actual_social_learning_adj = learning_adj_factor * random_direction_factor

                        current_identity_weight_social = next_prefs_social[
                            elector_id_social].get('identity_weight', 0.5)
                        new_identity_weight_social = current_identity_weight_social + \
                            actual_social_learning_adj

                        # Clamp between 0.05 and 0.95
                        next_prefs_social[elector_id_social][
                            'identity_weight'] = max(
                                0.05, min(0.95, new_identity_weight_social))
                        next_prefs_social[elector_id_social][
                            'policy_weight'] = 1.0 - next_prefs_social[
                                elector_id_social]['identity_weight']

                next_prefs_social[elector_id_social][
                    'leanings'] = target_leanings_update

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"Social influence computed ({iterations} iter, strength={alpha:.2f})."
    )
    return next_prefs_social


def verify_election(current_results, num_electors,
                    required_majority_percentage):
    """Verifies if a candidate has been elected."""
    if not current_results or num_electors == 0:  # pragma: no cover
        # Calculate votes_needed even if no results, for GUI display perhaps
        votes_needed = math.ceil(
            num_electors *
            required_majority_percentage) if num_electors > 0 else 1
        return None, votes_needed, 0  # Winner, votes_needed, top_votes

    votes_needed = math.ceil(num_electors * required_majority_percentage)
    # current_results is a Counter
    sorted_res_tuples = current_results.most_common()

    if sorted_res_tuples:
        top_candidate_name, top_candidate_votes = sorted_res_tuples[0]

        if top_candidate_votes >= votes_needed:
            # Check for ties for the first place
            if len(sorted_res_tuples
                   ) > 1 and sorted_res_tuples[1][1] == top_candidate_votes:
                return None, votes_needed, top_candidate_votes  # Tie, no single winner
            else:
                return top_candidate_name, votes_needed, top_candidate_votes  # Winner found
    else:  # No votes cast at all
        return None, votes_needed, 0

    return None, votes_needed, sorted_res_tuples[0][
        1] if sorted_res_tuples else 0  # No winner or no votes


def count_votes(votes_list):
    """Counts votes for each candidate from a list of votes."""
    return Counter(votes_list)
