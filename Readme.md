# Security Now Transcript Query Engine

This Python program allows you to build a retrieval-augmented generation (RAG) pipeline over Steve Gibson's Security Now podcast transcripts. You can query a range of years and get a coherent, LLM-generated answer based on indexed podcast content.

---

## Features

- Loads and parses text transcripts with chunked context windows
- Creates per-year vector indexes (2015 to 2025)
- Runs queries across a year range
- Optionally prints intermediate results
- Final summary synthesized by OpenAI's GPT-4o-mini

---

## How to Use

### 1. Install Dependencies
```bash
pip install llama-index openai python-dotenv
```

### 2. Download Transcripts
You can get Security Now transcripts from:
- https://www.grc.com/securitynow.htm

To download a range of `.txt` transcripts (e.g., episodes 480 to 500):
```bash
mkdir -p transcripts
cd transcripts
for i in {480..500}; do wget "https://www.grc.com/sn/sn-${i}.txt"; done
cd ..
```

Each `.txt` file should include a line starting with `DATE:` in this format:
```
DATE:		May 26, 2015
```
This will be used to auto-sort transcripts into per-year directories.

### 3. Sort Transcripts by Year
Use the included `sortfiles.py` script to organize `.txt` files into year folders based on the date in each file:
```bash
python sortfiles.py
```
This will move files into `./transcripts/2015`, `./transcripts/2016`, ..., `./transcripts/2025` automatically.

### 4. Set Up API Key
Create a `.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### 5. Run the Program
```bash
python snquery.py \
  -sy 2016 \
  -ey 2018 \
  -q "What did Steve say about VPNs?" \
  --hide-intermediate  # Optional: Hide intermediate year responses
```

### Flags
| Flag           | Long Form             | Description                                                             |
|----------------|------------------------|-------------------------------------------------------------------------|
| `-sy`          | `--start-year`         | Starting year for querying transcripts (>= 2015)                        |
| `-ey`          | `--end-year`           | Ending year for querying transcripts (<= 2025)                          |
| `-q`           | `--query`              | Your natural language query                                             |
|                | `--hide-intermediate`  | Hide intermediate year responses (default behavior shows intermediate)  |
|                | `--transcripts-dir`    | Directory containing transcript files (default: ./transcripts)          |
|                | `--index-dir`          | Directory containing index files (default: ./index)                     |
| `-d`           | `--debug`              | Print LLM internal debug prompts                                        |

---

## Notes
- Make sure transcripts are organized into folders like `./transcripts/2015`, `./transcripts/2016`, etc.
- The indexing happens on first use per year and is cached.
- You can delete `./index/*` folders to rebuild indexes.

---

## License
GNU Affero General Public License v3.0

