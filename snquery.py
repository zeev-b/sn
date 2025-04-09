import logging
import sys
import openai
import os
import re
from dotenv import load_dotenv
from llama_index.core import Settings, Document
from llama_index.core.schema import TextNode
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.llms.openai import OpenAI


class SnTextFileReader(BaseReader):
    def __init__(self, chunk_size=1024, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parser = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def load_data(self, file_path, extra_info=None):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        cleaned_text = raw_text.replace("\r\n\r\n", " ").replace("\n\n", " ")

        document = Document(
            text=cleaned_text,
            metadata=extra_info or {}
        )

        return self.parser.get_nodes_from_documents([document])


def load_docs(directory):
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


def get_index(docs_filepath, index_filepath):
    try:
        index = load_index_from_storage(StorageContext.from_defaults(persist_dir=index_filepath))
    except Exception:
        nodes = load_docs(docs_filepath)
        index = VectorStoreIndex(nodes)
        index.storage_context.persist(persist_dir=index_filepath)
    return index


def query(query_text, debug_mode=False):
    llama_debug_handler = None
    if debug_mode:
        llama_debug_handler = LlamaDebugHandler(print_trace_on_end=True)
        callback_manager = CallbackManager([llama_debug_handler])
        Settings.callback_manager = callback_manager

    index = get_index("./transcripts", "./index")

    retriever = VectorIndexRetriever(index=index, similarity_top_k=32)
    query_engine = RetrieverQueryEngine(retriever=retriever)

    response = query_engine.query(query_text)

    if debug_mode and llama_debug_handler:
        print("\n--- LLM PROMPTS AND RESPONSES ---\n")
        for input_event, output_event in llama_debug_handler.get_llm_inputs_outputs():
            print("INPUT EVENT PAYLOAD:\n", input_event.payload)
            print("OUTPUT EVENT PAYLOAD:\n", output_event.payload)
            print("\n" + "-" * 50 + "\n")

    return response


if __name__ == '__main__':
    load_dotenv()
    openai.api_key = os.environ["OPENAI_API_KEY"]

    Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)

    # res = query(
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
    res = query(
        "Which TV shows or series did Steve or Leo recommend? Look for mentions of streaming services like Netflix, Amazon Prime, or HBO.",
        debug_mode=False
    )
    print(res)
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