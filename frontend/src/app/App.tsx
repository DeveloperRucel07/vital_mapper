import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { apiClient } from "../shared/api/client";
import { ApiError } from "../shared/api/errors";
import { beginLogin, getSession, logout, type AuthUser } from "../features/auth/auth";
import {
  buildPatientSearchPayload,
  type PatientSearchCriteria,
} from "../features/patients/patientSearch";
import {
  initialRecorderState,
  recorderReducer,
  type RecorderStatus,
} from "../features/voice/recorderMachine";

type Page = "dashboard" | "patients" | "documentation" | "help";
type AuthView = "checking" | "signed-out" | "signed-in";

const ROLE_LABELS: Record<AuthUser["role"], string> = {
  pflegefachkraft: "Pflegefachkraft",
  schichtleitung: "Schichtleitung",
  administrator: "Administrator",
  qualitaetsverantwortlicher: "Qualitätsverantwortlicher",
  datenschutzbeauftragter: "Datenschutzbeauftragter",
};

function App() {
  const [authView, setAuthView] = useState<AuthView>("checking");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedPatientRef, setSelectedPatientRef] = useState<string | null>(null);

  useEffect(() => {
    getSession(apiClient).then((session) => {
      if (!session.authenticated || !session.user) {
        setAuthView("signed-out");
        return;
      }
      setUser({ id: session.user.subject, displayName: session.user.displayName, role: session.user.role });
      setAuthView("signed-in");
    }).catch(() => setAuthView("signed-out"));
  }, []);

  const handleLogin = useCallback(() => beginLogin(window.location.pathname), []);

  const handleLogout = useCallback(async () => {
    let providerLogoutPath: string | null = null;
    try { providerLogoutPath = await logout(apiClient); } finally {
      apiClient.setCsrfToken(null);
      setUser(null);
      setSelectedPatientRef(null);
      setPage("dashboard");
      setAuthView("signed-out");
    }
    if (providerLogoutPath) window.location.assign(providerLogoutPath);
  }, []);

  if (authView === "checking") return <LoadingScreen label="Sitzung wird geprüft" />;
  if (authView === "signed-out") return <LoginScreen onLogin={handleLogin} />;

  return (
    <div className="app-shell">
      <Sidebar page={page} onNavigate={setPage} onLogout={handleLogout} />
      <main className="main-content">
        <Header user={user} />
        {page === "dashboard" && <Dashboard onNavigate={setPage} />}
        {page === "patients" && (
          <PatientSearchConnected selectedPatientRef={selectedPatientRef} onSelect={setSelectedPatientRef} />
        )}
        {page === "documentation" && (
          <Documentation
            patientRef={selectedPatientRef}
            onChoosePatient={() => setPage("patients")}
            onSelectPatient={setSelectedPatientRef}
          />
        )}
        {page === "help" && <UserGuide />}
      </main>
    </div>
  );
}

function LoadingScreen({ label }: { label: string }) {
  return <div className="loading-screen"><span className="spinner" aria-hidden="true" />{label}</div>;
}

function LoginScreen({ onLogin }: { onLogin: () => void }) {
  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onLogin();
  }

  return (
    <div className="login-layout">
      <section className="login-intro">
        <div className="brand-mark" aria-hidden="true"><span>V</span></div>
        <p className="eyebrow">VITAL MAPPER</p>
        <h1>Dokumentation,<br /><em>die mitdenkt.</em></h1>
        <p className="login-lead">Sprachgestützte Pflege dokumentieren – mit fachlicher Prüfung bei jedem Schritt.</p>
        <div className="principle"><span className="principle-line" /><span>AI proposes · healthcare professional verifies · system persists</span></div>
      </section>
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-panel-inner">
          <p className="eyebrow">SICHERER ARBEITSPLATZ</p>
          <h2 id="login-title">Willkommen zurück</h2>
          <p className="muted">Melden Sie sich sicher über den zentralen Identitätsdienst an.</p>
          <form className="login-form" onSubmit={submit}>
            <button className="button button-primary button-full" type="submit">Mit Keycloak anmelden</button>{/*
              {busy ? <><span className="spinner spinner-light" aria-hidden="true" /> Anmeldung wird geprüft</> : "Anmelden"}
          */}</form>
          <p className="security-note"><span aria-hidden="true">⌁</span> Verschlüsselte Verbindung · Keine Gesundheitsdaten im Browser gespeichert</p>
        </div>
      </section>
    </div>
  );
}

