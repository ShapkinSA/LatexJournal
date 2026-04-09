from __future__ import annotations

import re
import subprocess
import unicodedata
from pathlib import Path
from typing import List, Tuple


class LatexJournalBuilder:
    def __init__(self, template_path: str | Path = "template/template.tex") -> None:
        self.article_name: str = "Без названия"
        self.issue_info: str = "Выпуск без даты"
        self.blocks: List[Tuple[str, str]] = []
        self.document_class: str = "article"
        self.document_options: List[str] = ["10pt", "a4paper", "twocolumn"]
        self.package_lines: List[str] = [
            "\\usepackage[T2A]{fontenc}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[russian]{babel}",
            "\\usepackage{graphicx}",
        ]
        self.lengths: dict[str, str] = {
            "topmargin": "-2.8cm",
            "oddsidemargin": "-0.8cm",
            "evensidemargin": "-0.8cm",
            "textwidth": "26.7cm",
            "textheight": "18.4cm",
            "columnsep": "0.9cm",
            "parindent": "1.25em",
            "parskip": "0.15em",
            "intextsep": "0.3em",
            "textfloatsep": "0.3em",
            "floatsep": "0.3em",
        }
        self.page_style: str = "plain"
        self.background_image_path: str | None = None
        self.page_margins: dict[str, str] | None = None
        self.fonts = {
            "body": {"size": self._format_font_size(10), "family": "\\rmfamily"},
            "article_title": {"size": self._format_font_size(16), "family": "\\rmfamily"},
            "issue_info": {"size": self._format_font_size(9), "family": "\\rmfamily"},
            "section_title": {"size": self._format_font_size(12), "family": "\\rmfamily"},
            "caption": {"size": self._format_font_size(9), "family": "\\rmfamily"},
            "page_number": {"size": self._format_font_size(10), "family": "\\rmfamily"},
        }
        self._load_globals_from_template(template_path)

    @staticmethod
    def _strip_comment(line: str) -> str:
        if "%" not in line:
            return line
        return line.split("%", 1)[0]

    def _load_globals_from_template(self, template_path: str | Path) -> None:
        template = Path(template_path)
        if not template.exists():
            return

        content = template.read_text(encoding="utf-8", errors="ignore")
        preamble = content.split("\\begin{document}", 1)[0]
        lines = preamble.splitlines()

        length_map: dict[str, str] = {}
        package_lines: List[str] = []

        for raw_line in lines:
            line = self._strip_comment(raw_line).strip()
            if not line:
                continue

            doc_match = re.match(
                r"\\documentclass(?:\[(?P<opts>[^\]]*)\])?\{(?P<cls>[^}]*)\}",
                line,
            )
            if doc_match:
                self.document_class = doc_match.group("cls").strip() or "article"
                opts = (doc_match.group("opts") or "").strip()
                self.document_options = (
                    [opt.strip() for opt in opts.split(",") if opt.strip()] if opts else []
                )
                continue

            if line.startswith("\\usepackage"):
                package_lines.append(line)
                continue

            len_match = re.match(r"\\setlength\{\\(?P<name>[^}]*)\}\{(?P<value>[^}]*)\}", line)
            if len_match:
                length_map[len_match.group("name").strip()] = len_match.group("value").strip()
                continue

            page_match = re.match(r"\\pagestyle\{(?P<style>[^}]*)\}", line)
            if page_match:
                self.page_style = page_match.group("style").strip()

        if package_lines:
            self.package_lines = package_lines
        if length_map:
            self.lengths.update(length_map)
        if "\\usepackage{float}" not in self.package_lines:
            self.package_lines.append("\\usepackage{float}")
        if "\\usepackage{multicol}" not in self.package_lines:
            self.package_lines.append("\\usepackage{multicol}")

    @staticmethod
    def _format_font_size(size: int | float) -> str:
        numeric_size = float(size)
        if numeric_size <= 0:
            raise ValueError("Font size must be greater than 0.")
        line_height = round(numeric_size * 1.2, 1)
        return f"\\fontsize{{{numeric_size:g}pt}}{{{line_height:g}pt}}\\selectfont"

    @staticmethod
    def _validate_font_family(family: str) -> str:
        families = {
            "roman": "\\rmfamily",
            "sans": "\\sffamily",
            "mono": "\\ttfamily",
        }
        if family not in families:
            raise ValueError("Unsupported family. Use: roman, sans, mono")
        return families[family]

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """
        Remove control/format Unicode chars that can break LaTeX compilation.
        Keep common whitespace controls: newline and tab.
        """
        cleaned: List[str] = []
        for ch in text:
            category = unicodedata.category(ch)
            if category[0] == "C" and ch not in ("\n", "\t"):
                continue
            cleaned.append(ch)
        return "".join(cleaned)

    @staticmethod
    def _is_wide_image(width: str) -> bool:
        width = width.strip()
        if not width:
            return False
        if "\\textwidth" in width or "\\paperwidth" in width:
            return True
        match = re.match(r"^\s*([0-9]*\.?[0-9]+)\s*\\columnwidth\s*$", width)
        if not match:
            return False
        return float(match.group(1)) > 1.0

    @staticmethod
    def _map_width_for_wide_block(width: str) -> str:
        """
        For wide (two-column) rendering, interpret N\\columnwidth as
        N * width_of_one_column, even outside multicols.
        """
        width = width.strip()
        match = re.match(r"^\s*([0-9]*\.?[0-9]+)\s*\\columnwidth\s*$", width)
        if match:
            factor = match.group(1)
            return f"{factor}\\JournalOneColWidth"
        return width

    @staticmethod
    def _validate_non_negative_dimension(value: str, name: str) -> str:
        """
        Accept LaTeX dimensions like '0', '1.5cm', '12pt', '3 mm'.
        Negative values are forbidden.
        """
        cleaned = value.strip().replace(" ", "")
        match = re.match(r"^(?P<num>[+-]?[0-9]*\.?[0-9]+)(?P<unit>cm|mm|in|pt|em|ex)?$", cleaned)
        if not match:
            raise ValueError(
                f"Invalid {name} value '{value}'. Use non-negative size like '0', '1.5cm', '12pt'."
            )
        number = float(match.group("num"))
        if number < 0:
            raise ValueError(f"{name} cannot be negative: {value}")
        # Bare numeric values are interpreted as centimeters.
        unit = match.group("unit") or "cm"
        return f"{number:g}{unit}"

    @staticmethod
    def _escape_latex(text: str) -> str:
        text = LatexJournalBuilder._sanitize_text(text)
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        escaped = text
        for original, replacement in replacements.items():
            escaped = escaped.replace(original, replacement)
        return escaped

    def set_article_name(self, article_name: str) -> "LatexJournalBuilder":
        self.article_name = self._escape_latex(article_name)
        return self

    def set_issue_info(self, issue_info: str) -> "LatexJournalBuilder":
        self.issue_info = self._escape_latex(issue_info)
        return self

    def set_document_options(self, options: List[str]) -> "LatexJournalBuilder":
        self.document_options = [opt.strip() for opt in options if opt.strip()]
        return self

    def set_landscape(self, enabled: bool) -> "LatexJournalBuilder":
        options = [opt for opt in self.document_options if opt != "landscape"]
        if enabled:
            options.append("landscape")
        self.document_options = options
        return self

    def set_page_style(self, style: str) -> "LatexJournalBuilder":
        self.page_style = style.strip()
        return self

    def set_length(self, name: str, value: str) -> "LatexJournalBuilder":
        self.lengths[name.strip().lstrip("\\")] = value.strip()
        return self

    def set_page_margins(
        self, top: str, right: str, bottom: str, left: str
    ) -> "LatexJournalBuilder":
        """
        Set page margins explicitly.
        Values should be LaTeX dimensions, e.g. '2cm', '15mm'.
        """
        top_v = self._validate_non_negative_dimension(top, "top")
        right_v = self._validate_non_negative_dimension(right, "right")
        bottom_v = self._validate_non_negative_dimension(bottom, "bottom")
        left_v = self._validate_non_negative_dimension(left, "left")

        # Keep explicit per-side values; applied via geometry package in _compose_tex.
        self.page_margins = {
            "top": top_v,
            "right": right_v,
            "bottom": bottom_v,
            "left": left_v,
        }
        return self

    def set_column_gap(self, value: str) -> "LatexJournalBuilder":
        self.lengths["columnsep"] = value.strip()
        return self

    def set_background_image(self, path_to_image: str) -> "LatexJournalBuilder":
        image_path = Path(path_to_image).resolve()
        if image_path.exists():
            self.background_image_path = str(image_path).replace("\\", "/")
        else:
            self.background_image_path = None
            print(f"Background image not found, skipping: {image_path}")
        return self

    def set_body_font(self, size: int | float, family: str) -> "LatexJournalBuilder":
        self.fonts["body"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }
        return self

    def set_article_title_font(self, size: int | float, family: str) -> "LatexJournalBuilder":
        self.fonts["article_title"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }
        return self

    def set_issue_info_font(self, size: int | float, family: str) -> "LatexJournalBuilder":
        self.fonts["issue_info"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }
        return self

    def set_section_title_font(self, size: int | float, family: str) -> "LatexJournalBuilder":
        self.fonts["section_title"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }
        return self

    def set_caption_font(self, size: int | float, family: str) -> "LatexJournalBuilder":
        self.fonts["caption"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }
        return self

    def set_page_number_font(
        self, size: int | float, family: str
    ) -> "LatexJournalBuilder":
        self.fonts["page_number"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }
        return self

    def add_section(self, section_name: str) -> "LatexJournalBuilder":
        escaped = self._escape_latex(section_name)
        self.blocks.append(
            (
                "normal",
                "\\par\\vspace{0.25cm}\n"
                f"{{\\SectionTitleFont\\bfseries {escaped}}}\n"
                "\\par\\vspace{0.1cm}",
            )
        )
        return self

    def add_paragraph(self, text: str) -> "LatexJournalBuilder":
        escaped = self._escape_latex(text).strip()
        # Always enforce first-line indentation, including after image blocks.
        self.blocks.append(
            ("normal", f"\\par{{\\BodyTextFont\\hspace*{{\\parindent}}{escaped}}}\\par")
        )
        return self

    def add_picture(
        self,
        path_to_picture: str,
        caption: str = "",
        width: str = "0.80\\columnwidth",
        height: str = "",
        span_wide_as_float: bool = False,
    ) -> "LatexJournalBuilder":
        picture_path = Path(path_to_picture).resolve()
        if not picture_path.exists():
            raise FileNotFoundError(f"Image not found: {picture_path}")

        latex_path = str(picture_path).replace("\\", "/")
        escaped_caption = self._escape_latex(caption).strip()
        caption_block = ""
        if escaped_caption:
            caption_block = (
                f"{{\\CaptionFont {escaped_caption}}}\n"
            )
        width = width.strip()
        height = height.strip()
        is_wide = self._is_wide_image(width)
        width_for_use = self._map_width_for_wide_block(width) if is_wide else width

        include_opts = []
        if width_for_use:
            include_opts.append(f"width={width_for_use}")
        if height:
            include_opts.append(f"height={height}")
        if width_for_use and height:
            include_opts.append("keepaspectratio")
        opts = f"[{','.join(include_opts)}]" if include_opts else ""
        if is_wide and span_wide_as_float:
            self.blocks.append(
                (
                    "normal",
                    "\\begin{figure*}[t]\n"
                    "\\centering\n"
                    "\\begin{minipage}{\\textwidth}\n"
                    "\\centering\n"
                    f"\\includegraphics{opts}{{{latex_path}}}\n"
                    f"{caption_block}"
                    "\\end{minipage}\n"
                    "\\end{figure*}",
                )
            )
        elif is_wide:
            wide_block = (
                "\\begin{samepage}\n"
                "\\noindent\\makebox[\\textwidth][c]{%\n"
                f"\\begin{{minipage}}{{{width_for_use}}}\n"
                "\\centering\n"
                f"\\includegraphics{opts}{{{latex_path}}}\n"
                f"{caption_block}"
                "\\end{minipage}\n"
                "}\n"
                "\\end{samepage}"
            )
            self.blocks.append(("wide", wide_block))
        else:
            normal_block = (
                "\\begin{samepage}\n"
                "\\noindent\\makebox[\\linewidth][c]{%\n"
                f"\\begin{{minipage}}{{{width_for_use}}}\n"
                "\\centering\n"
                f"\\includegraphics{opts}{{{latex_path}}}\n"
                f"{caption_block}"
                "\\end{minipage}\n"
                "}\n"
                "\\end{samepage}"
            )
            self.blocks.append(("normal", normal_block))
        return self

    def _compose_tex(self) -> str:
        options_list = [opt for opt in self.document_options if opt != "twocolumn"]
        options = f"[{','.join(options_list)}]" if options_list else ""
        package_lines = list(self.package_lines)
        if self.page_margins and "\\usepackage{geometry}" not in package_lines:
            package_lines.append("\\usepackage{geometry}")
        packages = "\n".join(package_lines)

        excluded_for_geometry = {"topmargin", "oddsidemargin", "evensidemargin", "textwidth", "textheight"}
        lengths_lines = []
        for name, value in self.lengths.items():
            if self.page_margins and name in excluded_for_geometry:
                continue
            lengths_lines.append(f"\\setlength{{\\{name}}}{{{value}}}")
        lengths = "\n".join(lengths_lines)

        geometry_setup = ""
        if self.page_margins:
            geometry_setup = (
                "\\geometry{"
                f"top={self.page_margins['top']},"
                f"right={self.page_margins['right']},"
                f"bottom={self.page_margins['bottom']},"
                f"left={self.page_margins['left']},"
                "ignoreheadfoot,"
                "nomarginpar"
                "}\n"
            )
        body_parts: List[str] = []
        in_multicols = False
        for block_type, content in self.blocks:
            if block_type == "wide":
                if in_multicols:
                    body_parts.append("\\end{multicols}")
                    in_multicols = False
                body_parts.append(content)
            else:
                if not in_multicols:
                    body_parts.append("\\begin{multicols}{2}")
                    in_multicols = True
                body_parts.append(content)
        if in_multicols:
            body_parts.append("\\end{multicols}")
        body = "\n".join(body_parts)
        body = body.replace("\\begin{multicols}{2}\n\\end{multicols}\n", "")
        body = body.replace("\\begin{multicols}{2}\n\\end{multicols}", "")
        if body.startswith("\\par\n"):
            body = body[len("\\par\n") :]
        elif body.startswith("\\par"):
            body = body[len("\\par") :]
        background_setup = ""
        background_apply = ""
        if self.background_image_path:
            background_setup = (
                "\\usepackage{eso-pic}\n"
                "\\newcommand{\\JournalBackground}{%\n"
                "  \\put(0,0){\\parbox[b][\\paperheight]{\\paperwidth}{%\n"
                "    \\vfill\\centering\n"
                f"    \\includegraphics[width=\\paperwidth,height=\\paperheight]{{{self.background_image_path}}}%\n"
                "    \\vfill\n"
                "  }}\n"
                "}\n"
            )
            background_apply = "\\AddToShipoutPictureBG{\\JournalBackground}\n"
        return (
            f"\\documentclass{options}{{{self.document_class}}}\n\n"
            f"{packages}\n\n"
            f"{background_setup}"
            f"{geometry_setup}"
            f"{lengths}\n"
            f"\\pagestyle{{{self.page_style}}}\n\n"
            f"\\newcommand{{\\BodyTextFont}}{{{self.fonts['body']['size']} {self.fonts['body']['family']}}}\n"
            f"\\newcommand{{\\ArticleTitleFont}}{{{self.fonts['article_title']['size']} {self.fonts['article_title']['family']}}}\n"
            f"\\newcommand{{\\IssueInfoFont}}{{{self.fonts['issue_info']['size']} {self.fonts['issue_info']['family']}}}\n"
            f"\\newcommand{{\\SectionTitleFont}}{{{self.fonts['section_title']['size']} {self.fonts['section_title']['family']}}}\n"
            f"\\newcommand{{\\CaptionFont}}{{{self.fonts['caption']['size']} {self.fonts['caption']['family']}}}\n\n"
            f"\\newcommand{{\\PageNumberFont}}{{{self.fonts['page_number']['size']} {self.fonts['page_number']['family']}}}\n\n"
            "\\makeatletter\n"
            "\\def\\ps@plain{%\n"
            "  \\let\\@mkboth\\@gobbletwo\n"
            "  \\let\\@oddhead\\@empty\n"
            "  \\let\\@evenhead\\@empty\n"
            "  \\def\\@oddfoot{\\hfil{\\PageNumberFont\\thepage}\\hfil}\n"
            "  \\let\\@evenfoot\\@oddfoot\n"
            "}\n"
            "\\makeatother\n\n"
            "\\newlength{\\JournalOneColWidth}\n"
            "\\setlength{\\JournalOneColWidth}{\\dimexpr(\\textwidth-\\columnsep)/2\\relax}\n\n"
            "\\begin{document}\n\n"
            f"{background_apply}"
            f"\\noindent{{\\IssueInfoFont\\textit{{{self.issue_info}}}}}\n\n"
            "\\vspace{\\baselineskip}\n"
            "{\\centering\n"
            f"{{\\ArticleTitleFont\\bfseries {self.article_name}}}\\par\n"
            "}\n"
            f"{body}\n"
            "\\end{document}\n"
        )

    def build_pdf(self, output_pdf_path: str, work_dir: str = "build") -> Path:
        output_pdf = Path(output_pdf_path).resolve()
        work_path = Path(work_dir).resolve()
        work_path.mkdir(parents=True, exist_ok=True)

        tex_path = work_path / "generated_article.tex"
        tex_path.write_text(self._compose_tex(), encoding="utf-8")

        command = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={work_path}",
            str(tex_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "pdflatex failed.\n"
                f"stdout:\n{result.stdout}\n\n"
                f"stderr:\n{result.stderr}"
            )

        generated_pdf = work_path / "generated_article.pdf"
        if not generated_pdf.exists():
            raise FileNotFoundError("PDF was not generated by pdflatex.")

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        output_pdf.write_bytes(generated_pdf.read_bytes())
        return output_pdf
