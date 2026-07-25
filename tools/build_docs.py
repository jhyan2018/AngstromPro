"""Build the bundled offline HTML documentation from the Markdown sources."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs"
OUTPUT = ROOT / "src" / "angstrompro" / "resources" / "docs"

NAVIGATION = [
    (
        "User Guide",
        [
            "user-guide/getting-started.md",
            "user-guide/planewave-synthesiser.md",
            "user-guide/workspaces-and-inspector.md",
            "user-guide/processes.md",
            "user-guide/image-stack-viewer.md",
            "user-guide/curve-stack-viewer.md",
            "user-guide/data-browser.md",
            "user-guide/file-formats.md",
            "user-guide/preferences.md",
            "user-guide/troubleshooting.md",
        ],
    ),
    (
        "Developer Guide",
        [
            "developer-guide/architecture.md",
            "developer-guide/workspaces.md",
            "developer-guide/data-model.md",
            "developer-guide/modules.md",
            "developer-guide/processes.md",
            "developer-guide/tasks.md",
            "developer-guide/plugins.md",
            "developer-guide/io-handlers.md",
            "developer-guide/configuration.md",
            "developer-guide/contributing.md",
        ],
    ),
]

STYLE = """
body {
  max-width: 980px; margin: 0 auto; padding: 24px 34px 48px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  font-size: 16px; line-height: 1.58; color: #25313b; background: #ffffff;
}
h1, h2, h3, h4 { color: #123848; line-height: 1.25; margin-top: 1.4em; }
h1 { border-bottom: 2px solid #0788a3; padding-bottom: .3em; }
h2 { border-bottom: 1px solid #d7e0e4; padding-bottom: .2em; }
a { color: #067d99; }
code { font-family: "SFMono-Regular", Consolas, monospace; background: #eef3f5;
       border-radius: 4px; padding: .1em .3em; }
pre { background: #eef3f5; border: 1px solid #d8e1e5; border-radius: 7px;
      padding: 14px; overflow: auto; }
pre code { padding: 0; background: transparent; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #cbd6db; padding: 7px 10px; text-align: left; }
th { background: #edf5f7; }
blockquote { margin-left: 0; padding-left: 16px; border-left: 4px solid #0788a3;
             color: #52636d; }
img { max-width: 100%; height: auto; }
"""


def _title(markdown_text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", markdown_text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _fix_links(rendered: str) -> str:
    rendered = re.sub(
        r'href="([^"]+?)\.md(#[^"]*)?"',
        lambda m: f'href="{m.group(1)}.html{m.group(2) or ""}"',
        rendered,
    )
    rendered = rendered.replace(
        'href="../../examples/example_plugin/README.html"',
        'href="https://github.com/jhyan2018/AngstromPro/tree/main/examples/example_plugin"',
    )
    return rendered


def build() -> None:
    pages: list[dict[str, object]] = []
    wanted = ["README.md"] + [path for _, paths in NAVIGATION for path in paths]

    for relative in wanted:
        source = SOURCE / relative
        text = source.read_text(encoding="utf-8")
        title = _title(text, source.stem.replace("-", " ").title())
        body = markdown.markdown(
            text,
            extensions=["fenced_code", "tables", "sane_lists", "toc"],
            output_format="html5",
        )
        body = _fix_links(body)
        output_relative = Path(relative).with_suffix(".html")
        if output_relative.name == "README.html":
            output_relative = output_relative.with_name("index.html")
        destination = OUTPUT / output_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            "<!doctype html>\n"
            '<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(title)} - AngstromPro</title>"
            f"<style>{STYLE}</style></head><body>{body}</body></html>\n",
            encoding="utf-8",
        )

    for section, paths in NAVIGATION:
        entries = []
        for relative in paths:
            source = SOURCE / relative
            text = source.read_text(encoding="utf-8")
            entries.append(
                {
                    "title": _title(text, source.stem),
                    "path": str(Path(relative).with_suffix(".html")).replace("\\", "/"),
                }
            )
        pages.append({"title": section, "pages": entries})

    (OUTPUT / "navigation.json").write_text(
        json.dumps({"home": "index.html", "sections": pages}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    build()
    print(f"Built offline documentation in {OUTPUT}")