function Sidebar({ page, onNavigate, onLogout }: { page: Page; onNavigate: (page: Page) => void; onLogout: () => void }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand"><div className="brand-mark small" aria-hidden="true"><span>V</span></div><span>Vital Mapper</span></div>
      <div className="sidebar-label">Arbeitsbereich</div>
      <nav aria-label="Hauptnavigation" className="main-nav">
        <NavItem active={page === "dashboard"} label="Übersicht" icon="grid" onClick={() => onNavigate("dashboard")} />
        <NavItem active={page === "patients"} label="Patienten" icon="users" onClick={() => onNavigate("patients")} />
        <NavItem active={page === "documentation"} label="Dokumentation" icon="file" onClick={() => onNavigate("documentation")} />
        <NavItem active={page === "help"} label="Hilfe" icon="help" onClick={() => onNavigate("help")} />
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-label">System</div>
        <NavItem active={false} label="Einstellungen" icon="settings" onClick={() => undefined} disabled />
        <button className="logout-button" onClick={onLogout}><Icon name="logout" /> Abmelden</button>
        <div className="sidebar-status"><span className="status-dot" /> API-Anbindung vorbereitet</div>
      </div>
    </aside>
  );
}

function NavItem({ active, label, icon, onClick, disabled = false }: { active: boolean; label: string; icon: IconName; onClick: () => void; disabled?: boolean }) {
  return <button className={`nav-item ${active ? "active" : ""}`} onClick={onClick} disabled={disabled} aria-current={active ? "page" : undefined}><Icon name={icon} /> <span>{label}</span>{disabled && <span className="nav-soon">bald</span>}</button>;
}

function Header({ user }: { user: AuthUser | null }) {
  return <header className="topbar"><div><p className="topbar-context">Arbeitsbereich / Übersicht</p><p className="topbar-date">Montag, 14. September 2026</p></div><div className="user-chip"><div className="avatar">{user?.role.slice(0, 2).toUpperCase() ?? "VM"}</div><div><strong>{user ? ROLE_LABELS[user.role] : "Benutzer"}</strong><span>Angemeldet</span></div><span className="chevron">⌄</span></div></header>;
}

function Dashboard({ onNavigate }: { onNavigate: (page: Page) => void }) {
  return <div className="page-content">
    <div className="page-heading"><div><p className="eyebrow">ÜBERSICHT</p><h1>Guten Morgen.</h1><p className="muted">Bereit für eine sichere, fokussierte Dokumentation?</p></div><button className="button button-primary" onClick={() => onNavigate("patients")}><span className="button-plus">+</span> Neue Dokumentation</button></div>
    <div className="notice notice-info"><span className="notice-icon">i</span><div><strong>Dokumentationsworkflow verfügbar</strong><p>Nach der Aufnahme können Sie jetzt Upload, Transkript, klinische Informationen, Bericht und manuelle Freigabe durchlaufen.</p></div></div>
    <section className="dashboard-grid" aria-label="Arbeitsübersicht">
      <div className="metric-card"><div className="metric-header"><span>Offene Entwürfe</span><Icon name="file" /></div><strong className="metric-value">—</strong><span className="metric-caption">API noch nicht verfügbar</span></div>
      <div className="metric-card"><div className="metric-header"><span>Heute dokumentiert</span><Icon name="check" /></div><strong className="metric-value">—</strong><span className="metric-caption">API noch nicht verfügbar</span></div>
      <div className="metric-card"><div className="metric-header"><span>Prüfstatus</span><Icon name="shield" /></div><strong className="metric-value">Human-in-the-loop</strong><span className="metric-caption">Freigabe bleibt immer manuell</span></div>
    </section>
    <div className="section-heading"><div><p className="eyebrow">SCHNELLSTART</p><h2>Was möchten Sie tun?</h2></div></div>
    <div className="quick-actions"><ActionCard icon="mic" title="Neue Dokumentation" description="Patient auswählen und Aufnahme starten" onClick={() => onNavigate("patients")} /><ActionCard icon="users" title="Patient suchen" description="Nur mit angebundener Patienten-API" onClick={() => onNavigate("patients")} /></div>
    <div className="section-heading recent-heading"><div><p className="eyebrow">AKTIVITÄT</p><h2>Letzte Dokumentationen</h2></div><span className="muted small-text">Keine Daten geladen</span></div>
    <div className="empty-panel"><Icon name="file" /><div><strong>Noch keine Dokumentationen sichtbar</strong><p>Die Liste wird angezeigt, sobald das Backend eine Draft-Lese-API bereitstellt.</p></div><span className="capability-tag">Backend capability missing</span></div>
  </div>;
}

