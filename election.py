import random
import math
import time
import copy
from collections import Counter
import sys
import threading
# Imports da altri moduli del progetto (assoluti)
import config
import data
import utils
import generation
import voting

# Store elector preferences with attribute weights and traits
elector_full_preferences = {}


def generate_candidate_oath(candidate_info):
    """Generates an oath/statement of intent string based on candidate attributes."""
    exp = candidate_info["attributes"]["administrative_experience"]
    soc = candidate_info["attributes"]["social_vision"]
    med = candidate_info["attributes"]["mediation_ability"]
    itg = candidate_info["attributes"]["ethical_integrity"]

    experience_phrase = ""
    if exp <= 2:
        experience_phrase = (
            "a commitment to developing administrative experience")
    elif exp == 3:
        experience_phrase = "solid administrative management"
    else:  # exp >= 4
        experience_phrase = "strong and experienced administrative leadership"

    social_vision_phrase = ""
    if soc <= 2:
        social_vision_phrase = (
            "a pragmatic approach focused on social stability")
    elif soc == 3:
        social_vision_phrase = "a balance between diverse social needs"
    else:  # soc >= 4
        social_vision_phrase = (
            "a progressive social vision attentive to innovation")

    mediation_phrase = ""
    if med <= 2:
        mediation_phrase = "addressing challenges with determination"
    elif med == 3:
        mediation_phrase = "fostering dialogue between parties"
    else:  # med >= 4
        mediation_phrase = "building bridges and actively seeking consensus"

    integrity_phrase = ""
    if itg <= 2:
        integrity_phrase = "with flexibility in interpreting norms"
    elif itg == 3:
        integrity_phrase = "respecting rules and fairness"
    else:  # itg >= 4
        integrity_phrase = "with unwavering integrity and transparency"

    return f"My commitment is based on {experience_phrase} and promoting {social_vision_phrase}. I am ready for {mediation_phrase} and I swear to always act {integrity_phrase}."


