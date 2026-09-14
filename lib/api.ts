import type { AppStatus, ControlPatch, DeviceState, DiscoverResult } from "@/lib/types"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // Keep the status text when the API did not return JSON.
    }
    throw new Error(detail)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export const api = {
  status: () => request<AppStatus>("/api/status"),
  devices: () => request<DeviceState[]>("/api/devices"),
  discover: (host?: string) =>
    request<DiscoverResult[]>("/api/discover", {
      method: "POST",
      body: JSON.stringify(host ? { host } : {}),
    }),
  addDevice: (payload: {
    ip: string
    name?: string
    token?: string
    key?: string
    device_id?: number
  }) =>
    request<DeviceState>("/api/devices", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  enableDemo: () => request<DeviceState>("/api/demo", { method: "POST" }),
  patchDevice: (id: string, patch: ControlPatch) =>
    request<DeviceState>(`/api/devices/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  removeDevice: (id: string) =>
    request<{ ok: boolean }>(`/api/devices/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
}
