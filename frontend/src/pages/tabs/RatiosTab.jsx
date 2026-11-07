import React, { useEffect, useState, useCallback, useRef } from 'react'
import { api, downloadUrl } from '../../api.js'
import { Badge, ErrorBox, Empty, fmtNum } from '../../components/common.jsx'

const ROLE_LABELS = { borrower: 'заемщик', guarantor: 'поручитель', related: 'связанная' }
const EMPTY_COMPANY = { name: '', inn: '', okved: '', role: 'borrower' }

export default function RatiosTab({ projectId }) {
  const [companies, setCompanies] = useState([])
  const [ratios, setRatios] = useState({})
  const [error, setError] = useState(null)
  const [form, setForm] = useState(EMPTY_COMPANY)
  const [showForm, setShowForm] = useState(false)
  const [year, setYear] = useState(new Date().getFullYear() - 1)
  const fileRef = useRef(null)
  const [uploadFor, setUploadFor] = useState(null)

  const load = useCallback(async () => {
    try {
      const list = await api.listCompanies(projectId)
      setCompanies(list)
      const r = {}
      for (const c of list) {
        if (c.years.length) {
          r[c.id] = await api.getRatios(c.id)
        }
      }
      setRatios(r)
    } catch (e) {
      setError(e.message)
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  async function addCompany(e) {
    e.preventDefault()
    try {
      await api.createCompany(projectId, form)
      setForm(EMPTY_COMPANY)
      setShowForm(false)
      await load()
    } catch (err) { setError(err.message) }
  }

  async function removeCompany(id) {
    if (!window.confirm('Удалить компанию вместе с отчетностью?')) return
    try {
      await api.deleteCompany(id)
      await load()
    } catch (err) { setError(err.message) }
  }

  function startUpload(companyId) {
    setUploadFor(companyId)
    setTimeout(() => fileRef.current?.click(), 0)
  }

  async function onFile(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !uploadFor) return
    try {
      await api.uploadStatement(uploadFor, year, file)
      await load()
    } catch (err) { setError(err.message) }
  }

  return (
    <>
      <ErrorBox error={error} />
      <div className="card">
        <div className="btn-row" style={{ justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>Компании группы</h2>
          <div className="btn-row">
            <a className="btn secondary small" href={downloadUrl(`/sample/statement?year=${year}`)}>
              Тестовая форма 1/2
            </a>
            <button className="btn small" onClick={() => setShowForm(!showForm)}>
              {showForm ? 'Отмена' : 'Добавить компанию'}
            </button>
          </div>
        </div>

        {showForm && (
          <form onSubmit={addCompany} style={{ marginTop: 16 }}>
            <div className="form-grid">
              <div className="field">
                <label>Название *</label>
                <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="field">
                <label>ИНН</label>
                <input value={form.inn} onChange={(e) => setForm({ ...form, inn: e.target.value })} />
              </div>
              <div className="field">
                <label>ОКВЭД</label>
                <input value={form.okved} onChange={(e) => setForm({ ...form, okved: e.target.value })} />
              </div>
              <div className="field">
                <label>Роль</label>
                <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                  {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            </div>
            <button className="btn">Добавить</button>
          </form>
        )}

        <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" className="file-input" onChange={onFile} />

        {companies.length === 0 ? (
          <Empty>Добавьте компании группы и загрузите отчетность (формы 1 и 2 в Excel/CSV по кодам строк РСБУ).</Empty>
        ) : (
          companies.map((c) => (
            <div key={c.id} style={{ borderTop: '1px solid var(--border)', marginTop: 16, paddingTop: 16 }}>
              <div className="btn-row" style={{ justifyContent: 'space-between' }}>
                <div>
                  <b>{c.name}</b> <span className="muted">ИНН {c.inn || '—'} · {ROLE_LABELS[c.role]}</span>
                  <div className="muted" style={{ fontSize: 12 }}>
                    Отчетность: {c.years.length ? c.years.join(', ') + ' г.' : 'не загружена'}
                  </div>
                </div>
                <div className="btn-row">
                  <div className="field" style={{ width: 110 }}>
                    <input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
                  </div>
                  <button className="btn small" onClick={() => startUpload(c.id)}>Загрузить форму 1/2</button>
                  <button className="btn danger small" onClick={() => removeCompany(c.id)}>Удалить</button>
                </div>
              </div>

              {(ratios[c.id] || []).map((cr) => (
                <div key={cr.year} style={{ marginTop: 12 }}>
                  <h3>
                    {cr.year} г. — <Badge status={cr.solvency === 'ok' ? 'ok' : cr.solvency === 'questionable' ? 'warning' : 'bad'}>
                      {cr.solvency_label}
                    </Badge>{' '}
                    <span className="muted" style={{ fontWeight: 400, fontSize: 13 }}>
                      Z-score Альтмана: {fmtNum(cr.z_score, 2)} ({cr.z_zone})
                    </span>
                  </h3>
                  <table>
                    <thead>
                      <tr><th>Коэффициент</th><th className="num">Значение</th><th>Норма</th><th>Оценка</th></tr>
                    </thead>
                    <tbody>
                      {cr.ratios.map((r) => (
                        <tr key={r.key}>
                          <td>{r.name}</td>
                          <td className="num">{r.unit === '%' && r.value != null ? fmtNum(r.value * 100, 1) + ' %' : fmtNum(r.value, r.unit === 'абс.' ? 0 : 2)}</td>
                          <td className="muted">{r.norm}</td>
                          <td><Badge status={r.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>{cr.ebitda_note} EBITDA = {fmtNum(cr.ebitda, 0)}</div>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </>
  )
}
