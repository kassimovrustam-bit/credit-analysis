import React from 'react'

export const STATUS_BADGE = { ok: 'ok', warning: 'warning', bad: 'bad', unknown: 'unknown' }

export const STATUS_LABELS = {
  ok: 'норма',
  warning: 'погранично',
  bad: 'неприемлемо',
  unknown: 'нет данных',
}

export function Badge({ status, children }) {
  return <span className={`badge ${status}`}>{children ?? STATUS_LABELS[status] ?? status}</span>
}

export function fmtNum(v, digits = 2) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('ru-RU', { maximumFractionDigits: digits, minimumFractionDigits: 0 })
}

export function fmtMoney(v) {
  return fmtNum(v, 2)
}

export function fmtPct(v) {
  if (v === null || v === undefined) return '—'
  return fmtNum(Number(v) * 100, 1) + ' %'
}

export function ErrorBox({ error }) {
  if (!error) return null
  return <div className="alert error">{String(error)}</div>
}

export function Empty({ children }) {
  return <div className="alert info">{children || 'Нет данных'}</div>
}
