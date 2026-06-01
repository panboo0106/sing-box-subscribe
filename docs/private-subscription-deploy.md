# 私有订阅自动化部署（方案一：私有 Git 仓库 + Token）

把"生成 → 上传网盘 → 各设备下载 → 手动重启"四步全部去掉手动环节。

## 0. 拓扑与数据流

```
┌────────────────────────────┐         ┌──────────────────────────┐
│ 源仓库（本仓库, 私有）       │         │ 产物仓库 dist (私有)      │
│  sing-box-subscribe         │  push   │  sing-box-config-dist    │
│  - main.py                  │ ──────▶ │  - macos/ai.json         │
│  - config_template/         │         │  - macos/streaming.json  │
│  - local_providers.json(秘) │         │  - linux/ai.json         │
└────────────────────────────┘         │  - linux/streaming.json  │
       │                                │  - VERSION (commit sha)  │
       │ 方式 A: GitHub Actions          └──────────────────────────┘
       │ 方式 B: 本地 launchd/cron                    │
       │                                              │ HTTPS + PAT(read)
       │                                              ▼
       │                              ┌───────────────────────────┐
       │                              │ 设备端 updater (cron)      │
       │                              │  - curl + ETag/sha256      │
       │                              │  - sing-box check          │
       │                              │  - 原子替换 + 重启         │
       │                              └───────────────────────────┘
       │                                  ▲                ▲
       │                                  │                │
       │                              macOS launchd   Linux systemd timer
```

涉及四把"钥匙"，先写在前面方便对照：

| 名称 | 用途 | 形态 | 存放位置 |
|------|------|------|----------|
| `PROVIDERS_JSON` | 你的真实订阅链接 | JSON 文本 | 源仓库 GitHub Secret（方式 A）/ 本地 `local_providers.json`（方式 B） |
| `DIST_WRITE_PAT` | CI 写产物仓库 | GitHub Fine-grained PAT | 源仓库 GitHub Secret |
| `DIST_READ_PAT`  | 设备拉产物仓库 | GitHub Fine-grained PAT | 各设备本地文件，权限 600 |
| `URL`            | 单台设备的订阅地址 | GitHub Contents API URL（见 §6.1/§7.1） | 设备本地 `/etc/sing-box-updater/url` |

---

## 1. 前置准备

- GitHub 账号，已开启 2FA（创建 fine-grained PAT 需要）
- 源仓库 `sing-box-subscribe` 已是私有
- 已用 `python main.py --providers ./local_providers.json --template_index=0` 在本地跑通过一次生成
- **构建端**（GitHub Actions 容器 / 本地生成机）需要：Python 3.11+、`jq`、`sing-box`（用于产物校验）
- **设备端**只需要：`curl`、`sing-box`（macOS 用 brew，Linux 用包管理器或 release 二进制）；**不需要 jq**

---

## 2. 创建产物仓库（dist repo）

在 GitHub 创建一个 **新的私有仓库**，建议命名 `sing-box-config-dist`。

```bash
# 本地初始化，第一次推个空 README 占位
mkdir /tmp/sing-box-config-dist && cd $_
git init -b main
echo "# generated configs, do not edit by hand" > README.md
git add README.md
git commit -m "init"
git remote add origin git@github.com:<your-user>/sing-box-config-dist.git
git push -u origin main
```

> 为什么独立仓库：产物每次生成内容差异巨大、还可能含敏感字段（节点名、域名规则），不该污染主代码仓库的 git 历史；以后想把订阅交给别人订阅、或独立轮换 PAT 都更方便。

---

## 3. 创建两枚 Fine-grained PAT

GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token。

**Token #1 — `DIST_WRITE_PAT`（CI 写入用）**

- Resource owner: 你自己
- Repository access: **Only select repositories** → `sing-box-config-dist`
- Permissions → Repository permissions:
  - `Contents`: **Read and write**
  - `Metadata`: Read（必选）
- Expiration: 90 天（到期前 GitHub 会邮件提醒，按期轮换）

**Token #2 — `DIST_READ_PAT`（设备读取用）**

