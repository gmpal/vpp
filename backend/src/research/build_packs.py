#!/usr/bin/env python3
"""Pre-packager: ingest Fluvius data into research community packs.

Reads all 8 Fluvius CSV files (300 meters x 8 categories = 2,400 meters),
stratified-samples per (size, seed), and writes entity + reading files.

Usage:
    python -m backend.src.research.build_packs

Defaults (matches presentation slides):
    sizes = [10, 30, 50, 100, 300]
    seeds  = [1, 2, 3, 4, 5]
    batteries: N x 10 kWh, 50 % initial SOC
"""

import json
import sys
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root
DATA_FLUVIUS = BASE_DIR / "data_fluvius" / "P6269_1_50_DMK_Sample_Elek_2024_Deel_1"
DATA_FLUVIUS_2 = BASE_DIR / "data_fluvius" / "P6269_1_50_DMK_Sample_Elek_2024_Deel_2"
OUTPUT_DIR = BASE_DIR / "data" / "packs"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SIZES = [10, 30, 50, 100, 300]
SEEDS = [1, 2, 3, 4, 5]

# Battery: capacity per household (kWh)
BATTERY_PER_HH = 10.0
# Initial SOC fraction
BATTERY_SOC_FRAC = 0.50

# ---------------------------------------------------------------------------
# Category mapping — filename -> (warmtepomp, ev, pv)
# ---------------------------------------------------------------------------

FILE_TO_INDICATORS = {
    "P6269_Open_Data_geen_ZP.csv": (0, 0, 0),
    "P6269_Open_Data_enkel_ZP.csv": (0, 0, 1),
    "P6269_Open_Data_WP_geen_ZP.csv": (1, 0, 0),
    "P6269_Open_Data_WP_met_ZP.csv": (1, 0, 1),
    "P6269_Open_Data_EV_geen_ZP.csv": (0, 1, 0),
    "P6269_Open_Data_EV_met_ZP.csv": (0, 1, 1),
    "P6269_Open_Data_WP_EV_geen_ZP.csv": (1, 1, 0),
    "P6269_Open_Data_WP_EV_met_ZP.csv": (1, 1, 1),
}


def load_all_meters():
    """Load all 8 Fluvius files into a single DataFrame with meter metadata.

    Returns a DataFrame indexed by EAN_ID for fast per-meter lookup.
    """
    print("Loading Fluvius data ...")
    all_rows = []
    for filename, indicators in FILE_TO_INDICATORS.items():
        filepath = DATA_FLUVIUS / filename
        if not filepath.exists():
            filepath = DATA_FLUVIUS_2 / filename
        if not filepath.exists():
            print(f"  WARN: {filepath} not found, skipping.")
            continue

        print(f"  Reading {filename} ...")
        df = pd.read_csv(
            filepath,
            usecols=[
                "EAN_ID", "Datum_Startuur",
                "Volume_Afname_KWh", "Volume_Injectie_KWh",
            ],
        )

        # Derive indicators from filename (reliable)
        hp, ev, pv = indicators
        df["pv"] = pv
        df["ev"] = ev

        # Derive category key
        df["category"] = f"{hp}{ev}{pv}"

        all_rows.append(df)

    df = pd.concat(all_rows, ignore_index=True)
    df = df.drop_duplicates(subset=["EAN_ID", "Datum_Startuur"])
    print(f"  -> {len(df):,} rows, {df['EAN_ID'].nunique():,} unique meters")

    # Group by meter for fast per-meter iteration in build_packs
    return df, df.groupby("EAN_ID")


