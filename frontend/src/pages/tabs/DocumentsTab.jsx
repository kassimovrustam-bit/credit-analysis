import React, { useEffect, useState, useCallback, useRef } from 'react'
import { api, downloadUrl } from '../../api.js'
import { ErrorBox, Empty, fmtNum, fmtMoney } from '../../components/common.jsx'

export default function DocumentsTab({ projectId }) {
  const [docs, setDocs] = useState([])
  const [docTypes, setDocTypes] = useState({})
  const [error, setError] = useState(null)
  const [docType, setDocType] = useState('other')
  const fileRef = useRef(null)

  const load = useCallback(async () => {
    try {
      setDocs(await api.listDocuments(projectId))
      setDocTypes(await api.docTypes())
    } catch (e) { setError(e.message) }
  }, [projectId])

  useEffect(() => { load() }, [load])

  async function onFile(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    try {
      await api.uploadDocument(projectId, docType, file)
      await load()
    } catch (err) { setError(err.message) }
  }

  async function removeDoc(id) {
    if (!window.confirm('Удалить документ?')) return
    try {
      await api.deleteDocument(id)
      await load()
    } catch (err) { setError(err.message) }
  }

  function extractedText(ex) {
    if (!ex || Object.keys(ex).length === 0) return null
    if (ex.note && Object.keys(ex).length === 1) return ex.note
    const parts = []
    if (ex.npv != null) parts.push(`NPV: ${fmtMoney(ex.npv)}`)
    if (ex.irr_pct != null) parts.push(`IRR: ${fmtNum(ex.irr_pct, 1)} %`)
    if (ex.payback_months != null) parts.push(`окупаемость: ${ex.payback_months} мес.`)
    if (ex.budget != null) parts.push(`бюджет: ${fmtMoney(ex.budget)}`)
    return parts.length ? parts.join(' · ') + (ex.note ? ` (${ex.note})` : '') : (ex.note || null)
  }

  return (
    <>
      <ErrorBox error={error} />
      <div className="card">
        <h2>Документы проекта</h2>
        <div className="btn-row">
          <div className="field" style={{ width: 260 }}>
            <select value={docType} onChange={(e) => setDocType(e.target.value)}>
              {Object.entries(docTypes).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <button className="btn" onClick={() => fileRef.current?.click()}>Загрузить файл</button>
          <input ref={fileRef} type="file" accept=".pdf,.txt,.xlsx,.xls,.csv,.docx,.doc" className="file-input" onChange={onFile} />
        </div>
        <p className="muted" style={{ fontSize: 12 }}>
          Для бизнес-плана (PDF/TXT) автоматически извлекаются NPV, IRR, срок окупаемости и бюджет.
        </p>

        {docs.length === 0 ? (
          <Empty>Загрузите бизнес-план, учредительные, личные и разрешительные документы проекта.</Empty>
        ) : (
          <table style={{ marginTop: 16 }}>
            <thead>
              <tr><th>Файл</th><th>Тип</th><th>Загружен</th><th>Извлеченные факты</th><th></th></tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td><a className="link" href={downloadUrl(`/documents/${d.id}/download`)}>{d.filename}</a></td>
                  <td>{docTypes[d.doc_type] || d.doc_type}</td>
                  <td className="muted">{d.uploaded_at}</td>
                  <td className="muted" style={{ fontSize: 12 }}>{extractedText(d.extracted) || '—'}</td>
                  <td><button className="btn danger small" onClick={() => removeDoc(d.id)}>×</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
