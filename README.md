# OKN-Guard
Objective
This multi-agent pipeline checks biomedical claims by collecting evidence from multiple knowledge graphs and scientific literature, then produces an explainable verdict with traceable sources and calibrated uncertainty.


Some gaps we try to fill are:
Existing systems have not demonstrated one general verification framework that formally supports and separately evaluates gene–disease, SNP–disease and pathway–disease claims using both KG and literature evidence. 
Evidence-family dependency control: Group repeated evidence that ultimately comes from the same study or database, so it is not counted multiple times.
Provenance-family removal testing: Remove one major evidence family at a time and check whether the verdict changes.
Conformal uncertainty calibration: Produce statistically calibrated verdict sets or abstain when the system cannot guarantee sufficient reliability.
Multiple-claim error correction: Apply BH/BY correction when verifying many claims, limiting the number of false discoveries across the batch.
Qualifier-preservation validation: Explicitly check that conditions such as species, population, tissue, dosage, negation and uncertainty survive claim decomposition and verification.
preserve claim composition : preserve an original claim which is combination of different claims


Property
meaning
Atomic claim decomposition
Breaks complicated questions into small, independently checkable claims.
Entity normalization
Maps names such as “APOE” to standard identifiers used across databases.
Multi-KG search
Searches Proto-OKN and other biomedical knowledge graphs instead of relying on one database.
Literature verification
Checks scientific papers independently of the KG results.
Support and falsification agents
One agent searches for supporting evidence; another actively searches for contradictions and counterexamples.
Evidence provenance
Records exactly which KG, paper, database and original source produced each piece of evidence.
Dependency-aware evidence
Avoids counting the same underlying study multiple times merely because several databases repeat it.
Evidence-quality assessment
Considers study type, relevance, credibility and biological context—not only the number of sources.
Robustness testing
Checks whether the verdict changes after removing a dominant evidence family or source.
Calibrated uncertainty
Reports uncertainty and can abstain when the available evidence is insufficient.
Multiple-claim correction
Uses BH/BY correction when many claims are tested, reducing false discoveries.
Explainability
Shows the reasoning, evidence paths, contradictions and limitations behind every verdict.
Auditable execution
Uses multi-agent orchestration and LangSmith tracing so each processing step can be inspected and debugged.
Interoperability
Crosswalks identifiers such as Entrez, Ensembl, HGNC, MONDO and DOID, allowing it to work across different KGs.




1. Shared-origin provenance-family detection -Using provenance lineage to detect correlated evidence 


Original ChEMBL assertion
├── SPOKE edge
├── DRKG edge
├── another integrated KG edge
└── review paper repeating the assertion

-Existing systems may preserve all four source references. Our system would additionally recognise that they are not four independent discoveries: 

{
  "provenance_family": "ChEMBL-assay-123",
  "observed_sources": ["SPOKE", "DRKG", "KG-X", "Review-Y"],
  "independent_primary_sources": 1
}

2.Partial dependencies complicate deduplication 

Paper A reports an experiment.
Paper B reanalyses Paper A’s dataset.
Review C cites Papers A and B.
KG D imports a relationship from Review C.


PF1: Original experimental family
├── Paper A: primary experiment
├── Paper B: dataset reuse with new analysis
├── Review C: secondary summary
└── KG D: imported assertion


Evidence
Role
Paper A
Primary evidence
Paper B
Partially dependent reanalysis
Review C
Secondary evidence
KG D
Derived representation





3. Would the verdict remain the same if one family were unavailable or incorrect?


Family
Evidence
PF1
ChEMBL assay, copied into three KGs
PF2
Independent clinical-trial publication
PF3
Independent experimental paper
PF4
Independent observational study


For every family PF-j calculate:
Δj = S(E) - S(E/PFj)

-S(E) is the score using all evidence families.
-S(E/PFj) is the score after removing family j.
-Δj measures how strongly the result depends on that family.

Example