# Nuova funzione per generare eventi casuali che influenzano gli elettori
def generate_random_event(candidates_info,
                          elector_full_preferences_data,
                          last_round_results=None):
    """Genera un evento casuale che può influenzare gli orientamenti degli elettori, potenzialmente influenzato dallo stato della simulazione."""

    # --- Analisi dello stato della simulazione (per influenzare la scelta dell'evento e l'impatto) ---
    # Esempio: Calcola la differenza massima nell'attributo integrità tra i candidati
    integrity_values = [
        c['attributes'].get('ethical_integrity', 0) for c in candidates_info
    ]
    max_integrity_diff = max(integrity_values) - min(
        integrity_values) if integrity_values else 0

    # Esempio: Trova il candidato con più voti nell'ultimo round (se disponibile)
    leader_name = None
    leader_votes = -1
    if last_round_results:
        # last_round_results è un Counter, most_common(1) restituisce una lista [(nome, voti)]
        if last_round_results.most_common(1):
            leader_name, leader_votes = last_round_results.most_common(1)[0]

    # --- Determinazione della probabilità degli eventi e della scelta dell'evento ---
    event_types = {
        "scandal": {
            "base_prob":
            0.15,
            "state_factor":
            max_integrity_diff *
            config.EVENT_SCANDAL_PROB_FACTOR_INTEGRITY_DIFF
        },  # Probabilità aumenta con differenza integrità
        "policy_focus": {
            "base_prob": 0.2,
            "state_factor": 0
        },  # Potremmo aggiungere un fattore basato sull'importanza media degli attributi per gli elettori
        "public_opinion_shift": {
            "base_prob": 0.1,
            "state_factor": 0
        },  # Potremmo aggiungere un fattore basato sulla volatilità delle preferenze
        "candidate_gaffe": {
            "base_prob": 0.1,
            "state_factor": 0
        },  # Potremmo aggiungere un fattore basato sulla "personalità" del candidato (se implementata)
        "candidate_success": {
            "base_prob": 0.1,
            "state_factor": 0
        },  # Potremmo aggiungere un fattore basato sulla "abilità" del candidato (se implementata)
        # Aggiungi nuovi tipi di eventi qui
        "ethics_debate": {
            "base_prob":
            0.05,
            "state_factor":
            max_integrity_diff *
            config.EVENT_ETHICS_DEBATE_PROB_FACTOR_INTEGRITY_DIFF
        },  # Più probabile con differenze di integrità
    }

    # Calcola le probabilità effettive e scegli un evento
    total_prob = 0
    event_probabilities = {}
    for event_type, params in event_types.items():
        # Assicurati che state_factor non renda la probabilità negativa
        effective_prob = max(0, params["base_prob"] + params["state_factor"])
        # Limita la probabilità massima per evitare che un singolo fattore la porti a 1.0 o oltre
        effective_prob = min(
            effective_prob,
            0.5)  # Esempio: probabilità massima di un singolo evento 50%
        event_probabilities[event_type] = effective_prob
        total_prob += effective_prob

    # Normalizza le probabilità e scegli l'evento
    if total_prob > 0:
        event_choices = list(event_probabilities.keys())
        event_weights = list(event_probabilities.values())
        chosen_event_type = random.choices(event_choices,
                                           weights=event_weights,
                                           k=1)[0]
    else:
        # Fallback se tutte le probabilità sono zero
        chosen_event_type = random.choice(list(event_types.keys()))
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "Warning: Total event probability is zero, falling back to random event choice."
        )

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Evento Casuale ---")
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"Tipo di evento scelto: {chosen_event_type}")

    # --- Applica impatto in base al tipo di evento e allo stato ---
    if chosen_event_type == "scandal":
        if candidates_info:
            # Un candidato con bassa integrità potrebbe avere più probabilità di essere colpito dallo scandalo
            candidates_by_integrity = sorted(
                candidates_info,
                key=lambda c: c['attributes'].get('ethical_integrity', 0))
            # Scegli un candidato con probabilità inversamente proporzionale all'integrità
            scandal_candidates_choices = [
                c['name'] for c in candidates_by_integrity
            ]
            # Pesi inversi: candidati con integrità 1 hanno peso N, 5 hanno peso 1
            scandal_candidates_weights = [
                config.ATTRIBUTE_RANGE[1] -
                c['attributes'].get('ethical_integrity', 0) + 1
                for c in candidates_by_integrity
            ]

            if sum(scandal_candidates_weights) > 0:
                scandalized_candidate_name = random.choices(
                    scandal_candidates_choices,
                    weights=scandal_candidates_weights,
                    k=1)[0]
                scandalized_candidate = next(
                    (c for c in candidates_info
                     if c['name'] == scandalized_candidate_name), None)

                if scandalized_candidate:
                    # L'impatto dello scandalo potrebbe essere maggiore se l'integrità del candidato è bassa
                    integrity_level = scandalized_candidate['attributes'].get(
                        'ethical_integrity', config.ATTRIBUTE_RANGE[1])
                    scandal_impact = random.uniform(
                        0.1, 0.5) * config.MAX_ELECTOR_LEANING_BASE * (
                            1.0 +
                            (config.ATTRIBUTE_RANGE[1] - integrity_level) /
                            config.ATTRIBUTE_RANGE[1] * 0.5
                    )  # Impatto aumenta se integrità bassa

                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        f"Evento: Scandalo colpisce {scandalized_candidate['name']}! Gli orientamenti degli elettori verso questo candidato potrebbero diminuire."
                    )
                    # Applica impatto negativo a tutti gli orientamenti degli elettori per questo candidato
                    for elector_id in elector_full_preferences_data:
                        if scandalized_candidate[
                                'name'] in elector_full_preferences_data[
                                    elector_id].get('leanings', {}):
                            elector_full_preferences_data[elector_id][
                                'leanings'][scandalized_candidate[
                                    'name']] -= scandal_impact
                            elector_full_preferences_data[elector_id][
                                'leanings'][
                                    scandalized_candidate['name']] = max(
                                        0.1, elector_full_preferences_data[
                                            elector_id]['leanings'][
                                                scandalized_candidate['name']])

    elif chosen_event_type == "policy_focus":
        if candidates_info:
            attribute_focused = random.choice(
                list(candidates_info[0]['attributes'].keys()))
            focus_impact = random.uniform(
                0.05, 0.2) * config.MAX_ELECTOR_LEANING_BASE
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Evento: L'attenzione pubblica si sposta su {attribute_focused.replace('_', ' ').title()}! Gli elettori potrebbero favorire i candidati forti in quest'area."
            )
            # Applica impatto positivo agli orientamenti degli elettori in base al livello dell'attributo del candidato
            for elector_id in elector_full_preferences_data:
                for candidate in candidates_info:
                    candidate_name = candidate['name']
                    attribute_level = candidate['attributes'].get(
                        attribute_focused, 0)
                    if attribute_level > config.ATTRIBUTE_RANGE[
                            1] / 2:  # Beneficia solo i candidati forti in questo attributo
                        if candidate_name in elector_full_preferences_data[
                                elector_id].get('leanings', {}):
                            adjustment = focus_impact * (
                                attribute_level / config.ATTRIBUTE_RANGE[1]
                            )  # Impatto maggiore per attributo più alto
                            elector_full_preferences_data[elector_id][
                                'leanings'][candidate_name] += adjustment
                            elector_full_preferences_data[elector_id][
                                'leanings'][candidate_name] = max(
                                    0.1,
                                    elector_full_preferences_data[elector_id]
                                    ['leanings'][candidate_name])

    elif chosen_event_type == "public_opinion_shift":
        if candidates_info:
            attribute_shifted = random.choice(
                list(candidates_info[0]['attributes'].keys()))
            shift_direction = random.choice(
                [-1, 1])  # -1 per spostamento negativo, 1 per positivo
            shift_amount = random.uniform(
                0.05, 0.15) * config.MAX_ELECTOR_LEANING_BASE
            direction_text = "favorendo" if shift_direction == 1 else "sfavorendo"
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Evento: L'opinione pubblica si sposta {direction_text} i candidati con alto {attribute_shifted.replace('_', ' ').title()}!"
            )
            # Applica spostamento agli orientamenti degli elettori in base al livello dell'attributo del candidato e alla direzione dello spostamento
            for elector_id in elector_full_preferences_data:
                for candidate in candidates_info:
                    candidate_name = candidate['name']
                    attribute_level = candidate['attributes'].get(
                        attribute_shifted, 0)
                    if candidate_name in elector_full_preferences_data[
                            elector_id].get('leanings', {}):
                        # Lo spostamento è proporzionale al livello dell'attributo e alla direzione
                        adjustment = shift_direction * shift_amount * (
                            attribute_level / config.ATTRIBUTE_RANGE[1])
                        elector_full_preferences_data[elector_id]['leanings'][
                            candidate_name] += adjustment
                        elector_full_preferences_data[elector_id]['leanings'][
                            candidate_name] = max(
                                0.1, elector_full_preferences_data[elector_id]
                                ['leanings'][candidate_name])

    elif chosen_event_type == "candidate_gaffe":
        if candidates_info:
            # Un candidato con bassa mediazione o integrità potrebbe avere più probabilità di fare una gaffe
            candidates_by_gaffe_risk = sorted(
                candidates_info,
                key=lambda c:
                (c['attributes'].get('mediation_ability', config.
                                     ATTRIBUTE_RANGE[1]) + c['attributes'].
                 get('ethical_integrity', config.ATTRIBUTE_RANGE[1]
                     )))  # Rischio minore se alta mediazione/integrità
            # Scegli un candidato con probabilità inversamente proporzionale alla mediazione/integrità
            gaffe_candidates_choices = [
                c['name'] for c in candidates_by_gaffe_risk
            ]
            # Pesi inversi: rischio alto (es. mediazione/integrità basse) hanno peso maggiore
            gaffe_candidates_weights = [
                (config.ATTRIBUTE_RANGE[1] -
                 c['attributes'].get('mediation_ability', 0)) +
                (config.ATTRIBUTE_RANGE[1] -
                 c['attributes'].get('ethical_integrity', 0)) + 1
                for c in candidates_by_gaffe_risk
            ]

            if sum(gaffe_candidates_weights) > 0:
                gaffe_candidate_name = random.choices(
                    gaffe_candidates_choices,
                    weights=gaffe_candidates_weights,
                    k=1)[0]
                gaffe_candidate = next((c for c in candidates_info
                                        if c['name'] == gaffe_candidate_name),
                                       None)

                if gaffe_candidate:
                    gaffe_impact = random.uniform(
                        0.05, 0.2) * config.MAX_ELECTOR_LEANING_BASE
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        f"Evento: {gaffe_candidate['name']} fa una gaffe pubblica. Impatto negativo minore."
                    )
                    for elector_id in elector_full_preferences_data:
                        if gaffe_candidate[
                                'name'] in elector_full_preferences_data[
                                    elector_id].get('leanings', {}):
                            elector_full_preferences_data[elector_id][
                                'leanings'][
                                    gaffe_candidate['name']] -= gaffe_impact
                            elector_full_preferences_data[elector_id][
                                'leanings'][gaffe_candidate['name']] = max(
                                    0.1,
                                    elector_full_preferences_data[elector_id]
                                    ['leanings'][gaffe_candidate['name']])

    elif chosen_event_type == "candidate_success":
        if candidates_info:
            # Un candidato con alta esperienza o visione sociale potrebbe avere più probabilità di un successo (es. annuncio politico positivo)
            candidates_by_success_potential = sorted(
                candidates_info,
                key=lambda c:
                (c['attributes'].get('administrative_experience', 0) + c[
                    'attributes'].get('social_vision', 0)),
                reverse=True
            )  # Potenziale maggiore se alta esperienza/visione sociale
            # Scegli un candidato con probabilità proporzionale all'esperienza/visione sociale
            success_candidates_choices = [
                c['name'] for c in candidates_by_success_potential
            ]
            success_candidates_weights = [
                c['attributes'].get('administrative_experience', 0) +
                c['attributes'].get('social_vision', 0) + 1
                for c in candidates_by_success_potential
            ]

            if sum(success_candidates_weights) > 0:
                success_candidate_name = random.choices(
                    success_candidates_choices,
                    weights=success_candidates_weights,
                    k=1)[0]
                success_candidate = next(
                    (c for c in candidates_info
                     if c['name'] == success_candidate_name), None)

                if success_candidate:
                    success_impact = random.uniform(
                        0.05, 0.2) * config.MAX_ELECTOR_LEANING_BASE
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        f"Evento: {success_candidate['name']} ottiene un successo pubblico. Impatto positivo minore."
                    )
                    for elector_id in elector_full_preferences_data:
                        if success_candidate[
                                'name'] in elector_full_preferences_data[
                                    elector_id].get('leanings', {}):
                            elector_full_preferences_data[elector_id][
                                'leanings'][success_candidate[
                                    'name']] += success_impact
                            elector_full_preferences_data[elector_id][
                                'leanings'][candidate_name] = max(
                                    0.1,
                                    elector_full_preferences_data[elector_id]
                                    ['leanings'][candidate_name])

    elif chosen_event_type == "ethics_debate":
        # Esempio di nuovo tipo di evento influenzato dallo stato
        if candidates_info:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                "Evento: Si accende il dibattito sull'etica! Gli elettori porgono maggiore attenzione all'integrità dei candidati."
            )
            # Questo evento potrebbe temporaneamente aumentare il peso dell'attributo "ethical_integrity" per tutti gli elettori per questo round
            # Oppure influenzare gli orientamenti in base alla distanza dall'ideale di integrità dell'elettore per TUTTI i candidati

            # Approccio 1 (semplice): Modifica temporanea degli orientamenti basata sull'integrità
            for elector_id in elector_full_preferences_data:
                elector_ideal_integrity = elector_full_preferences_data[
                    elector_id].get('preference_integrity',
                                    config.ELECTOR_IDEAL_PREFERENCE_RANGE[0])
                for candidate in candidates_info:
                    candidate_name = candidate['name']
                    candidate_integrity = candidate['attributes'].get(
                        'ethical_integrity', config.ATTRIBUTE_RANGE[0])

                    # Calcola la "vicinanza" (inverso della distanza) all'ideale di integrità dell'elettore
                    integrity_proximity = config.ATTRIBUTE_RANGE[1] - abs(
                        candidate_integrity - elector_ideal_integrity)
                    # Normalizza la vicinanza (0-1)
                    max_possible_distance = config.ATTRIBUTE_RANGE[
                        1] - config.ATTRIBUTE_RANGE[0]
                    normalized_proximity = integrity_proximity / \
                        max_possible_distance if max_possible_distance > 0 else 0

                    # Applica un bonus o malus all'orientamento in base alla vicinanza all'ideale di integrità
                    # Maggiore vicinanza all'ideale di integrità dell'elettore = bonus maggiore
                    # L'intensità dell'impatto può essere configurabile
                    impact_amount = (
                        normalized_proximity - 0.5
                    ) * config.EVENT_ETHICS_DEBATE_IMPACT * config.MAX_ELECTOR_LEANING_BASE  # Impatto positivo se sopra la media, negativo se sotto

                    if candidate_name in elector_full_preferences_data[
                            elector_id].get('leanings', {}):
                        elector_full_preferences_data[elector_id]['leanings'][
                            candidate_name] += impact_amount
                        elector_full_preferences_data[elector_id]['leanings'][
                            candidate_name] = max(
                                0.1, elector_full_preferences_data[elector_id]
                                ['leanings'][candidate_name])

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "--------------------")


