"""
Utility functions for data operations across the VPP application.
"""

from typing import List, Optional, Tuple

from backend.src.db import CrudManager, DatabaseManager


def get_datasets_list(db_manager: DatabaseManager, crud_manager: CrudManager) -> List[Tuple[str, Optional[str]]]:
    """
    Returns a list of (dataset, source_id) tuples.
    For renewable datasets, we retrieve all existing source_ids in the DB.
    For non-renewable datasets (like load, market), source_id is None.

    Args:
        db_manager: DatabaseManager instance
        crud_manager: CrudManager instance

    Returns:
        List of tuples (dataset_name, source_id)
    """
    datasets_info = []

    # 1) Loop over each renewable and its source_ids
    for renewable in db_manager.renewables:
        sids = crud_manager.query_source_ids(renewable)
        for sid in sids:
            datasets_info.append((renewable, sid))

    # 2) Add non-renewable datasets without source_id
    for ds in ["load", "market"]:
        datasets_info.append((ds, None))

    return datasets_info
