#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import re
import json
import glob
from collections import defaultdict
from tqdm import tqdm


def extract_urls_from_files(folder: str, save_file: str):
    files = glob.glob(rf"{folder}/*.md")

    file_to_urls = defaultdict(dict)
    urls = []

    for i, file in tqdm(enumerate(files[:])):
        with open(file, 'r') as f:
            text = f.read()

        file_to_urls[file]['description'] = extract_description(text)
        file_to_urls[file]['source'] = extract_source_url(text)
        file_to_urls[file]['related'] = extract_related_links_urls(text)

        urls.extend(extract_source_url(text))
        urls.extend(extract_related_links_urls(text))

        n = len(file_to_urls[file]['source']) + len(file_to_urls[file]['related'])

        if i % 50 == 0:
            print(f"File '{file}': {n} urls.")

    print(f'Number of urls: {len(urls)}')
    non_duplicate_urls = list(set(urls))
    print(f'Number of urls: {len(non_duplicate_urls)}')
    lakehead_sites = list(filter(lambda x: 'lakehead' in x, non_duplicate_urls))
    print(f'Number of urls: {len(lakehead_sites)}')

    # write to json file
    with open(save_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(lakehead_sites, ensure_ascii=False, indent=3))
        # for rec in file_to_urls:
        #     f.write(json.dumps({rec: file_to_urls[rec]}, ensure_ascii=False) + "\n")


def extract_source_url(text: str):
    # Regex bắt URL thông dụng
    pattern_source = r'\*\*Source\*\*:\s*(https?://[^\s)]+)'
    return re.findall(pattern_source, text)


def extract_related_links_urls(text: str):
    # Bước 1: Lấy block sau "## Related Links"
    block_pattern = r'## Related Links\s*(.*?)(?=\n##|\Z)'
    block_match = re.search(block_pattern, text, flags=re.DOTALL)

    if not block_match:
        return []  # Không có section "Related Links"

    block_text = block_match.group(1)

    # Bước 2: Lấy URL trong block
    link_pattern = r'- \[[^\]]+\]\((https?://[^\s)]+)\)'
    return re.findall(link_pattern, block_text)


def extract_description(text: str):
    # 1. Description
    pattern_description = r'\*\*Description\*\*:\s*(.+)'
    description = re.findall(pattern_description, text)

    if len(description) == 1:
        return description[0]

    return description


extract_urls_from_files(
    save_file="data/interm/lakehead_scraped/urls.jsonl",
    folder="data/external/lakehead_scraped/"
)
