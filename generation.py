# generation.py
import random
import math
import networkx as nx
import uuid
import json
import config  # Assicurati sia importato
import data
import db_manager
# Import opzionale numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:  # pragma: no cover
    HAS_NUMPY = False


def generate_attributes_by_age(age):
    """Genera attributi candidati influenzati dall'età."""
    min_age, max_age = config.CANDIDATE_AGE_RANGE
    min_attr, max_attr = config.ATTRIBUTE_RANGE
    # Gestisci age_range nullo o negativo
    age_range = max_age - min_age if max_age > min_age else 1
    norm_age = max(0, min(1, (age - min_age) /
                          age_range))  # Normalizza e clampa età tra 0 e 1

    # Esperienza: tende ad aumentare con l'età
    max_exp_potential = min_attr + math.floor(
        (max_attr - min_attr + 1) * norm_age * 1.1)
    max_exp_potential = min(max_attr, max(min_attr, max_exp_potential))
    min_exp_potential = min_attr + math.floor(
        (max_attr - min_attr) * norm_age *
        0.3)  # Modificato per evitare +1 e poi -1
    min_exp_potential = min(max_attr,
                            max(min_attr,
                                min(min_exp_potential,
                                    max_exp_potential)))  # Assicura min <= max
    experience = random.randint(min_exp_potential, max_exp_potential)

    # Visione Sociale: potenzialmente più alta a età medie/basse
    # Leggermente modificato range
    min_soc = min_attr + 1 if 0.1 < norm_age < 0.7 and max_attr > min_attr else min_attr
    social_vision = random.randint(min_soc, max_attr)

    # Mediazione: picco a età medie?
    max_med_potential = min_attr + math.floor(
        (max_attr - min_attr + 1) * norm_age * 0.8)
    max_med_potential = min(max_attr, max(min_attr, max_med_potential))
    min_med_potential = min_attr + math.floor(
        (max_attr - min_attr) * norm_age * 0.2)
    min_med_potential = min(
        max_attr, max(min_attr, min(min_med_potential, max_med_potential)))
    mediation = random.randint(min_med_potential, max_med_potential)

    # Integrità: meno correlata all'età (casuale)
    integrity = random.randint(min_attr, max_attr)

    return {
        "administrative_experience": experience,
        "social_vision": social_vision,
        "mediation_ability": mediation,
        "ethical_integrity": integrity
    }


def generate_candidates(num_candidates, pool_male_first_names,
                        pool_female_first_names, pool_surnames):
    """
    Genera/Carica candidati, assicurando struttura stats base.
    SENZA flag LLM.
    """
    if num_candidates <= 0:
        return []  # Gestisci input nullo
    db_manager.create_tables()
    candidates = []
    used_full_names = set()

    num_males_target = num_candidates // 2
    num_females_target = num_candidates - num_males_target
    max_attempts_per_candidate = 500

    available_male_first_names = list(pool_male_first_names)
    available_female_first_names = list(pool_female_first_names)
    available_surnames = list(pool_surnames)

    # Helper interno per generare/caricare
    def get_or_create_candidate(first_names, surnames, gender, used_names_set):
        candidate_data = None
        attempts = 0
        while candidate_data is None and attempts < max_attempts_per_candidate:
            attempts += 1
            if not first_names or not surnames:
                break

            first_name = random.choice(first_names)
            surname = random.choice(surnames)
            full_name = f"{first_name} {surname}"

            existing_candidate = db_manager.get_candidate_by_name(full_name)

            if existing_candidate:
                if full_name in used_names_set:  # Già aggiunto in questa run?
                    continue  # Cerca un altro nome
                print(f"Loaded existing candidate: {full_name}")
                candidate_data = existing_candidate
                # Assicura struttura stats base
                if 'stats' not in candidate_data or not isinstance(
                        candidate_data['stats'], dict):
                    candidate_data['stats'] = {}
                base_stats = {
                    "total_elections_participated": 0,
                    "governor_wins": 0,
                    "election_losses": 0,
                    "total_votes_received_all_time": 0,
                    "rounds_participated_all_time": 0
                }
                for k, v in base_stats.items():
                    candidate_data['stats'].setdefault(k, v)

            elif full_name not in used_names_set:
                age = random.randint(*config.CANDIDATE_AGE_RANGE)
                attributes = generate_attributes_by_age(age)
                party_id = random.choices(
                    config.PARTY_IDS,
                    weights=config.PARTY_ID_ASSIGNMENT_WEIGHTS,
                    k=1)[0]
                initial_budget = float(config.INITIAL_CAMPAIGN_BUDGET)
                base_stats = {
                    "total_elections_participated": 0,
                    "governor_wins": 0,
                    "election_losses": 0,
                    "total_votes_received_all_time": 0,
                    "rounds_participated_all_time": 0
                }
                candidate_data = {
                    "uuid": str(uuid.uuid4()),
                    "name": full_name,
                    "attributes": attributes,
                    "gender": gender,
                    "age": age,
                    "party_id": party_id,
                    "initial_budget": initial_budget,
                    "current_budget": initial_budget,
                    "traits": [],
                    "stats": base_stats
                }
                db_manager.save_candidate(candidate_data)
                print(f"Generated and saved new candidate: {full_name}")

            if candidate_data:
                used_names_set.add(full_name)
                # Ritorna struttura consistente, prendendo current_budget
                return {
                    "uuid":
                    candidate_data.get("uuid"),
                    "name":
                    candidate_data.get("name"),
                    "attributes":
                    candidate_data.get("attributes", {}),
                    "gender":
                    candidate_data.get("gender"),
                    "age":
                    candidate_data.get("age"),
                    "party_id":
                    candidate_data.get("party_id"),
                    "campaign_budget":
                    float(
                        candidate_data.get(
                            "current_budget",
                            candidate_data.get("initial_budget", 0))),
                    "initial_budget":
                    float(candidate_data.get("initial_budget", 0)),
                    "traits":
                    candidate_data.get("traits", []),
                    "stats":
                    candidate_data.get("stats", {})
                }
        print(f"Warning: Max attempts reached for {gender} name generation."
              )  # Log se esce dal while
        return None

    # Genera maschi
    males_generated = 0
    random.shuffle(available_male_first_names)
    random.shuffle(available_surnames)
    while males_generated < num_males_target:
        cand = get_or_create_candidate(available_male_first_names,
                                       available_surnames, "male",
                                       used_full_names)
        if cand:
            candidates.append(cand)
            males_generated += 1
        else:
            break

    # Genera femmine
    females_generated = 0
    random.shuffle(available_female_first_names)
    random.shuffle(available_surnames)  # Rimescola cognomi
    while females_generated < num_females_target:
        cand = get_or_create_candidate(available_female_first_names,
                                       available_surnames, "female",
                                       used_full_names)
        if cand:
            candidates.append(cand)
            females_generated += 1
        else:
            break

    # Fallback
    num_missing = num_candidates - len(candidates)
    if num_missing > 0:
        print(f"Warning: Generating {num_missing} fallback candidates...")
        fallback_counter = 1
        while len(candidates) < num_candidates:
            # ... (Logica fallback come mostrata prima, assicurandosi di inizializzare stats) ...
            full_name = f"Fallback Candidate {fallback_counter:03d}"
            if db_manager.candidate_exists(
                    full_name) or full_name in used_full_names:
                fallback_counter += 1
                continue
            # ... (genera dati fallback) ...
            base_stats_fb = {
                "total_elections_participated": 0,
                "governor_wins": 0,
                "election_losses": 0,
                "total_votes_received_all_time": 0,
                "rounds_participated_all_time": 0
            }
            candidate_data_fb = {
                "uuid": str(uuid.uuid4()),
                "name": full_name,  # ... altri dati ...
                "stats": base_stats_fb
            }
            db_manager.save_candidate(candidate_data_fb)
            used_full_names.add(full_name)
            # Aggiungi alla lista con struttura consistente
            candidates.append(
                {
                    k: v
                    for k, v in candidate_data_fb.items()
                    if k != 'current_budget' and k != 'initial_budget'
                } | {
                    'campaign_budget': candidate_data_fb['current_budget'],
                    'initial_budget': candidate_data_fb['initial_budget']
                })
            fallback_counter += 1

    random.shuffle(candidates)
    final_count = len(candidates)
    if final_count < num_candidates:
        print(
            f"ERROR: Could only generate {final_count}/{num_candidates} candidates."
        )
    else:
        print(f"Generated/Loaded {final_count} candidates successfully.")
    return candidates


