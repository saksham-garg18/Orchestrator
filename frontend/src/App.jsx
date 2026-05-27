import { useEffect, useMemo, useRef, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const FALLBACK_CATALOG = {
  equalizer: {
    bandFrequencies: [31, 63, 125, 250, 500, 1000, 2000, 3000, 4000, 6000, 8000, 10000, 12000, 14000, 16000, 20000],
    gainRangeDb: [-18, 18],
    defaultQ: 1.41,
    presets: {
      Flat: Array(16).fill(0),
      'Bass Boost': [6, 5, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      'Treble Boost': [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 6, 5],
    },
  },
  stemModels: {
    htdemucs: ['vocals', 'drums', 'bass', 'other'],
    htdemucs_6s: ['vocals', 'drums', 'bass', 'guitar', 'piano', 'other'],
    htdemucs_ft: ['vocals', 'drums', 'bass', 'other'],
    mdx_extra_q: ['vocals', 'drums', 'bass', 'other'],
  },
};

const STEM_ICONS = {
  vocals: '●',
  drums: '◌',
  bass: '■',
  guitar: '▲',
  piano: '◆',
  other: '✦',
};

const makeFlatEq = () => Array(16).fill(0);

function formatBand(hz) {
  return hz >= 1000 ? `${Math.round(hz / 1000)}k` : `${Math.round(hz)}`;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function useReveal() {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) {
      return undefined;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12 },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return [ref, visible];
}

function Reveal({ children, className = '' }) {
  const [ref, visible] = useReveal();
  return (
    <div ref={ref} className={`reveal ${visible ? 'reveal--visible' : ''} ${className}`}>
      {children}
    </div>
  );
}

function Card({ title, eyebrow, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      {eyebrow ? <div className="card__eyebrow">{eyebrow}</div> : null}
      {title ? <h2 className="card__title">{title}</h2> : null}
      {children}
    </section>
  );
}

function SectionHeader({ eyebrow, title, children }) {
  return (
    <div className="studio-section__header">
      {eyebrow ? <div className="studio-section__eyebrow">{eyebrow}</div> : null}
      <h2 className="studio-section__title">{title}</h2>
      {children ? <p className="studio-section__copy">{children}</p> : null}
    </div>
  );
}

function Toggle({ label, checked, onChange, hint }) {
  return (
    <label className="toggle">
      <span>
        <strong>{label}</strong>
        {hint ? <small>{hint}</small> : null}
      </span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span className="toggle__switch" />
    </label>
  );
}

function Range({ label, value, min, max, step, onChange, suffix = '', hint, disabled = false }) {
  return (
    <label className={`range ${disabled ? 'range--disabled' : ''}`}>
      <div className="range__meta">
        <span>{label}</span>
        <strong>
          {value}
          {suffix}
        </strong>
      </div>
      {hint ? <small>{hint}</small> : null}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function Select({ label, value, options, onChange, hint }) {
  return (
    <label className="select">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}

function Chip({ children }) {
  return <span className="chip">{children}</span>;
}

function StatusPill({ label, value }) {
  return (
    <div className="status-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EqGraph({ gains }) {
  const points = gains.map((gain, index) => {
    const x = (index / (gains.length - 1)) * 100;
    const y = 50 - clamp(gain, -18, 18) * 1.6;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });

  return (
    <div className="eq-graph">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="eqStroke" x1="0" x2="1">
            <stop offset="0%" stopColor="#4f7bd6" />
            <stop offset="55%" stopColor="#c4cad6" />
            <stop offset="100%" stopColor="#d8232f" />
          </linearGradient>
        </defs>
        <line x1="0" y1="50" x2="100" y2="50" stroke="rgba(176,188,212,0.14)" strokeWidth="0.6" strokeDasharray="2 2" />
        <polyline points={points.join(' ')} fill="none" stroke="url(#eqStroke)" strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <div className="eq-graph__ticks">
        <span>31</span>
        <span>1k</span>
        <span>20k</span>
      </div>
    </div>
  );
}

function EQEditor({ title, presets, bands, state, onChange, presetLabel = 'Preset' }) {
  const presetNames = Object.keys(presets);

  const applyPreset = (presetName) => {
    onChange({
      ...state,
      eqPreset: presetName,
      eqGains: [...presets[presetName]],
    });
  };

  const updateGain = (index, nextValue) => {
    const next = [...state.eqGains];
    next[index] = nextValue;
    onChange({ ...state, eqPreset: 'Custom', eqGains: next });
  };

  return (
    <Card title={title} eyebrow="Tone shaping">
      <div className="section-stack">
        <div className="control-grid control-grid--two">
          <Select
            label={presetLabel}
            value={state.eqPreset}
            options={presetNames}
            onChange={applyPreset}
            hint="Start from a curated curve or refine it manually."
          />
          <Range
            label="Q bandwidth"
            value={state.eqQ.toFixed(2)}
            min={0.5}
            max={4}
            step={0.01}
            onChange={(value) => onChange({ ...state, eqQ: value })}
            hint="Lower is wider, higher is more surgical."
          />
        </div>

        <EqGraph gains={state.eqGains} />

        <div className="eq-grid">
          {bands.map((band, index) => (
            <label key={band} className="eq-band">
              <span>{formatBand(band)}Hz</span>
              <input
                type="range"
                min={-18}
                max={18}
                step={0.5}
                value={state.eqGains[index]}
                onChange={(event) => updateGain(index, Number(event.target.value))}
              />
              <strong>{state.eqGains[index].toFixed(1)} dB</strong>
            </label>
          ))}
        </div>
      </div>
    </Card>
  );
}

function App() {
  const [catalog, setCatalog] = useState(FALLBACK_CATALOG);
  const [mode, setMode] = useState('single');
  const [audioFile, setAudioFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [singleResult, setSingleResult] = useState(null);
  const [stemResult, setStemResult] = useState(null);
  const [singleState, setSingleState] = useState({
    stretchRate: 1,
    pitchSteps: 0,
    applyNoiseReduction: false,
    applyMastering: false,
    targetLufs: -14,
    targetPeakDbfs: -1,
    enable8d: false,
    pan: 0,
    eqEnabled: true,
    eqPreset: 'Flat',
    eqQ: FALLBACK_CATALOG.equalizer.defaultQ,
    eqGains: makeFlatEq(),
  });
  const [stemState, setStemState] = useState({
    model: 'htdemucs',
    selected: FALLBACK_CATALOG.stemModels.htdemucs,
    positions: Object.fromEntries(FALLBACK_CATALOG.stemModels.htdemucs.map((stem) => [stem, 0])),
    enable8d: false,
    eightDDepth: 0.35,
    eqEnabled: true,
    eqPreset: 'Flat',
    eqQ: FALLBACK_CATALOG.equalizer.defaultQ,
    eqGains: makeFlatEq(),
  });

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/api/config`)
      .then((response) => response.json())
      .then((data) => {
        if (!active) {
          return;
        }
        setCatalog((current) => ({
          ...current,
          ...data,
          equalizer: {
            ...current.equalizer,
            ...(data.equalizer ?? {}),
          },
          stemModels: data.stemModels ?? current.stemModels,
        }));
      })
      .catch(() => {
        if (active) {
          setNotice('Using local defaults because the API catalog could not be loaded yet.');
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!audioFile) {
      setAudioUrl('');
      return undefined;
    }

    const nextUrl = URL.createObjectURL(audioFile);
    setAudioUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [audioFile]);

  useEffect(() => {
    const stems = catalog.stemModels[stemState.model] ?? [];
    setStemState((current) => {
      const positions = Object.fromEntries(stems.map((stem) => [stem, current.positions[stem] ?? 0]));
      const selected = stems.filter((stem) => current.selected.includes(stem));
      return {
        ...current,
        selected: selected.length ? selected : stems,
        positions,
      };
    });
  }, [catalog.stemModels, stemState.model]);

  const bands = catalog.equalizer.bandFrequencies;
  const presets = catalog.equalizer.presets;
  const availableStems = catalog.stemModels[stemState.model] ?? [];

  const selectedStemPositions = useMemo(
    () => Object.fromEntries(stemState.selected.map((stem) => [stem, stemState.positions[stem] ?? 0])),
    [stemState.positions, stemState.selected],
  );

  const clearMessage = () => {
    setError('');
    setNotice('');
  };

  const processSingle = async () => {
    if (!audioFile) {
      setError('Choose a track before processing.');
      return;
    }

    clearMessage();
    setLoading(true);
    try {
      const payload = {
        stretchRate: singleState.stretchRate,
        pitchSteps: singleState.pitchSteps,
        applyNoiseReduction: singleState.applyNoiseReduction,
        applyMastering: singleState.applyMastering,
        targetLufs: singleState.targetLufs,
        targetPeakDbfs: singleState.targetPeakDbfs,
        enable8d: singleState.enable8d,
        pan: singleState.pan,
        eqGainsDb: singleState.eqEnabled ? singleState.eqGains : null,
        eqQ: singleState.eqQ,
      };

      const formData = new FormData();
      formData.append('file', audioFile);
      formData.append('payload', JSON.stringify(payload));

      const response = await fetch(`${API_BASE}/api/process/single`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? 'Single-track processing failed.');
      }

      setSingleResult(data);
      setStemResult(null);
      setNotice('Preview updated. Download is only written to disk when you click the download button.');
    } catch (err) {
      setError(err.message || 'Single-track processing failed.');
    } finally {
      setLoading(false);
    }
  };

  const processStems = async () => {
    if (!audioFile) {
      setError('Choose a track before separating stems.');
      return;
    }

    if (!stemState.selected.length) {
      setError('Select at least one stem.');
      return;
    }

    clearMessage();
    setLoading(true);
    try {
      const payload = {
        model: stemState.model,
        positions: selectedStemPositions,
        apply8d: stemState.enable8d,
        eightDDepth: stemState.eightDDepth,
        eqGainsDb: stemState.eqEnabled ? stemState.eqGains : null,
        eqQ: stemState.eqQ,
      };

      const formData = new FormData();
      formData.append('file', audioFile);
      formData.append('payload', JSON.stringify(payload));

      const response = await fetch(`${API_BASE}/api/process/stems`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? 'Stem separation failed.');
      }

      setStemResult(data);
      setSingleResult(null);
      setNotice('Stem mix and stem previews are ready. Nothing is persisted until you download the mix.');
    } catch (err) {
      setError(err.message || 'Stem separation failed.');
    } finally {
      setLoading(false);
    }
  };

  const currentDownloadUrl = singleResult?.downloadUrl ?? stemResult?.downloadUrl ?? '';
  const currentPreviewUrl = singleResult?.previewUrl ?? stemResult?.previewUrl ?? '';
  const resultMetadata = singleResult?.metadata ?? stemResult?.metadata ?? null;
  const stemFiles = stemResult?.stemFiles ?? [];
  const bpm = resultMetadata?.bpm != null ? Number(resultMetadata.bpm).toFixed(2) : '—';
  const key = resultMetadata?.key ?? '—';
  const confidence = resultMetadata?.key_confidence != null ? Number(resultMetadata.key_confidence).toFixed(3) : '—';

  return (
    <div className="app-shell">
      <div className="background-orb background-orb--one" />
      <div className="background-orb background-orb--two" />
      <div className="background-grid" />

      <header className="topbar">
        <div>
          <div className="brand">AudioForge</div>
          <div className="brand-subtitle">An obsidian console for mastering, separation, EQ, and spatial audio</div>
        </div>
        <div className="topbar__actions">
          <a href="#import">Import</a>
          <a href="#single">Single Track</a>
          <a href="#stems">Stem Lab</a>
          <a href="#player">Player</a>
        </div>
      </header>

      <main className="layout">
        <aside className="rail">
          <Reveal className="rail__card">
            <div className="rail__badge">Modern audio console</div>
            <h1>Dark. Sharp. Built for audio work.</h1>
            <p>
              Every processing feature is laid out across dedicated studio surfaces — live preview playback, per-stem control, and a download-only persistence model so nothing touches disk until you ask.
            </p>
            <div className="rail__chips">
              <Chip>Obsidian black</Chip>
              <Chip>Midnight blue</Chip>
              <Chip>Blood red</Chip>
            </div>
          </Reveal>

          <Reveal className="rail__stats">
            <StatusPill label="Mode" value={mode === 'single' ? 'Single-track' : 'Stem lab'} />
            <StatusPill label="BPM" value={bpm} />
            <StatusPill label="Key" value={key} />
            <StatusPill label="Confidence" value={confidence} />
          </Reveal>

          <Reveal className="rail__card rail__card--warning">
            <strong>Storage policy</strong>
            <p>The final offline file is only written when you click download. Preview playback uses a temporary job file.</p>
          </Reveal>
        </aside>

        <section className="content">
          <Reveal>
            <Card eyebrow="Import" title="Drop in a track and start shaping it">
              <div className="import-panel" id="import">
                <label className="file-drop">
                  <input
                    type="file"
                    accept=".wav,.mp3,.flac,.ogg,.m4a,.aac"
                    onChange={(event) => setAudioFile(event.target.files?.[0] ?? null)}
                  />
                  <span className="file-drop__title">{audioFile ? audioFile.name : 'Drag and drop, or click to browse'}</span>
                  <span className="file-drop__meta">WAV, MP3, FLAC, OGG, M4A, AAC</span>
                </label>
                <div className="mode-switcher">
                  <button className={mode === 'single' ? 'mode-switcher__active' : ''} onClick={() => setMode('single')} type="button">
                    Full-track processing
                  </button>
                  <button className={mode === 'stems' ? 'mode-switcher__active' : ''} onClick={() => setMode('stems')} type="button">
                    Stem separation + panning
                  </button>
                </div>
              </div>
            </Card>
          </Reveal>

          <section className="studio-section" id="single">
            <SectionHeader eyebrow="Single-track" title="Dedicated section for the full-track workflow">
              Controls, preview, and output actions are separated so each step stays readable and nothing competes for space.
            </SectionHeader>

            <Reveal>
              <Card eyebrow="Single-track" title="Core transform stack">
                <div className="section-stack">
                  <p className="section-copy">
                    Stretch, pitch, noise reduction, mastering, 8D motion, stereo pan, and EQ — applied in a fixed, predictable chain.
                  </p>
                  <div className="control-grid">
                    <Range
                      label="Stretch rate"
                      value={singleState.stretchRate.toFixed(2)}
                      min={0.25}
                      max={3}
                      step={0.01}
                      onChange={(value) => setSingleState((current) => ({ ...current, stretchRate: value }))}
                      hint="0.25x is slow motion, 3x is fast-forward."
                    />
                    <Range
                      label="Pitch shift"
                      value={singleState.pitchSteps.toFixed(1)}
                      min={-24}
                      max={24}
                      step={0.5}
                      onChange={(value) => setSingleState((current) => ({ ...current, pitchSteps: value }))}
                      suffix=" st"
                      hint="Semitone shift before mastering and spatial effects."
                    />
                    <Range
                      label="Stereo pan"
                      value={singleState.pan.toFixed(2)}
                      min={-1}
                      max={1}
                      step={0.01}
                      onChange={(value) => setSingleState((current) => ({ ...current, pan: value }))}
                      hint="-1 left, 0 center, +1 right."
                    />
                  </div>

                  <div className="toggle-grid">
                    <Toggle
                      label="Noise reduction"
                      checked={singleState.applyNoiseReduction}
                      onChange={(checked) => setSingleState((current) => ({ ...current, applyNoiseReduction: checked }))}
                      hint="Uses the local noisereduce package if available."
                    />
                    <Toggle
                      label="Loudness mastering"
                      checked={singleState.applyMastering}
                      onChange={(checked) => setSingleState((current) => ({ ...current, applyMastering: checked }))}
                      hint="Targets LUFS and peak ceiling for streaming-safe output."
                    />
                    <Toggle
                      label="8D audio"
                      checked={singleState.enable8d}
                      onChange={(checked) => setSingleState((current) => ({ ...current, enable8d: checked }))}
                      hint="Creates moving stereo motion for headphone listening."
                    />
                  </div>

                  <div className="control-grid control-grid--two">
                    <Range
                      label="Target LUFS"
                      value={singleState.targetLufs.toFixed(1)}
                      min={-30}
                      max={-6}
                      step={0.5}
                      onChange={(value) => setSingleState((current) => ({ ...current, targetLufs: value }))}
                      disabled={!singleState.applyMastering}
                    />
                    <Range
                      label="Peak ceiling"
                      value={singleState.targetPeakDbfs.toFixed(1)}
                      min={-6}
                      max={-0.1}
                      step={0.1}
                      onChange={(value) => setSingleState((current) => ({ ...current, targetPeakDbfs: value }))}
                      suffix=" dBFS"
                      disabled={!singleState.applyMastering}
                    />
                  </div>
                </div>
              </Card>
            </Reveal>

            <Reveal>
              <Card eyebrow="Processing" title="Analysis and preview">
                <div className="summary-stack">
                  <StatusPill label="Current file" value={audioFile ? audioFile.name : 'No file loaded'} />
                  <StatusPill label="EQ" value={singleState.eqEnabled ? singleState.eqPreset : 'Disabled'} />
                  <StatusPill label="8D" value={singleState.enable8d ? 'On' : 'Off'} />
                  <button className="primary-button" type="button" onClick={processSingle} disabled={loading || !audioFile}>
                    {loading && mode === 'single' ? 'Processing…' : 'Generate single-track preview'}
                  </button>
                </div>
                {notice ? <div className="notice notice--info">{notice}</div> : null}
                {error ? <div className="notice notice--error">{error}</div> : null}
              </Card>
            </Reveal>
          </section>

          <section className="studio-section" id="player">
            <SectionHeader eyebrow="Player" title="Dedicated section for original and processed playback">
              The audio player is isolated from the controls so preview state, downloads, and analysis remain easy to scan.
            </SectionHeader>

            <Reveal>
              <Card eyebrow="Preview" title="Web player">
                <div className="player-stack">
                  <div className="player-panel">
                    <span>Original</span>
                    {audioUrl ? <audio controls src={audioUrl} /> : <div className="player-empty">Load a file to audition the original.</div>}
                  </div>
                  <div className="player-panel player-panel--accent">
                    <span>Processed</span>
                    {currentPreviewUrl ? (
                      <audio controls src={`${API_BASE}${currentPreviewUrl}`} />
                    ) : (
                      <div className="player-empty">Preview the processed output here after you run a job.</div>
                    )}
                  </div>
                </div>
                <div className="download-row">
                  <a className={`primary-button ${currentDownloadUrl ? '' : 'primary-button--disabled'}`} href={currentDownloadUrl ? `${API_BASE}${currentDownloadUrl}` : undefined}>
                    Download final track
                  </a>
                </div>
              </Card>
            </Reveal>

            <Reveal>
              <Card eyebrow="Live status" title="Result snapshot">
                <div className="result-grid">
                  <StatusPill label="BPM" value={bpm} />
                  <StatusPill label="Key" value={key} />
                  <StatusPill label="Confidence" value={confidence} />
                  <StatusPill label="Output" value={singleResult ? 'Single-track mix' : stemResult ? 'Stem mix' : 'Waiting'} />
                </div>
                {resultMetadata?.output_path ? <div className="path-note">Preview file: {resultMetadata.output_path}</div> : null}
              </Card>
            </Reveal>
          </section>

          <section className="studio-section" id="stems">
            <SectionHeader eyebrow="Stem lab" title="Dedicated section for separation, panning, and stem motion">
              Stem work stays in its own block so separation controls, per-stem routing, and render actions do not overlap the rest of the studio.
            </SectionHeader>

            <Reveal>
              <Card eyebrow="Stem lab" title="Separation, panning, and per-stem motion">
                <div className="section-stack">
                  <p className="section-copy">
                    Demucs separation is exposed as its own section, with selectable models, dedicated panning for every available stem, optional stem EQ, and 8D motion.
                  </p>

                  <div className="control-grid control-grid--two">
                    <Select
                      label="Demucs model"
                      value={stemState.model}
                      options={Object.keys(catalog.stemModels)}
                      onChange={(value) =>
                        setStemState((current) => ({
                          ...current,
                          model: value,
                          selected: catalog.stemModels[value] ?? [],
                        }))
                      }
                      hint="htdemucs_6s includes guitar and piano."
                    />
                    <Range
                      label="8D depth"
                      value={stemState.eightDDepth.toFixed(2)}
                      min={0}
                      max={1}
                      step={0.05}
                      onChange={(value) => setStemState((current) => ({ ...current, eightDDepth: value }))}
                      disabled={!stemState.enable8d}
                    />
                  </div>

                  <div className="toggle-grid">
                    <Toggle
                      label="Subtle 8D motion"
                      checked={stemState.enable8d}
                      onChange={(checked) => setStemState((current) => ({ ...current, enable8d: checked }))}
                      hint="Applies to the stem mix after per-stem panning."
                    />
                    <Toggle
                      label="Stem EQ"
                      checked={stemState.eqEnabled}
                      onChange={(checked) => setStemState((current) => ({ ...current, eqEnabled: checked }))}
                      hint="The same EQ curve is applied to every stem before the final mix."
                    />
                  </div>

                  <div className="stem-list">
                    {availableStems.map((stem) => (
                      <div key={stem} className="stem-card">
                        <label className="stem-card__toggle">
                          <span className="stem-card__icon">{STEM_ICONS[stem] ?? '◉'}</span>
                          <span>
                            <strong>{stem}</strong>
                            <small>Pan this stem independently</small>
                          </span>
                          <input
                            type="checkbox"
                            checked={stemState.selected.includes(stem)}
                            onChange={(event) => {
                              const checked = event.target.checked;
                              setStemState((current) => ({
                                ...current,
                                selected: checked
                                  ? [...current.selected, stem]
                                  : current.selected.filter((name) => name !== stem),
                              }));
                            }}
                          />
                        </label>
                        <Range
                          label="Position"
                          value={(stemState.positions[stem] ?? 0).toFixed(2)}
                          min={-1}
                          max={1}
                          step={0.01}
                          onChange={(value) =>
                            setStemState((current) => ({
                              ...current,
                              positions: {
                                ...current.positions,
                                [stem]: value,
                              },
                            }))
                          }
                          disabled={!stemState.selected.includes(stem)}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            </Reveal>

            <Reveal>
              <Card eyebrow="Action" title="Render the stem mix">
                <div className="summary-stack">
                  <StatusPill label="Model" value={stemState.model} />
                  <StatusPill label="Selected stems" value={stemState.selected.length.toString()} />
                  <StatusPill label="Per-stem EQ" value={stemState.eqEnabled ? stemState.eqPreset : 'Disabled'} />
                  <button className="primary-button" type="button" onClick={processStems} disabled={loading || !audioFile || !stemState.selected.length}>
                    {loading && mode === 'stems' ? 'Separating…' : 'Separate and render stems'}
                  </button>
                </div>
                {mode === 'stems' ? <div className="notice notice--info">{loading ? 'Demucs separation can take several minutes on the first run.' : 'Use this section for the full stem workflow, including per-stem positioning.'}</div> : null}
              </Card>
            </Reveal>
          </section>

          <section className="studio-section" id="equalizer">
            <SectionHeader eyebrow="Equalizer" title="Dedicated section for tonal shaping">
              EQ lives on its own row so the curve editor has room and the controls stay visually separated from playback.
            </SectionHeader>

            <Reveal>
              <EQEditor
                title={mode === 'single' ? 'Single-track equalizer' : 'Stem equalizer'}
                presets={presets}
                bands={bands}
                state={mode === 'single' ? singleState : stemState}
                onChange={mode === 'single' ? setSingleState : setStemState}
                presetLabel="Curve preset"
              />
            </Reveal>
          </section>

          <section className="studio-section" id="separated-stems">
            <SectionHeader eyebrow="Separated stems" title="Dedicated section for stem previews">
              Each rendered stem gets its own preview block, keeping playback clean and scannable after separation completes.
            </SectionHeader>

            <Reveal>
              <Card eyebrow="Separated stems" title="Preview each stem when you run the stem workflow">
                {stemResult ? (
                  <div className="stem-preview-grid">
                    {stemFiles.length ? (
                      stemFiles.map((stemFile) => (
                        <div className="stem-preview-card" key={stemFile.name}>
                          <span>{stemFile.name}</span>
                          <audio controls src={`${API_BASE}${stemFile.previewUrl}`} />
                        </div>
                      ))
                    ) : (
                      <div className="player-empty">No stem previews were returned.</div>
                    )}
                  </div>
                ) : (
                  <div className="player-empty">Stem previews appear here after separation finishes.</div>
                )}
              </Card>
            </Reveal>
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;
