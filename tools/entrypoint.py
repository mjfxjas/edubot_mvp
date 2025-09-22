import os, pathlib
import boto3, subprocess, json

BUCKET = os.environ["CURRICULUM_BUCKET"]
BOOK_ID = os.environ["BOOK_ID"]          # e.g., philosophy
SUBJECT = os.environ.get("SUBJECT", BOOK_ID)
S3_PDF_KEY = os.environ["S3_PDF_KEY"]    # e.g., philosophy/philosophy-textbook.pdf
S3_INDEX_PREFIX = os.environ.get("S3_INDEX_PREFIX", f"indexes/{BOOK_ID}")
KMS_ALIAS = os.environ.get("KMS_ALIAS", "alias/edubot-mvp-kms")
PAGES_PER_BLOCK = int(os.environ.get("PAGES_PER_BLOCK", "3"))

s3 = boto3.client("s3")

def sh(args):
    print("+", " ".join(map(str,args)))
    subprocess.check_call(args)

def main():
    pdf_local = f"/tmp/{pathlib.Path(S3_PDF_KEY).name}"
    print(f"Downloading s3://{BUCKET}/{S3_PDF_KEY} -> {pdf_local}")
    s3.download_file(BUCKET, S3_PDF_KEY, pdf_local)

    # run your existing indexer to emit local JSON and upload to S3 with SSE-KMS
    sh([
        "python", "/var/task/indexer.py",
        "--pdf", pdf_local,
        "--book-id", BOOK_ID,
        "--subject", SUBJECT,
        "--outdir", "/tmp/indexes",
        "--pages-per-block", str(PAGES_PER_BLOCK),
        "--s3-bucket", BUCKET,
        "--s3-prefix", S3_INDEX_PREFIX,
        "--kms-alias", KMS_ALIAS
    ])
    print("Indexing complete.")

if __name__ == "__main__":
    main()
