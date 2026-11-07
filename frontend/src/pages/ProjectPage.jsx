import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { api, downloadUrl } from '../api.js'
import { Badge, ErrorBox, Empty, fmtNum, fmtMoney, STATUS_LABELS } from '../components/common.jsx'
import RatiosTab from './tabs/RatiosTab.jsx'
import ForecastTab from './tabs/ForecastTab.jsx'
import TermsTab from './tabs/TermsTab.jsx'
import FoundersTab from './tabs/FoundersTab.jsx'
import RisksTab from './tabs/RisksTab.jsx'
import DocumentsTab from './tabs/DocumentsTab.jsx'
import SummaryTab from './tabs/SummaryTab.jsx'

const TABS = [
  { key: 'general', label: 'Общие сведения' },
  { key: 'companies', label: 'Компании и отчетность' },
  { key: 'forecast', label: 'Доходность проекта' },
  { key: 'terms', label: 'Условия и DSCR' },
  { key: 'founders', label: 'Учредители и проверки' },
  { key: 'risks', label: 'Риски' },
  { key: 'documents', label: 'Документы' },
  { key: 'summary', label: 'Скоринг и резюме' },
]

const STATUS_LABELS_PROJECT = {
  draft: 'черновик',
  review: 'на рассмотрении',
  approved: 'одобрен',
  rejected: 'отклонен',
}

export default function ProjectPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'general'

  const [project, setProject] = useState(null)
  const [error, setError] = useState(null)
  const [editForm, setEditForm] = useState(null)

  const load = useCallback(async () => {
    try {
      setProject(await api.getProject(id))
    } catch (e) {
      setError(e.message)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  function setTab(key) {
    setSearchParams({ tab: key })
  }

  async function saveGeneral(e) {
    e.preventDefault()
    try {
      await api.updateProject(id, editForm)
      setEditForm(null)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function removeProject() {
    if (!window.confirm('Удалить проект вместе со всеми данными?')) return
    try {
      await api.deleteProject(id)
      navigate('/projects')
    } catch (err) {
      setError(err.message)
    }
  }

  if (error && !project) return <ErrorBox error={error} />
  if (!project) return <div className="card">Загрузка…</div>

  return (
    <>
      <div className="btn-row" style={{ justifyContent: 'space-between', marginBottom: 4 }}>
        <div>
          <h1 className="page-title">{project.name}</h1>
          <p className="page-sub">
            {project.borrower || '—'} · {project.industry || '—'} ·{' '}
            <span className={`badge status-${project.status}`}>{STATUS_LABELS_PROJECT[project.status]}</span>
            {project.last_score != null && (
              <> · последний скоринг: <b>{fmtNum(project.last_score, 1)}</b></>
            )}
          </p>
        </div>
        <a className="btn secondary" href="/projects">← К реестру</a>
      </div>

      <ErrorBox error={error} />

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.key} className={'tab' + (tab === t.key ? ' active' : '')} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'general' && (
        <div className="card">
          <h2>Общие сведения</h2>
          {editForm ? (
            <form onSubmit={saveGeneral}>
              <div className="form-grid">
                <div className="field">
                  <label>Название *</label>
                  <input required value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                </div>
                <div className="field">
                  <label>Заемщик / группа</label>
                  <input value={editForm.borrower} onChange={(e) => setEditForm({ ...editForm, borrower: e.target.value })} />
                </div>
                <div className="field">
                  <label>Отрасль</label>
                  <input value={editForm.industry} onChange={(e) => setEditForm({ ...editForm, industry: e.target.value })} />
                </div>
                <div className="field">
                  <label>Цель финансирования</label>
                  <input value={editForm.purpose} onChange={(e) => setEditForm({ ...editForm, purpose: e.target.value })} />
                </div>
                <div className="field">
                  <label>Статус</label>
                  <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                    {Object.entries(STATUS_LABELS_PROJECT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
              </div>
              <div className="field" style={{ marginBottom: 16 }}>
                <label>Описание</label>
                <textarea rows={4} value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
              </div>
              <div className="btn-row">
                <button className="btn">Сохранить</button>
                <button type="button" className="btn secondary" onClick={() => setEditForm(null)}>Отмена</button>
              </div>
            </form>
          ) : (
            <>
              <table>
                <tbody>
                  <tr><th style={{ width: 220 }}>Заемщик / группа</th><td>{project.borrower || '—'}</td></tr>
                  <tr><th>Отрасль</th><td>{project.industry || '—'}</td></tr>
                  <tr><th>Цель финансирования</th><td>{project.purpose || '—'}</td></tr>
                  <tr><th>Описание</th><td className="section-text">{project.description || '—'}</td></tr>
                  <tr><th>Создан</th><td>{project.created_at || '—'}</td></tr>
                  <tr><th>Обновлен</th><td>{project.updated_at || '—'}</td></tr>
                </tbody>
              </table>
              <div className="btn-row" style={{ marginTop: 16 }}>
                <button className="btn secondary" onClick={() => setEditForm({
                  name: project.name, borrower: project.borrower, industry: project.industry,
                  purpose: project.purpose, description: project.description, status: project.status,
                })}>Редактировать</button>
                <button className="btn danger" onClick={removeProject}>Удалить проект</button>
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'companies' && <RatiosTab projectId={id} />}
      {tab === 'forecast' && <ForecastTab projectId={id} />}
      {tab === 'terms' && <TermsTab projectId={id} />}
      {tab === 'founders' && <FoundersTab projectId={id} />}
      {tab === 'risks' && <RisksTab projectId={id} />}
      {tab === 'documents' && <DocumentsTab projectId={id} />}
      {tab === 'summary' && <SummaryTab projectId={id} onUpdated={load} />}
    </>
  )
}
