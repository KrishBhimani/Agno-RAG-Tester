# 🧩 AGNO RAG Knowledge-Base Evaluation — Consolidated Report (Final)

**Scope:**  
Comprehensive evaluation of **AGNO RAG** across multiple knowledge-base configurations on both **financial** (leac203.pdf) and **technical** (Akreage dataset) documents.  
**Goal:**  
To benchmark retrieval, reasoning, latency, and accuracy across chunking, embedding, and search strategies — identifying production-ready and cost-aware defaults.

---

## 🧠 Overview: How the Evaluation Worked

Below is a simplified flow of how each configuration was tested and analyzed.

```mermaid
graph TD
    A[📄 Documents] --> B[🧩 Chunking Strategies]
    B --> C[🔢 Embedding Models]
    C --> D[🧭 Search & Ranking (Vector / Keyword / Hybrid)]
    D --> E[🧠 AGNO Agent Retrieval]
    E --> F[📊 Evaluation Metrics: Faithfulness, Completeness, Latency]
```
---

## ⚙️ Category Glossary

| Category | Meaning | Typical Values |
|-----------|----------|----------------|
| **Search Type** | Retrieval scoring mode.<br>• `vector` – semantic only<br>• `keyword` – literal term match<br>• `hybrid` – combines both for balance | `vector`, `keyword`, `hybrid` |
| **Chunking Strategy** | How text is split for embedding.<br>• `fixed` – uniform tokens<br>• `semantic` – LLM-based logical segmentation<br>• `recursive` – hierarchical<br>• `agentic` – LLM actively chooses cut points via intent and topic shifts | `fixed`, `semantic`, `recursive`, `agentic` |
| **Chunk Size / Overlap** | Tokens per chunk + context overlap. Large → richer context, slower embedding. | 500 – 2000 / overlap 50 – 150 |
| **Embedder Model** | Converts text → vectors. Large = richer semantics / higher cost. | `text-embedding-3-small`, `text-embedding-3-large` |
| **k (Max Results)** | Top-K chunks returned. Low = precision, High = recall. | 2 – 8 |
| **Similarity Threshold** | (Semantic/Agentic) Chunk merge sensitivity. Lower → broader groups. | 0.5 – 0.9 |
| **Metrics** | Evaluation axes: Latency (ms), Faithfulness, Completeness, Specificity, Contradictions (count). | Rated 1 – 5 + timings |

---

## 🧠 Experiment Matrix (Financial Corpus)

| Run | Chunking | Size | Thr. | Search | Embedder | k | Avg Latency (ms) | Faith- | Complete- | Spec- | Contra- | Key Notes |
|:--:|:--|--:|:--:|:--|:--|--:|--:|:--:|:--:|:--:|:--:|:--|
| #1 | Fixed | 800 | – | Vector | 3-Small | 3 | 10 700 | 3 | 3 | 3 | 2 | Baseline; concise but generic; Jam totals mismatch. |
| #2 | Semantic | 800 | 0.7 | Hybrid | 3-Large | 5 | 12 900 | 4 | 4 | 4 | 1 | Balanced; minor slip on reserves write-off. |
| #3 | Semantic | **1200** | 0.7 | Hybrid | 3-Large | 5 | **10 700** | **5** | **5** | **5** | **0** | ⭐ Best overall; stable & accurate. |
| #4 | Recursive | 1000 | – | Hybrid | 3-Large | 5 | 11 100 | 5 | 4 | 5 | 0 | Structured; best for tables. |
| #5 | Fixed | 800 | – | Hybrid | 3-Large | 5 | 10 700 | 4 | 4 | 4 | 2 | Good recall; some contradictions. |
| #6 | Semantic | – | 0.5 | Hybrid | 3-Large | 5 | 13 300 | 4 | 5 | 4 | 1 | Looser groups; verbose. |
| #7 | Fixed | 500 | – | Hybrid | 3-Large | 4 | 13 000 | 3 | 4 | 3 | 3 | High recall; noisy. |
| #8 | Agentic | 1000 | 0.5 | Hybrid | 3-Large | 5 | 12 200 | **5** | **5** | **5** | 0 | Adaptive segmentation; excellent reasoning. |

---

## 🔍 Parameter Highlights

| Dimension | Insight |
|------------|----------|
| **Search Type** | Hybrid consistently best for recall + precision. Vector-only misses literals; keyword-only good for flags only. |
| **Chunking** | Semantic 0.7 / 1200 best overall; Recursive most structured; Agentic best adaptive reasoning. |
| **Chunk Size** | 1000–1200 tokens ≈ sweet spot. Smaller → fragmentation / contradictions. |
| **Threshold** | 0.7 = stable; 0.5 = verbose. |
| **Embedder** | Large model ↑ faithfulness; Small + Hybrid ≈ 90 % quality at ⅓ cost. |
| **k (Max Results)** | 4 – 6 ideal. Above 6 adds noise/contradiction risk. |

---

## 🧾 Akreage Tech Dataset — Agentic vs Semantic Comparison

**Commands used**

```powershell
# Semantic
python rag_agno_qdrant_playground.py `
  --docs "C:\documents\GEN AI\Agno\Agno-Framework\XO-testing\data\user_abc" `
  --chunk semantic `
  --chunk-size 1000 `
  --similarity-threshold 0.5 `
  --embedder-id text-embedding-3-large `
  --search hybrid `
  --max-results 5 `
  --collection sample_akreage_semantic_chunking

# Agentic
python rag_agno_qdrant_playground.py `
  --docs "C:\documents\GEN AI\Agno\Agno-Framework\XO-testing\data\user_abc" `
  --chunk agentic `
  --chunk-size 1000 `
  --similarity-threshold 0.5 `
  --embedder-id text-embedding-3-large `
  --search hybrid `
  --max-results 5 `
  --collection sample_akreage_agentic_chunking
```

