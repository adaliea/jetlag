"""Geometry and Markdown rendering shared by the State College map builder."""
import math
import re
import html

def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i, coordinate in enumerate(polygon):
        xi, yi = coordinate[:2]
        xj, yj = polygon[j][:2]
        crosses = (yi > y) != (yj > y)
        if crosses and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def local_xy(point, latitude):
    lon, lat = point
    return lon * 111.32 * math.cos(math.radians(latitude)), lat * 110.574


def distance_to_segment_km(point, a, b):
    latitude = point[1]
    px, py = local_xy(point, latitude)
    ax, ay = local_xy(a, latitude)
    bx, by = local_xy(b, latitude)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def distance_to_boundary_km(point, polygon):
    return min(
        distance_to_segment_km(point, polygon[i - 1], polygon[i])
        for i in range(len(polygon))
    )


def perpendicular_distance(point, start, end):
    x, y = point
    x1, y1 = start
    x2, y2 = end
    if start == end:
        return math.hypot(x - x1, y - y1)
    return abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / math.hypot(
        y2 - y1, x2 - x1
    )


def simplify(points, tolerance=0.00018):
    if len(points) < 3:
        return points
    max_distance = 0
    index = 0
    for i in range(1, len(points) - 1):
        distance = perpendicular_distance(points[i], points[0], points[-1])
        if distance > max_distance:
            index, max_distance = i, distance
    if max_distance <= tolerance:
        return [points[0], points[-1]]
    left = simplify(points[: index + 1], tolerance)
    right = simplify(points[index:], tolerance)
    return left[:-1] + right


def geojson_feature(geometry_type, coordinates, properties):
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {"type": geometry_type, "coordinates": coordinates},
    }


def geometry_contains(point, geometry):
    coordinates = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        return point_in_polygon(point, coordinates[0]) and not any(point_in_polygon(point, ring) for ring in coordinates[1:])
    if geometry["type"] == "MultiPolygon":
        return any(point_in_polygon(point, polygon[0]) and not any(point_in_polygon(point, ring) for ring in polygon[1:]) for polygon in coordinates)
    return False


def render_inline_markdown(text):
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def render_markdown(markdown):
    lines = []
    for line in markdown.splitlines():
        if line.startswith("  ") and lines and lines[-1].lstrip().startswith("- "):
            lines[-1] += " " + line.strip()
        else:
            lines.append(line)
    output = []
    paragraph = []
    list_open = False
    table_rows = []

    def flush_paragraph():
        if paragraph:
            output.append(f"<p>{render_inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_open
        if list_open:
            output.append("</ul>")
            list_open = False

    def flush_table():
        if not table_rows:
            return
        header, *rows = table_rows
        output.append("<div class=\"table-wrap\"><table><thead><tr>")
        output.extend(f"<th>{render_inline_markdown(cell)}</th>" for cell in header)
        output.append("</tr></thead><tbody>")
        for row in rows:
            output.append("<tr>")
            output.extend(f"<td>{render_inline_markdown(cell)}</td>" for cell in row)
            output.append("</tr>")
        output.append("</tbody></table></div>")
        table_rows.clear()

    for line in lines + [""]:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            close_list()
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            table_rows.append(cells)
            continue
        flush_table()
        if stripped.startswith("#"):
            flush_paragraph()
            close_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 3)
            title = stripped[level:].strip()
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            output.append(
                f'<h{level} id="{slug}">{render_inline_markdown(title)}</h{level}>'
            )
        elif stripped.startswith("- "):
            flush_paragraph()
            if not list_open:
                output.append("<ul>")
                list_open = True
            output.append(f"<li>{render_inline_markdown(stripped[2:])}</li>")
        elif not stripped:
            flush_paragraph()
            close_list()
        else:
            paragraph.append(stripped)

    return "\n".join(output)


def render_rules_page(markdown):
    body = render_markdown(markdown)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>State College Rules | Jet Lag: Hide + Seek</title>
  <link rel="icon" href="./favicon.svg" type="image/svg+xml">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f4efe5; color: #1e2630; font-family: Inter, system-ui, sans-serif; line-height: 1.55; }}
    header {{ position: sticky; top: 0; padding: 14px 20px; background: #172331; color: white; box-shadow: 0 2px 12px #0003; }}
    header a {{ color: #ffd27a; margin-right: 18px; }}
    main {{ max-width: 820px; margin: 0 auto; padding: 24px 20px 60px; }}
    h1 {{ line-height: 1.1; }}
    h2 {{ margin-top: 36px; padding-top: 10px; border-top: 2px solid #d8cdbb; }}
    h3 {{ margin-top: 28px; }}
    a {{ color: #1261a0; }}
    li {{ margin: 7px 0; }}
    code {{ padding: 2px 4px; border-radius: 3px; background: #e8dfd1; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ padding: 9px 10px; border: 1px solid #d8cdbb; text-align: left; vertical-align: top; }}
    th {{ background: #e9dfcf; }}
  </style>
</head>
<body>
  <header><a href="./index.html">Back to map</a><span>Use your official cards and rulebooks</span></header>
  <main>{body}</main>
</body>
</html>"""
