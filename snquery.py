#
import logging
import sys
from http.client import responses

import openai
import os
from dotenv import load_dotenv
from llama_index.core.readers.base import BaseReader
#from llama_index.llms.gemini import Gemini
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings, Document
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core import SimpleDirectoryReader
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler


class SnTextFileReader(BaseReader):
    def load_data(self, file, extra_info=None):
        with open(file, "r") as f:
            text = f.read()
        cleaned_text = text.replace("\r\n\r\n", " ")
        cleaned_text = cleaned_text.replace("\n\n", " ")
        # load_data returns a list of Document objects
        return [Document(text=cleaned_text, extra_info=extra_info or {})]


def load_docs(filepath):
    """Load docs from a directory, excluding all other file types."""
    loader = SimpleDirectoryReader(
        input_dir=filepath,
        required_exts=[".txt"],
        file_extractor={".txt": SnTextFileReader()}
    )

    documents = loader.load_data()

    # exclude some metadata from the LLM
    for doc in documents:
        doc.excluded_llm_metadata_keys = ["File Name", "Content Type", "Header Path"]

    return documents


def get_index(docs_filepath, index_filepath):
    # create a vector store index for each folder
    try:
        sn_index = load_index_from_storage(StorageContext.from_defaults(persist_dir=index_filepath))
    except:
        sn_docs = load_docs(docs_filepath)
        sn_index = VectorStoreIndex.from_documents(sn_docs)
        sn_index.storage_context.persist(persist_dir=index_filepath)
    return sn_index


def query(query_text, debug_mode=False):

    # Initialize optional debugging tools
    llama_debug_handler = None
    if debug_mode:
        # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        # logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))
        llama_debug_handler = LlamaDebugHandler(print_trace_on_end=True)
        callback_manager = CallbackManager([llama_debug_handler])
        Settings.callback_manager = callback_manager

    # Load the index from disk
    index = get_index("./transcripts", "./index")

    # Create the query engine
    query_engine = index.as_query_engine()

    # Execute the query
    response = query_engine.query(query_text)

    # # If in debug mode, display the prompts sent to the LLM
    # if debug_mode and llama_debug_handler:
    #     print("\n--- LLM PROMPTS AND RESPONSES ---\n")
    #     for input_event, output_event in llama_debug_handler.get_llm_inputs_outputs():
    #         print("INPUT EVENT PAYLOAD:\n", input_event.payload)
    #         print("OUTPUT EVENT PAYLOAD:\n", output_event.payload)
    #         print("\n" + "-" * 50 + "\n")

    return response

if __name__ == '__main__':
    load_dotenv()  # Load the .env file
    #api_key = os.getenv('GOOGLE_API_KEY')
    openai.api_key = os.environ["OPENAI_API_KEY"]
    Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)

    # res = query("which science fiction books does Steve like, return a list of the names and a one sentence description of each book")
    # print(res)
    # res = query("which TV shows or series did Steve or Leo recommend, look for mentions of episodes and also of streaming services like Amazon Prime, NetFlix, HBO etc., return a list of the names and a one sentence description of each",
    #             True)
    expanded_query = (
        "Which TV shows, series, or streaming content (e.g., Netflix, Amazon Prime) "
        "did Steve or Leo mention or recommend? Look for mentions of seasons, episodes or trailers"
        "Avoid podcasts. "
    )
    res = query(expanded_query,True)
    # res = query("which Netflix shows, documentaries or series are recommended by Steve or Leo, don't include podcasts, return a list of the names and a one sentence description of each",
    #             False)
    print(res)

