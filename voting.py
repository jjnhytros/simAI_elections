import random
import math
from collections import Counter
# Imports da altri moduli del progetto (modificati da relativi a assoluti)
import config
import utils


def initialize_citizen_preferences(num_citizens, district_candidates):
    """Assigns random ideal preferences and traits to citizens."""
    preferences = {}
    for i in range(num_citizens):
        citizen_id = f"Citizen_{i+1}"
        # Assegna tratti casuali ai cittadini
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
            assigned_traits  # Aggiungi i tratti
        }
    return preferences


def simulate_citizen_vote(citizen_id, district_candidates_info, citizen_data):
    """Simulates the vote of a single citizen based on attribute preferences and traits."""
    candidates_dict = {c["name"]: c for c in district_candidates_info}
    candidate_names = list(candidates_dict.keys())

    if not candidate_names:
        return None  # No candidates to vote for

    citizen_preferences = {
        k: v
        for k, v in citizen_data.items() if k.startswith("preference_")
    }  # Estrai solo le preferenze
    citizen_traits = citizen_data.get(
        "traits",
        [])  # Ottieni i tratti, default a lista vuota se non presenti

    # Calculate an attraction score for each candidate based on attribute proximity to the citizen's ideals
    attraction_scores = {}
    for candidate_name in candidate_names:
        candidate = candidates_dict[candidate_name]
        experience_distance = abs(
            candidate["attributes"]["administrative_experience"] -
            citizen_preferences["preference_experience"])
        social_vision_distance = abs(
            candidate["attributes"]["social_vision"] -
            citizen_preferences["preference_social_vision"])
        mediation_distance = abs(candidate["attributes"]["mediation_ability"] -
                                 citizen_preferences["preference_mediation"])
        integrity_distance = abs(candidate["attributes"]["ethical_integrity"] -
                                 citizen_preferences["preference_integrity"])

        total_distance = (experience_distance + social_vision_distance +
                          mediation_distance + integrity_distance)

        # Calculate base score
        score = (
            config.MAX_CITIZEN_LEANING_BASE -
            total_distance * config.CITIZEN_ATTRIBUTE_MISMATCH_PENALTY_FACTOR)

        # Apply trait effects to the score
        trait_multiplier = 1.0
        random_bias = random.uniform(-0.5, 0.5)  # Base random bias

        if "Attribute Focused" in citizen_traits:
            trait_multiplier *= config.CITIZEN_TRAIT_MULTIPLIER_ATTRIBUTE_FOCUSED
            random_bias *= 0.5  # Riduci il bias casuale per chi è focalizzato sugli attributi
        if "Random Inclined" in citizen_traits:
            random_bias += random.uniform(
                -config.CITIZEN_TRAIT_RANDOM_INCLINED_BIAS,
                config.CITIZEN_TRAIT_RANDOM_INCLINED_BIAS
            )  # Aggiungi un bias casuale maggiore

        final_score = (score * trait_multiplier) + random_bias

        attraction_scores[candidate_name] = max(
            0.1, final_score)  # Keep minimum score > 0

    # Choose a candidate based on probabilities derived from attraction scores
    candidates_for_choice = list(attraction_scores.keys())
    weights_for_choice = list(attraction_scores.values())

    if not candidates_for_choice or sum(weights_for_choice) == 0:
        # Fallback to random vote among available candidates if weights are problematic or all zero
        if candidate_names:
            return random.choice(candidate_names)
        else:
            return None  # No votable candidates in the district

    choice = random.choices(candidates_for_choice,
                            weights=weights_for_choice,
                            k=1)[0]

    return choice


