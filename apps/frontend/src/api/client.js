import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

export function apiError(error) {
  const status = error?.response?.status ?? 0
  const data = error?.response?.data
  let message = data?.detail || data?.message || error?.message || 'Request failed.'
  if (Array.isArray(data?.detail)) message = data.detail.map((x) => x.msg || JSON.stringify(x)).join('; ')
  return { status, message, raw: data }
}