All families       → Supported, score 0.91
Remove PF1         → Supported, score 0.84
Remove PF2         → Supported, score 0.87
Remove PF3         → Supported, score 0.85
Remove PF4         → Supported, score 0.89

The verdict is stable under every removal

Verdict: Supported
Robustness: Robust across evidence families


All families       → Supported, score 0.90
Remove PF1         → Insufficient evidence, score 0.48
Remove PF2         → Supported, score 0.88
Remove PF3         → Supported, score 0.87

The verdict depends mainly on PF1
Verdict: Supported
Robustness: Fragile
Dominant family: PF1


When removal is redundant : 
-Only one evidence family exists
-The scoring model already exposes family influence 
Ex:
PF1 contribution = 85%
PF2 contribution = 10%
PF3 contribution = 5%

-All families have identical treatment and additive scores 
 If the scoring function is simply:
S=∑ wj
then removing a family just subtracts wj. No additional computation is required.


When removal is still useful 

Removal matters when the final verifier is nonlinear.
For example:
KG paths interact with literature evidence.
One family supplies the main relationship while another supplies a qualifier.
Removing one source breaks a multi-hop evidence chain.
Supporting and contradicting families interact.
The LLM may change its interpretation when evidence context changes.

Ex:

PF1: Drug X inhibits Protein P
PF2: Protein P increases Disease Y
PF3: A trial reports Drug X improves Disease Y

Removing PF2 breaks the mechanistic path even though PF1 and PF3 remain.
Therefore, the effect cannot always be estimated by merely subtracting a weight.

Workflow after finding a dominant family

Dominant family detected
        ↓
Provenance and quality audit
        ↓
Recalculate evidence strength
        ↓
Judge Agent assigns final verdict

SCORES



Score
Meaning


Entity-match score
How well “APOE” matches an identifier


Retrieval score
How relevant a paper or KG path is


NLI score
How strongly a passage entails or contradicts a claim


Source-quality score
Strength of study design and provenance


Evidence-family score
Strength of one independent evidence family


Raw verdict score
Judge’s preference for supported/contradicted/insufficient


Conformal result
Statistically calibrated prediction set or p-value


Robustness score
Sensitivity to evidence removal





Level 1: Individual evidence score 

For each KG edge or publication:
Linear combination of 
relevance to the claim.
source/study quality.
directness of evidence.
contextual match.
For a family:
family_score = max(primary_evidence_scores)
Or
family_score = primary_score + small_confirmation_bonus

Aggregate families supporting and contradicting
Retain both support score and contraction score 
Judge provides raw scores 
{
  "supported": 0.69,
  "contradicted": 0.18,
  "insufficient": 0.13
}

Next steps : conformal prediction , bh/by correction
Conformal prediction: ( calibrated score against cosine similarity and llm-as-judge)
-It compares how unusual the new example would be if it had that label against calibration examples with that label. 
-small dataset where you already know the definitive truth (size -n)
- non conformity score : a=1−score for the label being tested. 
Ex: support score:0.7
- anew=0.3
-conformal p-value is 
	p(supported)= 1+#{ai>=anew} / n+1 

-calculate it for every possible label 
- Choose a significance level, say α=0.10\alpha=0.10. Keep every label whose p-value is greater than α 


preserve claim composition : 

Original:
APOE is associated with Alzheimer’s disease and participates in lipid metabolism.

C1: APOE is associated with Alzheimer’s disease.
C2: APOE participates in lipid metabolism.


{
  "group_id": "G1",
  "source_span": "APOE is associated with Alzheimer's disease and participates in lipid metabolism.",
  "member_claim_ids": ["C1", "C2"],
  "operator": "and"
}


Original statement
       │
      AND
     /   \
   C1     C2

It provides following benefits:
Correct verdict reconstruction
If C1 is supported but C2 is contradicted, the original conjunction is not fully supported.
Dependency information
Claims derived from the same statement are statistically related. This matters when applying BH correction.

