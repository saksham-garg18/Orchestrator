from pathlib import Path
import tempfile

import streamlit as st
import numpy as np

from core.pipeline import process_audio_file, separate_and_render_stems
from ui.theme import STREAMLIT_THEME_CSS


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _save_upload(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


def _audio_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


# ──────────────────────────────────────────────────────────────────────────────
# Pages
# ──────────────────────────────────────────────────────────────────────────────

def _page_single_file():
    st.markdown('<div class="af-card">', unsafe_allow_html=True)
    st.markdown("### Upload a file")
    uploaded = st.file_uploader(
        "Drag & drop or browse",
        type=["wav", "mp3", "flac", "ogg", "m4a"],
        key="single_upload",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if not uploaded:
        return

    st.markdown('<div class="af-card">', unsafe_allow_html=True)
    st.markdown("### Transform controls")

    col1, col2, col3 = st.columns(3)
    with col1:
        stretch_rate = st.slider(
            "Stretch rate",
            min_value=0.25, max_value=3.0, value=1.0, step=0.01,
            help="1.0 = original speed. >1 = faster, <1 = slower.",
        )
        pitch_steps = st.slider(
            "Pitch shift (semitones)",
            min_value=-24.0, max_value=24.0, value=0.0, step=0.5,
        )
    with col2:
        enable_nr      = st.checkbox("Noise reduction")
        enable_master  = st.checkbox("Loudness normalize / master")
        if enable_master:
            target_lufs = st.slider("Target LUFS", -30.0, -6.0, -14.0, 0.5)
            target_peak = st.slider("Peak ceiling (dBFS)", -6.0, -0.1, -1.0, 0.1)
        else:
            target_lufs = -14.0
            target_peak = -1.0
    with col3:
        enable_8d = st.checkbox("8D audio", help="Binaural-style sweeping pan. Use headphones.")
        pan = st.slider(
            "Manual stereo pan",
            min_value=-1.0, max_value=1.0, value=0.0, step=0.01,
            help="-1 = hard left  |  0 = center  |  1 = hard right",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("⚙️  Process", use_container_width=True):
        input_path = _save_upload(uploaded)
        with st.spinner("Processing…"):
            result = process_audio_file(
                input_path=input_path,
                output_dir="output/single",
                stretch_rate=stretch_rate,
                pitch_steps=pitch_steps,
                apply_noise_reduction=enable_nr,
                apply_mastering=enable_master,
                enable_8d=enable_8d,
                pan=pan,
                mastering_target_lufs=target_lufs,
                mastering_peak_dbfs=target_peak,
            )

        c1, c2, c3 = st.columns(3)
        c1.metric("BPM",        f"{result['bpm']:.2f}")
        c2.metric("Key",        result["key"])
        c3.metric("Confidence", f"{result['key_confidence']:.3f}")

        data = _audio_bytes(result["output_path"])
        st.audio(data, format="audio/wav")
        st.download_button(
            "⬇  Download processed audio",
            data=data,
            file_name="processed.wav",
            mime="audio/wav",
            use_container_width=True,
        )


def _page_stems():
    st.markdown('<div class="af-card">', unsafe_allow_html=True)
    st.markdown("### Upload source song for stem separation")
    uploaded = st.file_uploader(
        "Drag & drop or browse",
        type=["wav", "mp3", "flac", "ogg", "m4a"],
        key="stems_upload",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="af-card">', unsafe_allow_html=True)
    st.markdown(
        "### Stem stereo positions  "
        '<span class="af-pill">−1 = left speaker</span> '
        '<span class="af-pill">0 = center</span> '
        '<span class="af-pill">+1 = right speaker</span>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        vocals = st.slider("🎤  Vocals", -1.0, 1.0, 0.0, 0.01)
    with c2:
        drums  = st.slider("🥁  Drums",  -1.0, 1.0, 0.0, 0.01)
    with c3:
        bass   = st.slider("🎸  Bass",   -1.0, 1.0, 0.0, 0.01)
    with c4:
        other  = st.slider("🎹  Other",  -1.0, 1.0, 0.0, 0.01)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        enable_8d_stems = st.checkbox(
            "Subtle 8D motion on stems",
            help="Applies a gentle binaural sweep after each stem is panned.",
        )
        eight_d_depth = st.slider("8D depth", 0.0, 1.0, 0.35, 0.05) if enable_8d_stems else 0.35
    with col_b:
        model = st.selectbox(
            "Demucs model",
            ["htdemucs", "mdx_extra_q", "htdemucs_ft"],
            help="htdemucs is the default. mdx_extra_q is the old default and sometimes better.",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="af-warn">⚠ Demucs downloads model weights (~80 MB) on first run '
        'and separation takes several minutes.</div>',
        unsafe_allow_html=True,
    )

    if not uploaded:
        return

    if st.button("🎚  Separate & render stems", use_container_width=True):
        input_path = _save_upload(uploaded)
        with st.spinner("Running Demucs separation… this may take a few minutes."):
            result = separate_and_render_stems(
                input_path=input_path,
                output_dir="output/stems",
                positions={
                    "vocals": vocals,
                    "drums":  drums,
                    "bass":   bass,
                    "other":  other,
                },
                model=model,
                apply_8d=enable_8d_stems,
                eight_d_depth=eight_d_depth,
            )

        st.success(f"Stems saved to: `{result['stems_dir']}`")
        data = _audio_bytes(result["mix_path"])
        st.audio(data, format="audio/wav")
        st.download_button(
            "⬇  Download stereo stem mix",
            data=data,
            file_name="stem_mix.wav",
            mime="audio/wav",
            use_container_width=True,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="AudioForge",
        page_icon="🎧",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(STREAMLIT_THEME_CSS, unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 🎧 AudioForge")
        st.markdown("---")
        mode = st.radio(
            "Mode",
            ["Single file processing", "Stem separation + spatial mix"],
        )
        st.markdown("---")
        st.markdown(
            "**Tips**\n"
            "- 8D audio sounds best on headphones.\n"
            "- Demucs runs on CPU by default; GPU speeds it up ~10×.\n"
            "- Loudness normalize targets −14 LUFS (streaming-safe).\n"
            "- Pan values use equal-power law so volume stays balanced.",
            unsafe_allow_html=True,
        )

    # ── Main area ────────────────────────────────────────────────────────────
    st.title("🎧 AudioForge")
    st.caption(
        "BPM & key detection · time-stretching · pitch shifting · "
        "noise reduction · loudness mastering · 8D audio · "
        "Demucs stem separation · per-stem stereo positioning"
    )
    st.markdown("---")

    if mode == "Single file processing":
        _page_single_file()
    else:
        _page_stems()