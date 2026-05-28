# Assessment Tasks — Data & AI Product Engineer

Assessment tasks for the Data & AI Product Engineer position at Tacheon. Two tasks completed within the assessment window, submitted as a single repository.

---

## Repository Structure

```
├── Task_1_Product_Scoping/      ← Product scoping for a marketing insights tool
│   ├── README.md                   Decisions, reasoning, and what I'd revisit
│   └── product_brief.md           What the tool is, who it's for, and V1 scope
│
├── Task_2_pipeline_building/    ← Data pipeline: Open-Meteo API → BigQuery
│   ├── README.md                   Full documentation, setup, and production thinking
│   ├── config.py                   All parameterised values
│   ├── main.py                     Pipeline orchestrator (fetch → transform → load)
│   ├── pipeline/
│   │   ├── fetch.py                API fetching with retry logic
│   │   ├── transform.py            Data cleaning and derived fields
│   │   └── load.py                 BigQuery loading with explicit schema
│   ├── queries/
│   │   └── summary.sql             Analytical queries with sample output
│   ├── tests/
│   │   └── test_transform.py       Unit tests for transformation logic
│   └── requirements.txt
│
└── README.md                    ← You are here
```

## Branch Strategy

- **`task1`** — All Task 1 (Product Scoping) work
- **`task2`** — All Task 2 (Pipeline Building) work, branched from `task1`
- **`main`** — Both tasks merged

Each task was developed on its own branch with incremental commits, then merged into `main`.

## Quick Links

- **Task 1 README:** [Task_1_Product_Scoping/README.md](Task_1_Product_Scoping/README.md)
- **Task 2 README:** [Task_2_pipeline_building/README.md](Task_2_pipeline_building/README.md)
