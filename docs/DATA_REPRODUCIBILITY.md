# Dataset Preprocessing and Reproducibility Guide

This guide documents the authoritative, deterministic preprocessing pipeline for the **UCI Online Retail II** dataset used by the Warehouse Intelligence Twin simulation.

---

## 1. Provenance and Source Citation

- **Dataset:** Online Retail II (Chen, D., 2012)
- **DOI:** [10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D)
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Official UCI Page:** [https://archive.ics.uci.edu/dataset/502/online+retail+ii](https://archive.ics.uci.edu/dataset/502/online+retail+ii)
- **Direct Download URL:** [https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip](https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip)
- **Official Workbook SHA-256:** `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`
- **Target Sheet:** `Year 2010-2011`
- **Target Month:** June 2011 (`2011-06`)

---

## 2. Invariants and Determinism Rules

The preprocessing script `scripts/preprocess_retail.py` enforces deterministic rules to produce canonical, byte-identical snapshot fixtures:

1. **Target Calendar Month Filter:** June 2011 (`2011-06`, 36,874 sheet rows).
2. **Cancellation Filter:** All invoice numbers beginning with `"C"` are excluded (711 rows).
3. **Non-Positive / Missing Quantity:** Rows where `Quantity <= 0` or is missing are excluded (818 rows).
4. **Non-Product Codes:** Service charges and non-physical SKUs are excluded (`POST`, `DOT`, `M`, `D`, `BANK CHARGES`, `AMAZONFEE`, `C2`, `CRUK`, `S`, `PADS`, `B`, `ADJUST`, `ADJUST2`, `TEST001`, `TEST002`, `SAMPLES`) (241 rows).
5. **Retained Product Lines:** Exactly 35,857 valid positive product lines.
6. **Pick Frequency Definition:** Number of retained picking lines per SKU across the month (not sum of units).
7. **Top-100 SKU Ranking & Tie-Breaking:** Sorted by pick frequency descending (`-sku_freq[s]`), with ties broken deterministically by ascending SKU code (`s`).
8. **SKU Product Description:** First observed non-null description for each SKU in stable source dataset row order.
9. **Order Selection & Tie-Breaking:** First 20 invoices by earliest retained line timestamp. Timestamp ties are broken by stable source row appearance order.
10. **Order Line Items:** Retained order lines for the top 100 SKUs in order of appearance.
11. **Initial Warehouse Layout:** 21x21 grid (1.5m cell pitch), 100 rack slots on impassable odd/odd coordinates with southern access cells; slot assignments generated using seeded PRNG (`random.Random(42)`).

---

## 3. Clean-Checkout Reproduction Instructions

Follow these exact steps to reproduce the dataset from scratch on a clean checkout:

### Step 1: Install Dependencies

```bash
cd warehouse-intelligence-twin
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Step 2: Download and Verify Official Source Workbook

```bash
mkdir -p datasets/online-retail-ii
curl -fsSL -o datasets/online-retail-ii/online-retail-ii.zip "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
unzip -q datasets/online-retail-ii/online-retail-ii.zip -d datasets/online-retail-ii/

# Verify SHA-256 checksum
echo "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980  datasets/online-retail-ii/online_retail_II.xlsx" | sha256sum -c -
```

### Step 3: Run Preprocessing

```bash
# Explicit path
python scripts/preprocess_retail.py --input datasets/online-retail-ii/online_retail_II.xlsx

# Alternatively, set UCI_DATASET_PATH:
# export UCI_DATASET_PATH=datasets/online-retail-ii/online_retail_II.xlsx
# python scripts/preprocess_retail.py
```

The script automatically verifies the SHA-256 checksum, processes the June 2011 sheet, and outputs:
- `backend/app/data/demo.json`
- `backend/app/data/demo-provenance.json`
- `frontend/public/demo.json`
- `frontend/public/demo-provenance.json`

### Step 4: Verify Fixture Byte Identity

```bash
diff -u backend/app/data/demo.json frontend/public/demo.json
diff -u backend/app/data/demo-provenance.json frontend/public/demo-provenance.json
git status
```

Rerunning preprocessing produces zero diff against committed fixtures.

### Step 5: Run Automated Tests

```bash
python -m pytest tests/ -v
```

All 22 unit, contract, and preprocessing tests will pass.

---

## 4. Expected Simulation Metrics

The deterministic June 2011 dataset produces exact, repeatable simulation metrics across both backend simulation endpoints and frontend verification:

| Metric | Original Policy | Fast-Mover Baseline | Improvement |
| :--- | :--- | :--- | :--- |
| **Walking Distance** | 2,844.0 m | 2,820.0 m | -24.0 m (-0.84%) |
| **Picking Time** | 3,470.0 s | 3,450.0 s | -20.0 s (-0.58%) |
| **Selected Orders** | 20 | 20 | Identical order batch |
| **SKUs Slotted** | 100 | 100 | 100 slots (21x21 grid) |
| **Walking Speed** | 1.2 m/s | 1.2 m/s | Constant parameter |
| **Pick Handling Time** | 5.0 s / line | 5.0 s / line | Constant parameter |

---

## 5. Git Repository Safety

The original 44 MB workbook must **never** be committed to Git. The project `.gitignore` explicitly ignores:
- `*.xlsx`
- `*.xls`
- `datasets/`
- `data/raw/`
