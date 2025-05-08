# config.py
# In config.py

import random

# --- Simulation Configuration ---

# NUM_GRAND_ELECTORS sarà un numero casuale >= 100 e multiplo di 12
_min_grand_electors = 100
# Esempio: fino a 20*12. Range per la casualità iniziale.
_max_grand_electors = 240
_raw_grand_electors = random.randint(_min_grand_electors, _max_grand_electors)
TARGET_DIVISOR_ELECTORS = 12

if _raw_grand_electors % TARGET_DIVISOR_ELECTORS != 0:
    # Prova ad aumentare al prossimo multiplo
    increased_electors = (_raw_grand_electors //
                          TARGET_DIVISOR_ELECTORS + 1) * TARGET_DIVISOR_ELECTORS
    # Prova a diminuire al precedente multiplo
    decreased_electors = (_raw_grand_electors //  # Corrected variable name here
                          TARGET_DIVISOR_ELECTORS) * TARGET_DIVISOR_ELECTORS

    if decreased_electors < _min_grand_electors:
        NUM_GRAND_ELECTORS = increased_electors
    else:
        if (_raw_grand_electors - decreased_electors) <= (increased_electors - _raw_grand_electors):
            NUM_GRAND_ELECTORS = decreased_electors
        else:
            NUM_GRAND_ELECTORS = increased_electors
else:
    NUM_GRAND_ELECTORS = _raw_grand_electors

if NUM_GRAND_ELECTORS < _min_grand_electors:  # Assicurazione finale
    NUM_GRAND_ELECTORS = ((_min_grand_electors + TARGET_DIVISOR_ELECTORS - 1) //
                          TARGET_DIVISOR_ELECTORS) * TARGET_DIVISOR_ELECTORS

MIN_ELECTOR_AGE = 20
CANDIDATE_AGE_RANGE = (30, 75)  # NUOVO: Range età candidati (min, max)
PARTY_IDS = ["Reds", "Blues", "Greens", "Golds",
             "Independent"]  # NUOVO: Possibili partiti
# NUOVO: Pesi per assegnazione casuale (somma a 1)
PARTY_ID_ASSIGNMENT_WEIGHTS = [0.25, 0.25, 0.15, 0.15, 0.20]

