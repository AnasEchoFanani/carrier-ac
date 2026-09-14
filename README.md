# Carrier AC for Arch Linux

Local control for **Carrier ductless / Wi-Fi split** air conditioners from Arch Linux.

**GitHub:** [https://github.com/AnasEchoFanani/carrier-ac](https://github.com/AnasEchoFanani/carrier-ac)

Most Carrier indoor units that pair with **Carrier Home**, **NetHome Plus**, or **Midea SmartHome** are Midea OEM hardware. They speak a LAN protocol on **TCP 6444** (discovery on **UDP 6445**). This project wraps that protocol in:

- a dashboard at `http://127.0.0.1:43147`
- a CLI, `carrier-ac`

After a newer V3 stick fetches its token once (via NetHome), commands stay on your LAN. No Carrier cloud account is required for day-to-day control.

## Download onto your PC (GitHub folder)

On Arch Linux, clone this repo into your GitHub folder, then install and run it:

```bash
sudo pacman -S --needed git python python-pip nodejs npm
python -m pip install --user uv
curl -fsSL https://get.pnpm.io/install.sh | sh -

mkdir -p ~/GitHub
cd ~/GitHub
git clone https://github.com/AnasEchoFanani/carrier-ac.git
cd carrier-ac

uv sync --directory server --extra dev
pnpm install
pnpm dev
```

Open http://127.0.0.1:43147

If you keep clones somewhere else (`~/Documents/GitHub`, `~/src`), change `~/GitHub` above.

To talk to a real indoor unit on the same Wi-Fi:

```bash
uv run --directory server carrier-ac discover
uv run --directory server carrier-ac add 192.168.1.50 --name Bedroom
```

To try the dashboard without hardware:

```bash
pnpm dev:demo
```

## CLI

```bash
uv run --directory server carrier-ac status
uv run --directory server carrier-ac set --power on --mode cool --temp 24 --fan auto
```

Saved units live in `~/.config/carrier-ac/devices.json`.
