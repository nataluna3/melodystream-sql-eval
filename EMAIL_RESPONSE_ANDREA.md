# Email draft: MelodyStream text-to-SQL — send to Andrea

**To:** Andrea Chen \<andrea.chen@melodystream.com\>  
**From:** Nathalia Luna \<nathalia@fireworks.ai\>  
**Cc:** Solutions Team \<solutions@fireworks.ai\>  
**Subject:** MelodyStream text-to-SQL — what we measured, what we’d ship, and what I’d do next

---

Hi Andrea,

Thanks again for looping us in. I know your team’s time is tight, so I’ll cut straight to what you asked for: **how to measure this**, **how to fix the prompt**, and **what to run in production**, with real numbers from the benchmark you shared, not hand-waving.

## What we actually tested

We built a small harness around your Chinook database and the ten questions in `evaluation_data.json`. For each question we:

1. Ask the model for SQL.  
2. Run it against your SQLite file.  
3. Check whether the **rows come back exactly right** compared to your ground truth—same data, including the messy duplicate rows in the playlist cases. (We don’t insist the SQL text matches ours letter for letter; we care whether the **answer** matches.)

We also tracked **execution rate** (did the query at least run?) and **latency** (how long the model took per question), because “throughout the workday” matters as much as accuracy.

## The headline: your gut on the baseline was right

The simple prompt you’ve been using “Convert this question to SQL” **flatlined**. On both models we tried, **functional accuracy was 0%** on all ten questions. So if your team felt the POC was unreliable, **the eval backs that up**. It’s not them; the setup really wasn’t giving the model enough to work with.

## What changed when we fixed the prompt

We added what was missing: **full schema context** from the live database, **explicit SQLite rules**, and a few **carefully chosen examples** (not copied from your ten test questions, so we weren’t “teaching to the test”).

Here’s how that 2×2 shook out:

| Setup | Model | Functional accuracy | Execution rate | Avg. latency / question |
|--------|--------|---------------------|----------------|-------------------------|
| Baseline prompt | Mixtral 8×22B Instruct | **0%** (0/10) | **0%** | **0.84 s** |
| Baseline prompt | DeepSeek V3.2 | **0%** (0/10) | **30%** | **7.27 s** |
| **Improved prompt** | **Mixtral 8×22B Instruct** | **40%** (4/10) | **100%** | **0.84 s** |
| Improved prompt | DeepSeek V3.2 | **10%** (1/10) | **90%** | **7.28 s** |

Initially we had **Qwen2.5-Coder 32B** in scope—it’s purpose-built for SQL and code generation and would’ve been the obvious “heavy hitter” here, but it sits behind **on-demand deployment** on Fireworks, not the **serverless** path we could use for this exercise. So we benchmarked against the **strongest serverless models available to us** (Mixtral 8×22B Instruct and DeepSeek V3.2), which still shows clearly what fixing the prompt does for you. When MelodyStream is ready to push accuracy further, **a dedicated Qwen Coder deployment** is where I’d go first—it’s usually the cleanest way to get a big jump on gnarly joins and analytics SQL without changing how your teams work with the product.

A few things jump out:

- **Improved prompt + Mixtral** is the only combo where **every query was at least valid SQLite** (100% execution), and it **answered four of ten exactly right**, not where we want to land forever, but a real step up from “0% and mostly hallucinated table names.”
- **DeepSeek** did pull more queries into “runs without error” with the improved prompt, but **accuracy stayed low** and latency sat around **7.3 seconds per question**. For a tool people reach for all day, that’s going to feel heavy, and it didn’t buy you a better hit rate on this set than Mixtral.

## What I’d recommend for MelodyStream

**Ship Mixtral 8×22B Instruct with the improved prompt** as your first production pattern—then **keep iterating on the eval set** with real analyst questions so “40%” climbs in a way that reflects your actual workflows.

Fireworks is a good long-term home for this, in plain English:

- You get **open-weight models** you can **reason about and swap**—not a bet-the-company lock-in on one opaque black box.
- Inference is **fast where it matters**: we saw **sub-second average latency** on Mixtral with this workload— workable for interactive BI.
- When you’ve accumulated enough **good question → SQL** pairs from your own analysts, you can **fine-tune** on **your** patterns so the model speaks *your* schema and naming habits, not a generic demo.

I’m not claiming you’ll never want guardrails—in production I’d still want read-only connections, sensible row limits, and maybe a quick human glance for high-stakes numbers. But this gets you from “we can’t tell if it works” to **a measured baseline** and a **clear direction**.

## Next steps (concrete)

1. **Drop the baseline prompt** for anything customer-facing; keep it only as a regression check so you never slip backward.  
2. **Run the improved prompt + Mixtral** as default; wire the eval into CI or a weekly job as you add questions.  
3. **Harvest failures** from real usage and append them to your golden set—that’s how 40% becomes 70%+.  
4. When volume justifies it, talk to us about **fine-tuning** on Fireworks so the model learns MelodyStream’s *actual* query language.

Everything, including how to reproduce these numbers—is in the repo: **https://github.com/nataluna3/melodystream-sql-eval** (README → **Solution**). If you want a short walkthrough live, happy to slot something in.

Thanks for trusting us with a real problem. This is solvable; you’re just past the “vibe check” stage and into the part where measurement makes it boring—in a good way.

Best,  
Nathalia Luna
Solutions Architect

---

I used Cursor with Composer 2 as my AI coding assistant throughout this project to accelerate development. The evaluation methodology, model selection rationale, and recommendations are my own.