- Resource owner: 你自己
- Repository access: Only select repositories → `sing-box-config-dist`
- Permissions → Repository permissions:
  - `Contents`: **Read-only**
  - `Metadata`: Read
- Expiration: 90 天

> 两把 token 严格分权。即使设备被偷或日志泄露，攻击者也只能读，不能改产物仓库。

把两个 token 字符串临时记下，下面会用到。

---

## 4. 生成方式 A：GitHub Actions（推荐）

在 **源仓库** `sing-box-subscribe` 操作。

### 4.1 注入 Secrets

源仓库 Settings → Secrets and variables → Actions → New repository secret：

| Secret 名 | 值 |
|-----------|----|
| `PROVIDERS_JSON` | 本地 `local_providers.json` 的完整内容（粘贴 JSON 文本） |
| `DIST_WRITE_PAT` | 上一步的 Token #1 |

### 4.2 创建 workflow

新建 `.github/workflows/build-config.yml`：

```yaml
name: build-config

on:
  push:
    branches: [main]
    paths:
      - 'config_template/**'
      - 'main.py'
      - 'tool.py'
      - 'parsers/**'
      - '.github/workflows/build-config.yml'
  schedule:
    - cron: '17 */6 * * *'   # 每 6 小时刷新一次（订阅本身可能更新）
  workflow_dispatch:

concurrency:
  group: build-config
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Install sing-box (for `sing-box check`)
        run: |
          curl -fsSL https://sing-box.app/install.sh | sh
          sing-box version

      - name: Write providers secret to disk
        env:
          PROVIDERS_JSON: ${{ secrets.PROVIDERS_JSON }}
        run: |
          printf '%s' "$PROVIDERS_JSON" > local_providers.json
          python -c "import json; json.load(open('local_providers.json'))"  # 校验 JSON

      - name: Generate variants
        run: |
          mkdir -p dist
          # 在这里把你要的变体逐行列出：<输出文件名> <模板路径>
          variants=(
            "macos/ai.json         config_template/ai/tun-macos.json"
            "macos/streaming.json  config_template/streaming/tun.json"
            "linux/ai.json         config_template/ai/tun-linux.json"
            "linux/streaming.json  config_template/streaming/tun-linux.json"
          )
          for v in "${variants[@]}"; do
            out=$(echo "$v" | awk '{print $1}')
            tpl=$(echo "$v" | awk '{print $2}')
            mkdir -p "dist/$(dirname "$out")"
            # 用 jq 临时覆写 config_template + save_config_path
            jq --arg tpl "$tpl" --arg out "dist/$out" \
               '.config_template=$tpl | .save_config_path=$out' \
               local_providers.json > _providers.json
            python main.py --providers ./_providers.json
            # 验证产物合法
            sing-box check -c "dist/$out" 2>/dev/null || \
              { echo "::error::sing-box check failed for $out"; exit 1; }
          done
          # 写一个版本戳，方便设备端调试
          echo "${{ github.sha }} $(date -u +%FT%TZ)" > dist/VERSION

      - name: Push to dist repo
        env:
          DIST_WRITE_PAT: ${{ secrets.DIST_WRITE_PAT }}
        run: |
          cd dist
          git init -q -b main
          git config user.name  "sing-box-bot"
          git config user.email "bot@users.noreply.github.com"
          git add .
          git commit -q -m "build: ${{ github.sha }}"
          git push -q --force \
            "https://x-access-token:${DIST_WRITE_PAT}@github.com/<your-user>/sing-box-config-dist.git" \
            main
```

要点：

- `--force` 推送是有意的：dist 仓库只关心"当前是什么"，不需要 history，省空间也更干净。
- `sing-box check` 在 CI 阶段就能拦截无效配置，避免坏配置发出去。
- 想新增变体时，只改 `variants=( ... )` 数组那一段。

### 4.3 触发与验证

```bash
# 推一个空 commit 触发首次构建
git commit --allow-empty -m "ci: bootstrap"
git push
```

到 Actions 标签页看绿；成功后去 dist 仓库应看到 `macos/`、`linux/`、`VERSION` 三类文件。

---

## 5. 生成方式 B：本地 launchd / cron

