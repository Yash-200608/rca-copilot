from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/samples", tags=["samples"])
DIR = Path(__file__).resolve().parents[3] / "samples"
LABELS = {
    "IR-B-26-093_Omeprazole_Stage4.pdf": "Incident report (PDF) - Omeprazole Stage-4 temperature excursion",
    "OOS_Gabapentin_GBP-26-0734.eml": "Email (.eml) - Gabapentin residual-solvent OOS",
    "ShiftLog_Metformin_MFH-26-1187.txt": "Shift log (text) - Metformin quarantined lot charged",
    "Scanned_Incident_NO_TEXT.pdf": "Scanned PDF (no text layer) - shows OCR-required handling",
}


@router.get("")
async def list_samples():
    return [{"name": n, "label": l} for n, l in LABELS.items() if (DIR / n).exists()]


@router.get("/{name}")
async def get_sample(name: str):
    if name not in LABELS or not (DIR / name).exists():
        raise HTTPException(404, "Unknown sample")
    return FileResponse(DIR / name, filename=name)
