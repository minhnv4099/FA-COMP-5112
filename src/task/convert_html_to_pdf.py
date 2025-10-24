#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import asyncio
import glob
import os

import tqdm
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


async def html_to_pdf(input_html, output_pdf):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Hỗ trợ cả file cục bộ hoặc URL
        if os.path.exists(input_html):
            input_html = "file://" + os.path.abspath(input_html)

        await page.goto(input_html)
        await page.pdf(path=output_pdf, format="A4", print_background=True)

        await browser.close()
        print(f"✅ Saved PDF: {output_pdf}")


def main():
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


if __name__ == '__main__':
    main()
