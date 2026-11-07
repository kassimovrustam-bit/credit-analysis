import React, { useEffect, useState, useCallback } from 'react'
import { api, downloadUrl } from '../../api.js'
import { Badge, ErrorBox, Empty, fmtNum, fmtMoney } from '../../components/common.jsx'

const BLOCK_LABELS = {
  finance: 'Финансовое состояние группы',
  project: 'Доходность проекта',
  founders: 'Учредители',
  risks: 'Риски',
}

export default function SummaryTab({ projectId, onUpdated }) {
  const [summary, setSummary] = useState(null)
  const [history, setHistory] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const s = await api.getSummary(projectId)
      setSummary(s)
      try { setHistory(await api.scoringHistory(projectId)) } catch { setHistory([]) }
      onUpdated?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  if (error && !summary) return <ErrorBox error={error} />
  if (!summary) return <div className="card">Формируется резюме…</div>

  const sc = summary.scoring
  const verdictClass = sc.total_score >= 70 ? 'ok' : sc.total_score >= 50 ? 'warning' : 'bad'

  return (
    <>
      <ErrorBox error={error} />

      <div className="card">
        <div className="btn-row" style={{ justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>Скоринг и вердикт</h2>
          <div className="btn-row">
            <button className="btn secondary small" onClick={load} disabled={loading}>
              {loading ? 'Пересчет…' : 'Пересчитать'}
            </button>
            <a className="btn small" href={downloadUrl(`/projects/${projectId}/summary/docx`)}>Выгрузить резюме (.docx)</a>
          </div>
        </div>
        <div className="score-hero">
          <div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 4 }}>Итоговый балл</div>
            <div className="score-value">{fmtNum(sc.total_score, 1)}<span className="muted" style={{ fontSize: 22 }}> / 100</span></div>
          </div>
          <div className="score-verdict"><Badge status={verdictClass}>{sc.verdict}</Badge></div>
        </div>

        <table>
          <thead>
            <tr><th>Блок</th><th className="num">Вес</th><th className="num">Балл</th><th style={{ width: '45%' }}></th></tr>
          </thead>
          <tbody>
            {Object.entries(BLOCK_LABELS).map(([key, label]) => {
              const block = sc.blocks[key]
              const weight = sc.weights[key]
              return (
                <tr key={key}>
                  <td>{label}{block.note && <div className="muted" style={{ fontSize: 12 }}>{block.note}</div>}</td>
                  <td className="num">{Math.round(weight * 100)} %</td>
                  <td className="num"><b>{fmtNum(block.score, 1)}</b></td>
                  <td><div className="progress-bar"><div className={`progress-fill ${block.score >= 70 ? 'ok' : block.score >= 50 ? 'warning' : 'bad'}`} style={{ width: `${Math.min(block.score, 100)}%` }} /></div></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {summary.sections.map((section) => (
        <div className="card" key={section.key}>
          <h2>{section.title}</h2>
          <div className="section-text">{section.text}</div>
          {section.key === 'finance' && (section.company_ratios || []).map((cr) => (
            <div key={`${cr.company_id}-${cr.year}`} style={{ marginTop: 16 }}>
              <h3 style={{ fontSize: 15 }}>Коэффициенты: {cr.company_name}, {cr.year} г.</h3>
              <table>
                <thead>
                  <tr><th>Коэффициент</th><th className="num">Значение</th><th>Норма</th><th>Оценка</th></tr>
                </thead>
                <tbody>
                  {cr.ratios.map((r) => (
                    <tr key={r.key}>
                      <td>{r.name}</td>
                      <td className="num">{r.unit === '%' ? fmtNum(r.value * 100, 1) + ' %' : fmtNum(r.value)}</td>
                      <td className="muted">{r.norm}</td>
                      <td><Badge status={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      ))}

      <div className="card">
        <h2>История скоринга</h2>
        {history.length === 0 ? (
          <Empty>Пока нет сохраненных расчетов.</Empty>
        ) : (
          <table>
            <thead>
              <tr><th>Дата и время</th><th className="num">Балл</th><th>Вердикт</th></tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{h.created_at}</td>
                  <td className="num"><b>{fmtNum(h.total_score, 1)}</b></td>
                  <td>{h.verdict}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
