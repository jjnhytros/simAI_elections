# config.py
import random

# ==============================================================================
# --- CORE SIMULATION SETUP ---
# ==============================================================================
_min_grand_electors = 100
_max_grand_electors = 240
TARGET_DIVISOR_ELECTORS = 12
_raw_grand_electors = random.randint(_min_grand_electors, _max_grand_electors)
if _raw_grand_electors % TARGET_DIVISOR_ELECTORS != 0:
    increased_electors = (_raw_grand_electors // TARGET_DIVISOR_ELECTORS +
                          1) * TARGET_DIVISOR_ELECTORS
    decreased_electors = (_raw_grand_electors //
                          TARGET_DIVISOR_ELECTORS) * TARGET_DIVISOR_ELECTORS
    if decreased_electors < _min_grand_electors:
        NUM_GRAND_ELECTORS = increased_electors
    else:
        NUM_GRAND_ELECTORS = decreased_electors if (
            _raw_grand_electors - decreased_electors) <= (
                increased_electors -
                _raw_grand_electors) else increased_electors
else:
    NUM_GRAND_ELECTORS = _raw_grand_electors
if NUM_GRAND_ELECTORS < _min_grand_electors:
    NUM_GRAND_ELECTORS = (
        (_min_grand_electors + TARGET_DIVISOR_ELECTORS - 1) //
        TARGET_DIVISOR_ELECTORS) * TARGET_DIVISOR_ELECTORS
MAX_ELECTION_ATTEMPTS = 6

# ==============================================================================
# --- CANDIDATE PROPERTIES & GENERATION ---
# ==============================================================================
CANDIDATE_AGE_RANGE = (20, 45)
ATTRIBUTE_RANGE = (1, 5)
PARTY_IDS = ["Reds", "Blues", "Greens", "Golds", "Independent"]
PARTY_ID_ASSIGNMENT_WEIGHTS = [0.25, 0.25, 0.15, 0.15, 0.20]
INITIAL_CAMPAIGN_BUDGET = random.randint(700, 1500)
NUM_PRESELECTED_CANDIDATES = 0
PRESELECTED_CANDIDATE_BOOST = random.uniform(4.0, 6.0)
RUNOFF_CARRYOVER_LEANING_BONUS = random.uniform(1.5, 2.5)

# ==============================================================================
# --- ELECTOR/CITIZEN PROPERTIES & AI ---
# ==============================================================================
MIN_ELECTOR_AGE = 20
ELECTOR_IDEAL_PREFERENCE_RANGE = (1, 5)
ELECTOR_ATTRIBUTE_WEIGHT_RANGE = (0, 7)
ELECTOR_ATTRIBUTE_MISMATCH_PENALTY_FACTOR = random.uniform(0.3, 0.7)
MAX_ELECTOR_LEANING_BASE = random.randint(8, 12)
ELECTOR_RANDOM_LEANING_VARIANCE = random.uniform(0.5, 1.5)
# ELECTOR_MOMENTUM_FACTOR = random.uniform(0.1, 0.25) # Apparentemente non usato
IDENTITY_WEIGHT_RANGE = (0.1, 0.8)
IDENTITY_MATCH_BONUS_FACTOR = 0.6
ELECTOR_TRAITS = [
    "Loyal", "Pragmatic", "Idealistic", "Swing Voter", "Risk-Averse",
    "Easily Influenced", "Bandwagoner", "Contrarian", "AntiEstablishment",
    "CharismaFocused", "Underdog Supporter", "Confirmation Prone",
    "Motivated Reasoner", "Strong Partisan"
]
ELECTOR_TRAIT_COUNT = random.randint(1, 6)
ELECTOR_SUSCEPTIBILITY_BASE = random.uniform(0.4, 0.6)
INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED = random.uniform(1.8, 2.5)
INFLUENCE_TRAIT_MULTIPLIER_LOYAL = random.uniform(0.3, 0.6)
STRATEGIC_VOTING_START_ROUND = random.randint(2, 5)
UNLIKELY_TO_WIN_THRESHOLD = random.uniform(0.05, 0.15)
STRATEGIC_VOTING_TRAIT_MULTIPLIER_PRAGMATIC = random.uniform(1.3, 1.7)
STRATEGIC_VOTING_TRAIT_MULTIPLIER_IDEALISTIC = random.uniform(0.6, 0.9)
STRATEGIC_VOTING_TRAIT_PENALTY_IDEALISTIC_INTEGRITY = random.uniform(1.8, 2.5)
STRONGLY_DISLIKED_THRESHOLD_FACTOR = random.uniform(0.2, 0.4)
ELECTOR_SWING_THRESHOLD = random.uniform(0.5, 1.5)
BANDWAGON_EFFECT_FACTOR = random.uniform(0.1, 0.25)
UNDERDOG_EFFECT_FACTOR = random.uniform(0.1, 0.25)
MAX_BIAS_LEANING_ADJUSTMENT = random.uniform(0.8, 1.8)
CONFIRMATION_BIAS_FACTOR = random.uniform(1.1, 1.4)
MOTIVATED_REASONING_FACTOR = random.uniform(0.3, 0.6)
MEDIA_LITERACY_RANGE = (1, 5)
MEDIA_LITERACY_EFFECT_FACTOR = random.uniform(0.1, 0.3)
ELECTOR_LEARNING_RATE = random.uniform(0.01, 0.05)
CAMPAIGN_EXPOSURE_LEARNING_EFFECT = random.uniform(0.02, 0.08)
SOCIAL_INFLUENCE_LEARNING_EFFECT = random.uniform(0.01, 0.05)
# Citizen Params
CITIZEN_IDEAL_PREFERENCE_RANGE = (1, 5)
CITIZEN_ATTRIBUTE_MISMATCH_PENALTY_FACTOR = random.uniform(0.6, 0.9)
MAX_CITIZEN_LEANING_BASE = random.randint(4, 6)
CITIZEN_RANDOM_LEANING_VARIANCE = random.uniform(0.3, 0.7)
CITIZEN_TRAITS = ["Attribute Focused", "Random Inclined", "Locally Loyal"]
CITIZEN_TRAIT_COUNT = 1
CITIZEN_SUSCEPTIBILITY_BASE = random.uniform(0.7, 0.9)
CITIZEN_TRAIT_MULTIPLIER_RANDOM_INCLINED = random.uniform(1.3, 1.7)
CITIZEN_TRAIT_MULTIPLIER_ATTRIBUTE_FOCUSED = 1.0
CITIZEN_TRAIT_RANDOM_INCLINED_BIAS = random.uniform(0.8, 1.5)