适合不想把订阅链接放进 GitHub Secret、或希望生成机器和设备分离时使用。在一台常开的机器（家里的 Mac mini / NAS / 小服务器）上跑。

### 5.1 项目准备

```bash
cd ~/dev/sing-box-subscribe
# local_providers.json 已就位，权限收紧
chmod 600 local_providers.json
```

### 5.2 包装脚本 `scripts/build-and-push.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
SRC_ROOT="$(pwd)"
DIST_DIR="${DIST_DIR:-$HOME/.cache/sing-box-dist}"
DIST_REMOTE="${DIST_REMOTE:-git@github.com:<your-user>/sing-box-config-dist.git}"

# 1) 准备 dist 工作区
if [ ! -d "$DIST_DIR/.git" ]; then
  git clone --depth 1 "$DIST_REMOTE" "$DIST_DIR"
fi
git -C "$DIST_DIR" fetch -q origin main
git -C "$DIST_DIR" reset -q --hard origin/main
find "$DIST_DIR" -mindepth 1 -maxdepth 1 ! -name '.git' ! -name 'README.md' -exec rm -rf {} +

# 2) 跑生成
variants=(
  "macos/ai.json         config_template/ai/tun-macos.json"
  "macos/streaming.json  config_template/streaming/tun.json"
  "linux/ai.json         config_template/ai/tun-linux.json"
  "linux/streaming.json  config_template/streaming/tun-linux.json"
)
for v in "${variants[@]}"; do
  out=$(echo "$v" | awk '{print $1}')
  tpl=$(echo "$v" | awk '{print $2}')
  mkdir -p "$DIST_DIR/$(dirname "$out")"
  jq --arg tpl "$tpl" --arg out "$DIST_DIR/$out" \
     '.config_template=$tpl | .save_config_path=$out' \
     local_providers.json > /tmp/_providers.json
  python main.py --providers /tmp/_providers.json
  sing-box check -c "$DIST_DIR/$out"
done
date -u +%FT%TZ > "$DIST_DIR/VERSION"

# 3) 提交并推送（无变化则 no-op）
cd "$DIST_DIR"
git add .
if git diff --cached --quiet; then
  echo "no changes"
else
  git -c user.name=local-builder -c user.email=builder@local commit -q -m "build: $(date -u +%FT%TZ)"
  git push -q --force origin main
fi
```

```bash
chmod +x scripts/build-and-push.sh
```

### 5.3 macOS：用 launchd 定时

`~/Library/LaunchAgents/com.local.singbox-build.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.local.singbox-build</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>cd $HOME/dev/sing-box-subscribe && ./scripts/build-and-push.sh</string>
  </array>
  <key>StartInterval</key><integer>21600</integer> <!-- 6h -->
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/tmp/singbox-build.out.log</string>
  <key>StandardErrorPath</key><string>/tmp/singbox-build.err.log</string>
</dict>
</plist>
```

```bash
launchctl load -w ~/Library/LaunchAgents/com.local.singbox-build.plist
launchctl start com.local.singbox-build  # 立即跑一次
tail -f /tmp/singbox-build.err.log
```

### 5.4 Linux：用 cron

```cron
17 */6 * * *  cd $HOME/dev/sing-box-subscribe && ./scripts/build-and-push.sh >> /tmp/singbox-build.log 2>&1
```

> 方式 B 的前提是这台机器已经做好了 `git push` 到 dist 仓库的免密（SSH key 或 PAT 写进 git credentials）。

---

## 6. 设备端 — macOS（brew + launchd）

> 适用场景：sing-box 通过 `brew services start sing-box` 启动，配置路径是 `$(brew --prefix)/etc/sing-box/config.json`。TUN 模式需要 root 启动，所以 updater 也用 **LaunchDaemon（root 上下文）**。

### 6.1 选定一个设备变体

每台设备订阅自己的那一份。比如这台 Mac 用 `macos/ai.json`：

```bash
sudo mkdir -p /etc/sing-box-updater
# Token 文件，仅 root 可读
echo '<DIST_READ_PAT>' | sudo tee /etc/sing-box-updater/token >/dev/null
sudo chmod 600 /etc/sing-box-updater/token

