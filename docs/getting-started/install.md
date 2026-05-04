# Install

Pick the path for your machine. Builds aren't code-signed yet, so each OS will warn the first time — instructions for getting past the warning are inline.

## macOS

Download [Eternego.dmg](https://github.com/Eternego-AI/eternego/releases/latest/download/Eternego.dmg). Open it, drag **Eternego** to **Applications**, then double-click Eternego from Applications.

The first launch shows: *"Eternego.app cannot be opened because the developer cannot be verified."* Right-click (or Control-click) the app, choose **Open**, then **Open** again in the dialog. macOS remembers the choice — subsequent launches are normal.

## Windows

Download [Eternego-setup.exe](https://github.com/Eternego-AI/eternego/releases/latest/download/Eternego-setup.exe). Walk through the wizard (Next → Install → Finish). Eternego launches automatically and adds Start Menu and Desktop shortcuts.

The first dialog is *"Windows protected your PC"* (SmartScreen). Click **More info**, then **Run anyway**. SmartScreen remembers this app afterwards.

## Linux (.AppImage)

Download [Eternego-x86_64.AppImage](https://github.com/Eternego-AI/eternego/releases/latest/download/Eternego-x86_64.AppImage), make it executable, run:

```bash
chmod +x Eternego-x86_64.AppImage
./Eternego-x86_64.AppImage
```

A single self-contained binary. No system Python needed.

## Docker

The image ships with the persona's own desktop baked in (Xvfb + fluxbox + noVNC). She can click, type, install browsers herself when you ask. Peek at what she's doing at `http://localhost:6080/vnc.html`.

```bash
docker run -d --name eternego --network=host \
  -v ~/.eternego:/data \
  ghcr.io/eternego-ai/eternego:latest
```

Persona files live in `~/.eternego` on the host — same place as native install. Switch between Docker and native without losing data.

`--network=host` lets the container reach Ollama running natively on your machine. Without it, set `-e OLLAMA_HOST=http://host.docker.internal:11434` and add `-p 5000:5000 -p 6080:6080`.

For an everything-in-containers setup with Ollama as a sibling service:

```bash
curl -fsSL https://raw.githubusercontent.com/Eternego-AI/eternego/master/installation/docker/docker-compose.yml > eternego.compose.yml
docker compose -f eternego.compose.yml up -d
```

Use the `:full` tag (or `image: ghcr.io/eternego-ai/eternego:full` in the compose file) for the training-equipped image — adds ~5.5 GB of CUDA wheels for LoRA fine-tuning.

## Background service (CLI, auto-start on boot)

The installers above launch when you open them. To register her as a system service so she keeps running across reboots:

```bash
# Linux (systemd) / macOS (launchd) — auto-installs Python and Ollama via apt/dnf/pacman/brew
curl -fsSL https://raw.githubusercontent.com/Eternego-AI/eternego/master/installation/install.sh | bash
```

```powershell
# Windows (Scheduled Task) — auto-installs Python via winget
iwr -useb https://raw.githubusercontent.com/Eternego-AI/eternego/master/installation/install.ps1 | iex
```

Both scripts accept `--full` (or `-Full` on Windows) to install training extras.

## From source (contributors)

```bash
git clone https://github.com/Eternego-AI/eternego.git
cd eternego
bash installation/install.sh        # Linux/macOS
pwsh installation/install.ps1       # Windows
```

See [CONTRIBUTING.md](https://github.com/Eternego-AI/eternego/blob/master/CONTRIBUTING.md) before sending a PR.

## After install

Your browser opens to `http://localhost:5000`. If port 5000 is taken on your machine, the daemon picks the next free one and prints which it chose.

Continue to [Your first persona →](your-first-persona.md).