function ActionCard({ icon, title, description, onClick }: { icon: IconName; title: string; description: string; onClick: () => void }) {
  return <button className="action-card" onClick={onClick}><span className="action-icon"><Icon name={icon} /></span><span><strong>{title}</strong><small>{description}</small></span><span className="arrow">→</span></button>;
}

type PatientSearchResult = { resource?: { id?: string; name?: Array<{ family?: string; given?: string[] }> } };
type PatientSearchBundle = { entry?: PatientSearchResult[] };

function PatientSearchConnected({ selectedPatientRef, onSelect }: { selectedPatientRef: string | null; onSelect: (patientRef: string) => void }) {
  const [criteria, setCriteria] = useState<PatientSearchCriteria>({ given: "", family: "", birthdate: "" });
  const [results, setResults] = useState<PatientSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function search() {
    const payload = buildPatientSearchPayload(criteria);
    if (Object.keys(payload).length === 0) return;
    setBusy(true); setError(null);
    try {
      const response = await apiClient.post<PatientSearchBundle>("/interop/v1/patients/search", payload);
      setResults(response.entry ?? []);
    } catch { setResults([]); setError("Die Patientensuche konnte nicht sicher abgeschlossen werden."); }
    finally { setBusy(false); }
  }

  const updateCriteria = (field: keyof PatientSearchCriteria, value: string) => {
    setCriteria((current) => ({ ...current, [field]: value }));
  };
  const hasCriteria = Object.keys(buildPatientSearchPayload(criteria)).length > 0;

  return <div className="page-content narrow-content">
    <div className="page-heading"><div><p className="eyebrow">PATIENTENKONTEXT</p><h1>Patient auswählen</h1><p className="muted">Prüfen Sie den Patientenkontext vor jeder Dokumentation.</p></div></div>
    <div className="patient-safety-banner"><Icon name="shield" /><div><strong>Patientensicherheit</strong><p>Der aktuelle Patient bleibt während des gesamten Workflows sichtbar. Ein Wechsel erfolgt nie automatisch.</p></div></div>
    <section className="search-panel"><div className="search-fields">
      <div className="search-field"><label htmlFor="patient-given">Vorname</label><input id="patient-given" value={criteria.given} onChange={(event) => updateCriteria("given", event.target.value)} autoComplete="off" /></div>
      <div className="search-field"><label htmlFor="patient-family">Nachname</label><input id="patient-family" value={criteria.family} onChange={(event) => updateCriteria("family", event.target.value)} autoComplete="off" /></div>
      <div className="search-field"><label htmlFor="patient-birthdate">Geburtsdatum</label><input id="patient-birthdate" type="date" value={criteria.birthdate} onChange={(event) => updateCriteria("birthdate", event.target.value)} /></div>
    </div><div className="search-actions"><div className="search-input"><Icon name="search" /><span>Patientensuche</span></div><button className="button button-primary" onClick={search} disabled={busy || !hasCriteria}>{busy ? "Suche…" : "Patienten suchen"}</button></div><p className="field-hint">Sie können nach Vorname, Nachname, Geburtsdatum oder einer Kombination suchen. Die Treffer stammen ausschließlich vom berechtigten Gateway.</p>{error && <div className="alert alert-error" role="alert">{error}</div>}</section>
    {selectedPatientRef && <div className="selected-patient"><span className="status-dot" /><div><small>Aktuell ausgewählt</small><strong>{selectedPatientRef}</strong></div></div>}
    {results.length > 0 && <div className="patient-results">{results.map((entry) => { const patient = entry.resource; const id = patient?.id; if (!id) return null; const name = patient.name?.[0]; const displayName = [...(name?.given ?? []), name?.family].filter(Boolean).join(" "); return <button className="selected-patient" key={id} onClick={() => onSelect(id)}><div><small>{displayName || "Patient"}</small><strong>{id}</strong></div></button>; })}</div>}
  </div>;
}

type TranscriptResponse = {
  id: string;
  recording_id: string;
  text: string;
  confidence: number;
  whisper_version: string;
};

