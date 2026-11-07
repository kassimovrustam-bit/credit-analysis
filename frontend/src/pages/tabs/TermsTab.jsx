import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../../api.js'
import { Badge, ErrorBox, Empty, fmtNum, fmtMoney } from '../../components/common.jsx'

const EMPTY_TERMS = { amount: 0, rate: 0, term_months: 60, grace_months: 0, schedule_type: 'annuity', discount_rate: 15 }

export default function TermsTab({ projectId }) {
  const [terms, setTerms] = useState(null)
  const [form, setForm] = useState(EMPTY_TERMS)
  const [schedule, setSchedule] = useState(null)
  const [dscr, setDscr] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      try {
        const t = await api.getTerms(projectId)
        setTerms(t)
        setForm({ amount: t.amount, rate: t.rate, term_months: t.term_months, grace_months: t.grace_months, schedule_type: t.schedule_type, discount_rate: t.discount_rate })
        try { setSchedule(await api.getSchedule(projectId)) } catch { setSchedule(null) }
      } catch {
        setTerms(null)
        setSchedule(null)
      }
      try { setDscr(await api.getDscr(projectId)) } catch { setDscr(null) }
    } catch (e) { setError(e.message) }
  }, [projectId])

  useEffect(() => { load() }, [load])

  async function save(e) {
    e.preventDefault()
    setError(null)
    try {
      await api.setTerms(projectId, {
        amount: Number(form.amount) || 0,
        rate: Number(form.rate) || 0,
        term_months: Number(form.term_months) || 0,
        grace_months: Number(form.grace_months) || 0,
        schedule_type: form.schedule_type,
        discount_rate: Number(form.discount_rate) || 15,
      })
      await load()
    } catch (err) { setError(err.message) }
  }

  return (
    <>
      <ErrorBox error={error} />
      <div className="card">
        <h2>Условия кредитования</h2>
        <form onSubmit={save}>
          <div className="form-grid">
            <div className="field"><label>Сумма, руб.</label><input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div>
            <div className="field"><label>Ставка, % годовых</label><input type="number" step="0.1" value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} /></div>
            <div className="field"><label>Срок, мес.</label><input type="number" value={form.term_months} onChange={(e) => setForm({ ...form, term_months: e.target.value })} /></div>
            <div className="field"><label>Льготный период, мес.</label><input type="number" value={form.grace_months} onChange={(e) => setForm({ ...form, grace_months: e.target.value })} /></div>
            <div className="field">
              <label>Тип графика</label>
              <select value={form.schedule_type} onChange={(e) => setForm({ ...form, schedule_type: e.target.value })}>
                <option value="annuity">аннуитетный</option>
                <option value="differentiated">дифференцированный</option>
              </select>
            </div>
            <div className="field"><label>Ставка дисконтирования, %</label><input type="number" step="0.1" value={form.discount_rate} onChange={(e) => setForm({ ...form, discount_rate: e.target.value })} /></div>
          </div>
          <button className="btn">Сохранить условия</button>
        </form>
      </div>

      {dscr && dscr.length > 0 && (
        <div className="card">
          <h2>DSCR по годам <span className="muted" style={{ fontSize: 13, fontWeight: 400 }}>(норма ≥ 1,2)</span></h2>
          <table>
            <thead>
              <tr><th>Год</th><th className="num">CFADS</th><th className="num">Обслуживание долга</th><th className="num">DSCR</th><th>Оценка</th></tr>
            </thead>
            <tbody>
              {dscr.map((d) => (
                <tr key={d.year}>
                  <td>{d.year}</td>
                  <td className="num">{fmtMoney(d.cfads)}</td>
                  <td className="num">{fmtMoney(d.debt_service)}</td>
                  <td className="num"><b>{fmtNum(d.dscr, 2)}</b></td>
                  <td><Badge status={d.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {schedule && schedule.schedule.length > 0 && (
        <div className="card">
          <h2>График платежей</h2>
          <div style={{ maxHeight: 420, overflow: 'auto' }}>
            <table>
              <thead>
                <tr><th>Месяц</th><th className="num">Платеж</th><th className="num">Тело</th><th className="num">Проценты</th><th className="num">Остаток</th></tr>
              </thead>
              <tbody>
                {schedule.schedule.map((s) => (
                  <tr key={s.month} style={s.grace ? { background: 'var(--warn-bg)' } : undefined}>
                    <td>{s.month}{s.grace ? ' (льготный)' : ''}</td>
                    <td className="num">{fmtMoney(s.payment)}</td>
                    <td className="num">{fmtMoney(s.principal)}</td>
                    <td className="num">{fmtMoney(s.interest)}</td>
                    <td className="num">{fmtMoney(s.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!terms && (
        <div className="card">
          <Empty>Условия кредитования еще не заданы. Заполните форму выше — график платежей и DSCR рассчитаются автоматически.</Empty>
        </div>
      )}
    </>
  )
}