# 记录订阅 URL —— 使用 GitHub Contents API（对 fine-grained PAT 兼容最稳）
echo 'https://api.github.com/repos/<your-user>/sing-box-config-dist/contents/macos/ai.json' \
  | sudo tee /etc/sing-box-updater/url >/dev/null
sudo chmod 600 /etc/sing-box-updater/url
```

> 不用 `raw.githubusercontent.com`：fine-grained PAT 对 raw 主机的兼容性历史上反复过几次，Contents API 是官方文档明确支持的通道。配合 `Accept: application/vnd.github.raw` 直接返回文件原始内容，不是 base64。

### 6.2 updater 脚本 `/usr/local/sbin/singbox-update.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# LaunchDaemon 默认 PATH 不含 brew/sing-box，必须显式注入
# Intel Mac 把下面两个路径改成 /usr/local/bin/brew 和 /usr/local
BREW_BIN="/opt/homebrew/bin/brew"
eval "$("$BREW_BIN" shellenv)"

CONF_DIR="$(brew --prefix)/etc/sing-box"
CONF="$CONF_DIR/config.json"
ETAG_FILE="/var/lib/sing-box-updater/etag"
TOKEN="$(cat /etc/sing-box-updater/token)"
URL="$(cat /etc/sing-box-updater/url)"

mkdir -p "$CONF_DIR" "$(dirname "$ETAG_FILE")"

# TMP 要和 CONF 在同一卷，mv 才是原子的（rename(2)）
TMP="$(mktemp "$CONF_DIR/.config.json.XXXXXX")"
HDR="$(mktemp)"
trap 'rm -f "$TMP" "$HDR"' EXIT

ETAG_OPT=()
[ -f "$ETAG_FILE" ] && ETAG_OPT=(-H "If-None-Match: $(cat "$ETAG_FILE")")

HTTP_CODE=$(curl -sS -o "$TMP" -D "$HDR" -w '%{http_code}' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github.raw" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "${ETAG_OPT[@]}" "$URL")

case "$HTTP_CODE" in
  304) logger -t singbox-update "not modified"; exit 0 ;;
  200) ;;
  *)   logger -t singbox-update "fetch failed: HTTP $HTTP_CODE"; exit 1 ;;
esac

# 校验配置
if ! sing-box check -c "$TMP"; then
  logger -t singbox-update "invalid config, abort"
  exit 1
fi

# 内容真有变化才动
NEW_SHA=$(shasum -a 256 "$TMP" | awk '{print $1}')
OLD_SHA=$(shasum -a 256 "$CONF" 2>/dev/null | awk '{print $1}' || echo none)
if [ "$NEW_SHA" = "$OLD_SHA" ]; then
  grep -i '^etag:' "$HDR" | awk '{print $2}' | tr -d '\r\n' > "$ETAG_FILE" || true
  exit 0
fi

# 备份 → 原子替换（同卷 rename，BSD install 不保证原子，所以用 mv）
cp -p "$CONF" "$CONF.bak" 2>/dev/null || true
mv -f "$TMP" "$CONF"
chmod 644 "$CONF"
grep -i '^etag:' "$HDR" | awk '{print $2}' | tr -d '\r\n' > "$ETAG_FILE" || true

# 重启服务（brew 装的 sing-box）—— 不吞 stderr，失败要进日志
if ! brew services restart sing-box; then
  logger -t singbox-update "restart failed after writing $NEW_SHA"
  exit 1
fi
logger -t singbox-update "updated to $NEW_SHA, restarted"
```

```bash
sudo mkdir -p /usr/local/sbin
sudo install -m 0755 singbox-update.sh /usr/local/sbin/singbox-update.sh
```

> **macOS 平台分支**：脚本头部的 `BREW_BIN` 路径区分 Apple Silicon（`/opt/homebrew/bin/brew`）和 Intel（`/usr/local/bin/brew`）。`brew shellenv` 一次性把 PATH/MANPATH/INFOPATH 注入，比 fallback 到字面量更稳。

### 6.3 LaunchDaemon `/Library/LaunchDaemons/com.local.singbox-update.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.local.singbox-update</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>/usr/local/sbin/singbox-update.sh</string>
  </array>
  <key>StartInterval</key><integer>300</integer>     <!-- 5 分钟 -->
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/var/log/singbox-update.log</string>
  <key>StandardErrorPath</key><string>/var/log/singbox-update.log</string>