type DraftResponse = {
  id: string;
  extraction_id: string;
  report_text: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type ExtractionResponse = {
  id: string;
  transcript_id: string;
  data: Record<string, unknown>;
  ollama_version: string;
  draft: DraftResponse | null;
};

type ExtractionUpdateResponse = {
  id: string;
  transcript_id: string;
  data: Record<string, unknown>;
  ollama_version: string;
};

type ApprovalResponse = {
  submission_status: "submitted" | "failed";
  monitoring_resource_id?: string;
};

type TranscriptWorkspaceItem = {
  transcript: TranscriptResponse;
  patient_ref: string;
  recording_started_at: string;
  extraction: Omit<ExtractionResponse, "draft"> | null;
  draft: DraftResponse | null;
};

type TranscriptWorkspaceResponse = {
  day: string;
  items: TranscriptWorkspaceItem[];
};

function Documentation({
  patientRef,
  onChoosePatient,
  onSelectPatient,
}: {
  patientRef: string | null;
  onChoosePatient: () => void;
  onSelectPatient: (patientRef: string) => void;
}) {
  const [step, setStep] = useState(1);
  const [recorder, dispatch] = useReducer(recorderReducer, initialRecorderState);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [recordingStartedAt, setRecordingStartedAt] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResponse | null>(null);
  const [extractionJson, setExtractionJson] = useState("");
  const [draft, setDraft] = useState<DraftResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [approved, setApproved] = useState(false);
  const [submissionStatus, setSubmissionStatus] = useState<ApprovalResponse["submission_status"] | null>(null);
  const [savedTranscripts, setSavedTranscripts] = useState<TranscriptWorkspaceItem[]>([]);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [workspaceDay, setWorkspaceDay] = useState(() => new Date().toISOString().slice(0, 10));
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    if (recorder.status !== "recording") return;
    const interval = window.setInterval(() => dispatch({ type: "tick" }), 1000);
    return () => window.clearInterval(interval);
  }, [recorder.status]);

  useEffect(() => () => {
    stream.current?.getTracks().forEach((track) => track.stop());
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  const loadSavedTranscripts = useCallback(async () => {
    setHistoryBusy(true);
    try {
      const response = await apiClient.get<TranscriptWorkspaceResponse>(`/transcripts/workspace?day=${workspaceDay}`);
      setSavedTranscripts(response.items);
    } catch {
      setSavedTranscripts([]);
    } finally {
      setHistoryBusy(false);
    }
  }, [workspaceDay]);

  useEffect(() => {
    void loadSavedTranscripts();
  }, [loadSavedTranscripts]);

  function resetWorkflow() {
    if (mediaRecorder.current?.state !== "inactive") mediaRecorder.current?.stop();
    stream.current?.getTracks().forEach((track) => track.stop());
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
    setAudioBlob(null);
    setRecordingStartedAt(null);
    setTranscript(null);
    setExtraction(null);
    setExtractionJson("");
    setDraft(null);
    setApproved(false);
    setSubmissionStatus(null);
    setWorkflowError(null);
    setStep(1);
    chunks.current = [];
    dispatch({ type: "discard" });
  }

  function openSavedTranscript(item: TranscriptWorkspaceItem) {
    onSelectPatient(item.patient_ref);
    setTranscript(item.transcript);
    setExtraction(
      item.extraction
        ? { ...item.extraction, draft: item.draft }
        : null,
    );
    setExtractionJson(item.extraction ? JSON.stringify(item.extraction.data, null, 2) : "");
    setDraft(item.draft);
    setApproved(false);
    setSubmissionStatus(null);
    setWorkflowError(null);
    setStep(item.extraction ? (item.draft ? 4 : 3) : 2);
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia) {
      dispatch({ type: "error", message: "Dieser Browser unterstützt keinen Mikrofonzugriff." });
      return;
    }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks.current = [];
      const recorderInstance = new MediaRecorder(stream.current);
      recorderInstance.ondataavailable = (event) => { if (event.data.size > 0) chunks.current.push(event.data); };
      recorderInstance.onstop = () => {
        const blob = new Blob(chunks.current, { type: recorderInstance.mimeType || "audio/webm" });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        stream.current?.getTracks().forEach((track) => track.stop());
      };
      mediaRecorder.current = recorderInstance;
      recorderInstance.start();
      setRecordingStartedAt(new Date().toISOString());
      setWorkflowError(null);
      setTranscript(null); setExtraction(null); setExtractionJson(""); setDraft(null); setApproved(false); setStep(1);
      dispatch({ type: "start" });
    } catch {
      dispatch({ type: "error", message: "Mikrofonzugriff wurde nicht erteilt. Bitte prüfen Sie die Browser-Berechtigung." });
    }
  }

  function pauseRecording() { mediaRecorder.current?.pause(); dispatch({ type: "pause" }); }
  function resumeRecording() { mediaRecorder.current?.resume(); dispatch({ type: "resume" }); }
  function stopRecording() { if (mediaRecorder.current?.state !== "inactive") mediaRecorder.current?.stop(); dispatch({ type: "stop" }); }
  function discardRecording() {
    if (mediaRecorder.current?.state !== "inactive") mediaRecorder.current?.stop();
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
    setAudioBlob(null);
    setRecordingStartedAt(null);
    setWorkflowError(null);
    setTranscript(null); setExtraction(null); setExtractionJson(""); setDraft(null); setApproved(false); setStep(1);
    chunks.current = [];
    dispatch({ type: "discard" });
  }

  async function uploadAndTranscribe() {
    if (!audioBlob || !recordingStartedAt) return;
    setBusy(true); setWorkflowError(null);
    try {
      const form = new FormData();
      form.append("patient_ref", patientRef ?? "");
      form.append("started_at", recordingStartedAt);
      form.append("audio", audioBlob, "recording.webm");
      const recording = await apiClient.postFormData<{ id: string }>("/recordings", form);
      const nextTranscript = await apiClient.post<TranscriptResponse>(`/recordings/${recording.id}/transcribe`, {});
      setTranscript(nextTranscript);
      await loadSavedTranscripts();
      setStep(2);
    } catch {
      setWorkflowError("Upload oder Transkription konnte nicht abgeschlossen werden. Bitte versuchen Sie es erneut.");
    } finally { setBusy(false); }
  }

  async function extractTranscript() {
    if (!transcript) return;
    setBusy(true); setWorkflowError(null);
    try {
      const nextExtraction = await apiClient.post<ExtractionResponse>(`/transcripts/${transcript.id}/extract`, { text: transcript.text });
      setExtraction(nextExtraction);
      setExtractionJson(JSON.stringify(nextExtraction.data, null, 2));
      setDraft(nextExtraction.draft);
      await loadSavedTranscripts();
      setStep(3);
    } catch {
      setWorkflowError("Die klinische Extraktion konnte nicht abgeschlossen werden. Prüfen Sie das Transkript und versuchen Sie es erneut.");
    } finally { setBusy(false); }
  }

  async function saveExtractionAndContinue() {
    if (!extraction) return;
    let data: unknown;
    try {
      data = JSON.parse(extractionJson);
    } catch {
      setWorkflowError("Das JSON ist ungültig. Bitte prüfen Sie Syntax und Anführungszeichen.");
      return;
    }
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      setWorkflowError("Die klinische Extraktion muss ein JSON-Objekt sein.");
      return;
    }
    setBusy(true); setWorkflowError(null);
    try {
      const updated = await apiClient.patch<ExtractionUpdateResponse>(`/extractions/${extraction.id}`, { data });
      setExtraction({ ...extraction, data: updated.data });
      setExtractionJson(JSON.stringify(updated.data, null, 2));
      await loadSavedTranscripts();
      setStep(4);
    } catch (error) {
      setWorkflowError(error instanceof ApiError ? `Die JSON-Korrektur konnte nicht gespeichert werden: ${error.message}` : "Die JSON-Korrektur konnte nicht gespeichert werden. Bitte prüfen Sie Feldnamen und Datentypen.");
    } finally { setBusy(false); }
  }

  async function saveDraftAndReview() {
    if (!draft) return;
    setBusy(true); setWorkflowError(null);
    try {
      const nextDraft = await apiClient.patch<DraftResponse>(`/drafts/${draft.id}`, { report_text: draft.report_text });
      setDraft(nextDraft); setStep(5);
    } catch {
      setWorkflowError("Der Bericht konnte nicht gespeichert werden.");
    } finally { setBusy(false); }
  }

  async function approveDraft() {
    if (!draft || !transcript || !extraction) return;
    setBusy(true); setWorkflowError(null);
    try {
      const response = await apiClient.post<ApprovalResponse>(`/drafts/${draft.id}/approve`, { model_versions: { whisper: transcript.whisper_version, ollama: extraction.ollama_version } });
      setApproved(true);
      setSubmissionStatus(response.submission_status);
      await loadSavedTranscripts();
    } catch {
      setWorkflowError("Die Freigabe konnte nicht abgeschlossen werden.");
    } finally { setBusy(false); }
  }

  return <div className="page-content documentation-page">
    <SavedTranscriptsPanel day={workspaceDay} items={savedTranscripts} busy={historyBusy} onDayChange={setWorkspaceDay} onOpen={openSavedTranscript} />
    {!patientRef ? <div className="locked-workflow"><Icon name="lock" /><h2>Patientenkontext erforderlich</h2><p>Wählen Sie zuerst einen Patienten aus. Eine neue Aufnahme ohne sichtbaren Patientenkontext ist nicht zulässig.</p><button className="button button-primary" onClick={onChoosePatient}>Patient auswählen</button></div> : <>
    <div className="patient-context-bar"><div><small>AKTUELLER PATIENT</small><strong>{patientRef}</strong></div><button className="text-button" onClick={onChoosePatient}>Patient wechseln</button></div>
    <div className="page-heading compact-heading"><div><p className="eyebrow">DOKUMENTATION STARTEN</p><h1>Neue Pflegedokumentation</h1><p className="muted">Der Vorschlag bleibt bis zur fachlichen Freigabe ein Entwurf.</p></div><span className="draft-status"><span className="status-dot amber" /> Entwurf</span></div>
    <div className="stepper" aria-label="Dokumentationsschritte">{["Aufnahme", "Transkript", "Klinische Informationen", "Bericht", "Prüfen & Freigeben"].map((label, index) => <button key={label} className={`step ${index + 1 === step ? "current" : ""} ${index + 1 < step ? "complete" : ""}`} onClick={() => index + 1 <= step && setStep(index + 1)} disabled={index + 1 > step}><span>{index + 1 < step ? "✓" : index + 1}</span>{label}</button>)}</div>
    {workflowError && <div className="alert alert-error workflow-alert" role="alert">{workflowError}</div>}
    {step === 1 && <section className="recorder-panel"><div className="section-heading"><div><p className="eyebrow">SCHRITT 1 VON 5</p><h2>Sprache aufnehmen</h2></div><span className={`recording-state ${recorder.status}`}><span className="recording-dot" /> {recorderStatusLabel(recorder.status)}</span></div><div className="recorder-stage"><div className={`mic-ring ${recorder.status === "recording" ? "is-recording" : ""}`}><Icon name="mic" /></div><strong className="duration">{formatDuration(recorder.durationSeconds)}</strong><span className="muted">{recorder.status === "idle" ? "Bereit für die Aufnahme" : "Aufnahme bleibt bis zum Upload temporär im Arbeitsspeicher"}</span></div>{recorder.error && <div className="alert alert-error" role="alert">{recorder.error}</div>}<div className="recorder-controls">{recorder.status === "idle" || recorder.status === "error" ? <button className="button button-record" onClick={startRecording}><Icon name="mic" /> Aufnahme starten</button> : recorder.status === "recording" ? <><button className="button button-secondary" onClick={pauseRecording}><Icon name="pause" /> Pausieren</button><button className="button button-record" onClick={stopRecording}><span className="stop-square" /> Stoppen</button></> : recorder.status === "paused" ? <><button className="button button-primary" onClick={resumeRecording}><Icon name="play" /> Fortsetzen</button><button className="button button-record" onClick={stopRecording}><span className="stop-square" /> Stoppen</button></> : <><button className="button button-secondary" onClick={discardRecording}>Verwerfen</button>{audioUrl && <audio controls src={audioUrl} aria-label="Aufnahme abspielen" />}<button className="button button-primary" onClick={uploadAndTranscribe} disabled={busy || !audioBlob}>{busy ? "Upload läuft …" : "Upload & weiter"}</button></>}</div>{recorder.status === "stopped" && <div className="notice notice-info" role="status"><span className="notice-icon">i</span><div><strong>Aufnahme beendet</strong><p>Hören Sie die Aufnahme bei Bedarf noch einmal an. Mit „Upload & weiter“ wird sie geschützt gespeichert und zur Transkription weitergeleitet.</p></div></div>}<div className="recorder-footnote"><span className="status-dot" /> Mikrofon wird nur nach Ihrer ausdrücklichen Aktion aktiviert <span className="divider" /> <span className="muted">Keine Speicherung in localStorage, sessionStorage oder IndexedDB</span></div></section>}
    {step === 2 && transcript && <section className="review-panel"><WorkflowHeading step="2" title="Transkript prüfen" /><p className="muted">Korrigieren Sie nur erkennbare Transkriptionsfehler. Die klinische Extraktion verwendet genau diesen Text.</p><textarea className="review-textarea" value={transcript.text} onChange={(event) => setTranscript({ ...transcript, text: event.target.value })} aria-label="Transkript" /><div className="workflow-actions"><button className="button button-secondary" onClick={resetWorkflow}>Abbrechen &amp; später fortsetzen</button><button className="button button-primary" onClick={extractTranscript} disabled={busy}>{busy ? "Extraktion läuft …" : "Weiter zur klinischen Extraktion"}</button></div></section>}
    {step === 3 && extraction && <section className="review-panel"><WorkflowHeading step="3" title="Klinische Informationen prüfen" /><p className="muted">Dev-Modus: Sie können die strukturierte JSON-Extraktion direkt korrigieren. Die Änderung wird vor dem Bericht gespeichert.</p><textarea className="review-textarea json-editor" value={extractionJson} onChange={(event) => setExtractionJson(event.target.value)} aria-label="Klinische Extraktion als JSON" spellCheck={false} /><div className="workflow-actions"><button className="button button-secondary" onClick={resetWorkflow}>Abbrechen &amp; später fortsetzen</button><button className="button button-primary" onClick={saveExtractionAndContinue} disabled={busy}>{busy ? "JSON wird gespeichert …" : "JSON speichern und weiter"}</button></div></section>}
    {step === 4 && draft && <section className="review-panel"><WorkflowHeading step="4" title="Bericht bearbeiten" /><p className="muted">Der Bericht bleibt bis zur manuellen Freigabe ein Entwurf.</p><textarea className="review-textarea report-textarea" value={draft.report_text} onChange={(event) => setDraft({ ...draft, report_text: event.target.value })} aria-label="Pflegebericht-Entwurf" /><div className="workflow-actions"><button className="button button-secondary" onClick={resetWorkflow}>Abbrechen &amp; später fortsetzen</button><button className="button button-primary" onClick={saveDraftAndReview} disabled={busy}>{busy ? "Speichern läuft …" : "Weiter zur Freigabe"}</button></div></section>}
    {step === 5 && draft && <section className="review-panel"><WorkflowHeading step="5" title="Prüfen & freigeben" /><p className="muted">Lesen Sie den vollständigen Bericht vor der Freigabe sorgfältig durch.</p><div className="report-preview">{draft.report_text}</div>{approved ? <div className="notice notice-info" role="status"><span className="notice-icon">✓</span><div><strong>Dokumentation freigegeben</strong><p>{submissionStatus === "submitted" ? "Die Dokumentation wurde freigegeben und an das Pflege-Monitoring zur Speicherung weitergeleitet." : "Die Dokumentation wurde freigegeben, konnte aber noch nicht an das Pflege-Monitoring übertragen werden. Bitte prüfen Sie die Backend-Logs."}</p></div></div> : <div className="workflow-actions"><button className="button button-secondary" onClick={resetWorkflow}>Abbrechen &amp; später fortsetzen</button><button className="button button-primary" onClick={approveDraft} disabled={busy}>{busy ? "Freigabe läuft …" : "Manuell freigeben"}</button></div>}</section>}
    </>}
  </div>;
}

