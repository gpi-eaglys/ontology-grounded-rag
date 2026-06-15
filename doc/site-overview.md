# Failure Knowledge Database (FKD)
* **FKD** (**失敗知識データベース**) is a Japanese web database of accident and failure cases in science and technology, maintained by the NPO _Association for the Study of Failure_ (ASF).


```
build/mandala/crawl/
├── eshippai                   # Crawl of the e-Shippai site (NPO Association for the Study of Failure)
│   └── html                   # Entry-point PHP/HTML pages
├── fkd                        # 失敗知識データベース — Failure Knowledge Database (FKD)
│   ├── cf                     # Case files: individual failure case pages (CA*.html)
│   │
│   ├── en                     # English-language mirror of the FKD
│   │   ├── cfen               # English case files (CA1*.html)
│   │   ├── hfen               # English case PDFs (HA1*.pdf)
│   │   ├── infen              # English info pages (Mandara explanation, etc.)
│   │   ├── lisen              # English list/index pages
│   │   ├── mfen               # English media images (MA1*.jpg)
│   │   └── sfen               # English case summary pages (SA1*.html)
│   │
│   ├── hf                     # Case PDF documents (HA*.pdf)
│   ├── include                # Shared CSS/JS layout assets
│   ├── inf                    # Info pages (Mandara explanation, etc.)
│   ├── lis                    # Category list/index pages
│   ├── mf                     # Media images for cases (MA*.gif/jpg)
│   └── sf                     # Case summary pages (SA*.html)
│
├── hatamura                   # Content from Hatamura Yotaro's failure knowledge site
│   └── playvid                # Video player pages for lecture recordings
│
└── shippai                    # shippai.net ASF failure case database
    ├── exhibit                # Exhibition/showcase pages
    │   └── img                # Exhibition images
    ├── html                   # Main HTML pages
    │   └── BalanceSheet       # NPO annual balance sheet PDFs
    ├── member                 # Member area pages
    │   └── personal           # Personal member profile pages
    └── personal               # Personal pages (top-level)
```

* `en/` mirrors everything in English 
  * with a 1 inserted in the ID prefix \ (e.g. CA0* → CA1*)
* core structure:
    ```
    cf   CA1*.html       — case files
    mf   CA1*.{jpg,gif}  — images referenced in case files
    sf   SA1*.html       — summary files   
    ```

    ```
    inf  .html     — landing page    
    lis  .html     — 'l': categorized lists of cases, ref to `cf/` pages
    hf   .pdf     HA*  — 'hf': hazard files: detailed case analysis PDFs
    ```

* 


## Case 216: Titanic
* related files (Enlgsh files omitted)
```
./cf/CA0000216.html   Case file
./hf/HA0000216.pdf    本文 document Hazard file 
./sf/SA0000216.html   Summary 
```
*  `HA0000216.pdf`  contains:
```
１. 事象         — incident description
２. 経過         — sequence of events / timeline
３. 原因         — root cause analysis
４. 対処         — immediate response
５. 対策         — countermeasures / lessons learned
６. 総括         — overall summary
```

So each HA*.pdf is a structured narrative report for one failure case, paired with the corresponding CA*.html page by the same ID number. hf probably stands for Honbun File (本文 = full text / body), not hazard — it's the long-form document while sf (SA*.html) is the shorter summary.