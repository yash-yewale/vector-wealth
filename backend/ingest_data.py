from __future__ import annotations

import math
import os
import re
import time
from pathlib import Path
from typing import Iterable

import chromadb
import pandas as pd
from dotenv import load_dotenv
from google import genai


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
CSV_PATH = ROOT_DIR / "data" / "IndianFinancialNews.csv"
DB_PATH = Path(os.getenv("VECTOR_WEALTH_DB_PATH", str(Path(__file__).resolve().parent / "vector_wealth_db")))
COLLECTION_NAME = "market_news"
EMBEDDING_MODELS = ("text-embedding-004", "gemini-embedding-001")

BATCH_SIZE = 100
MAX_CHARS_PER_CHUNK = 1200
OVERLAP_CHARS = 100
EMBED_CALL_BATCH_SIZE = 24
EMBED_REQUEST_PAUSE_SECONDS = 0.8
EMBED_MAX_RETRIES = 6
DEFAULT_RETRY_DELAY_SECONDS = 30.0
MIN_DESCRIPTION_CHARS = 40


def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK, overlap: int = OVERLAP_CHARS) -> list[str]:
    cleaned = " ".join(str(text).split())
    if not cleaned:
        return []

    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    text_len = len(cleaned)
    step = max_chars - overlap
    while start < text_len:
        end = min(start + max_chars, text_len)
        chunks.append(cleaned[start:end])
        start += step
    return chunks


def iter_batches(df: pd.DataFrame, batch_size: int) -> Iterable[pd.DataFrame]:
    total = len(df)
    for start in range(0, total, batch_size):
        yield df.iloc[start : start + batch_size]


def iter_list_batches(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def normalize_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    unnamed_columns = [col for col in df.columns if col.startswith("Unnamed") or col == ""]
    if unnamed_columns:
        df = df.drop(columns=unnamed_columns, errors="ignore")

    required_cols = {"Date", "Title", "Description"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}")

    for col in ["Date", "Title", "Description"]:
        df[col] = df[col].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    df = df[df["Description"].str.len() >= MIN_DESCRIPTION_CHARS]
    df = df[df["Title"].str.len() > 0]
    df = df[df["Date"].str.len() > 0]

    df = df.drop_duplicates(subset=["Date", "Title", "Description"], keep="first")
    return df.reset_index(drop=True)


def build_document_text(title_value: str, description_value: str) -> str:
    return f"Title: {title_value}\nDescription: {description_value}"


def extract_embedding_values(embedding_response) -> list[list[float]]:
    vectors: list[list[float]] = []
    if hasattr(embedding_response, "embeddings"):
        for item in embedding_response.embeddings:
            if hasattr(item, "values"):
                vectors.append(item.values)
            else:
                vectors.append(item)
    else:
        raise ValueError("Embedding response does not contain embeddings.")
    return vectors


def embed_texts(client: genai.Client, texts: list[str]):
    last_error: Exception | None = None
    for model_name in EMBEDDING_MODELS:
        try:
            return client.models.embed_content(
                model=model_name,
                contents=texts,
            )
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError("Embedding failed: no models configured.")


def _extract_retry_delay_seconds(error: Exception) -> float:
    message = str(error)
    decimal_match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", message, flags=re.IGNORECASE)
    if decimal_match:
        return float(decimal_match.group(1))

    int_match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?([0-9]+)s", message, flags=re.IGNORECASE)
    if int_match:
        return float(int_match.group(1))

    return DEFAULT_RETRY_DELAY_SECONDS


def embed_texts_with_retry(client: genai.Client, texts: list[str]):
    delay_seconds = 1.5
    attempt = 1

    while attempt <= EMBED_MAX_RETRIES:
        try:
            return embed_texts(client, texts)
        except Exception as exc:
            message = str(exc)
            is_quota_error = "429" in message or "RESOURCE_EXHAUSTED" in message
            if not is_quota_error or attempt == EMBED_MAX_RETRIES:
                raise

            retry_after = _extract_retry_delay_seconds(exc)
            sleep_for = max(retry_after + 1.0, delay_seconds)
            print(
                f"Embedding rate-limited (attempt {attempt}/{EMBED_MAX_RETRIES}). "
                f"Sleeping {sleep_for:.1f}s before retry."
            )
            time.sleep(sleep_for)
            delay_seconds = min(delay_seconds * 2, 60.0)
            attempt += 1


def ingest() -> None:
    load_dotenv(ENV_PATH)
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is missing. Add it to the root .env file.")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    raw_df = pd.read_csv(CSV_PATH)
    raw_rows = len(raw_df)
    df = normalize_dataframe(raw_df)

    if df.empty:
        raise RuntimeError("No valid rows left after CSV cleaning. Check dataset quality rules.")

    print(f"Loaded {raw_rows} rows; retained {len(df)} rows after cleaning and deduplication.")

    client = genai.Client(api_key=api_key)

    chroma_client = chromadb.PersistentClient(path=str(DB_PATH))
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

    total_rows = len(df)
    total_batches = int(math.ceil(total_rows / BATCH_SIZE)) if total_rows else 0
    global_chunk_counter = collection.count()

    for batch_index, batch_df in enumerate(iter_batches(df, BATCH_SIZE), start=1):
        chunk_texts: list[str] = []
        metadatas: list[dict] = []
        ids: list[str] = []

        for row_idx, row in batch_df.iterrows():
            date_value = str(row.get("Date", ""))
            title_value = str(row.get("Title", ""))
            description_value = str(row.get("Description", ""))
            document_text = build_document_text(title_value, description_value)

            row_chunks = chunk_text(document_text)
            for chunk_idx, chunk in enumerate(row_chunks):
                doc_id = f"news_{row_idx}_{chunk_idx}_{global_chunk_counter}"
                global_chunk_counter += 1

                chunk_texts.append(chunk)
                ids.append(doc_id)
                metadatas.append(
                    {
                        "Date": date_value,
                        "Title": title_value,
                        "source_row": int(row_idx),
                        "chunk_index": int(chunk_idx),
                    }
                )

        if not chunk_texts:
            print(f"Batch {batch_index}/{total_batches}: no valid chunks, skipped.")
            continue

        embeddings: list[list[float]] = []
        chunk_count = len(chunk_texts)
        chunk_batches = int(math.ceil(chunk_count / EMBED_CALL_BATCH_SIZE))

        for chunk_batch_index, text_batch in enumerate(
            iter_list_batches(chunk_texts, EMBED_CALL_BATCH_SIZE), start=1
        ):
            embedding_response = embed_texts_with_retry(client, text_batch)
            embeddings.extend(extract_embedding_values(embedding_response))

            if chunk_batch_index < chunk_batches:
                time.sleep(EMBED_REQUEST_PAUSE_SECONDS)

        collection.add(
            ids=ids,
            documents=chunk_texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        print(
            f"Batch {batch_index}/{total_batches}: ingested {len(chunk_texts)} chunks from {len(batch_df)} rows."
        )

    print(f"Ingestion complete. Collection '{COLLECTION_NAME}' now has {collection.count()} documents.")


if __name__ == "__main__":
    ingest()
