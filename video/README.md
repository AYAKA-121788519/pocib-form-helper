# 介绍片（OpenFilm 工程）

60 秒横屏介绍片，画面是程序真实界面的缩放特写，旁白用本机 audio.cpp-hub 的 IndexTTS2 合成。

成片：`out/POCIB-intro-1080p.mp4`（1920×1080 · 30fps · 59.1s · −14 LUFS）

## 目录

| 文件 | 作用 |
| --- | --- |
| `film.html` | 时间线：10 个镜头 + 10 条旁白，由 `scripts/build_film.py` 生成，别手改 |
| `01-numbers.html` | 镜头 1：21 / 43 / 483 三个数字砸入 |
| `02-mess.html` | 镜头 2：单据卡片堆满屏幕 → 红字「错一个数，整张发票重来」 |
| `zoom.tpl` | 分区特写模板：取景窗 + 高亮框 + 标题 + 字幕，按参数生成 `shots/NN.html` |
| `shots/NN.html` | 生成物，每个分区一页（交易剖面 / 履约流程 / 派生值 / 选品 / 税则 / 预算 / 函电） |
| `end.html` | 收尾：43 份 / 21 份手填 / 80% 自动 → 品牌与一句话 |
| `regions.json` | 各分区在截图里的坐标（脚本量的，供改取景时参考） |
| `vo.json` | 每句旁白的文本与真实时长 |

`assets/`（截图、旁白 wav）、`out/`、`.film/`、`smoke/` 都在 `.gitignore` 里，不进仓库。

## 改一版

```bash
# 1. 抓界面截图（程序界面改了才需要重跑）
node scripts/shoot_shots.mjs

# 2. 改旁白文案 → 重新配音（TTS 服务要先开着）
python scripts/tts_local.py            # 全部重配
python scripts/tts_local.py --only 05  # 只重配第 5 句
python scripts/tts_local.py --list     # 看可用音色

# 3. 重排时间线（镜头时长自动跟着新旁白走）
python scripts/build_film.py

# 4. 看效果 / 出片
npx -y openfilm@latest look            # 整片联系表（会顺手起 Studio）
npx -y openfilm@latest look 16.5       # 单帧
npx -y openfilm@latest render --loudness=-14 --out out/POCIB-intro-1080p.mp4
npx -y openfilm@latest look --full out/POCIB-intro-1080p.mp4   # 逐帧查闪黑 / 跳帧
```

旁白文案在 `scripts/tts_local.py` 的 `LINES` 里，镜头取景在 `scripts/build_film.py` 的 `SHOTS` 里（`cx/cy0/cy1` 是截图坐标，`cy0≠cy1` 就是纵向摇镜）。

## 几个坑

- `shots/*.html` 里的图片路径要 `../assets/`，且 `zoom.tpl` 必须给 `img` 写死 `width:1920px`，否则图片按 3840 原始像素铺开，取景全错。
- 页面别写 `duration`，镜头长度用 `#t=0,长度` 给；否则会和旁白时长打架。
- 每个镜头的第 0 帧必须有画面，不然切点会闪一帧黑（`look --full` 会报 black）。
