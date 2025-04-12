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
from llama_index.core.schema import TextNode
from llama_index.llms.openai import OpenAI


class SnTextFileReader(BaseReader):
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def load_data(self, file_path: str, extra_info: Optional[Dict] = None) -> List[TextNode]:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        cleaned_text = raw_text.replace("\r\n\r\n", " ").replace("\n\n", " ")
        document = Document(text=cleaned_text, metadata=extra_info or {})
        return self.parser.get_nodes_from_documents([document])


def load_docs(directory) -> List[TextNode]:
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
    return query_years(2015, 2025, query_text, show_intermediate=show_intermediate, debug_mode=debug_mode)

def query_years(start_year: int, end_year: int, query_text: str, show_intermediate: bool = False, debug_mode: bool = False) -> CompletionResponse:
    all_responses = []
    for year in range(start_year, end_year+1):
        response = query_year(query_text, year, debug_mode)
        response_with_year = f"\n--- {year} ---\n{response}\n"
        all_responses.append(response_with_year)
        if show_intermediate:
            print(response_with_year)

    if len(all_responses) > 1:
        # combined_prompt = "Combine the following answers into a single, coherent summary:\n\n" + "\n\n---\n\n".join(all_responses)
        combined_prompt = (f"The original query per year was: '{query_text}'\n. Following are the responses we got from querying" +
                          "the transcripts per year. Combine the answers we got from all years into a single coherent answer.\n\n" +
                           "\n".join(all_responses))
        final_response = Settings.llm.complete(combined_prompt)
    else:
        final_response = all_responses[0]
    return final_response


