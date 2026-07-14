"""Generate `ERD Diagram.drawio` from the SQLAlchemy models.

The ERD used to be hand-drawn and drifted badly: it froze at Alembic revision 001
(7 tables) while the schema grew to 20. Generating it from `Base.metadata` means
it cannot drift again.

Run after adding a migration:

    cd app
    .venv/Scripts/python.exe ../doc/diagrams/generate_erd.py

Requires no database connection.
"""

from __future__ import annotations

import io
import os
import sys
from xml.sax.saxutils import escape

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://u:p@localhost:5432/db")
os.environ.setdefault("MAGIC_LINK_BASE_URL", "http://localhost:5173/auth/verify")
os.environ.setdefault("SECRET_KEY", "x" * 32)

REPO_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app")
sys.path.insert(0, os.path.abspath(REPO_APP))

from sqlalchemy.dialects import postgresql  # noqa: E402

from src.core.database import Base  # noqa: E402
import src.core.rate_limit  # noqa: E402,F401
import src.modules.billing.models  # noqa: E402,F401
import src.modules.dining.models  # noqa: E402,F401
import src.modules.identity.models  # noqa: E402,F401
import src.modules.menu.models  # noqa: E402,F401
import src.modules.menu_scan.models  # noqa: E402,F401

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ERD Diagram.drawio")

# Tables grouped into the five business domains + infrastructure. Order inside a
# group is the vertical stacking order of that column.
GROUPS: list[tuple[str, str, list[str]]] = [
    (
        "Identity",
        "#dae8fc",
        [
            "users",
            "magic_link_tokens",
            "user_sessions",
            "food_profiles",
            "food_profile_preferences",
        ],
    ),
    ("Menu Scan", "#ffe6cc", ["scan_sessions", "scan_source_files", "ocr_results"]),
    ("Menu", "#d5e8d4", ["menus", "food_items"]),
    (
        "Dining / Recommendation",
        "#e1d5e7",
        [
            "dining_sessions",
            "dining_session_invites",
            "dining_session_participants",
            "dining_session_participant_preferences",
            "food_item_recommendations",
            "food_item_recommendation_participant_breakdowns",
        ],
    ),
    ("Billing", "#fff2cc", ["bills", "bill_items", "bill_adjustments"]),
    ("Infrastructure", "#f5f5f5", ["ai_throttle"]),
]

COL_W = 330
COL_GAP = 60
ROW_H = 18
HEADER_H = 26
TABLE_GAP = 34
TOP = 110
LEFT = 40


def type_label(column) -> str:
    """Short, readable Postgres type for a column."""
    try:
        text = column.type.compile(dialect=postgresql.dialect())
    except Exception:
        text = str(column.type)
    text = text.replace("TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ")
    text = text.replace("CHARACTER VARYING", "VARCHAR")
    text = text.replace("DOUBLE PRECISION", "FLOAT")
    return text


def column_line(table, column) -> str:
    """One ERD row: key marker, name, type, nullability."""
    markers = []
    if column.primary_key:
        markers.append("PK")
    if column.foreign_keys:
        markers.append("FK")
    marker = ",".join(markers)
    prefix = f"{marker} " if marker else ""

    bits = [f"{prefix}{column.name}", type_label(column)]
    if not column.nullable and not column.primary_key:
        bits.append("NOT NULL")
    return "  ".join(bits)


