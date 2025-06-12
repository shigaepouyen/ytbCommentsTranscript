#!/usr/bin/env python3
"""
ytbComentsTranscript.py
————————————————————————————————————
• Exporte les commentaires (colonne is_owner) dans fichier/<titre>/comments_<id>_<titre>.csv
• Exporte la transcription FR (ou EN si pas de FR) :
      └─ fichier/<titre>/transcript_<id>_<titre>_<lang>.csv
      └─ fichier/<titre>/transcript_<id>_<titre>_<lang>.txt (texte brut nettoyé)

Prérequis
---------
1. config.ini dans le même dossier :
   [youtube]
   api_key = VOTRE_CLÉ_API

2. pip install --upgrade requests rich youtube_transcript_api yt-dlp
"""

# ─── Imports ────────────────────────────────────────────────────────────────
import os, re, csv, sys, logging, subprocess, configparser, string
from pathlib import Path
from typing  import List, Dict
from xml.etree.ElementTree import ParseError

import requests
from rich.progress import Progress, SpinnerColumn, TextColumn
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# ─── Configuration ──────────────────────────────────────────────────────────
TARGET_LANGS = ["fr", "en"]                 # priorité : fr puis en
cfg = configparser.ConfigParser(); cfg.read("config.ini")
API_KEY = cfg.get("youtube", "api_key", fallback=os.getenv("YOUTUBE_API_KEY"))
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
VIDEO_DIR   = Path(".")  # défini dynamiquement dans main()

os.system("clear" if os.name == "posix" else "cls")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

if not API_KEY:
    logging.error("⚠️  API YouTube non trouvée (config.ini ou env)."); sys.exit(1)

# ─── Helpers ────────────────────────────────────────────────────────────────
def _sanitize(txt: str) -> str:
    allowed = f"-_.() {string.ascii_letters}{string.digits}"
    return "".join(c if c in allowed else "_" for c in txt).strip().replace(" ", "_")

def extract_video_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()

    # Cas 1 : l’utilisateur a collé directement l’ID (11 caractères)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id

    # Cas 2 : URL standard ou courte → on recherche le pattern sans look‑behind
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url_or_id)
    if m:
        return m.group(1)

    raise ValueError("ID vidéo introuvable dans l’URL.")

def get_video_metadata(vid: str) -> Dict[str, str]:
    r = requests.get(f"{YOUTUBE_API}/videos",
                     params={"part": "snippet", "id": vid, "key": API_KEY},
                     timeout=10)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items: logging.error("Vidéo inaccessible."); sys.exit(1)
    sn = items[0]["snippet"]
    return {"channel_id": sn["channelId"], "title": sn["title"]}

# ─── Commentaires ───────────────────────────────────────────────────────────
def _comment_threads(vid: str):
    params = {"part":"snippet","videoId":vid,"maxResults":100,"textFormat":"plainText","key":API_KEY}
    while True:
        r = requests.get(f"{YOUTUBE_API}/commentThreads", params=params, timeout=10)
        r.raise_for_status(); data=r.json()
        yield from data.get("items", [])
        if "nextPageToken" in data: params["pageToken"]=data["nextPageToken"]
        else: break

def _replies(pid:str)->List[Dict]:
    params = {"part":"snippet","parentId":pid,"maxResults":100,"textFormat":"plainText","key":API_KEY}
    rep=[]
    while True:
        r=requests.get(f"{YOUTUBE_API}/comments",params=params,timeout=10)
        if r.status_code!=200: break
        d=r.json(); rep.extend(d.get("items",[]))
        if "nextPageToken" in d: params["pageToken"]=d["nextPageToken"]
        else: break
    return rep

def export_comments(vid:str, owner:str, safe_title:str):
    out = VIDEO_DIR / f"comments_{vid}_{safe_title}.csv"
    tot=0
    with open(out,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["type","author","text","likes","published_at","parent_id","is_owner"])
        for th in _comment_threads(vid):
            top=th["snippet"]["topLevelComment"]; sn=top["snippet"]; cid=top["id"]
            owner_flag = sn["authorChannelId"]["value"]==owner
            w.writerow(["comment",sn["authorDisplayName"],sn["textDisplay"],sn["likeCount"],sn["publishedAt"],"",owner_flag]); tot+=1
            for rp in _replies(cid):
                rs=rp["snippet"]; owner_flag=rs["authorChannelId"]["value"]==owner
                w.writerow(["reply",rs["authorDisplayName"],rs["textDisplay"],rs["likeCount"],rs["publishedAt"],cid,owner_flag]); tot+=1
    logging.info(f"✔︎ {tot} commentaires exportés → {out}")