# Nuova funzione per simulare la campagna distrettuale
def simulate_district_campaigning(district_candidates_info, citizen_data):
    """Simula le campagne dei candidati distrettuali influenzando le preferenze dei cittadini."""
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "\n--- Simulazione Campagna Distrettuale ---")

    if not district_candidates_info or not citizen_data:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "Nessun candidato o cittadino per la campagna distrettuale.")
        return

    total_campaign_attempts = 0
    successful_campaign_impacts = 0

    citizen_ids = list(citizen_data.keys())

    for candidate in district_candidates_info:
        candidate_name = candidate['name']
        candidate_attributes = candidate['attributes']
        # Assumi un attributo che rappresenta l'abilità di campagna, es. una combinazione di mediation e social_vision
        campaign_ability = (candidate_attributes.get('mediation_ability', 0) +
                            candidate_attributes.get('social_vision', 0)) / 2.0

        # Ogni candidato cerca di influenzare un certo numero di cittadini
        num_citizens_to_influence = min(
            config.INFLUENCE_CITIZENS_PER_CANDIDATE, len(citizen_ids))
        citizens_to_target_ids = random.sample(citizen_ids,
                                               num_citizens_to_influence)

        for citizen_id in citizens_to_target_ids:
            total_campaign_attempts += 1
            citizen_info = citizen_data[citizen_id]
            citizen_traits = citizen_info.get('traits', [])

            # Determinare la suscettibilità del cittadino alla campagna
            susceptibility = config.CITIZEN_SUSCEPTIBILITY_BASE + random.uniform(
                -0.1, 0.1)
            if "Random Inclined" in citizen_traits:  # I random inclined sono più influenzabili
                susceptibility *= config.CITIZEN_TRAIT_MULTIPLIER_RANDOM_INCLINED
            # I focalizzati sugli attributi sono meno influenzabili dalla campagna generica
            if "Attribute Focused" in citizen_traits:
                # Usa un moltiplicatore diverso o inverti
                susceptibility *= config.CITIZEN_TRAIT_MULTIPLIER_ATTRIBUTE_FOCUSED

            susceptibility = max(0.1, min(
                1.0, susceptibility))  # Clampa la suscettibilità

            # La probabilità di successo dipende dall'abilità di campagna del candidato e dalla suscettibilità del cittadino
            success_chance = (
                campaign_ability / config.ATTRIBUTE_RANGE[1]
            ) * susceptibility  # Normalizza per il range attributi

            if random.random() < success_chance:
                successful_campaign_impacts += 1
                # Quanto viene modificata la preferenza del cittadino
                influence_strength = config.CAMPAIGN_INFLUENCE_STRENGTH_CITIZEN * random.uniform(
                    0.8, 1.2)

                # Modifica le preferenze ideali del cittadino per avvicinarle agli attributi del candidato
                for attr in candidate_attributes:
                    pref_key = f"preference_{attr}"
                    if pref_key in citizen_info:
                        # Sposta la preferenza del cittadino verso l'attributo del candidato
                        current_pref = citizen_info[pref_key]
                        candidate_attr_value = candidate_attributes[attr]

                        # La modifica è proporzionale alla differenza e alla forza dell'influenza
                        adjustment = (candidate_attr_value -
                                      current_pref) * influence_strength
                        citizen_info[pref_key] += adjustment

                        # Clampa la preferenza all'interno del range valido
                        citizen_info[pref_key] = max(
                            config.CITIZEN_IDEAL_PREFERENCE_RANGE[0],
                            min(config.CITIZEN_IDEAL_PREFERENCE_RANGE[1],
                                citizen_info[pref_key]))

        # Output di log per la campagna
        # if total_influence_attempts > 0: # Questo log era per il totale per candidato
        #     theme_text = f"Temi: {', '.join(candidate_themes)}" if candidate_themes else "Nessun Tema Specifico"
        #     utils.send_pygame_update(
        #         utils.UPDATE_TYPE_MESSAGE,
        #         f"  Campagna di {candidate_name} ({theme_text}): Tentativi su {len(electors_to_influence_ids)} elettori target ({successful_influence_attempts} successi)."
        #     )
        # else:
        #      utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
        #                          f"  Campagna di {candidate_name}: Nessun elettore target selezionato.")

    # Output di log riassuntivo per la campagna distrettuale in questo distretto
    # utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"  Riepilogo Campagna Distrettuale: Tentativi totali: {total_campaign_attempts}, Impatti riusciti: {successful_campaign_impacts}")


