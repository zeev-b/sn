import os
from typing import List

import streamlit as st
from dotenv import load_dotenv
from sn_rag_engine import SnRAGEngine

# Load environment variables
load_dotenv()

# Set default LLM provider
provider = os.getenv("LLM_PROVIDER", "openai")
SnRAGEngine.set_llm(provider)

class StreamlitLogger:
    @staticmethod
    def log(message: str):
        st.info(message)

# Subclass with logging
class SnRAGEngineWithUI(SnRAGEngine):
    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger

    def query_year(self, query_text: str, year: int) -> str:
        self.logger.log(f"🔍 Querying year {year}...")
        return super().query_year(query_text, year)

    def _summarize_responses(self, query_text: str, responses: List[str]) -> str:
        self.logger.log(f"🧠 Summarizing results from {len(responses)} years...")
        return super()._summarize_responses(query_text, responses)

# Streamlit UI
st.title("🔍 Security Now Transcript Query")
st.markdown("Run RAG-powered queries over Security Now podcast transcripts by year range.")

with st.sidebar:
    st.title("🔧 Settings")
    start_year = st.number_input("Start Year", min_value=2015, max_value=2025, value=2016)
    end_year = st.number_input("End Year", min_value=2015, max_value=2025, value=2018)
# show_intermediate = st.checkbox("Show intermediate year results", value=False)
show_intermediate = False
# debug_mode = st.checkbox("Enable debug mode", value=False)
debug_mode = False
# summary_prompt = st.text_area("Custom Summary Prompt (optional)", "")
summary_prompt = ""

if query := st.chat_input("What did Steve say about VPNs?"):
    if start_year > end_year:
        st.error("Start year must be less than or equal to end year.")
    elif not query.strip():
        st.error("Query must not be empty.")
    else:
        st.chat_message("user").markdown(query)
        logger = StreamlitLogger()
        engine = SnRAGEngineWithUI(
            logger=logger,
            transcripts_dir="./transcripts",
            index_dir="./index",
            summary_prompt=summary_prompt if summary_prompt.strip() else None,
            debug_mode=debug_mode,
        )

        with st.spinner("Running query across selected years..."):
            result = engine.query_range(
                query_text=query,
                start_year=start_year,
                end_year=end_year,
                show_intermediate=show_intermediate,
            )

        st.chat_message("assistant").markdown(str(result))