def generate_grand_electors(num_electors):
    """Genera Grand Electors con tratti (SENZA flag LLM)."""
    electors = []
    if num_electors <= 0:
        return electors

    for i in range(num_electors):
        elector_id = f"Elector_{i+1}"
        assigned_traits = []
        if config.ELECTOR_TRAITS:
            k_traits = min(config.ELECTOR_TRAIT_COUNT,
                           len(config.ELECTOR_TRAITS))
            if k_traits > 0:
                assigned_traits = random.sample(config.ELECTOR_TRAITS,
                                                k_traits)
        electors.append({
            "id": elector_id,
            "traits": assigned_traits
        })  # Niente is_llm_agent

    return electors


def create_elector_network(elector_ids):
    """Crea rete sociale Watts-Strogatz."""
    # ... (Codice completo e robusto come mostrato prima) ...
    num_nodes = len(elector_ids)
    if num_nodes == 0:
        return nx.Graph()
    k = config.NETWORK_AVG_NEIGHBORS
    p = config.NETWORK_REWIRING_PROB
    if k >= num_nodes:
        k = max(0, num_nodes - 2)
    if k % 2 != 0:
        k = max(0, k - 1)
    G = nx.empty_graph(num_nodes)  # Default a grafo vuoto
    if k > 0 or num_nodes <= 2:  # k=0 valido solo per n<=2 in WS
        print(f"Generating Watts-Strogatz graph: n={num_nodes}, k={k}, p={p}")
        try:
            G = nx.watts_strogatz_graph(n=num_nodes, k=k, p=p)
        except nx.NetworkXError:  # pragma: no cover
            print(
                f"Warning: WS graph failed with N={num_nodes}, K={k}. Creating fallback ring."
            )
            try:
                G = nx.watts_strogatz_graph(
                    n=num_nodes, k=k,
                    p=0) if k > 0 else nx.empty_graph(num_nodes)
            except:
                G = nx.empty_graph(num_nodes)  # Fallback estremo
    id_map = {i: elector_id for i, elector_id in enumerate(elector_ids)}
    G_relabeled = nx.relabel_nodes(G, id_map, copy=True)
    print(
        f"Social network generated: {G_relabeled.number_of_nodes()} nodes, {G_relabeled.number_of_edges()} edges."
    )
    if G_relabeled.number_of_nodes() > 0:
        avg_degree = sum(dict(
            G_relabeled.degree()).values()) / G_relabeled.number_of_nodes()
        print(f"Average node degree: {avg_degree:.2f}")
    return G_relabeled
