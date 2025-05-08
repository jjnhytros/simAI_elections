import random
import math
import time
import copy
from collections import Counter
import sys
import threading
import networkx as nx
import uuid  # Import uuid for handling candidate UUIDs
# Imports da altri moduli del progetto (assoluti)
import config
import data
import utils
# Importa le funzioni da voting, inclusa identify_key_electors e execute_voting_round
import voting
import db_manager  # Import the db_manager for potential DB interactions later

# identify_key_electors is now defined in voting.py and imported via 'import voting'
# execute_voting_round is now defined in voting.py and imported via 'import voting'
# Le definizioni di queste funzioni sono state rimosse da questo file.


# Funzione per generare giuramento candidato
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
    if hot and hot in attrs:
        lvl = attrs[hot]
        readable = hot.replace('_', ' ').title()
        if lvl >= 4:
            oath += f" Affronterò con decisione {readable}."
        elif lvl <= 2 and random.random() < 0.5:
            oath += f" Riconosco l'importanza di {readable}."
    return oath


# Funzione per generare eventi casuali
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
        lit_score = e_data.get('media_literacy',
                               config.MEDIA_LITERACY_RANGE[0])
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
        config.CURRENT_HOT_TOPIC = random.choice([
            "administrative_experience", "social_vision", "mediation_ability",
            "ethical_integrity"
        ])
    elif random.random() < 0.05:
        config.CURRENT_HOT_TOPIC = None
    integrity_vals = [
        c['attributes'].get('ethical_integrity', 1) for c in candidates_info
    ]
    max_integ_diff = max(integrity_vals) - min(
        integrity_vals) if integrity_vals and len(integrity_vals) > 1 else 0
    event_types = {  # Probabilità riviste
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
    if not choices:
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "Nessun evento casuale.")
        return
    chosen_event = random.choices(choices, weights=weights, k=1)[0]
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"\n--- Evento Casuale: {chosen_event.replace('_',' ').title()} ---")

    # Apply Event Impact
    if chosen_event == "scandal" and candidates_info:
        # Trova il candidato con l'integrità più bassa (più probabilità) o casuale
        scandalized_cand = min(
            candidates_info,
            key=lambda c: c['attributes'].get('ethical_integrity', 5))
        if random.random() < 0.7:  # Maggiore probabilità per il meno integro
            scandalized_name = scandalized_cand['name']
            scandal_impact = random.uniform(1.0, 3.0) * (
                6 - scandalized_cand['attributes'].get('ethical_integrity', 5)
            )  # Impatto maggiore per bassa integrità
        else:  # Scandal casuale
            scandalized_name = random.choice(candidates_info)['name']
            scandal_impact = random.uniform(1.0, 3.0)

        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 f"  Scandalo su {scandalized_name}!")
        base_neg_impact = -scandal_impact
        for e_id in elector_full_preferences_data:
            apply_event_impact(e_id, scandalized_name, base_neg_impact)

    elif chosen_event == "policy_focus" and candidates_info:
        # Scegli un attributo casuale su cui concentrarsi
        attr_focused = random.choice([
            "administrative_experience", "social_vision", "mediation_ability",
            "ethical_integrity"
        ])
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  Focus su {attr_focused.replace('_',' ').title()}!")
        for e_id in elector_full_preferences_data:
            e_data = elector_full_preferences_data.get(e_id)
            if not e_data:
                continue
            e_ideal_pref = e_data.get(f'preference_{attr_focused}',
                                      config.ELECTOR_IDEAL_PREFERENCE_RANGE[0])
            for cand in candidates_info:
                cand_attr_val = cand['attributes'].get(
                    attr_focused, config.ATTRIBUTE_RANGE[0])
                # L'impatto dipende da quanto il candidato si allinea con la preferenza ideale dell'elettore sull'attributo
                distance = abs(cand_attr_val - e_ideal_pref)
                # Impatto positivo per candidati più allineati, negativo per meno allineati
                # Scaling: distanza 0 -> impatto max, distanza max -> impatto min (o leggermente negativo)
                max_dist = config.ELECTOR_IDEAL_PREFERENCE_RANGE[
                    1] - config.ELECTOR_IDEAL_PREFERENCE_RANGE[0]
                if max_dist == 0:
                    max_dist = 1
                norm_dist = distance / max_dist
                base_impact = random.uniform(
                    0.5, 1.5) * (1.0 - norm_dist * 1.5
                                 )  # Impatto più positivo se norm_dist è basso

                apply_event_impact(e_id, cand['name'], base_impact)

    elif chosen_event == "public_opinion_shift" and candidates_info:
        attr_shifted = random.choice([
            "administrative_experience", "social_vision", "mediation_ability",
            "ethical_integrity"
        ])
        shift_dir = random.choice(
            [-1, 1])  # -1 per shift verso basso, 1 per shift verso alto
        shift_magnitude = random.uniform(0.5, 1.5)
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  Shift d'opinione su {attr_shifted.replace('_',' ').title()} ({'Alto' if shift_dir > 0 else 'Basso'})!"
        )
        for e_id in elector_full_preferences_data:
            e_data = elector_full_preferences_data.get(e_id)
            if not e_data:
                continue
            # L'impatto dipende da quanto il candidato si allinea con la nuova direzione dello shift
            e_current_leanings = e_data.get('leanings', {})
            for cand_name, cand_lean in e_current_leanings.items():
                cand_info = next(
                    (c for c in candidates_info if c['name'] == cand_name),
                    None)
                if not cand_info:
                    continue
                cand_attr_val = cand_info['attributes'].get(
                    attr_shifted, config.ATTRIBUTE_RANGE[0])
                # Impatto positivo se il candidato ha un valore alto nell'attributo e lo shift è verso l'alto, o basso e shift verso il basso
                # Impatto negativo altrimenti
                impact = 0.0
                if shift_dir > 0:  # Shift verso alto
                    impact = (cand_attr_val - config.ATTRIBUTE_RANGE[0]) / (
                        config.ATTRIBUTE_RANGE[1] -
                        config.ATTRIBUTE_RANGE[0]) * shift_magnitude
                else:  # Shift verso basso
                    impact = (config.ATTRIBUTE_RANGE[1] - cand_attr_val) / (
                        config.ATTRIBUTE_RANGE[1] -
                        config.ATTRIBUTE_RANGE[0]) * shift_magnitude
                    impact *= -1  # Impatto negativo per shift verso basso e alto valore attributo, positivo per shift verso basso e basso valore attributo

                apply_event_impact(e_id, cand_name, impact)

    elif chosen_event == "candidate_gaffe" and candidates_info:
        gaffe_name = random.choice(candidates_info)['name']
        gaffe_impact = random.uniform(0.8, 2.0)
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 f"  Gaffe di {gaffe_name}!")
        base_neg_impact = -gaffe_impact
        for e_id in elector_full_preferences_data:
            apply_event_impact(e_id, gaffe_name, base_neg_impact)

    elif chosen_event == "candidate_success" and candidates_info:
        success_name = random.choice(candidates_info)['name']
        success_impact = random.uniform(0.8, 2.0)
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 f"  Successo di {success_name}!")
        for e_id in elector_full_preferences_data:
            impact_adj = success_impact
            apply_event_impact(e_id, success_name, impact_adj)

    elif chosen_event == "ethics_debate" and candidates_info:
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 f"  Dibattito Etico!")
        for e_id in elector_full_preferences_data:
            e_data = elector_full_preferences_data.get(e_id)
            if not e_data:
                continue
            # Impatto basato sull'integrità del candidato
            for cand in candidates_info:
                cand_name = cand['name']
                cand_integrity = cand['attributes'].get(
                    'ethical_integrity', config.ATTRIBUTE_RANGE[0])
                # Impatto positivo per alta integrità, negativo per bassa integrità
                norm_integrity = (cand_integrity - config.ATTRIBUTE_RANGE[0]
                                  ) / (config.ATTRIBUTE_RANGE[1] -
                                       config.ATTRIBUTE_RANGE[0]) if (
                                           config.ATTRIBUTE_RANGE[1] -
                                           config.ATTRIBUTE_RANGE[0]
                ) > 0 else 0.5
                base_impact = (
                    norm_integrity - 0.5
                ) * config.EVENT_ETHICS_DEBATE_IMPACT * 2  # Centra l'impatto intorno allo 0

                apply_event_impact(e_id, cand_name, base_impact)

    elif chosen_event == "endorsement" and candidates_info:
        endorsed_cand = random.choice(candidates_info)
        endorsed_name = endorsed_cand['name']
        endorsement_impact = random.uniform(
            *config.EVENT_ENDORSEMENT_IMPACT_RANGE)
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 f"  Endorsement per {endorsed_name}!")
        for e_id in elector_full_preferences_data:
            impact_adj = endorsement_impact
            apply_event_impact(e_id, endorsed_name, impact_adj)

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "--------------------")


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

    total_campaign_attempts_overall = 0
    successful_impacts_overall = 0
    elector_map = {
        e['id']: e
        for e in electors
    }  # Map elector IDs to their objects
    elector_ids = list(elector_map.keys())  # List of all elector IDs

    # Identify key electors for targeting consideration
    # Need the full elector preferences data and last results
    key_electors_summary = identify_key_electors(elector_full_preferences_data,
                                                 last_round_results)
    key_elector_ids = {ke['id']
                       for ke in key_electors_summary
                       }  # Set of key elector IDs

    # Calculate elector potentials once for this round
    # This potential score can influence both targeting selection and potentially budget allocation per elector
    elector_potentials = {}
    for e_obj in electors:
        e_id = e_obj['id']
        e_prefs = elector_full_preferences_data.get(e_id, {})
        e_traits = e_obj.get('traits', [])

        # Simplified elector potential/susceptibility for targeting:
        elector_potential_score = config.ELECTOR_SUSCEPTIBILITY_BASE  # Base susceptibility
        if "Easily Influenced" in e_traits:
            elector_potential_score *= config.INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED
        if "Loyal" in e_traits:  # Loyal electors might be less susceptible to opposing campaigns
            # This needs candidate context to be truly effective
            # For simplicity, let's just consider if they are loyal in general might affect their *overall* potential to be swayed by *any* campaign
            # A loyal elector might be highly susceptible to *their own party's* campaign but resistant to others.
            # The current potential is a general susceptibility score. Let's keep it that way for now.
            pass  # Loyal trait effect is handled in the influence application based on party match

        # Consider if they are a key elector (swing or easily influenced) - these are often high potential targets
        if e_id in key_elector_ids:
            # TARGETING_KEY_ELECTOR_BONUS_FACTOR is now defined in config.py
            # Bonus for key electors
            elector_potential_score *= config.TARGETING_KEY_ELECTOR_BONUS_FACTOR

        elector_potentials[e_id] = max(0.1, min(
            5.0, elector_potential_score))  # Clamp score

    # Normalize potentials to get weights for budget allocation (higher potential elector gets a higher weight)
    total_potential_sum = sum(
        elector_potentials.values()) if elector_potentials else 1.0
    elector_allocation_weights = {
        e_id: pot / total_potential_sum
        for e_id, pot in elector_potentials.items()
    }

    for cand in candidates_info:
        cand_name = cand['name']
        cand_attrs = cand.get("attributes", {})
        cand_med = cand_attrs.get('mediation_ability',
                                  config.ATTRIBUTE_RANGE[0])
        themes = cand.get('current_campaign_themes',
                          [])  # Use the adapted themes
        budget = cand.get('campaign_budget', 0)
        min_cost_per_elector = config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[0]

        # Determine how many electors this candidate can attempt to target this round
        num_electors_to_target = config.INFLUENCE_ELECTORS_PER_CANDIDATE
        if num_electors_to_target <= 0 or not elector_ids:
            continue

        # Select potential targets based on potential score (higher potential = higher chance of being targeted)
        # Use the calculated elector_potentials for weighted sampling. Sample 'num_electors_to_target' unique electors.
        # Using random.choices with weights and then taking a sample to ensure uniqueness and the correct number.
        if total_potential_sum > 0:
            # Create a list of electors to sample from, weighted by potential
            weighted_elector_list = []
            for e_id, potential in elector_potentials.items():
                # Add elector ID to the list 'potential * 10' times (scaling factor)
                # This creates a list where high-potential electors appear more frequently
                # Need to handle potential = 0 case
                num_add = max(1, int(
                    potential * 10))  # Add at least once, scale by potential
                weighted_elector_list.extend([e_id] * num_add)

            # Sample unique elector IDs from the weighted list
            # Ensure we don't try to sample more unique items than available
            num_to_sample_unique = min(num_electors_to_target,
                                       len(elector_ids))
            if len(weighted_elector_list) >= num_to_sample_unique:
                target_ids = random.sample(weighted_elector_list,
                                           num_to_sample_unique)
                # Ensure uniqueness after sampling - convert to set and back to list
                target_ids = list(set(target_ids))
                # If we still don't have enough after making unique (unlikely if list was large enough), resample randomly
                while len(target_ids) < num_to_sample_unique and len(
                        elector_ids) > len(target_ids):
                    needed_more = num_to_sample_unique - len(target_ids)
                    remaining_elector_ids = [
                        eid for eid in elector_ids if eid not in target_ids
                    ]
                    target_ids.extend(
                        random.sample(
                            remaining_elector_ids,
                            min(needed_more, len(remaining_elector_ids))))
                    target_ids = list(
                        set(target_ids))  # Ensure uniqueness again
            else:  # Fallback to random sampling if no potential sum
                target_ids = random.sample(
                    elector_ids, min(num_electors_to_target, len(elector_ids)))

        else:  # Fallback to random sampling if no potential sum
            target_ids = random.sample(
                elector_ids, min(num_electors_to_target, len(elector_ids)))

        succ_cand = 0  # Successful influences for this candidate in this round
        influenced_cnt = 0  # Number of electors targeted by this candidate in this round

        # Allocate budget strategically among selected targets and simulate influence attempts
        total_budget_spent_this_round = 0
        for e_id in target_ids:
            if budget <= min_cost_per_elector:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"  {cand_name} budget low ({budget:.2f}). Campaign ended early."
                )
                break  # Stop targeting if budget is too low

            influenced_cnt += 1
            # Count total attempts across all candidates and electors
            total_campaign_attempts_overall += 1

            e_info = elector_map.get(e_id)  # Get elector object
            e_prefs = elector_full_preferences_data.get(
                e_id
            )  # Get elector preferences (where leanings and weights are)
            if not e_info or not e_prefs:
                continue  # Skip if elector info or preferences are missing
            e_traits = e_info.get('traits', [])  # Get elector traits

            # Determine budget to allocate to THIS specific elector attempt
            # Allocate more budget to higher potential targets, within the allocation range
            elector_weight = elector_allocation_weights.get(
                e_id,
                0)  # Use the pre-calculated allocation weight for this elector

            # Scale the allocation within the per-attempt range based on elector's allocation weight
            # This makes high-weight electors receive a larger portion of the budget allocated per attempt
            alloc_range_size = config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[
                1] - config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[0]
            alloc = config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[
                0] + elector_weight * alloc_range_size
            alloc = min(
                budget, alloc
            )  # Ensure allocated amount does not exceed remaining budget
            alloc = max(
                min_cost_per_elector, alloc
            ) if budget >= min_cost_per_elector else 0  # Ensure minimum cost if enough budget, else 0

            # If budget > 0 but alloc is 0 (e.g., due to min_cost_per_elector), allocate min cost if possible
            if alloc == 0 and budget > 0:
                alloc = min(budget, min_cost_per_elector
                            ) if budget >= min_cost_per_elector else 0

            # Deduct allocated budget
            budget -= alloc
            total_budget_spent_this_round += alloc

            # Susceptibility (with Media Literacy) - uses the same logic as before
            # Base susceptibility adjusted by traits
            base_sus = config.ELECTOR_SUSCEPTIBILITY_BASE + random.uniform(
                -0.2, 0.2)
            if "Easily Influenced" in e_traits:
                base_sus *= config.INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED

            # Loyal trait effect: harder to sway with campaigns *against* their party
            if "Loyal" in e_traits:
                cand_party = cand.get('party_id', 'Unknown')
                elector_party = e_prefs.get('party_preference', 'Independent')
                # If candidate and elector have different parties (and neither is independent)
                if cand_party != 'Independent' and elector_party != 'Independent' and cand_party != elector_party:
                    # Apply loyal multiplier (less susceptible)
                    base_sus *= config.INFLUENCE_TRAIT_MULTIPLIER_LOYAL

            # Media Literacy effect: reduces susceptibility
            lit_score = e_prefs.get('media_literacy',
                                    config.MEDIA_LITERACY_RANGE[0])
            min_l, max_l = config.MEDIA_LITERACY_RANGE
            norm_lit = (lit_score - min_l) / (max_l - min_l) if (
                max_l - min_l) > 0 else 0
            lit_reduc = norm_lit * config.MEDIA_LITERACY_EFFECT_FACTOR
            final_sus = max(0.05, min(
                0.95, base_sus * (1.0 - lit_reduc)))  # Final susceptibility

            # Success Chance - influenced by candidate's ability, elector's susceptibility, and allocated budget
            base_chance = (cand_med / config.ATTRIBUTE_RANGE[1]) * final_sus
            # Allocation bonus for success chance: spending more increases chance
            alloc_success_bonus = (
                alloc / config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1]
            ) * config.CAMPAIGN_ALLOCATION_SUCCESS_CHANCE_FACTOR  # Scale bonus by proportion of max allocation
            final_chance = max(0.05, min(
                1.0, base_chance + alloc_success_bonus))  # Cap success chance

            # If campaign attempt is successful
            if random.random() < final_chance:
                succ_cand += 1
                # Count total successful impacts across all candidates and electors
                successful_impacts_overall += 1

                # Influence Amount - influenced by base strength, allocated budget, and themes
                base_inf = config.INFLUENCE_STRENGTH_FACTOR * config.MAX_ELECTOR_LEANING_BASE * random.uniform(
                    0.8, 1.2)
                # Allocation bonus for influence strength: spending more increases influence
                alloc_inf_bonus = (
                    alloc / config.CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE[1]
                ) * config.CAMPAIGN_ALLOCATION_INFLUENCE_FACTOR  # Scale bonus by proportion of max allocation
                total_inf = min(base_inf + alloc_inf_bonus,
                                config.MAX_CAMPAIGN_INFLUENCE_PER_ATTEMPT
                                )  # Cap total influence

                # Apply Theme Bonus (more likely for chosen themes)
                theme_bonus = 0.0
                e_weights = e_prefs.get('weights',
                                        {})  # Elector's attribute weights
                if themes and e_weights:
                    for t in themes:
                        w = e_weights.get(t, 0)
                        # If elector cares about the theme (weight > min)
                        if w > config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE[0]:
                            max_w = config.ELECTOR_ATTRIBUTE_WEIGHT_RANGE[1]
                            norm_w = w / max_w if max_w > 0 else 0.5  # Normalize weight
                            # Apply bonus, potentially boosted if it's an adapted theme
                            if t in themes:  # Check if this theme is one of the candidate's CURRENT campaign themes
                                theme_bonus += config.CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE * norm_w * random.uniform(
                                    1.0,
                                    1.5)  # Slightly boosted if adapted theme
                            # Still apply some bonus if elector cares about a theme, even if it's not the candidate's adapted theme (less likely)
                            else:
                                theme_bonus += config.CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE * norm_w * random.uniform(
                                    0.5, 1.0
                                )  # Reduced if not explicitly in adapted themes

                total_inf += theme_bonus  # Add theme bonus to total influence

                # Confirmation Bias - Influences how the elector reacts to the message
                # Adjusts influence based on whether the message aligns with the elector's existing leanings
                conf_mod = 1.0
                if "Confirmation Prone" in e_traits:
                    curr_l = e_prefs.get('leanings', {}).get(
                        cand_name,
                        0)  # Elector's current leaning towards this candidate
                    mid = config.MAX_ELECTOR_LEANING_BASE / 2.0  # Midpoint of leaning scale
                    bias_f = config.CONFIRMATION_BIAS_FACTOR  # Strength of confirmation bias

                    # If elector already leans towards the candidate, influence is amplified
                    if curr_l > mid:
                        conf_mod = bias_f
                    # If elector leans strongly against the candidate, influence is reduced
                    elif curr_l < mid * 0.8:  # Check if leaning is significantly below midpoint
                        conf_mod = 1.0 / bias_f  # Reduce influence

                adj_inf = total_inf * conf_mod  # Apply confirmation bias modifier

                # Apply influence to elector's leaning towards this candidate
                if cand_name in e_prefs['leanings']:
                    e_prefs['leanings'][cand_name] = max(
                        0.1, e_prefs['leanings'][cand_name] +
                        adj_inf)  # Ensure leaning stays above 0.1

                # --- Elector Learning: Campaign Exposure ---
                # Elector learns/adopts the importance of identity vs policy based on successful campaign exposure
                # Successful exposure might strengthen (or randomly weaken) the importance they give to identity vs policy
                learning_adj = config.ELECTOR_LEARNING_RATE * config.CAMPAIGN_EXPOSURE_LEARNING_EFFECT * random.uniform(
                    -0.5, 0.5
                )  # Small random adjustment proportional to learning rate and effect

                # Apply learning adjustment to identity_weight (and update policy_weight)
                e_prefs['identity_weight'] = max(
                    0.1, min(0.9, e_prefs['identity_weight'] + learning_adj
                             ))  # Clamp identity weight between 0.1 and 0.9
                e_prefs['policy_weight'] = 1.0 - e_prefs[
                    'identity_weight']  # Ensure policy weight is complementary

            # else: campaign attempt was not successful, budget is still spent

        # Update candidate's remaining budget after spending on this elector attempt
        # This is done within the loop per elector attempt to accurately reflect spending
        # The total budget update for the candidate object happens after the loop over targets.
        pass  # Budget deduction is already handled above inside the loop

    # Update candidate's remaining budget after spending in this round on all targeted electors
    for c in candidates_info:
        # Find the candidate in the original list (candidates_info) by name
        # This is needed because 'cand' in the loop is a copy, but we need to update
        # the budget in the original list that's passed back and forth.
        # This is inefficient; it would be better to modify the candidate object directly
        # by passing it or its reference to the loop, or operating on a mutable list.
        # Given the current structure, updating by name in the list is necessary.
        # However, 'candidates_info' IS the list being iterated and modified.
        # The 'budget' variable inside the loop holds the updated budget for the current cand.
        # We just need to save this updated budget back to the DB.
        if c['name'] == cand_name:
            # Update the budget in the original list
            c['campaign_budget'] = budget

            # Save updated budget and other relevant candidate info to DB
            db_manager.save_candidate({
                'uuid':
                c.get('uuid', str(uuid.uuid4())),  # Ensure UUID is present
                'name':
                c['name'],
                'current_budget':
                budget,  # Save the updated budget to DB
                # Include other required fields to avoid overwriting with defaults if not fetched
                'gender':
                c.get('gender', 'Unknown'),
                'age':
                c.get('age', 0),
                'party_id':
                c.get('party_id', 'Unknown'),
                'initial_budget':
                c.get('initial_budget', config.INITIAL_CAMPAIGN_BUDGET
                      ),  # Need initial budget in candidate obj or fetch
                'attributes':
                c.get('attributes', {}),
                'traits':
                c.get('traits', []),
                'stats':
                c.get('stats', {})
            })
            break  # Found the candidate, exit inner loop

    # Log campaign summary for the candidate in this round
    themes_str = ", ".join([t.replace('_', ' ').title()
                            for t in themes]) if themes else "N/A"
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"  Campaign {cand_name} (Themes: {themes_str}): Targeted {influenced_cnt} electors ({succ_cand} succ.). Budget left: {budget:.2f}"
    )

    # Summary Log (Optional, if needed to sum up across all campaigning candidates)
    # This summary might not be accurate if not all candidates campaigned.
    # The per-candidate logs above are more informative.
    # If needed, sum up attempts and successes across all campaigning candidates here.
    # For now, let's keep the per-candidate log as primary.
    # if total_campaign_attempts_overall > 0:
    #     utils.send_pygame_update(
    #         utils.UPDATE_TYPE_MESSAGE,
    #         f"  Overall Campaign Summary (This Round): Attempts={total_campaign_attempts_overall}, Successes={successful_impacts_overall}"
    #     )
    # else:
    #     utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
    #                              "  No campaign attempts this round.")


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


# Entry point
# This __main__ block should remain in election.py as it's the primary entry point
if __name__ == "__main__":
    # Ensure DB tables are created when the script starts
    import db_manager
    db_manager.create_tables()
    # Log DB file name
    print(f"Database tables ensured in {config.DATABASE_FILE}")

    # Initialize Pygame and start the GUI thread
    import gui
    gui_thread = threading.Thread(target=gui.main_pygame_gui)
    # Allow the main program to exit even if this thread is running
    gui_thread.daemon = True
    gui_thread.start()

    # The main thread keeps running to keep the GUI alive.
    try:
        while gui_thread.is_alive():
            time.sleep(0.1)  # Sleep briefly
        print("GUI thread finished.")
    except KeyboardInterrupt:
        print("Keyboard interrupt received in main thread.")
        pass
    print("Main thread exiting.")
    sys.exit()
