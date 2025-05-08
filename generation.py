import random
# Imports da altri moduli del progetto (modificati da relativi a assoluti)
import config
import data


def generate_candidates(num_candidates, pool_first_names, pool_surnames):
    """Generates a list of candidates with diverse names and simulated attributes."""
    candidates = []

    used_first_names = set()
    used_surnames = set()

    # Get available standing sprite keys from the SPRITE_MAPPING
    available_sprite_keys = [
        key for key in data.SPRITE_MAPPING if key.endswith("_standing")
    ]
    if not available_sprite_keys:
        print(
            "Warning: No '_standing' sprite keys found in SPRITE_MAPPING. Characters will be placeholders."
        )
        if data.SPRITE_MAPPING:  # If any sprites are mapped at all, add their keys as fallback
            available_sprite_keys = list(data.SPRITE_MAPPING.keys())

    for i in range(num_candidates):
        # Choose a random, not-yet-used first name
        first_name_chosen = random.choice(pool_first_names)
        attempt_count = 0
        while (first_name_chosen in used_first_names and attempt_count < 100
               and len(used_first_names) < len(pool_first_names)):
            first_name_chosen = random.choice(pool_first_names)
            attempt_count += 1
        used_first_names.add(first_name_chosen)

        # Choose a random, not-yet-used surname
        surname_chosen = random.choice(pool_surnames)
        attempt_count = 0
        while (surname_chosen in used_surnames and attempt_count < 100
               and len(used_surnames) < len(pool_surnames)):
            surname_chosen = random.choice(pool_surnames)
            attempt_count += 1
        used_surnames.add(surname_chosen)

        full_name = f"{first_name_chosen} {surname_chosen}"

        # Assign random attributes to the candidate
        attributes = {
            "administrative_experience":
            random.randint(*config.ATTRIBUTE_RANGE),
            "social_vision": random.randint(*config.ATTRIBUTE_RANGE),
            "mediation_ability": random.randint(*config.ATTRIBUTE_RANGE),
            "ethical_integrity": random.randint(*config.ATTRIBUTE_RANGE),
        }

        # Add sprite key assignment based on gender guess and available sprites
        sprite_key = None
        first_name = full_name.split(' ')[0]

        # Determine gender guess
        is_female = any(name in first_name for name in data.FEMALE_FIRST_NAMES)
        is_male = any(name in first_name for name in data.MALE_FIRST_NAMES)

        # Try to find a suitable standing sprite key based on gender
        suitable_keys = []
        if is_female:
            suitable_keys = [
                key for key in available_sprite_keys
                if key.startswith("female_")
            ]
        elif is_male:
            suitable_keys = [
                key for key in available_sprite_keys if key.startswith("male_")
            ]

        if suitable_keys:
            sprite_key = random.choice(
                suitable_keys)  # Pick a random suitable standing sprite
        elif available_sprite_keys:  # Fallback: if gender match fails, pick any standing sprite if available
            sprite_key = random.choice(available_sprite_keys)
        # Fallback: use default if no standing sprites matched/available
        elif "default_standing" in data.SPRITE_MAPPING:
            sprite_key = "default_standing"
        elif data.SPRITE_MAPPING:  # If no standing, just pick the first defined sprite key if any exist
            try:
                sprite_key = list(data.SPRITE_MAPPING.keys())[0]
            except Exception:
                sprite_key = None

        candidates.append({
            "name": full_name,
            "attributes": attributes,
            "sprite_key": sprite_key
        })  # Add sprite_key

    # Fallback if the requested number of candidates exceeds the unique name/surname combination pool
    while len(candidates) < num_candidates:
        full_name = f"Generic Candidate {len(candidates)+1}"
        attributes = {
            "administrative_experience":
            random.randint(*config.ATTRIBUTE_RANGE),
            "social_vision": random.randint(*config.ATTRIBUTE_RANGE),
            "mediation_ability": random.randint(*config.ATTRIBUTE_RANGE),
            "ethical_integrity": random.randint(*config.ATTRIBUTE_RANGE),
        }
        # Assign a sprite key even to fallback candidates (using same logic)
        sprite_key = None
        if available_sprite_keys:
            sprite_key = random.choice(available_sprite_keys)
        elif "default_standing" in data.SPRITE_MAPPING:
            sprite_key = "default_standing"
        elif data.SPRITE_MAPPING:
            try:
                sprite_key = list(data.SPRITE_MAPPING.keys())[0]
            except Exception:
                sprite_key = None

        candidates.append({
            "name": full_name,
            "attributes": attributes,
            "sprite_key": sprite_key
        })

    return candidates


def generate_grand_electors(num_electors):
    """Generates a list of identifiers for the Grand Electors with assigned traits."""
    electors = []
    for i in range(num_electors):
        elector_id = f"Elector_{i+1}"
        # Assegna tratti casuali agli elettori
        assigned_traits = random.sample(
            config.ELECTOR_TRAITS,
            min(config.ELECTOR_TRAIT_COUNT, len(config.ELECTOR_TRAITS)))
        electors.append({"id": elector_id, "traits": assigned_traits})
    return electors
