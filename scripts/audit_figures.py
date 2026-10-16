"""只读检查 DOCX 图片结构；不代替原图核对和最终页面验收。"""
import argparse
import hashlib
import io
import json
import posixpath
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, UnidentifiedImageError

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}
FIG = re.compile(r"图\s*(\d+(?:[-－.]\d+)?)")
CAPTION = re.compile(r"^图\s*(\d+(?:[-－.]\d+)?)(?:\s+|[：:、])\S")
RANGE = re.compile(r"^\s*([~～至—–-])\s*(?:图\s*)?(\d+)")
EXTERNAL_SOURCE = re.compile(r"(?:指导书|实验指南|教材|原文|参考文献)(?:中的|中|的)?[ \t]*(?:第[ \t]*)?$")


def number(value):
    return re.sub(r"[－.]", "-", value)


def issue(items, level, code, message, location):
    items.append(dict(level=level, code=code, message=message, location=location))


def caption_styles(archive):
    if "word/styles.xml" not in archive.namelist():
        return {"Caption"}
    root = ET.fromstring(archive.read("word/styles.xml"))
    result = {"Caption"}
    for style in root.findall("w:style", NS):
        name = style.find("w:name", NS)
        if name is not None and name.get(f"{{{NS['w']}}}val", "").lower() in {"caption", "题注", "图题"}:
            result.add(style.get(f"{{{NS['w']}}}styleId"))
    return result


def read_notes(path, captions, items):
    content = Path(path).read_text(encoding="utf-8-sig")
    entries = re.split(r"(?m)^##\s+(IMG-\d+)\s*$", content)
    registered = set()
    if len(entries) == 1:
        issue(items, "unverified", "notes_format", "未识别到 ## IMG-001 形式的图片记录。", str(path))
    for index in range(1, len(entries), 2):
        identity, body = entries[index:index + 2]
        fields = {key.strip(): value.strip() for key, value in re.findall(r"(?m)^[ \t]*-[ \t]*([^：:\r\n]+)[：:][ \t]*([^\r\n]*)$", body)}
        status = fields.get("采用状态", "").strip()
        labels = {number(m.group(1)) for m in FIG.finditer(fields.get("报告图号", ""))}
        if status in {"采用", "参考"} and labels:
            registered.update(labels)
            if not fields.get("原始来源", "").strip():
                issue(items, "warning", "notes_source_missing", "采用图片未登记原始来源。", identity)
            for label in labels - set(captions):
                issue(items, "warning", "notes_figure_missing", f"笔记中的图{label}未匹配报告图题。", identity)
        elif status == "采用":
            issue(items, "warning", "notes_number_missing", "采用图片未登记报告图号。", identity)
        elif status not in {"参考", "不采用", "待确认"}:
            issue(items, "unverified", "notes_status", "采用状态缺失或不在支持范围内。", identity)
    for label in set(captions) - registered:
        issue(items, "warning", "notes_registration_missing", f"图{label}缺少采用图片的来源记录。", f"图{label}")


