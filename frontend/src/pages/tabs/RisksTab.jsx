import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../../api.js'
import { Badge, ErrorBox, Empty } from '../../components/common.jsx'

const EMPTY_RISK = { title: '', category: 'structural', criticality: 'medium', description: '', mitigation: '' }
const CRIT_BADGE = { low: 'ok', medium: 'warning', high: 'bad', critical: 'bad' }

export default function RisksTab({ projectId }) {
  const [risks, setRisks] = useState([])
  const [dicts, setDicts] = useState({ categories: {}, criticality: {} })
  const [error, setError] = useState(null)
  const [form, setForm] = useState(EMPTY_RISK)
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(async () => {
    try {
      setRisks(await api.listRisks(projectId))
      setDicts(await api.riskDicts())
    } catch (e) { setError(e.message) }
  }, [projectId])

  useEffect(() => { load() }, [load])

  async function addRisk(e) {
    e.preventDefault()
    try {
      await api.createRisk(projectId, form)
      setForm(EMPTY_RISK)
      setShowForm(false)
      await load()
    } catch (err) { setError(err.message) }
  }

  async function removeRisk(id) {
    if (!window.confirm('Удалить риск?')) return
    try {
      await api.deleteRisk(id)
      await load()
    } catch (err) { setError(err.message) }
  }

  return (
    <>
      <ErrorBox error={error} />
      <div className="card">
        <div className="btn-row" style={{ justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>Реестр рисков</h2>
          <button className="btn small" onClick={() => setShowForm(!showForm)}>{showForm ? 'Отмена' : 'Добавить риск'}</button>
        </div>

        {showForm && (
          <form onSubmit={addRisk} style={{ marginTop: 16 }}>
            <div className="form-grid">
              <div className="field"><label>Название *</label><input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
              <div className="field">
                <label>Категория</label>
                <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                  {Object.entries(dicts.categories).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Критичность</label>
                <select value={form.criticality} onChange={(e) => setForm({ ...form, criticality: e.target.value })}>
                  {Object.entries(dicts.criticality).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            </div>
            <div className="form-grid">
              <div className="field"><label>Описание</label><textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
              <div className="field">
                <label>Меры снижения</label>
                <textarea rows={2} value={form.mitigation} onChange={(e) => setForm({ ...form, mitigation: e.target.value })} />
                <span className="muted" style={{ fontSize: 11 }}>Наличие мер снижает штраф в скоринге на 40%</span>
              </div>
            </div>
            <button className="btn">Добавить</button>
          </form>
        )}

        {risks.length === 0 ? (
          <Empty>Реестр рисков пуст. Добавьте структурные, отраслевые, финансовые и прочие риски проекта.</Empty>
        ) : (
          <table style={{ marginTop: 16 }}>
            <thead>
              <tr><th>Риск</th><th>Категория</th><th>Критичность</th><th>Описание</th><th>Меры снижения</th><th></th></tr>
            </thead>
            <tbody>
              {risks.map((r) => (
                <tr key={r.id}>
                  <td><b>{r.title}</b></td>
                  <td>{dicts.categories[r.category] || r.category}</td>
                  <td><Badge status={CRIT_BADGE[r.criticality]}>{dicts.criticality[r.criticality] || r.criticality}</Badge></td>
                  <td className="muted">{r.description || '—'}</td>
                  <td className="muted">{r.mitigation || '—'}</td>
                  <td><button className="btn danger small" onClick={() => removeRisk(r.id)}>×</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