def initialize_elector_preferences(electors_with_traits,
                                   candidates,
                                   preselected_candidates_info=None):
    """
    Assigns initial preferences (leanings), attribute weights, and traits for each elector towards each candidate,
    based on elector ideal preferences and candidate attributes. Applies boost for pre-selected candidates.
    Returns a dictionary of elector preferences.
    """
    elector_full_preferences_data = {
    }  # Use a local variable to avoid global state modification here

    # Map candidate names to candidate objects for easy attribute access
    candidates_dict = {c["name"]: c for c in candidates}
    # Get names of pre-selected candidates for easy checking
    preselected_candidate_names = ([
        c["name"] for c in preselected_candidates_info
    ] if preselected_candidates_info else [])

    for elector_data in electors_with_traits:
        elector_id = elector_data['id']
        elector_traits = elector_data['traits']

        elector_full_preferences_data[elector_id] = {
            'weights': {},
            'leanings': {},
            'initial_leanings': {},
            'traits': elector_traits
        }
        # Assign random attribute weights to the elector
        elector_full_preferences_data[elector_id]['weights'] = {
            "administrative_experience":
            random.randint(*config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE),
            "social_vision":
            random.randint(*config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE),
            "mediation_ability":
            random.randint(*config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE),
            "ethical_integrity":
            random.randint(*config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE),
        }

        # Assign random ideal attribute preferences to the elector (used for base preference calculation)
        elector_ideal_preferences = {
            "preference_experience":
            random.randint(*config.ELECTOR_IDEAL_PREFERENCE_RANGE),
            "preference_social_vision":
            random.randint(*config.ELECTOR_IDEAL_PREFERENCE_RANGE),
            "preference_mediation":
            random.randint(*config.ELECTOR_IDEAL_PREFERENCE_RANGE),
            "preference_integrity":
            random.randint(*config.ELECTOR_IDEAL_PREFERENCE_RANGE),
        }

        for candidate_name in candidates_dict:
            candidate = candidates_dict[candidate_name]

            # Calculate the "distance" between candidate attributes and elector ideal preferences, using weights
            weighted_distance_sum = 0
            for attr, weight in elector_full_preferences_data[elector_id][
                    'weights'].items():
                ideal_pref_key = f"preference_{attr}"
                if ideal_pref_key in elector_ideal_preferences:
                    distance = abs(candidate["attributes"][attr] -
                                   elector_ideal_preferences[ideal_pref_key])
                    weighted_distance_sum += distance * weight

            # Calculate a base leaning score: higher if weighted distance is lower
            penalty_score = weighted_distance_sum * \
                config.ELECTOR_ATTRIBUTE_MISMATCH_PENALTY_FACTOR
            leaning_base = config.MAX_ELECTOR_LEANING_BASE - penalty_score

            # Apply trait effects to initial leaning calculation for Electors
            trait_leaning_modifier = 1.0
            # Example: Idealistic electors penalize low integrity more
            if "Idealistic" in elector_traits:
                if candidate["attributes"]["ethical_integrity"] <= 2:
                    penalty_score *= config.STRATEGIC_VOTING_TRAIT_PENALTY_IDEALISTIC_INTEGRITY
                # Idealistic might also slightly favor candidates aligned with their top preference attribute

            # Recalculate leaning based on potential adjusted penalty
            leaning_base = config.MAX_ELECTOR_LEANING_BASE - penalty_score

            # Add a small random variance
            initial_leaning = leaning_base + random.uniform(
                -config.ELECTOR_RANDOM_LEANING_VARIANCE,
                config.ELECTOR_RANDOM_LEANING_VARIANCE,
            )

            # Apply boost for pre-selected candidates
            if candidate_name in preselected_candidate_names:
                initial_leaning += config.PRESELECTED_CANDIDATE_BOOST

            # Ensure initial leaning is not negative
            elector_full_preferences_data[elector_id]['leanings'][
                candidate_name] = max(0.1, initial_leaning)
            elector_full_preferences_data[elector_id]['initial_leanings'][
                candidate_name] = elector_full_preferences_data[elector_id][
                    'leanings'][candidate_name]

    return elector_full_preferences_data