# Configuration Phase 1: District Elections
# Distretti casuali, almeno 10, ma legati anche a NUM_GRAND_ELECTORS
NUM_DISTRICTS = random.randint(10, max(12, NUM_GRAND_ELECTORS // 6))
CANDIDATES_PER_DISTRICT = random.randint(10, 20)
CITIZENS_PER_DISTRICT = random.randint(1000, 10000)
INFLUENCE_CITIZENS_PER_CANDIDATE = random.randint(
    30, min(100, CITIZENS_PER_DISTRICT // 10))


# Configuration Phase 2: Governor Election (College of Grand Electors)
MAX_NORMAL_ROUNDS = random.randint(10, 15)
# Maggioranza leggermente variabile
REQUIRED_MAJORITY = random.uniform(0.6, 0.7)
# Manteniamo fisso per il 4° tentativo come da logica originale
REQUIRED_MAJORITY_ATTEMPT_4 = 0.5
GOVERNOR_PAUSE_SECONDS = 0.3  # Pausa leggermente ridotta per dinamismo GUI
# Anche i round totali possono variare un po'
MAX_TOTAL_ROUNDS = MAX_NORMAL_ROUNDS + random.randint(20, 30)

# Numero di candidati riportati (mantenuto a 0 come da file originale per evitare errori di configurazione con la divisibilità,
# a meno che la logica di gestione del carry-over e della divisibilità non venga ulteriormente raffinata)
NUM_PRESELECTED_CANDIDATES = 0
PRESELECTED_CANDIDATE_BOOST = random.uniform(4.0, 6.0)
RUNOFF_CARRYOVER_LEANING_BONUS = random.uniform(1.5, 2.5)

MAX_ELECTION_ATTEMPTS = 6

STEP_BY_STEP_MODE_DEFAULT = False

# --- Network Configuration (NUOVO) ---
USE_SOCIAL_NETWORK = True  # Imposta a True per attivare l'influenza della rete
# Parametri per Watts-Strogatz Small-World Graph:
# k: Ogni elettore è inizialmente connesso a k vicini più prossimi (numero pari)
NETWORK_AVG_NEIGHBORS = 6
# p: Probabilità di riconnettere un arco a un nodo casuale
NETWORK_REWIRING_PROB = 0.1

# Parametri per Influenza Sociale (Modello Media Pesata)
# Alpha: Quanto peso viene dato alla media dei vicini (0=nessuna influenza, 1=solo vicini)
SOCIAL_INFLUENCE_STRENGTH = 0.05
SOCIAL_INFLUENCE_ITERATIONS = 1   # Quante volte applicare l'influenza per round
# Fattore che influenza quanto l'esposizione all'influenza sociale modifica i pesi delle preferenze (es. identity_weight)
SOCIAL_INFLUENCE_LEARNING_EFFECT = random.uniform(0.01, 0.05)


### AI INTEGRATION ###
# Grand Elector "AI" voting parameters
ATTRIBUTE_RANGE = (1, 5)
ELECTOR_IDEAL_PREFERENCE_RANGE = (1, 5)
# NUOVI Parametri per Media Literacy
MEDIA_LITERACY_RANGE = (1, 5)  # Range del punteggio (1=Basso, 5=Alto)
# Fattore di effetto: quanto la literacy riduce l'impatto/suscettibilità.
# Es: 0.2 significa che max literacy (normalizzata a 1) riduce l'effetto del 20%.
MEDIA_LITERACY_EFFECT_FACTOR = random.uniform(0.1, 0.3)
ELECTOR_ATTRIBUTE_MISMATCH_PENALTY_FACTOR = random.uniform(0.3, 0.7)
MAX_ELECTOR_LEANING_BASE = random.randint(8, 12)
# NUOVO: Range per il peso dato all'identità (vs policy)
IDENTITY_WEIGHT_RANGE = (0.1, 0.8)
# NUOVO: Fattore del bonus massimo per corrispondenza partito (es. 0.6 => 60% di MAX_ELECTOR_LEANING_BASE)
IDENTITY_MATCH_BONUS_FACTOR = 0.6
ELECTOR_RANDOM_LEANING_VARIANCE = random.uniform(0.5, 1.5)
ELECTOR_MOMENTUM_FACTOR = random.uniform(
    0.1, 0.25)  # Aumentata la possibile variabilità

# Range ampliato per maggiore specializzazione
ELECTOR_ATTRIBUTE_WEIGHT_RANGE = (0, 7)
ELECTOR_TRAITS = [
    "Loyal", "Pragmatic", "Idealistic", "Swing Voter", "Risk-Averse",
    "Easily Influenced", "Bandwagoner", "Contrarian", "AntiEstablishment",
    "CharismaFocused", "Underdog Supporter", "Confirmation Prone",
    "Motivated Reasoner", "Strong Partisan"
    # Potremmo aggiungere un tratto "Media Savvy" che aumenta la literacy? Per ora no.
]
# Aumentato leggermente max numero tratti
ELECTOR_TRAIT_COUNT = random.randint(1, 6)
# NUOVO: Range per il peso dato all'identità (vs policy)
IDENTITY_WEIGHT_RANGE = (0.1, 0.8)
# NUOVO: Fattore del bonus massimo per corrispondenza partito (es. 0.6 => 60% di MAX_ELECTOR_LEANING_BASE)
IDENTITY_MATCH_BONUS_FACTOR = 0.6

# Elector Trait Modifiers
ELECTOR_SUSCEPTIBILITY_BASE = random.uniform(
    0.4, 0.6)  # Base suscettibilità resa casuale
INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED = random.uniform(1.8, 2.5)
INFLUENCE_TRAIT_MULTIPLIER_LOYAL = random.uniform(0.3, 0.6)

# Strategic Voting Parameters
STRATEGIC_VOTING_START_ROUND = random.randint(2, 5)
UNLIKELY_TO_WIN_THRESHOLD = random.uniform(0.05, 0.15)
STRATEGIC_VOTING_TRAIT_MULTIPLIER_PRAGMATIC = random.uniform(1.3, 1.7)
STRATEGIC_VOTING_TRAIT_MULTIPLIER_IDEALISTIC = random.uniform(0.6, 0.9)
STRATEGIC_VOTING_TRAIT_PENALTY_IDEALISTIC_INTEGRITY = random.uniform(1.8, 2.5)
STRONGLY_DISLIKED_THRESHOLD_FACTOR = random.uniform(0.2, 0.4)
# NUOVO: Soglia per identificare elettori swing
ELECTOR_SWING_THRESHOLD = random.uniform(0.5, 1.5)

# Cognitive Bias Parameters
BANDWAGON_EFFECT_FACTOR = random.uniform(0.1, 0.25)
UNDERDOG_EFFECT_FACTOR = random.uniform(0.1, 0.25)
MAX_BIAS_LEANING_ADJUSTMENT = random.uniform(0.8, 1.8)
CONFIRMATION_BIAS_FACTOR = random.uniform(1.1, 1.4)
# NUOVO: Fattore di riduzione per info incongruenti (es. 0.6 => riduce del 60%)
MOTIVATED_REASONING_FACTOR = random.uniform(0.3, 0.6)

# Candidate Campaign Parameters
INFLUENCE_ELECTORS_PER_CANDIDATE = random.randint(max(
    10, NUM_GRAND_ELECTORS // 10), max(20, NUM_GRAND_ELECTORS // 4))  # Dinamico con NUM_GRAND_ELECTORS
CAMPAIGN_INFLUENCE_CHANCE = random.uniform(
    0.6, 0.85)  # Aumentata chance massima
INFLUENCE_STRENGTH_FACTOR = random.uniform(
    0.08, 0.18)  # Aumentata possibile forza

CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE = random.uniform(0.4, 0.7)

INITIAL_CAMPAIGN_BUDGET = random.randint(700, 1500)
_min_alloc = random.randint(1, 10)
_max_alloc = random.randint(40, 80)
if _min_alloc > _max_alloc:
    _min_alloc = _max_alloc - 1 if _max_alloc > 1 else 1  # Assicura min <= max
CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE = (_min_alloc, _max_alloc)

CAMPAIGN_ALLOCATION_INFLUENCE_FACTOR = random.uniform(0.03, 0.08)
CAMPAIGN_ALLOCATION_SUCCESS_CHANCE_FACTOR = random.uniform(0.003, 0.008)
MAX_CAMPAIGN_INFLUENCE_PER_ATTEMPT = random.uniform(2.0, 4.0)
# NUOVO: Per normalizzare il potential score nell'allocazione budget
MAX_TARGETING_POTENTIAL_SCORE = 25.0

# --- Competitive Adaptation Parameters (NUOVO) ---
# Quanto i candidati si concentrano sui propri punti di forza (0=solo attacco, 1=solo forza)
COMPETITIVE_ADAPTATION_SELF_FOCUS_FACTOR = random.uniform(0.4, 0.7)
# Quanto l'analisi competitiva influenza la selezione dei temi
COMPETITIVE_ADAPTATION_IMPACT = random.uniform(0.3, 0.6)
# Quanti avversari principali vengono considerati nell'analisi
COMPETITIVE_ADAPTATION_TOP_OPPONENTS = 2

# --- Elector Learning Parameters (NUOVO) ---
# Tasso di apprendimento: determina la magnitudo dei cambiamenti per round
ELECTOR_LEARNING_RATE = random.uniform(0.01, 0.05)
# Fattore che influenza quanto l'esposizione alla campagna modifica i pesi delle preferenze (es. identity_weight)
CAMPAIGN_EXPOSURE_LEARNING_EFFECT = random.uniform(0.02, 0.08)


### CITIZEN AI INTEGRATION (for District Elections) ###
CITIZEN_IDEAL_PREFERENCE_RANGE = (1, 5)
CITIZEN_ATTRIBUTE_MISMATCH_PENALTY_FACTOR = random.uniform(
    0.6, 0.9)  # Cittadini più sensibili
MAX_CITIZEN_LEANING_BASE = random.randint(4, 6)
CITIZEN_RANDOM_LEANING_VARIANCE = random.uniform(0.3, 0.7)

CITIZEN_TRAITS = ["Attribute Focused", "Random Inclined",
                  "Locally Loyal"]  # Esempio nuovo tratto
# Mantenuto a 1 per semplicità, ma può essere random.randint(0,1) o (1,2)
CITIZEN_TRAIT_COUNT = 1

CITIZEN_SUSCEPTIBILITY_BASE = random.uniform(0.7, 0.9)
CITIZEN_TRAIT_MULTIPLIER_RANDOM_INCLINED = random.uniform(1.3, 1.7)
# Lasciato a 1, la loro logica è nel voto
CITIZEN_TRAIT_MULTIPLIER_ATTRIBUTE_FOCUSED = 1.0
CITIZEN_TRAIT_RANDOM_INCLINED_BIAS = random.uniform(0.8, 1.5)


# --- Pygame Configuration ---
PIXEL_FONT_SIZE = 18
BLOCK_SIZE = 10  # Sembra non utilizzato, ma presente nel file originale

# NUOVE COSTANTI PER GLI SPRITE:
SPRITE_WIDTH = 32  # Modifica questo valore alla larghezza effettiva dei tuoi sprite
SPRITE_HEIGHT = 32  # Modifica questo valore all'altezza effettiva dei tuoi sprite

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)  # Blu standard
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_BLUE = (173, 216, 230)  # Azzurro chiaro (già presente)
PINK = (255, 182, 193)       # Rosa chiaro (NUOVO)

BG_COLOR = DARK_GRAY

WINDOW_TITLE = "Anthalys Governor Election Simulation"

# Image Paths
IMAGE_PATHS = {
    "character_male_dark": "assets/characters/darkmale.png",
    # Assicurati che questo file esista
    "character_male_light": "assets/characters/lightmale.png",
    "character_female_dark": "assets/characters/darkfemale.png",
    "character_female_light": "assets/characters/lightfemale.png",
    # Assicurati che questo file esista
    "character_male_tanned": "assets/characters/maletanned.png",
    # Assicurati che questo file esista
    "character_male_tanned2": "assets/characters/maletanned2.png",
    # Assicurati che questo file esista
    "character_female_tanned": "assets/characters/femaletanned.png",
    # Assicurati che questo file esista
    "character_female_tanned2": "assets/characters/femaletanned2.png",
}

# Event Parameters
EVENT_SCANDAL_PROB_FACTOR_INTEGRITY_DIFF = random.uniform(
    0.015, 0.035)  # Range leggermente più ampio
EVENT_ETHICS_DEBATE_PROB_FACTOR_INTEGRITY_DIFF = random.uniform(
    0.008, 0.02)  # Range leggermente più ampio
EVENT_ETHICS_DEBATE_IMPACT = random.uniform(
    0.08, 0.15)  # Range leggermente più ampio

# Nuovi parametri per eventi (da usare in election.py)
# Esempio: probabilità base per un nuovo evento "Positive Endorsement"
EVENT_ENDORSEMENT_BASE_PROB = 0.05
# Esempio: impatto di un endorsement
# Influenza sull'orientamento (leaning)
EVENT_ENDORSEMENT_IMPACT_RANGE = (0.1, 0.3)

# Variabile globale per il tema caldo corrente, può essere None
CURRENT_HOT_TOPIC = None
# CURRENT_HOT_TOPIC può essere una stringa tipo "social_vision", "ethical_integrity", etc.
# Viene impostato da eventi casuali in election.py
