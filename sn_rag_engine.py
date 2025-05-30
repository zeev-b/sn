import os
import time
from typing import List, Optional

from llama_index.core import Settings, Document, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import BaseNode
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler

TRANSCRIPTS_DIR = "./transcripts"
INDEX_DIR = "./index"
SUMMARY_PROMPT = (
    "Following are year-by-year responses to the query :\n"
    "<QUERY> {query_text} </QUERY>\n\n"
    "Combine the responses below from **all years** into a single coherent answer for that query:\n\n"
    "<RESPONSES>{responses}</RESPONSES>"
)
EMBED_MODEL_FILE = "embed_model.txt"

class SnTextFileReader(BaseReader):
    """Custom file reader for text documents with sentence splitting."""
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def load_data(self, file_path: str, extra_info: Optional[dict] = None) -> List[BaseNode]:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        cleaned_text = raw_text.replace("\r\n\r\n", " ").replace("\n\n", " ")
        document = Document(text=cleaned_text, metadata=extra_info or {})
        return self.parser.get_nodes_from_documents([document])

class SnRAGEngine:
    """
    Core RAG engine for querying podcast transcripts organized by year.
    Suitable for use in CLI, REST APIs, or other backends.
    """
    def __init__(
        self,
        transcripts_dir: str = TRANSCRIPTS_DIR,
        index_dir: str = INDEX_DIR,
        summary_prompt: str = SUMMARY_PROMPT,
        debug_mode: bool = False
    ) -> None:
        self.transcripts_dir = transcripts_dir or TRANSCRIPTS_DIR
        self.index_dir = index_dir or INDEX_DIR
        self.summary_prompt = summary_prompt or SUMMARY_PROMPT
        self.debug_mode = debug_mode

    def query_year(self, query_text: str, year: int) -> str:
        """Query a single year's index."""
        if self.debug_mode:
            llama_debug_handler = LlamaDebugHandler(print_trace_on_end=True)
            Settings.callback_manager = CallbackManager([llama_debug_handler])
        index = self.get_index(f"{self.transcripts_dir}/{year}", f"{self.index_dir}/{year}")
        retriever = VectorIndexRetriever(index=index, similarity_top_k=getattr(Settings, "similarity_top_k", 32))
        # from llama_index.core.response_synthesizers import get_response_synthesizer
        # from llama_index.core.response_synthesizers import ResponseMode
        query_engine = RetrieverQueryEngine(retriever=retriever)  #, response_synthesizer=get_response_synthesizer(response_mode=ResponseMode.REFINE))
        response = query_engine.query(query_text)
        return str(response)

    def query_range(self, query_text: str, start_year: int, end_year: int, show_intermediate: bool = False) -> str:
        """Query a range of years and summarize the results."""
        responses = []
        for year in range(start_year, end_year + 1):
            response = self.query_year(query_text, year)
            wrapped = f"\n--- {year} ---\n{response}\n"
            if show_intermediate:
                print(wrapped)
            responses.append(wrapped)
        return self._summarize_responses(query_text, responses)

    def _summarize_responses(self, query_text: str, responses: List[str]) -> str:
        """Combine yearly responses into a single coherent summary."""
        if len(responses) == 1:
            return responses[0]
        prompt = self.summary_prompt.format(query_text=query_text, responses="\n".join(responses))
        return Settings.llm.complete(prompt)

    def get_index(self, docs_path: str, index_path: str) -> VectorStoreIndex:
        """Load or create a vector index for a given path."""
        embed_info_path = os.path.join(index_path, EMBED_MODEL_FILE)
        embed_model_id = self.get_model_id()
        try:
            if os.path.exists(embed_info_path):
                with open(embed_info_path, "r") as f:
                    stored_model_id = f.read().strip()
                if stored_model_id != embed_model_id:
                    raise ValueError(f"Embedding model mismatch: expected '{embed_model_id}', found '{stored_model_id}'")
            if self.debug_mode:
                start_time = time.time()
            index = load_index_from_storage(StorageContext.from_defaults(persist_dir=index_path))
            if self.debug_mode:
                elapsed = time.time() - start_time
                print(f"✅ Index loaded in {elapsed:.2f} seconds")
        except Exception:
            nodes = self.load_docs(docs_path)
            index = VectorStoreIndex(nodes)
            index.storage_context.persist(persist_dir=index_path)
            with open(embed_info_path, "w") as f:
                f.write(embed_model_id)
        return index

    def load_docs(self, directory: str) -> List[BaseNode]:
        """Load and parse documents from a directory."""
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

    def get_model_id(self) -> str:
        """Return a string ID representing the current embedding model."""
        model_class = Settings.embed_model.__class__.__name__
        model_config = getattr(Settings.embed_model, 'model_name', getattr(Settings.embed_model, 'model', 'unknown'))
        return f"{model_class}:{model_config}"

    @staticmethod
    def set_llm(provider: str) -> None:
        """Set the global LLM and embedding model used by llama-index."""
        def openai_handler():
            # The 'openai' LLM provider requires installing llama-index-llms-openai.
            from llama_index.llms.openai import OpenAI
            from llama_index.embeddings.openai import OpenAIEmbedding
            Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
            Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
            Settings.similarity_top_k = 32

        def together_handler():
            # The 'together' LLM provider requires installing llama-index-llms-together and
            # llama-index-embeddings-fireworks.
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
            Settings.llm = TogetherLLM(
                model="mistralai/Mixtral-8x7B-Instruct-v0.1",
                api_key=os.environ["TOGETHER_API_KEY"],
                temperature=0,
                is_chat_model=False,
                completion_to_prompt=completion_to_prompt
            )
            Settings.similarity_top_k = 16

        def fireworks_handler():
            from llama_index.llms.fireworks import Fireworks
            from llama_index.embeddings.fireworks import FireworksEmbedding
            Settings.embed_model = FireworksEmbedding(model_name="nomic-ai/nomic-embed-text-v1.5")

            # had to enlarge the max_tokens for llama-v3p1-8b-instruct since the final output got truncated
            # Settings.llm = Fireworks(model="accounts/fireworks/models/llama-v3p1-8b-instruct", api_key=os.environ["FIREWORKS_API_KEY"],
            #                          temperature=0, max_tokens=4096)

            Settings.llm = Fireworks(
                model="accounts/fireworks/models/mixtral-8x22b-instruct",
                api_key=os.environ["FIREWORKS_API_KEY"],
                temperature=0,
                max_tokens=4096
            )
            Settings.similarity_top_k = 32

        switch_dict = {
            "openai": openai_handler,
            "together": together_handler,
            "fireworks": fireworks_handler,
        }
        # Run handler
        switch_dict.get(provider, openai_handler)()
