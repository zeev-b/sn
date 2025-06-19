# Security Now Transcript Query Engine

This Python program allows you to build a retrieval-augmented generation (RAG) pipeline over Steve Gibson's Security Now podcast transcripts. 
You can query a range of years and get a coherent, LLM-generated answer based on indexed podcast content.

---

## How it works

- Loads and parses text transcripts with chunked context windows
- Creates a per-year vector index
- Runs the query on each year
- Optionally prints intermediate results (per year result)
- Final summary synthesized by another call to the model

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
Use the included `sortfiles.py` script to organize `.txt` transcript files into year folders based on the date contained in each file. The script will only process files with a `.txt` extension and organize them into folders for each year between `2015` and `2025`.

By default, the script looks for transcripts in the `./transcripts` directory. If your transcripts are located elsewhere, you can specify the target directory using the `--transcripts-dir` parameter. For example:
```bash
python sortfiles.py --transcripts-dir /path/to/your/transcripts
```
If no directory is specified, running:
```bash
python sortfiles.py
```
will default to organizing the files in the `./transcripts` directory. After running the command, the transcript files will be moved into subdirectories, such as `./transcripts/2015`, `./transcripts/2016`, and so on.

### 4. Set Up API Key
Create a `.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### 5. Run the Program
```bash
python sn_cli.py \
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
- Ensure transcripts are organized into folders, such as `./transcripts/2015`, `./transcripts/2016`, etc.
- The indexing happens on first use per year and is cached.
- You can delete `./index/*` folders to rebuild indexes.

---

## License
GNU Affero General Public License v3.0

