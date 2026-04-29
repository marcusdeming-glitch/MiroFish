import service from './index'

// Portfolio CRUD
export const createPortfolio = (data) => service.post('/api/portfolio/', data)
export const listPortfolios  = ()     => service.get('/api/portfolio/')
export const getPortfolio    = (id)   => service.get(`/api/portfolio/${id}`)
export const updatePortfolio = (id, data) => service.put(`/api/portfolio/${id}`, data)
export const deletePortfolio = (id)   => service.delete(`/api/portfolio/${id}`)

// Holdings
export const setHoldings   = (id, holdings) => service.put(`/api/portfolio/${id}/holdings`, { holdings })
export const addHolding    = (id, holding)  => service.post(`/api/portfolio/${id}/holdings`, holding)
export const removeHolding = (id, ticker)   => service.delete(`/api/portfolio/${id}/holdings/${ticker}`)

// News & Filings
export const getPortfolioNews    = (id, params = {}) => service.get(`/api/portfolio/${id}/news`, { params })
export const getPortfolioFilings = (id, params = {}) => service.get(`/api/portfolio/${id}/filings`, { params })

// Analysis
export const startAnalysis      = (id, body = {}) => service.post(`/api/portfolio/${id}/analyze`, body)
export const getAnalysisStatus  = (id, analysisId) =>
  service.get(`/api/portfolio/${id}/analyze/status`, { params: analysisId ? { analysis_id: analysisId } : {} })
export const getAnalysisResult  = (id) => service.get(`/api/portfolio/${id}/analysis`)
