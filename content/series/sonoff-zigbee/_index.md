+++
title = "A Wired Sonoff Zigbee Alternative"
template = "series.html"
transparent = true
insert_anchor_links = "left"

# Series run oldest-first, but Zola's sort_by = "date" is newest-first. Per
# tabi's docs the only way to flip it without touching every post is to
# paginate the section and reverse it.
sort_by = "date"
paginate_by = 9999
paginate_reversed = true

[extra]
series = true
show_previous_next_article_links = true

[extra.series_intro_templates]
default = "Part $SERIES_PAGE_INDEX of $SERIES_PAGES_NUMBER in $SERIES_HTML_LINK."

[extra.series_outro_templates]
next_only = "Next in this series: $NEXT_HTML_LINK"
middle = "Next in this series: $NEXT_HTML_LINK"
prev_only = "That is the end of the series. Previously: $PREV_HTML_LINK"
+++

Flashing Tasmota onto the EACHEN ZB-GW03 to get a wired Zigbee coordinator, and the run of firmware fixes that followed.
