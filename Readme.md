# Security Now Transcript Query Engine

This Python program allows you to build a retrieval-augmented generation (RAG) pipeline over Steve Gibson's Security Now podcast transcripts. 
You can query a range of years and get a coherent, LLM-generated answer based on indexed podcast content.

---
### 🚀 **Streamlit App Now Live!**

You can now try the Security Now Query Engine in your browser — no setup required:

👉 [https://snquery.streamlit.app/](https://snquery.streamlit.app/)

---

### 📣 **Mentioned on Security Now!**

This project was mentioned in [Security Now episode #1030](https://youtu.be/u0rMgT-rUIQ?si=SSDwmXG1pidcTvuz), aired on **June 17th, 2025**, during the segment ["An LLM describes Steve's (my) evolution on Microsoft security."](https://youtu.be/u0rMgT-rUIQ?si=SSDwmXG1pidcTvuz&t=6570)  
The answer that Steve read in the podcast is available at [examples/Microsoft-security.txt](examples/Microsoft-security.txt)

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
- The indexing happens on first use per year and is stored in the index directories (`./index/...`).
- You can delete `./index/*` folders to rebuild indexes.


### 6. Run the Streamlit App (Optional)

You can also run a simple web interface to interactively query Security Now transcripts using Streamlit.

```bash
pip install streamlit
streamlit run app.py
```

Once launched, the app will let you:

- Select a year range
- Enter your LLM provider (OpenAI, Together, Fireworks)
- Provide your API key
- Input a query (e.g., “What did Steve say about VPNs?”)


---

### 📁 Streamlit Secrets Configuration

To securely provide your API keys when running the app locally or deploying it to Streamlit Cloud, you should use a `.streamlit/secrets.toml` file.

#### Local Use
Create a file at `.streamlit/secrets.toml` with the following content:

```toml
OPENAI_API_KEY = "your_openai_api_key"
TOGETHER_API_KEY = "your_together_api_key"
FIREWORKS_API_KEY = "your_fireworks_api_key"
PASSWORD = "your_local_access_password"
```

**Note:** The `PASSWORD` key can be used to unlock environment-defined keys instead of inputting them in the UI

#### Deployment on Streamlit Cloud
Go to your app settings on [Streamlit Cloud](https://streamlit.io/cloud) and set the same keys in the **Secrets** tab.

### 📦 Prebuilt Index Files

This repository includes prebuilt vector index files under the `./index` directory for selected years. 
These are included to enable immediate usage of the app, especially when deployed on Streamlit Cloud, 
where building indexes at runtime can be slow or restricted.


### 📝 Optional: Log Queries to Google Sheets

You can optionally enable logging of user queries and RAG-generated responses to a Google Sheet using a free Google Apps Script Web App.

1. Create a Google Sheet and rename one sheet to **"Logs"**
   - Add optional headers: `Timestamp | Query | Response | Provider`
  

2. Open the sheet, go to **Extensions > Apps Script**, and paste in this script:

    ```javascript
    function doPost(e) {
      var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Logs");
      var data = JSON.parse(e.postData.contents);
    
      sheet.appendRow([
        new Date(),
        data.query,
        data.response,
        data.provider
      ]);
    
      return ContentService.createTextOutput("Success").setMimeType(ContentService.MimeType.TEXT);
    }
    ```

3. Deploy it:
   - Click **Deploy > Manage deployments > New deployment**
   - Choose **"Web app"**
   - Set **"Execute as"** to *Me*, and **"Who has access"** to *Anyone*
   - Copy the Web App URL (e.g. `https://script.google.com/macros/s/.../exec`)  
  

4. Add the Web App URL to the `.streamlit/secrets.toml` file:
```toml
LOG_WEBHOOK_URL = "https://script.google.com/macros/s/.../exec"
```
 
**Note:** Google may warn you that the app is unverified. Click "Advanced" and proceed if you trust your own script.

## License
GNU Affero General Public License v3.0