# ==============================================================================
# --- PHASE 1: DISTRICT ELECTIONS ---
# ==============================================================================
NUM_DISTRICTS = random.randint(10, max(12, NUM_GRAND_ELECTORS // 6))
CANDIDATES_PER_DISTRICT = random.randint(10, 20)
CITIZENS_PER_DISTRICT = random.randint(1000, 10000)
INFLUENCE_CITIZENS_PER_CANDIDATE = random.randint(
    30, min(100, CITIZENS_PER_DISTRICT // 10))

# ==============================================================================
# --- PHASE 2: GOVERNOR ELECTION (COLLEGE) ---
# ==============================================================================
MAX_NORMAL_ROUNDS = random.randint(10, 15)
REQUIRED_MAJORITY = random.uniform(0.6, 0.7)
REQUIRED_MAJORITY_ATTEMPT_4 = 0.5  # Soglia ridotta per tentativi successivi
MAX_TOTAL_ROUNDS = MAX_NORMAL_ROUNDS + random.randint(20, 30)
GOVERNOR_PAUSE_SECONDS = 0.3

# ==============================================================================
# --- CAMPAIGN DYNAMICS ---
# ==============================================================================
INFLUENCE_ELECTORS_PER_CANDIDATE = random.randint(
    max(10, NUM_GRAND_ELECTORS // 10), max(20, NUM_GRAND_ELECTORS // 4))
# CAMPAIGN_INFLUENCE_CHANCE = random.uniform(0.6, 0.85) # Non più usato direttamente
INFLUENCE_STRENGTH_FACTOR = random.uniform(0.08, 0.18)
CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE = random.uniform(0.4, 0.7)
# Budget Allocation
_min_alloc = random.randint(1, 10)
_max_alloc = random.randint(40, 80)
if _min_alloc > _max_alloc:
    _min_alloc = _max_alloc - 1 if _max_alloc > 1 else 1
CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE = (_min_alloc, _max_alloc)
CAMPAIGN_ALLOCATION_INFLUENCE_FACTOR = random.uniform(0.03, 0.08)
CAMPAIGN_ALLOCATION_SUCCESS_CHANCE_FACTOR = random.uniform(0.003, 0.008)
MAX_CAMPAIGN_INFLUENCE_PER_ATTEMPT = random.uniform(2.0, 4.0)
# Rendimenti Decrescenti
DIMINISHING_RETURNS_EXPONENT_PER_ATTEMPT = random.uniform(0.6, 0.85)

# ==============================================================================
# --- COMPETITIVE ADAPTATION (CAMPAIGN AI) ---
# ==============================================================================
COMPETITIVE_ADAPTATION_SELF_FOCUS_FACTOR = random.uniform(0.4, 0.7)
# COMPETITIVE_ADAPTATION_IMPACT = random.uniform(0.3, 0.6) # Non usato direttamente?
COMPETITIVE_ADAPTATION_TOP_OPPONENTS = 2
TARGETING_KEY_ELECTOR_BONUS_FACTOR = random.uniform(1.5, 2.5)

# ==============================================================================
# --- SOCIAL NETWORK ---
# ==============================================================================
USE_SOCIAL_NETWORK = True
NETWORK_AVG_NEIGHBORS = 6
NETWORK_REWIRING_PROB = 0.1
SOCIAL_INFLUENCE_STRENGTH = 0.05
SOCIAL_INFLUENCE_ITERATIONS = 1

# ==============================================================================
# --- EVENTS ---
# ==============================================================================
CURRENT_HOT_TOPIC = None
EVENT_SCANDAL_PROB_FACTOR_INTEGRITY_DIFF = random.uniform(0.015, 0.035)
EVENT_SCANDAL_IMPACT = random.uniform(1.0, 3.0)
EVENT_ETHICS_DEBATE_PROB_FACTOR_INTEGRITY_DIFF = random.uniform(0.008, 0.02)
EVENT_ETHICS_DEBATE_IMPACT = random.uniform(0.08, 0.15)
EVENT_ENDORSEMENT_BASE_PROB = 0.05
EVENT_ENDORSEMENT_IMPACT_RANGE = (0.1, 0.3)
EVENT_DEBATE_BASE_PROB = 0.08
EVENT_DEBATE_IMPACT_FACTOR = random.uniform(0.3, 0.8)
EVENT_DEBATE_NUM_PARTICIPANTS = random.randint(3, 5)
EVENT_RALLY_BASE_PROB = 0.10
EVENT_RALLY_IMPACT_FACTOR = random.uniform(0.4, 0.9)
EVENT_RALLY_BUDGET_COST = random.randint(20, 60)
EVENT_RALLY_FAVORABLE_THRESHOLD_FACTOR = 0.6
EVENT_RALLY_OPPOSED_THRESHOLD_FACTOR = 0.3

# ==============================================================================
# --- MEDIA ECOSYSTEM ---
# ==============================================================================
MEDIA_OUTLETS = [
    {"id": "Progressive Post", "bias_spectrum": -0.7, "reach": 0.35, "credibility": 0.8,
        "preferred_topics": ["social_vision", "ethical_integrity"]},
    {"id": "Central Times", "bias_spectrum": 0.0, "reach": 0.50, "credibility": 0.9,
        "preferred_topics": ["administrative_experience", "mediation_ability"]},
    {"id": "Conservative Chronicle", "bias_spectrum": 0.8, "reach": 0.30, "credibility": 0.75,
        "preferred_topics": ["administrative_experience", "ethical_integrity"]},
    {"id": "NetFeed Opinion", "bias_spectrum": -0.9, "reach": 0.60, "credibility": 0.4,  # Esempio più estremo
        "preferred_topics": []},  # Nessun focus specifico, copre tutto?
    {"id": "Local Bulletin", "bias_spectrum": random.uniform(-0.2, 0.2), "reach": 0.20, "credibility": 0.6,
        "preferred_topics": ["mediation_ability"]}  # Esempio media locale
]
# Fattori per calcolo influenza media
MEDIA_BIAS_FACTOR = 0.6  # Quanto il bias influenza la valutazione (0-1)
# Moltiplicatore impatto se bias allineati (Elettore-Fonte)
MEDIA_CONFIRMATION_BIAS_FACTOR = 1.6
# Moltiplicatore impatto se bias opposti (Elettore-Fonte)
MEDIA_OPPOSING_BIAS_FACTOR = 0.4
# Scala impatto base in base a credibilità fonte (0-1)
MEDIA_CREDIBILITY_FACTOR = 1.0
MEDIA_IMPACT_SCALE = 0.25  # Fattore scala generale per impatto media sui leanings

# ==============================================================================
# --- DATABASE ---
# ==============================================================================
DATABASE_FILE = 'simai.db'

# ==============================================================================
# --- GUI / PYGAME ---
# ==============================================================================
STEP_BY_STEP_MODE_DEFAULT = False
PIXEL_FONT_SIZE = 18
# BLOCK_SIZE = 10 # Apparentemente non usato
SPRITE_WIDTH = 32
SPRITE_HEIGHT = 32
# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_BLUE = (173, 216, 230)
PINK = (255, 182, 193)
BG_COLOR = DARK_GRAY
WINDOW_TITLE = "Anthalys Governor Election Simulation"
IMAGE_PATHS = {  # Assicurati che questi percorsi siano corretti
    "character_male_dark": "assets/characters/darkmale.png",
    "character_male_light": "assets/characters/lightmale.png",
    "character_female_dark": "assets/characters/darkfemale.png",
    "character_female_light": "assets/characters/lightfemale.png",
    "character_male_tanned": "assets/characters/maletanned.png",
    "character_male_tanned2": "assets/characters/maletanned2.png",
    "character_female_tanned": "assets/characters/femaletanned.png",
    "character_female_tanned2": "assets/characters/femaletanned2.png",
}

# --- NESSUNA SEZIONE IA e LLM QUI ---
