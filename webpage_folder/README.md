# webpage_folder

Webpage that explains `scripts/make_tides.py`, and the scripts that make its figures.

- `tide_page.html`: the page. It loads the PNGs from `figures/`.
- `common.py`: paths, colours and small helpers for the figure scripts.
- `fig_*.py`: one script per figure. Each writes one PNG to `figures/`.

Make all figures (in the `moana_python` environment):

    cd webpage_folder
    for s in fig_*.py; do python $s; done
