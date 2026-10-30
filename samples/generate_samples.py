"""Generate the demo input documents (all names, sites and batch numbers are fictional).

Run:  backend\\.venv\\Scripts\\python samples\\generate_samples.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).parent

IR_PDF = [
    ("title", "KESTREL FINE CHEMICALS LTD. - UNIT 3 (API), BLOCK B"),
    ("h1", "INCIDENT REPORT (Form QA-F-021, Rev. 04)"),
    ("table", [
        ["Incident Report No.:", "IR/B/26/093", "Date of Report:", "21-Oct-2026"],
        ["Department:", "Production - Block B", "Product:", "Omeprazole (API)"],
        ["Batch No.:", "OMZ-2610-017", "Stage:", "Stage-4 (Oxidation)"],
        ["Batch Size:", "410 kg (input sulfide)", "Output:", "312 kg"],
        ["Equipment:", "R-204 (5 KL GLR), TIC-204 / TCV-204, dosing pump P-206", "", ""],
    ]),
    ("h2", "1. Description of incident"),
    ("p", "During Stage-4 oxidation of batch OMZ-2610-017 in the night shift of 13/14-Oct-2026, m-CPBA solution was being added to the "
          "reaction mass in R-204 as per BMR step 4.12 (mass temperature -5 °C to +5 °C during addition). During the addition the jacket "
          "brine valve TCV-204 did not respond to the TIC-204 output and the mass temperature went down to -11.6 °C. Addition was continued. "
          "The operator put TIC-204 in manual and closed the brine inlet hand valve, after which the temperature rose sharply to a maximum of "
          "+13.8 °C (DCS) and the high temperature alarm came. The operator stopped P-206 and opened the brine hand valve. Temperature came "
          "back within range and the balance addition was completed. Total time outside range was approx. 1 hour. The operator recorded the "
          "event in BMR remarks."),
    ("p", "IPC (HPLC) after reaction: Sulfone (Imp-D) 0.91% (IPC limit NMT 0.30%); Sulfide 0.38% (NMT 0.50%). The batch was taken forward "
          "for work-up, isolation and drying."),
    ("p", "On 20-Oct-2026 QC reported OOS in the finished API (A.R. No. QC/26/4471): Impurity D (sulfone) 0.27% against specification "
          "NMT 0.10%. Total impurities 0.46% (NMT 0.5%); Assay 99.4% (98.0-102.0%). The OOS is considered linked to the temperature "
          "excursion in Stage-4."),
    ("h2", "2. Immediate action taken"),
    ("p", "a) Batch OMZ-2610-017 (312 kg) kept on hold in quarantine area. QA informed."),
    ("p", "b) Instrumentation checked TCV-204; positioner found faulty and replaced on 15-Oct-2026."),
    ("p", "c) R-204 not used for Stage-4 till valve check was completed."),
    ("h2", "3. Probable cause"),
    ("p", "Malfunction of brine control valve TCV-204."),
    ("h2", "4. Proposed action"),
    ("p", "Investigation to be carried out along with QA. Batch disposition as per QA decision."),
    ("spacer", ""),
    ("p", "Reported by: Rahul Sharma, Production Officer - Sign/Date: R.S. 21-Oct-2026"),
    ("p", "Reviewed by: Vikram Rao, HOD Production - Sign/Date: V.R. 21-Oct-2026"),
    ("p", "QA Receipt: ______________   Date/Time: ______________"),
]

EML = """From: Anjali Verma <anjali.verma@westbrook-api.example>
To: QA Investigations <qa.investigations@westbrook-api.example>; Head Production - Block C <head.prod.c@westbrook-api.example>
Cc: Head QC <head.qc@westbrook-api.example>
Subject: OOS - Residual Solvent (Methanol) - Gabapentin USP - B.No. GBP-26-0734
Date: Tue, 27 Oct 2026 16:52:00 +0530
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"

Dear All,

This is to inform you that Gabapentin USP batch GBP-26-0734 (final API, sample received in QC on 25-Oct-2026) has failed in Residual Solvents by HS-GC (STP/QC/GBP-014).

Results:
- Methanol: 4,180 ppm and 4,260 ppm (two independent sample preparations), average 4,220 ppm. Specification: NMT 3000 ppm.
- 2-Propanol: 640 ppm. Specification: NMT 5000 ppm - complies.
- LOD (release test): 0.49% w/w. Specification: NMT 0.5% w/w - complies.

Preliminary laboratory checks (Phase Ia) were done by the GC section in-charge along with the analyst:
- System suitability passed (%RSD of six methanol standard injections 2.4%, limit NMT 10.0%; resolution complies). Blank shows no peak at methanol RT.
- Standard and sample weights, dilutions and calculations re-verified - no error found.
- Headspace vials checked for crimp integrity - OK.
- GC-HS-04 calibration valid till 12-Dec-2026; no error messages in the sequence.
- Standard stock solution and balance sample quantity retained.

