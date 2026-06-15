

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