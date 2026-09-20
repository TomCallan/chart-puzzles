"""Jinja2 rendering and WeasyPrint PDF generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import PROJECT_ROOT
from .layout import content_height_in

TEMPLATES_DIR = PROJECT_ROOT / "templates"


def build_environment(templates_dir: str | Path | None = None) -> Environment:
    directory = Path(templates_dir) if templates_dir else TEMPLATES_DIR
    return Environment(
        loader=FileSystemLoader(str(directory)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_css_override(cfg: Mapping[str, Any]) -> str:
    """Emit config-driven print rules injected after styles.css."""
    book = cfg["book"]
    margins = book["margins"]
    trim = book["trim"]
    dots = book["dot_grid"]
    width = float(trim["width"])
    height = float(trim["height"])
    inside = float(margins["inside"])
    outside = float(margins["outside"])
    top = float(margins["top"])
    bottom = float(margins["bottom"])
    content_h = content_height_in(cfg)
    return f"""
@page {{
  size: {width}in {height}in;
  margin: {top}in {outside}in {bottom}in {inside}in;
}}
@page :right {{
  margin-left: {inside}in;
  margin-right: {outside}in;
}}
@page :left {{
  margin-left: {outside}in;
  margin-right: {inside}in;
}}
.page--workspace .dot-grid {{
  background-image: radial-gradient(
    circle,
    {dots['color']} {dots['radius']}px,
    transparent {dots['radius']}px
  );
  background-size: {dots['spacing']}in {dots['spacing']}in;
  height: {content_h}in;
}}
.page--workspace {{ height: {content_h}in; }}
""".strip()


def render_book_html(
    pages: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    templates_dir: str | Path | None = None,
    standalone: bool = False,
) -> str:
    env = build_environment(templates_dir)
    template = env.get_template("book_template.html")
    directory = Path(templates_dir) if templates_dir else TEMPLATES_DIR
    styles_path = directory / "styles.css"
    styles_css = styles_path.read_text(encoding="utf-8") if styles_path.exists() else ""
    return template.render(
        pages=pages,
        cfg=cfg,
        styles_css=styles_css,
        css_override=render_css_override(cfg),
        standalone=standalone,
    )


def html_to_pdf(html: str, out_path: str | Path, base_url: str | Path | None = None) -> Path:
    from weasyprint import HTML  # lazy: heavy import

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(base_url or PROJECT_ROOT)).write_pdf(str(out_path))
    return out_path
