# DataOps & System Reliability Report

## 1. System Reliability Architecture
To ensure Martin Kleppmann's core pillars of Reliability, Scalability, and Maintainability, the pipeline incorporates the following safeguards:

### Fault Tolerance & Isolation
The traditional approach of halting a data pipeline upon encountering corrupt data leads to brittle architecture, reducing total uptime. Instead, this pipeline separates valid data from malformed data natively using vectorized `pandas` operations masked with specific validation conditions (e.g. checking for negative values or null identifier).
- **Graceful degradation**: Corrupted telemetry logs do not disrupt the pipeline flow. They are efficiently isolated into a discrete CSV (`quarantine/failed_vitals.csv`), making them available for manual review by data stewards without blocking analytics workloads.
- **Fail-safe Logging**: Exceptions that breach schema definitions are caught with global `try-except` blocks. All critical execution steps are output into the operational ledger in `logs/hospital_ops.log`.

### Idempotency Guarantee
Idempotency ensures that rerunning a script against the same input dataset will always produce an identical final state. In this architecture:
- Output repositories (`data/lakehouse/` and `quarantine/failed_vitals.csv`) are routinely cleared at the start of each execution. 
- The log file handler operates in overwrite (`'w'`) mode, ensuring each execution produces a clean, single-run trace without residual entries from previous runs.
- Repeated execution of the orchestrator will not result in row duplication inside the Data Lake or the quarantine ledger.

## 2. PII Security & Compliance
As Patient Telemetry contains highly sensitive Personally Identifiable Information (PII) mapped to medical outcomes, safeguarding identity tracking is an utmost priority:

### Cryptographic Identity Masking
Regulatory directives (like HIPAA) mandate the obscuration of Personal Health Information (PHI).
- Text fields `patient_name` and `patient_id` are strictly standardized before passing through **SHA-256 cryptographic hashing** via Python's built-in `hashlib` module.
- This implementation turns highly mutable human identities into fixed-length hex digests, structurally preventing reverse engineering back to plaintext without heavily resourced dictionary attacks.
- **Both clean and quarantined records** are hashed before being written to any output target. This ensures that even corrupted rows archived in `quarantine/failed_vitals.csv` do not expose raw patient identifiers, maintaining end-to-end compliance boundaries across all output streams.
- Analytics models (like machine learning predictive engines relying upon past telemetry) can still successfully track specific patients longitudinally using these hash keys without explicitly compromising personal identities.

### Text Sanitization
The `department` field arrives from the source system with inconsistent formatting — irregular whitespace padding and random uppercase casing. Before any analytical processing:
- `.str.strip()` removes leading and trailing whitespace.
- `.str.lower()` normalizes all department names to lowercase, ensuring consistent partition key generation downstream.

## 3. Storage Serialization & Partitioning Architecture
The final analytical output is serialized into **Apache Parquet** format using the PyArrow engine, chosen over flat text formats (CSV/JSON) for several critical reasons:

### Why Parquet over CSV/JSON
- **Columnar storage**: Parquet stores data column-by-column rather than row-by-row, enabling analytical engines to read only the columns needed for a given query, drastically reducing I/O.
- **Native type preservation**: Unlike CSVs (which serialize everything as text), Parquet preserves native data types (integers, floats, timestamps) in the binary schema, eliminating type drift on read-back.
- **Built-in compression**: Snappy compression is applied during serialization, reducing disk footprint by up to 80% compared to equivalent CSVs while maintaining near-instantaneous decompression speeds.

### Hive-Style Partitioning
The lakehouse output is organized using Hive-style directory partitioning with two levels:
```
data/lakehouse/
├── dept=cardiology/
│   ├── year=2025/
│   └── year=2026/
├── dept=emergency/
│   ├── year=2025/
│   └── year=2026/
└── ...
```
- The `key=value/` folder convention allows query engines (Spark, Athena, Presto) to perform **partition pruning** — skipping entire directory subtrees that don't match WHERE clause filters.
- This transforms full-table scans into targeted sub-directory reads, reducing query latency proportionally to the selectivity of the partition predicate.
