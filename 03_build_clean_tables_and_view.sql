USE hsk_corpus_db;

-- 1. Deduplicate & Clean HSK Master (Regex-strip numbers, English letters, and suffixes)
DROP TABLE IF EXISTS hsk_master_clean;

CREATE TABLE hsk_master_clean AS
SELECT 
    REGEXP_REPLACE(word, '[0-9a-zA-Z[:space:]_]+', '') AS word, 
    MIN(hsk_level) AS hsk_level
FROM hsk_master
WHERE REGEXP_REPLACE(word, '[0-9a-zA-Z[:space:]_]+', '') != ''
GROUP BY REGEXP_REPLACE(word, '[0-9a-zA-Z[:space:]_]+', '');

ALTER TABLE hsk_master_clean MODIFY COLUMN word VARCHAR(100), ADD PRIMARY KEY (word);

-- 2. Aggregate Weibo Frequency to 1:1 Word Grain
DROP TABLE IF EXISTS weibo_freq_clean;

CREATE TABLE weibo_freq_clean AS
SELECT 
    word, 
    SUM(count) AS count,
    ROUND(LOG10((SUM(count) / (SELECT SUM(count) FROM weibo_freq)) * 1000000000), 4) AS zipf_weibo
FROM weibo_freq
GROUP BY word;

ALTER TABLE weibo_freq_clean MODIFY COLUMN word VARCHAR(100), ADD PRIMARY KEY (word);

-- 3. Aggregate News Frequency to 1:1 Word Grain
DROP TABLE IF EXISTS news_freq_clean;

CREATE TABLE news_freq_clean AS
SELECT 
    word, 
    SUM(count) AS count,
    ROUND(LOG10((SUM(count) / (SELECT SUM(count) FROM news_freq)) * 1000000000), 4) AS zipf_news
FROM news_freq
GROUP BY word;

ALTER TABLE news_freq_clean MODIFY COLUMN word VARCHAR(100), ADD PRIMARY KEY (word);

-- 4. Ensure Subtlex Staging Table is Indexed
ALTER TABLE subtlex_freq MODIFY COLUMN word VARCHAR(100);
ALTER TABLE subtlex_freq ADD INDEX idx_word (word);

-- 5. Re-create the Final Joined View
CREATE OR REPLACE VIEW v_hsk_joined AS
SELECT 
    h.word,
    h.hsk_level,
    s.count AS freq_subtlex,
    s.zipf_subtlex,
    w.count AS freq_weibo,
    w.zipf_weibo,
    n.count AS freq_news,
    n.zipf_news
FROM hsk_master_clean h
LEFT JOIN subtlex_freq s ON h.word = s.word
LEFT JOIN weibo_freq_clean w ON h.word = w.word
LEFT JOIN news_freq_clean n ON h.word = n.word;


-- 6. Verification Checks
SELECT 
    COUNT(*) AS total_joined_rows, 
    COUNT(DISTINCT word) AS unique_words 
FROM v_hsk_joined;

SELECT 
    word, 
    hsk_level, 
    zipf_subtlex, 
    zipf_weibo, 
    zipf_news 
FROM v_hsk_joined 
WHERE zipf_subtlex IS NOT NULL 
  AND zipf_weibo IS NOT NULL 
  AND zipf_news IS NOT NULL
LIMIT 10;

SELECT COUNT(*) AS rows_in_view,
       COUNT(zipf_subtlex) AS has_subtlex,
       COUNT(zipf_weibo)   AS has_weibo,
       COUNT(zipf_news)    AS has_news,
       SUM(zipf_subtlex IS NOT NULL AND zipf_weibo IS NOT NULL AND zipf_news IS NOT NULL) AS complete_in_all_three
FROM v_hsk_joined;