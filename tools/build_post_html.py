"""Render a Jekyll post in _posts/ to the static HTML the public site serves.

Jekyll is not installed locally (system Ruby is 2.6), so this reproduces the
post layout by reusing an already-published page as the shell template. That
means <public_root> must already contain TEMPLATE below.

Requires the `markdown` package (pip install markdown).

Usage:
    python tools/build_post_html.py _posts/2025-12-05-polaris.md <public_root>
"""

import argparse
import pathlib
import re
import sys

import markdown

TEMPLATE = "2024/12/08/robot-arm-advml/index.html"
SITE_URL = "https://kausarpatherya.com"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# KaTeX runs in the browser, so math must survive the Markdown pass untouched.
MATH_PATTERNS = (re.compile(r"\$\$.+?\$\$", re.DOTALL), re.compile(r"(?<!\$)\$[^$\n]+?\$"))


def parse_front_matter(text):
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise SystemExit("post is missing YAML front matter")

    meta = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta, match.group(2)


def protect_math(text):
    spans = []

    def stash(match):
        spans.append(match.group(0))
        return f"\x00MATH{len(spans) - 1}\x00"

    for pattern in MATH_PATTERNS:
        text = pattern.sub(stash, text)
    return text, spans


def restore_math(html, spans):
    return re.sub(r"\x00MATH(\d+)\x00", lambda m: spans[int(m.group(1))], html)


def wrap_tables(html):
    """Wide tables need their own scroll container; the post column is only 800px."""
    return re.sub(
        r"<table>.*?</table>",
        lambda m: f'<div class="table-scroll">{m.group(0)}</div>',
        html,
        flags=re.DOTALL,
    )


def render_body(body):
    body, spans = protect_math(body)
    html = markdown.markdown(
        body,
        extensions=["tables", "attr_list", "md_in_html", "sane_lists", "smarty"],
        output_format="html5",
    )
    return wrap_tables(restore_math(html, spans))


def build(post_path, public_root):
    meta, body = parse_front_matter(post_path.read_text(encoding="utf-8"))

    year, month, day, slug = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.+)\.md$", post_path.name).groups()
    permalink = f"/{year}/{month}/{day}/{slug}/"
    pretty_date = f"{MONTHS[int(month) - 1]} {int(day)}, {year}"

    template = (public_root / TEMPLATE).read_text(encoding="utf-8")
    head, _, rest = template.partition("<title>")
    _, _, rest = rest.partition("</title>")
    shell_top = f"{head}<title>{meta['title']}</title>{rest}"

    shell_top = re.sub(
        r'<link rel="canonical" href="[^"]*">',
        f'<link rel="canonical" href="{SITE_URL}{permalink}">',
        shell_top,
    )

    prefix, _, remainder = shell_top.partition("<header class=\"post-header\">")
    _, _, suffix = remainder.partition("</article>")

    page = (
        f"{prefix}<header class=\"post-header\">\n"
        f"    <h1>{meta['title']}</h1>\n"
        f"    <p class=\"meta\">{pretty_date}</p>\n"
        f"  </header>\n\n"
        f"  <article class=\"post-content\">\n"
        f"  {render_body(body)}\n"
        f"</article>{suffix}"
    )

    out_dir = public_root / year / month / day / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    out_path.write_text(page, encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("post", type=pathlib.Path)
    parser.add_argument("public_root", type=pathlib.Path)
    args = parser.parse_args()

    out_path = build(args.post, args.public_root)
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
