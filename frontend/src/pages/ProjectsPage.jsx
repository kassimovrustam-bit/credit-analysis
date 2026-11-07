import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { Badge, ErrorBox, Empty, fmtNum } from '../components/common.jsx'

const STATUS_LABELS = {
  draft: 'черновик',
  review: 'на рассмотрении',
  approved: 'одобрен',
  rejected: 'отклонен',
}

const EMPTY_FORM = { name: '', borrower: '', industry: '', purpose: '', description: '', status: 'draft' }

export default function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)

  async function load() {
    try {
      setProjects(await api.listProjects())
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => { load() }, [])

  async function submit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.createProject(form)
      setForm(EMPTY_FORM)
      setShowForm(false)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="btn-row" style={{ justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h1 className="page-title">Реестр проектов</h1>
          <p className="page-sub">Проекты финансирования групп компаний</p>
        </div>
        <button className="btn" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Отмена' : 'Новый проект'}
        </button>
      </div>

      <ErrorBox error={error} />

      {showForm && (
        <div className="card">
          <h2>Новый проект</h2>
          <form onSubmit={submit}>
            <div className="form-grid">
              <div className="field">
                <label>Название проекта *</label>
                <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="field">
                <label>Заемщик / группа</label>
                <input value={form.borrower} onChange={(e) => setForm({ ...form, borrower: e.target.value })} />
              </div>
              <div className="field">
                <label>Отрасль</label>
                <input value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} />
              </div>
              <div className="field">
                <label>Цель финансирования</label>
                <input value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} />
              </div>
            </div>
            <div className="field" style={{ marginBottom: 16 }}>
              <label>Описание</label>
              <textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <button className="btn" disabled={saving}>Создать</button>
          </form>
        </div>
      )}

      <div className="card">
        {projects.length === 0 ? (
          <Empty>Проектов пока нет. Создайте первый проект.</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Проект</th>
                <th>Заемщик / группа</th>
                <th>Отрасль</th>
                <th>Статус</th>
                <th className="num">Компании</th>
                <th className="num">Учредители</th>
                <th className="num">Риски</th>
                <th className="num">Документы</th>
                <th className="num">Скоринг</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id}>
                  <td><Link className="link" to={`/projects/${p.id}`}><b>{p.name}</b></Link></td>
                  <td>{p.borrower || '—'}</td>
                  <td>{p.industry || '—'}</td>
                  <td><span className={`badge status-${p.status}`}>{STATUS_LABELS[p.status] || p.status}</span></td>
                  <td className="num">{p.counters?.companies ?? 0}</td>
                  <td className="num">{p.counters?.founders ?? 0}</td>
                  <td className="num">{p.counters?.risks ?? 0}</td>
                  <td className="num">{p.counters?.documents ?? 0}</td>
                  <td className="num">
                    {p.last_score != null ? (
                      <b className={p.last_score >= 70 ? '' : p.last_score >= 50 ? '' : ''} style={{
                        color: p.last_score >= 70 ? 'var(--ok)' : p.last_score >= 50 ? 'var(--warn)' : 'var(--bad)',
                      }}>{fmtNum(p.last_score, 1)}</b>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
