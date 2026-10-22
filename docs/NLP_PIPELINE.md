# VaaniLink — NLP Language Intelligence Pipeline

## 1. Architectural Philosophy
VaaniLink does not assume that Latin script implies English. In modern vernacular communications across India and globally, users frequently write Romanized Hindi (Hinglish), Romanized Bengali, Romanized Gujarati, or code-mixed sentences (e.g., "me kal nahi aaunga", "kal meeting hai kya?", "haan bro I will come tomorrow").

The NLP pipeline is composed of isolated, modular stages where each step can be evaluated, mocked, and enhanced independently.

---

## 2. Pipeline Sequence

```
Raw Text
   │
   ▼
[1. Unicode Normalization]  ──> Normalizes NFKC, cleans zero-width spaces, strips invalid control chars
   │
   ▼
[2. Protected Token Extraction] ──> Extracts URLs, emails, @mentions, #hashtags, phone numbers, codes
   │
   ▼
[3. Emoji Isolation & Preservation] ──> Preserves Unicode emoji clusters with byte-exact placeholders
   │
   ▼
[4. Script Detection] ──> Detects Unicode blocks (Devanagari, Latin, Arabic, Bengali, Gujarati, etc.)
   │
   ▼
[5. Language Identification & Romanization Analysis]
   ├─ If Latin script: Analyzes dictionary hit rates, n-gram patterns, phonetic romanization markers
   └─ Identifies whether text is Romanized Indic (e.g., Hinglish) vs. standard English
   │
   ▼
[6. Code-Mixed & Segmentation Analysis] ──> Generates token/span-level language classifications
   │
   ▼
[7. Transliteration / Normalization Pre-Processing] ──> Maps romanized tokens to phonetic canonical forms
   │
   ▼
[8. Strategy Selection & Target Routing] ──> Chooses optimal translation strategy for target language
   │
   ▼
[9. Protected Token & Emoji Restoration] ──> Seamlessly re-injects placeholders into translated output
   │
   ▼
[10. Quality Validation & Cache Store] ──> Validates completeness, stores in PostgreSQL cache
```

---

## 3. Protected Tokens Specification
Protected tokens are mapped to unique alphanumeric placeholders (e.g., `__PROT_URL_0__`, `__PROT_EMO_0__`) before entering translation engines, ensuring that:
- URLs (`https://...`) are never translated or corrupted.
- Email addresses and `@usernames` remain identical.
- Unicode emojis (including multi-codepoint sequences, skin tone modifiers, and ZWJ sequences) remain exact.
- Placeholders are restored faithfully in the post-processing stage.
