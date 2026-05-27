from __future__ import annotations

import json
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.equalizer import BAND_FREQS, EQ_PRESETS, GAIN_RANGE_DB
from core.io_utils import ensure_dir
from core.pipeline import process_audio_file, separate_and_render_stems


STEM_MODELS: dict[str, list[str]] = {
    "htdemucs": ["vocals", "drums", "bass", "other"],
    "htdemucs_6s": ["vocals", "drums", "bass", "guitar", "piano", "other"],
    "htdemucs_ft": ["vocals", "drums", "bass", "other"],
    "mdx_extra_q": ["vocals", "drums", "bass", "other"],
}


@dataclass
class JobRecord:
    job_id: str
    kind: str
    created_at: str
    job_dir: Path
    input_path: Path
    preview_path: Path
    result: dict[str, Any] = field(default_factory=dict)
    stems_dir: Path | None = None
    stem_files: list[dict[str, str]] = field(default_factory=list)


app = FastAPI(title="AudioForge API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_JOBS: dict[str, JobRecord] = {}
_LOCK = threading.Lock()
_WORK_ROOT = ensure_dir(Path(tempfile.gettempdir()) / "audioforge_jobs")
_DOWNLOAD_ROOT = ensure_dir(Path("output") / "downloads")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_dir(job_id: str) -> Path:
    path = _WORK_ROOT / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slugify_name(name: str) -> str:
    cleaned = [ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name]
    slug = "".join(cleaned).strip("_")
    return slug or "track"


def _parse_payload(raw_payload: str | None) -> dict[str, Any]:
    if not raw_payload:
        return {}
    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object.")
    return parsed


def _store_upload(job_dir: Path, uploaded_file: UploadFile) -> Path:
    filename = Path(uploaded_file.filename or "input.wav").name
    target = job_dir / "input" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


async def _save_upload_file(target: Path, uploaded_file: UploadFile) -> None:
    data = await uploaded_file.read()
    target.write_bytes(data)


def _register_job(record: JobRecord) -> JobRecord:
    with _LOCK:
        _JOBS[record.job_id] = record
    return record


def _get_job(job_id: str) -> JobRecord:
    with _LOCK:
        job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _preview_response(job: JobRecord) -> FileResponse:
    if not job.preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview file is no longer available")
    return FileResponse(
        path=str(job.preview_path),
        media_type="audio/wav",
        filename=job.preview_path.name,
    )


def _download_response(job: JobRecord) -> FileResponse:
    if not job.preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview file is no longer available")
    persisted_name = f"{job.job_id}_{job.preview_path.name}"
    persisted_path = _DOWNLOAD_ROOT / persisted_name
    shutil.copy2(job.preview_path, persisted_path)
    return FileResponse(
        path=str(persisted_path),
        media_type="audio/wav",
        filename=persisted_name,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {
        "equalizer": {
            "bandFrequencies": BAND_FREQS,
            "gainRangeDb": GAIN_RANGE_DB,
            "presets": EQ_PRESETS,
            "defaultQ": 1.41,
        },
        "stemModels": STEM_MODELS,
        "singleTrackModes": [
            "BPM and key analysis",
            "Time stretch",
            "Pitch shift",
            "Noise reduction",
            "Loudness mastering",
            "8D motion",
            "Stereo pan",
            "16-band EQ",
        ],
    }


@app.get("/api/jobs/{job_id}")
def describe_job(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    return {
        "jobId": job.job_id,
        "kind": job.kind,
        "createdAt": job.created_at,
        "result": job.result,
        "previewAvailable": job.preview_path.exists(),
        "downloadUrl": f"/api/jobs/{job.job_id}/download",
    }


@app.get("/api/jobs/{job_id}/preview")
def get_preview(job_id: str) -> FileResponse:
    return _preview_response(_get_job(job_id))


@app.get("/api/jobs/{job_id}/download")
def download_preview(job_id: str) -> FileResponse:
    return _download_response(_get_job(job_id))


@app.get("/api/jobs/{job_id}/stems")
def list_stems(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    return {
        "jobId": job.job_id,
        "stems": job.stem_files,
        "stemsDir": str(job.stems_dir) if job.stems_dir else None,
    }


@app.get("/api/jobs/{job_id}/stems/{stem_name}")
def get_stem(job_id: str, stem_name: str) -> FileResponse:
    job = _get_job(job_id)
    if not job.stems_dir:
        raise HTTPException(status_code=404, detail="No stem previews are available for this job")

    target = job.stems_dir / f"{stem_name}.wav"
    if not target.exists():
        target = job.stems_dir / f"{stem_name}.flac"
    if not target.exists():
        target = job.stems_dir / f"{stem_name}.mp3"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Stem file not found")

    media_type = "audio/wav"
    if target.suffix == ".flac":
        media_type = "audio/flac"
    elif target.suffix == ".mp3":
        media_type = "audio/mpeg"

    return FileResponse(path=str(target), media_type=media_type, filename=target.name)


@app.post("/api/process/single")
async def process_single_track(
    file: UploadFile = File(...),
    payload: str | None = Form(default=None),
) -> dict[str, Any]:
    params = _parse_payload(payload)

    job_id = uuid4().hex
    job_dir = _job_dir(job_id)
    input_path = _store_upload(job_dir, file)
    await _save_upload_file(input_path, file)

    output_dir = job_dir / "single"
    output_basename = _slugify_name(Path(file.filename or "track").stem) + "_processed"

    result = process_audio_file(
        input_path=str(input_path),
        output_dir=str(output_dir),
        stretch_rate=float(params.get("stretchRate", 1.0)),
        pitch_steps=float(params.get("pitchSteps", 0.0)),
        apply_noise_reduction=bool(params.get("applyNoiseReduction", False)),
        apply_mastering=bool(params.get("applyMastering", False)),
        enable_8d=bool(params.get("enable8d", False)),
        pan=float(params["pan"]) if params.get("pan") is not None else None,
        mastering_target_lufs=float(params.get("targetLufs", -14.0)),
        mastering_peak_dbfs=float(params.get("targetPeakDbfs", -1.0)),
        eq_gains_db=params.get("eqGainsDb"),
        eq_q=float(params.get("eqQ", 1.41)),
        output_basename=output_basename,
    )

    preview_path = Path(result["output_path"])
    record = _register_job(
        JobRecord(
            job_id=job_id,
            kind="single",
            created_at=_now_iso(),
            job_dir=job_dir,
            input_path=input_path,
            preview_path=preview_path,
            result=result,
        )
    )

    return {
        "jobId": record.job_id,
        "kind": record.kind,
        "metadata": result,
        "previewUrl": f"/api/jobs/{record.job_id}/preview",
        "downloadUrl": f"/api/jobs/{record.job_id}/download",
    }


@app.post("/api/process/stems")
async def process_stems(
    file: UploadFile = File(...),
    payload: str | None = Form(default=None),
) -> dict[str, Any]:
    params = _parse_payload(payload)
    positions = params.get("positions") or {}
    if not isinstance(positions, dict) or not positions:
        raise HTTPException(status_code=400, detail="At least one stem position is required")

    job_id = uuid4().hex
    job_dir = _job_dir(job_id)
    input_path = _store_upload(job_dir, file)
    await _save_upload_file(input_path, file)

    output_dir = job_dir / "stems"
    output_basename = _slugify_name(Path(file.filename or "track").stem) + "_stem_mix"

    result = separate_and_render_stems(
        input_path=str(input_path),
        output_dir=str(output_dir),
        positions={str(name): float(value) for name, value in positions.items()},
        model=str(params.get("model", "htdemucs")),
        apply_8d=bool(params.get("apply8d", False)),
        eight_d_depth=float(params.get("eightDDepth", 0.35)),
        eq_gains_db=params.get("eqGainsDb"),
        eq_q=float(params.get("eqQ", 1.41)),
        output_basename=output_basename,
    )

    stems_dir = Path(result["stems_dir"])
    stem_files = []
    for stem_path in sorted(stems_dir.glob("*.wav")):
        stem_files.append(
            {
                "name": stem_path.stem,
                "filename": stem_path.name,
                "previewUrl": f"/api/jobs/{job_id}/stems/{stem_path.stem}",
            }
        )

    record = _register_job(
        JobRecord(
            job_id=job_id,
            kind="stems",
            created_at=_now_iso(),
            job_dir=job_dir,
            input_path=input_path,
            preview_path=Path(result["mix_path"]),
            result=result,
            stems_dir=stems_dir,
            stem_files=stem_files,
        )
    )

    return {
        "jobId": record.job_id,
        "kind": record.kind,
        "metadata": result,
        "previewUrl": f"/api/jobs/{record.job_id}/preview",
        "downloadUrl": f"/api/jobs/{record.job_id}/download",
        "stemFiles": stem_files,
    }

# Serve built frontend (if present)
dist_dir = Path(__file__).parent / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
else:
    @app.get("/")
    def root_info():
        return {
            "message": "Frontend build not found. Run `cd frontend && npm install && npm run build`, then restart the server."
        }