</dict>
</plist>
```

```bash
sudo chown root:wheel /Library/LaunchDaemons/com.local.singbox-update.plist
sudo chmod 644       /Library/LaunchDaemons/com.local.singbox-update.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.local.singbox-update.plist
sudo launchctl start com.local.singbox-update   # 立即触发一次
tail -f /var/log/singbox-update.log
```

卸载：

```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.local.singbox-update.plist
```

---

## 7. 设备端 — Linux（systemd timer）

> 适用场景：sing-box 以 `sing-box.service` 形式运行（包管理器装的常这样），配置在 `/etc/sing-box/config.json`。

### 7.1 选定订阅 URL 并写入凭据

```bash
sudo install -d -m 0700 /etc/sing-box-updater
echo '<DIST_READ_PAT>' | sudo tee /etc/sing-box-updater/token >/dev/null
sudo chmod 600 /etc/sing-box-updater/token

echo 'https://api.github.com/repos/<your-user>/sing-box-config-dist/contents/linux/ai.json' \
  | sudo tee /etc/sing-box-updater/url >/dev/null
sudo chmod 600 /etc/sing-box-updater/url

sudo install -d -m 0755 /var/lib/sing-box-updater
```

### 7.2 updater 脚本 `/usr/local/sbin/singbox-update.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

CONF=/etc/sing-box/config.json
ETAG_FILE=/var/lib/sing-box-updater/etag
TOKEN=$(cat /etc/sing-box-updater/token)
URL=$(cat /etc/sing-box-updater/url)

TMP=$(mktemp); HDR=$(mktemp)
trap 'rm -f "$TMP" "$HDR"' EXIT

ETAG_OPT=()
[ -f "$ETAG_FILE" ] && ETAG_OPT=(-H "If-None-Match: $(cat "$ETAG_FILE")")

HTTP_CODE=$(curl -sS -o "$TMP" -D "$HDR" -w '%{http_code}' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github.raw" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "${ETAG_OPT[@]}" "$URL")

case "$HTTP_CODE" in
  304) logger -t singbox-update "not modified"; exit 0 ;;
  200) ;;
  *)   logger -t singbox-update "fetch failed: HTTP $HTTP_CODE"; exit 1 ;;
esac

if ! sing-box check -c "$TMP"; then
  logger -t singbox-update "invalid config, abort"
  exit 1
fi

NEW_SHA=$(sha256sum "$TMP" | awk '{print $1}')
OLD_SHA=$(sha256sum "$CONF" 2>/dev/null | awk '{print $1}' || echo none)
if [ "$NEW_SHA" = "$OLD_SHA" ]; then
  grep -i '^etag:' "$HDR" | awk '{print $2}' | tr -d '\r\n' > "$ETAG_FILE" || true
  exit 0
fi

cp -p "$CONF" "$CONF.bak" 2>/dev/null || true
install -m 0644 "$TMP" "$CONF"
grep -i '^etag:' "$HDR" | awk '{print $2}' | tr -d '\r\n' > "$ETAG_FILE" || true

systemctl restart sing-box
logger -t singbox-update "updated to $NEW_SHA, restarted"
```

```bash
sudo install -m 0755 singbox-update.sh /usr/local/sbin/singbox-update.sh
```

### 7.3 service + timer

`/etc/systemd/system/singbox-update.service`：

```ini
[Unit]
Description=Update sing-box config from private dist repo
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/singbox-update.sh
```

`/etc/systemd/system/singbox-update.timer`：

```ini
[Unit]
Description=Periodically refresh sing-box config

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=30s
Persistent=true

[Install]
WantedBy=timers.target
```

启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now singbox-update.timer
sudo systemctl list-timers | grep singbox
journalctl -u singbox-update.service -n 50 --no-pager
```

> Persistent=true 让设备断电再上线时能补一次错过的执行。

---

## 8. 验证与故障排查

**手动跑一遍设备端拉取**（不重启服务）：

