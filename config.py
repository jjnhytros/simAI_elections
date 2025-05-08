# config.py
import random

# ==============================================================================
# --- CORE SIMULATION SETUP ---
# ==============================================================================

# Number of Grand Electors (random, multiple of 12)
_min_grand_electors = 100
_max_grand_electors = 240
TARGET_DIVISOR_ELECTORS = 12

_raw_grand_electors = random.randint(_min_grand_electors, _max_grand_electors)

# Ensure NUM_GRAND_ELECTORS is a multiple of TARGET_DIVISOR_ELECTORS
if _raw_grand_electors % TARGET_DIVISOR_ELECTORS != 0:
    increased_electors = (_raw_grand_electors //
                          TARGET_DIVISOR_ELECTORS + 1) * TARGET_DIVISOR_ELECTORS
    decreased_electors = (_raw_grand_electors //
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

# Final check to ensure minimum is met
if NUM_GRAND_ELECTORS < _min_grand_electors:
    NUM_GRAND_ELECTORS = ((_min_grand_electors + TARGET_DIVISOR_ELECTORS - 1) //
                          TARGET_DIVISOR_ELECTORS) * TARGET_DIVISOR_ELECTORS

MAX_ELECTION_ATTEMPTS = 6  # Total attempts before deadlock failure

# ==============================================================================
# --- CANDIDATE PROPERTIES & GENERATION ---
# ==============================================================================

CANDIDATE_AGE_RANGE = (20, 45)  # Range età candidati (min, max)
# Range for candidate attributes (e.g., experience, integrity)
ATTRIBUTE_RANGE = (1, 5)

PARTY_IDS = ["Reds", "Blues", "Greens",
             "Golds", "Independent"]  # Possible parties
# Weights for random assignment (sum to 1)
PARTY_ID_ASSIGNMENT_WEIGHTS = [0.25, 0.25, 0.15, 0.15, 0.20]

INITIAL_CAMPAIGN_BUDGET = random.randint(
    700, 1500)  # Initial budget for candidates

# Parameters for carrying over candidates in case of deadlock
# Number of candidates automatically advanced (currently 0)
NUM_PRESELECTED_CANDIDATES = 0
# Leaning bonus for pre-selected candidates
PRESELECTED_CANDIDATE_BOOST = random.uniform(4.0, 6.0)
# Leaning bonus for runoff winner carried over
RUNOFF_CARRYOVER_LEANING_BONUS = random.uniform(1.5, 2.5)

# ==============================================================================
# --- ELECTOR/CITIZEN PROPERTIES & AI ---
# ==============================================================================

MIN_ELECTOR_AGE = 20  # Minimum age for Grand Electors

# Elector (College) AI Parameters
# Range for elector ideal preferences on attributes
ELECTOR_IDEAL_PREFERENCE_RANGE = (1, 5)
# Range for weights electors give to attributes
ELECTOR_ATTRIBUTE_WEIGHT_RANGE = (0, 7)

ELECTOR_ATTRIBUTE_MISMATCH_PENALTY_FACTOR = random.uniform(
    0.3, 0.7)  # How much attribute mismatch reduces leaning
MAX_ELECTOR_LEANING_BASE = random.randint(
    8, 12)  # Base maximum possible leaning score
ELECTOR_RANDOM_LEANING_VARIANCE = random.uniform(
    0.5, 1.5)  # Random noise in initial leanings
# How much previous results influence leaning
ELECTOR_MOMENTUM_FACTOR = random.uniform(0.1, 0.25)

# Identity vs. Policy Voting
# Range for the weight given to identity (vs policy)
IDENTITY_WEIGHT_RANGE = (0.1, 0.8)
# Factor for the bonus for matching party identity
IDENTITY_MATCH_BONUS_FACTOR = 0.6

# Elector Traits (College)
ELECTOR_TRAITS = [
    "Loyal", "Pragmatic", "Idealistic", "Swing Voter", "Risk-Averse",
    "Easily Influenced", "Bandwagoner", "Contrarian", "AntiEstablishment",
    "CharismaFocused", "Underdog Supporter", "Confirmation Prone",
    "Motivated Reasoner", "Strong Partisan"
]
# Number of traits assigned to each elector
ELECTOR_TRAIT_COUNT = random.randint(1, 6)

# Elector Trait Modifiers
ELECTOR_SUSCEPTIBILITY_BASE = random.uniform(
    0.4, 0.6)  # Base susceptibility to influence
INFLUENCE_TRAIT_MULTIPLIER_EASILY_INFLUENCED = random.uniform(
    1.8, 2.5)  # Easily Influenced trait multiplier
# Loyal trait multiplier (applied to influence *against* their party)
INFLUENCE_TRAIT_MULTIPLIER_LOYAL = random.uniform(0.3, 0.6)

# Strategic Voting Parameters
STRATEGIC_VOTING_START_ROUND = random.randint(
    2, 5)  # Round when strategic voting starts
# Vote share below which a candidate is unlikely to win
UNLIKELY_TO_WIN_THRESHOLD = random.uniform(0.05, 0.15)
STRATEGIC_VOTING_TRAIT_MULTIPLIER_PRAGMATIC = random.uniform(
    1.3, 1.7)  # Pragmatic trait effect on strategic voting
STRATEGIC_VOTING_TRAIT_MULTIPLIER_IDEALISTIC = random.uniform(
    0.6, 0.9)  # Idealistic trait effect on strategic voting
STRATEGIC_VOTING_TRAIT_PENALTY_IDEALISTIC_INTEGRITY = random.uniform(
    1.8, 2.5)  # Idealistic trait penalty for low integrity candidates
# How low leaning must be to strongly dislike a candidate
STRONGLY_DISLIKED_THRESHOLD_FACTOR = random.uniform(0.2, 0.4)
# Threshold for identifying swing voters
ELECTOR_SWING_THRESHOLD = random.uniform(0.5, 1.5)

# Cognitive Bias Parameters
BANDWAGON_EFFECT_FACTOR = random.uniform(
    0.1, 0.25)  # Strength of the bandwagon effect
UNDERDOG_EFFECT_FACTOR = random.uniform(
    0.1, 0.25)  # Strength of the underdog effect
MAX_BIAS_LEANING_ADJUSTMENT = random.uniform(
    0.8, 1.8)  # Maximum leaning adjustment from biases
# Strength of confirmation bias (amplifies congruent info, reduces incongruent)
CONFIRMATION_BIAS_FACTOR = random.uniform(1.1, 1.4)
# Reduction factor for impact of incongruent info
MOTIVATED_REASONING_FACTOR = random.uniform(0.3, 0.6)

# Media Literacy Parameters
MEDIA_LITERACY_RANGE = (1, 5)  # Range del punteggio (1=Basso, 5=Alto)
# How much literacy reduces impact/suscettibility
MEDIA_LITERACY_EFFECT_FACTOR = random.uniform(0.1, 0.3)

# Elector Learning Parameters (NUOVO - Spostato sotto AI Integration)
# Learning rate for elector preference weights
ELECTOR_LEARNING_RATE = random.uniform(0.01, 0.05)
# How much campaign exposure influences learning
CAMPAIGN_EXPOSURE_LEARNING_EFFECT = random.uniform(0.02, 0.08)
# How much social influence influences learning
SOCIAL_INFLUENCE_LEARNING_EFFECT = random.uniform(0.01, 0.05)

# Citizen (District) AI Parameters
# Range for citizen ideal preferences on attributes
CITIZEN_IDEAL_PREFERENCE_RANGE = (1, 5)
# How much attribute mismatch reduces leaning for citizens
CITIZEN_ATTRIBUTE_MISMATCH_PENALTY_FACTOR = random.uniform(0.6, 0.9)
# Base maximum possible leaning score for citizens
MAX_CITIZEN_LEANING_BASE = random.randint(4, 6)
# Random noise in initial leanings for citizens
CITIZEN_RANDOM_LEANING_VARIANCE = random.uniform(0.3, 0.7)

# Citizen Traits (District)
CITIZEN_TRAITS = ["Attribute Focused", "Random Inclined",
                  "Locally Loyal"]  # Possible citizen traits
CITIZEN_TRAIT_COUNT = 1  # Number of traits assigned to each citizen

# Citizen Trait Modifiers
# Base susceptibility to influence for citizens
CITIZEN_SUSCEPTIBILITY_BASE = random.uniform(0.7, 0.9)
CITIZEN_TRAIT_MULTIPLIER_RANDOM_INCLINED = random.uniform(
    1.3, 1.7)  # Random Inclined trait effect
# Attribute Focused trait effect (currently no multiplier)
CITIZEN_TRAIT_MULTIPLIER_ATTRIBUTE_FOCUSED = 1.0
CITIZEN_TRAIT_RANDOM_INCLINED_BIAS = random.uniform(
    0.8, 1.5)  # Bias for Random Inclined trait


# ==============================================================================
# --- PHASE 1: DISTRICT ELECTIONS ---
# ==============================================================================

NUM_DISTRICTS = random.randint(
    10, max(12, NUM_GRAND_ELECTORS // 6))  # Number of districts
# Number of candidates in each district
CANDIDATES_PER_DISTRICT = random.randint(10, 20)
# Number of citizens in each district
CITIZENS_PER_DISTRICT = random.randint(1000, 10000)
# How many citizens a district candidate can influence per round
INFLUENCE_CITIZENS_PER_CANDIDATE = random.randint(
    30, min(100, CITIZENS_PER_DISTRICT // 10))


# ==============================================================================
# --- PHASE 2: GOVERNOR ELECTION (COLLEGE) ---
# ==============================================================================

MAX_NORMAL_ROUNDS = random.randint(10, 15)  # Maximum rounds before runoff
# Percentage of votes required to win (e.g., 0.6 for 60%)
REQUIRED_MAJORITY = random.uniform(0.6, 0.7)
REQUIRED_MAJORITY_ATTEMPT_4 = 0.5  # Reduced majority for later attempts
# Maximum total rounds including runoff
MAX_TOTAL_ROUNDS = MAX_NORMAL_ROUNDS + random.randint(20, 30)

# Pause duration in seconds during the College phase GUI updates
GOVERNOR_PAUSE_SECONDS = 0.3


# ==============================================================================
# --- CAMPAIGN DYNAMICS ---
# ==============================================================================

INFLUENCE_ELECTORS_PER_CANDIDATE = random.randint(
    max(10, NUM_GRAND_ELECTORS // 10), max(20, NUM_GRAND_ELECTORS // 4)
)  # How many electors a college candidate can target per round

# Base chance of a campaign attempt being successful
CAMPAIGN_INFLUENCE_CHANCE = random.uniform(0.6, 0.85)
# Base strength of campaign influence on elector leanings
INFLUENCE_STRENGTH_FACTOR = random.uniform(0.08, 0.18)

# Bonus to influence if campaign theme matches elector's high-weight attribute
CAMPAIGN_THEME_BONUS_PER_ATTRIBUTE = random.uniform(0.4, 0.7)

# Campaign Budget and Allocation
# INITIAL_CAMPAIGN_BUDGET is defined in Candidate Properties section
_min_alloc = random.randint(1, 10)
_max_alloc = random.randint(40, 80)
if _min_alloc > _max_alloc:  # Ensure min <= max
    _min_alloc = _max_alloc - 1 if _max_alloc > 1 else 1
# Range of budget spent per elector per campaign attempt
CAMPAIGN_ALLOCATION_PER_ATTEMPT_RANGE = (_min_alloc, _max_alloc)

# How much allocated budget increases influence strength
CAMPAIGN_ALLOCATION_INFLUENCE_FACTOR = random.uniform(0.03, 0.08)
CAMPAIGN_ALLOCATION_SUCCESS_CHANCE_FACTOR = random.uniform(
    0.003, 0.008)  # How much allocated budget increases success chance
# Maximum influence points per successful attempt
MAX_CAMPAIGN_INFLUENCE_PER_ATTEMPT = random.uniform(2.0, 4.0)
# For normalizing the targeting potential calculation
MAX_TARGETING_POTENTIAL_SCORE = 25.0

# Esponente per i rendimenti decrescenti sulla spesa per tentativo di influenza
# Un valore < 1.0 causa rendimenti decrescenti (es. 0.7 significa che raddoppiare la spesa non raddoppia il bonus)
# Un valore = 1.0 sarebbe lineare (nessun rendimento decrescente)
DIMINISHING_RETURNS_EXPONENT_PER_ATTEMPT = random.uniform(0.6, 0.85)  # Es. 0.7

# ==============================================================================
# --- COMPETITIVE ADAPTATION (CAMPAIGN AI) ---
# ==============================================================================

# How much candidates focus on their own strengths vs. countering opponents (0=only counter, 1=only focus on self)
COMPETITIVE_ADAPTATION_SELF_FOCUS_FACTOR = random.uniform(0.4, 0.7)
# How much competitive analysis influences theme selection
COMPETITIVE_ADAPTATION_IMPACT = random.uniform(0.3, 0.6)
# Number of top opponents considered for counter-messaging strategy
COMPETITIVE_ADAPTATION_TOP_OPPONENTS = 2

# Targeting Parameters (Used in simulate_campaigning for potential calculation)
TARGETING_KEY_ELECTOR_BONUS_FACTOR = random.uniform(
    1.5, 2.5)  # Bonus to potential for key electors


# ==============================================================================
# --- SOCIAL NETWORK ---
# ==============================================================================

USE_SOCIAL_NETWORK = True  # Enable/disable social network influence

# Watts-Strogatz Small-World Graph Parameters:
# k: Each elector is initially connected to k nearest neighbors
NETWORK_AVG_NEIGHBORS = 6
NETWORK_REWIRING_PROB = 0.1  # p: Probability of rewiring an edge to a random node

# Social Influence Parameters (Weighted Average Model)
# Alpha: Weight given to neighbors' average opinion (0=no influence, 1=only neighbors)
SOCIAL_INFLUENCE_STRENGTH = 0.05
# How many times to apply influence calculation per round
SOCIAL_INFLUENCE_ITERATIONS = 1
# SOCIAL_INFLUENCE_LEARNING_EFFECT is defined in Elector Learning Parameters section


# ==============================================================================
# --- EVENTS ---
# ==============================================================================

# Global variable for the current hot topic (e.g., attribute name)
CURRENT_HOT_TOPIC = None

# Scandal Event Parameters
EVENT_SCANDAL_PROB_FACTOR_INTEGRITY_DIFF = random.uniform(0.015, 0.035)
EVENT_SCANDAL_IMPACT = random.uniform(1.0, 3.0)

# Ethics Debate Event Parameters
EVENT_ETHICS_DEBATE_PROB_FACTOR_INTEGRITY_DIFF = random.uniform(0.008, 0.02)
EVENT_ETHICS_DEBATE_IMPACT = random.uniform(0.08, 0.15)

# Endorsement Event Parameters
EVENT_ENDORSEMENT_BASE_PROB = 0.05
EVENT_ENDORSEMENT_IMPACT_RANGE = (0.1, 0.3)

# --- NUOVI PARAMETRI PER DIBATTITI E RALLY ---
# Political Debate Event Parameters
EVENT_DEBATE_BASE_PROB = 0.08  # Probabilità base che si verifichi un dibattito
# Fattore generale per l'impatto del dibattito sui leanings
EVENT_DEBATE_IMPACT_FACTOR = random.uniform(0.3, 0.8)
# Numero di candidati principali che partecipano (basato sui risultati precedenti)
EVENT_DEBATE_NUM_PARTICIPANTS = random.randint(3, 5)

# Candidate Rally Event Parameters
EVENT_RALLY_BASE_PROB = 0.10  # Probabilità base che un candidato tenga un rally
# Fattore generale per l'impatto del rally sui leanings
EVENT_RALLY_IMPACT_FACTOR = random.uniform(0.4, 0.9)
# Costo opzionale in budget per tenere un rally
EVENT_RALLY_BUDGET_COST = random.randint(20, 60)
# Soglia di leaning per considerare un elettore "favorevole" al candidato del rally
EVENT_RALLY_FAVORABLE_THRESHOLD_FACTOR = 0.6  # (es. leaning > 60% del max)
# Soglia per considerare un elettore "opposto"
EVENT_RALLY_OPPOSED_THRESHOLD_FACTOR = 0.3  # (es. leaning < 30% del max)
# --- FINE NUOVI PARAMETRI ---


# ==============================================================================
# --- DATABASE ---
# ==============================================================================

DATABASE_FILE = 'simai.db'  # Name of the SQLite database file


# ==============================================================================
# --- GUI / PYGAME ---
# ==============================================================================

# Default simulation mode (True for step-by-step, False for continuous)
STEP_BY_STEP_MODE_DEFAULT = False

PIXEL_FONT_SIZE = 18  # Base font size for GUI text
BLOCK_SIZE = 10  # Appears unused, but kept for completeness if present in original

SPRITE_WIDTH = 32  # Width of character sprites (adjust if needed)
SPRITE_HEIGHT = 32  # Height of character sprites (adjust if needed)

# --- Colors ---
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

BG_COLOR = DARK_GRAY  # Background color for GUI

WINDOW_TITLE = "Anthalys Governor Election Simulation"  # Window title

# Image Paths (Make sure these files exist in your assets directory)
IMAGE_PATHS = {
    "character_male_dark": "assets/characters/darkmale.png",
    "character_male_light": "assets/characters/lightmale.png",
    "character_female_dark": "assets/characters/darkfemale.png",
    "character_female_light": "assets/characters/lightfemale.png",
    "character_male_tanned": "assets/characters/maletanned.png",
    "character_male_tanned2": "assets/characters/maletanned2.png",
    "character_female_tanned": "assets/characters/femaletanned.png",
    "character_female_tanned2": "assets/characters/femaletanned2.png",
}

# Note: SPRITE_MAPPING is typically in data.py as it maps asset keys to logical sprites.
