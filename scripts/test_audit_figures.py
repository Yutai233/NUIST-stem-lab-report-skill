"""用小型 DOCX 验证辅助检查的判断与不判断边界。"""
import contextlib
import io
import shutil
import unittest
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

from audit_figures import audit, main


def picture(data=None, size=(900, 450), color="white"):
    if data is not None:
        return data
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


def paragraph(text, style=None):
    props = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{props}<w:r><w:t>{escape(text)}</w:t></w:r></w:p>'


def drawing(rid="r1", width=3, height=1.5, floating=False, crop=""):
    tag = "anchor" if floating else "inline"
    return (f'<w:p><w:r><w:drawing><wp:{tag}><wp:extent cx="{int(width * 914400)}" cy="{int(height * 914400)}"/>'
            f'<a:graphic><a:graphicData><a:blipFill><a:blip r:embed="{rid}"/>{crop}</a:blipFill></a:graphicData></a:graphic>'
            f'</wp:{tag}></w:drawing></w:r></w:p>')


class FigureAuditTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parent / ("_audit_test_" + uuid.uuid4().hex)
        self.root.mkdir()
        self.report = self.root / "中文报告.docx"

    def tearDown(self):
        shutil.rmtree(self.root)

    def docx(self, blocks, images=None, rels=None):
        images = images or {"one.png": picture()}
        rels = rels or {"r1": "one.png"}
        namespaces = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"')
        with zipfile.ZipFile(self.report, "w") as archive:
            archive.writestr("word/document.xml", f'<w:document {namespaces}><w:body>{"".join(blocks)}</w:body></w:document>')
            archive.writestr("word/_rels/document.xml.rels", '<Relationships>' + ''.join(f'<Relationship Id="{rid}" Target="media/{name}"/>' for rid, name in rels.items()) + '</Relationships>')
            archive.writestr("word/styles.xml", f'<w:styles {namespaces}><w:style w:styleId="MyCaption"><w:name w:val="Caption"/></w:style></w:styles>')
            for name, data in images.items():
                archive.writestr("word/media/" + name, data)
        return self.report

    def codes(self, result):
        return {item["code"] for item in result["issues"]}

    def test_normal_and_chinese_notes_with_fullwidth_colons(self):
        self.docx([paragraph("图1中可以看到测量结果。"), drawing(), paragraph("图1 测量结果")])
        notes = self.root / "图片证据笔记.md"
        notes.write_text("## IMG-001\n- 原始来源：原图.png\n- 采用状态：采用\n- 报告图号：图1\n", encoding="utf-8")
        result = audit(self.report, notes)
        self.assertEqual(result["summary"]["error"], 0)
        self.assertNotIn("notes_registration_missing", self.codes(result))
        self.assertIn("semantic_and_page_review", self.codes(result))

    def test_missing_figure8_and_duplicate_caption(self):
        self.docx([paragraph("见图8。"), drawing(), paragraph("图1 结果"), drawing(), paragraph("图1 对照")])
        result = audit(self.report)
        self.assertIn("missing_figure_reference", self.codes(result))
        self.assertIn("duplicate_caption", self.codes(result))
        self.assertTrue(any("图8" in item["message"] for item in result["issues"]))

    def test_explicit_external_figure_reference_is_unverified(self):
        for prefix in ("实验指导书", "实验指南中的", "教材中的第", "原文的", "参考文献中"):
            with self.subTest(prefix=prefix):
                self.docx([paragraph(prefix + "图8为理论参考曲线。")])
                result = audit(self.report)
                self.assertEqual(result["summary"]["error"], 0)
                self.assertIn("external_figure_reference", self.codes(result))
                self.assertNotIn("missing_figure_reference", self.codes(result))
        self.docx([paragraph("表3及图8支持该结论。")])
        result = audit(self.report)
        self.assertIn("missing_figure_reference", self.codes(result))
        self.assertNotIn("external_figure_reference", self.codes(result))
        self.docx([paragraph("实验指南图1～图3为理论示例。")])
        result = audit(self.report)
        self.assertEqual(result["summary"]["error"], 0)
        self.assertIn("external_figure_reference", self.codes(result))

    def test_offset_numbering_is_unverified_but_internal_gap_is_error(self):
        self.docx([drawing(), paragraph("图4 续号结果"), paragraph("见图4。")])
        result = audit(self.report)
        self.assertEqual(result["summary"]["error"], 0)
        self.assertIn("caption_start_offset", self.codes(result))
        self.assertNotIn("caption_gap", self.codes(result))
        self.docx([drawing(), paragraph("图4 结果"), drawing(), paragraph("图6 对照"), paragraph("见图4、图6。")])
        gaps = [item for item in audit(self.report)["issues"] if item["code"] == "caption_gap"]
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["level"], "error")
        self.assertIn("图5", gaps[0]["message"])
        self.assertNotIn("图1", gaps[0]["message"])

    def test_reused_resource_is_duplicate_but_unused_media_is_ignored(self):
        raw = picture()
        self.docx([drawing(), paragraph("图1 结果"), drawing(), paragraph("图2 对照"), paragraph("见图1、图2。")], {"one.png": raw, "unused.png": raw})
        duplicates = [item for item in audit(self.report)["issues"] if item["code"] == "duplicate_image_content"]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(len(duplicates[0]["location"]), 2)
        self.docx([drawing(), paragraph("图1 结果"), paragraph("见图1。")], {"one.png": raw, "unused.png": raw})
        self.assertNotIn("duplicate_image_content", self.codes(audit(self.report)))

    def test_same_bytes_in_two_resources_and_cropped_file(self):
        raw = picture()
        self.docx([drawing(), paragraph("图1 结果"), drawing("r2"), paragraph("图2 对照")], {"one.png": raw, "two.png": raw}, {"r1": "one.png", "r2": "two.png"})
        self.assertIn("duplicate_image_content", self.codes(audit(self.report)))
        with Image.open(io.BytesIO(raw)) as original:
            output = io.BytesIO()
            original.crop((0, 0, 450, 450)).save(output, format="PNG")
        self.docx([drawing(), paragraph("图1 结果"), drawing("r2"), paragraph("图2 对照")], {"one.png": raw, "two.png": output.getvalue()}, {"r1": "one.png", "r2": "two.png"})
        self.assertNotIn("duplicate_image_content", self.codes(audit(self.report)))

    def test_low_dpi_and_aspect_ratio(self):
        self.docx([drawing(width=6, height=6), paragraph("图1 结果")], {"one.png": picture(size=(300, 150))})
        codes = self.codes(audit(self.report))
        self.assertIn("low_dpi", codes)
        self.assertIn("aspect_ratio", codes)

    def test_missing_notes_registration_and_shared_subfigures(self):
        self.docx([drawing(), paragraph("图1 结果"), paragraph("见图1。")])
        notes = self.root / "notes.md"
        notes.write_text("## IMG-002\n- 原始来源: b.png\n- 采用状态: 不采用\n- 报告图号: 图1\n", encoding="utf-8")
        self.assertIn("notes_registration_missing", self.codes(audit(self.report, notes)))
        entry = "## IMG-{id}\n- 原始来源: {id}.png\n- 采用状态: 采用\n- 报告图号: 图1\n"
        notes.write_text(entry.format(id="001") + entry.format(id="002"), encoding="utf-8")
        result = audit(self.report, notes)
        self.assertEqual(result["summary"]["error"], 0)
        self.assertNotIn("notes_registration_missing", self.codes(result))

    def test_ranges_caption_style_and_leading_reference(self):
        blocks = [drawing(), paragraph("图1 结果", "MyCaption"), drawing(), paragraph("图2 对照", "MyCaption"), drawing(), paragraph("图3 验证", "MyCaption")]
        for refs in ("参见图1-图2和图3。", "参见图1～图3。", "参见图1、图2及图3。", "图1中已有说明，另见图2、图3。"):
            with self.subTest(refs=refs):
                self.docx(blocks + [paragraph(refs)])
                result = audit(self.report)
                self.assertEqual(result["summary"]["error"], 0)
                self.assertNotIn("unreferenced_figure", self.codes(result))
                self.assertNotIn("duplicate_caption", self.codes(result))

    def test_compound_caption_is_not_split_into_range(self):
        self.docx([drawing(), paragraph("图1-2 对照", "MyCaption"), paragraph("见图1-2。")])
        result = audit(self.report)
        self.assertEqual(result["summary"]["error"], 0)
        self.assertNotIn("unreferenced_figure", self.codes(result))
        self.assertIn("compound_number_sequence", self.codes(result))

    def test_missing_compound_number_is_not_inferred_as_range(self):
        self.docx([drawing(), paragraph("图1 结果"), drawing(), paragraph("图2 对照"), paragraph("参见图1-2。")])
        result = audit(self.report)
        self.assertIn("ambiguous_hyphen_reference", self.codes(result))
        unreferenced = [item for item in result["issues"] if item["code"] == "unreferenced_figure"]
        self.assertEqual(len(unreferenced), 2)
        self.assertNotIn("missing_figure_reference", self.codes(result))

    def test_empty_notes_source_does_not_consume_next_field(self):
        self.docx([drawing(), paragraph("图1 结果"), paragraph("参见图1。")])
        notes = self.root / "笔记.md"
        notes.write_text("## IMG-001\n- 原始来源 ： \n- 采用状态：采用\n- 报告图号：图1\n", encoding="utf-8")
        codes = self.codes(audit(self.report, notes))
        self.assertIn("notes_source_missing", codes)
        self.assertNotIn("notes_status", codes)
        self.assertNotIn("notes_registration_missing", codes)

    def test_ambiguous_plain_caption_is_not_a_false_missing_reference(self):
        self.docx([paragraph("图1 测量结果"), paragraph("参见图1。")])
        result = audit(self.report)
        self.assertEqual(result["summary"]["error"], 0)
        self.assertIn("ambiguous_caption", self.codes(result))
        self.assertIn("reference_caption_uncertain", self.codes(result))
        self.docx([drawing(), paragraph("图1 中可见测量结果。"), paragraph("图1 真实图题", "MyCaption")])
        self.assertNotIn("duplicate_caption", self.codes(audit(self.report)))

    def test_gap_unreferenced_and_unknown_syntax(self):
        self.docx([drawing(), paragraph("图1 结果"), drawing(), paragraph("图3 验证"), paragraph("参见图1、3及图3(a)。")])
        codes = self.codes(audit(self.report))
        self.assertIn("caption_gap", codes)
        self.assertIn("abbreviated_reference", codes)
        self.assertIn("subfigure_reference", codes)
        self.docx([drawing(), paragraph("图1 结果")])
        self.assertIn("unreferenced_figure", self.codes(audit(self.report)))

    def test_floating_and_vector_images_are_unverified(self):
        self.docx([drawing(floating=True), paragraph("图1 结果")])
        self.assertIn("floating_image", self.codes(audit(self.report)))
        self.docx([drawing(), paragraph("图1 结果")], {"one.png": b"not a supported image"})
        self.assertIn("unsupported_image", self.codes(audit(self.report)))

    def test_cli_exit_codes_and_never_overwrites_inputs(self):
        self.docx([drawing(), paragraph("图1 结果"), paragraph("见图1。")])
        before = self.report.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.report), "--out", str(self.root / "结果.json")]), 0)
            self.assertEqual(main([str(self.report), "--out", str(self.report)]), 2)
            self.assertEqual(self.report.read_bytes(), before)
            self.assertEqual(main([str(self.root / "不存在.docx")]), 2)
            self.docx([paragraph("见图8。")])
            self.assertEqual(main([str(self.report)]), 1)
        self.assertTrue((self.root / "结果.json").is_file())
        self.assertTrue(before.startswith(b"PK"))


if __name__ == "__main__":
    unittest.main()
