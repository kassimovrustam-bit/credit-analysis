import React, { useEffect, useState, useCallback, useRef } from 'react'
import { api, downloadUrl } from '../../api.js'
import { Badge, ErrorBox, Empty, fmtNum, fmtMoney } from '../../components/common.jsx'

const EMPTY_FOUNDER = { full_name: '', inn: '', share: 0, role: '' }
const CHECK_STATUS_LABELS = { clean: 'чисто', attention: 'внимание', negative: 'негатив' }
const CHECK_STATUS_BADGE = { clean: 'ok', attention: 'warning', negative: 'bad' }
const PKB_QUALITY_LABELS = { ok: 'удовлетворительная', warning: 'требует внимания', bad: 'негативная' }

export default function FoundersTab({ projectId }) {
  const [founders, setFounders] = useState([])
  const [checkTypes, setCheckTypes] = useState({})
  const [error, setError] = useState(null)
  const [form, setForm] = useState(EMPTY_FOUNDER)
  const [showForm, setShowForm] = useState(false)
  const [pkbFor, setPkbFor] = useState(null)
  const fileRef = useRef(null)

  const load = useCallback(async () => {
    try {
      setFounders(await api.listFounders(projectId))
      setCheckTypes(await api.checkTypes())
    } catch (e) { setError(e.message) }
  }, [projectId])

  useEffect(() => { load() }, [load])

  async function addFounder(e) {
    e.preventDefault()
    try {
      await api.createFounder(projectId, { ...form, share: Number(form.share) || 0 })
      setForm(EMPTY_FOUNDER)
      setShowForm(false)
      await load()
    } catch (err) { setError(err.message) }
  }

  async function removeFounder(id) {
    if (!window.confirm('Удалить учредителя вместе с проверками?')) return
    try {
      await api.deleteFounder(id)
      await load()
    } catch (err) { setError(err.message) }
  }

  async function setCheck(founderId, type, status) {
    const existing = founders.find((f) => f.id === founderId)?.checks.find((c) => c.check_type === type)
    const comment = window.prompt(
      'Комментарий (источник, дата проверки):',
      existing?.comment || ''
    )
    if (comment === null) return
    try {
      await api.setCheck(founderId, type, { status, comment, checked_at: new Date().toISOString().slice(0, 10) })
      await load()
    } catch (err) { setError(err.message) }
  }

  function startPkb(founderId) {
    setPkbFor(founderId)
    setTimeout(() => fileRef.current?.click(), 0)
  }

  async function onPkbFile(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !pkbFor) return
    try {
      await api.uploadPkb(pkbFor, file)
      await load()
    } catch (err) { setError(err.message) }
  }

  return (
    <>
      <ErrorBox error={error} />
      <div className="card">
        <div className="btn-row" style={{ justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>Учредители</h2>
          <button className="btn small" onClick={() => setShowForm(!showForm)}>{showForm ? 'Отмена' : 'Добавить учредителя'}</button>
        </div>

        {showForm && (
          <form onSubmit={addFounder} style={{ marginTop: 16 }}>
            <div className="form-grid">
              <div className="field"><label>ФИО *</label><input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
              <div className="field"><label>ИНН</label><input value={form.inn} onChange={(e) => setForm({ ...form, inn: e.target.value })} /></div>
              <div className="field"><label>Доля, %</label><input type="number" step="0.01" value={form.share} onChange={(e) => setForm({ ...form, share: e.target.value })} /></div>
              <div className="field"><label>Роль</label><input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} placeholder="бенефициар, гендир…" /></div>
            </div>
            <button className="btn">Добавить</button>
          </form>
        )}

        <input ref={fileRef} type="file" accept=".pdf" className="file-input" onChange={onPkbFile} />

        {founders.length === 0 ? (
          <Empty>Добавьте учредителей. Проверки по госбазам вносятся вручную со статусом и комментарием; отчет ПКБ загружается PDF.</Empty>
        ) : (
          founders.map((f) => (
            <div key={f.id} style={{ borderTop: '1px solid var(--border)', marginTop: 20, paddingTop: 16 }}>
              <div className="btn-row" style={{ justifyContent: 'space-between' }}>
                <div>
                  <b>{f.full_name}</b> <span className="muted">ИНН {f.inn || '—'} · доля {fmtNum(f.share, 2)}%{f.role ? ' · ' + f.role : ''}</span>
                </div>
                <button className="btn danger small" onClick={() => removeFounder(f.id)}>Удалить</button>
              </div>

              <h3>Чек-лист проверок</h3>
              <table>
                <thead>
                  <tr><th>Проверка</th><th>Статус</th><th>Комментарий</th><th>Дата</th><th></th></tr>
                </thead>
                <tbody>
                  {Object.entries(checkTypes).map(([type, label]) => {
                    const c = f.checks.find((x) => x.check_type === type)
                    return (
                      <tr key={type}>
                        <td>{label}</td>
                        <td>{c ? <Badge status={CHECK_STATUS_BADGE[c.status]}>{CHECK_STATUS_LABELS[c.status]}</Badge> : <span className="muted">не проведена</span>}</td>
                        <td className="muted">{c?.comment || '—'}</td>
                        <td className="muted">{c?.checked_at || '—'}</td>
                        <td>
                          <div className="pill-list">
                            <button className="btn small secondary" onClick={() => setCheck(f.id, type, 'clean')}>чисто</button>
                            <button className="btn small secondary" onClick={() => setCheck(f.id, type, 'attention')}>внимание</button>
                            <button className="btn small secondary" onClick={() => setCheck(f.id, type, 'negative')}>негатив</button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>

              <h3>Отчет Первого кредитного бюро</h3>
              <div className="btn-row">
                <button className="btn small" onClick={() => startPkb(f.id)}>Загрузить PDF</button>
                {f.pkb && (
                  <a className="btn secondary small" href={downloadUrl(`/founders/${f.id}/pkb/file`)}>Скачать оригинал</a>
                )}
              </div>
              {f.pkb && (
                <div style={{ marginTop: 10 }}>
                  {f.pkb.error ? (
                    <div className="alert warn">{f.pkb.error}</div>
                  ) : (
                    <>
                      <div className="form-grid">
                        <div className="field"><label>Договоров всего / открытых</label><div><b>{f.pkb.contracts_total} / {f.pkb.contracts_open}</b></div></div>
                        <div className="field"><label>Текущая задолженность</label><div><b>{fmtMoney(f.pkb.current_debt)}</b></div></div>
                        <div className="field"><label>Макс. просрочка, дн.</label><div><b>{f.pkb.max_overdue_days}</b></div></div>
                        <div className="field">
                          <label>Качество КИ</label>
                          <div><Badge status={f.pkb.quality}>{PKB_QUALITY_LABELS[f.pkb.quality] || f.pkb.quality}</Badge></div>
                        </div>
                      </div>
                      {Object.values(f.pkb.markers || {}).some(Boolean) && (
                        <div className="alert warn">
                          Негативные маркеры: {Object.entries(f.pkb.markers).filter(([, v]) => v).map(([k]) => k).join(', ')}
                        </div>
                      )}
                      {(f.pkb.snippets || []).length > 0 && (
                        <details style={{ marginTop: 8 }}>
                          <summary className="muted" style={{ cursor: 'pointer' }}>Сниппеты для сверки с оригиналом ({f.pkb.snippets.length})</summary>
                          <ul style={{ fontSize: 12, color: 'var(--muted)' }}>
                            {f.pkb.snippets.map((s, i) => <li key={i} style={{ marginTop: 4 }}>{s}</li>)}
                          </ul>
                        </details>
                      )}
                    </>
                  )}
                  <div className="alert warn" style={{ marginTop: 10 }}>{f.pkb.disclaimer}</div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </>
  )
}
