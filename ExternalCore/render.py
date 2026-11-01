# Python | ExternalCore/render.py | Python 3.12+ | portable export of the overlay command stream.
from pathlib import Path
import xml.etree.ElementTree as ET


def save_svg(path, width, height, commands, *, provenance=""):
    if any(type(v) is not int or not 1 <= v <= 8192 for v in (width, height)):
        raise ValueError("SVG dimensions must be in [1,8192]")
    root = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", width=str(width), height=str(height),
                      viewBox=f"0 0 {width} {height}")
    ET.SubElement(root, "desc").text = provenance
    ET.SubElement(root, "rect", width="100%", height="100%", fill="#11151b")
    for index, command in enumerate(commands):
        if index >= 10000:
            raise ValueError("too many SVG commands")
        rgb = command["color"]
        if len(rgb) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in rgb):
            raise ValueError("invalid RGB color")
        color = "#" + "".join(f"{v:02x}" for v in rgb)
        kind = command["kind"]
        if kind == "line":
            ET.SubElement(root, "line", **{k: str(command[k]) for k in ("x1","y1","x2","y2")},
                          stroke=color, **{"stroke-width": str(command.get("width", 1))})
        elif kind == "circle":
            ET.SubElement(root, "circle", cx=str(command["x"]), cy=str(command["y"]),
                          r=str(command["radius"]), fill="none", stroke=color,
                          **{"stroke-width": str(command.get("width", 1))})
        elif kind == "text":
            ET.SubElement(root, "text", x=str(command["x"]), y=str(command["y"]+12),
                          fill=color, **{"font-family": "monospace", "font-size": "12"}).text = command["text"]
        else:
            raise ValueError("unknown SVG drawing command")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
