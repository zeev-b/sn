import argparse
import os
from dotenv import load_dotenv
from sn_rag_engine import SnRAGEngine

MIN_YEAR = 2015
MAX_YEAR = 2025


def main():
    parser = argparse.ArgumentParser(description="Query podcast transcripts by year range and summarize results.")
    parser.add_argument("-sy", "--start-year", type=int, required=True, help="Start year for querying transcripts")
    parser.add_argument("-ey", "--end-year", type=int, required=True, help="End year for querying transcripts")
    parser.add_argument("-q", "--query", type=str, required=True, help="Query to execute")
    parser.add_argument("--hide-intermediate", action="store_true", default=False, help="Hide intermediate yearly results")
    parser.add_argument("--transcripts-dir", type=str, default="./transcripts", help="Directory containing transcript files")
    parser.add_argument("--index-dir", type=str, default="./index", help="Directory containing index files")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Show debug information")
    parser.add_argument("--summary-prompt", type=str, default=None, help="Custom summary prompt template. Use '{query_text}' and '{responses}' as placeholders.")
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

    provider = os.getenv("LLM_PROVIDER", "openai")
    SnRAGEngine.set_llm(provider)

    engine = SnRAGEngine(
        transcripts_dir=args.transcripts_dir,
        index_dir=args.index_dir,
        summary_prompt=args.summary_prompt,
        debug_mode=args.debug,
    )

    result = engine.query_range(
        query_text=args.query,
        start_year=args.start_year,
        end_year=args.end_year,
        show_intermediate=not args.hide_intermediate,
    )

    print("\n\n=== Summary result ===")
    print(result)


if __name__ == '__main__':
    main()
