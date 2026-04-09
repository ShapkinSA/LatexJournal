from __future__ import annotations

from pathlib import Path
from model.latex_journal_builder import LatexJournalBuilder


_builder = LatexJournalBuilder()

if __name__ == "__main__":
    # Установка шрифтов
    _builder.set_body_font(10, "roman")
    _builder.set_article_title_font(16, "roman")
    _builder.set_issue_info_font(9, "roman")
    _builder.set_section_title_font(12, "roman")
    _builder.set_caption_font(9, "roman")



    #Заполнение текстом
    _builder.set_issue_info("Выпуск из программного генератора от 09.04.2026")
    _builder.set_article_name("Из старых записей")
    _builder.add_section("Предисловие")
    _builder.add_paragraph(
        "Этот текст формируется из Python-функций и собирается в единый PDF."
    )
    _builder.add_section("Итог")
    _builder.add_paragraph(
        "Добавляйте разделы, абзацы и изображения в нужном порядке."
    )

    # Example:
    # addPicture("template/sample.jpg", "Подпись к изображению")

    pdf_path = _builder.build_pdf("output/final_article.pdf")
    print(f"PDF generated: {pdf_path}")

