import arxiv
import requests
import time
import tarfile
import tempfile
import os
import re
import csv

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
    # Raw symbols
    gt = tex_data.count(">")
    lt = tex_data.count("<")

    # LaTeX inequality commands
    leq = len(re.findall(r'\\leq\b', tex_data))
    geq = len(re.findall(r'\\geq\b', tex_data))
    lt_cmd = len(re.findall(r'\\lt\b', tex_data))
    gt_cmd = len(re.findall(r'\\gt\b', tex_data))
    ll = len(re.findall(r'\\ll\b', tex_data))
    gg = len(re.findall(r'\\gg\b', tex_data))

    total_gt = gt + geq + gt_cmd + gg
    total_lt = lt + leq + lt_cmd + ll

    return {
        'raw >': gt,
        'raw <': lt,
        '\\geq': geq,
        '\\leq': leq,
        '\\gt': gt_cmd,
        '\\lt': lt_cmd,
        '\\gg': gg,
        '\\ll': ll,
        'total >-like': total_gt,
        'total <-like': total_lt
    }


def compare_symbols_on_random_math_papers(n=5, csv_filename="inequality_counts.csv", verbose_output=False):
    client = arxiv.Client()
    search = arxiv.Search(
        query="cat:math*",
        max_results=100,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    papers = list(client.results(search))
    Running_total = {
        'total >-like': 0,
        'total <-like': 0 
    }
    rows = []

    for paper in papers[:n]:
        print(f"Analyzing: {paper.title} ({paper.entry_id})")
        arxiv_id = paper.entry_id.split('/')[-1]
        tex = download_and_extract_tex(arxiv_id)
        if tex:
            symbols = count_symbols(tex)

            if verbose_output:
                for k, v in symbols.items():
                    print(f"  {k}: {v}")
                if symbols['total >-like'] > symbols['total <-like']:
                    print("  ➤ More >-like symbols (including LaTeX)")
                elif symbols['total >-like'] < symbols['total <-like']:
                    print("  ➤ More <-like symbols (including LaTeX)")
                else:
                    print("  ➤ Equal number of > and < symbols (including LaTeX)")

            Running_total['total <-like'] += symbols['total <-like']
            Running_total['total >-like'] += symbols['total >-like']
            result = {
                'arxiv_id': arxiv_id,
                'title': paper.title,
                **symbols
            }
            rows.append(result)

        else:
            print("  ✘ Could not extract LaTeX source")
        print('-' * 60)

    print()
    if Running_total['total >-like'] > Running_total['total <-like']:
        print("  ➤ More >-like symbols (including LaTeX)")
    elif Running_total['total >-like'] < Running_total['total <-like']:
        print("  ➤ More <-like symbols (including LaTeX)")
    else:
        print("  ➤ Equal number of > and < symbols (including LaTeX)")

    print(Running_total)

    # Write to CSV
    fieldnames = ['arxiv_id', 'title'] + list(symbols.keys())
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Saved results to: {csv_filename}")

if __name__ == "__main__":
    compare_symbols_on_random_math_papers(n=3)