def build_packs(df: pd.DataFrame, meter_groups: pd.core.groupby.DataFrameGroupBy):
    """Build and write all community packs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Group meters by category for stratified sampling
    meters_by_cat = df.groupby("category")["EAN_ID"].unique().to_dict()
    for cat, meters in meters_by_cat.items():
        print(f"  Category {cat}: {len(meters)} meters")

    total = len(SIZES) * len(SEEDS)
    count = 0

    for size in SIZES:
        for seed in SEEDS:
            count += 1
            print(f"\n[{count}/{total}] Building pack {size}_{seed} ...")

            # --- stratified sample ---
            samples = {}  # category -> [ean_ids]
            per_cat = size // 8
            remainder = size - per_cat * 8

            for i, cat in enumerate(sorted(meters_by_cat.keys())):
                cat_meters = list(meters_by_cat[cat])
                n = per_cat + (1 if i < remainder else 0)
                rng = np.random.default_rng(seed + i * 1000)
                samples[cat] = rng.choice(
                    cat_meters, size=min(n, len(cat_meters)), replace=False,
                ).tolist()

            # Flatten into ordered meter list
            all_meters = []
            for cat in sorted(samples.keys()):
                all_meters.extend(samples[cat])
            assert len(all_meters) == size, f"Expected {size} meters, got {len(all_meters)}"

            # --- entity IDs ---
            community_id = str(uuid.uuid4())
            battery_id = f"bat_{size}_{seed}"

            entities = {
                "community_id": community_id,
                "community_name": f"community_{size}_{seed}",
                "size": size,
                "seed": seed,
                "battery_id": battery_id,
                "battery_capacity_kwh": size * BATTERY_PER_HH,
                "battery_soc_pct": BATTERY_SOC_FRAC,
                "households": [],
                "sources": [],
                "vehicles": [],
            }

            # --- per-meter metadata ---
            for ean_id in all_meters:
                meter_sample = meter_groups.get_group(ean_id).iloc[0]
                hh_id = f"hh_{size}_{seed}_{ean_id}"

                entry = {
                    "household_id": hh_id,
                    "ean_id": int(ean_id),
                    "building_type": "Residentieel",
                    "num_people": 1,
                    "solar_panels": 1 if meter_sample["pv"] == 1 else 0,
                    "num_evs": 1 if meter_sample["ev"] == 1 else 0,
                    "community_id": community_id,
                }
                entities["households"].append(entry)

                # Energy source for PV meters
                if meter_sample["pv"] == 1:
                    src_id = f"src_{size}_{seed}_{ean_id}"
                    entities["sources"].append({
                        "source_id": src_id,
                        "household_id": hh_id,
                        "community_id": community_id,
                        "type": "solar",
                        "ean_id": int(ean_id),
                    })

                # Electric vehicle for EV meters
                if meter_sample["ev"] == 1:
                    vid = f"veh_{size}_{seed}_{ean_id}"
                    entities["vehicles"].append({
                        "vehicle_id": vid,
                        "household_id": hh_id,
                        "community_id": community_id,
                        "name": f"EV_{ean_id}",
                        "capacity_kwh": 60.0,
                        "soc_kwh": 30.0,
                        "max_charge_kw": 11.0,
                        "max_discharge_kw": 0.0,
                        "eta": 0.95,
                        "status": "home",
                    })

            # --- write entities ---
            pack_dir = OUTPUT_DIR / f"{size}_{seed}"
            pack_dir.mkdir(parents=True, exist_ok=True)
            with open(pack_dir / "entities.json", "w") as f:
                json.dump(entities, f, indent=2)

            # --- concatenate readings (grouped for speed) ---
            print(f"  Writing {size} x ~35K readings ...")
            out_path = pack_dir / "readings.csv"
            rows: list[tuple] = []

            for ean_id in all_meters:
                meter_df = meter_groups.get_group(ean_id).sort_values(
                    "Datum_Startuur",
                )
                hh_id = f"hh_{size}_{seed}_{ean_id}"
                has_pv = meter_df["pv"].iloc[0] == 1

                # Household load (Volume_Afname_KWh)
                load_df = meter_df[["Datum_Startuur", "Volume_Afname_KWh"]].dropna()
                for _, r in load_df.iterrows():
                    rows.append((
                        str(r["Datum_Startuur"]),
                        "", hh_id,
                        float(r["Volume_Afname_KWh"]),
                        "load",
                    ))

                # Solar injection (Volume_Injectie_KWh)
                if has_pv:
                    src_id = f"src_{size}_{seed}_{ean_id}"
                    pv_df = meter_df[["Datum_Startuur", "Volume_Injectie_KWh"]].dropna()
                    for _, r in pv_df.iterrows():
                        rows.append((
                            str(r["Datum_Startuur"]),
                            src_id, "",
                            float(r["Volume_Injectie_KWh"]),
                            "solar",
                        ))

            # Write CSV via pandas (much faster than row-by-row csv.writer)
            out_df = pd.DataFrame(rows, columns=[
                "timestamp", "source_id", "household_id",
                "value", "meter_type",
            ])
            out_df.to_csv(out_path, index=False)
            print(f"  -> {pack_dir}  ({len(rows):,} readings)")

    print(f"\nAll {total} packs written to {OUTPUT_DIR}")


def main():
    if not DATA_FLUVIUS.exists():
        print(f"ERROR: Fluvius data directory not found: {DATA_FLUVIUS}")
        sys.exit(1)

    df, meter_groups = load_all_meters()
    build_packs(df, meter_groups)


if __name__ == "__main__":
    main()