# ─── Transcriptions ─────────────────────────────────────────────────────────
def _vtt_to_sec(ts:str)->float:
    ts=ts.split()[0]; h,m,sms=ts.split(":"); s,ms=sms.split(".")
    return int(h)*3600+int(m)*60+int(s)+int(ms)/1000

def _clean(raw:str)->str:
    txt = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>","",raw)   # timecodes
    txt = re.sub(r"</?c>","",txt)                        # balises <c>
    return txt.strip()

def fetch_transcript(vid:str, lang:str)->List[Dict]:
    try: return YouTubeTranscriptApi.get_transcript(vid, languages=[lang])
    except Exception: pass
    try: trs = YouTubeTranscriptApi.list_transcripts(vid)
    except Exception: trs=None
    if trs:
        for fn in [lambda: trs.find_manually_created_transcript([lang]).fetch(),
                   lambda: trs.find_generated_transcript([lang]).fetch()]:
            try: return fn()
            except Exception: pass
        for t in trs:
            if t.is_translatable:
                try: return t.translate(lang).fetch()
                except Exception: pass
    try:
        tmp=Path("/tmp/ytvtt"); tmp.mkdir(exist_ok=True)
        subprocess.run(["yt-dlp","--skip-download","--write-auto-sub",
                        f"--sub-lang={lang}","--sub-format","vtt",
                        "-o",f"{tmp}/%(id)s.%(ext)s",
                        f"https://youtu.be/{vid}","--quiet","--no-warnings"],
                       check=True)
        vtt=list(tmp.glob(f"{vid}*.vtt"))[0]
        seg=[]
        with vtt.open(encoding="utf-8") as fh:
            for line in fh:
                if "-->" not in line: continue
                try: start_raw,end_raw=line.strip().split(" --> ")
                except ValueError: continue
                start,end=start_raw.split()[0],end_raw.split()[0]
                text=[]
                for tline in fh:
                    tline=tline.rstrip()
                    if tline=="": break
                    text.append(tline)
                if text:
                    seg.append({"start":_vtt_to_sec(start),"duration":_vtt_to_sec(end)-_vtt_to_sec(start),"text":" ".join(text)})
        return seg
    except Exception as e:
        logging.warning(f"yt-dlp KO {lang}: {e}")
    return []

def export_transcript(vid:str, lang:str, segs:List[Dict], safe_title:str):
    if not segs:
        logging.warning(f"– Pas de transcription {lang}"); return
    csv_p = VIDEO_DIR / f"transcript_{vid}_{safe_title}_{lang}.csv"
    txt_p = VIDEO_DIR / f"transcript_{vid}_{safe_title}_{lang}.txt"
    with open(csv_p,"w",newline="",encoding="utf-8") as fc:
        w=csv.writer(fc); w.writerow(["start_sec","duration","text"])
        for s in segs: w.writerow([s["start"],s["duration"],s["text"]])
    with open(txt_p,"w",encoding="utf-8") as ft:
        ft.write(" ".join(_clean(s["text"]) for s in segs if s["text"].strip()))
    logging.info(f"✔︎ Transcription {lang} → {csv_p} & {txt_p}")

# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    try: vid=extract_video_id(input("🔗 URL/ID : ").strip())
    except ValueError as e: logging.error(e); sys.exit(1)

    meta=get_video_metadata(vid); owner=meta["channel_id"]; safe_title=_sanitize(meta["title"])
    global VIDEO_DIR; VIDEO_DIR=Path("fichier")/safe_title; VIDEO_DIR.mkdir(parents=True,exist_ok=True)
    logging.info(f"Chaîne : {owner}")
    logging.info(f"Dossier : {VIDEO_DIR}")

    with Progress(SpinnerColumn(),TextColumn("Export des commentaires…"),transient=True) as p:
        p.add_task("",total=None); export_comments(vid,owner,safe_title)

    # — FR en priorité
    seg_fr=fetch_transcript(vid,"fr")
    if seg_fr:
        with Progress(SpinnerColumn(),TextColumn("Transcription FR…"),transient=True) as p:
            p.add_task("",total=None); export_transcript(vid,"fr",seg_fr,safe_title)
    else:
        seg_en=fetch_transcript(vid,"en")
        if seg_en:
            with Progress(SpinnerColumn(),TextColumn("Transcription EN…"),transient=True) as p:
                p.add_task("",total=None); export_transcript(vid,"en",seg_en,safe_title)

    logging.info("🎉 Terminé.")

if __name__=="__main__":
    main()