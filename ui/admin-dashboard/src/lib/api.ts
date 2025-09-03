import axios from 'axios'
import type {
  AppSettings,
  Assistant,
  LogItem,
  LogStats,
  PluginManifest,
  Workflow,
  MarketItem,
  MarketMetadata,
  MarketDownloadRequest,
  MarketDownloadResponse,
  OverviewData,
  AdminAnalyticsData,
} from './types'

const BASE_URL = (import.meta.env.VITE_BACKEND_URL || '') + '/api/v1'
const HTTP_TIMEOUT = 120_000

// 可选：从本地存储读取鉴权令牌
function getAuthToken(): string | null {
  return localStorage.getItem('DASHBOARD_TOKEN')
}

export const http = axios.create({
  baseURL: BASE_URL,
  timeout: HTTP_TIMEOUT,
})

// 附加 Authorization（如果存在）
http.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 统一错误信息提取（与后端 detail 字段对齐）
function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const resp = err.response
    if (resp?.data && typeof resp.data === 'object' && 'detail' in resp.data) {
      return String((resp.data as any).detail)
    }
    if (typeof resp?.data === 'string') return resp.data
    if (resp?.status) return `HTTP ${resp.status}`
    return err.message || 'Network error'
  }
  return String(err)
}

export async function getOverview(): Promise<OverviewData> {
  try {
    const { data } = await http.get<OverviewData>('/overview')
    return data
  } catch (err) {
    throw new Error(`Failed to fetch overview: ${extractErrorMessage(err)}`)
  }
}

export async function getBudget(): Promise<AdminAnalyticsData> {
  try {
    const { data } = await http.get<AdminAnalyticsData>('/overview/budget')
    return data
  } catch (err) {
    throw new Error(`Failed to fetch budget: ${extractErrorMessage(err)}`)
  }
}
// --- Settings ---

export async function getAppSettings(): Promise<AppSettings | null> {
  try {
    const { data } = await http.get<AppSettings>('/settings')
    return data
  } catch (err) {
    throw new Error(`Failed to fetch app settings: ${extractErrorMessage(err)}`)
  }
}

export async function saveAppSettings(payload: AppSettings): Promise<void> {
  try {
    // Use PATCH for partial updates
    await http.patch('/settings', payload)
  } catch (err) {
    throw new Error(`Failed to save app settings: ${extractErrorMessage(err)}`)
  }
}

// --- Assistants ---

export async function getAssistantsConfig(): Promise<Assistant[] | null> {
  try {
    const { data } = await http.get<Assistant[]>('/assistants')
    return data
  } catch (err) {
    return []
  }
}

export async function _saveAssistantsConfig(
  payload: Assistant[]
): Promise<void> {
  try {
    // Use PUT to replace the entire collection
    await http.put('/assistants', payload)
  } catch (err) {
    throw new Error(
      `Failed to save assistants configuration: ${extractErrorMessage(err)}`
    )
  }
}

export async function addAssistant(
  name: string,
  description: string
): Promise<Assistant> {
  try {
    // POST to the collection endpoint
    const { data } = await http.post<Assistant>('/assistants', {
      name,
      description,
    })
    return data
  } catch (err) {
    throw new Error(
      `Failed to add assistant '${name}': ${extractErrorMessage(err)}`
    )
  }
}

export async function deleteAssistant(assistantId: string): Promise<void> {
  try {
    // Use DELETE on the specific resource URL
    await http.delete(`/assistants/${assistantId}`)
  } catch (err) {
    throw new Error(
      `Failed to delete assistant '${assistantId}': ${extractErrorMessage(err)}`
    )
  }
}

export async function addPluginToAssistant(
  assistantId: string,
  pluginId: string
): Promise<void> {
  try {
    // POST to the plugins sub-collection with the name in the body
    await http.post(`/assistants/${assistantId}/plugins`, {
      plugin_id: pluginId,
    })
  } catch (err) {
    throw new Error(
      `Failed to add plugin '${pluginId}': ${extractErrorMessage(err)}`
    )
  }
}

export async function removePluginFromAssistant(
  assistantId: string,
  pluginId: string
): Promise<void> {
  try {
    // Use DELETE on the specific plugin sub-resource URL
    await http.delete(`/assistants/${assistantId}/plugins/${pluginId}`)
  } catch (err) {
    throw new Error(
      `Failed to remove plugin '${pluginId}': ${extractErrorMessage(err)}`
    )
  }
}

export async function updateAssistant(
  assistantId: string,
  payload: Partial<Assistant>
): Promise<Assistant> {
  try {
    const transformedPayload = structuredClone(payload)

    if (transformedPayload.plugins) {
      transformedPayload.plugins.forEach((plugin) => {
        if (plugin.config && Array.isArray(plugin.config)) {
          const newConfigObject = plugin.config.reduce(
            (acc, item) => {
              if (item.value !== undefined && item.value !== null) {
                acc[item.name] = item.value
              }
              return acc
            },
            {} as Record<string, unknown>
          )
          ;(plugin as any).config = newConfigObject
        }
      })
    }

    const { data } = await http.patch(
      `/assistants/${assistantId}`,
      transformedPayload
    )

    return data
  } catch (err) {
    throw new Error(`Failed to update assistant: ${extractErrorMessage(err)}`)
  }
}

