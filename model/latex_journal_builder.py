from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


class LatexJournalBuilder:
    def __init__(self) -> None:
        self.article_name: str = "Без названия"
        self.issue_info: str = "Выпуск без даты"
        self.blocks: List[str] = []
        self.fonts = {
            "body": {"size": self._format_font_size(10), "family": "\\rmfamily"},
            "article_title": {"size": self._format_font_size(16), "family": "\\rmfamily"},
            "issue_info": {"size": self._format_font_size(9), "family": "\\rmfamily"},
            "section_title": {"size": self._format_font_size(12), "family": "\\rmfamily"},
            "caption": {"size": self._format_font_size(9), "family": "\\rmfamily"},
        }

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
    def _escape_latex(text: str) -> str:
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

    def set_article_name(self, article_name: str) -> None:
        self.article_name = self._escape_latex(article_name)

    def set_issue_info(self, issue_info: str) -> None:
        self.issue_info = self._escape_latex(issue_info)

    def set_body_font(self, size: int | float, family: str) -> None:
        self.fonts["body"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }

    def set_article_title_font(self, size: int | float, family: str) -> None:
        self.fonts["article_title"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }

    def set_issue_info_font(self, size: int | float, family: str) -> None:
        self.fonts["issue_info"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }

    def set_section_title_font(self, size: int | float, family: str) -> None:
        self.fonts["section_title"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }

    def set_caption_font(self, size: int | float, family: str) -> None:
        self.fonts["caption"] = {
            "size": self._format_font_size(size),
            "family": self._validate_font_family(family),
        }

    def add_section(self, section_name: str) -> None:
        escaped = self._escape_latex(section_name)
        self.blocks.append(
            "\\par\\vspace{0.25cm}\n"
            f"{{\\SectionTitleFont\\bfseries {escaped}}}\n"
            "\\par\\vspace{0.1cm}"
        )

    def add_paragraph(self, text: str) -> None:
        self.blocks.append(f"{{\\BodyTextFont {self._escape_latex(text)}}}")

    def add_picture(self, path_to_picture: str, caption: str = "") -> None:
        picture_path = Path(path_to_picture).resolve()
        if not picture_path.exists():
            raise FileNotFoundError(f"Image not found: {picture_path}")

        latex_path = str(picture_path).replace("\\", "/")
        escaped_caption = self._escape_latex(caption) if caption else "Иллюстрация"

        self.blocks.append(
            "\\begin{figure}[h]\n"
            "\\centering\n"
            f"\\includegraphics[width=0.80\\columnwidth]{{{latex_path}}}\n"
            f"\\caption{{{{\\CaptionFont {escaped_caption}}}}}\n"
            "\\end{figure}"
        )

    def _compose_tex(self) -> str:
        body = "\n\n".join(self.blocks)
        return (
            "\\documentclass[10pt,a4paper,landscape,twocolumn]{article}\n\n"
            "\\usepackage[T2A]{fontenc}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[russian]{babel}\n"
            "\\usepackage{graphicx}\n\n"
            "\\setlength{\\topmargin}{-2.8cm}\n"
            "\\setlength{\\oddsidemargin}{-0.8cm}\n"
            "\\setlength{\\evensidemargin}{-0.8cm}\n"
            "\\setlength{\\textwidth}{26.7cm}\n"
            "\\setlength{\\textheight}{18.4cm}\n"
            "\\setlength{\\columnsep}{0.9cm}\n"
            "\\setlength{\\parindent}{1.25em}\n"
            "\\setlength{\\parskip}{0.15em}\n"
            "\\pagestyle{plain}\n\n"
            f"\\newcommand{{\\BodyTextFont}}{{{self.fonts['body']['size']} {self.fonts['body']['family']}}}\n"
            f"\\newcommand{{\\ArticleTitleFont}}{{{self.fonts['article_title']['size']} {self.fonts['article_title']['family']}}}\n"
            f"\\newcommand{{\\IssueInfoFont}}{{{self.fonts['issue_info']['size']} {self.fonts['issue_info']['family']}}}\n"
            f"\\newcommand{{\\SectionTitleFont}}{{{self.fonts['section_title']['size']} {self.fonts['section_title']['family']}}}\n"
            f"\\newcommand{{\\CaptionFont}}{{{self.fonts['caption']['size']} {self.fonts['caption']['family']}}}\n\n"
            "\\begin{document}\n\n"
            f"\\noindent{{\\IssueInfoFont\\textit{{{self.issue_info}}}}}\n\n"
            "\\vspace{0.4cm}\n\n"
            "\\begin{center}\n"
            f"    {{\\ArticleTitleFont\\bfseries {self.article_name}}}\n"
            "\\end{center}\n\n"
            "\\vspace{0.3cm}\n\n"
            f"{body}\n\n"
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
