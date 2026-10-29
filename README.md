# hsk-vs-real-world-chinese

# Does HSK 3.0 Match Real-World Chinese? A Multi-Register Frequency Analysis

An end-to-end data project that tests whether the level grading of the **revised HSK 3.0 vocabulary list** (July 2026 syllabus) matches how often words are actually used, and whether the answer changes with **register** (spoken-style, social-media and official-press Chinese).

It combines PDF data extraction, Unicode-level data cleaning, three frequency corpora, a MySQL join layer, engineered statistical metrics in Python, and a four-page Power BI dashboard. Because the questions are about language, it also includes a linguistic commentary written from a Chinese-language and translation background.

**Contents**
[Headline results](#headline-results) · [Dashboard](#dashboard) · [Data sources](#data-sources) · [Repository and run order](#repository-and-run-order) · [Pipeline in detail](#pipeline-in-detail) · [Metrics](#engineered-metrics) · [Findings](#key-findings) · [Linguistic notes](#linguistic-notes) · [Data gotchas](#data-gotchas-and-how-they-were-fixed) · [Limitations](#known-limitations) · [Reproducing](#how-to-reproduce) · [Credits](#credits-and-citations)

---

## Headline results

- **HSK levels track frequency overall.** Median word frequency falls steadily from Level 1 to Levels 7-9 in all three corpora.
- **Register tilt is real but modest and depends on the filter.** Levels 1-2 lean toward subtitle (spoken-style) vocabulary and Levels 4-6 lean toward News vocabulary at every minimum-count threshold I tested. The apparent News lean at Levels 7-9 is threshold-dependent (average bias 0.44 with no filter, 0.14 at a minimum count of 50, about 0 at 100), so I report it as suggestive only.
- **Strongly register-bound words are rare:** 163 of 8,165 reliable words (about 2%) differ by 1.5 or more Zipf points between News and subtitles. Spoken-skewed words cluster at Level 1; News-skewed words peak at Level 5.
- **Out-of-vocabulary (OOV) words mostly reflect gaps in the frequency lists, not rarity.** The OOV rate is highest at Level 1 (7.0%), driven by numerals, compounds the corpus segmenter splits, and erhua forms.
- **Common News words absent from the HSK 3.0 word list** are mostly proper nouns, press terms and some everyday compounds (这种, 不能, 还有). The News list appears to be official-press text, which colors every "news skew" result.

## Dashboard

The Power BI report is exported as [`dashboard_export.pdf`](dashboard_export.pdf) (four pages).

| Page | What it shows |
|---|---|
| **1. Overview and Incomplete Words** | Median Zipf by HSK level for each corpus (reliable words), plus a table of the 338 HSK words missing from at least one corpus, with a "Missing From" column and an HSK level slicer |
| **2. Register Bias and Out-of-Vocabulary** | Average news-minus-spoken bias by level (reliable words); counts of strongly News-skewed and Spoken-skewed words by level; OOV count and OOV rate by level; the top high-frequency News words that are not in the HSK 3.0 list, with their Weibo and subtitle Zipf values |
| **3. News Frequency Gaps** | The 10 words furthest above and furthest below their level's typical News frequency |
| **4. About and Limitations** | Sources, definitions, which word set each chart uses, findings and limitations |

Power BI content: measures `Median_Subtlex_Zipf`, `Median_Weibo_Zipf`, `Median_News_Zipf`, `OOV_Count` and `OOV_Rate`; a calculated column `Skew Class` (News-skewed at bias >= 1.5, Spoken-skewed at bias <= -1.5). The report reads the `hsk_engineered_metrics` table and the `v_top_unlisted_news` view from MySQL. The `.pbix` file is not included; the PDF is the deliverable.

## Data sources

Raw data is **not** redistributed in this repository. Download each source and place it in `data/raw/` (see [How to reproduce](#how-to-reproduce)). Check each source's terms of use.

| Source | What it is | Used for |
|---|---|---|
| **HSK 3.0 vocabulary lists**, July 2026 revised syllabus, via [MandarinBean](https://mandarinbean.com/new-hsk-vocabulary/) (seven PDFs: Levels 1-6 individually, Levels 7-9 combined) | 11,000 words with level, pinyin, part of speech and (Levels 1-6) English; the syllabus counts are 300 / 500 / 1,000 / 2,000 / 3,600 / 5,400 / 11,000 cumulative | The vocabulary being evaluated |
| **SUBTLEX-CH** ([Ghent University](https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch)) | Word frequencies from film and TV subtitles, 2010, about 33.5 million words, 99,121 entries | Spoken-style register (scripted dialogue as a proxy for speech) |
| **BCC Weibo word list** (BLCU Chinese Corpus, [BCC_LEX_Zh](http://bcc.blcu.edu.cn/downloads/resources/BCC_LEX_Zh.zip)) | Social-media word frequencies, about 4.26 billion tokens, 328,257 entries | Informal written register |
| **BCC News word list** (same corpus) | News word frequencies, about 1.53 billion tokens, 406,779 entries. The most frequent non-HSK words (本报讯, 新华社, 毛主席) suggest official-press text | Formal written register |
| **CC-CEDICT** ([MDBG](https://www.mdbg.net/chinese/dictionary?page=cc-cedict)) | Open Chinese-English dictionary | Back-filling English glosses for HSK Levels 7-9, which the source PDF does not provide |

The Weibo and News lists have no header row and two tab-separated columns (word, count). SUBTLEX-CH has a header and 15 columns (including pinyin, part of speech and English translations), of which only the word and count are used for frequency.

## Repository and run order

```
.
├── 00_extract_hsk_pdfs.py               # PDF tables -> raw CSV (11,000 rows)
├── 01_clean_hsk_vocabulary.ipynb        # Unicode, part-of-speech and English cleaning
├── 02_clean_corpora.ipynb               # clean the 3 corpora, compute Zipf, load MySQL
├── 03_build_clean_tables_and_view.sql   # clean tables, primary keys, joined view
├── 04_blind_spot_view.sql               # News words absent from the HSK list
├── 05_metric_engineering.ipynb          # metrics, analysis, write hsk_engineered_metrics
├── dashboard_export.pdf                 # Power BI dashboard (4 pages)
└── README.md
```

Run the files in numeric order. Details are in [How to reproduce](#how-to-reproduce).

## Pipeline in detail

### Stage 0. Extract the vocabulary tables from PDF (`00_extract_hsk_pdfs.py`)

The seven PDFs hold the word lists as tables. Reading the text line by line scrambles entries whose part of speech or translation wraps onto a second line, so the script uses **word coordinates** (via `pdfplumber`): it finds the header row's x-positions and assigns every word to a column by where it sits on the page. Wrapped continuation lines are appended to the right column of the previous entry.

Validation: the parsed entry counts match the official per-level counts exactly (300, 200, 500, 1,000, 1,600, 1,800 and 5,600 new words per level; 11,000 in total).

The output is deliberately raw. The next stage fixes what the PDF font encoding got wrong.

### Stage 1. Clean the HSK vocabulary (`01_clean_hsk_vocabulary.ipynb`)

1. **Part-of-speech standardization.** Raw tags look like `adjective、 preposition、 （verb、 classifier）`. A regular expression extracts the tag tokens, Levels 7-9's single-character Chinese tags (动, 名, 形 and so on) are mapped onto the same English vocabulary, duplicates are removed, and the result is stored as a pipe-delimited list. 1,179 raw entries have several tags; after cleaning 1,177 remain multi-tag (two collapsed because a tag was repeated). An indentation bug that kept only the last tag was found through this check and fixed.
2. **Unicode normalization (NFKC).** The PDF font stored common characters (八, 一, 大, 子, 工 ...) as visually identical **Kangxi radical** code points. About 2,166 words were affected, and they silently failed to match any corpus until normalized.
3. **口 mistaken for 又.** The 45 words containing 口 came through as the radical form of 又. NFKC turns that into the real 又, which is still the wrong character, so these were fixed by cross-checking each word's pinyin (kǒu) and leaving the one genuine 又 (yòu) untouched.
4. **Excel date corruption.** Opening and re-saving the CSV in Excel turned the level label `7-9` into a date (`7-Sep`); it was restored.
5. **English for Levels 7-9.** The source PDF has no translations for the top tier, so glosses were looked up in CC-CEDICT using normalized keys (sense-number suffixes and erhua 儿 stripped), with the last few entries filled by hand.

### Stage 2. Clean the three frequency corpora (`02_clean_corpora.ipynb`)

- **Load.** Weibo and News: tab-separated, no header. SUBTLEX-CH: tab-separated with a header; only `Word` and `WCount` are used.
- **Duplicates.** SUBTLEX-CH has 388 repeated words (one per pinyin reading), Weibo 2 (`0%`, `1100%`), News 0. Repeats are merged with group-by and sum, because the project measures the written word, not each reading.
- **Normalization.** NFKC on every word column.
- **Invisible characters.** The Weibo list contains 38 tokens with control characters (for example `\x14一`, a real word with an invisible character glued on, plus tokens that are only invisible characters). They are dropped. See [Data gotchas](#data-gotchas-and-how-they-were-fixed) for why this matters.
- **Symbol noise check.** Single-character tokens that are not Chinese characters: 1,094 of 406,779 News entries (0.27%) and 1,566 of 328,257 Weibo entries (0.48%). The tilde `~` is the sixth most frequent Weibo token, a small illustration of informal register.
- **Zipf scores.** Each corpus is converted to the Zipf scale (below) using that corpus's own summed counts as the denominator. This is what makes three corpora of very different sizes comparable.
- **Load into MySQL** as `hsk_master`, `subtlex_freq`, `weibo_freq` and `news_freq`.

**The Zipf scale.** `Zipf = log10(count / corpus total * 1,000,000,000)`, equivalent to `log10(frequency per million) + 3` (van Heuven et al., 2014). Each +1 means ten times more frequent. Observed values run from below 1 for the rarest words to about 7.8 for 的.

### Stage 3. The SQL layer (`03_build_clean_tables_and_view.sql`)

- `hsk_master_clean`: a regular expression strips sense digits, stray Latin letters and spaces from HSK entries (36 words changed: 35 trailing digits such as 花2, and `劳verb`), then `GROUP BY word` with `MIN(hsk_level)` leaves **10,896 unique words**. Where a word appeared at several levels, the lowest is kept.
- `weibo_freq_clean`, `news_freq_clean`: `GROUP BY word` with `SUM(count)`, Zipf recomputed in SQL from the summed count and the corpus total taken from a `SUM` subquery (never typed by hand), and a **primary key on `word`**, so a duplicate would fail loudly instead of silently multiplying rows.
- `v_hsk_joined`: `LEFT JOIN`s from the HSK table to each corpus. The `LEFT JOIN` keeps every HSK word, and a `NULL` means "not in that corpus". That `NULL` is what becomes the OOV flag in Python.
- Built-in verification queries: 10,896 rows in the view, of which 10,558 are present in all three corpora.

Why SQL for the join and Pandas for the metrics: the join is relational work (keys, join types, constraints), and the row-wise arithmetic across several Zipf columns is simpler to write and debug in Pandas.

### Stage 4. The blind-spot view (`04_blind_spot_view.sql`)

`v_top_unlisted_news` is an anti-join (`LEFT JOIN ... WHERE h.word IS NULL`) that finds the most frequent News words that are not in the HSK list. Filters: Chinese characters only (`REGEXP '^[一-龥]+$'`), more than one character (`CHAR_LENGTH(word) > 1`), top 150 by count. It also brings in the Weibo and subtitle Zipf values, so a word that is missing everywhere can be told apart from one missing only because it is a News-specific term.

### Stage 5. Metric engineering and analysis (`05_metric_engineering.ipynb`)

Reads `v_hsk_joined`, builds the metrics below, runs the analysis in the next sections, and writes the result to MySQL as `hsk_engineered_metrics` (10,896 rows, `VARCHAR` types for `word` and `hsk_level`, indexes on `word`, `hsk_level` and `oov_flag`).

## Engineered metrics

| Metric | Definition |
|---|---|
| `in_subtlex`, `in_weibo`, `in_news` | 1 if the word has a value in that corpus |
| `corpora_present_count`, `oov_flag` | How many corpora contain the word; `oov_flag = 1` if any is missing |
| `min_count`, `reliable_flag` | Smallest raw count across the three corpora; `reliable_flag = 1` if the word is present in all three **and** `min_count >= 50` (8,165 words) |
| `mean_zipf` | Mean of the three Zipf values |
| `rsi` (Register Skew Index) | Highest Zipf minus lowest Zipf across the three corpora. Large means the word's popularity swings between registers |
| `news_vs_spoken_bias` | Zipf News minus Zipf subtitles; positive leans News. Also `social_vs_spoken_bias` and `news_vs_social_bias` |
| `register_dispersion` | Standard deviation of the three Zipf values |
| `is_single_char`, `missing_from` | Whether the word is one character; which corpora lack it |
| `Skew Class` (Power BI) | News-skewed (bias >= 1.5), Spoken-skewed (bias <= -1.5), otherwise Neutral |

**Design decisions**

- **OOV rows get `NaN`, not 0, for every spread metric.** A word with a single value would otherwise get an RSI of exactly 0, which looks like perfect stability but is really missing data.
- **A minimum-count filter** (`reliable_flag`), because a Zipf score built from a handful of occurrences is noise. 外资 and 华侨 each occur once in the 33.5-million-word subtitle corpus yet topped the first skew ranking.
- **Low RSI means stable, not common.** "Stable core" words are therefore low RSI **and** high `mean_zipf` (at least 4.5).
- **The 50-count threshold is a judgment call**, so the analysis shows how results change at 20 and 100 rather than treating 50 as optimal.

## Key findings

All numbers come from the pipeline above. Medians and biases use reliable words unless stated.

**Dataset:** 10,896 HSK words; 10,558 present in all three corpora; 338 incomplete; 8,165 reliable.

### 1. HSK levels track frequency

| Level | Reliable words | Median Zipf: subtitles | Weibo | News |
|---|---|---|---|---|
| 1 | 275 | 5.50 | 5.50 | 5.19 |
| 2 | 185 | 5.19 | 5.23 | 4.93 |
| 3 | 464 | 4.81 | 4.95 | 4.81 |
| 4 | 930 | 4.56 | 4.71 | 4.74 |
| 5 | 1,447 | 4.20 | 4.45 | 4.60 |
| 6 | 1,471 | 3.93 | 4.12 | 4.29 |
| 7-9 | 3,393 | 3.66 | 3.77 | 3.84 |

### 2. Register tilt, and how fragile it is at the top

Average news-minus-spoken bias by level, under different filters:

| Level | All complete words | Count >= 20 | Count >= 50 | Count >= 100 |
|---|---|---|---|---|
| 1 | -0.28 | -0.28 | -0.30 | -0.30 |
| 2 | -0.20 | -0.20 | -0.22 | -0.24 |
| 3 | 0.05 | 0.04 | 0.02 | -0.01 |
| 4 | 0.25 | 0.22 | 0.21 | 0.18 |
| 5 | 0.47 | 0.43 | 0.41 | 0.37 |
| 6 | 0.47 | 0.41 | 0.33 | 0.25 |
| 7-9 | 0.44 | 0.28 | 0.14 | 0.01 |

Levels 1-2 lean spoken and Levels 4-6 lean toward News at every threshold. The Levels 7-9 result changes with the threshold, so I do not claim it. Two explanations remain open: noise from tiny subtitle counts, or the filter removing genuinely News-only words that are rare in subtitles.

### 3. Strongly register-bound words are rare and clustered

Reliable words with a bias of at least 1.5 in either direction:

| Level | Spoken-skewed | News-skewed | Reliable words | Share |
|---|---|---|---|---|
| 1 | 11 | 1 | 275 | 4.4% |
| 2 | 1 | 0 | 185 | 0.5% |
| 3 | 0 | 4 | 464 | 0.9% |
| 4 | 6 | 16 | 930 | 2.4% |
| 5 | 4 | 54 | 1,447 | 4.0% |
| 6 | 2 | 23 | 1,471 | 1.7% |
| 7-9 | 13 | 28 | 3,393 | 1.2% |
| **Total** | **37** | **126** | **8,165** | **2.0%** |

The 1.5 cutoff is an analyst choice. Most vocabulary behaves similarly across registers; a small minority is strongly bound to one.

**Most register-skewed reliable words.** Spoken-style: 晚安, 嗯, 抱歉, 嘿, 拜托. News-style: 社会主义, 职工, 农村, 建设, 群众.
**Stable core** (low RSI, mean Zipf >= 4.5): 根, 大学, 改变, 上去, 除了, 特别.

### 4. Single-character words behave differently

Among reliable words, 1,429 are single characters (average bias 0.08) and 6,736 are multi-character (average bias 0.23). A plausible reason is that the corpora segment text differently, which distorts single-character counts. This is a hypothesis, not a tested result.

### 5. Out-of-vocabulary words

338 of 10,896 words (3.1%) are missing from at least one corpus. 177 are missing from subtitles, 232 from Weibo and 226 from News.

| Level | HSK words | OOV | OOV rate |
|---|---|---|---|
| 1 | 300 | 21 | 7.0% |
| 2 | 197 | 8 | 4.1% |
| 3 | 491 | 14 | 2.9% |
| 4 | 990 | 21 | 2.1% |
| 5 | 1,579 | 24 | 1.5% |
| 6 | 1,777 | 45 | 2.5% |
| 7-9 | 5,562 | 205 | 3.7% |

Levels 7-9 hold the most OOV words only because they hold half the vocabulary; the **rate** is highest at Level 1. The causes are list artifacts: the BCC lists lack bare numerals (一, 二, 三, 十 and the digits are absent); the BCC segmenter appears to split some compounds (下载, 上传, 主播, 手机, 黑客 are missing from the BCC lists while the single characters 载, 传, 播 have very large counts); modern terms such as 高铁 and 链接 are missing from the 2010 subtitles; and HSK lists erhua forms (面条儿) that the corpora write without 儿. **OOV means "not a token in that list", not "unused".**

### 6. High-frequency News words that are not in the HSK 3.0 list

The most frequent (Chinese-only, multi-character) are 美国, 全国, 毛主席, 我国, 新华社, 本报讯, 这种, 北京, 不能, 劳动. They fall into groups: proper nouns (美国, 北京; HSK materials may list proper names separately, so these are not necessarily omissions), press and political terms (新华社, 本报讯, 毛主席), and everyday compounds that are common in every register (这种, 不能). The compounds are the pedagogically interesting group, since HSK may deliberately omit them because they are built from listed parts. That is a hypothesis to test, not a finding.

### 7. Words furthest from their level's typical News frequency

Gap = a word's News Zipf minus the median News Zipf of its HSK level (dashboard page 3).

- **Above their level:** 同志, 社会主义, 群众, 革命, 人民, 我们, 委员会, 机关, 工作, 生产. Mostly institutional vocabulary. Level 1 entries such as 我们 and 工作 are common in all registers and cannot be placed lower, so for them the gap reflects overall frequency rather than News tilt.
- **Below their level:** 好玩儿, 晚安, 叉子, 改天, 冰激凌, 差点儿, 甜品, 橙子, 勺子, 吸管. Everyday topic and colloquial words that official press rarely uses.

## Linguistic notes

These are my interpretations from a Chinese-language and translation background. They are hypotheses grounded in the data, not tested claims. Zipf values are subtitles / Weibo / News; a dash means the word is not in that list.

| Word | HSK level | Zipf: subtitles / Weibo / News |
|---|---|---|
| 晚安 | 4 | 5.05 / 5.61 / 2.48 |
| 嗯 | 4 | 6.01 / 5.14 / 3.46 |
| 抱歉 | 4 | 5.81 / 4.34 / 3.31 |
| 嘿 | 6 | 6.09 / 4.84 / 3.62 |
| 拜托 | 7-9 | 5.40 / 4.39 / 2.95 |
| 社会主义 | 7-9 | 3.34 / 4.17 / 5.96 |
| 群众 | 6 | 3.78 / 4.53 / 6.14 |
| 干部 | 7-9 | 2.84 / 4.31 / 5.99 |
| 同志 | 7-9 | 4.75 / 4.52 / 5.98 |
| 农村 | 4 | 3.22 / 4.38 / 5.73 |
| 好玩儿 | 1 | 3.43 / 3.61 / 1.74 |
| 冰激凌 | 3 | 3.94 / 4.01 / 2.57 |
| 勺子 | 3 | 3.66 / 3.85 / 2.80 |
| 改天 | 5 | 3.81 / 4.13 / 2.43 |
| 差点儿 | 4 | 3.69 / 3.25 / 2.65 |
| 根 | 5 | 5.01 / 5.03 / 5.01 |
| 大学 | 1 | 5.12 / 5.12 / 5.10 |
| 手机 | 1 | 5.03 / - / - |
| 面条儿 | 1 | - / - / - |

- **晚安 (Level 4).** A conversational closing formula addressed to another person, so it is frequent in dialogue and in Weibo posts and almost absent from press text. Its subtitle frequency (5.05) sits near the Level 2-3 medians (5.19 and 4.81), yet it is placed at Level 4.
- **嗯, 嘿, 抱歉, 拜托.** Interactional words (backchannel, attention-getter, apology, request) that carry discourse function rather than content, which explains the spoken skew. 拜托 at Levels 7-9 has a subtitle Zipf (5.40) close to the Level 1-2 medians (5.50 and 5.19), making it a candidate for earlier placement.
- **社会主义, 群众, 干部, 同志, 农村.** Institutional vocabulary of official discourse: News Zipf of about 5.7 to 6.1 against about 2.8 to 4.8 in subtitles. Because the News list looks like party-press text, the "news skew" here is partly an "official discourse" skew. 同志 is polysemous, with a political sense and an informal modern one; the frequency counts cannot separate them.
- **好玩儿, 冰激凌, 勺子, 改天, 差点儿.** Everyday topic and colloquial vocabulary (food, tableware, colloquial adverbials) that is rare in News (Zipf 1.7 to 2.8). Their placement at Levels 1-5 looks driven by communicative themes more than raw frequency, which is a hypothesis. 好玩儿 and 差点儿 are erhua forms, a feature of spoken (especially northern) Mandarin.
- **根, 大学.** Almost identical Zipf in all three registers (about 5.0 to 5.1): register-stable and common. 根 is a single character, so the segmentation caveat applies.
- **手机, 面条儿 (the OOV examples).** 手机 is common in subtitles (5.03) but absent from the BCC lists, most likely a segmentation effect. 面条儿 is the HSK's erhua spelling, while all three corpora contain 面条. Both show that OOV reflects list artifacts, not rarity.

## Data gotchas and how they were fixed

Most of the work on this project was finding why results were quietly wrong. Each of these produced plausible-looking output.

| Issue | How it showed up | Cause | Fix |
|---|---|---|---|
| Look-alike characters | Only about 79% of HSK words matched a frequency corpus; basic words like 八 failed | PDF font stored common characters as Kangxi radical code points | NFKC normalization; match rate rose to about 98% |
| 口 read as 又 | 45 words with pinyin kǒu showed 又 | Font mapping error that NFKC alone cannot fix | Cross-check against pinyin; keep the genuine 又 |
| Wrapped table cells | Scrambled part-of-speech and English columns | Line-by-line text extraction cannot tell which column a wrapped line belongs to | Assign words to columns by x-coordinate |
| Title block and footer leaking | 11,001 rows instead of 11,000; stray digits in entries | "Level 7 - 9" and the page and level numbers share x-positions with data columns | Filter the title block; drop the whole footer line |
| Lost part-of-speech tags | 1,179 multi-tag entries but almost none survived cleaning | Inner loop indented outside the token loop, keeping only the last tag | Re-indented; verified 1,177 multi-tag rows |
| Excel date conversion | Level `7-9` became `7-Sep` | Excel auto-converted text when the CSV was round-tripped | Restored; avoid saving CSVs through Excel |
| Garbled Chinese in Excel | Characters unreadable on opening | CSV lacked a UTF-8 byte-order mark | Write `utf-8-sig` |
| Join fan-out | View returned 11,014 rows for 10,921 distinct words | Repeated HSK words, plus MySQL's case-, accent- and kana-insensitive comparison treating different corpus tokens as equal | Merge in clean tables, primary keys on `word`, regex cleanup of sense digits (10,896 rows) |
| Invisible characters | HSK 一 received a Weibo frequency of 22 (Zipf 0.7) | The Weibo list has a token `\x14一`; MySQL ignores control characters when comparing | Drop the 38 Weibo tokens containing control characters |
| Hard-coded corpus total | News Zipf ran above 9, which is impossible | A typed total of 33,000,000 instead of 1,533,155,467 (about 46 times too small, inflating News Zipf by about 1.67) | Compute the total with a `SUM` subquery; the top word now scores about 7.8 in News |
| TEXT columns | MySQL error 1170 when indexing | `to_sql` writes text columns as `TEXT`, which cannot be indexed without a length | Specify `VARCHAR` dtypes |
| Silent zero | RSI of 0 for words with one value | `max` and `min` skip missing values | Set spread metrics to `NaN` for OOV words |
| Noise at the extremes | Top skew list led by words with a corpus count of 1 | Zipf from tiny counts is unstable | `reliable_flag` (minimum count 50 in every corpus) |
| Object clutter | Views pointing at wrong tables | Versioned experiment tables (`..._clean1`, `..._clean2`) | One name per table; scripts drop and recreate |

## Known limitations

- **The subtitle corpus is small and from 2010** (about 33.5 million words), so rare-word counts are noisy and modern vocabulary is missing. Scripted dialogue is a proxy for speech, not speech.
- **The News list is not general journalism.** It appears to be official-press text, possibly spanning decades, so the News register partly means "official discourse".
- **The BCC lists omit bare numerals and appear to split some compounds**, so OOV means "not a token in that list".
- **Tokenization differs across corpora.** Single-character words are distorted, and a compound can be counted as one token in one corpus and two in another.
- **Thresholds are analyst choices:** the minimum count of 50 and the skew cutoff of 1.5. The Levels 7-9 result is threshold-dependent.
- **Merged sense variants.** Merging 花 and 花2 keeps the lowest HSK level; the later sense is lost.
- **"Not in the HSK list" means absent from the 11,000-word list.** Proper names may be listed separately.
- **Gap lists conflate sources of difference.** News Zipf minus the level's median News Zipf mixes overall frequency with register effects, and Level 1 words cannot be placed lower.
- **A frequency count does not separate word senses** (for example 同志).
- **Descriptive, not causal.** Nothing here shows how the HSK syllabus was designed or how learners should be taught.

## How to reproduce

**Requirements:** Python 3 with `pandas`, `numpy`, `sqlalchemy`, `pymysql`, `pdfplumber` and Jupyter; MySQL 8.0 or later (the scripts use `REGEXP_REPLACE`).

1. Create a `data/raw/` folder and place the downloaded sources in it: the seven HSK level PDFs (named `New-HSK-Vocabulary-Level-1.pdf` to `Level-6.pdf` and `New-HSK-Vocabulary-Level-7-9.pdf`), SUBTLEX-CH, the BCC Weibo and News word lists, and the CC-CEDICT file.
2. Create an empty MySQL database named `hsk_corpus_db` (utf8mb4).
3. In each notebook, set the connection string for your own MySQL account. The files contain only a placeholder password (`password`); never commit a real one. The metrics notebook asks for the password when it reads from MySQL.
4. Run in order:
   1. `python 00_extract_hsk_pdfs.py --pdf-dir data/raw --out data/raw/hsk_vocabulary_raw_uncleaned.csv`
   2. `01_clean_hsk_vocabulary.ipynb`
   3. `02_clean_corpora.ipynb` (loads the four staging tables)
   4. `03_build_clean_tables_and_view.sql`. Step 4 of this script (indexing `subtlex_freq`) is run-once; skip it on re-runs.
   5. `04_blind_spot_view.sql`
   6. `05_metric_engineering.ipynb`
5. Verify: the view `v_hsk_joined` should have 10,896 rows, with 10,558 present in all three corpora and 8,165 reliable words once the metrics notebook has run.

Update the file paths in the notebooks to match your `data/raw/` locations.

## Skills demonstrated

Python (pandas, NumPy, SQLAlchemy, pdfplumber) · SQL (CTAS, joins, anti-joins, views, primary keys, `REGEXP_REPLACE`, aggregate and verification queries) · Unicode and encoding debugging · data validation against independent counts · statistical metric design (Zipf normalization, minimum-count filtering, sensitivity analysis, handling of missing data) · Power BI (measures, calculated columns, report design) · corpus linguistics and register analysis · reproducible documentation.

## AI assistance

I used Claude (Anthropic) for guidance throughout, including the PDF extraction script, debugging of encoding and join problems, and methodology review. I ran, checked and adapted the code, and made the analytical decisions. Counts were validated against independent rebuilds from the raw files.

## Credits and citations

- Cai, Q., & Brysbaert, M. (2010). SUBTLEX-CH: Chinese word and character frequencies based on film subtitles. *PLoS ONE, 5*(6), e10729.
- van Heuven, W. J. B., Mandera, P., Keuleers, E., & Brysbaert, M. (2014). SUBTLEX-UK: A new and improved word frequency database for British English. *Quarterly Journal of Experimental Psychology, 67*(6), 1176-1190. (Zipf scale.)
- BCC corpus word lists: Beijing Language and Culture University (BLCU).
- HSK vocabulary lists compiled by [MandarinBean](https://mandarinbean.com/new-hsk-vocabulary/) from the HSK 3.0 syllabus.
- CC-CEDICT, released under a Creative Commons Attribution-ShareAlike license.

## Author

**[Magda Maurice Bebawy]** · [www.linkedin.com/in/magda-maurice-8383523b8] · [magymaurice100@gmail.com]
Background: Chinese language, literature and translation; self-taught data analyst.
