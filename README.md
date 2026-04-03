# FireworksAI Applied AI Take-Home Assessment

This take-home reflects things that you would typically spend time on day-to-day in the role. It helps us understand your ability to:

1. **Understand a customer's problem** - Analyze business requirements and technical constraints
2. **Iterate on a solution** - Apply AI engineering methods to improve model performance
3. **Evaluate model quality** - Define metrics and systematically measure performance
4. **Model selection** - Choose appropriate models based on requirements and trade-offs
5. **Communicate effectively** - Present technical findings and recommendations clearly

Below is an email from Andrea, VP of Analytics at MelodyStream (a large music streaming platform), who is evaluating AI models to build an internal business intelligence tool that converts natural language queries to SQL.

## What We're Looking For

In responding to this take-home, you should:

1. **Define and measure quality** - Create an evaluation framework with clear metrics
2. **Iterate to improve performance** - Apply AI engineering techniques (prompt engineering, few-shot examples, etc..) to improve baseline results.
3. **Select and justify a model** - Choose an appropriate model and clearly explain your reasoning (cost, latency, accuracy trade-offs)
4. **Why FireworksAI**: Make a case to the client why FireworksAI is the right platform to solve this problem.
5. **Communicate professionally** - Draft a response email with findings, recommendations, code, and instructions

## Submission Guidelines

- **Time limit:** Please spend no more than **4 hours** on this assessment. Provide a next steps plan for how you would continue to improve the model.
- **Submission deadline:** Within 24 hours of receiving this assessment
- **Format:** Submit as you would a real customer communication (email response with readable clean code and instructions on how to run it)
- **Resources:** You may use the internet, documentation, python packages and any tools you'd use in your day-to-day work. If you use AI to generate code, please include the source of the AI tool in the email.
- **Questions:** If you have questions during the assessment, please reach out to [ravi@fireworks.ai]

**Note on scope:** We're more interested in your approach, thought process, and ability to make progress in a time-boxed manner than achieving perfect accuracy. 
Focus on demonstrating sound business, engineering, and communication skills.

## Email from the Customer

**From:** Andrea Chen <andrea.chen@melodystream.com>
**To:** Solutions Team <solutions@fireworks.ai>
**Subject:** Help Needed: Text-to-SQL for Internal BI Tool

Hi Fireworks team,

Following up on our conversation last week about building an internal business intelligence tool. Our analytics and business operations teams spend a lot of time writing SQL queries against our music catalog database, and we want to enable them to ask questions in natural language instead.

**Our situation:**

We have a production database (SQLite) with our music catalog data - artists, albums, tracks, customers, invoices, playlists, etc. Our teams need to answer questions like "What are the top-selling genres in Germany?" or "Which support rep has the most customers?" throughout the day.

**What we've tried:**

We put together a quick proof of concept using a simple prompt:

```
Convert this question to SQL:
{question}
```

We tested it on a handful of questions and the results were... mixed. Sometimes it works great, sometimes it hallucinates table names or writes invalid SQL. We're not sure how to systematically evaluate whether this is "good enough" or how to improve it.

**What we need help with:**

1. How do we measure if the model is actually working well? What's a good accuracy target?
2. How can we improve the performance from where we are now?
3. Which model should we use? We care about accuracy, but also cost and speed since this will be used frequently throughout the day.

**What we're providing:**

- Our music database (you can download it via the setup script in this repo)
- A set of test questions we've created with ground truth SQL queries for evaluation
- Utility code for querying the database

I'd love to hear your recommendations on how to move forward. We're hoping to make a decision on this in the next couple weeks.

Thanks,
Andrea Chen
VP of Analytics, MelodyStream

---

## Getting Started

### Setup

Run the setup script to create a virtual environment and download the database:

```bash
./setup.sh
```

Or manually:

```bash
# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Download database
curl -s https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql | sqlite3 Chinook.db
```

### Database Schema

The database contains 11 tables modeling a digital music store:

- **Artist, Album, Track** - Music catalog
- **Customer, Employee** - People
- **Invoice, InvoiceLine** - Sales transactions
- **Playlist, PlaylistTrack** - Curated collections
- **Genre, MediaType** - Classification

