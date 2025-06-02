import os
from typing import List
from typing_extensions import LiteralString
import requests
import openai
import streamlit as st
from dotenv import load_dotenv
from sn_rag_engine import SnRAGEngine

API_ENV_KEY_NAMES = {"OpenAI": "OPENAI_API_KEY", "together.ai": "TOGETHER_API_KEY", "Fireworks AI": "FIREWORKS_API_KEY"}
PROVIDERS = {"OpenAI": "openai", "together.ai": "together", "Fireworks AI": "fireworks"}

# Load environment variables
load_dotenv()

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

def validate_openai_key(api_key: str) -> bool:
    try:
        client = openai.OpenAI(api_key=api_key)
        client.models.list()
        return True
    except openai.AuthenticationError:
        return False
    except Exception:
        return False

def validate_together_key(api_key: str) -> bool:
    url = "https://api.together.xyz/v1/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/Mistral-7B-Instruct-v0.1",  # public model
        "prompt": "Hello",
        "max_tokens": 1,
        "temperature": 0
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        st.info(response.content)
        if response.status_code == 200 and "error" not in response.json():
            return True
        return False
    except Exception:
        return False

def validate_fireworks_key(api_key: str) -> bool:
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get("https://api.fireworks.ai/inference/v1/models", headers=headers, timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def run_query(provider: str, api_key: str):
    try:
        with st.spinner("Running query across selected years..."):
            # Set LLM provider and API key
            SnRAGEngine.set_llm(provider, api_key=api_key)

            st.chat_message("user").markdown(query)
            logger = StreamlitLogger()
            engine = SnRAGEngineWithUI(
                logger=logger,
                transcripts_dir="./transcripts",
                index_dir="./index",
                summary_prompt=summary_prompt if summary_prompt.strip() else None,
                debug_mode=debug_mode,
            )

            result = engine.query_range(
                query_text=query,
                start_year=start_year,
                end_year=end_year,
                show_intermediate=show_intermediate,
            )

        st.chat_message("assistant").markdown(str(result))

    except Exception as e:
        st.error(f"❌ An error occurred: {e}")
        st.stop()


def run():
    global start_year, end_year, api_key, show_intermediate, debug_mode, summary_prompt, query
    # Streamlit UI
    st.title("🔍 Security Now Transcript Query")
    st.markdown("Run RAG-powered queries over Security Now podcast transcripts by year range.")
    with st.sidebar:
        st.title("🔧 Settings")
        start_year = st.number_input("Start Year", min_value=2015, max_value=2025, value=2016)
        end_year = st.number_input("End Year", min_value=2015, max_value=2025, value=2018)
        provider = st.selectbox("LLM Provider", ["OpenAI", "together.ai", "Fireworks AI"], index=0)
        user_api_key = st.text_input("API Key", placeholder="Enter your API key")
        api_key = None
        if user_api_key == os.getenv("PASSWORD"):
            api_key = os.getenv(API_ENV_KEY_NAMES.get(provider), "INVALID")
        else:
            api_key = user_api_key.strip()
            if not api_key:
                api_key = "INVALID"
    # show_intermediate = st.checkbox("Show intermediate year results", value=False)
    show_intermediate = False
    # debug_mode = st.checkbox("Enable debug mode", value=False)
    debug_mode = False
    # summary_prompt = st.text_area("Custom Summary Prompt (optional)", "")
    summary_prompt = ""
    VALIDATORS = {
        "OpenAI": validate_openai_key,
        "together.ai": validate_together_key,
        "Fireworks AI": validate_fireworks_key,
    }
    if query := st.chat_input("What did Steve say about VPNs?"):
        if start_year > end_year:
            st.error("Start year must be less than or equal to end year.")
        elif not query.strip():
            st.error("Query must not be empty.")
        elif api_key == "INVALID":
            st.error("❌ API key is required to proceed.")
            st.stop()
        elif not VALIDATORS[provider](api_key):
            st.error("❌ API key appears to be invalid.")
            st.stop()
        else:
            run_query(PROVIDERS[provider], api_key)


run()