// --- Plugins ---

export async function getAvailablePlugins(): Promise<PluginManifest[] | null> {
  try {
    // Corrected collection URL
    const { data } = await http.get<PluginManifest[]>('/plugins')
    return data
  } catch (err) {
    throw new Error(
      `Failed to fetch available plugins: ${extractErrorMessage(err)}`
    )
  }
}

export async function deletePlugin(pluginId: string): Promise<void> {
  try {
    // Use DELETE on the specific plugin resource URL
    await http.delete(`/plugins/${pluginId}`)
  } catch (err) {
    throw new Error(
      `Failed to delete plugin '${pluginId}': ${extractErrorMessage(err)}`
    )
  }
}

// --- Logs ---

export async function getLogs(params: {
  level?: string | null
  module?: string | null
  limit?: number | null
  search?: string | null
}): Promise<LogItem[]> {
  try {
    // Use GET and pass filters as query parameters
    const { data } = await http.get<LogItem[]>('/logs', { params })
    return data
  } catch (err) {
    throw new Error(`Failed to fetch logs: ${extractErrorMessage(err)}`)
  }
}

export async function getLogStatistics(): Promise<LogStats> {
  try {
    // Corrected nested URL
    const { data } = await http.get<LogStats>('/logs/stats')
    return data
  } catch {
    // Default value on failure
    return {
      total_logs: 0,
      by_level: {},
      by_module: {},
      oldest_timestamp: null,
      newest_timestamp: null,
    }
  }
}

// Assuming the backend provides a DELETE /logs endpoint to clear all logs
export async function clearAllLogs(): Promise<boolean> {
  try {
    await http.delete('/logs/clear') // Using a more specific clear endpoint
    return true
  } catch {
    return false
  }
}

// --- Workflows ---

export async function getWorkflows(): Promise<Workflow[] | null> {
  try {
    const { data } = await http.get<Workflow[]>('/workflows')
    return data
  } catch (err) {
    // Return mock data for development when backend is not available
    console.warn('Backend not available, returning mock workflows', err)
    return []
  }
}

export async function getWorkflow(
  workflowId: string
): Promise<Workflow | null> {
  try {
    const { data } = await http.get<Workflow>(`/workflows/${workflowId}`)
    return data
  } catch (err) {
    throw new Error(
      `Failed to fetch workflow '${workflowId}': ${extractErrorMessage(err)}`
    )
  }
}

export async function saveWorkflow(workflow: Workflow): Promise<Workflow> {
  try {
    console.log('Saving workflow', workflow)
    const { data } = await http.put<Workflow>(
      `/workflows/${workflow.id}`,
      workflow
    )
    return data
  } catch (err) {
    // Mock save for development
    console.warn('Backend not available, mocking workflow save')
    return { ...workflow, updated_at: new Date().toISOString() }
  }
}

export async function createWorkflow(
  name: string,
  description?: string
): Promise<Workflow> {
  try {
    const { data } = await http.post<Workflow>('/workflows', {
      name,
      description,
    })
    return data
  } catch (err) {
    // Mock create for development
    console.warn('Backend not available, mocking workflow creation')
    return {
      id: `mock-${Date.now()}`,
      name,
      description,
      nodes: [],
      edges: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  }
}

export async function deleteWorkflow(workflowId: string): Promise<void> {
  try {
    await http.delete(`/workflows/${workflowId}`)
  } catch (err) {
    // Mock delete for development
    console.warn('Backend not available, mocking workflow deletion')
    return
  }
}

// --- Market ---

export async function getMarketMetadata(): Promise<MarketMetadata | null> {
  try {
    const { data } = await http.get<MarketMetadata>('/market/metadata')
    return data
  } catch (err) {
    console.warn('Backend not available, returning mock market metadata', err)
    // Mock data for development
    return {
      version: '1.0.0',
      updated_at: new Date().toISOString(),
      categories: {
        plugins: 15,
        assistants: 8,
        workflows: 5,
      },
    }
  }
}

export async function getMarketItems(
  category: 'all' | 'plugin' | 'assistant' | 'workflow'
): Promise<MarketItem[] | null> {
  try {
    const url = category
      ? `/market/items?category=${category}`
      : '/market/items'
    const { data } = await http.get<MarketItem[]>(url)
    return data
  } catch (err) {
    console.warn('Backend not available, returning mock market items', err)
    // Mock data for development
    return []
  }
}

export async function downloadMarketItem(
  request: MarketDownloadRequest
): Promise<MarketDownloadResponse> {
  try {
    const { data } = await http.post<MarketDownloadResponse>(
      '/market/download',
      request
    )
    return data
  } catch (err) {
    throw new Error(
      `Failed to download ${request.category} '${request.item_id}': ${extractErrorMessage(err)}`
    )
  }
}

export async function getMarketItemReadme(
  itemId: string
): Promise<string | null> {
  try {
    const { data } = await http.get<{ readme: string }>(
      `/market/items/${itemId}/readme`
    )
    return data.readme
  } catch (err) {
    console.warn('Failed to fetch readme for', itemId, err)
    return null
  }
}