# Aggiunti parametri continue_event, running_event, step_by_step_mode
def execute_district_election(district_id,
                              winners_to_elect,
                              continue_event=None,
                              running_event=None,
                              step_by_step_mode=False):
    """Simulates the election in a single district, electing a specified number of winners."""
    # Attendi qui se in modalità passo-passo
    if continue_event and step_by_step_mode:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_STATUS,
            {
                "phase": "District Election",
                "round": district_id,
                "status":
                # Stato di attesa
                f"District {district_id} - Waiting for Next Round",
            },
        )
        continue_event.wait()  # Aspetta il segnale dalla GUI
        continue_event.clear(
        )  # Una volta ripartito, pulisci l'evento per il prossimo round

    # Controlla se Pygame è ancora attivo prima di procedere dopo l'attesa
    try:
        import pygame
        if not pygame.display.get_init():
            # Clear running event if Pygame quits unexpectedly
            if running_event:
                running_event.clear()
            return  # Esci dalla funzione
    except ImportError:
        pass

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"\n--- District {district_id} Election ---")
    utils.send_pygame_update(
        utils.UPDATE_TYPE_STATUS,
        {
            "attempt":
            None,  # Non abbiamo un attempt number significativo per i distretti in questa fase
            "phase": "District Elections",
            "round": district_id,
            "status":
            f"District {district_id} Voting",  # Stato di votazione effettivo
        },
    )

    # 1. Generate candidates for the district
    district_candidates_info = generation.generate_candidates(
        config.CANDIDATES_PER_DISTRICT,
        data.MALE_FIRST_NAMES + data.FEMALE_FIRST_NAMES,
        data.SURNAMES,
    )
    district_candidate_names = [c["name"] for c in district_candidates_info]

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"  Number of candidates in the district: {len(district_candidates_info)}",
    )

    # 2. Initialize citizen preferences (now includes traits)
    citizen_data = voting.initialize_citizen_preferences(
        config.CITIZENS_PER_DISTRICT, district_candidates_info)

    # --- Fase di Campagna Distrettuale ---
    simulate_district_campaigning(district_candidates_info, citizen_data)

    # 3. Simulates citizen votes, passing complete citizen data
    district_votes = []
    for citizen_id, citizen_info in citizen_data.items():
        vote = voting.simulate_citizen_vote(
            citizen_id,
            district_candidates_info,
            citizen_info,
        )
        if vote is not None:
            district_votes.append(vote)

    # 4. Count votes
    district_vote_results = voting.count_votes(district_votes)

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "  District Vote Results:")
    if not district_vote_results:
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "    No valid votes cast in this district.")
        district_winners_info = []
    else:
        # 5. Select district winners based on the number to elect for this process attempt
        if winners_to_elect <= 0:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"    This district needs to elect {winners_to_elect} candidate(s). Electing 0.",
            )
            district_winners_names = []
        else:
            actual_winners_to_elect = min(winners_to_elect,
                                          len(district_vote_results))
            if actual_winners_to_elect < winners_to_elect:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"    Warning: Only {actual_winners_to_elect} candidate(s) received votes, need to elect {winners_to_elect}. Electing {actual_winners_to_elect}.",
                )

            district_winners_names = [
                c[0] for c in district_vote_results.most_common(
                    actual_winners_to_elect)
            ]

        # Retrieve complete information of winning candidates
        district_winners_info = [
            c for c in district_candidates_info
            if c["name"] in district_winners_names
        ]

        # Send results and elected status as part of the results update
        district_results_data = []
        district_candidates_dict = {
            c["name"]: c
            for c in district_candidates_info
        }

        for candidate_name, votes in district_vote_results.most_common():
            is_elected = candidate_name in district_winners_names
            sprite_key = district_candidates_dict.get(candidate_name, {}).get(
                'sprite_key', None)
            # Non includiamo attributi qui per brevità nella visualizzazione distrettuale
            # attributi = district_candidates_dict.get(candidate_name, {}).get('attributes', {})

            district_results_data.append({
                "name": candidate_name,
                "votes": votes,
                "elected": is_elected,
                "sprite_key": sprite_key
            })
        utils.send_pygame_update(
            utils.UPDATE_TYPE_RESULTS,
            {
                "type": "district",
                "results": district_results_data
            },
        )

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"  District Winners (become Grand Electors): {[w['name'] for w in district_winners_info]}",
    )
    # time.sleep(config.DISTRICT_PAUSE_SECONDS * 5) # Rimosso, attesa gestita dall'evento

    return district_winners_info


# Aggiunti parametri continue_event, running_event, step_by_step_mode
def execute_voting_round(
    current_voting_electors_ids,
    votable_candidates_info,
    elector_full_preferences_data,
    last_round_results=None,
    num_electors_percentage_base=0,
    required_majority_percentage=config.REQUIRED_MAJORITY,
    current_round=0,
    all_candidates_info=None,
    runoff_carryover_winner_name=None,
    continue_event=None,  # Aggiunto parametro evento
    running_event=None,  # Aggiunto parametro evento
    step_by_step_mode=False  # Aggiunto parametro modalità
):
    """
    Executes a single AI voting round for all active electors in the College.
    Updates elector preferences based on the last round's results and campaigns.
    Returns the elected governor (or None), the round results, and the potentially updated preferences.
    """
    # Attendi qui se in modalità passo-passo
    if continue_event and step_by_step_mode:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_STATUS,
            {
                "phase": "College Election",
                "round": current_round,
                "status": "Waiting for Next Round",  # Stato di attesa
            },
        )
        continue_event.wait()  # Aspetta il segnale dalla GUI
        continue_event.clear(
        )  # Una volta ripartito, pulisci l'evento per il prossimo round

    # Controlla se Pygame è ancora attivo prima di procedere dopo l'attesa
    try:
        import pygame
        if not pygame.display.get_init():
            # Clear running event if Pygame quits unexpectedly
            if running_event:
                running_event.clear()
            return (None, {}, elector_full_preferences_data, 0
                    )  # Esci dalla funzione e restituisci valori di default
    except ImportError:
        pass

    utils.send_pygame_update(
        utils.UPDATE_TYPE_STATUS,
        {
            "attempt": None,  # L'attempt number viene gestito nel loop esterno
            "phase": "College Election",
            "round": current_round,
            "status": "Voting...",  # Stato di votazione effettivo
        },
    )

    round_votes = []

    # Apply momentum to preferences based on the last round BEFORE electors vote in this round
    if last_round_results and num_electors_percentage_base > 0:
        initial_candidate_names_from_pref = []
        if elector_full_preferences_data and list(
                elector_full_preferences_data.values()):
            initial_candidate_names_from_pref = list(
                list(elector_full_preferences_data.values())[0].get(
                    'leanings', {}).keys())

        if (initial_candidate_names_from_pref
                and num_electors_percentage_base > 0):
            average_expected_percentage = 1 / len(
                initial_candidate_names_from_pref)
            for elector_id in elector_full_preferences_data:
                elector_data = elector_full_preferences_data.get(
                    elector_id, {})
                elector_leanings = elector_data.get('leanings', {})
                elector_traits = elector_data.get('traits', [])

                momentum_modifier = 1.0
                if "Swing Voter" in elector_traits:
                    momentum_modifier *= 1.5
                if "Loyal" in elector_traits:
                    momentum_modifier *= 0.5

                for candidate_name in initial_candidate_names_from_pref:
                    vote_percentage = (
                        last_round_results.get(candidate_name, 0) /
                        num_electors_percentage_base)

                    adjustment = (
                        (vote_percentage - average_expected_percentage) *
                        config.ELECTOR_MOMENTUM_FACTOR *
                        config.MAX_ELECTOR_LEANING_BASE * momentum_modifier)
                    if candidate_name in elector_leanings:
                        elector_leanings[candidate_name] += adjustment
                        elector_leanings[candidate_name] = max(
                            0.1, elector_leanings[candidate_name])
                elector_full_preferences_data[elector_id][
                    'leanings'] = elector_leanings

    # --- Apply Runoff Carryover Bonus in the FIRST round if applicable ---
    if current_round == 1 and runoff_carryover_winner_name is not None and elector_full_preferences_data:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"\nApplying +2 vote equivalent bonus to {runoff_carryover_winner_name}'s leanings for this first round (carried over from runoff deadlock)."
        )
        for elector_id in elector_full_preferences_data:
            if runoff_carryover_winner_name in elector_full_preferences_data[
                    elector_id].get('leanings', {}):
                original_leaning = elector_full_preferences_data[elector_id][
                    'leanings'][runoff_carryover_winner_name]
                elector_full_preferences_data[elector_id]['leanings'][
                    runoff_carryover_winner_name] += config.RUNOFF_CARRYOVER_LEANING_BONUS
                elector_full_preferences_data[elector_id]['leanings'][
                    runoff_carryover_winner_name] = max(
                        0.1, elector_full_preferences_data[elector_id]
                        ['leanings'][runoff_carryover_winner_name])

    # Now, each elector participating in this round votes using their updated preferences
    for elector_id in current_voting_electors_ids:
        vote = voting.simulate_ai_vote(
            elector_id, votable_candidates_info,
            elector_full_preferences_data.get(elector_id, {}),
            last_round_results, current_round, all_candidates_info)

        if vote is not None:
            round_votes.append(vote)

    current_results = voting.count_votes(round_votes)

    governor_elected, votes_needed, display_votes_needed = voting.verify_election(
        current_results, config.NUM_GRAND_ELECTORS,
        required_majority_percentage)

    return governor_elected, current_results, elector_full_preferences_data, votes_needed


