"""Generates docs/decision_log.pdf (1 page).  Run: python docs/make_decision_log.py"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent / "decision_log.pdf"
ss = getSampleStyleSheet()
body = ParagraphStyle("b", parent=ss["Normal"], fontSize=9, leading=12)
cell = ParagraphStyle("c", parent=body, fontSize=8.3, leading=10.5)
cellb = ParagraphStyle("cb", parent=cell, fontName="Helvetica-Bold")
h = ParagraphStyle("h", parent=ss["Heading2"], fontSize=11, spaceBefore=6, spaceAfter=3)
title = ParagraphStyle("t", parent=ss["Title"], fontSize=16, spaceAfter=2)

rows = [
    ("Trade-off", "FAISS (on-device)", "Qdrant free cloud tier"),
    ("Cost", "Free, no usage caps. Only local CPU/RAM is used.",
     "Free tier is capped (small cluster, limited storage) and may require a paid plan as data grows."),
    ("Latency", "In-process search, typically under 1 ms for ~200 vectors. No network hop.",
     "Every query crosses the network; tens to hundreds of ms depending on region and connection."),
    ("Privacy and offline use", "Data never leaves the device; works fully offline.",
     "Vectors and payloads are stored on a third-party server; needs internet and API keys."),
    ("Filtering and metadata", "None built in. Must filter via SQLite (price, brand) and join by id.",
     "Native payload filtering, so vector search and filters (e.g. price &lt; 100) run in one call."),
    ("Scaling and sharing", "Limited to one machine's RAM; index file must be copied to share it.",
     "Easy multi-user access, replication and growth to millions of vectors."),
    ("Operations", "We save/load the .faiss file ourselves and keep it in sync with SQLite.",
     "Managed service: backups, upserts and updates handled by the provider; adds vendor dependency."),
]
data = [[Paragraph(c, cellb if (r == 0 or i == 0) else cell) for i, c in enumerate(row)]
        for r, row in enumerate(rows)]

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                        topMargin=14*mm, bottomMargin=12*mm,
                        title="Architecture Decision Log: FAISS vs Qdrant", author="Product Search Project")
t = Table(data, colWidths=[34*mm, 68*mm, 68*mm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f4f8")]),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c2cf")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
]))
# header row text must be white
for p in data[0]:
    p.style = ParagraphStyle("hw", parent=cellb, textColor=colors.white)

story = [
    Paragraph("Architecture Decision Log: Local FAISS vs Qdrant Free Tier", title),
    Paragraph("ADR-001 | Status: Accepted | Scope: vector search for the electronics product catalog", body),
    Paragraph("1. Context", h),
    Paragraph("The catalog has about 200 electronics products stored in SQLite (<i>products.db</i>), with an FTS5 table for "
              "BM25 keyword search. Titles and descriptions are embedded with <i>all-MiniLM-L6-v2</i> "
              "(384 dimensions). We need a place to store these vectors and run semantic search. "
              "Two options were considered: a local FAISS index file, or the free tier of Qdrant Cloud.", body),
    Paragraph("2. Options compared", h),
    t,
    Paragraph("3. Decision", h),
    Paragraph("<b>Use FAISS on-device</b> (<i>IndexIDMap</i> over <i>IndexFlatIP</i>, saved as <i>products.faiss</i>). "
              "At 200 vectors of 384 floats the index is about 300 KB, so an exact brute-force search is instant and "
              "needs no tuning. Vectors are normalized, so inner product equals cosine similarity, and FAISS ids are "
              "the SQLite product ids, which makes joining results back to product rows trivial.", body),
    Paragraph("4. Consequences", h),
    Paragraph("<b>Positive:</b> zero cost, no network dependency, offline-capable, simple reproducible rebuild "
              "(<i>python rebuild_all.py</i>). <b>Negative:</b> no built-in metadata filtering (we post-filter using SQLite), "
              "and the index must be rebuilt or updated whenever products change. "
              "<b>Revisit when:</b> the catalog grows beyond roughly 100k items, multiple users or services must query the "
              "same index, or hybrid vector-plus-filter queries become a core requirement. "
              "At that point migrating to Qdrant is straightforward because the embeddings and ids are already stored "
              "in a portable form.", body),
    Spacer(1, 4),
    Paragraph("<font size=7 color='#666666'>Note: free-tier limits and latency figures are approximate and should be "
              "verified against Qdrant's current pricing page before any migration.</font>", body),
]
doc.build(story)
print("Wrote", OUT)