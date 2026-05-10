# kdev-ingestor

Python utility that injects kdev-secure-coding rule markdowns into the
Understand-Anything `knowledge-graph.json` as `concept` nodes carrying
`kdev:*` tags. Designed to be 100% non-invasive to UA's schema.

## Install

    pip install -e ".[dev]"

## Run tests

    pytest

## Inject rules into a graph

    kdev-ingest inject \
        --rules-dir ../../kdev-secure-coding/skills/python-security-coding/references \
        --graph .understand-anything/knowledge-graph.json