function SavedTranscriptsPanel({
  day,
  items,
  busy,
  onDayChange,
  onOpen,
}: {
  day: string;
  items: TranscriptWorkspaceItem[];
  busy: boolean;
  onDayChange: (day: string) => void;
  onOpen: (item: TranscriptWorkspaceItem) => void;
}) {
  return <section className="saved-transcripts" aria-labelledby="saved-transcripts-title">
    <div className="section-heading"><div><p className="eyebrow">ARBEITSLISTE</p><h2 id="saved-transcripts-title">Offene Transkripte</h2></div><div className="saved-transcript-filter"><label htmlFor="workspace-day">Tag</label><input id="workspace-day" type="date" value={day} onChange={(event) => onDayChange(event.target.value)} /><span className="muted small-text">{busy ? "Wird geladen …" : `${items.length} offen`}</span></div></div>
    <p className="muted saved-transcripts-intro">Transkripte werden nach dem Upload automatisch gespeichert. Sie können die Bearbeitung später fortsetzen und erst danach freigeben.</p>
    {items.length === 0 && !busy ? <div className="empty-panel compact-empty"><Icon name="file" /><div><strong>Keine offenen Transkripte</strong><p>Nach dem nächsten Upload erscheint der Arbeitsstand hier.</p></div></div> : <div className="saved-transcript-list">{items.map((item) => {
      const status = item.draft ? "Bericht bereit" : item.extraction ? "Klinische Informationen offen" : "Transkript offen";
      return <article className="saved-transcript-item" key={item.transcript.id}><div className="saved-transcript-meta"><strong>{new Date(item.recording_started_at).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })} Uhr</strong><span>{item.patient_ref}</span><small>{status}</small></div><p>{item.transcript.text.slice(0, 180)}{item.transcript.text.length > 180 ? " …" : ""}</p><button className="button button-secondary" onClick={() => onOpen(item)}>Öffnen</button></article>;
    })}</div>}
  </section>;
}

