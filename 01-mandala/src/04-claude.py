import json
import os
import time
import logging
import anthropic

LOG = logging.getLogger(__name__)

SCRIPT_DIR = os.path.realpath(__file__)
PRJ_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BLD_DIR = os.path.join(PRJ_DIR, "build")

client = anthropic.Anthropic(max_retries=5)  # needs 'ANTHROPIC_API_KEY' in env

SECTIONS: dict[str, str] = {
    "表題":     "pre",
    "参考文献": "bib",
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
SECTIONS_INV = {v: k for k, v in SECTIONS.items()}

TOOL = {
    "name": "extract_entities_relations",
    "description": "Extract entities and relations from a failure case section.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name":  {"type": "string"},
                        "type":  {"type": "string", "enum": [
                            "Person", "Organization", "Equipment",
                            "Location", "Substance", "Phenomenon", "Other"
                        ]},
                    },
                    "required": ["name", "type"],
                },
            },
            "relations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source":   {"type": "string"},
                        "relation": {"type": "string", "enum": [
                            "CAUSED_BY", "LED_TO", "INVOLVES", "TRIGGERED", 
                            "OCCURRED_AT", "PREVENTED_BY", "OTHER"
                        ]},
                        "target":   {"type": "string"},
                    },
                    "required": ["source", "relation", "target"],
                },
            },
        },
        "required": ["entities", "relations"],
    },
}

def extract_relations(section_name: str, text: str) -> dict:
    """
    Extracts entities and relations from a failure case section using Claude.

    Sends the section text to Claude Haiku via the Anthropic tool-use API,
    forcing a call to the ``extract_entities_relations`` tool so the response
    is always structured JSON.

    @param section_name: The name of the section within the failure case document
        (e.g. ``"原因"`` or ``"対策"``). Used to contextualise the prompt sent to
        the model.
    @param text: The raw text content of the section to analyse.
    @return: A dict with two keys extracted by the tool:
        - ``"entities"`` : list of entity dicts (``{"name": str, "type": str, ...}``).
        - ``"relations"``: list of relation dicts (``{"source": str, "target": str, "type": str, ...}``).
    """
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "extract_entities_relations"},
        messages=[{
            "role": "user",
            "content": (
                f"以下は失敗事例の「{section_name}」セクションです。\n"
                f"エンティティと関係を抽出してください。\n\n{text}"
            ),
        }],
    )
    return response.content[0].input  # {"entities": [...], "relations": [...]}


def test_one(report: str = "HA0000601", section: str = "03_genin.txt") -> None:
    """Run extract() on a single hardcoded sample and print the result.

    Uses a short inline Japanese text that mimics the '原因' (cause) section
    of a failure case report, so the test can run without any pipeline output
    in the build directory.

    @return: None
    """
    fpath_sec = os.path.join(SECTIONS_DIR, report, section)
    if not os.path.isfile(fpath_sec):
        raise ValueError(f"Cannot find file: {fpath_sec}")

    lines = []
    with open(fpath_sec) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("３． 原因"): 
                continue 
            if line == "": 
                continue 
            lines.append(line)

    sample_section = "原因"
    sample_text = "".join(lines)

    result = extract_relations(sample_section, sample_text)

    print(f"{report}::entities ================================================")
    for ent in result.get("entities", []):
        print(f"  {ent['type']:12s}  {ent['name']}")
    print(f"{report}::relations ================================================")
    for rel in result.get("relations", []):
        print(f"  {rel['source']}  --[{rel['relation']}]-->  {rel['target']}")
    print(f"=====================================================================")

    return result


def process_sections():
    dpath_in = os.path.join(BLD_DIR, "extract", "hf-sections")
    dpath_out = os.path.join(BLD_DIR, "extract", "hf-relations")
    n_in, n_proc, n_already = 0, 0, 0
    for root, dnames, fnames in os.walk(dpath_in):
        for fname in fnames: 
            fpath_in = os.path.join(root, fname)
            report_id = fpath_in.split("/")[-2]
            fname_out = os.path.join("{}.json".format(os.path.splitext(fname)[0]))
            fpath_out = os.path.join(dpath_out, report_id, fname_out)
            n_in += 1
            if os.path.isfile(fpath_out):
                LOG.info(f"Already extracted: {fpath_in}")
                n_already += 1
                continue

            os.makedirs(os.path.dirname(fpath_out), exist_ok=True)
            
            # get section name
            sec_name_ascii = os.path.splitext(fname)[0].split("_")[-1]
            sec_name_kanji = SECTIONS_INV[sec_name_ascii]
            with open(fpath_in, encoding="utf-8") as fh:
                text = fh.read()

            time.sleep(3)
            result = extract_relations(sec_name_kanji, text)
            LOG.info(f"Processing  ({n_in}): {fpath_out}")
            with open(fpath_out, "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
    LOG.info(f"Files: {n_proc}/{n_already}/{n_in} ")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    # test_one()
    process_sections()

