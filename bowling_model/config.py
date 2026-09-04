"""Config generated from the notebook's config cell -- paths, feature
settings, and the player -> bowling style label mapping."""
import os

MODELS_DIR = "models"
DATA_DIR = "data"
CACHE_DIR = os.path.join(DATA_DIR, "cache")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

ACTION_FILTER_MODEL_PATH = os.path.join(MODELS_DIR, "action_filter.keras")
ARM_MODEL_PATH = os.path.join(MODELS_DIR, "arm_classifier.keras")
PACE_MODEL_PATH = os.path.join(MODELS_DIR, "pace_classifier.keras")
ACTION_FILTER_META_PATH = os.path.join(MODELS_DIR, "action_filter_meta.joblib")
ARM_META_PATH = os.path.join(MODELS_DIR, "arm_meta.joblib")
PACE_META_PATH = os.path.join(MODELS_DIR, "pace_meta.joblib")
REFERENCE_LIBRARY_PATH = os.path.join(MODELS_DIR, "reference_library.npz")
FEATURE_CACHE_PATH = os.path.join(CACHE_DIR, "angle_features.npz")
POSE_MODEL_PATH = os.path.join(MODELS_DIR, "pose_landmarker.task")

SEQUENCE_LENGTH = 30
LM = {'nose': 0, 'l_shoulder': 11, 'r_shoulder': 12, 'l_elbow': 13, 'r_elbow': 14, 'l_wrist': 15, 'r_wrist': 16, 'l_hip': 23, 'r_hip': 24, 'l_knee': 25, 'r_knee': 26, 'l_ankle': 27, 'r_ankle': 28, 'l_heel': 29, 'r_heel': 30, 'l_foot_index': 31, 'r_foot_index': 32}
ANGLE_NAMES = ['l_elbow_angle', 'r_elbow_angle', 'l_knee_angle', 'r_knee_angle', 'l_shoulder_angle', 'r_shoulder_angle', 'l_hip_angle', 'r_hip_angle', 'trunk_lean_angle']
ARM_CLASSES = ['left', 'right']
PACE_CLASSES = ['fast', 'spin']
ACTION_FILTER_CLASSES = ['not_bowling', 'bowling']
PLAYER_STYLE = {'Adil Rasheed': ('right', 'spin'), 'Brett Lee': ('right', 'fast'), 'Chris Woakes': ('right', 'fast'), 'DJ Bravo': ('right', 'fast'), 'Dale Steyn': ('right', 'fast'), 'Haris Rauf': ('right', 'fast'), 'Hasan Mahmud': ('right', 'fast'), 'Ish Sodhi': ('right', 'spin'), 'James Anderson': ('right', 'fast'), 'James Faulkner': ('right', 'fast'), 'James Pattinson': ('right', 'fast'), 'Jasprit Bumrah': ('right', 'fast'), 'Jofra Archer': ('right', 'fast'), 'Josh Hazlewood': ('right', 'fast'), 'Kagiso Rabada': ('right', 'fast'), 'Keshav Maharaj': ('left', 'spin'), 'Lasith Malinga': ('right', 'fast'), 'Lockie Furguson': ('right', 'fast'), 'Mark Wood': ('right', 'fast'), 'Mashrafe Bin Mortaza': ('right', 'fast'), 'Mehidy Hasan Miraz': ('right', 'spin'), 'Mitchell Johnson': ('left', 'fast'), 'Mitchell Starc': ('left', 'fast'), 'Moeen Ali': ('right', 'spin'), 'Mohammad Nabi': ('right', 'spin'), 'Mohammed Shami': ('right', 'fast'), 'Mohammed Siraj': ('right', 'fast'), 'Morne Morkel': ('right', 'fast'), 'Mujeeb Ur Rahman': ('right', 'spin'), 'Mustafizur Rahman': ('left', 'fast'), 'Nahid Rana': ('right', 'fast'), 'Naseem Shah': ('right', 'fast'), 'Nathan Ellis': ('right', 'fast'), 'Pat Cummins': ('right', 'fast'), 'Rashid Khan': ('right', 'spin'), 'Ravichandran Ashwin': ('right', 'spin'), 'Ravindra Jadeja': ('left', 'spin'), 'Sakib Al Hasan': ('left', 'spin'), 'Sam Curran': ('left', 'fast'), 'Shadab Khan': ('right', 'spin'), 'Shaheen Afridi': ('left', 'fast'), 'Shamar Joseph': ('right', 'fast'), 'Shane Watson': ('right', 'fast'), 'Stuart Broad': ('right', 'fast'), 'Taijul Islam': ('left', 'spin'), 'Taskin Ahmed': ('right', 'fast'), 'Tim Saudi': ('right', 'fast'), 'Trent Boult': ('left', 'fast'), 'Wahab Riaz': ('left', 'fast'), 'Wanindu Hasaranga': ('right', 'spin')}

