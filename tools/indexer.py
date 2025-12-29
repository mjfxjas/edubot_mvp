#!/usr/bin/env python3
import argparse, json, os, re, time, uuid, pathlib
from typing import List, Dict, Any, Tuple, Optional

# Optional upload
try:
    import boto3
except Exception:
    boto3 = None

# --- helpers ---
def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def split_paragraphs(text: str) -> List[str]:
    # split on blank lines or hard breaks
    parts = re.split(r"\n\s*\n", text)
    parts = [normalize_ws(p) for p in parts if normalize_ws(p)]
    return parts

def chunk_paragraphs(paragraphs: List[str], max_chars: int = 1800) -> List[str]:
    chunks, cur = [], []
    cur_len = 0
    for p in paragraphs:
        if cur_len + len(p) + 1 > max_chars and cur:
            chunks.append(" ".join(cur))
            cur, cur_len = [], 0
        cur.append(p)
        cur_len += len(p) + 1
    if cur:
        chunks.append(" ".join(cur))
    return chunks

# --- PDF extraction (by pages, then chunk) ---
def extract_pdf_to_chunks(pdf_path: str, pages_per_block: int = 3) -> List[Dict[str, Any]]:
    import pdfplumber
    chunks_all: List[Dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        block_id = 0
        for start in range(0, total_pages, pages_per_block):
            end = min(start + pages_per_block, total_pages)
            texts = []
            for i in range(start, end):
                page = pdf.pages[i]
                try:
                    texts.append(page.extract_text() or "")
                except Exception:
                    texts.append("")
            block_text = "\n".join(texts)
            block_text = normalize_ws(block_text)
            if not block_text:
                continue
            # paragraph-based sub-chunking for more even sizes
            paragraphs = split_paragraphs(block_text)
            for subidx, chunk in enumerate(chunk_paragraphs(paragraphs, max_chars=1800)):
                chunks_all.append({
                    "block_index": block_id,
                    "sub_index": subidx,
                    "page_start": start + 1,   # 1-based for humans
                    "page_end": end,
                    "text": chunk
                })
            block_id += 1
    return chunks_all

def write_json(path: pathlib.Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def upload_dir_to_s3(local_dir: pathlib.Path, bucket: str, prefix: str, kms_alias: str) -> None:
    if boto3 is None:
        raise RuntimeError("boto3 not installed. Run: pip install boto3")
    s3 = boto3.client("s3")
    for root, _, files in os.walk(local_dir):
        for name in files:
            full = pathlib.Path(root) / name
            rel = full.relative_to(local_dir)
            key = f"{prefix.rstrip('/')}/{rel.as_posix()}"
            s3.upload_file(str(full), bucket, key)
            print(f"Uploaded: s3://{bucket}/{key}")

def main():
    ap = argparse.ArgumentParser(description="EduBot indexer: PDF -> JSON chunks + toc.json")
    ap.add_argument("--pdf", required=True, help="Path to local PDF")
    ap.add_argument("--book-id", required=True, help="Book ID slug, e.g. 'philosophy' or 'history'")
    ap.add_argument("--subject", required=True, help="High-level subject folder, e.g. 'philosophy', 'history'")
    ap.add_argument("--outdir", default="indexes", help="Output base directory (local)")
    ap.add_argument("--pages-per-block", type=int, default=3, help="Pages grouped per block before sub-chunking")
    ap.add_argument("--s3-bucket", help="If set, upload output to this S3 bucket")
    ap.add_argument("--s3-prefix", help="S3 prefix (e.g., 'indexes/philosophy') -- defaults to 'indexes/<book-id>'")
    ap.add_argument("--kms-alias", default="alias/edubot-mvp-kms", help="KMS alias for SSE-KMS")
    args = ap.parse_args()

    pdf_path = pathlib.Path(args.pdf).expanduser().resolve()
    ts = int(time.time())

    # Extract chunks
    chunks = extract_pdf_to_chunks(str(pdf_path), pages_per_block=args.pages_per_block)

    # Prepare output structure
    base = pathlib.Path(args.outdir) / args.book_id
    sections_dir = base / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    # Write sections as separate JSON files
    section_entries: List[Dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        section_id = f"{args.book_id}-b{ch['block_index']}-s{ch['sub_index']}"
        section_obj = {
            "book_id": args.book_id,
            "subject": args.subject,
            "section_id": section_id,
            "title": f"{args.book_id} block {ch['block_index']} chunk {ch['sub_index']}",
            "page_start": ch["page_start"],
            "page_end": ch["page_end"],
            "text": ch["text"],
            "source_pdf": pdf_path.name,
            "created_at": ts
        }
        write_json(sections_dir / f"{section_id}.json", section_obj)
        section_entries.append({
            "section_id": section_id,
            "title": section_obj["title"],
            "page_start": ch["page_start"],
            "page_end": ch["page_end"],
            "bytes": len(section_obj["text"].encode("utf-8"))
        })

    # Write TOC
    toc = {
        "book_id": args.book_id,
        "subject": args.subject,
        "source_pdf": pdf_path.name,
        "created_at": ts,
        "sections": section_entries
    }
    write_json(base / "toc.json", toc)

    print(f"Wrote {len(section_entries)} sections to {sections_dir}")

    # Optional upload
    if args.s3_bucket:
        prefix = args.s3_prefix or f"indexes/{args.book_id}"
        upload_dir_to_s3(base, args.s3_bucket, prefix, args.kms_alias)
        print(f"Uploaded index to s3://{args.s3_bucket}/{prefix}/")

if __name__ == "__main__":
    main()
