import argparse
import os
from typing import Optional, Dict, List

import openai
from dotenv import load_dotenv
from llama_index.core import Settings, Document, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.base.llms.types import CompletionResponse
from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
from llama_index.core.schema import TextNode, BaseNode
from llama_index.llms.openai import OpenAI

TRANSCRIPTS_DIR = "./transcripts"
INDEX_DIR = "./index"
MIN_YEAR = 2015
MAX_YEAR = 2025


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


def get_index(docs_filepath: str, index_filepath: str) -> VectorStoreIndex:
    try:
        index = load_index_from_storage(StorageContext.from_defaults(persist_dir=index_filepath))
    except Exception:
        nodes = load_docs(docs_filepath)
        index = VectorStoreIndex(nodes)
        index.storage_context.persist(persist_dir=index_filepath)
    return index

def query_all_years(query_text: str, show_intermediate: bool = False, debug_mode: bool = False) -> CompletionResponse:
    return query_years(MIN_YEAR, MAX_YEAR, query_text, show_intermediate=show_intermediate, debug_mode=debug_mode)

def query_years(start_year: int, end_year: int, query_text: str, show_intermediate: bool = False, debug_mode: bool = False,
                transcripts_dir: str = TRANSCRIPTS_DIR, index_dir: str = INDEX_DIR, summary_prompt: str = None) -> CompletionResponse:
    all_responses = []
    for year in range(start_year, end_year+1):
        response = query_year(query_text, year, debug_mode, transcripts_dir, index_dir)
        response_with_year = f"\n--- {year} ---\n{response}\n"
        all_responses.append(response_with_year)
        if show_intermediate:
            print(response_with_year)

    if len(all_responses) > 1:
        if summary_prompt is None:
            summary_prompt = ("The original query per year was: '{query_text}'\n. "
                              "Following are the responses we got from querying the transcripts per year. "
                              "Combine the answers we got from all years into a single coherent answer:\n\n{responses}")
        combined_prompt = summary_prompt.format(query_text=query_text, responses="\n".join(all_responses))
        final_response = Settings.llm.complete(combined_prompt)
    else:
        final_response = all_responses[0]
    return final_response


def query_year(query_text: str, year: int, debug_mode: bool, transcripts_dir: str, index_dir: str) -> RESPONSE_TYPE:
    if debug_mode:
        llama_debug_handler = LlamaDebugHandler(print_trace_on_end=True)
        Settings.callback_manager = CallbackManager([llama_debug_handler])
    index = get_index(f"{transcripts_dir}/{year}", f"{index_dir}/{year}")
    retriever = VectorIndexRetriever(index=index, similarity_top_k=32)
    query_engine = RetrieverQueryEngine(retriever=retriever)
    response = query_engine.query(query_text)
    return response


def main():
    parser = argparse.ArgumentParser(description="Query podcast transcripts by year range and summarize results.")
    parser.add_argument("-sy", "--start-year", type=int, required=True, help="Start year for querying transcripts")
    parser.add_argument("-ey", "--end-year", type=int, required=True, help="End year for querying transcripts")
    parser.add_argument("-q", "--query", type=str, required=True, help="Query to execute")
    parser.add_argument("--hide-intermediate", action="store_true", default=False, help="Hide intermediate yearly results")
    parser.add_argument("--transcripts-dir", type=str, default=TRANSCRIPTS_DIR, help="Directory containing transcript files")
    parser.add_argument("--index-dir", type=str, default=INDEX_DIR, help="Directory containing index files")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Show debug information")
    parser.add_argument("--summary-prompt", type=str, default="The original query per year was: '{query_text}'\n. Following are the responses we got from querying the transcripts per year. Combine the answers we got from all years into a single coherent answer:\n\n{responses}", help="Custom summary prompt template. Use '{query_text}' and '{responses}' as placeholders.")
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

    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: The environment variable OPENAI_API_KEY is missing. Please set it in your .env file.")
        exit(1)
    openai.api_key = api_key
    Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)


    result = query_years(
        start_year=args.start_year,
        end_year=args.end_year,
        query_text=args.query,
        debug_mode=args.debug,
        show_intermediate=not args.hide_intermediate,
        transcripts_dir=args.transcripts_dir,
        index_dir=args.index_dir,
        summary_prompt=args.summary_prompt
    )
    print("\n\n=== Summary result ===")
    print(result)


if __name__ == '__main__':
    main()

