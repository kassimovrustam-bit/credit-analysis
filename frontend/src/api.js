const BASE = '/api'

async function request(path, options = {}) {
  const resp = await fetch(BASE + path, options)
  if (!resp.ok) {
    let detail = `Ошибка ${resp.status}`
    try {
      const body = await resp.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {}
    throw new Error(detail)
  }
  if (resp.status === 204) return null
  return resp.json()
}

function json(method, path, body) {
  return request(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

function upload(path, file, extraFields = {}) {
  const fd = new FormData()
  Object.entries(extraFields).forEach(([k, v]) => fd.append(k, String(v)))
  fd.append('file', file)
  return request(path, { method: 'POST', body: fd })
}

export const api = {
  // Проекты
  listProjects: () => request('/projects'),
  getProject: (id) => request(`/projects/${id}`),
  createProject: (data) => json('POST', '/projects', data),
  updateProject: (id, data) => json('PUT', `/projects/${id}`, data),
  deleteProject: (id) => request(`/projects/${id}`, { method: 'DELETE' }),

  // Компании и отчетность
  listCompanies: (pid) => request(`/projects/${pid}/companies`),
  createCompany: (pid, data) => json('POST', `/projects/${pid}/companies`, data),
  updateCompany: (id, data) => json('PUT', `/companies/${id}`, data),
  deleteCompany: (id) => request(`/companies/${id}`, { method: 'DELETE' }),
  uploadStatement: (cid, year, file) => upload(`/companies/${cid}/statements`, file, { year }),
  listStatements: (cid) => request(`/companies/${cid}/statements`),
  deleteStatement: (cid, year) => request(`/companies/${cid}/statements/${year}`, { method: 'DELETE' }),
  getRatios: (cid) => request(`/companies/${cid}/ratios`),

  // Прогноз и условия
  getForecast: (pid) => request(`/projects/${pid}/forecast`),
  setForecast: (pid, rows) => json('PUT', `/projects/${pid}/forecast`, rows),
  uploadForecast: (pid, file) => upload(`/projects/${pid}/forecast/upload`, file),
  getYield: (pid) => request(`/projects/${pid}/yield`),
  getTerms: (pid) => request(`/projects/${pid}/terms`),
  setTerms: (pid, data) => json('PUT', `/projects/${pid}/terms`, data),
  getSchedule: (pid) => request(`/projects/${pid}/schedule`),
  getDscr: (pid) => request(`/projects/${pid}/dscr`),

  // Учредители
  listFounders: (pid) => request(`/projects/${pid}/founders`),
  createFounder: (pid, data) => json('POST', `/projects/${pid}/founders`, data),
  updateFounder: (id, data) => json('PUT', `/founders/${id}`, data),
  deleteFounder: (id) => request(`/founders/${id}`, { method: 'DELETE' }),
  setCheck: (fid, type, data) => json('PUT', `/founders/${fid}/checks/${type}`, data),
  uploadPkb: (fid, file) => upload(`/founders/${fid}/pkb`, file),
  checkTypes: () => request('/check-types'),

  // Риски
  listRisks: (pid) => request(`/projects/${pid}/risks`),
  createRisk: (pid, data) => json('POST', `/projects/${pid}/risks`, data),
  updateRisk: (id, data) => json('PUT', `/risks/${id}`, data),
  deleteRisk: (id) => request(`/risks/${id}`, { method: 'DELETE' }),
  riskDicts: () => request('/risk-dicts'),

  // Документы
  listDocuments: (pid) => request(`/projects/${pid}/documents`),
  uploadDocument: (pid, docType, file) => upload(`/projects/${pid}/documents`, file, { doc_type: docType }),
  deleteDocument: (id) => request(`/documents/${id}`, { method: 'DELETE' }),
  docTypes: () => request('/doc-types'),

  // Резюме и скоринг
  getSummary: (pid) => request(`/projects/${pid}/summary`),
  scoringHistory: (pid) => request(`/projects/${pid}/scoring/history`),
}

export function downloadUrl(path) {
  return BASE + path
}
