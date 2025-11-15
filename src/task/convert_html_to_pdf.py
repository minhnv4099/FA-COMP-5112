#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import asyncio
import glob
import json
import os
import tqdm
import requests

from json import load, dumps
from urllib.parse import urlparse
from playwright.async_api import async_playwright

DOC_EX_DIR = "data/external/blender_python_reference_4_5"
DOC_IN_DIR = "data/interm/blender_python_reference_4_5"

html_dir = "data/external/blender_python_reference_4_5"
pdf_dir = "data/interm/blender_python_reference_4_5"

exclusive_patterns = [
    'search.html',
    'py-modindex.html',
    'index.html',
    'info_advanced.html',
    'info_gotcha.html',
]


async def html_to_pdf(url, output_path):
    # Tạo tên file theo domain + path

    # 1. Kiểm tra MIME xem có phải PDF không
    try:
        head = requests.head(url, allow_redirects=True, timeout=10)
        content_type = head.headers.get("Content-Type", "").lower()
    except:
        content_type = ""

    # 2. Nếu đúng là PDF → download trực tiếp
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        print(f"[DOWNLOAD] {url} → {output_path}")
        r = requests.get(url, stream=True)
        with open(output_path, "wb") as f:
            f.write(r.content)
        return output_path

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Hỗ trợ cả file cục bộ hoặc URL
        if os.path.exists(url):
            url = "file://" + os.path.abspath(url)

        await page.goto(url, timeout=100000)
        await page.pdf(path=output_path, format="A4", print_background=True)

        await browser.close()
        print(f"✅ Saved PDF: {output_path}")


def htmls_to_pdfs():
    html_files = glob.glob(fr"{html_dir}/*.html")
    exist_pdf_files = glob.glob(fr"{pdf_dir}/*.pdf")

    exist_html = [f.replace('interm', 'external').replace('pdf', 'html') for f in exist_pdf_files]

    complemented_files = set(html_files).difference(exist_html)
    print(len(complemented_files))
    print(len(html_files))
    print(len(exist_pdf_files))

    for html_file in tqdm.tqdm(complemented_files):
        pdf_file = html_file.replace("external", "interm").replace('html', 'pdf')

        is_skip = (os.path.basename(html_file) in exclusive_patterns
                   or 'genindex' in html_file)
        if is_skip:
            continue
        asyncio.run(html_to_pdf(html_file, pdf_file))


async def urls_to_pdfs(urls: list[str]):
    output_dir = "data/interm/lakehead_scraped"

    exist_pdf_files = glob.glob(fr"{output_dir}/**/*.pdf")

    print(len(exist_pdf_files))

    for i, url in tqdm.tqdm(enumerate(urls)):
        parsed = urlparse(url)

        base = os.path.basename(parsed.path) or "index"

        if not base.lower().endswith(".pdf"):
            base += ".pdf"

        out_dir = os.path.join(output_dir, parsed.netloc)
        os.makedirs(out_dir, exist_ok=True)

        output_path = os.path.join(out_dir, base)

        if output_path in exist_pdf_files:
            # print(output_path)
            continue
        try:
            await html_to_pdf(url, output_path)
        except Exception:
            continue


if __name__ == '__main__':
    file = 'data/external/urls.jsonl'
    with open(file, 'r') as f:
        urls = json.load(f)

    asyncio.run(urls_to_pdfs(urls=urls))