def simulate_ai_vote(elector_id,
                     votable_candidates_info,
                     elector_data,
                     last_round_results=None,
                     current_round=0,
                     all_candidates_info=None):
    """Simulates the vote of a single elector based on preferences, potentially strategically."""

    elector_leanings = elector_data.get('leanings', {})
    elector_initial_leanings = elector_data.get('initial_leanings', {})
    elector_traits = elector_data.get('traits', [])

    # Ensure we only consider leanings for candidates that are votable in this specific round
    votable_candidate_names_this_round = [
        c["name"] for c in votable_candidates_info
    ]
    votable_leanings = {
        name: leaning
        for name, leaning in elector_leanings.items()
        if name in votable_candidate_names_this_round
    }

    if not votable_leanings:
        if votable_candidate_names_this_round:
            return random.choice(votable_candidate_names_this_round)
        else:
            return None

    # Determine the most preferred candidate among votable ones based on *current* leanings
    most_preferred_candidate_current = max(votable_leanings,
                                           key=votable_leanings.get)

    # --- Strategic Voting Logic ---
    if current_round >= config.STRATEGIC_VOTING_START_ROUND and last_round_results and all_candidates_info:
        most_preferred_current_votes = last_round_results.get(
            most_preferred_candidate_current, 0)
        total_votes_last_round = sum(last_round_results.values())
        most_preferred_current_vote_share = most_preferred_current_votes / \
            total_votes_last_round if total_votes_last_round > 0 else 0

        is_most_preferred_current_unlikely = most_preferred_current_vote_share < config.UNLIKELY_TO_WIN_THRESHOLD

        strategic_chance_modifier = 1.0
        if "Pragmatic" in elector_traits:
            strategic_chance_modifier *= config.STRATEGIC_VOTING_TRAIT_MULTIPLIER_PRAGMATIC
        if "Idealistic" in elector_traits:
            strategic_chance_modifier *= config.STRATEGIC_VOTING_TRAIT_MULTIPLIER_IDEALISTIC

        if is_most_preferred_current_unlikely:
            if elector_initial_leanings:
                most_disliked_candidate_initial = min(
                    elector_initial_leanings, key=elector_initial_leanings.get)
                most_disliked_initial_leaning = elector_initial_leanings.get(
                    most_disliked_candidate_initial, 0)

                is_most_disliked_strongly = most_disliked_initial_leaning < config.MAX_ELECTOR_LEANING_BASE * \
                    config.STRONGLY_DISLIKED_THRESHOLD_FACTOR

                if is_most_disliked_strongly and most_disliked_candidate_initial in votable_candidate_names_this_round:
                    strategic_candidates = {
                        name: leaning
                        for name, leaning in votable_leanings.items()
                        if name != most_disliked_candidate_initial
                    }

                    if strategic_candidates:
                        strategic_choice = max(strategic_candidates,
                                               key=strategic_candidates.get)

                        most_disliked_votes_last_round = last_round_results.get(
                            most_disliked_candidate_initial, 0)
                        total_votes_last_round_strategic = sum(
                            last_round_results.values())
                        most_disliked_vote_share = most_disliked_votes_last_round / \
                            total_votes_last_round_strategic if total_votes_last_round_strategic > 0 else 0

                        strategic_chance = most_disliked_vote_share * strategic_chance_modifier

                        if random.random() < strategic_chance:
                            return strategic_choice

    # --- Normal Voting (or if strategic conditions not met) ---
    candidates_for_choice = list(votable_leanings.keys())
    weights_for_choice = list(votable_leanings.values())

    if not candidates_for_choice or sum(weights_for_choice) == 0:
        if votable_candidate_names_this_round:
            return random.choice(votable_candidate_names_this_round)
        else:
            return None

    choice = random.choices(candidates_for_choice,
                            weights=weights_for_choice,
                            k=1)[0]

    return choice


