#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用本地 audio.cpp-hub（IndexTTS2）生成介绍片旁白，并输出时长与字幕。

- 服务地址：http://127.0.0.1:18080
- 音色：/api/voices 里的参考音频（默认「神里绫华」）
- 产物：video/assets/vo/NN.wav、NN.vtt、video/vo.json

用法：python scripts/tts_local.py [--only 2] [--voice 8730b00d] [--list]
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

HUB = "http://127.0.0.1:18080"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "video", "assets", "vo")
PROFILE = {"modelId": "index_tts2", "weightsPath": "models/IndexTTS2-GGUF",
           "backend": "hip", "executableId": "d2b18b5b", "name": "video"}

LINES = [
    ("01", "二十一个环节，四十三份单证，四百八十三个字段。"),
    ("02", "数据散在十几个页面，抄一遍、算一遍、再核对一遍——错一个，整张发票重来。"),
    ("03", "填单助手把源头收在一屏：先看交易剖面。"),
    ("04", "二十一个履约环节，点哪一步，就只显示那一步要交的单。"),
    ("05", "改一个数，CIF、柜数、单据字段同时重算，校验当场给结论。"),
    ("06", "五国二百零九种商品，价差排行直接告诉你进什么。"),
    ("07", "一万一千条税则，关税、消费税、增值税逐项算清。"),
    ("08", "运费按九十条航线自动带价，两张预算表跟着联动。"),
    ("09", "九封函电，中英对照，一键生成。"),
    ("10", "四十三份单证，二十一份手填，八成字段自动填好。双击就能用，不装不联网。"),
]


def get(path, timeout=10):
    with urllib.request.urlopen(HUB + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body, timeout=600, raw=False):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(HUB + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read() if raw else json.loads(r.read().decode("utf-8"))


def ensure_instance():
    insts = get("/api/instances")
    ready = [i for i in insts if i.get("status") == "READY"]
    if ready:
        return ready[0]["instanceName"]
    print("启动 index_tts2 实例…")
    inst = post("/api/instances", PROFILE, timeout=60)
    for _ in range(120):
        time.sleep(2)
        for i in get("/api/instances"):
            if i["id"] == inst["id"] and i.get("status") == "READY":
                print("实例就绪：", i["instanceName"])
                return i["instanceName"]
        for i in get("/api/instances"):
            if i["id"] == inst["id"] and i.get("status") == "ERROR":
                raise SystemExit("实例启动失败：" + str(i.get("errorMessage")))
    raise SystemExit("实例启动超时")


def voices():
    return get("/api/voices")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path],
                         capture_output=True, text=True).stdout.strip()
    return round(float(out or 0), 3)


def vtt(path, text, dur):
    def ts(t):
        h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
        return "%02d:%02d:%06.3f" % (h, m, s)
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n1\n%s --> %s\n%s\n" % (ts(0), ts(dur), text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="只生成某一句，如 02")
    ap.add_argument("--voice", default="8730b00d", help="音色 vid，见 --list")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for v in voices():
            print(v["vid"], v["name"], round(v.get("durationSec") or 0, 1), v["path"])
        return

    model = ensure_instance()
    ref = next((v["path"] for v in voices() if v["vid"] == args.voice), None)
    if not ref:
        raise SystemExit("找不到音色 " + args.voice)
    os.makedirs(OUT, exist_ok=True)

    todo = [l for l in LINES if not args.only or l[0] == args.only]
    meta = {}
    jf = os.path.join(ROOT, "video", "vo.json")
    if os.path.exists(jf):
        meta = json.load(open(jf, encoding="utf-8"))

    for key, text in todo:
        t0 = time.time()
        print("生成", key, text[:18], "…", end="", flush=True)
        wav = post("/v1/audio/speech", {
            "model": model, "input": text, "voice_ref": ref,
            "language": "zh", "response_format": "wav",
        }, raw=True)
        p = os.path.join(OUT, key + ".wav")
        open(p, "wb").write(wav)
        d = duration(p)
        vtt(os.path.join(OUT, key + ".vtt"), text, d)
        meta[key] = {"text": text, "dur": d, "wav": "assets/vo/%s.wav" % key}
        print(" %.2fs（用时 %.0fs）" % (d, time.time() - t0))

    json.dump(meta, open(jf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    total = sum(v["dur"] for v in meta.values())
    print("合计 %.1f 秒 / %d 句" % (total, len(meta)))


if __name__ == "__main__":
    main()