def run_election_simulation(
        election_attempt=1,
        preselected_candidates_info=None,
        runoff_carryover_winner_name=None,
        continue_event=None,
        running_event=None,
        step_by_step_mode=False  # Aggiunto parametro modalità
):
    """Runs the entire electoral process simulation."""
    global elector_full_preferences

    if running_event:
        running_event.set()

    try:
        import pygame
        if not pygame.display.get_init():
            if running_event:
                running_event.clear()
            return
    except ImportError:
        pass

    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"\n{'='*50}")
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"--- Starting Complete Anthalys Electoral Process (Attempt {election_attempt}/{config.MAX_ELECTION_ATTEMPTS}) ---",
    )
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"{'='*50}")
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "Initial Situation: Governor position vacant.")
    utils.send_pygame_update(
        utils.UPDATE_TYPE_STATUS,
        {
            "attempt": election_attempt,
            "phase": "Initialization",
            "round": 0,
            "status": "Starting",
        },
    )

    # In modalità continua, l'evento deve essere settato all'inizio
    # In modalità passo passo, l'evento sarà settato solo al click del pulsante
    # Quindi, se non siamo in modalità passo passo, settiamo l'evento qui per farlo partire
    if not step_by_step_mode:
        if continue_event:
            continue_event.set()

    governor_candidates_info = []
    district_elected_candidates_info = []

    # --- Determine Candidates for Phase 2 ---
    num_preselected = (len(preselected_candidates_info)
                       if preselected_candidates_info else 0)

    if num_preselected > 0:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"\nProcess Restart: {num_preselected} candidate(s) pre-selected from previous attempt's final round.",
        )
        governor_candidates_info.extend(preselected_candidates_info)

        num_district_winners_needed = config.NUM_GRAND_ELECTORS - num_preselected

        if num_district_winners_needed < 0:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_ERROR,
                f"Configuration Error: Cannot elect a negative number of candidates from districts ({num_district_winners_needed}). NUM_PRESELECTED_CANDIDATES ({num_preselected}) > NUM_GRAND_ELECTORS ({config.NUM_GRAND_ELECTORS})."
            )
            utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE,
                                     {"elected": False})
            if running_event:
                running_event.clear()
            return

        winners_per_district_base = num_district_winners_needed // config.NUM_DISTRICTS
        districts_electing_one_more = num_district_winners_needed % config.NUM_DISTRICTS

        if num_district_winners_needed > 0:
            if districts_electing_one_more > 0:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"Due to carrying over {num_preselected} candidates, {districts_electing_one_more} districts will elect {winners_per_district_base + 1} candidate(s), and the remaining {config.NUM_DISTRICTS - districts_electing_one_more} districts will elect {winners_per_district_base} candidate(s).",
                )
            else:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"Each district will elect {winners_per_district_base} candidate(s) to fill the remaining {num_district_winners_needed} spots.",
                )
        else:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                "Phase 1 (District Elections) skipped as all candidates are pre-selected."
            )

    else:
        num_district_winners_needed = config.NUM_GRAND_ELECTORS
        winners_per_district_base = config.NUM_GRAND_ELECTORS // config.NUM_DISTRICTS
        districts_electing_one_more = config.NUM_GRAND_ELECTORS % config.NUM_DISTRICTS

        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"\nFirst attempt: All {config.NUM_GRAND_ELECTORS} candidates come from district elections.",
        )
        if districts_electing_one_more > 0:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Due to configuration, {districts_electing_one_more} districts will elect {winners_per_district_base + 1} candidate(s), and the remaining {config.NUM_DISTRICTS - districts_electing_one_more} districts will elect {winners_per_district_base} candidate(s).",
            )
        else:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Each district will elect {winners_per_district_base} candidate(s).",
            )

    # --- FASE 1: District Elections ---
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"\n{'*'*40}")
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        "--- PHASE 1: District Elections in Anthalys ---")
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             f"Number of Districts: {config.NUM_DISTRICTS}")
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"Candidates per district: {config.CANDIDATES_PER_DISTRICT}",
    )
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"Simulated citizens per district: {config.CITIZENS_PER_DISTRICT}",
    )
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"{'*'*40}")

    utils.send_pygame_update(
        utils.UPDATE_TYPE_STATUS,
        {
            "attempt": election_attempt,
            "phase": "District Elections",
            "round": 0,
            "status": "Running",
        },
    )

    if num_district_winners_needed > 0:
        for i in range(1, config.NUM_DISTRICTS + 1):
            try:
                import pygame
                if not pygame.display.get_init():
                    # Clear running event if Pygame quits unexpectedly
                    if running_event:
                        running_event.clear()
                    return
            except ImportError:
                pass

            winners_to_elect_this_district = winners_per_district_base
            if i <= districts_electing_one_more:
                winners_to_elect_this_district += 1

            # Passa gli eventi e la modalità al district election
            district_winners_info = execute_district_election(
                i,
                winners_to_elect_this_district,
                continue_event,
                running_event,
                step_by_step_mode  # Passa qui
            )
            # Controlla di nuovo dopo la chiamata, in caso district_election sia uscito presto
            try:
                import pygame
                if not pygame.display.get_init():
                    if running_event:
                        running_event.clear()
                    return
            except ImportError:
                pass

            # Se la simulazione non è in modalità passo passo, settiamo l'evento per il prossimo distretto
            if continue_event and not step_by_step_mode:
                continue_event.set()

            district_elected_candidates_info.extend(district_winners_info)

    else:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "Phase 1 (District Elections) skipped as all candidates are pre-selected."
        )

    governor_candidates_info.extend(district_elected_candidates_info)

    if len(governor_candidates_info) != config.NUM_GRAND_ELECTORS:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_ERROR,
            f"Internal Error: Final number of candidates for Phase 2 ({len(governor_candidates_info)}) does not match NUM_GRAND_ELECTORS ({config.NUM_GRAND_ELECTORS}).",
        )
        utils.send_pygame_update(utils.UPDATE_TYPE_ERROR,
                                 "Cannot proceed to Phase 2.")
        utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE,
                                 {"elected": False})
        if running_event:
            running_event.clear()
        return

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"\n--- Phase 1 Completed ---",
    )
    if num_preselected > 0:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"--- {num_preselected} candidate(s) carried over from previous attempt ---",
        )
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"Total candidates for Governor (Grand Electors): {len(governor_candidates_info)}",
    )

    # --- PHASE 2: Governor Election by the College of Grand Electors ---
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"\n{'*'*40}")
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        "--- PHASE 2: Governor Election by the College of Grand Electors ---",
    )
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"{'*'*40}")

    # Pausa rituale prima del College (mantienila anche in modalità passo-passo)
    if continue_event:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_STATUS,
            {
                "attempt": election_attempt,
                "phase": "College Election",
                "round": 0,
                "status": "Entering Electoral Palace...",
            },
        )
        if step_by_step_mode:
            continue_event.wait()
            continue_event.clear()
        else:
            time.sleep(config.GOVERNOR_PAUSE_SECONDS *
                       2)  # Pausa fissa in modalità continua
            continue_event.set(
            )  # Settalo di nuovo per permettere il prossimo step

    final_governor_candidate_names = [
        c['name'] for c in governor_candidates_info
    ]
    grand_electors_with_traits = generation.generate_grand_electors(
        len(final_governor_candidate_names))
    grand_electors_ids = [
        e_data['id'] for e_data in grand_electors_with_traits
    ]

    available_standing_sprite_keys = [
        key for key in data.SPRITE_MAPPING if key.endswith("_standing")
    ]
    if not available_standing_sprite_keys and not data.SPRITE_MAPPING:
        print(
            "Warning: No '_standing' sprite keys found in SPRITE_MAPPING, and no sprites defined at all. Characters will be placeholders."
        )

    for cand in governor_candidates_info:
        if 'sprite_key' not in cand or cand['sprite_key'] is None:
            sprite_key = None
            first_name = cand['name'].split(' ')[0]
            is_female = any(name in first_name
                            for name in data.FEMALE_FIRST_NAMES)
            is_male = any(name in first_name for name in data.MALE_FIRST_NAMES)
            suitable_keys = []
            if is_female:
                suitable_keys = [
                    key for key in available_standing_sprite_keys
                    if key.startswith("female_")
                ]
            elif is_male:
                suitable_keys = [
                    key for key in available_standing_sprite_keys
                    if key.startswith("male_")
                ]
            if suitable_keys:
                sprite_key = random.choice(suitable_keys)
            elif available_standing_sprite_keys:
                sprite_key = random.choice(available_standing_sprite_keys)
            elif "default_standing" in data.SPRITE_MAPPING:
                sprite_key = "default_standing"
            elif data.SPRITE_MAPPING:
                try:
                    sprite_key = list(data.SPRITE_MAPPING.keys())[0]
                except Exception:
                    sprite_key = None
            cand['sprite_key'] = sprite_key

    all_governor_candidate_names = [
        c["name"] for c in governor_candidates_info
    ]
    votable_candidates_turn_info = list(governor_candidates_info)

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"\nTotal number of Grand Electors (voters): {len(grand_electors_ids)}",
    )
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        f"Number of Governor candidates: {len(governor_candidates_info)}",
    )

    elector_full_preferences = voting.initialize_elector_preferences(
        grand_electors_with_traits, governor_candidates_info,
        preselected_candidates_info)

    # --- Initialize Candidate Campaign Budget ---
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        "\n--- Initializing Candidate Campaign Budgets ---")
    for candidate in governor_candidates_info:
        candidate['campaign_budget'] = config.INITIAL_CAMPAIGN_BUDGET
        # Log budget iniziale per ogni candidato
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"  {candidate['name']} starts with Budget: {candidate['campaign_budget']}"
        )
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                             "---------------------------------------------")

    # 2. Entry and Isolation (Simulated) - Questo step è la pausa iniziale che abbiamo gestito sopra

    # 3. Oath Ceremony (Simulated)
    if continue_event:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_STATUS,
            {
                "attempt": election_attempt,
                "phase": "College Election",
                "round": 0,
                "status": "Taking Oath...",
            },
        )
        if step_by_step_mode:
            continue_event.wait()
            continue_event.clear()
        else:
            time.sleep(config.GOVERNOR_PAUSE_SECONDS
                       )  # Pausa fissa in modalità continua
            continue_event.set(
            )  # Settalo di nuovo per permettere il prossimo step

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        "\nOath Ceremony of the Grand Electors for the Election of the Governor..."
    )
    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        "Formula: 'I swear upon my honor... to elect him or her whom I sincerely believe to be the most competent...'"
    )
    time.sleep(
        config.GOVERNOR_PAUSE_SECONDS)  # Mantieni pausa rituale dopo il testo

    # --- Presentation of Governor Candidates and Their Statement of Intent ---
    if continue_event:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_STATUS,
            {
                "attempt": election_attempt,
                "phase": "College Election",
                "round": 0,
                "status": "Presenting Candidates...",
            },
        )
        if step_by_step_mode:
            continue_event.wait()
            continue_event.clear()
        else:
            time.sleep(config.GOVERNOR_PAUSE_SECONDS
                       )  # Pausa fissa in modalità continua
            continue_event.set(
            )  # Settalo di nuovo per permettere il prossimo step

    utils.send_pygame_update(
        utils.UPDATE_TYPE_MESSAGE,
        "\n--- Presentation of Governor Candidates and Their Statement of Intent ---",
    )
    governor_candidates_info_sorted = sorted(governor_candidates_info,
                                             key=lambda x: x["name"])
    preselected_names_set = ({c["name"]
                              for c in preselected_candidates_info}
                             if preselected_candidates_info else set())

    for i, candidate in enumerate(governor_candidates_info_sorted):
        status = ""
        if candidate["name"] in preselected_names_set:
            status = "(Pre-selected from previous attempt)"
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"\nGovernor Candidate {i+1}: {candidate['name']} {status}",
        )
        attributes_str = ", ".join([
            f"{key.replace('_', ' ').title()}=(Level {value}/{config.ATTRIBUTE_RANGE[1]})"
            for key, value in candidate["attributes"].items()
        ])
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 f"  Simulated Attributes: {attributes_str}")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f'  Statement: "{generate_candidate_oath(candidate)}"',
        )
        time.sleep(config.GOVERNOR_PAUSE_SECONDS / 4)
    utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, "-" * 40)
    # time.sleep(config.GOVERNOR_PAUSE_SECONDS * 2) # Rimosso, attesa gestita dall'evento

    current_round = 0
    governor_elected = None
    num_active_electors = len(grand_electors_ids)
    current_voting_electors_ids = list(grand_electors_ids)
    runoff_mode = False
    runoff_candidate_names = []
    last_round_results = {}
    last_normal_round_results = {}
    current_required_majority_percentage = config.REQUIRED_MAJORITY
    if election_attempt == 4:
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "\n--- Special Rule for Attempt 4: Required Majority is 50% ---",
        )
        current_required_majority_percentage = 0.5

    # 4. College Voting Rounds (Loop)
    while (governor_elected is None
           and current_round < config.MAX_TOTAL_ROUNDS):
        current_round += 1
        # Attesa per l'inizio del round è ora gestita all'inizio di execute_voting_round

        # --- Simulate Campaigning before Voting ---
        # Esegui campagna a partire dal round 1 (dopo la presentazione)
        if current_round > 0:
            # --- Candidate Theme Selection for this Round ---
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"\n--- Campaign Round {current_round} - Candidate Theme Selection ---"
            )
            for candidate in governor_candidates_info:
                # Semplice logica: i candidati scelgono 1 o 2 dei loro attributi più alti come temi
                sorted_attributes = sorted(candidate['attributes'].items(),
                                           key=lambda item: item[1],
                                           reverse=True)
                # Scegli i N attributi più alti, con N casuale tra 1 e 2 (o configurabile)
                num_themes = random.randint(
                    1, 2)  # Potrebbe essere un parametro di config
                selected_themes = [
                    attr[0] for attr in sorted_attributes[:num_themes]
                ]
                candidate[
                    'current_campaign_themes'] = selected_themes  # Aggiungi i temi all'oggetto candidato
                theme_text = ", ".join([
                    theme.replace('_', ' ').title()
                    for theme in selected_themes
                ])
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"  {candidate['name']} focuses on: {theme_text}")
            utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                     "-------------------------------")

            # Log budget prima della campagna per mostrare l'impatto
            utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                     "\nBudget before Campaign:")
            for candidate in governor_candidates_info:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"  {candidate['name']}: {candidate.get('campaign_budget', 'N/A')}"
                )
            utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                     "-----------------------")

            voting.simulate_campaigning(governor_candidates_info,
                                        grand_electors_with_traits,
                                        elector_full_preferences,
                                        last_round_results)
            time.sleep(config.GOVERNOR_PAUSE_SECONDS / 2)

        if runoff_mode:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"\nRunoff Mode between: {runoff_candidate_names[0]} and {runoff_candidate_names[1]}",
            )
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Number of Grand Electors participating: {len(grand_electors_ids)}",
            )
            votable_candidates_turn_info = [
                c for c in governor_candidates_info
                if c["name"] in runoff_candidate_names
            ]
            current_voting_electors_ids = list(grand_electors_ids)

        else:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"\nNumber of Grand Electors participating: {len(grand_electors_ids)}",
            )
            votable_candidates_turn_info = list(governor_candidates_info)
            current_voting_electors_ids = (grand_electors_ids)

        # Execute the voting round, passing events and mode
        round_governor_elected, current_results, elector_full_preferences, votes_needed_this_round = execute_voting_round(
            current_voting_electors_ids,
            votable_candidates_turn_info,
            elector_full_preferences,
            last_round_results,
            len(grand_electors_ids),
            current_required_majority_percentage,
            current_round,
            governor_candidates_info,
            runoff_carryover_winner_name,
            continue_event,  # Passa l'evento
            running_event,  # Passa l'evento
            step_by_step_mode  # Passa la modalità
        )

        governor_elected = round_governor_elected

        # Controlla di nuovo se Pygame è attivo dopo il round
        try:
            import pygame
            if not pygame.display.get_init():
                if running_event:
                    running_event.clear()
                return
            # Aggiungi un breve ritardo per permettere alla GUI di aggiornarsi tra i round in modalità continua
            if continue_event and not step_by_step_mode:
                time.sleep(config.GOVERNOR_PAUSE_SECONDS)
        except ImportError:
            pass

        # --- Log Budget after Campaign ---
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "\nBudget after Campaign:")
        for candidate in governor_candidates_info:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"  {candidate['name']}: {candidate.get('campaign_budget', 'N/A'):.2f}"
            )  # Formatta per 2 decimali
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "-----------------------")

        if not runoff_mode:
            last_normal_round_results = copy.deepcopy(current_results)

        last_round_results = copy.deepcopy(current_results)

        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "\nCollege Round Results:")
        college_results_data = []
        all_candidates_dict = {c["name"]: c for c in governor_candidates_info}

        for candidate_name, votes in current_results.most_common():
            is_elected_this_round = (governor_elected is not None
                                     and candidate_name == governor_elected)
            sprite_key = all_candidates_dict.get(candidate_name,
                                                 {}).get('sprite_key', None)
            attributes = all_candidates_dict.get(candidate_name, {}).get(
                'attributes', {})  # Includi attributi nei risultati
            college_results_data.append({
                "name": candidate_name,
                "votes": votes,
                "elected_this_round": is_elected_this_round,
                "sprite_key": sprite_key,
                "attributes": attributes  # Aggiungi attributi
            })

        utils.send_pygame_update(
            utils.UPDATE_TYPE_RESULTS,
            {
                "type": "college",
                "results": college_results_data
            },
        )

        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"\nVotes needed for election: {votes_needed_this_round} (based on {current_required_majority_percentage*100:.0f}% of {config.NUM_GRAND_ELECTORS} Grand Electors)"
        )

        if governor_elected:
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"MAJORITY REACHED! {governor_elected} is elected Governor.")
            utils.send_pygame_update(utils.UPDATE_TYPE_FLAG, True)
            utils.send_pygame_update(
                utils.UPDATE_TYPE_STATUS,
                {
                    "attempt": election_attempt,
                    "phase": "College Election",
                    "round": current_round,
                    "status": "Governor Elected!",
                },
            )
            break

        else:
            utils.send_pygame_update(utils.UPDATE_TYPE_FLAG, False)
            # In modalità continua, non c'è uno stato "Waiting", semplicemente va al round successivo
            status_text = "No Election"
            if step_by_step_mode:
                # Se in passo passo, lo stato diventa attesa
                status_text = "Waiting for Next Round"

            utils.send_pygame_update(
                utils.UPDATE_TYPE_STATUS,
                {
                    "attempt": election_attempt,
                    "phase": "College Election",
                    "round": current_round,
                    "status": status_text,
                },
            )

            # Gestisci la transizione al runoff
            if not runoff_mode and current_round >= config.MAX_NORMAL_ROUNDS:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"\nReached the limit of {config.MAX_NORMAL_ROUNDS} normal College rounds without election.",
                )
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    "Proceeding to select candidates for the runoff from the most voted in the last normal round.",
                )
                # Lo stato di attesa per il Next Round (se in passo passo) è già stato settato sopra
                if not step_by_step_mode:
                    # In modalità continua, invia uno stato "Preparing Runoff" prima di procedere
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_STATUS,
                        {
                            "attempt": election_attempt,
                            "phase": "College Election",
                            "round": current_round,
                            "status": "Preparing Runoff",
                        },
                    )
                    time.sleep(config.GOVERNOR_PAUSE_SECONDS
                               )  # Breve pausa prima del runoff automatico
                    if continue_event:
                        continue_event.set(
                        )  # Settalo di nuovo per permettere al runoff di iniziare

                if not last_normal_round_results:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_ERROR,
                        "No valid votes recorded in the last normal College round. Cannot proceed to runoff.",
                    )
                    utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE,
                                             {"elected": False})
                    if running_event:
                        running_event.clear()
                    break

                initial_governor_candidate_names = [
                    c['name'] for c in governor_candidates_info
                ]

                filtered_initial_results = {
                    c: v
                    for c, v in last_normal_round_results.items()
                    if c in initial_governor_candidate_names
                }

                if len(filtered_initial_results) < 2:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_ERROR,
                        "Fewer than two Governor candidates received valid votes in the last normal College round that are still in the initial candidate list."
                    )
                    utils.send_pygame_update(utils.UPDATE_TYPE_ERROR,
                                             "Cannot proceed to runoff.")
                    utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE,
                                             {"elected": False})
                    if running_event:
                        running_event.clear()
                    break

                most_voted = Counter(filtered_initial_results).most_common(2)
                runoff_candidate_names = [c[0] for c in most_voted]

                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    f"Governor Runoff Candidates: {runoff_candidate_names[0]} and {runoff_candidate_names[1]}",
                )

                runoff_mode = True

            # Se non sei in modalità passo passo e non sei passato al runoff (o il runoff è già iniziato)
            # e non sei nell'ultimo round, settiamo l'evento per il prossimo round automatico.
            # In modalità passo passo, l'evento viene resettato e atteso all'inizio del loop.
            if continue_event and not step_by_step_mode and current_round < config.MAX_TOTAL_ROUNDS:
                continue_event.set()

    # 5. Acceptance and Announcement OR Handling Deadlock / Restart
    if governor_elected:
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"\n{'='*50}")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"--- Anthalys Electoral Process (Attempt {election_attempt}) Concluded Successfully ---",
        )
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"{'='*50}")
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "\n--- Governor Acceptance Phase ---")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"The President of the College addresses {governor_elected}: 'Do you accept the election as Governor conferred upon you by the College of Grand Electors, in accordance with the statute of the Anthalys governorship and with full awareness of the responsibilities this entails?'",
        )
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"Response from {governor_elected}: 'I accept with a sense of responsibility and dedication the election as Governor. I pledge to serve Anthalys with integrity, justice, and fairness, working for its progress and well-being, in compliance with the statute and laws.'",
        )
        time.sleep(config.GOVERNOR_PAUSE_SECONDS * 2)

        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "\n--- Announcement to the Community of Anthalys Phase ---")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "The President of the College appears on the balcony...",
        )
        elected_gender = "man"
        elected_candidate_info = next((c for c in governor_candidates_info
                                       if c['name'] == governor_elected), None)

        if elected_candidate_info:
            first_name_of_elected = elected_candidate_info['name'].split(
                ' ')[0]
            if any(name in first_name_of_elected
                   for name in data.FEMALE_FIRST_NAMES):
                elected_gender = "woman"
            elif any(name in first_name_of_elected
                     for name in data.MALE_FIRST_NAMES):
                elected_gender = "man"
            else:
                elected_gender = "person"

        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"Announcement Formula: 'Citizens of our governorship! The electoral process is concluded, and the necessary consensus has been reached. We announce with satisfaction: We have the Governor! The College of Grand Electors has elected {governor_elected}, a {elected_gender} of proven experience and dedication, as your next Governor.'",
        )
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"{governor_elected} is presented to the community.",
        )
        time.sleep(config.GOVERNOR_PAUSE_SECONDS * 2)

        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                 "\n--- Process Completed ---")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"The new elected Governor is: {governor_elected}",
        )
        utils.send_pygame_update(
            utils.UPDATE_TYPE_COMPLETE,
            {
                "elected": True,
                "governor": governor_elected
            },
        )
        if running_event:
            running_event.clear()

    else:
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"\n{'='*50}")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"--- Anthalys Electoral Process (Attempt {election_attempt}) Concluded with Deadlock in the College Phase ---",
        )
        utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"{'='*50}")
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            f"The College of Grand Electors failed to elect a Governor within the maximum limit of {config.MAX_TOTAL_ROUNDS} rounds.",
        )
        utils.send_pygame_update(
            utils.UPDATE_TYPE_MESSAGE,
            "This prolonged deadlock requires the activation of further statutory steps, which include restarting the entire electoral process from the district elections.",
        )
        # Se c'è stato uno stallo finale, lo stato di attesa non ha più senso
        utils.send_pygame_update(
            utils.UPDATE_TYPE_STATUS,
            {
                "attempt": election_attempt,
                "phase": "College Election",
                "round": current_round,
                "status": "DEADLOCK",
            },
        )

        next_preselected_candidates_info = []
        carried_over_winner_name_for_next_attempt = None

        if election_attempt < config.MAX_ELECTION_ATTEMPTS:
            utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE,
                                     "\nStatutory Steps Activated:")

            results_for_carryover = last_round_results

            if results_for_carryover:
                if runoff_mode and len(runoff_candidate_names) == 2:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        "\nRunoff deadlock detected. Applying specific rules.")
                    runoff_candidates_final_results = {
                        c: results_for_carryover.get(c, 0)
                        for c in runoff_candidate_names
                    }

                    sorted_runoff_results = sorted(
                        runoff_candidates_final_results.items(),
                        key=lambda item: item[1],
                        reverse=True)

                    if len(sorted_runoff_results) == 2:
                        runoff_winner_name = sorted_runoff_results[0][0]
                        runoff_loser_name = sorted_runoff_results[1][0]

                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_MESSAGE,
                            f"Runoff Winner (most votes): {runoff_winner_name} ({sorted_runoff_results[0][1]} votes)"
                        )
                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_MESSAGE,
                            f"Runoff Loser (fewer votes): {runoff_loser_name} ({sorted_runoff_results[1][1]} votes)"
                        )

                        carried_over_candidate_info_list = [
                            c for c in governor_candidates_info
                            if c['name'] == runoff_winner_name
                        ]

                        if carried_over_candidate_info_list:
                            next_preselected_candidates_info = carried_over_candidate_info_list
                            carried_over_winner_name_for_next_attempt = runoff_winner_name
                            utils.send_pygame_update(
                                utils.UPDATE_TYPE_MESSAGE,
                                f"{runoff_winner_name} will be carried over to the next attempt with a bonus."
                            )
                            utils.send_pygame_update(
                                utils.UPDATE_TYPE_MESSAGE,
                                f"{runoff_loser_name} is excluded from the next attempt."
                            )
                        else:
                            utils.send_pygame_update(
                                utils.UPDATE_TYPE_ERROR,
                                f"Could not find full info for runoff winner {runoff_winner_name}. Cannot carry over."
                            )
                            next_preselected_candidates_info = []
                            carried_over_winner_name_for_next_attempt = None

                    else:
                        utils.send_pygame_update(
                            utils.UPDATE_TYPE_ERROR,
                            "Internal logic error: Runoff mode active but unexpected number of candidates in runoff_results."
                        )
                        num_to_carry_over = min(
                            config.NUM_PRESELECTED_CANDIDATES,
                            len(results_for_carryover))
                        top_voted_in_last_round = Counter(
                            results_for_carryover).most_common(
                                num_to_carry_over)
                        top_candidate_names_for_carryover = [
                            c[0] for c in top_voted_in_last_round
                        ]
                        next_preselected_candidates_info = [
                            c for c in governor_candidates_info
                            if c["name"] in top_candidate_names_for_carryover
                        ]
                        carried_over_winner_name_for_next_attempt = None

                else:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        "\nGeneral College deadlock detected. Identifying top candidates."
                    )
                    num_to_carry_over = min(config.NUM_PRESELECTED_CANDIDATES,
                                            len(results_for_carryover))
                    top_voted_in_last_round = Counter(
                        results_for_carryover).most_common(num_to_carry_over)
                    top_candidate_names_for_carryover = [
                        c[0] for c in top_voted_in_last_round
                    ]
                    next_preselected_candidates_info = [
                        c for c in governor_candidates_info
                        if c["name"] in top_candidate_names_for_carryover
                    ]
                    carried_over_winner_name_for_next_attempt = None

                if next_preselected_candidates_info:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        f"Candidates carried over to next attempt: {[c['name'] for c in next_preselected_candidates_info]}"
                    )
                else:
                    utils.send_pygame_update(
                        utils.UPDATE_TYPE_MESSAGE,
                        "No candidates carried over to the next attempt.")

            else:
                utils.send_pygame_update(
                    utils.UPDATE_TYPE_MESSAGE,
                    "No results available from the last College round to identify candidates for carryover.",
                )
                next_preselected_candidates_info = []
                carried_over_winner_name_for_next_attempt = None

            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"Initiating a new complete electoral process (Attempt {election_attempt + 1}), starting from the district elections, carrying over {len(next_preselected_candidates_info)} candidate(s)."
            )

            try:
                import pygame
                if pygame.display.get_init():
                    run_election_simulation(
                        election_attempt + 1,
                        preselected_candidates_info=next_preselected_candidates_info,
                        runoff_carryover_winner_name=carried_over_winner_name_for_next_attempt,
                        continue_event=continue_event,
                        running_event=running_event,
                        step_by_step_mode=step_by_step_mode  # Passa la modalità
                    )
                else:
                    print(
                        "Pygame closed during restart preparation, stopping.")
            except ImportError:
                run_election_simulation(
                    election_attempt + 1,
                    preselected_candidates_info=next_preselected_candidates_info,
                    runoff_carryover_winner_name=carried_over_winner_name_for_next_attempt,
                    continue_event=continue_event,
                    running_event=running_event,
                    step_by_step_mode=step_by_step_mode  # Passa la modalità
                )

        else:
            utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"\n{'='*50}")
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                "Maximum number of electoral process attempts reached.",
            )
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                f"After {config.MAX_ELECTION_ATTEMPTS} complete attempts, it was not possible to elect a Governor for Anthalys.",
            )
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                "Exceptional measures are required according to the statute of Anthalys (e.g., referendum, external intervention).",
            )
            utils.send_pygame_update(utils.UPDATE_TYPE_MESSAGE, f"{'='*50}")
            utils.send_pygame_update(
                utils.UPDATE_TYPE_MESSAGE,
                "\n--- Electoral Procedure Finally Concluded Without Election ---",
            )
            utils.send_pygame_update(utils.UPDATE_TYPE_COMPLETE,
                                     {"elected": False})
            if running_event:
                running_event.clear()