def simulate_campaigning(candidates_info, electors,
                         elector_full_preferences_data, last_round_results):
    """Simulates candidates attempting to influence electors between rounds."""
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulating Candidate Campaigning ---")

    candidate_names = [c['name'] for c in candidates_info]
    if not candidate_names or not electors:
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "No candidates or electors for campaigning.")
        return

    total_influence_attempts = 0
    successful_influence_attempts = 0

    elector_data_map = {e_data['id']: e_data for e_data in electors}

    for candidate in candidates_info:  # candidates_info include tutti i candidati Governor, usalo per il budget
        candidate_name = candidate['name']
        candidate_mediation = candidate['attributes']['mediation_ability']
        candidate_themes = candidate.get('current_campaign_themes', [])
        candidate_budget = candidate.get('campaign_budget',
                                         0)  # Ottieni il budget corrente

        # --- Strategia di Targeting Elettori (esistente) ---
        # Questa parte del codice per il targeting è già stata implementata
        # e seleziona gli elettori in base al potenziale di influenza.
        # Non la modifichiamo ora, usiamo i bersagli selezionati.
        elector_targeting_potential = []
        for elector_data in electors:
            elector_id = elector_data['id']
            elector_current_leanings = elector_full_preferences_data.get(
                elector_id, {}).get('leanings', {})
            elector_ideal_preferences = {
                k.replace('preference_', ''): v
                for k, v in elector_full_preferences_data.get(
                    elector_id, {}).items() if k.startswith('preference_')
            }
            elector_traits = elector_data.get('traits', [])
            elector_weights = elector_full_preferences_data.get(
                elector_id, {}).get('weights', {})
            leaning_towards_candidate = elector_current_leanings.get(
                candidate_name, 0)

            potential_score = 0
            susceptibility_trait_factor = 1.0
            if "Easily Influenced" in elector_traits:
                susceptibility_trait_factor *= 2.0
            if "Loyal" in elector_traits:
                susceptibility_trait_factor *= 0.5
            potential_score += susceptibility_trait_factor * config.TARGETING_TRAIT_BASE_SCORE

            optimal_leaning_range = (config.MAX_ELECTOR_LEANING_BASE * 0.25,
                                     config.MAX_ELECTOR_LEANING_BASE * 0.75)
            if optimal_leaning_range[
                    0] <= leaning_towards_candidate <= optimal_leaning_range[1]:
                potential_score += config.TARGETING_OPTIMAL_LEANING_BONUS

            weighted_distance_to_candidate = 0
            if elector_ideal_preferences and elector_weights:
                for attr in candidate['attributes']:
                    ideal_pref_key = f"preference_{attr}"
                    if attr in elector_ideal_preferences and attr in elector_weights:
                        distance = abs(candidate["attributes"][attr] -
                                       elector_ideal_preferences[attr])
                        weighted_distance_sum = weighted_distance_to_candidate  # Corretto nome variabile
                        weighted_distance_sum += distance * elector_weights[
                            attr]  # Somma corretta

            max_possible_weighted_distance = 0
            if elector_weights:
                for attr, weight in elector_weights.items():
                    max_distance_per_attribute = config.ATTRIBUTE_RANGE[
                        1] - config.ATTRIBUTE_RANGE[0]
                    # Corretto nome variabile
                    max_possible_weighted_weighted_distance = max_possible_weighted_distance
                    max_possible_weighted_weighted_distance += max_distance_per_attribute * \
                        weight  # Somma corretta

            alignment_potential_factor = 1.0 - (
                weighted_distance_to_candidate / max_possible_weighted_distance
                if max_possible_weighted_distance > 0 else 0)
            potential_score += alignment_potential_factor * \
                config.TARGETING_ALIGNMENT_BONUS_FACTOR
            elector_targeting_potential.append((elector_id, potential_score))

        elector_targeting_potential.sort(key=lambda item: item[1],
                                         reverse=True)
        electors_to_influence_ids = [
            item[0] for item in
            elector_targeting_potential[:config.
                                        INFLUENCE_ELECTORS_PER_CANDIDATE]
        ]
        # Fine Strategia di Targeting

        successful_influence_attempts_this_candidate = 0  # Contatore per questo candidato
        # Conta quanti elettori sono stati *effettivamente* targettati (e costati budget)
        electors_influenced_count = 0

        # Determina il budget minimo necessario per fare ALMENO un tentativo
        min_allocation_cost = config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[0]

        # --- Esegui la Campagna sui bersagli selezionati, con allocazione budget ---
        for elector_id in electors_to_influence_ids:

            # Verifica se il candidato ha almeno il budget minimo per un tentativo
            if candidate_budget >= min_allocation_cost:

                # --- Strategia di Allocazione Budget per questo tentativo (Semplice) ---
                # Per ora, allocazione casuale tra il minimo e il massimo consentito, limitata dal budget disponibile
                # O un'allocazione strategica potrebbe essere implementata qui (es. allocare di più sui target a più alto potenziale)
                max_possible_allocation = min(
                    candidate_budget,
                    config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1])
                # Assicurati che il range sia valido: min <= max
                if min_allocation_cost > max_possible_allocation:
                    # Questo candidato non può permettersi nemmeno l'allocazione minima
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        f"  {candidate_name} has budget {candidate_budget}, less than min allocation {min_allocation_cost}. Campaign for this round ended."
                    )
                    break  # Esci dal loop degli elettori target per questo candidato

                allocated_budget_for_attempt = random.randint(
                    min_allocation_cost, max_possible_allocation)

                candidate_budget -= allocated_budget_for_attempt  # Scala il budget
                electors_influenced_count += 1  # Incrementa il contatore dei tentativi effettivi

                # ... (codice esistente per calcolare suscettibilità e base success_chance) ...
                elector_data = elector_data_map.get(elector_id)
                if not elector_data:
                    continue

                elector_traits = elector_data.get('traits', [])
                elector_current_leanings = elector_full_preferences_data.get(
                    elector_id, {}).get('leanings', {})
                elector_weights = elector_full_preferences_data.get(
                    elector_id, {}).get('weights', {})

                susceptibility = config.ELECTOR_SUSCEPTIBILITY_BASE + random.uniform(
                    -0.2, 0.2)
                if "Easily Influenced" in elector_traits:
                    susceptibility *= config.INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED
                if "Loyal" in elector_traits:
                    susceptibility *= config.INFLUENCE_TRAIT_MULTIPLIER_LOYAL
                susceptibility = max(0.1, min(0.9, susceptibility))

                # Calcolo della probabilità di successo base (basata su mediazione e suscettibilità)
                base_success_chance = (
                    candidate_mediation /
                    config.ATTRIBUTE_RANGE[1]) * susceptibility

                # --- Bonus Probabilità di Successo basato sul Budget Allocato ---
                # Bonus = (Budget Allocato - Budget Minimo) * Fattore Success Chance
                allocation_bonus_success_chance = (
                    allocated_budget_for_attempt - min_allocation_cost
                ) * config.CAMPAIGN_ALLOCATION_SUCCESS_CHANCE_FACTOR

                final_success_chance = base_success_chance + allocation_bonus_success_chance
                final_success_chance = max(0.05, min(
                    1.0, final_success_chance))  # Clampa la probabilità

                if random.random() < final_success_chance:
                    successful_influence_attempts_this_candidate += 1

                    # Calcolo dell'ammontare di influenza base (basato su fattore base)
                    base_influence_amount = config.INFLUENCE_STRENGTH_FACTOR * config.MAX_ELECTOR_LEANING_BASE * random.uniform(
                        0.8, 1.2)

                    # --- Bonus Ammontare di Influenza basato sul Budget Allocato ---
                    # Bonus = (Budget Allocato - Budget Minimo) * Fattore Influenza
                    allocation_bonus_influence_amount = (
                        allocated_budget_for_attempt - min_allocation_cost
                    ) * config.CAMPAIGN_ALLOCATION_INFLUENCE_FACTOR

                    total_influence_this_attempt = base_influence_amount + \
                        allocation_bonus_influence_amount
                    # Clampa l'influenza massima applicabile per singolo tentativo
                    total_influence_this_attempt = min(
                        total_influence_this_attempt,
                        config.MAX_CAMPAIGN_INFLUENCE_PER_ATTEMPT)

                    theme_influence_bonus = 0
                    if candidate_themes and elector_weights:
                        for theme_attr in candidate_themes:
                            if theme_attr in elector_weights and elector_weights[
                                    theme_attr] > config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE[
                                        0]:
                                theme_influence_bonus += config.CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE * (
                                    elector_weights[theme_attr] /
                                    config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE[1])

                    total_influence_this_attempt += theme_influence_bonus  # Aggiungi il bonus tema

                    original_leaning = elector_full_preferences_data[
                        elector_id]['leanings'][candidate_name]
                    new_leaning = original_leaning + total_influence_this_attempt

                    elector_full_preferences_data[elector_id]['leanings'][
                        candidate_name] = max(0.1, new_leaning)

                # Incrementa i contatori totali solo per i tentativi EFFETTIVI con budget
                total_influence_attempts += 1

            else:
                # Se non c'è budget minimo per un tentativo, interrompi la campagna per questo candidato
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"  {candidate_name} has budget {candidate_budget}, less than min allocation {min_allocation_cost}. Campaign for this round ended."
                )
                break  # Esci dal loop degli elettori target per questo candidato

        # Aggiorna il budget del candidato nell'oggetto candidato originale in candidates_info
        for c in candidates_info:
            if c['name'] == candidate_name:
                c['campaign_budget'] = candidate_budget
                break

        # Output di log per la campagna di questo candidato
        theme_text_display = ", ".join([
            theme.replace('_', ' ').title() for theme in candidate_themes
        ]) if candidate_themes else "Nessun Tema Specifico"
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            # Aggiunto log budget rimanente
            f"  Campagna di {candidate_name} (Temi: {theme_text_display}): {electors_influenced_count} tentativi con budget ({successful_influence_attempts_this_candidate} successi). Budget rimanente: {candidate_budget:.2f}"
        )
        successful_influence_attempts += successful_influence_attempts_this_candidate

    # Output di log riassuntivo
    if total_influence_attempts > 0:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  Riepilogo Campagna Round: Tentativi totali effettivi: {total_influence_attempts}, Influenze riuscite totali: {successful_influence_attempts}"
        )
    else:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "  Nessun tentativo di campagna con budget in questo round.")