function WorkflowHeading({ step, title }: { step: string; title: string }) {
  return <div className="section-heading"><div><p className="eyebrow">SCHRITT {step} VON 5</p><h2>{title}</h2></div></div>;
}

function UserGuide() {
  return <div className="page-content guide-page">
    <div className="page-heading"><div><p className="eyebrow">HILFE</p><h1>Benutzeranleitung</h1><p className="muted">Die wichtigsten Schritte für eine sichere Dokumentation.</p></div></div>
    <div className="notice notice-info"><span className="notice-icon">i</span><div><strong>Der vollständige Ablauf ist verfügbar</strong><p>Nach dem Stoppen laden Sie die Aufnahme hoch. Das Transkript wird für heute gespeichert und kann später weiterbearbeitet und manuell freigegeben werden.</p></div></div>
    <div className="guide-grid">
      <GuideCard number="1" title="Patient auswählen">Öffnen Sie „Patienten“, suchen Sie nach Vorname, Nachname oder Geburtsdatum und wählen Sie den gewünschten Treffer aus. Der Patientenkontext bleibt während der Dokumentation sichtbar.</GuideCard>
      <GuideCard number="2" title="Aufnahme erstellen">Öffnen Sie „Dokumentation“ und wählen Sie „Aufnahme starten“. Sie können pausieren, fortsetzen und anschließend stoppen. Prüfen Sie die Aufnahme vor dem Verwerfen.</GuideCard>
      <GuideCard number="3" title="Upload und Transkript">Klicken Sie nach dem Stoppen auf „Upload & weiter“. Das Transkript erscheint danach unter „Offene Transkripte“ und bleibt dort bis zur Freigabe gespeichert.</GuideCard>
      <GuideCard number="4" title="Später fortsetzen oder freigeben">Öffnen Sie einen gespeicherten Eintrag jederzeit wieder. Mit „Abbrechen & später fortsetzen“ verlassen Sie den aktuellen Schritt, ohne den Arbeitsstand zu löschen. Erst „Manuell freigeben“ schließt die Dokumentation ab.</GuideCard>
    </div>
    <section className="guide-safety"><Icon name="shield" /><div><strong>Patientensicherheit</strong><p>Die Audioaufnahme bleibt bis zum Upload nur temporär im Arbeitsspeicher. Nach erfolgreichem Upload wird das Transkript geschützt gespeichert; die Freigabe bleibt immer manuell.</p></div></section>
  </div>;
}

