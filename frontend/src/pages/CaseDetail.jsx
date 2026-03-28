import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Send, ChevronUp, ChevronDown, FileText } from 'lucide-react'
import { fetchCase, fetchEscalationPath, draftComplaint, escalateCase, resolveCase } from '../api'
import { useWallet } from '../context/WalletContext'
import StatusBadge from '../components/StatusBadge'

const TIER_LABELS = {
  US: ['Company Internal', 'CFPB / State AG', 'OCC / FDIC / FRB', 'Small Claims / Federal Court'],
  EU: ['Company Internal', 'National ADR / EU ODR', 'National Consumer Authority', 'National Court / CJEU'],
}

export default function CaseDetail() {
  const { id } = useParams()
  const { role } = useWallet()
  const isAdmin = role === 'admin'
  const [c, setCase] = useState(null)
  const [path, setPath] = useState(null)
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState('')
  const [resolveForm, setResolveForm] = useState({ note: '', amount: '0' })
  const [showComplaints, setShowComplaints] = useState(true)

  const load = async () => {
    setLoading(true)
    const [caseData, pathData] = await Promise.all([
      fetchCase(id),
      fetchEscalationPath(id),
    ])
    setCase(caseData)
    setPath(pathData)
    setLoading(false)
  }

  useEffect(() => { load() }, [id])

  const handleDraft = async () => {
    setActing('draft')
    await draftComplaint(id)
    await load()
    setActing('')
  }

  const handleEscalate = async () => {
    setActing('escalate')
    await escalateCase(id)
    await load()
    setActing('')
  }

  const handleResolve = async (e) => {
    e.preventDefault()
    setActing('resolve')
    await resolveCase(id, resolveForm)
    await load()
    setActing('')
  }

  if (loading) {
    return (
      <div className="min-h-screen grid-bg flex items-center justify-center">
        <RefreshCw className="w-5 h-5 text-muted animate-spin" />
      </div>
    )
  }

  if (!c) {
    return (
      <div className="min-h-screen grid-bg flex items-center justify-center">
        <p className="text-ghost text-sm">Case not found.</p>
      </div>
    )
  }

  const complaints = c.complaints || []
  const analyses = c.response_analyses || []
  const tierLabels = TIER_LABELS[c.jurisdiction] || TIER_LABELS.US

  return (
    <div className="min-h-screen grid-bg">
      {/* Top bar */}
      <div className="sticky top-0 z-40 border-b border-edge bg-void/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 h-14">
          <div className="flex items-center gap-3">
            <Link to="/incidents" className="text-ghost hover:text-signal transition-colors">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <span className="text-sm font-bold text-signal">Case #{c.id}</span>
            <StatusBadge status={c.status} />
          </div>
          {c.status !== 'resolved' && isAdmin && (
            <div className="flex items-center gap-2">
              <button onClick={handleDraft} disabled={!!acting} className="btn-ghost text-xs flex items-center gap-1.5">
                <FileText className="w-3 h-3" />
                {acting === 'draft' ? 'Drafting...' : 'Draft Complaint'}
              </button>
              <button onClick={handleEscalate} disabled={!!acting} className="btn-primary text-xs flex items-center gap-1.5">
                <ChevronUp className="w-3.5 h-3.5" />
                {acting === 'escalate' ? 'Escalating...' : 'Escalate'}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="px-6 py-6 max-w-[1200px] mx-auto">
        {/* Case header card */}
        <div className="card p-6 mb-5">
          <h2 className="text-lg font-bold text-signal mb-2">
            {c.violation_type?.replace(/_/g, ' ')}
          </h2>
          <p className="text-sm text-ghost leading-relaxed mb-5">{c.description}</p>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-4">
            <MetaItem label="Case ID" value={`#${c.id}`} />
            <MetaItem label="Jurisdiction" value={c.jurisdiction} />
            <MetaItem label="Current Tier" value={`${c.current_tier} — ${tierLabels[c.current_tier] || '?'}`} />
            <MetaItem label="Amount" value={c.amount_disputed || 0} />
            <MetaItem label="Severity" value={`${c.severity || '?'} / 5`} />
            <MetaItem label="Status" value={c.status} />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* LEFT — Timeline + Resolve */}
          <div className="space-y-5">
            {/* Escalation timeline */}
            {path?.path && (
              <div className="card p-6">
                <h3 className="text-sm font-bold text-signal mb-5">Escalation Path</h3>
                <div className="relative pl-6">
                  <div className="absolute left-[7px] top-1 bottom-1 w-px bg-edge" />
                  {path.path.map((step, i) => (
                    <div key={i} className="relative pb-6 last:pb-0">
                      <div className={`absolute left-[-19px] top-1 w-3 h-3 rounded-full border-2 ${
                        step.status === 'completed' ? 'bg-valid border-valid' :
                        step.status === 'current' ? 'bg-acid border-acid' :
                        'bg-void border-edge'
                      }`} />
                      <div className="text-sm font-semibold text-signal">
                        Tier {step.tier}: {step.body}
                      </div>
                      <div className="font-mono text-[11px] text-muted mt-0.5">
                        Deadline: {step.deadline_days} days · {step.status}
                      </div>
                    </div>
                  ))}
                </div>

                {path.history?.length > 0 && (
                  <>
                    <div className="h-px bg-edge my-4" />
                    <div className="font-mono text-[11px] text-muted">
                      {path.history.map((h, i) => (
                        <div key={i} className="py-1">
                          {h.from_body} → {h.to_body}{h.reason ? `: ${h.reason}` : ''}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Resolve form or resolution */}
            {c.status !== 'resolved' && isAdmin ? (
              <div className="card p-6">
                <h3 className="text-sm font-bold text-signal mb-4">Resolve Case</h3>
                <form onSubmit={handleResolve}>
                  <div className="mb-3">
                    <label className="label-field">Resolution Note</label>
                    <textarea className="input-field min-h-[80px] resize-y" placeholder="Describe how the case was resolved..."
                      required value={resolveForm.note} onChange={e => setResolveForm({...resolveForm, note: e.target.value})} />
                  </div>
                  <div className="mb-4">
                    <label className="label-field">Amount Recovered</label>
                    <input type="number" className="input-field" min="0"
                      value={resolveForm.amount} onChange={e => setResolveForm({...resolveForm, amount: e.target.value})} />
                  </div>
                  <button type="submit" className="btn-primary text-xs w-full" disabled={!!acting}>
                    {acting === 'resolve' ? 'Resolving...' : 'Mark as Resolved'}
                  </button>
                </form>
              </div>
            ) : c.status === 'resolved' ? (
              <div className="card p-6">
                <h3 className="text-sm font-bold text-valid mb-3">Resolution</h3>
                <p className="text-sm text-ghost leading-relaxed">{c.resolution_note || 'No note'}</p>
                <div className="font-mono text-xs text-muted mt-3">
                  Amount recovered: <span className="text-valid font-medium">{c.amount_recovered || 0}</span>
                </div>
              </div>
            ) : null}
          </div>

          {/* RIGHT — Complaints + Analyses */}
          <div className="space-y-5">
            <div className="card">
              <button
                onClick={() => setShowComplaints(!showComplaints)}
                className="w-full flex items-center justify-between px-6 py-4 hover:bg-surface/50 transition-colors"
              >
                <h3 className="text-sm font-bold text-signal">
                  Complaints <span className="text-muted font-normal ml-1">({complaints.length})</span>
                </h3>
                {showComplaints ? <ChevronUp className="w-4 h-4 text-muted" /> : <ChevronDown className="w-4 h-4 text-muted" />}
              </button>

              {showComplaints && (
                <div className="px-6 pb-6">
                  {complaints.length === 0 ? (
                    <div className="text-center py-6">
                      <FileText className="w-6 h-6 text-edge mx-auto mb-2" />
                      <p className="font-mono text-xs text-muted">No complaints drafted yet.</p>
                      {c.status !== 'resolved' && (
                        <button onClick={handleDraft} disabled={!!acting} className="btn-ghost text-xs mt-3">
                          Draft First Complaint
                        </button>
                      )}
                    </div>
                  ) : (
                    complaints.map((comp, i) => (
                      <div key={i} className={`${i > 0 ? 'mt-5 pt-5 border-t border-edge' : ''}`}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="inline-flex items-center justify-center w-6 h-6 bg-signal text-void rounded-sm font-mono text-xs font-bold">
                            {comp.tier}
                          </span>
                          <span className="text-sm font-semibold text-signal">{comp.subject || 'Untitled'}</span>
                        </div>
                        <div className="bg-void border border-edge rounded-sm p-4 max-h-[300px] overflow-y-auto">
                          <p className="font-mono text-xs text-ghost whitespace-pre-wrap leading-relaxed">
                            {comp.body}
                          </p>
                        </div>
                        {comp.legal_clauses_cited?.length > 0 && (
                          <div className="font-mono text-[11px] text-muted mt-2">
                            Legal: {comp.legal_clauses_cited.join(', ')}
                          </div>
                        )}
                        {comp.remedy_sought && (
                          <div className="font-mono text-[11px] text-muted mt-1">
                            Remedy: {comp.remedy_sought}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Response analyses */}
            {analyses.length > 0 && (
              <div className="card p-6">
                <h3 className="text-sm font-bold text-signal mb-4">Response Analyses</h3>
                {analyses.map((ra, i) => (
                  <div key={i} className={`${i > 0 ? 'mt-4 pt-4 border-t border-edge' : ''}`}>
                    <div className="text-sm font-semibold text-signal mb-1">
                      Recommendation: <span className="text-acid">{ra.recommendation}</span>
                    </div>
                    <div className="font-mono text-[11px] text-muted">
                      Acknowledged: {ra.acknowledged} · Remedy: {ra.remedy_offered} · Adequate: {ra.remedy_adequate}
                    </div>
                    <div className="font-mono text-[11px] text-ghost mt-1">{ra.summary}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function MetaItem({ label, value }) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-widest text-muted mb-1">{label}</div>
      <div className="text-sm font-semibold text-signal">{value}</div>
    </div>
  )
}
