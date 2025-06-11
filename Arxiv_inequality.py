import arxiv
import requests
import time
import tarfile
import tempfile
import os
import re
import random

retries = 3

def download_and_extract_tex(arxiv_id):
    url = f"https://arxiv.org/e-print/{arxiv_id}"
    headers = {
        "User-Agent": "arxiv-symbol-scraper/0.1 (+https://yourdomain.com/contact)"
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed for {arxiv_id}: {e}")
            if attempt + 1 == retries:
                return None
            time.sleep(2 ** attempt)

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = os.path.join(tmpdir, f"{arxiv_id}.tar")
        with open(tar_path, "wb") as f:
            f.write(response.content)
        try:
            with tarfile.open(tar_path) as tar:
                tar.extractall(tmpdir)
        except Exception as e:
            print(f"Failed to extract {arxiv_id}: {e}")
            return None

        # Find all .tex files
        tex_contents = ""
        for root, _, files in os.walk(tmpdir):
            for file in files:
                if file.endswith(".tex"):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as tex_file:
                            tex_contents += tex_file.read()
                    except Exception:
                        continue
        return tex_contents if tex_contents else None

def count_symbols(tex_data):
    greater_than = tex_data.count(">")
    less_than = tex_data.count("<")
    return greater_than, less_than

def compare_symbols_on_random_math_papers(n=5):
    client = arxiv.Client()
    search = arxiv.Search(
        query="cat:math*",
        max_results=100,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    papers = list(client.results(search))
    random.shuffle(papers)

    for paper in papers[:n]:
        print(f"Analyzing: {paper.title} ({paper.entry_id})")
        arxiv_id = paper.entry_id.split('/')[-1]
        tex = download_and_extract_tex(arxiv_id)
        if tex:
            gt, lt = count_symbols(tex)
            print(f"  > : {gt} times")
            print(f"  < : {lt} times")
            if gt > lt:
                print("  More '>' symbols")
            elif lt > gt:
                print("  More '<' symbols")
            else:
                print("  Equal number of '>' and '<'")
        else:
            print("  ✘ Could not extract LaTeX source")
        print('-' * 60)
        time.sleep(1)

if __name__ == "__main__":
    compare_symbols_on_random_math_papers(n=3)