function GuideCard({ number, title, children }: { number: string; title: string; children: string }) {
  return <article className="guide-card"><span className="guide-number">{number}</span><div><h2>{title}</h2><p>{children}</p></div></article>;
}

function recorderStatusLabel(status: RecorderStatus): string {
  return { idle: "Bereit", recording: "Aufnahme läuft", paused: "Aufnahme pausiert", stopped: "Aufnahme beendet", error: "Mikrofonfehler" }[status];
}

function formatDuration(seconds: number): string { return `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`; }

type IconName = "grid" | "users" | "file" | "settings" | "logout" | "check" | "shield" | "mic" | "search" | "lock" | "pause" | "play" | "help";

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, string> = useMemo(() => ({
    grid: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    users: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
    file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h6",
    settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-1.4 1.4-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V20h-2v-.5a1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-1.4-1.4.06-.06A1.7 1.7 0 0 0 9.6 15a1.7 1.7 0 0 0-1.56-1.03H7v-2h.5A1.7 1.7 0 0 0 9.06 11a1.7 1.7 0 0 0-.34-1.88l-.06-.06 1.4-1.4.06.06A1.7 1.7 0 0 0 12 8.06V7.5h2v.56a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 1.4 1.4-.06.06A1.7 1.7 0 0 0 18.94 13h.56v2h-.56a1.7 1.7 0 0 0-1.54 0z",
    logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
    check: "M20 6 9 17l-5-5",
    shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM9 12l2 2 4-4",
    mic: "M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3zM19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8",
    search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.35-4.35",
    lock: "M5 11h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2zM7 11V7a5 5 0 0 1 10 0v4",
    pause: "M6 4h4v16H6zM14 4h4v16h-4z",
    play: "m8 5 11 7-11 7V5z",
    help: "M9.5 9a2.5 2.5 0 1 1 4.2 1.8c-.8.7-1.7 1.1-1.7 2.7M12 17h.01",
  }), []);
  return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}

export { App };
