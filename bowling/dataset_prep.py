"""Video dataset indexing + grouped CV splits. Only needed if you retrain
locally -- not used at inference time. Generated from the notebook's dataset-prep cell."""
import os
from dataclasses import dataclass
from typing import List
from sklearn.model_selection import GroupKFold
from config import VIDEO_DATASET_DIR, PLAYER_STYLE


@dataclass
class ClipEntry:
    path: str
    player: str
    arm: str
    pace: str

def index_video_dataset(video_dir=VIDEO_DATASET_DIR):
    if not os.path.isdir(video_dir):
        raise FileNotFoundError(
            f"{video_dir} not found. Run the dataset-download cell first, or check "
            f"VIDEO_DATASET_DIR matches the unzipped folder name."
        )

    entries = []
    skipped_unmapped = []
    for player_folder in sorted(os.listdir(video_dir)):
        player_path = os.path.join(video_dir, player_folder)
        if not os.path.isdir(player_path):
            continue
        if player_folder not in PLAYER_STYLE:
            skipped_unmapped.append(player_folder)
            continue
        arm, pace = PLAYER_STYLE[player_folder]
        for fname in sorted(os.listdir(player_path)):
            if fname.lower().endswith((".mp4", ".avi", ".mov")):
                entries.append(ClipEntry(
                    path=os.path.join(player_path, fname),
                    player=player_folder, arm=arm, pace=pace,
                ))

    if skipped_unmapped:
        print(f"WARNING: {len(skipped_unmapped)} folder(s) not in PLAYER_STYLE, skipped: "
              f"{skipped_unmapped}")

    print(f"Indexed {len(entries)} clips across {len(set(e.player for e in entries))} players.")
    return entries


def grouped_kfold_indices(entries, n_splits=5):
    """Yields (train_idx, val_idx) folds grouped by player -- zero leakage."""
    players = [e.player for e in entries]
    gkf = GroupKFold(n_splits=n_splits)
    dummy_X = list(range(len(entries)))
    for train_idx, val_idx in gkf.split(dummy_X, groups=players):
        yield train_idx, val_idx


