export type DeviceState = {
  id: string
  name: string
  kind: "midea" | "demo"
  ip: string
  port: number
  online: boolean
  supported: boolean
  power: boolean
  mode: string
  fan_speed: string
  swing_mode: string
  target_temperature: number
  indoor_temperature: number | null
  outdoor_temperature: number | null
  eco: boolean
  turbo: boolean
  sleep: boolean
  display_on: boolean
  min_target_temperature: number
  max_target_temperature: number
  supported_modes: string[]
  supported_fan_speeds: string[]
  supported_swing_modes: string[]
  supports_eco: boolean
  supports_turbo: boolean
  supports_sleep: boolean
  last_error: string | null
  demo: boolean
}

export type DiscoverResult = {
  ip: string
  port: number
  id: string | null
  name: string | null
  sn: string | null
  device_type: string | null
  online: boolean | null
  supported: boolean | null
  token: string | null
  key: string | null
  protocol: string | null
}

export type AppStatus = {
  demo: boolean
  device_count: number
  hint: string
}

export type ControlPatch = {
  power?: boolean
  mode?: string
  fan_speed?: string
  swing_mode?: string
  target_temperature?: number
  eco?: boolean
  turbo?: boolean
  sleep?: boolean
  display_on?: boolean
  name?: string
}
