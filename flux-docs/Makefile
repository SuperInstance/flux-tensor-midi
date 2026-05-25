PANDOC = pandoc
SRCS = $(shell find . -name '*.md' -not -path './.git/*')
HTMLS = $(SRCS:.md=.html)

.PHONY: html clean serve

html: $(HTMLS)

%.html: %.md
	@mkdir -p $(dir $@)
	$(PANDOC) --standalone --metadata title="$(shell head -1 $< | sed 's/^# //')" \
		--css=style.css \
		-f markdown -t html \
		-o $@ $<

clean:
	find . -name '*.html' -delete

serve: html
	python3 -m http.server 8080

style.css:
	@echo 'body { max-width: 48em; margin: 2em auto; padding: 0 1em; font-family: system-ui, sans-serif; line-height: 1.6; color: #222; }' > $@
	@echo 'pre { background: #f4f4f4; padding: 1em; overflow-x: auto; border-radius: 4px; }' >> $@
	@echo 'code { font-family: "SF Mono", Menlo, monospace; font-size: 0.9em; }' >> $@
	@echo 'table { border-collapse: collapse; width: 100%; margin: 1em 0; }' >> $@
	@echo 'th, td { border: 1px solid #ddd; padding: 0.5em; text-align: left; }' >> $@
	@echo 'th { background: #f8f8f8; }' >> $@
	@echo 'a { color: #0066cc; }' >> $@
	@echo 'blockquote { border-left: 3px solid #ccc; margin: 1em 0; padding: 0.5em 1em; color: #555; }' >> $@
