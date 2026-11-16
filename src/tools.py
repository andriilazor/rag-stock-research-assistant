import csv
import json

from langchain.tools import tool
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

from config import EMBED_MODEL, INDEX_DIR, OLLAMA_URL

embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
index = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)

with open("data/prices.csv") as f:
    PRICES = list(csv.DictReader(f)) # load prices

with open("data/metrics.json") as f:
    METRICS = json.load(f) # load metrics

TICKERS = list(METRICS["companies"])

def unknown_ticker(ticker):
    return f"Ticker {ticker} not found."

@tool(response_format="content_and_artifact", parse_docstring=True)
def search_reports(query: str, ticker: str | None = None) -> tuple[str, list[str]]:
    """Search company reports, news, risk factors and company overviews.

    Use it for facts and explanations: events, reasons ("why"), risks, guidance, strategy
    and company facts (people, headcount, assets, customers).

    Args:
        query: What to look for. Write it in English.
        ticker: Optional. NWE, HLXB or VTL, to search one company only.
    """
    if ticker:
        ticker = ticker.upper()
        if ticker not in TICKERS:
            return unknown_ticker(ticker), []

    search_filter = {"ticker": ticker} if ticker else None # parameter for search filter
      # FAISS similarity search.
      # Query is transformed to embedding ->
      # FAISS compares query embedding with embeddings of the documents ->
      # The closest vectors are determined ->
      # Relevant documents are returned (given 6 closest) 
    docs = index.similarity_search(query, k=6, filter=search_filter, fetch_k=30) 
    docs.sort(key=lambda doc: doc.metadata["date"], reverse=True) # sorting using date

    text = "\n\n".join(f"[{doc.metadata['source']}, {doc.metadata['date']}]\n{doc.page_content}" for doc in docs) # documents list to str
      # As the result agent receives one str with found fregments
      # like so:
      #  [example_report.pdf, 2026-10-15]
      #  Extracted fragment
      
      #  [example_report_2.pdf, 2026-10-15]
      #  Extracted fragment 2
    sources = sorted({doc.metadata["source"] for doc in docs}) # collect sources of the documents into set to remove duplicates
    return text, sources

@tool(response_format="content_and_artifact", parse_docstring=True)
def get_price_history(ticker: str, days: int = 30) -> tuple[str, list[str]]:
    """Get daily closing prices and volumes (September-October 2026).

    Each day also shows the previous close and the change in percent.
    It returns numbers only: to explain why a price moved, also call search_reports.

    Args:
        ticker: NWE, HLXB or VTL.
        days: How many most recent trading days to return (1-30). Use 30 to see the whole period.
    """
    ticker = ticker.upper()
    rows = [row for row in PRICES if row["ticker"] == ticker]
    if not rows:
        return unknown_ticker(ticker), []
      
    
    # Iterates through the selected days, calculates daily percentage changes, tracks the biggest drop. 
    days = min(max(days, 1), len(rows))
    lines, biggest_drop = [], None
    for i in range(len(rows) - days, len(rows)):
        row = rows[i]
        line = f"{row['date']}: close {row['close']}, volume {row['volume']}"
        if i > 0:  
            previous = rows[i - 1]["close"]
            change = (float(row["close"]) / float(previous) - 1) * 100
            line += f", previous close {previous}, change {change:+.2f}%"
            if change < 0 and (biggest_drop is None or change < biggest_drop[0]):
                biggest_drop = (change, line)
        lines.append(line)
    if biggest_drop:
        lines.append(f"Biggest daily drop in this period: {biggest_drop[1]}")
    return "\n".join(lines), ["prices.csv"]

@tool(response_format="content_and_artifact", parse_docstring=True)
def get_financial_metrics(ticker: str) -> tuple[str, list[str]]:
    """Get financial metrics: P/E, revenue TTM, net margin TTM, debt/equity, market cap, dividend yield.

    Args:
        ticker: NWE, HLXB or VTL.
    """
    ticker = ticker.upper()
    if ticker not in TICKERS:
        return unknown_ticker(ticker), []

    m = METRICS["companies"][ticker]
    currency = m["currency"]
    pe_ratio = m["pe_ratio"] if m["pe_ratio"] is not None else "not available"
    text = (
        f"{m['name']} ({ticker}), metrics as of {METRICS['as_of']}\n"
        f"P/E ratio: {pe_ratio}\n"
        f"Revenue TTM: {m['revenue_ttm'] / 1e6:.0f} million {currency}\n"
        f"Net margin TTM: {m['net_margin_ttm'] * 100:.1f}%\n"
        f"Debt/equity: {m['debt_to_equity']}\n"
        f"Market cap: {m['market_cap'] / 1e6:.0f} million {currency}\n"
        f"Dividend yield: {m['dividend_yield'] * 100:.1f}%"
    )
    return text, ["metrics.json"]

TOOLS = [search_reports, get_price_history, get_financial_metrics]