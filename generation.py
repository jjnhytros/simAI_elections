# In generation.py

import random
import math
import networkx as nx  # <--- ASSICURATI CHE QUESTA RIGA SIA PRESENTE E NON COMMENTATA
# Imports da altri moduli del progetto (modificati da relativi a assoluti)
import config
import data

# ... (funzione generate_attributes_by_age come prima) ...


def generate_candidates(num_candidates, pool_male_first_names, pool_female_first_names, pool_surnames):
    """
    Generates candidates with gender split, unique names, age, age-biased attributes, and party ID.
    """
    candidates = []
    used_full_names = set()

    num_males_target = num_candidates // 2
    num_females_target = num_candidates - num_males_target
    max_attempts_per_candidate = 1000

    # Liste disponibili (copiate)
    available_male_first_names = list(pool_male_first_names)
    available_female_first_names = list(pool_female_first_names)
    available_surnames = list(pool_surnames)

    # Helper (come prima)
    def generate_attributes_by_age(age):
        # ... (logica attributi basati su età come prima) ...
        min_age, max_age = config.CANDIDATE_AGE_RANGE
        min_attr, max_attr = config.ATTRIBUTE_RANGE
        age_range = max_age - min_age
        norm_age = (age - min_age) / age_range if age_range > 0 else 0.5
        max_exp_potential = min_attr + \
            math.floor((max_attr - min_attr + 1) * norm_age * 1.1)
        max_exp_potential = min(max_attr, max(min_attr, max_exp_potential))
        min_exp_potential = min_attr + \
            math.floor((max_attr - min_attr - 1) * norm_age * 0.3)
        min_exp_potential = min(min_exp_potential, max_exp_potential)
        experience = random.randint(min_exp_potential, max_exp_potential)
        min_soc = min_attr
        if 0.2 < norm_age < 0.7:
            min_soc = min_attr + 1 if max_attr > min_attr else min_attr
        social_vision = random.randint(min_soc, max_attr)
        max_med_potential = min_attr + \
            math.floor((max_attr - min_attr + 1) * norm_age * 0.8)
        max_med_potential = min(max_attr, max(min_attr, max_med_potential))
        min_med_potential = min_attr + \
            math.floor((max_attr - min_attr - 1) * norm_age * 0.2)
        min_med_potential = min(min_med_potential, max_med_potential)
        mediation = random.randint(min_med_potential, max_med_potential)
        integrity = random.randint(min_attr, max_attr)
        return {"administrative_experience": experience, "social_vision": social_vision, "mediation_ability": mediation, "ethical_integrity": integrity}

    # --- Genera Candidati Maschi ---
    males_generated = 0
    random.shuffle(available_male_first_names)
    random.shuffle(available_surnames)
    while males_generated < num_males_target:
        candidate_generated = False
        attempts = 0
        while not candidate_generated and attempts < max_attempts_per_candidate:
            attempts += 1
            if not available_male_first_names or not available_surnames:
                break
            first_name = random.choice(available_male_first_names)
            surname = random.choice(available_surnames)
            full_name = f"{first_name} {surname}"
            if full_name not in used_full_names:
                used_full_names.add(full_name)
                age = random.randint(*config.CANDIDATE_AGE_RANGE)
                attributes = generate_attributes_by_age(age)
                # --- Assegna Party ID ---
                party_id = random.choices(
                    config.PARTY_IDS, weights=config.PARTY_ID_ASSIGNMENT_WEIGHTS, k=1)[0]
                # --- Fine Assegnazione ---
                candidates.append({"name": full_name, "attributes": attributes,
                                  "gender": "male", "age": age, "party_id": party_id})  # Aggiunto party_id
                males_generated += 1
                candidate_generated = True
        if not candidate_generated:
            print(
                f"Warning: Max attempts reached for male {males_generated+1}.")
            break

    # --- Genera Candidate Femmine ---
    females_generated = 0
    random.shuffle(available_female_first_names)
    random.shuffle(available_surnames)
    while females_generated < num_females_target:
        candidate_generated = False
        attempts = 0
        while not candidate_generated and attempts < max_attempts_per_candidate:
            attempts += 1
            if not available_female_first_names or not available_surnames:
                break
            first_name = random.choice(available_female_first_names)
            surname = random.choice(available_surnames)
            full_name = f"{first_name} {surname}"
            if full_name not in used_full_names:
                used_full_names.add(full_name)
                age = random.randint(*config.CANDIDATE_AGE_RANGE)
                attributes = generate_attributes_by_age(age)
                # --- Assegna Party ID ---
                party_id = random.choices(
                    config.PARTY_IDS, weights=config.PARTY_ID_ASSIGNMENT_WEIGHTS, k=1)[0]
                # --- Fine Assegnazione ---
                candidates.append({"name": full_name, "attributes": attributes,
                                  "gender": "female", "age": age, "party_id": party_id})  # Aggiunto party_id
                females_generated += 1
                candidate_generated = True
        if not candidate_generated:
            print(
                f"Warning: Max attempts reached for female {females_generated+1}.")
            break

    # --- Fallback (come prima, ma aggiunge party_id) ---
    num_generated = len(candidates)
    num_missing = num_candidates - num_generated
    if num_missing > 0:
        print(f"Warning: Generating {num_missing} fallback candidates...")
        fallback_counter = 1
        while len(candidates) < num_candidates:
            age = random.randint(*config.CANDIDATE_AGE_RANGE)
            attributes = generate_attributes_by_age(age)
            gender = random.choice(["male", "female"])
            # --- Assegna Party ID Fallback ---
            party_id = random.choices(
                config.PARTY_IDS, weights=config.PARTY_ID_ASSIGNMENT_WEIGHTS, k=1)[0]
            # --- Fine Assegnazione ---
            # Genera nome fallback univoco (come prima)
            full_name = f"Fallback Candidate {gender.capitalize()} {fallback_counter:03d}"
            attempts = 0
            max_name_attempts = 10
            while full_name in used_full_names and attempts < max_name_attempts:
                full_name = f"Fallback Candidate {gender.capitalize()} {fallback_counter:03d}_{random.randint(100,999)}"
                attempts += 1
            if full_name in used_full_names:
                full_name = f"Fallback Forced Unique {random.randint(10000, 99999)}"
            used_full_names.add(full_name)

            candidates.append({"name": full_name, "attributes": attributes,
                              "gender": gender, "age": age, "party_id": party_id})  # Aggiunto party_id
            fallback_counter += 1
            if fallback_counter > num_missing * 2 and len(candidates) < num_candidates:
                print(f"ERROR: Fallback loop stuck.")
                break  # Safety break

    # --- Conclusione ---
    random.shuffle(candidates)
    final_count = len(candidates)
    if final_count != num_candidates:
        print(
            f"ERROR: Final candidate count! Generated {final_count}, needed {num_candidates}.")
    else:
        print(
            f"Generated {final_count}/{num_candidates} candidates successfully.")
    return candidates