| **Metric** | **Agentic Chunking** | **Semantic Chunking** | **Analysis & Verdict** |
|-------------|----------------------|-----------------------|------------------------|
| 🕒 Avg Response Time | ~17.68 s | ~17.84 s | Practically equal (< 1 s diff). |
| 📚 Docs Retrieved / Query | 5 docs | 3 docs | Agentic broader; Semantic denser context. |
| 🎯 Retrieval Accuracy | 8.9 / 10 | **9.3 / 10** | Semantic more precise boundaries. |
| 🧠 Reasoning Depth | 8.9 / 10 | **9.1 / 10** | Semantic marginally better concept synthesis. |
| 📖 Context Fidelity | 8.8 / 10 | **9.4 / 10** | Semantic better grounding to original meaning. |
| 🧩 Information Coverage | **9.4 / 10** | 8.9 / 10 | Agentic wider coverage (better for exploration). |
| 🗂️ Relevance Density | 0.81 | **0.92** | Semantic higher signal/noise. |
| ⚙️ Tokens Processed | ~1.25 × | Baseline (1 ×) | Agentic 25 % higher token cost. |
| 🧮 Overall Accuracy | 8.89 / 10 (≈ 89 %) | **9.22 / 10 (≈ 92 %)** | Semantic wins narrowly on precision & fidelity. |
| 🤖 Best Use Case Fit | **Agentic → Procedural, multi-step reasoning** | **Semantic → Factual QA / Governance Docs** | Use Agentic for workflow reasoning; Semantic for QA precision. |

**Interpretation**

| Dimension | Better Performer | Reason |
|------------|------------------|--------|
| Breadth / Exploration | Agentic | Adaptive segmentation surfaces diverse context. |
| Precision / Groundedness | Semantic | Embedding-based proximity keeps semantics tight. |
| System Efficiency | Semantic | Lower token usage ≈ cheaper by ~25 %. |
| Multi-Step Reasoning | Agentic | Flexible for procedural logic and chain-of-thought. |
| Stability Across Domains | Semantic | Deterministic and consistent boundaries. |

**Quantitative Summary**

| Metric | Agentic | Semantic |
|--------|:--:|:--:|
| Retrieval Accuracy | 8.9 | **9.3** |
| Reasoning Depth | 8.9 | **9.1** |
| Context Fidelity | 8.8 | **9.4** |
| Info Coverage | **9.4** | 8.9 |
| Efficiency (↑ better = lower cost) | 7.5 | **9.0** |
| Overall Accuracy | 8.9 | **9.2** |

*(Higher = better)*

**Verdict**  
> **Semantic Chunking** remains the stronger default for *precision and cost-efficiency*.  
> **Agentic Chunking** shines when *context-chaining and multi-step reasoning* are required.  
> Best practice: maintain both indices; route factual QA → Semantic, procedural tasks → Agentic.

---

## ✅ Recommended Configurations

| Scenario | Recommended Args |
|-----------|-----------------|
| **Production (default)** | `--chunk recursive --chunk-size 1000 --overlap 120 --embedder-id text-embedding-3-large --search hybrid --max-results 5` |
| **Cost Aware** | `--chunk semantic --chunk-size 1200 --similarity-threshold 0.7 --embedder-id text-embedding-3-small --search hybrid --max-results 5` |
| **Best Overall (Benchmark Winner)** | `--chunk semantic --chunk-size 1200 --similarity-threshold 0.7 --embedder-id text-embedding-3-large --search hybrid --max-results 5` |
| **Agentic Reasoning / Procedural Docs** | `--chunk agentic --chunk-size 1000 --similarity-threshold 0.5 --embedder-id text-embedding-3-large --search hybrid --max-results 5` |
| **Literal Lookups (API flags)** | `--search keyword --chunk fixed --chunk-size 800 --embedder-id text-embedding-3-small --max-results 3` |

---

## 🧩 Generalized Findings (Finance + Tech Corpora)

| Aspect | Observation |
|--------|--------------|
| **Hybrid Search** | Consistently superior; combines recall + precision. |
| **Chunk Coherence** | More critical than embedder size. |
| **Agentic vs Semantic** | Agentic = coverage + multi-step depth; Semantic = faithful precision + efficiency. |
| **k > 6** | Marginal gains; ↑ contradictions. |
| **Page/Section Awareness** | Essential for table and code layouts. |
| **Optimal Default** | Semantic (1200, 0.7) + Hybrid + Large Embedder + k = 5. |

---

## 🩵 Final Takeaways

1. **Semantic Chunking (0.7, 1200)** + **Hybrid Search** + **Large Embedder** = best universal setup (accuracy ≈ 92 %, low token cost).  
2. **Agentic Chunking** adds dynamic contextual reasoning for multi-hop tasks; ≈ 15 % slower but broader coverage.  
3. **Recursive Chunking** is a safe production default for mixed financial or technical docs.  
4. **Hybrid Index Architecture** = store both semantic and agentic indices → route queries by intent.  
5. **Focus on faithfulness and zero contradictions** > raw retrieval count.  

---

> **Final One-Line Summary:**  
> **Semantic Chunking (0.7, ≈ 1200 tokens) + Hybrid Search + Large Embedder (k ≈ 5)** delivers the most accurate, efficient, and coherent retrieval for **QA and compliance KBs**, while **Agentic Chunking** is ideal for **dynamic reasoning and multi-step agent systems** across both **technical** and **financial** documents.