def verify_election(current_results, num_electors,
                    required_majority_percentage):
    """
    Verifies if a candidate has been elected based on the required majority percentage.
    Returns the elected candidate's name (or None) and the number of votes needed.
    """
    if not current_results:
        return None, math.ceil(num_electors *
                               required_majority_percentage), math.ceil(
                                   num_electors * required_majority_percentage)

    total_votes = sum(current_results.values())
    votes_needed = math.ceil(num_electors * required_majority_percentage)

    # In modalità runoff, total_votes dovrebbe essere il numero di elettori che hanno votato
    # Consideriamo sempre il numero totale di elettori aventi diritto (config.NUM_GRAND_ELECTORS) per la maggioranza.
    # Per mostrare il numero di voti richiesti basato sul totale degli elettori
    display_votes_needed = votes_needed

    # Ordina i risultati per voti (dal più alto al più basso)
    sorted_results = current_results.most_common()

    if sorted_results:
        top_candidate, top_votes = sorted_results[0]
        if top_votes >= votes_needed:
            # Assicurati che non ci sia un pareggio per la maggioranza (molto improbabile ma teoricamente possibile)
            if len(sorted_results) > 1 and sorted_results[1][1] == top_votes:
                # C'è un pareggio per il primo posto con o sopra la maggioranza richiesta
                return None, votes_needed, display_votes_needed
            else:
                return top_candidate, votes_needed, display_votes_needed

    return None, votes_needed, display_votes_needed  # Nessuno eletto


def count_votes(votes):
    """Counts votes for each candidate."""
    return Counter(votes)