def main() -> None:
    tables = {t.name: t for t in Base.metadata.sorted_tables}

    known = {name for _, _, names in GROUPS for name in names}
    missing = set(tables) - known
    if missing:
        raise SystemExit(
            f"Tables not assigned to a group in GROUPS: {sorted(missing)}. "
            "Add them, otherwise the ERD would silently omit them."
        )

    cells: list[str] = []
    geometry: dict[str, tuple[int, int, int, int]] = {}

    cells.append(
        '<mxCell id="title" value="MenuScan — Entity Relationship Diagram '
        "(Alembic head e8b5d3f07a24 — 20 tables)&#10;Generated from the SQLAlchemy "
        'models by doc/diagrams/generate_erd.py" '
        'style="text;html=1;align=center;verticalAlign=middle;fontSize=20;fontStyle=1;" '
        'vertex="1" parent="1">'
        f'<mxGeometry x="{LEFT}" y="24" width="1400" height="56" as="geometry"/>'
        "</mxCell>"
    )

    for col_index, (group_name, color, table_names) in enumerate(GROUPS):
        x = LEFT + col_index * (COL_W + COL_GAP)
        y = TOP

        cells.append(
            f'<mxCell id="grp_{col_index}" value="{escape(group_name)}" '
            'style="text;html=1;align=center;verticalAlign=middle;fontSize=14;'
            'fontStyle=1;fillColor=none;strokeColor=none;" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{TOP - 34}" width="{COL_W}" height="26" as="geometry"/>'
            "</mxCell>"
        )

        for table_name in table_names:
            table = tables[table_name]
            columns = list(table.columns)
            height = HEADER_H + ROW_H * len(columns)
            tid = f"t_{table_name}"
            geometry[table_name] = (x, y, COL_W, height)

            cells.append(
                f'<mxCell id="{tid}" value="{escape(table_name)}" '
                'style="swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;'
                f"startSize={HEADER_H};horizontalStack=0;resizeParent=0;resizeParentMax=0;"
                "html=1;whiteSpace=wrap;fontSize=12;marginBottom=0;swimlaneFillColor=#ffffff;"
                f'fillColor={color};strokeColor=#666666;" vertex="1" parent="1">'
                f'<mxGeometry x="{x}" y="{y}" width="{COL_W}" height="{height}" as="geometry"/>'
                "</mxCell>"
            )

            for row_index, column in enumerate(columns):
                is_key = column.primary_key or bool(column.foreign_keys)
                style = (
                    "text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
                    "spacingLeft=6;spacingRight=6;overflow=hidden;rotatable=0;"
                    "points=[[0,0.5],[1,0.5]];portConstraint=eastwest;whiteSpace=wrap;"
                    "html=1;fontSize=10;fontFamily=Courier New;"
                )
                if is_key:
                    style += "fontStyle=1;"
                cells.append(
                    f'<mxCell id="{tid}_c{row_index}" '
                    f'value="{escape(column_line(table, column))}" '
                    f'style="{style}" vertex="1" parent="{tid}">'
                    f'<mxGeometry y="{HEADER_H + row_index * ROW_H}" width="{COL_W}" '
                    f'height="{ROW_H} " as="geometry"/>'
                    "</mxCell>"
                )

            y += height + TABLE_GAP

    # Foreign-key edges: child -> parent, labelled with cardinality.
    edge_index = 0
    for table in Base.metadata.sorted_tables:
        for fk_constraint in table.foreign_key_constraints:
            parent = fk_constraint.referred_table.name
            child = table.name
            if parent not in geometry or child not in geometry:
                continue

            local_cols = [el.parent for el in fk_constraint.elements]
            optional = any(col.nullable for col in local_cols)
            unique_cols = {
                tuple(sorted(c.name for c in uc.columns))
                for uc in table.constraints
                if uc.__class__.__name__ == "UniqueConstraint"
            }
            local_names = tuple(sorted(c.name for c in local_cols))
            one_to_one = local_names in unique_cols

            if one_to_one:
                label = "1 : 0..1"
            elif optional:
                label = "1 : 0..N"
            else:
                label = "1 : N"

            edge_index += 1
            cells.append(
                f'<mxCell id="e{edge_index}" value="{label}" '
                'style="edgeStyle=entityRelationEdgeStyle;rounded=0;html=1;'
                "exitX=0;exitY=0.5;entryX=1;entryY=0.5;endArrow=ERoneToMany;"
                'startArrow=ERone;endFill=0;startFill=0;fontSize=10;strokeColor=#555555;" '
                f'edge="1" parent="1" source="t_{child}" target="t_{parent}">'
                '<mxGeometry relative="1" as="geometry"/>'
                "</mxCell>"
            )

    note = (
        "ai_throttle has no foreign keys: it is an infrastructure table "
        "(anti-spam throttle for AI calls, src/core/rate_limit.py), not a "
        "business entity. It is why the system needs no Redis."
    )
    cells.append(
        f'<mxCell id="note" value="{escape(note)}" '
        'style="shape=note;whiteSpace=wrap;html=1;size=14;fontSize=11;align=left;'
        'spacingLeft=6;fillColor=#f5f5f5;strokeColor=#999999;" vertex="1" parent="1">'
        f'<mxGeometry x="{LEFT + 5 * (COL_W + COL_GAP)}" y="{TOP + 190}" '
        f'width="{COL_W}" height="110" as="geometry"/>'
        "</mxCell>"
    )

    body = "\n        ".join(cells)
    xml = f"""<mxfile host="app.diagrams.net">
  <diagram id="menuscan-erd" name="MenuScan ERD">
    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="2400" pageHeight="1800" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        {body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(xml)

    print(f"wrote {OUT}")
    print(f"  tables: {len(tables)}")
    print(f"  fk edges: {edge_index}")


if __name__ == "__main__":
    main()