# Funzione generate_grand_electors rimane invariata
def generate_grand_electors(num_electors):
    """Generates a list of identifiers for the Grand Electors with assigned traits."""
    electors = []
    for i in range(num_electors):
        elector_id = f"Elector_{i+1}"
        assigned_traits = []
        if config.ELECTOR_TRAITS:  # Controlla se la lista tratti non è vuota
            assigned_traits = random.sample(
                config.ELECTOR_TRAITS,
                min(config.ELECTOR_TRAIT_COUNT, len(config.ELECTOR_TRAITS)))
        electors.append({"id": elector_id, "traits": assigned_traits})
    return electors

# --- NUOVA FUNZIONE: Creazione Rete Sociale ---


def create_elector_network(elector_ids):
    """
    Crea una rete sociale tra gli elettori usando il modello Watts-Strogatz.
    Args:
        elector_ids: Lista degli ID degli elettori (che saranno i nodi).
    Returns:
        Un oggetto networkx.Graph.
    """
    num_nodes = len(elector_ids)
    k = config.NETWORK_AVG_NEIGHBORS
    p = config.NETWORK_REWIRING_PROB

    # Assicura che k sia pari e minore del numero di nodi
    if k >= num_nodes:
        k = max(2, num_nodes - 2)  # Adatta k se ci sono pochi nodi
    if k % 2 != 0:
        k = max(2, k - 1)  # Rendi k pari

    print(f"Generating Watts-Strogatz graph: n={num_nodes}, k={k}, p={p}")
    try:
        # Crea il grafo usando il modello piccolo-mondo
        G = nx.watts_strogatz_graph(n=num_nodes, k=k, p=p)
    except nx.NetworkXError as e:
        print(
            f"Error generating Watts-Strogatz graph: {e}. Falling back to simple ring lattice.")
        # Fallback a un grafo a reticolo circolare semplice se WS fallisce (k troppo grande?)
        G = nx.watts_strogatz_graph(
            n=num_nodes, k=k if k < num_nodes else max(2, num_nodes-2), p=0)

    # Mappa gli ID degli elettori ai nodi del grafo (da 0 a n-1)
    # NetworkX usa interi 0..n-1 come nodi di default per questo generatore.
    # Creiamo un mapping se vogliamo usare gli ID stringa come nodi (più leggibile).
    id_map = {i: elector_id for i, elector_id in enumerate(elector_ids)}
    G_relabeled = nx.relabel_nodes(G, id_map, copy=True)

    print(
        f"Social network generated with {G_relabeled.number_of_nodes()} nodes and {G_relabeled.number_of_edges()} edges.")
    avg_degree = sum(dict(G_relabeled.degree()).values(
    )) / G_relabeled.number_of_nodes() if G_relabeled.number_of_nodes() > 0 else 0
    print(f"Average node degree: {avg_degree:.2f}")

    return G_relabeled
# --- FINE NUOVA FUNZIONE ---