Other helpful measures to consider:
-retrieve broadly from abstracts, verify with full-text passages where accessible, and measure whether the added context improves evidence-grounded judgments 
-Before the user's prompt ever reaches your main agent, run it through a lightweight classifier to detect prompt injections, off-topic requests, or malicious intent. 
-checking if the generated citation string exactly matches a substring in the provided context 
- introduce a verifier node -The verifier evaluates the structured output of the first node against the original system prompt using Natural Language Inference (NLI) and routes it back for a retry if a rule was violated.























Limitations mentioned:
BioKGBench:
Need for granular metrics
Binary evaluation limitation
SCV scope limitation(uses abstracts rather than full text )

MedRAGChecker (check claims made by biomedical RAG systems. )
	-teacher supervision bias
	-kg coverage
	-scope limited to RAG outputs


HEG‑TKG (help an AI produce clinical explanations that people can trace back to biomedical sources, while representing when symptoms or disease events tend to occur. )
	-limited disease coverage
	-Full-text evidence gap (uses abstracts)

Fast-Checking Generative AI:
	-Closed-World Assumption 
	-aggregate links do not check relation meaning 
	-limited sample size




Paper
What it does
Limitations acknowledged in the paper
Fact-Checking Generative AI: Ontology-Driven Biological Graphs for Disease–Gene Link Verification — Hamed et al., 2023, preprint
Builds a reference biological graph from roughly 200,000 PubMed abstracts using disease and gene ontologies. It compares aggregate disease–gene, gene–gene and disease–disease links extracted from ChatGPT-generated simulated articles against the literature graph. Reported link-overlap accuracy ranges from 70–86%. arxiv.org
Assumes a closed world: anything outside the literature graph cannot be validated. Verification is at aggregate link level and does not inspect the precise semantics of each relation. Evaluation covers generated abstracts and a limited set of entity/relation types; the authors propose testing other domains and ontologies as future work.
Triangulating Evidence in Health Sciences with Annotated Semantic Queries—ASQ — Liu & Gaunt, Bioinformatics, 2024
Converts free text into subject–predicate–object claims using SemRep. It normalizes entities and retrieves supporting, reversing, insufficient and contextual evidence from EpiGraphDB, including literature triples and genetic-association analyses. It ranks evidence by relevance and estimated strength while retaining links to the source data. academic.oup.com
Claim extraction can miss or misinterpret claims. SemMedDB triples lack section-level context and may represent hypotheses rather than conclusions; SemRep has limited extraction performance. Literature evidence is affected by publication bias, and EpiGraphDB/OpenGWAS coverage is incomplete, so ASQ is explicitly an evidence-identification aid rather than a comprehensive fact-checker. academic.oup.com
BioKGBench: A Knowledge Graph Checking Benchmark of AI Agent for Biomedical Science — Lin et al., 2024, preprint
Introduces claim-verification, biomedical KGQA and the combined KGCheck task. BKGAgent uses a leader, KG agent and literature-validation agent to inspect KG nodes, attributes and relations. The benchmark contains more than 2,000 atomic-task examples and 225 expert-annotated KGCheck cases. arxiv.org
Tasks provide predefined checking instructions rather than discovering errors autonomously. Evaluation is mainly atomic node/triple inspection; binary questions permit chance success, and exact-match scoring cannot distinguish a correct evidence process from a lucky final answer. Agent coordination and leader errors can propagate into incorrect conclusions.
TripleCheck: Transparent Post-Hoc Verification of Biomedical Claims in AI-Generated Answers — González et al., HCI+NLP 2025
Extracts atomic triples from biomedical AI answers and compares them with both the answer’s retrieved context and a large biomedical KG. It classifies claims as supported, unsupported or contradicted and exposes the relevant evidence to the user. Its SciFact development-set experiment reports approximately 0.70 zero-shot F1. aclanthology.org
The evaluation is preliminary and does not include a large user study. KG incompleteness particularly affects recent and rare knowledge, while extraction can split, merge or represent claims incorrectly. The added checking stages increase latency and interface complexity, and proprietary components make exact replication harder.
MedRAGChecker: Claim-Level Verification for Biomedical Retrieval-Augmented Generation — Ji et al., 2026, preprint
Decomposes long biomedical RAG answers into atomic SPO claims. Each claim is assessed through textual NLI over retrieved passages and a KG plausibility signal from DRKG or BioPortal; KG fusion is gated when conflict is sufficiently strong. Results are aggregated into faithfulness, under-evidence, contradiction and safety-critical diagnostics. arxiv.org
GPT-4.1 teacher labels can transmit errors and biases, particularly for rare or ambiguous claims. Contradictions are relatively scarce and subtle contradictions remain difficult. KG coverage and entity-linking failures materially limit performance; human evaluation is comparatively small, and transferring to another biomedical domain can require another KG and renewed distillation.
Complementary Evidence Pathways for LLM-Based Gene–Disease Plausibility Assessment—GAIA — Yu et al., IEEE ICHI 2026
GAIA evaluates gene–disease plausibility through complementary pathways: a scientific-literature claim-verification component and a structured KG pathway. The system investigates whether structured biological connections improve an LLM’s graded plausibility assessment under different retrieval depths. It is one of the closest comparisons for a combined KG-plus-literature verdict. ieeexplore.ieee.org
The paper’s demonstrated scope is gene–disease plausibility, rather than arbitrary biomedical predicates or multi-claim questions. Its conclusions depend on coverage in the selected literature and graph resources. I could not identify a separate, explicit limitations section in the publicly accessible paper text, so these are reported experimental scope boundaries rather than inferred defects.
KG-Orchestra: An Open-Source Multi-Agent Framework for Evidence-Based Biomedical Knowledge Graph Enrichment — Mohamed et al., bioRxiv 2026
Starts with a seed biomedical KG and uses coordinated agents to retrieve PubMed/PMC evidence, construct directional paths, align relations to a schema, normalize entities and validate or repair each hop. Accepted relations retain PMCID/DOI, excerpts and validation provenance. Its primary goal is evidence-grounded KG enrichment rather than verdicting arbitrary user claims. biorxiv.org
Evaluation is a focused proof of concept involving specialised seed graphs and pathway-oriented enrichment, so generalisation to other biomedical schemas is not yet established. Performance depends on seed-graph quality, retrieval coverage, ontology alignment and LLM validation. The publicly accessible record did not expose a clearly separated limitations section, so these are boundaries described through the study design and discussion.
DeepEvidence: Empowering Biomedical Evidence Exploration and Synthesis with Deep Knowledge Graph Research — Wang et al., Nature Machine Intelligence, 2026
Uses coordinated breadth-first and depth-first exploration over heterogeneous biomedical KGs, literature, clinical trials and related sources. It incrementally constructs a traceable evidence graph connecting genes, drugs, pathways, diseases and clinical findings. It evaluates discovery, preclinical, trial and evidence-based medicine research tasks. arxiv.org
Coverage remains incomplete and its benchmarks represent only a subset of biomedical research tasks. It relies on well-curated KGs and usable APIs, creating difficulty with proprietary sources, missing data and inconsistent interfaces. The authors also identify the need for more explicit probabilistic or uncertainty-aware reconciliation of conflicting and context-dependent evidence.
Building Evidence-Based Knowledge Graphs from Full-Text Literature for Disease-Specific Biomedical Reasoning—EvidenceNet — Zong et al., 2026, preprint
Converts full-text papers into structured evidence nodes that preserve provenance, PICO-like study context and quantitative findings rather than flattening everything into triples. It releases HCC and CRC graphs with thousands of evidence records and typed semantic relations. The graphs support RAG, link prediction and therapeutic-target prioritisation. arxiv.org
Coverage is limited to recent, accessible full-text PubMed articles for HCC and CRC; absence from the graph is therefore not evidence of biological absence. Cold-start entities and incomplete ontology alignment remain problems. Graph proximity cannot be interpreted directly as clinical support because preclinical, translational and clinical results coexist and must be inspected in their original context. arxiv.org


