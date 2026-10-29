-- 1. Create a refined view for unlisted news words with multi-character and Chinese-only filters
CREATE OR REPLACE VIEW v_top_unlisted_news AS
SELECT 
    n.word, 
    n.count AS news_count,
    n.zipf_news,
    w.zipf_weibo,
    s.zipf_subtlex
FROM news_freq_clean n
LEFT JOIN hsk_master_clean h ON n.word = h.word
LEFT JOIN weibo_freq_clean w ON n.word = w.word
LEFT JOIN subtlex_freq s ON n.word = s.word
WHERE h.word IS NULL
  AND n.word REGEXP '^[一-龥]+$'
  AND CHAR_LENGTH(n.word) > 1
ORDER BY n.count DESC
LIMIT 150;

-- 2. Select the top 20 rows to inspect our refined blind-spot list
SELECT * FROM v_top_unlisted_news LIMIT 20;