import React, { useEffect, useState, useCallback, useRef } from 'react'
import { api, downloadUrl } from '../../api.js'
import { Badge, ErrorBox, Empty, fmtNum, fmtMoney } from '../../components/common.jsx'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts'

const EMPTY_ROW = () => ({ year: new Date().getFullYear(), revenue: 0, ebitda: 0, capex: 0, tax: 0, cfads: '' })

export default function ForecastTab({ projectId }) {
  const [rows, setRows] = useState([])
  const [yieldData, setYieldData] = useState(null)
  const [error, setError] = useState(null)
  const [editRows, setEditRows] = useState(null)
  const fileRef = useRef(null)

  const load = useCallback(async () => {
    try {
      const forecast = await api.getForecast(projectId)
      setRows(forecast)
      if (forecast.length) {
        try { setYieldData(await api.getYield(projectId)) } catch { setYieldData(null) }
      } else {
        setYieldData(null)
      }
    } catch (e) { setError(e.message) }
  }, [projectId])

  useEffect(() => { load() }, [load])

  async function save() {
    try {
      const payload = editRows.map((r) => ({
        year: Number(r.year),
        revenue: Number(r.revenue) || 0,
        ebitda: Number(r.ebitda) || 0,
        capex: Number(r.capex) || 0,
        tax: Number(r.tax) || 0,
        cfads: r.cfads === '' || r.cfads === null ? null : Number(r.cfads),
      }))
      await api.setForecast(projectId, payload)
      setEditRows(null)
      await load()
    } catch (err) { setError(err.message) }
  }

  async function onFile(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    try {
      await api.uploadForecast(projectId, file)
      await load()
    } catch (err) { setError(err.message) }
  }

  function updateRow(i, key, value) {
    const next = [...editRows]
    next[i] = { ...next[i], [key]: value }
    setEditRows(next)
  }

  const chartData = rows.map((r) => ({
    year: String(r.year),
    'Выручка': r.revenue,
    'EBITDA': r.ebitda,
    'CFADS': r.cfads ?? (r.ebitda - r.capex - r.tax),
  }))

  return (
    <>
      <ErrorBox error={error} />
      <div className="card">
        <div className="btn-row" style={{ justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>Прогноз денежных потоков</h2>
          <div className="btn-row">
            <a className="btn secondary small" href={downloadUrl(`/projects/${projectId}/forecast/sample`)}>Шаблон Excel</a>
            <button className="btn secondary small" onClick={() => fileRef.current?.click()}>Загрузить Excel</button>
            <button className="btn small" onClick={() => setEditRows(rows.length ? rows.map((r) => ({ ...r, cfads: r.cfads ?? '' })) : [EMPTY_ROW()])}>
              {rows.length ? 'Редактировать таблицу' : 'Ввести таблицу'}
            </button>
          </div>
        </div>
        <input ref={fileRef} type="file" accept=".xlsx,.xls" className="file-input" onChange={onFile} />

        {editRows ? (
          <>
            <table style={{ marginTop: 16 }}>
              <thead>
                <tr>
                  <th>Год</th><th>Выручка</th><th>EBITDA</th><th>CAPEX</th><th>Налог</th><th>CFADS</th><th></th>
                </tr>
              </thead>
              <tbody>
                {editRows.map((r, i) => (
                  <tr key={i}>
                    {['year', 'revenue', 'ebitda', 'capex', 'tax', 'cfads'].map((k) => (
                      <td key={k}>
                        <input
                          type="number"
                          style={{ width: 110 }}
                          value={r[k] ?? ''}
                          placeholder={k === 'cfads' ? 'авто' : ''}
                          onChange={(e) => updateRow(i, k, e.target.value)}
                        />
                      </td>
                    ))}
                    <td>
                      <button className="btn danger small" onClick={() => setEditRows(editRows.filter((_, j) => j !== i))}>×</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="btn-row" style={{ marginTop: 12 }}>
              <button className="btn secondary small" onClick={() => setEditRows([...editRows, EMPTY_ROW()])}>+ Год</button>
              <button className="btn" onClick={save}>Сохранить</button>
              <button className="btn secondary" onClick={() => setEditRows(null)}>Отмена</button>
            </div>
            <p className="muted" style={{ fontSize: 12 }}>Пустой CFADS рассчитывается как EBITDA − CAPEX − налог.</p>
          </>
        ) : rows.length === 0 ? (
          <Empty>Задайте прогноз таблицей или загрузите Excel (колонки year, revenue, ebitda, capex, tax, cfads).</Empty>
        ) : (
          <>
            <table style={{ marginTop: 16 }}>
              <thead>
                <tr><th>Год</th><th className="num">Выручка</th><th className="num">EBITDA</th><th className="num">CAPEX</th><th className="num">Налог</th><th className="num">CFADS</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.year}</td>
                    <td className="num">{fmtMoney(r.revenue)}</td>
                    <td className="num">{fmtMoney(r.ebitda)}</td>
                    <td className="num">{fmtMoney(r.capex)}</td>
                    <td className="num">{fmtMoney(r.tax)}</td>
                    <td className="num">{fmtMoney(r.cfads)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ height: 260, marginTop: 20 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis />
                  <Tooltip formatter={(v) => fmtMoney(v)} />
                  <Legend />
                  <Bar dataKey="Выручка" fill="#93c5fd" />
                  <Bar dataKey="EBITDA" fill="#1a56db" />
                  <Bar dataKey="CFADS" fill="#057a55" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>

      {yieldData && (
        <div className="card">
          <h2>Показатели доходности</h2>
          <div className="form-grid">
            <div className="field"><label>Ставка дисконтирования</label><div><b>{fmtNum(yieldData.discount_rate, 1)} %</b></div></div>
            <div className="field"><label>Инвестиции</label><div><b>{fmtMoney(yieldData.investment)}</b></div></div>
            <div className="field">
              <label>NPV</label>
              <div><b>{fmtMoney(yieldData.npv)}</b> <Badge status={yieldData.npv_status}>{yieldData.npv_status === 'ok' ? 'приемлемо' : 'неприемлемо'}</Badge></div>
            </div>
            <div className="field">
              <label>IRR</label>
              <div><b>{yieldData.irr != null ? fmtNum(yieldData.irr, 1) + ' %' : '—'}</b>{' '}
                {yieldData.irr_status && yieldData.irr_status !== 'unknown' && (
                  <Badge status={yieldData.irr_status}>{yieldData.irr_status === 'ok' ? 'приемлемо' : 'неприемлемо'}</Badge>
                )}
              </div>
            </div>
            <div className="field"><label>Индекс доходности (PI)</label><div><b>{fmtNum(yieldData.pi, 2)}</b></div></div>
            <div className="field"><label>Срок окупаемости простой</label><div><b>{fmtNum(yieldData.payback_simple_years, 1)} лет</b></div></div>
            <div className="field"><label>Дисконтированный</label><div><b>{fmtNum(yieldData.payback_discounted_years, 1)} лет</b></div></div>
          </div>
        </div>
      )}
    </>
  )
}
