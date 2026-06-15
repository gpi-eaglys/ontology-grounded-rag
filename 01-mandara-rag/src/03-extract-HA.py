"""
Extacts text from fh/HA.*pdf files.
"""
import glob
import os
import logging
import re
import subprocess

LOG = logging.getLogger(__name__)

SCRIPT_DIR = os.path.realpath(__file__)
PRJ_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BLD_DIR = os.path.join(PRJ_DIR, "build")
CRAWL_DIR = os.path.join(BLD_DIR, "mandala", "crawl")


def extract_pdf(fpath_pdf: str, fpath_txt: str) -> None:
    """Extract plain text from a PDF file using pdftotext.

    @param fpath_pdf: absolute path to the source PDF file.
    @param fpath_txt: absolute path to the output text file to write.
    """
    subprocess.run(
        ["pdftotext", "-layout", fpath_pdf, fpath_txt],
        check=True,
    )


FULLWIDTH_DIGIT: dict[str, int] = {
    "０": 0, "１": 1, "２": 2, "３": 3, "４": 4,
    "５": 5, "６": 6, "７": 7, "８": 8, "９": 9,
}

SECTIONS: dict[str, str] = {
    "事象":    "jisho",
    "経過":    "keika",
    "原因":    "genin",
    "対処":    "taisho",
    "対策":    "taisaku",
    "総括":    "sokatsu",
    "知識化":  "chishikika",
    "背景":    "haikei",
    "四方山話": "yomoyama",  # yomoyamabanashi
    "後日談":  "gojitsudan",
}

# Matches a section header line, e.g. " ２． 経過（図２参照）"


def split_sections(fpath_ha: str, outdir: str) -> None:
    """Parse the six fixed sections from a HA file and write each to its own file.

    Output files are written as '<outdir>/<stem>/<nn>_<slug>.txt' where nn is
    the 1-based section index (01–06) and slug is the romanised section name.

    @param fpath_ha: path to pdf extracted plain-text
    @param outdir: parent output directory (e.g. 'build/extract/hf').
    """

    report_id = os.path.splitext(os.path.basename(fpath_ha))[0]
    os.makedirs(os.path.join(outdir, report_id), exist_ok=True)

    pat_hdr = re.compile(r"^[ \t]*(?P<sec_num>[１２３４５６７８９０]+)[．\.]?[ \t]*(?P<sec_title>.+)")

    fpath_out = os.path.join(outdir, report_id, "00_pre.txt")
    sink = open(fpath_out, "w", encoding="utf-8")

    with open(fpath_ha) as fh:
        for line in fh:
            line = line.strip().strip("　")
            if line == "": 
                continue 

            if line == "＜引用文献＞":
                if sink: sink.close()
                fname_out = f"{num_norm+1:02d}_bib.txt"
                fpath_out = os.path.join(outdir, report_id, fname_out)
                sink = open(fpath_out, "w", encoding="utf8")
                continue 

            m = pat_hdr.match(line)
            if m: 
                num = m.group("sec_num")
                # multi-char e.g. "１０" → 10
                num_norm = int("".join(str(FULLWIDTH_DIGIT[c]) for c in num))  

                title = m.group("sec_title").strip().strip("　")
                title_norm = SECTIONS.get(title)
                if title_norm is None:
                    """ try: cf.  "原因(図３のガス供給設備の配管系統図参照)" """
                    chunks = re.sub(r"[()（）]", " ", title).strip().split() 
                    title_norm = SECTIONS.get(chunks[0])
                if title_norm is None:
                    if sink: sink.write(f"{line}\n")
                    continue
                # new title 
                if sink: 
                    sink.close()
                    sink = None
                fname_out = f"{num_norm:02d}_{title_norm}.txt"
                fpath_out = os.path.join(outdir, report_id, fname_out)
                sink = open(fpath_out, "w", encoding="utf8")
            else:
                if sink: 
                    sink.write(f"{line}\n")
                else:
                    print(f"PRE: {line}")
    if sink: sink.close()
                

            
    # matches = list(_HEADER_RE.finditer(text))
    # if len(matches) != len(SECTIONS):
    #     raise ValueError(
    #         f"{stem}: expected {len(SECTIONS)} sections, found {len(matches)}"
    #     )

    # section_dir = os.path.join(outdir, stem)
    # os.makedirs(section_dir, exist_ok=True)

    # for i, match in enumerate(matches):
    #     start = match.start()
    #     end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    #     content = text[start:end].strip()

    #     fname = f"{i + 1:02d}_{SECTION_SLUGS[i]}.txt"
    #     fpath = os.path.join(section_dir, fname)
    #     with open(fpath, "w", encoding="utf-8") as f:
    #         f.write(content)


def process_HA_files() -> None:
    """Extract text from all HA*.pdf files in 'build/mandala/crawl/fkd/hf/'.

    For each matching PDF, writes a corresponding .txt file under
    'build/extract/hf/' with the same stem.
    """
    dpath_pdf_root = os.path.join(CRAWL_DIR, "fkd", "hf")
    if not os.path.isdir(dpath_pdf_root):
        raise ValueError("Cannot find dir: %s", dpath_pdf_root)

    ##############################################################
    # PDF -> TEXT
    ##############################################################
    dpath_out_txt = os.path.join(BLD_DIR, "extract", "hf")
    os.makedirs(dpath_out_txt, exist_ok=True)

    LOG.info(f"Input PDF dir  : {os.path.relpath(dpath_pdf_root, PRJ_DIR)}")
    LOG.info(f"PDF extract dir: {os.path.relpath(dpath_out_txt, PRJ_DIR)}")

    pdf_files = sorted(glob.glob(os.path.join(dpath_pdf_root, "HA*.pdf")))
    LOG.info(f"Found {len(pdf_files)} HA*.pdf files")

    for fpath_pdf in pdf_files:
        stem = os.path.splitext(os.path.basename(fpath_pdf))[0]
        fpath_txt = os.path.join(dpath_out_txt, stem + ".txt")
        if os.path.exists(fpath_txt):
            LOG.debug(f"Skipping {stem} (already extracted)")
            continue
        else:
            LOG.debug(f"Extracting {stem}")
            extract_pdf(fpath_pdf, fpath_txt)

    ##############################################################
    # TEXT -> sections
    ##############################################################
    dpath_out_sec = os.path.join(BLD_DIR, "extract", "hf-sections")
    os.makedirs(dpath_out_sec, exist_ok=True)

    txt_files = sorted(glob.glob(os.path.join(dpath_out_txt, "HA*.txt")))
    LOG.info(f"Found {len(txt_files)} PDF exttract HA*.txt files")

    for fpath_txt in txt_files:
        LOG.info(f"Parsing: {os.path.realpath(fpath_txt, )}")
        # text = open(fpath_txt, encoding="utf-8").read()
        # stem = os.path.splitext(os.path.basename(fpath_txt))[0]
        split_sections(fpath_txt, dpath_out_sec)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    process_HA_files()