No assignable laboratory error has been identified so far. As per SOP QA-OOS-002 we request QA approval for hypothesis testing and retest of the original sample by a second analyst.

For your information, the previous batch GBP-26-0731 gave methanol 2,710 ppm (within limit). Normally this product gives 400-1,100 ppm.

Production is requested to check the drying records of this batch. The batch is under QC hold in SAP.

Regards,
Anjali Verma
Manager - Quality Control
Westbrook API Site
"""

SHIFT_LOG = """SHIFT LOG - RM STORES (DISPENSING) / PRODUCTION BLOCK A
Date: 22/10/2026 | Shift: B (14:00-22:00) | Product: Metformin HCl | B.No.: MFH-26-1187 (Stage-I)

15:20 - Dispensing for B.No. MFH-26-1187 started at booth DB-02. Balance WB-07 daily check done. DMA.HCl 5 drums ok. Dicyandiamide (DCDA) 8 bags x 25 kg as per dispensing slip, lot DCD/26/0912. Weighed on WB-07, printouts taken. Checked by PS.
16:10 - Material shifted to Block A. Charged to R-101 approx 16:40-17:15 as per BMR.
17:50 - During empty bag reconciliation store helper (Sachin) found 3 empty DCDA bags with yellow UNDER TEST label, lot DCD/26/0931 (GRN dt 20/10). Other 5 empty bags are lot 0912. Both lots same supplier, same bag print. Lot 0931 was kept in rack R-3 along with 0912 since Tuesday because quarantine bay was full.
18:05 - Informed shift in-charge Mr. R. Kale. 2 full bags of 0931 still lying in R-3 - shifted to quarantine bay and tagged.
18:20 - QA on-call informed on phone. Told to continue reaction and keep batch on hold before isolation. Deviation to be raised in general shift tomorrow.
Reaction temp 128-131 C, normal. IPC sample to be sent at 21:00.
Dispensing slip and BMR show lot 0912 for all 8 bags - to be corrected after QA decision.

Note for next shift:
1) Do not issue DCDA from R-3 till QA clearance.
2) Check whether any 0931 bags went for B.No. MFH-26-1186 (A-shift) - not verified yet.

Logged by: P. Shinde, Production Officer (B-shift)
"""


def build_incident_pdf(path: Path) -> None:
    ss = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=ss["Title"], fontSize=13, spaceAfter=4)
    h1 = ParagraphStyle("h1", parent=ss["Heading2"], fontSize=11, alignment=1)
    h2 = ParagraphStyle("h2", parent=ss["Heading3"], fontSize=10, spaceBefore=8, spaceAfter=2)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.2, leading=12.5)
    cell = ParagraphStyle("c", parent=body, fontSize=8.5, leading=11)
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Incident Report IR/B/26/093", author="Kestrel Fine Chemicals Ltd. (fictional)")
    flow = []
    for kind, content in IR_PDF:
        if kind == "title":
            flow.append(Paragraph(content, title))
        elif kind == "h1":
            flow.append(Paragraph(content, h1))
        elif kind == "h2":
            flow.append(Paragraph(content, h2))
        elif kind == "p":
            flow.append(Paragraph(content, body))
        elif kind == "spacer":
            flow.append(Spacer(1, 8))
        elif kind == "table":
            rows = [[Paragraph(c, cell) for c in r] for r in content]
            t = Table(rows, colWidths=[32 * mm, 62 * mm, 30 * mm, 48 * mm])
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("SPAN", (1, 4), (3, 4))]))
            flow += [t, Spacer(1, 4)]
    doc.build(flow)


def build_scanned_pdf(path: Path) -> None:
    """An image-only PDF (no text layer) used to demonstrate scanned-document detection."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    img = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    y = 120
    for line in ["INCIDENT REPORT (scanned copy)", "Batch OMZ-2610-017  Stage-4 oxidation", "Temperature went outside the CPP range.",
                 "(This page is an image: no text layer.)"]:
        d.text((100, y), line, fill="black", font=font)
        y += 60
    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawImage(ImageReader(img), 0, 0, width=A4[0], height=A4[1])
    c.save()


if __name__ == "__main__":
    build_incident_pdf(OUT / "IR-B-26-093_Omeprazole_Stage4.pdf")
    (OUT / "OOS_Gabapentin_GBP-26-0734.eml").write_text(EML, encoding="utf-8")
    (OUT / "ShiftLog_Metformin_MFH-26-1187.txt").write_text(SHIFT_LOG, encoding="utf-8")
    build_scanned_pdf(OUT / "Scanned_Incident_NO_TEXT.pdf")
    print("samples written to", OUT)
