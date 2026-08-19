# AI-Powered Job Market & Workforce Intelligence Platform

An end-to-end analytics system for extracting, normalizing, and analyzing job-market data across **Pakistan** and the **UK**, with NLP-based skill extraction, market comparison, and career intelligence features.

## Business Problem

Job seekers, career changers, and workforce planners lack a data-driven, comparative view of job-market requirements across different countries. This platform transforms raw job-posting data into actionable intelligence by:

- Extracting and normalizing skills from unstructured job descriptions
- Comparing job-market demands between Pakistan and the UK
- Identifying skill gaps and growth trends
- Providing candidate-to-job matching and career-gap analysis

## Architecture

```
Sources (Adzuna API, Kaggle Rozee.pk)
    |
    v
[data/raw] -> [data/staging] -> [data/validated] -> [data/processed]
    |                                                       |
    v                                                       v
ingestion_runs + quality_reports              PostgreSQL (analytical schema)
                                                       |
                                              +--------+--------+
                                              |        |        |
                                              v        v        v
                                         Power BI   API    React Web
```

## Technology Stack

| Layer | Tool |
|-------|------|
| Language | Python 3.14 |
| Data | pandas, pyarrow, NumPy |
| Database | PostgreSQL 17 (portable) |
| NLP | spaCy, NLTK, regex lexicons |
| ML | scikit-learn |
| API | FastAPI + Uvicorn |
| Web | React + Vite |
| Dashboard | Power BI Desktop |
| Tests | pytest + GitHub Actions |
| Lint | ruff |

## Setup

```bash
# 1. Clone
git clone https://github.com/twothousandthree18-spec/AI_Job_Market_Workforce_Intelligence.git
cd AI_Job_Market_Workforce_Intelligence

# 2. Python environment
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 3. PostgreSQL (portable on D:\Tools\PostgreSQL)
#    See docs/postgresql_setup.md for instructions

# 4. Environment variables
copy .env.example .env
# Edit .env with your database URL and API keys

# 5. Run pipeline
python scripts/run_pipeline.py --stage all
```

## Data Sources

| Source | Market | Type | Notes |
|--------|--------|------|-------|
| Adzuna API | UK | Live API | Free key required (developer.adzuna.com) |
| Kaggle Rozee.pk Dataset | Pakistan | Historical | 2024 listings, publicly shared |

## Database Design

See `sql/schema.sql` for the complete analytical schema. Key tables: `jobs`, `companies`, `locations`, `job_titles`, `skills`, `job_skills`, `salary_data`, `ingestion_runs`, `data_quality_results`.

## Project Structure

```
data/           # raw, staging, validated, processed, external, quarantine
src/            # Python modules: ingestion, validation, cleaning, normalization, nlp, analytics, ml, pipeline
sql/            # PostgreSQL schema and analytical queries
configs/        # skill lexicon, title maps, source configs
scripts/        # pipeline orchestrator, utilities
tests/          # unit + integration tests
notebooks/      # Jupyter exploration notebooks
api/            # FastAPI backend
web/            # React frontend
dashboard/      # Power BI templates and documentation
docs/           # architecture, methodology, screenshots
models/         # saved ML models
logs/           # pipeline run logs and quality reports
```

## NLP Methodology

Job descriptions are processed through a layered extraction system:
1. Text cleaning (HTML strip, boilerplate removal)
2. Curated lexicon matching (200+ skills across 6 categories)
3. spaCy NER + noun phrase extraction
4. Fuzzy matching (rapidfuzz) for variant normalization
5. Title normalization via alias dictionary

## Market Comparison

The platform directly compares Pakistan and UK job markets for data/analytics roles, analyzing:
- Job volume and growth
- Required skills and tools
- Salary ranges (where advertised)
- Education and experience requirements
- Work modes (remote/hybrid/onsite)
- Industry distribution

## Limitations

- Pakistan data is historical (2024); fresh PK data requires future collection
- Salary data is sparse (many postings omit salary); explicit advertised-vs-estimated split
- Skill extraction is rule-based; precision/recall validated on labeled sample
- No scraping of job boards (LinkedIn, Rozee.pk, Mustakbil) — data from APIs and public datasets only

## Responsible Use

- All job data collected via legitimate APIs and public datasets
- No personal candidate data is collected or stored
- Career recommendations are analytical tools, not hiring decisions
- Salary figures are observed or estimated, never fabricated

## License

MIT
