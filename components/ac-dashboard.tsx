"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  AirVentIcon,
  MinusIcon,
  PlusIcon,
  PowerIcon,
  RefreshCwIcon,
  SearchIcon,
  SnowflakeIcon,
  Trash2Icon,
  WifiOffIcon,
} from "lucide-react"
import { toast } from "sonner"

import { api } from "@/lib/api"
import type { ControlPatch, DeviceState, DiscoverResult } from "@/lib/types"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Slider } from "@/components/ui/slider"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

const MODE_LABELS: Record<string, string> = {
  auto: "Auto",
  cool: "Cool",
  dry: "Dry",
  heat: "Heat",
  fan_only: "Fan",
  smart_dry: "Smart dry",
}

const FAN_LABELS: Record<string, string> = {
  auto: "Auto",
  silent: "Quiet",
  low: "Low",
  medium: "Med",
  high: "High",
  max: "Max",
}

const SWING_LABELS: Record<string, string> = {
  off: "Off",
  vertical: "Vertical",
  horizontal: "Horizontal",
  both: "Both",
}

function formatTemp(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—"
  return `${value.toFixed(digits)}°`
}

function sliderValue(value: number | readonly number[]) {
  return Array.isArray(value) ? value[0] : value
}

export function AcDashboard() {
  const [devices, setDevices] = useState<DeviceState[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [apiDown, setApiDown] = useState(false)
  const [found, setFound] = useState<DiscoverResult[]>([])
  const [host, setHost] = useState("")
  const [addOpen, setAddOpen] = useState(false)
  const [manualIp, setManualIp] = useState("")
  const [manualName, setManualName] = useState("")

  const selected = useMemo(
    () => devices.find((device) => device.id === selectedId) ?? devices[0] ?? null,
    [devices, selectedId]
  )

  const loadDevices = useCallback(async () => {
    try {
      const next = await api.devices()
      setDevices(next)
      setApiDown(false)
      setError(null)
      setSelectedId((current) => {
        if (current && next.some((device) => device.id === current)) return current
        return next[0]?.id ?? null
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not reach the LAN API"
      setApiDown(true)
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function boot() {
      for (let attempt = 0; attempt < 12 && !cancelled; attempt += 1) {
        try {
          const next = await api.devices()
          if (cancelled) return
          setDevices(next)
          setApiDown(false)
          setError(null)
          setSelectedId((current) => {
            if (current && next.some((device) => device.id === current)) {
              return current
            }
            return next[0]?.id ?? null
          })
          setLoading(false)
          return
        } catch {
          await new Promise((resolve) => window.setTimeout(resolve, 400))
        }
      }
      if (!cancelled) {
        await loadDevices()
      }
    }
    void boot()
    const timer = window.setInterval(() => {
      void loadDevices()
    }, 5000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [loadDevices])

  async function run(label: string, work: () => Promise<void>) {
    setBusy(label)
    try {
      await work()
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed"
      toast.error(message)
      setError(message)
    } finally {
      setBusy(null)
    }
  }

  async function patch(update: ControlPatch) {
    if (!selected) return
    const previous = devices
    setDevices((current) =>
      current.map((device) =>
        device.id === selected.id ? { ...device, ...update } : device
      )
    )
    try {
      const next = await api.patchDevice(selected.id, update)
      setDevices((current) =>
        current.map((device) => (device.id === next.id ? next : device))
      )
    } catch (err) {
      setDevices(previous)
      const message = err instanceof Error ? err.message : "Control failed"
      toast.error(message)
    }
  }

  async function scan() {
    await run("scan", async () => {
      const results = await api.discover(host.trim() || undefined)
      setFound(results)
      if (results.length === 0) {
        toast.message("No units answered", {
          description:
            "Stay on the same subnet as the indoor unit. Discovery uses UDP 6445.",
        })
      } else {
        toast.success(
          `Found ${results.length} unit${results.length === 1 ? "" : "s"}`
        )
      }
    })
  }

  async function addFound(item: DiscoverResult) {
    await run(`add-${item.ip}`, async () => {
      const device = await api.addDevice({
        ip: item.ip,
        name: item.name ?? undefined,
        token: item.token ?? undefined,
        key: item.key ?? undefined,
        device_id: item.id && /^\d+$/.test(item.id) ? Number(item.id) : undefined,
      })
      toast.success(`Connected ${device.name}`)
      await loadDevices()
      setSelectedId(device.id)
    })
  }

  async function addManual() {
    await run("add-manual", async () => {
      const device = await api.addDevice({
        ip: manualIp.trim(),
        name: manualName.trim() || undefined,
      })
      toast.success(`Connected ${device.name}`)
      setAddOpen(false)
      setManualIp("")
      setManualName("")
      await loadDevices()
      setSelectedId(device.id)
    })
  }

  async function startDemo() {
    await run("demo", async () => {
      const device = await api.enableDemo()
      toast.success("Demo living-room unit is ready")
      await loadDevices()
      setSelectedId(device.id)
    })
  }

  async function removeSelected() {
    if (!selected) return
    await run("remove", async () => {
      await api.removeDevice(selected.id)
      toast.success(`Removed ${selected.name}`)
      await loadDevices()
    })
  }

  const disabled = !selected?.power || busy !== null

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 md:px-8 md:py-10">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">Arch Linux · local LAN</p>
          <h1 className="font-heading text-2xl font-medium tracking-tight md:text-3xl">
            Carrier air conditioner
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Talks to Carrier splits that use the Midea Wi-Fi module (Carrier,
            NetHome Plus, or SmartHome apps). Control stays on your network after
            the first V3 token fetch.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => void loadDevices()}
            disabled={busy !== null}
          >
            {busy === null && loading ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <RefreshCwIcon data-icon="inline-start" />
            )}
            Refresh
          </Button>
          {selected ? (
            <Button variant="destructive" onClick={() => void removeSelected()}>
              <Trash2Icon data-icon="inline-start" />
              Remove
            </Button>
          ) : null}
        </div>
      </header>

      {apiDown ? (
        <Alert variant="destructive">
          <WifiOffIcon />
          <AlertTitle>LAN API is not running</AlertTitle>
          <AlertDescription>
            Start it with <code>pnpm dev</code> or{" "}
            <code>uv run --directory server carrier-ac serve --demo</code>. The
            dashboard proxies to port 43148.
            {error ? ` (${error})` : null}
          </AlertDescription>
        </Alert>
      ) : null}

      {loading ? (
        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      ) : selected ? (
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <Card>
            <CardHeader>
              <CardTitle>{selected.name}</CardTitle>
              <CardDescription>
                {selected.ip}:{selected.port}
                {selected.demo ? " · simulated unit" : " · Midea LAN"}
              </CardDescription>
              <CardAction>
                <div className="flex flex-wrap justify-end gap-2">
                  <Badge variant={selected.power ? "default" : "secondary"}>
                    {selected.power ? "On" : "Off"}
                  </Badge>
                  <Badge variant="outline">
                    {selected.online ? "Online" : "Offline"}
                  </Badge>
                  {selected.demo ? <Badge variant="outline">Demo</Badge> : null}
                </div>
              </CardAction>
            </CardHeader>
            <CardContent className="flex flex-col gap-6">
              {selected.last_error ? (
                <Alert variant="destructive">
                  <AlertTitle>Unit error</AlertTitle>
                  <AlertDescription>{selected.last_error}</AlertDescription>
                </Alert>
              ) : null}

              <div className="flex flex-col items-center gap-4 rounded-xl bg-muted/50 px-4 py-8">
                <p className="text-sm text-muted-foreground">Setpoint</p>
                <div className="flex items-center gap-4">
                  <Button
                    size="icon-lg"
                    variant="outline"
                    disabled={disabled}
                    onClick={() =>
                      void patch({
                        target_temperature: Math.max(
                          selected.min_target_temperature,
                          selected.target_temperature - 0.5
                        ),
                      })
                    }
                  >
                    <MinusIcon />
                    <span className="sr-only">Colder</span>
                  </Button>
                  <p className="min-w-32 text-center font-heading text-6xl font-medium tracking-tight">
                    {formatTemp(selected.target_temperature)}
                  </p>
                  <Button
                    size="icon-lg"
                    variant="outline"
                    disabled={disabled}
                    onClick={() =>
                      void patch({
                        target_temperature: Math.min(
                          selected.max_target_temperature,
                          selected.target_temperature + 0.5
                        ),
                      })
                    }
                  >
                    <PlusIcon />
                    <span className="sr-only">Warmer</span>
                  </Button>
                </div>
                <div className="flex flex-wrap justify-center gap-3 text-sm text-muted-foreground">
                  <span>Indoor {formatTemp(selected.indoor_temperature, 1)}</span>
                  <span>Outdoor {formatTemp(selected.outdoor_temperature, 1)}</span>
                </div>
                <Slider
                  min={selected.min_target_temperature}
                  max={selected.max_target_temperature}
                  step={0.5}
                  value={[selected.target_temperature]}
                  disabled={disabled}
                  onValueCommitted={(value) => {
                    const next = sliderValue(value)
                    if (typeof next === "number") {
                      void patch({ target_temperature: next })
                    }
                  }}
                />
              </div>

              <FieldGroup>
                <Field>
                  <FieldLabel>Mode</FieldLabel>
                  <ToggleGroup
                    value={[selected.mode]}
                    disabled={disabled}
                    spacing={0}
                    className="flex-wrap"
                    onValueChange={(value) => {
                      const next = value[0]
                      if (next) void patch({ mode: next })
                    }
                  >
                    {selected.supported_modes.map((mode) => (
                      <ToggleGroupItem key={mode} value={mode}>
                        {MODE_LABELS[mode] ?? mode}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                </Field>
                <Field>
                  <FieldLabel>Fan</FieldLabel>
                  <ToggleGroup
                    value={[selected.fan_speed]}
                    disabled={disabled}
                    spacing={0}
                    className="flex-wrap"
                    onValueChange={(value) => {
                      const next = value[0]
                      if (next) void patch({ fan_speed: next })
                    }
                  >
                    {selected.supported_fan_speeds.map((speed) => (
                      <ToggleGroupItem key={speed} value={speed}>
                        {FAN_LABELS[speed] ?? speed}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                </Field>
                <Field>
                  <FieldLabel>Swing</FieldLabel>
                  <ToggleGroup
                    value={[selected.swing_mode]}
                    disabled={disabled}
                    spacing={0}
                    className="flex-wrap"
                    onValueChange={(value) => {
                      const next = value[0]
                      if (next) void patch({ swing_mode: next })
                    }
                  >
                    {selected.supported_swing_modes.map((swing) => (
                      <ToggleGroupItem key={swing} value={swing}>
                        {SWING_LABELS[swing] ?? swing}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                </Field>
              </FieldGroup>
            </CardContent>
            <CardFooter className="justify-between gap-3">
              <div className="flex items-center gap-2 text-sm">
                <PowerIcon />
                {selected.power ? "Unit is running" : "Unit is off"}
              </div>
              <Button
                variant={selected.power ? "destructive" : "default"}
                onClick={() => void patch({ power: !selected.power })}
                disabled={busy !== null}
              >
                <PowerIcon data-icon="inline-start" />
                {selected.power ? "Turn off" : "Turn on"}
              </Button>
            </CardFooter>
          </Card>

          <div className="flex flex-col gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Comfort flags</CardTitle>
                <CardDescription>
                  Eco and turbo cancel each other. Sleep is a local preset on the
                  indoor board.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FieldGroup>
                  <Field orientation="horizontal">
                    <FieldContent>
                      <FieldLabel htmlFor="eco">Eco</FieldLabel>
                      <FieldDescription>
                        Lower compressor demand
                      </FieldDescription>
                    </FieldContent>
                    <Switch
                      id="eco"
                      checked={selected.eco}
                      disabled={disabled || !selected.supports_eco}
                      onCheckedChange={(checked) => void patch({ eco: checked })}
                    />
                  </Field>
                  <Field orientation="horizontal">
                    <FieldContent>
                      <FieldLabel htmlFor="turbo">Turbo</FieldLabel>
                      <FieldDescription>Reach setpoint faster</FieldDescription>
                    </FieldContent>
                    <Switch
                      id="turbo"
                      checked={selected.turbo}
                      disabled={disabled || !selected.supports_turbo}
                      onCheckedChange={(checked) =>
                        void patch({ turbo: checked })
                      }
                    />
                  </Field>
                  <Field orientation="horizontal">
                    <FieldContent>
                      <FieldLabel htmlFor="sleep">Sleep</FieldLabel>
                      <FieldDescription>Nighttime ramp</FieldDescription>
                    </FieldContent>
                    <Switch
                      id="sleep"
                      checked={selected.sleep}
                      disabled={disabled || !selected.supports_sleep}
                      onCheckedChange={(checked) =>
                        void patch({ sleep: checked })
                      }
                    />
                  </Field>
                  <Field orientation="horizontal">
                    <FieldContent>
                      <FieldLabel htmlFor="display">Indoor display</FieldLabel>
                      <FieldDescription>LED on the front panel</FieldDescription>
                    </FieldContent>
                    <Switch
                      id="display"
                      checked={selected.display_on}
                      disabled={disabled}
                      onCheckedChange={(checked) =>
                        void patch({ display_on: checked })
                      }
                    />
                  </Field>
                </FieldGroup>
              </CardContent>
            </Card>
            <SetupCard
              host={host}
              setHost={setHost}
              found={found}
              busy={busy}
              addOpen={addOpen}
              setAddOpen={setAddOpen}
              manualIp={manualIp}
              setManualIp={setManualIp}
              manualName={manualName}
              setManualName={setManualName}
              onScan={() => void scan()}
              onAddFound={(item) => void addFound(item)}
              onAddManual={() => void addManual()}
              onDemo={() => void startDemo()}
            />
          </div>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <Card>
            <Empty className="min-h-80 border-0">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <AirVentIcon />
                </EmptyMedia>
                <EmptyTitle>No Carrier unit saved yet</EmptyTitle>
                <EmptyDescription>
                  Scan this subnet for a Midea-protocol indoor unit, add one by
                  IP, or load the demo living-room split.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <div className="flex flex-wrap justify-center gap-2">
                  <Button onClick={() => void scan()} disabled={busy !== null}>
                    {busy === "scan" ? (
                      <Spinner data-icon="inline-start" />
                    ) : (
                      <SearchIcon data-icon="inline-start" />
                    )}
                    Scan network
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void startDemo()}
                    disabled={busy !== null}
                  >
                    <SnowflakeIcon data-icon="inline-start" />
                    Use demo unit
                  </Button>
                </div>
              </EmptyContent>
            </Empty>
          </Card>
          <SetupCard
            host={host}
            setHost={setHost}
            found={found}
            busy={busy}
            addOpen={addOpen}
            setAddOpen={setAddOpen}
            manualIp={manualIp}
            setManualIp={setManualIp}
            manualName={manualName}
            setManualName={setManualName}
            onScan={() => void scan()}
            onAddFound={(item) => void addFound(item)}
            onAddManual={() => void addManual()}
            onDemo={() => void startDemo()}
          />
        </div>
      )}
    </div>
  )
}

function SetupCard({
  host,
  setHost,
  found,
  busy,
  addOpen,
  setAddOpen,
  manualIp,
  setManualIp,
  manualName,
  setManualName,
  onScan,
  onAddFound,
  onAddManual,
  onDemo,
}: {
  host: string
  setHost: (value: string) => void
  found: DiscoverResult[]
  busy: string | null
  addOpen: boolean
  setAddOpen: (open: boolean) => void
  manualIp: string
  setManualIp: (value: string) => void
  manualName: string
  setManualName: (value: string) => void
  onScan: () => void
  onAddFound: (item: DiscoverResult) => void
  onAddManual: () => void
  onDemo: () => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Connect from Arch</CardTitle>
        <CardDescription>
          Same Wi-Fi as the indoor unit. TCP 6444 for control, UDP 6445 for
          discovery.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="host">Scan target</FieldLabel>
            <Input
              id="host"
              placeholder="Leave blank for the whole subnet"
              value={host}
              onChange={(event) => setHost(event.target.value)}
            />
            <FieldDescription>
              Use an IP if broadcast is blocked, or for a V3 unit that needs a
              cloud token on first connect.
            </FieldDescription>
          </Field>
        </FieldGroup>
        <div className="flex flex-wrap gap-2">
          <Button onClick={onScan} disabled={busy !== null}>
            {busy === "scan" ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <SearchIcon data-icon="inline-start" />
            )}
            Scan
          </Button>
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger render={<Button variant="outline" />}>
              Add by IP
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add a unit by IP</DialogTitle>
                <DialogDescription>
                  Newer V3 sticks fetch a token from NetHome once, then stay
                  local.
                </DialogDescription>
              </DialogHeader>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="manual-ip">IP address</FieldLabel>
                  <Input
                    id="manual-ip"
                    placeholder="192.168.1.50"
                    value={manualIp}
                    onChange={(event) => setManualIp(event.target.value)}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="manual-name">Name</FieldLabel>
                  <Input
                    id="manual-name"
                    placeholder="Bedroom"
                    value={manualName}
                    onChange={(event) => setManualName(event.target.value)}
                  />
                </Field>
              </FieldGroup>
              <DialogFooter>
                <Button
                  onClick={onAddManual}
                  disabled={!manualIp.trim() || busy !== null}
                >
                  {busy === "add-manual" ? (
                    <Spinner data-icon="inline-start" />
                  ) : null}
                  Connect
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button variant="ghost" onClick={onDemo} disabled={busy !== null}>
            <SnowflakeIcon data-icon="inline-start" />
            Demo
          </Button>
        </div>
        {found.length > 0 ? (
          <div className="flex flex-col gap-2">
            <Separator />
            <p className="text-sm font-medium">Discovered</p>
            <ul className="flex flex-col gap-2">
              {found.map((item) => (
                <li
                  key={`${item.ip}-${item.id ?? "unknown"}`}
                  className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {item.name ?? "Carrier unit"} · {item.ip}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {item.supported ? "Supported" : "Unknown type"}
                      {item.device_type ? ` · ${item.device_type}` : ""}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onAddFound(item)}
                    disabled={busy !== null}
                  >
                    Save
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <Alert>
          <AlertTitle>Wrong Carrier family?</AlertTitle>
          <AlertDescription>
            Infinity / Ion thermostats need Infinitude, not this LAN protocol.
            Ductless Wi-Fi splits that pair with Carrier Home, NetHome Plus, or
            SmartHome belong here.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  )
}
