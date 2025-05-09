import argparse
import os
import time
from typing import Optional, Dict, List

from dotenv import load_dotenv
from llama_index.core import Settings, Document, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
from llama_index.core.schema import BaseNode

# Uncomment to get verbose logging info
# import logging
# logging.basicConfig(level=logging.DEBUG)


TRANSCRIPTS_DIR = "./transcripts"
INDEX_DIR = "./index"
MIN_YEAR = 2015
MAX_YEAR = 2025
SUMMARY_PROMPT = ("Following are year-by-year responses to the query :\n" 
                  "<QUERY> {query_text} </QUERY>\n\n " 
                  "Combine the responses below from **all years** into a single coherent answer for the query:\n\n"
                  "<RESPONSES>{responses}</RESPONSES>")

EMBED_MODEL_FILE = "embed_model.txt"

class SnTextFileReader(BaseReader):
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def load_data(self, file_path: str, extra_info: Optional[Dict] = None) -> List[BaseNode]:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        cleaned_text = raw_text.replace("\r\n\r\n", " ").replace("\n\n", " ")
        document = Document(text=cleaned_text, metadata=extra_info or {})
        return self.parser.get_nodes_from_documents([document])

def load_docs(directory: str) -> List[BaseNode]:
    nodes = []
    for fname in os.listdir(directory):
        if fname.endswith(".txt"):
            path = os.path.join(directory, fname)
            reader = SnTextFileReader()
            file_nodes = reader.load_data(path, extra_info={"file_name": fname})
            for node in file_nodes:
                node.excluded_llm_metadata_keys = ["file_name"]
            nodes.extend(file_nodes)
    return nodes


def get_index(docs_filepath: str, index_filepath: str, debug_mode: bool = False) -> VectorStoreIndex:
    embed_info_path = os.path.join(index_filepath, EMBED_MODEL_FILE)
    embed_model_id = get_model_id()
    try:
        # Validate stored embedding model
        if os.path.exists(embed_info_path):
            with open(embed_info_path, "r") as f:
                stored_model_id = f.read().strip()
            if stored_model_id != embed_model_id:
                raise ValueError(f"Embedding model mismatch: expected '{embed_model_id}', found '{stored_model_id}'")
        if debug_mode:
            start_time = time.time()
        index = load_index_from_storage(StorageContext.from_defaults(persist_dir=index_filepath))
        if debug_mode:
            elapsed_time = time.time() - start_time
            print(f"✅ Index loaded in {elapsed_time:.2f} seconds")
    except Exception:
        nodes = load_docs(docs_filepath)
        index = VectorStoreIndex(nodes)
        index.storage_context.persist(persist_dir=index_filepath)
        with open(embed_info_path, "w") as f:
            f.write(embed_model_id)
    return index


def query_all_years(query_text: str, show_intermediate: bool = False, debug_mode: bool = False) -> str:
    return query_years(MIN_YEAR, MAX_YEAR, query_text, show_intermediate=show_intermediate, debug_mode=debug_mode)


def query_years(start_year: int, end_year: int, query_text: str, show_intermediate: bool = False, debug_mode: bool = False,
                transcripts_dir: str = TRANSCRIPTS_DIR, index_dir: str = INDEX_DIR, summary_prompt: str = None) -> str:
    all_responses = []
    for year in range(start_year, end_year + 1):
        response = query_year(query_text, year, debug_mode, transcripts_dir, index_dir)
        response_with_year = f"\n--- {year} ---\n{response}\n"
        all_responses.append(response_with_year)
        if show_intermediate:
            print(response_with_year)

    if len(all_responses) > 1:
        combined_prompt = summary_prompt.format(query_text=query_text, responses="\n".join(all_responses))
        #print(combined_prompt)
        final_response = Settings.llm.complete(combined_prompt)
    else:
        final_response = all_responses[0]
    return final_response


def get_model_id():
    """
    Return an ID representing the model used
    :return: model ID
    """
    model_class = Settings.embed_model.__class__.__name__
    model_config = getattr(Settings.embed_model, 'model_name', getattr(Settings.embed_model, 'model', 'unknown'))
    embed_model_id = f"{model_class}:{model_config}"
    return embed_model_id


def query_year(query_text: str, year: int, debug_mode: bool, transcripts_dir: str, index_dir: str) -> RESPONSE_TYPE:
    if debug_mode:
        llama_debug_handler = LlamaDebugHandler(print_trace_on_end=True)
        Settings.callback_manager = CallbackManager([llama_debug_handler])
    index = get_index(f"{transcripts_dir}/{year}", f"{index_dir}/{year}", debug_mode)
    retriever = VectorIndexRetriever(index=index, similarity_top_k=getattr(Settings, "similarity_top_k", 32))
    #from llama_index.core.response_synthesizers import get_response_synthesizer
    #from llama_index.core.response_synthesizers import ResponseMode
    query_engine = RetrieverQueryEngine(retriever=retriever) #, response_synthesizer=get_response_synthesizer(response_mode=ResponseMode.REFINE))
    response = query_engine.query(query_text)
    return response


