# Japanese Learning Podcast Tracker (Static Generator)

A lightweight, strictly typed, and functional Python-based static site generator. It tracks the *Nihongo Con Teppei / Radio Nikkei Nagara* podcast feed, translates titles, breaks down vocabulary, and publishes both a clean responsive learning homepage and a secondary vocabulary-enriched RSS feed to GitHub Pages.

---

## 🚀 Key Features

* **Functional & Zero Dependency**: Built using standard library Python modules with zero runtime dependency overhead.
* **Strict Type Safety**: Fully compliant with PEP 585 standard collections and annotated with strict type checking (`mypy --strict`).
* **Self-Healing Feed Tracking**: Scans feed episodes, translates the newest releases via Gemini API, and safely logs rate-limited or failed runs with `is_mock: true` cards, auto-healing them on subsequent runs.
* **Leak-Proof Error Redaction**: Automatic API key redaction in traceback error logs to prevent raw key exposure inside connection exceptions.
* **XSS & RSS Injection Sanitization**: Context-escapes all dynamic fields using standard `html.escape()`, and runs strict schema validations (`http://` or `https://` only) to block script injections.
* **Deterministic Expect Testing**: A highly optimized snapshot/golden-file expect testing suite (`test_build.py`) to prevent layout regressions, executing in less than 10ms.
* **Secure pre-commit Hooks**: Enforces automatic Gitleaks secrets scanning and snapshot unit tests locally before commits are accepted.
* **Secure GitHub Actions Pipeline**: Deploys statically generated artifacts directly to GitHub Pages via secure, first-party actions pinned to cryptographic 40-character SHAs.

---

## 📁 Repository Layout

```
.
├── .github/workflows/      # Secure GitHub Actions workflows
├── .githooks/              # Native pre-commit Git hooks (Gitleaks + tests)
├── test/
│   └── expect/             # Golden Expect/Snapshot files (HTML & XML)
├── build.py                # Core functional static site generator
├── test_build.py           # Unit and Snapshot expectation tests
├── history.json            # Database tracking chronological translations
├── .env                    # Local environment config (GEMINI_API_KEY)
├── .gitleaks.toml          # Gitleaks scanning exclusions & rule configuration
└── README.md               # Project documentation
```

---

## 🛠️ Getting Started

### 1. Prerequisites
Ensure you are using the **Nix** environment where all development tooling is pre-configured:
```bash
nix shell nixpkgs#python313 nixpkgs#mypy nixpkgs#black nixpkgs#gitleaks
```


### 2. Running the Builder
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

Execute the generator:
```bash
python build.py
```
This parses the latest feed items, translates new titles, updates `history.json`, and outputs the generated files in the static workspace.

### 3. Running Tests
Run the expect test suite:
```bash
python test_build.py
```

To update or re-record the golden snapshots when layout changes are intentional:
```bash
UPDATE_EXPECT=1 python test_build.py
```

### 4. Code Quality & Linting
Run formatting and strict type checks:
```bash
black build.py test_build.py
mypy --strict build.py test_build.py
```