def query_year(query_text: str, year: int, debug_mode: bool) -> RESPONSE_TYPE:
    if debug_mode:
        llama_debug_handler = LlamaDebugHandler(print_trace_on_end=True)
        Settings.callback_manager = CallbackManager([llama_debug_handler])
    index = get_index(f"./transcripts/{year}", f"./index/{year}")
    retriever = VectorIndexRetriever(index=index, similarity_top_k=32)
    query_engine = RetrieverQueryEngine(retriever=retriever)
    response = query_engine.query(query_text)
    return response


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Query podcast transcripts by year range and summarize results.")
    parser.add_argument("-sy", "--start-year", type=int, required=True, help="Start year for querying transcripts")
    parser.add_argument("-ey", "--end-year", type=int, required=True, help="End year for querying transcripts")
    parser.add_argument("-q", "--query", type=str, required=True, help="Query to execute")
    parser.add_argument("-i", "--show-intermediate", action="store_true", default=True, help="Show intermediate yearly results")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Show debug information")
    args = parser.parse_args()

    if args.start_year < 2015 or args.end_year > 2025:
        print("Start year must be >= 2015 and end year must be <= 2025.")
        exit(1)
    if args.start_year > args.end_year:
        print("Start year must be <= end year.")
        exit(1)
    if not args.query.strip():
        print("Query must not be empty.")
        exit(1)

    load_dotenv()
    openai.api_key = os.environ["OPENAI_API_KEY"]
    Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)


    result = query_years(
        start_year=args.start_year,
        end_year=args.end_year,
        query_text=args.query,
        debug_mode=args.debug,
        show_intermediate=args.show_intermediate
    )
    print("\n\n=== Summary result ===")
    print(result)

    # res = query_all_years(
    #     "what are the best practices for safe home networks.",
    #     debug_mode=False
    # )
    # print(res)

    #500-1000
    # 1. **No Default Credentials**: Devices should not have manufacturer-set credentials. Upon first use, they should generate strong, unique credentials that the user can then change.
    #
    # 2. **Physical Access Required for Changes**: Any significant security changes, such as enabling remote access or changing admin settings, should require a physical button press to confirm the action. This helps prevent unauthorized remote changes.
    #
    # 3. **Minimal Public Exposure**: Only the essential functions of a device should be exposed to the internet by default. Additional services should require explicit manual enabling, accompanied by clear warnings.
    #
    # 4. **Automatic Firmware Updates**: Devices should come with auto-update features enabled by default, ensuring they regularly check for and apply firmware updates to maintain security.
    #
    # 5. **Ongoing Firmware Maintenance**: Manufacturers should commit to providing firmware updates for as long as the device is in service, addressing vulnerabilities and ensuring continued security.
    #
    # Implementing these practices can significantly enhance the security of home networks.

    #800-850
    # To ensure a safe home network, consider implementing the following best practices:
    #
    # 1. **Use Strong Passwords**: Ensure that all devices, including routers and IoT devices, have unique and complex passwords. Avoid using default passwords.
    #
    # 2. **Enable Firewall Protection**: Utilize firewall software or hardware to monitor and control incoming and outgoing network traffic. Ensure that it is properly configured and active.
    #
    # 3. **Keep Software Updated**: Regularly update all devices, including computers, smartphones, and IoT devices, to patch vulnerabilities and improve security.
    #
    # 4. **Implement Network Segmentation**: Place IoT devices on a separate network from your main devices to limit potential exposure and reduce risk.
    #
    # 5. **Use Two-Factor Authentication**: Enable two-factor authentication on accounts and devices whenever possible to add an extra layer of security.
    #
    # 6. **Disable Unused Services**: Turn off any services or features on your router and devices that you do not use, such as remote access or UPnP, to minimize potential attack vectors.
    #
    # 7. **Monitor Network Traffic**: Regularly check for unusual activity on your network, which could indicate unauthorized access or malware.
    #
    # 8. **Use a Virtual Private Network (VPN)**: Consider using a VPN for added privacy and security, especially when accessing your home network remotely.
    #
    # 9. **Educate Household Members**: Ensure that everyone in the household understands basic security practices, such as recognizing phishing attempts and the importance of not sharing passwords.
    #
    # 10. **Limit Remote Access**: Restrict remote access to your network and devices, and only allow it when absolutely necessary, using secure methods.
    #
    # By following these practices, you can significantly enhance the security of your home network.

    # res = query(
    #     "what topics did Leo and Steve discuss.",
    #     debug_mode=False
    # )
    # print(res)
    # res = query_all_years(
    #     "Which TV shows or series did Steve or Leo recommend? Look for mentions of streaming services like Netflix, Amazon Prime, or HBO.",
    #     show_intermediate=True,
    #     debug_mode=False
    #
    # )
    # print(res)

    # res = query_all_years(
    #     "Which tools and utilities are recommended, If possible, include the site from which to download each one",
    #     show_intermediate=True,
    #     debug_mode=False
    #
    # )
    # print(res)

    # res = query_years(2020, 2023,
    #     "Was Israel mentioned in the podcast and in what context?",
    #     show_intermediate=True,
    #     debug_mode=False
    # )
    # print(res)

    # 800-850
    # "Which TV shows or series did Steve or Leo recommend? Look for mentions of streaming services like Netflix, Amazon Prime, or HBO."
    #
    # Steve and Leo recommended the following TV shows and series:
    #
    # 1. **The Expanse** - Available on Amazon Prime, praised for its realistic visuals and complex plot.
    # 2. **Wheel of Time** - Also on Amazon Prime, noted for its adaptation from the beloved book series.
    # 3. **Foundation** - Mentioned in the context of watching and discussing its episodes.
    # 4. **In the Shadow of the Moon** - Recommended by Steve, though Leo has not watched it yet.
    # 5. **The Tomorrow War** - A movie available on Amazon Prime, which they both enjoyed for its action and special effects.
    #
    # These recommendations highlight their appreciation for science fiction and engaging storytelling.
    # ----
    # 500-1000
    # Steve and Leo recommended several TV shows and series, including:
    #
    # 1. **Devs** - A miniseries produced by FX and streaming on Hulu.
    # 2. **The Dropout** - A show that Steve just started watching.
    # 3. **WeCrashed** - Recommended by Leo as a companion to "The Dropout," available on Apple TV.
    # 4. **Ozark** - Mentioned by Steve as a series they finished watching.
    # 5. **Better Call Saul** - Discussed by Leo, who was watching the final episodes.
    # 6. **Fargo** - Steve praised the second season, which he found to be even better than the first.
    # 7. **Billions** - A series starring Damian Lewis and Paul Giamatti, available on demand.
    # 8. **Homeland** - Steve encouraged viewers to watch this series, which he recently finished.
    #
    # Additionally, they discussed various streaming services like Hulu, Amazon Prime, and HBO Max in relation to these shows.