def set_llm(provider: str):
    """
    Sets the LLM (and embedding model) according to the provider
    :param provider: provider's name
    :return: None
    """
    def openai_handler():
        try:
            from llama_index.llms.openai import OpenAI
            from llama_index.embeddings.openai import OpenAIEmbedding
            Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        except ImportError:
            raise ImportError("The 'openai' LLM provider requires installing llama-index-llms-openai. Please install it with pip.")
        Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
        Settings.similarity_top_k_ = 32

    def together_handler():
        try:
            from llama_index.llms.together import TogetherLLM
            from llama_index.embeddings.fireworks import FireworksEmbedding
            # Together.ai's embedding model is commented out since I gave up on them,
            # they were very slow and yielded bad results.
            # from llama_index.embeddings.together import TogetherEmbedding
            # Settings.embed_model = TogetherEmbedding(model_name="togethercomputer/m2-bert-80M-2k-retrieval")

            # Provide a template following the LLM's original chat template.
            # This was taken from https://www.together.ai/blog/rag-tutorial-llamaindex
            def completion_to_prompt(completion: str) -> str:
                return f"<s>[INST] {completion} [/INST] </s>\n"

            Settings.embed_model = FireworksEmbedding(model_name="nomic-ai/nomic-embed-text-v1.5")
        except ImportError:
            raise ImportError("The 'together' LLM provider requires installing llama-index-llms-together and "
                              "lllama-index-embeddings-fireworks. Please install it with pip.")
        # Llama-3 models yielded bad results so I switched to Mixtral
        Settings.llm = TogetherLLM(model="mistralai/Mixtral-8x7B-Instruct-v0.1", api_key=os.environ["TOGETHER_API_KEY"],
                                   temperature=0, is_chat_model=False, completion_to_prompt=completion_to_prompt)
        Settings.similarity_top_k = 16

    def fireworks_handler():
        try:
            from llama_index.llms.fireworks import Fireworks
            from llama_index.embeddings.fireworks import FireworksEmbedding
            Settings.embed_model = FireworksEmbedding(model_name="nomic-ai/nomic-embed-text-v1.5")
        except ImportError:
            raise ImportError("The 'fireworks' LLM provider requires installing llama-index-llms-fireworks and "
                              "llama-index-embeddings-fireworks. Please install it with pip.")
        # had to enlarge the max_tokens since the final output got truncated
        # Settings.llm = Fireworks(model="accounts/fireworks/models/llama-v3p1-8b-instruct", api_key=os.environ["FIREWORKS_API_KEY"],
        #                          temperature=0, max_tokens=4096)
        Settings.llm = Fireworks(model="accounts/fireworks/models/mixtral-8x22b-instruct", api_key=os.environ["FIREWORKS_API_KEY"], temperature=0)
        Settings.similarity_top_k = 32

    switch_dict = {
        "openai": openai_handler,
        "together": together_handler,
        "fireworks": fireworks_handler,
    }

    handler = switch_dict.get(provider, openai_handler)
    return handler()


def main():
    parser = argparse.ArgumentParser(description="Query podcast transcripts by year range and summarize results.")
    parser.add_argument("-sy", "--start-year", type=int, required=True, help="Start year for querying transcripts")
    parser.add_argument("-ey", "--end-year", type=int, required=True, help="End year for querying transcripts")
    parser.add_argument("-q", "--query", type=str, required=True, help="Query to execute")
    parser.add_argument("--hide-intermediate", action="store_true", default=False, help="Hide intermediate yearly results")
    parser.add_argument("--transcripts-dir", type=str, default=TRANSCRIPTS_DIR, help="Directory containing transcript files")
    parser.add_argument("--index-dir", type=str, default=INDEX_DIR, help="Directory containing index files")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Show debug information")
    parser.add_argument("--summary-prompt", type=str, default=SUMMARY_PROMPT, help="Custom summary prompt template. Use '{query_text}' and '{responses}' as placeholders.")
    args = parser.parse_args()

    if args.start_year < MIN_YEAR or args.end_year > MAX_YEAR:
        print(f"Start year must be >= {MIN_YEAR} and end year must be <= {MAX_YEAR}.")
        exit(1)
    if args.start_year > args.end_year:
        print("Start year must be <= end year.")
        exit(1)
    if not args.query.strip():
        print("Query must not be empty.")
        exit(1)
    if not args.summary_prompt.strip():
        print("Summary prompt must not be empty.")
        exit(1)

    load_dotenv()

    provider = os.getenv("LLM_PROVIDER", "openai")
    set_llm(provider)

    result = query_years(
        start_year=args.start_year,
        end_year=args.end_year,
        query_text=args.query,
        debug_mode=args.debug,
        show_intermediate=not args.hide_intermediate,
        transcripts_dir=args.transcripts_dir,
        index_dir=args.index_dir,
        summary_prompt=args.summary_prompt,
    )
    print("\n\n=== Summary result ===")
    print(result)


if __name__ == '__main__':
    main()