Use the provided utility functions to explore:

```python
from utils import load_db, query_db, print_table_schema

# Load database
conn = load_db()

# View schema
print_table_schema(conn)

# Run a query
results = query_db(conn, "SELECT * FROM Artist LIMIT 5")
```

### Evaluation Data

A file `evaluation_data.json` is provided with 10 test cases. Each test case includes:

- **question**: Natural language query
- **sql**: Ground truth SQL query
- **expected_result**: The actual results from running the query

This can get you started on your evals.

**Note:** Some test cases may return duplicate rows (e.g., playlists with the same name). This reflects the actual database state and is expected.

Example format:

```json
[
  {
    "question": "What are the top 5 best-selling genres by total sales?",
    "sql": "SELECT g.Name, SUM(il.UnitPrice * il.Quantity) as TotalSales FROM Genre g JOIN Track t ON g.GenreId = t.GenreId JOIN InvoiceLine il ON t.TrackId = il.TrackId GROUP BY g.Name ORDER BY TotalSales DESC LIMIT 5",
    "expected_result": [
      {"Name": "Rock", "TotalSales": 826.65},
      {"Name": "Latin", "TotalSales": 382.14},
      ...
    ]
  }
]
```


### Resources
1. [FireworksAI model library](https://app.fireworks.ai/models)
2. [FireworksAI docs](https://fireworks.ai/docs)
3. [FireworksAI OpenAI SDK](https://fireworks.ai/docs/tools-sdks/openai-compatibility#openai-compatibility)

---

## Solution

This section documents the solution added for MelodyStream’s text-to-SQL evaluation and improvement work. **All assignment text above is unchanged.**

### What was built

| Area | Purpose |
|------|---------|
| **`melodystream_eval/`** | Python package: env loading, Chinook schema → prompt text, baseline vs improved prompts, Fireworks chat completion, SQL extraction, multiset result comparison, eval loop, CLI. |
| **`.env` / `.env.example` / `.gitignore`** | Keeps `FIREWORKS_API_KEY` out of git; documents required variables. |
| **`EMAIL_RESPONSE_ANDREA.md`** | Customer-facing email draft to Andrea Chen with recommendations and why Fireworks fits. |

**Design choices (interview talking points):**

- **Ground truth:** Each of the 10 cases in `evaluation_data.json` supplies `expected_result`. The model’s SQL is executed on `Chinook.db`; success means the returned rows match `expected_result` as a **multiset** (order-independent, duplicates preserved). This rewards missing-semantics fixes, not string equality with the reference SQL.
- **Metrics:** **Functional accuracy** = fraction of cases with a matching result set. **Execution rate** = fraction where generated SQL ran without error. **Mean LLM latency** = average wall time per Fireworks completion (reported per run).
- **Prompts:** *Baseline* mirrors your POC (“Convert this question to SQL”). *Improved* adds live schema introspection (via existing `utils.get_schema`), rules (SQLite-only, `SELECT`/`WITH`, model must return SQL only inside one markdown `sql` code fence), and **held-out** few-shot examples (not copied from the 10 eval questions).
- **Models compared (serverless on this account):** `accounts/fireworks/models/deepseek-v3p2` (strong general / reasoning) vs `accounts/fireworks/models/mixtral-8x22b-instruct` (faster instruct MoE). CLI aliases `qwen` / `llama` map to these for backward compatibility with the take-home brief.

### How to run the evaluation

Run everything from the **repository root** (the directory that contains `Chinook.db`, `evaluation_data.json`, and `melodystream_eval/`).

#### One-time setup

```bash
git clone https://github.com/nataluna3/melodystream-sql-eval.git
cd melodystream-sql-eval
./setup.sh
source .venv/bin/activate    # on Windows: .venv\Scripts\activate
```

If you skip `setup.sh`, use Python 3.11+ and install the project (dependencies are in `pyproject.toml`):

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -e .
# Ensure Chinook.db exists, e.g. download via curl/sqlite3 per Getting Started above
```

#### API key (required for LLM runs)

```bash
cp .env.example .env
# Edit .env: set FIREWORKS_API_KEY=<your key from https://app.fireworks.ai/>
```

#### Reproduce the reported 2×2 results (exact commands)

These match the run that produced the numbers in **Summary of findings** below. Uses default serverless models in `melodystream_eval/config.py` (Mixtral 8×22B Instruct + DeepSeek V3.2; CLI aliases `llama` / `qwen`). Generation uses `temperature=0` in code.

```bash
cd /path/to/melodystream-sql-eval
source .venv/bin/activate   # if using the setup.sh venv

# Optional: verify benchmark + DB only (no API calls)
python3 -m melodystream_eval.cli sanity-check

# Full matrix: 4 configs × 10 questions (40 Fireworks calls). Writes JSON report.
python3 -m melodystream_eval.cli compare-matrix --output results/compare_matrix.json
```

Inspect **`results/compare_matrix.json`**: each entry has `functional_accuracy`, `execution_rate`, `mean_llm_latency_s`, and per-case rows. Console output prints the same summary metrics for each run.

#### Other useful commands

**Single model + single prompt** (`--model` accepts aliases `qwen` / `llama` or full Fireworks `model` ids):

```bash
python3 -m melodystream_eval.cli run --model llama --prompt improved --output results/mixtral_improved.json
python3 -m melodystream_eval.cli run --model qwen --prompt baseline --output results/deepseek_baseline.json
```

**Override models** (if your account uses different serverless ids):

```bash
python3 -m melodystream_eval.cli compare-matrix \
  --fast-model accounts/fireworks/models/mixtral-8x22b-instruct \
  --coder-model accounts/fireworks/models/deepseek-v3p2 \
  --output results/compare_matrix.json
```

Artifacts land under `results/` (gitignored by default) unless you pass another `--output` path.

### Summary of findings

**How to read results:** Each JSON report includes per-case `generated_sql`, execution status, multiset match detail, and token usage summaries from the API. Use `compare_matrix.json` to compare all four configurations side by side.

**Measured 2×2 matrix** (10 cases in `evaluation_data.json`; Mixtral = CLI alias `llama`, DeepSeek = CLI alias `qwen`; see `melodystream_eval/config.py` for full model ids):

| Prompt | Model | Functional accuracy | Execution rate | Mean LLM latency (s) |
|--------|--------|---------------------|----------------|----------------------|
| Baseline | Mixtral 8×22B Instruct | **0%** (0/10) | **0%** (0/10) | **0.84** |
| Baseline | DeepSeek V3.2 | **0%** (0/10) | **30%** (3/10) | **7.27** |
| Improved | Mixtral 8×22B Instruct | **40%** (4/10) | **100%** (10/10) | **0.84** |
| Improved | DeepSeek V3.2 | **10%** (1/10) | **90%** (9/10) | **7.28** |

**Takeaways:**

1. **Baseline prompt:** **0% functional accuracy on both models**—confirms the customer POC problem (no schema → hallucinated tables and brittle SQL).
2. **Improved prompt** (schema + SQLite rules + held-out few-shots): lifts **execution rate** sharply and enables non-zero **functional accuracy**; **Mixtral + improved** is the best trade on this run (**40%** accuracy, **100%** execution, **~0.84 s** mean latency).
3. **DeepSeek V3.2** with improved prompt reached **10%** functional accuracy with **~7.3 s** mean latency—too slow for an always-on internal tool on this setup relative to the accuracy gained.
4. **Recommendation:** Default **Mixtral 8×22B Instruct + improved prompt** for production v1; expand the golden set and consider **fine-tuning** on Fireworks as real analyst traces accumulate. Customer-facing narrative: `EMAIL_RESPONSE_ANDREA.md`.

### Repository layout (solution files only)

```
melodystream_eval/
  __init__.py
  __main__.py      # python -m melodystream_eval
  cli.py           # sanity-check | run | compare-matrix
  config.py
  env_loader.py
  fireworks_client.py
  paths.py
  prompts.py
  result_matching.py
  runner.py
  schema_context.py
  sql_postprocess.py
  types_eval.py
.env.example
EMAIL_RESPONSE_ANDREA.md
```