```bash
curl -I \
  -H "Authorization: Bearer $(sudo cat /etc/sing-box-updater/token)" \
  -H 'Accept: application/vnd.github.raw' \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  "$(sudo cat /etc/sing-box-updater/url)"
# 期望: HTTP/2 200，ETag: "..."
```

| 症状 | 排查方向 |
|------|----------|
| `HTTP 401/403` | PAT 过期 / 选错仓库 / 权限不是 Contents:Read |
| `HTTP 404` | URL 里仓库名/分支/路径打错；或 PAT 没勾上这个仓库 |
| `HTTP 304` 但本地配置确实老了 | 删除 ETag 缓存：`rm /var/lib/sing-box-updater/etag` |
| `sing-box check` 失败 | 看 CI 那一步的日志；本地用 `sing-box check -c <tmp>` 复现 |
| 重启后 TUN 起不来 | `journalctl -u sing-box -n 100` / macOS 看 `/var/log/sing-box.log`；用 `cp $CONF.bak $CONF` 回滚 |
| Actions 推送失败 | 检查 `DIST_WRITE_PAT` 是否过期，是否选了 dist 仓库 |

**快速回滚**到上一份配置：

```bash
# macOS (Apple Silicon；Intel 把两处 /opt/homebrew 改为 /usr/local)
sudo cp /opt/homebrew/etc/sing-box/config.json.bak /opt/homebrew/etc/sing-box/config.json
sudo /opt/homebrew/bin/brew services restart sing-box
# Linux
sudo cp /etc/sing-box/config.json.bak /etc/sing-box/config.json
sudo systemctl restart sing-box
```

---

## 9. 安全清单

- [ ] dist 仓库为私有，且**只有你**有 Collaborator 权限
- [ ] CI Secret 里的 `PROVIDERS_JSON` 没有出现在任何 push 的文件里（`local_providers.json` 已在 `.gitignore`，确认无误）
- [ ] 两枚 PAT 都是 fine-grained，仅授权到 dist 仓库
- [ ] 设备上 `/etc/sing-box-updater/token` 权限 `600`，owner `root`
- [ ] PAT 过期日历提醒（90 天）建好
- [ ] 设备上没有把 token 写进 shell history（统一用 `tee` + heredoc 写入，避免 `echo $TOKEN`）
- [ ] dist 仓库开启了 "Block force pushes" → **不要**开启，本方案 CI 需要 force push

---

## 10. 可选增强

- **失败通知**：updater 脚本里把 `exit 1` 之前加一行调用 [Bark](https://github.com/Finb/Bark)/Telegram bot/钉钉机器人，断网时心里有数。
- **金丝雀灰度**：让 dist 同时有 `macos/ai.json` 和 `macos/ai-canary.json` 两份产物（CI 的 `variants` 数组各列一行，模板可指向不同 branch 或不同 ruleset 版本）；指定一台设备的 `/etc/sing-box-updater/url` 指向 canary 那份，跑 24 小时无事再让其他设备切回正式版。
- **多 profile 切换**：updater 脚本读 `/etc/sing-box-updater/url`，所以"切换订阅"只需 `echo <new-url> | sudo tee /etc/sing-box-updater/url && sudo systemctl start singbox-update.service`（macOS 用 `sudo launchctl kickstart -k system/com.local.singbox-update`）。
- **CDN 加速**：本方案走 `api.github.com`，公共 GitHub 代理（gh-proxy 等）通常只代理 `raw.githubusercontent.com`，不能直接套。若 `api.github.com` 在你网络环境下慢，更稳的做法是在自己 VPS 上跑一层 nginx 反代到 `api.github.com`，注意保留 `Authorization`/`Accept` header 透传。

---

## 11. 迁移路径

从"网盘手动"切到本方案，建议分两阶段：

1. **影子运行 1–2 天**：先把 CI 跑起来推 dist 仓库，**手动**在一台备机上 `curl` 拉下来对比内容，确认与你手动生成的产物一致。
2. **逐设备切换**：每台设备装好 updater 后，停用网盘同步，先 `singbox-update.sh` 手动跑一次，确认服务正常再交给 timer/launchd 接管。

完成后即可把网盘里旧 config.json 归档/删除。