def audit(path, notes=None, min_dpi=150):
    items, drawings = [], []
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
        if root.find("w:body", NS) is None:
            raise ValueError("不支持该文档正文结构或XML命名空间")
        rels = ET.fromstring(archive.read("word/_rels/document.xml.rels")) if "word/_rels/document.xml.rels" in archive.namelist() else []
        targets = {rel.get("Id"): posixpath.normpath(posixpath.join("word", rel.get("Target", ""))) for rel in rels if rel.get("TargetMode") != "External"}
        styles = caption_styles(archive)
        paragraphs = []
        if root.find(".//w:txbxContent", NS) is not None:
            issue(items, "unverified", "textbox_content", "文本框中的图片、图题和引用未单独验证，需检查渲染页面。", "正文文本框")
        textbox_paragraphs = {p for box in root.findall(".//w:txbxContent", NS) for p in box.findall(".//w:p", NS)}
        for p in root.findall(".//w:body//w:p", NS):
            if p in textbox_paragraphs:
                continue
            text = "".join(t.text or "" for t in p.findall(".//w:t", NS))
            style = p.find("w:pPr/w:pStyle", NS)
            paragraphs.append(dict(text=text.strip(), style=style.get(f"{{{NS['w']}}}val") if style is not None else None, xml=p, images=[]))
        for index, p in enumerate(paragraphs):
            for drawing in p["xml"].findall(".//w:drawing", NS):
                if drawing.find(".//w:txbxContent", NS) is not None:
                    continue
                for blip in drawing.findall(".//a:blip", NS):
                    extent = drawing.find(".//wp:extent", NS)
                    record = dict(paragraph=index, target=targets.get(blip.get(f"{{{NS['r']}}}embed")), floating=drawing.find("wp:anchor", NS) is not None, extent=extent, xml=drawing)
                    drawings.append(record)
                    p["images"].append(record)
            if p["xml"].find(".//w:pict", NS) is not None:
                issue(items, "unverified", "legacy_drawing", "VML/旧式图片的尺寸和关联未验证。", f"段落{index + 1}")
        captions, ambiguous = defaultdict(list), set()
        for index, p in enumerate(paragraphs):
            match = FIG.match(p["text"])
            nearby = p["images"] or (index > 0 and paragraphs[index - 1]["images"])
            narrative = match and re.match(r"\s*(?:中|所示|可见|显示|可以|表明|的|给出|说明)", p["text"][match.end():])
            if match and (p["style"] in styles or (CAPTION.match(p["text"]) and nearby and not narrative and "。" not in p["text"])):
                p["caption"] = number(match.group(1))
                captions[p["caption"]].append(index)
                if not nearby:
                    issue(items, "warning", "caption_image_association", "图题附近未找到正文嵌入图片，需复核实际关联。", f"段落{index + 1}")
            elif match and not narrative and "。" not in p["text"]:
                p["ambiguous_caption"] = True
                ambiguous.add(number(match.group(1)))
                issue(items, "unverified", "ambiguous_caption", "段首图号可能是图题或正文；缺少明确样式/图片关联，不自动认定。", f"段落{index + 1}")
        for label, locations in captions.items():
            if len(locations) > 1:
                issue(items, "error", "duplicate_caption", f"图{label}题注重复。", [f"段落{i + 1}" for i in locations])
        simple = sorted(int(label) for label in captions if label.isdigit())
        if simple:
            if min(simple) > 1:
                issue(items, "unverified", "caption_start_offset", f"简单图号从图{min(simple)}开始，需确认节选或续号约定；未要求补齐此前图号。", "正文图题")
            missing = sorted(set(range(min(simple), max(simple) + 1)) - set(simple))
            uncertain = [n for n in missing if str(n) in ambiguous]
            missing = [n for n in missing if str(n) not in ambiguous]
            if uncertain:
                issue(items, "unverified", "caption_gap_uncertain", "连续图号中存在尚未确认的图题，需人工核对。", "正文图题")
            if missing:
                issue(items, "error", "caption_gap", f"简单连续图号缺少：{', '.join('图' + str(n) for n in missing)}；如为节选请人工确认编号约定。", "正文图题")
        if any(not label.isdigit() for label in captions):
            issue(items, "unverified", "compound_number_sequence", "分章/复合图号只检查引用，不推定连续编号规则。", "正文图题")
        referenced = set()
        for index, p in enumerate(paragraphs):
            if "caption" in p or p.get("ambiguous_caption"):
                continue
            skip_until = 0
            for match in FIG.finditer(p["text"]):
                if match.start() < skip_until:
                    continue
                if EXTERNAL_SOURCE.search(p["text"][:match.start()]):
                    issue(items, "unverified", "external_figure_reference", "图号前有明确外部材料来源；未作为本报告插图引用，需核对原材料。", f"段落{index + 1}")
                    external_range = RANGE.match(p["text"][match.end():])
                    if external_range:
                        skip_until = match.end() + external_range.end()
                    continue
                label = number(match.group(1))
                labels = [label]
                tail = p["text"][match.end():]
                end = RANGE.match(tail) if label.isdigit() else None
                if end:
                    start_value, end_value = int(label), int(end.group(2))
                    skip_until = match.end() + end.end()
                    if start_value <= end_value <= start_value + 200:
                        labels = [str(n) for n in range(start_value, end_value + 1)]
                    else:
                        issue(items, "unverified", "reference_range", "图号范围逆序或过大，未展开。", f"段落{index + 1}")
                        continue
                elif "-" in label and label not in captions and labels == [label]:
                    issue(items, "unverified", "ambiguous_hyphen_reference", f"图{label}可能是复合图号或范围，未自动拆分。", f"段落{index + 1}")
                    continue
                if re.match(r"\s*[、,，]\s*\d", tail):
                    issue(items, "unverified", "abbreviated_reference", "省略“图”字的并列引用未全部展开，请复核。", f"段落{index + 1}")
                if re.match(r"\s*[（(][a-zA-Z一二三四五六七八九十]+[）)]", tail):
                    issue(items, "unverified", "subfigure_reference", "子图引用只核对主图号，子图是否存在需人工核对。", f"段落{index + 1}")
                for label in labels:
                    referenced.add(label)
                    if label in ambiguous and label not in captions:
                        issue(items, "unverified", "reference_caption_uncertain", f"图{label}只能匹配到歧义图题，未认定失效引用。", f"段落{index + 1}")
                    elif label not in captions:
                        issue(items, "error", "missing_figure_reference", f"正文引用图{label}，但未找到对应图题。", f"段落{index + 1}")
        for label in set(captions) - referenced:
            issue(items, "warning", "unreferenced_figure", f"图{label}未找到正文引用。", f"图{label}")
        hashes = defaultdict(list)
        for sequence, drawing in enumerate(drawings, 1):
            loc = f"正文图片{sequence}（段落{drawing['paragraph'] + 1}）"
            target = drawing["target"]
            if not target or target not in archive.namelist():
                issue(items, "unverified", "image_unavailable", "图片为外部链接或内嵌资源不可读取。", loc)
                continue
            data = archive.read(target)
            hashes[hashlib.sha256(data).hexdigest()].append(loc)
            if drawing["floating"]:
                issue(items, "unverified", "floating_image", "浮动图片的显示位置、图题关联和布局未验证。", loc)
                continue
            try:
                with Image.open(io.BytesIO(data)) as image:
                    width, height = image.size
            except (UnidentifiedImageError, OSError):
                issue(items, "unverified", "unsupported_image", "图片格式无法测量；矢量图/WMF等需渲染检查。", loc)
                continue
            extent = drawing["extent"]
            try:
                cx, cy = float(extent.get("cx")), float(extent.get("cy"))
                if cx <= 0 or cy <= 0:
                    raise ValueError
            except (AttributeError, TypeError, ValueError):
                issue(items, "unverified", "image_extent", "无法读取有效显示尺寸。", loc)
                continue
            crop = drawing["xml"].find(".//a:srcRect", NS)
            if crop is not None:
                width *= 1 - (int(crop.get("l", 0)) + int(crop.get("r", 0))) / 100000
                height *= 1 - (int(crop.get("t", 0)) + int(crop.get("b", 0))) / 100000
            if width <= 0 or height <= 0:
                issue(items, "unverified", "image_crop", "图片裁剪参数无法测量。", loc)
                continue
            dpi = min(width * 914400 / cx, height * 914400 / cy)
            if dpi < min_dpi:
                issue(items, "warning", "low_dpi", f"有效分辨率约{dpi:.0f} DPI，低于预警值{min_dpi:g} DPI；文字可读性仍需页面检查。", loc)
            transform = drawing["xml"].find(".//a:xfrm", NS)
            rotation = int(transform.get("rot", 0)) if transform is not None else 0
            if rotation:
                issue(items, "unverified", "rotated_image", "旋转图片的最终尺寸与纵横比需渲染核对。", loc)
            elif abs((cx / cy) / (width / height) - 1) > 0.05:
                issue(items, "warning", "aspect_ratio", "显示纵横比与裁剪后图片相差超过5%，需核对是否拉伸。", loc)
            index = drawing["paragraph"]
            if not any("caption" in paragraphs[n] for n in (index, index + 1) if n < len(paragraphs)):
                issue(items, "warning", "image_caption_association", "图片附近未匹配普通图题；封面标志、装饰图可人工排除。", loc)
        for locations in hashes.values():
            if len(locations) > 1:
                issue(items, "warning", "duplicate_image_content", "多处正文图片使用完全相同内容（含同一资源复用），请核对是否符合用途。", locations)
        if notes:
            read_notes(notes, captions, items)
        for part in archive.namelist():
            if re.match(r"word/(header|footer)\d+\.xml$", part) and b"drawing" in archive.read(part):
                issue(items, "unverified", "outside_body_images", "页眉/页脚图片未纳入正文图片检查。", part)
        issue(items, "unverified", "semantic_and_page_review", "未验证图面与图注语义、实验来源真实性、读数一致性、同页关系及最终可读性；须回看原图并检查最新渲染页面。", "整份报告")
    counts = Counter(item["level"] for item in items)
    return dict(report=str(path), summary={level: counts[level] for level in ("error", "warning", "unverified")}, issues=items, scope="只读结构辅助检查；退出码0仅表示未发现明确结构错误，不表示报告验收通过。")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--min-dpi", type=float, default=150)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.min_dpi <= 0:
        parser.error("--min-dpi 必须大于0")
    try:
        if args.out and args.out.resolve() in {p.resolve() for p in (args.report, args.notes) if p}:
            raise ValueError("输出路径不能覆盖输入报告或图片笔记")
        result = audit(args.report, args.notes, args.min_dpi)
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            args.out.write_text(payload + "\n", encoding="utf-8")
        print(payload)
        return int(result["summary"]["error"] > 0)
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError, ValueError) as exc:
        print(json.dumps({"error": f"无法处理输入或写入检查结果：{exc}"}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
