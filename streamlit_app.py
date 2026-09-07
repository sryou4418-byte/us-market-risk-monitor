import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import requests, csv, os, threading, shutil, json, time, re, html
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path as _Path
from urllib.parse import quote

from loading_service import start as start_job, status as job_status
from news_categories import CATEGORIES, QUERIES, select as select_news
from market_loader import load as load_market_aux

def _esc(x): return html.escape(str(x))

st.set_page_config(page_title="미국 증시 위험 모니터", page_icon="🇺🇸", layout="wide")

# v3.48.1: card-style news category navigation with visible article counts.
# UI state must be initialized before any theme/navigation rendering.
_qp = st.query_params
_view = str(_qp.get("view", "dashboard"))
_theme = str(_qp.get("theme", "light"))
if _view not in ("dashboard", "risk", "heatmap", "news", "market"):
    _view = "dashboard"
if _theme not in ("light", "dark"):
    _theme = "light"

st.markdown("""<style>
:root{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Apple SD Gothic Neo","Noto Sans KR","Segoe UI",sans-serif}
html,body,[class*="css"],.stApp,.stMarkdown,.stCaption,button,input,textarea,select{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Apple SD Gothic Neo","Noto Sans KR","Segoe UI",sans-serif!important}
.block-container{max-width:1180px;padding-top:2.2rem;padding-bottom:4rem}
.dev-credit{font-size:12px;color:#8b8f98;font-weight:600;letter-spacing:-.01em;margin-top:-.35rem;margin-bottom:.35rem}
.app-title-row{display:flex;align-items:center;margin-top:2px;margin-bottom:2px;padding:7px 0 4px;overflow:visible}.app-title-text{font-size:2.35rem;line-height:1.24;font-weight:850;letter-spacing:-.055em;color:#20232b;margin:0;overflow:visible}.overview-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:12px 0 8px}.overview-card{border:1px solid #e3e6eb;border-radius:22px;padding:18px 20px;background:rgba(255,255,255,.80);min-height:154px;box-sizing:border-box}.overview-head{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:800;color:#555b65;margin-bottom:14px}.overview-head-icon{width:28px;height:28px;border:1px solid #e4e7eb;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;background:#fff;flex:0 0 28px}.overview-head-icon svg{width:17px;height:17px}.overview-main{display:flex;align-items:baseline;gap:6px;min-height:52px}.overview-score{font-size:44px;line-height:1.04;font-weight:840;letter-spacing:-.045em;color:#2b2f37}.overview-unit{font-size:15px;font-weight:700;color:#444a54}.overview-status{display:flex;align-items:center;gap:9px;font-size:42px;font-weight:820;letter-spacing:-.04em;color:#282c34;min-height:52px;line-height:1.04}.overview-status .signal-status-dot{width:11px;height:11px;flex-basis:11px}.overview-sub{font-size:12px;color:#737983;margin-top:9px;line-height:1.45;min-height:18px}.overview-delta{font-size:11.5px;color:#717781;border-top:1px solid #eceef1;margin-top:12px;padding-top:9px}.overview-count{display:inline-flex;align-items:center;align-self:center;padding:2px 6px;border-radius:999px;background:#f2f3f5;color:#656b74;font-size:10px;line-height:1.3;font-weight:750;margin-left:4px;white-space:nowrap;letter-spacing:-.01em}
.hero{border:1px solid #e5e7eb;border-radius:28px;padding:30px 32px;margin:12px 0 22px;background:rgba(255,255,255,.72)}
.hero-score{font-size:64px;line-height:1;font-weight:850;letter-spacing:-.06em;color:#30323a}
.score-row{display:flex;align-items:baseline;gap:14px;margin-top:6px;flex-wrap:wrap}
.score-unit{font-size:20px;font-weight:650;letter-spacing:-.02em;color:#30323a}
.risk-guide{font-size:13px;font-weight:600;color:#6b7280;background:#f3f4f6;border-radius:999px;padding:7px 11px;white-space:nowrap}
.risk-label{font-size:18px;font-weight:750;margin-top:8px;color:#20232b}
.delta-up{color:#e5484d!important;font-weight:750!important}.delta-down{color:#2878d7!important;font-weight:750!important}.delta-flat{color:#8b8f98!important;font-weight:650!important}
.risk-state{display:flex;align-items:center;gap:6px;font-size:13px;color:#6b7280;margin-top:7px}.risk-dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:0 0 8px}.risk-dot.vlow{background:#22a06b}.risk-dot.low{background:#78b84a}.risk-dot.mid{background:#e5b82e}.risk-dot.high{background:#ef8b2c}.risk-dot.vhigh{background:#e5484d}.risk-dot.na{background:#a1a1aa}
.hero-state{display:flex;align-items:center;gap:8px;font-size:18px;font-weight:750;margin-top:8px;color:#20232b}.hero-state .risk-dot{width:10px;height:10px;flex-basis:10px}
.recession-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:8px}.recession-card{border:1px solid #e5e7eb;border-radius:16px;padding:11px 13px;background:rgba(255,255,255,.78);min-height:72px}.recession-name{font-size:12px;font-weight:700;color:#656b74;margin-bottom:6px}.recession-value{font-size:19px;font-weight:800;color:#282c34;line-height:1.15}
.signal-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:12px 0 5px}.signal-card{border:1px solid #e5e7eb;border-radius:18px;padding:15px 16px;background:rgba(255,255,255,.78);min-height:96px}.signal-name{font-size:12px;font-weight:760;color:#737983;margin-bottom:9px;letter-spacing:-.01em}.signal-status{display:flex;align-items:center;gap:8px;min-height:25px}.signal-status-dot{width:10px;height:10px;border-radius:50%;display:inline-block;flex:0 0 10px}.signal-status-dot.normal{background:#22a06b}.signal-status-dot.watch{background:#e5b82e}.signal-status-dot.caution{background:#ef8b2c}.signal-status-dot.alert{background:#e5484d}.signal-value{font-size:21px;font-weight:850;color:#282c34;line-height:1.15;letter-spacing:-.025em}.signal-count{display:inline-flex;align-items:center;min-height:20px;padding:2px 7px;border-radius:999px;background:#f2f3f5;color:#656b74;font-size:10.5px;font-weight:750;white-space:nowrap}.signal-detail{font-size:11.5px;color:#737983;margin-top:8px;line-height:1.45;white-space:normal}
.small{font-size:13px;color:#6b7280}.hero-title{font-size:15px;font-weight:800;color:#555b65}.section{margin-top:30px;margin-bottom:10px}
div[data-testid="stMetric"]{border:1px solid #e5e7eb;border-radius:18px;padding:14px}
.data-status{font-size:12px;color:#6b7280;display:flex;align-items:center;gap:7px;margin:-2px 0 8px}.data-status span{width:7px;height:7px;border-radius:50%;background:#a1a1aa;animation:pulse 1.1s ease-in-out infinite}.data-status.done span{background:#22a06b;animation:none}
.loading-shell{border:1px solid #eceef1;border-radius:28px;padding:30px 32px;margin:20px 0;background:#fff}.loading-title,.loading-score,.loading-row span{background:linear-gradient(90deg,#f1f2f4 25%,#fafafa 50%,#f1f2f4 75%);background-size:200% 100%;animation:shimmer 1.2s infinite;border-radius:10px}.loading-title{height:18px;width:180px}.loading-score{height:58px;width:240px;margin-top:20px}.loading-row{display:flex;gap:12px;margin-top:24px}.loading-row span{display:block;height:70px;flex:1}.loading-text{font-size:13px;color:#8b8f98;margin-top:16px}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
.risk-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:10px}
.risk-card{position:relative;border:1px solid #e5e7eb;border-radius:18px;padding:16px 17px;background:rgba(255,255,255,.78);min-height:118px}
.risk-title{display:flex;align-items:center;gap:5px;font-size:15px;font-weight:750;color:#20232b;margin-bottom:13px}
.risk-score{font-size:27px;font-weight:850;line-height:1.05;letter-spacing:-.035em;color:#252831}
.risk-score span{font-size:13px;font-weight:650;color:#6b7280;letter-spacing:0}
.info-icon{appearance:none;-webkit-appearance:none;border:1.2px solid #7b818b;background:transparent;padding:0;margin:0;display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border-radius:50%;font-size:9px;line-height:1;font-weight:800;color:#626975;cursor:help;position:relative;outline:none;box-sizing:border-box}
.info-icon::before{content:'i';font-family:Arial,sans-serif}
.info-icon:hover,.info-icon:focus,.info-icon:focus-visible{background:#eef0f3;color:#32363f;border-color:#32363f}
.info-tip{visibility:hidden;opacity:0;pointer-events:none;position:absolute;z-index:999;left:50%;top:23px;transform:translateX(-50%) translateY(-2px);width:min(310px,76vw);padding:11px 12px;border:1px solid #dfe2e7;border-radius:12px;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,.12);font-size:12.5px;font-weight:500;line-height:1.55;color:#3d424b;text-align:left;transition:opacity .12s ease,transform .12s ease}
.info-icon:hover .info-tip,.info-icon:focus .info-tip,.info-icon:focus-visible .info-tip{visibility:visible;opacity:1;transform:translateX(-50%) translateY(0)}
.market-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:10px}
.market-card{border:1px solid #e5e7eb;border-radius:18px;padding:15px 16px;background:rgba(255,255,255,.82);min-height:118px;overflow:hidden}.market-card-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.spark-wrap{height:34px;margin-top:10px;opacity:.88}.spark-wrap svg{display:block;width:100%;height:34px}.spark-line{fill:none;stroke:#8b93a1;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.spark-base{stroke:#eef0f3;stroke-width:1}.overview-horizon{font-size:10.5px;font-weight:700;color:#8b8f98;margin-top:2px}.overview-signal-line{display:flex;align-items:center;gap:6px;font-size:11px;color:#6f7580;margin-top:8px}.overview-signal-line .signal-status-dot{width:8px;height:8px;flex-basis:8px}
.market-name{display:flex;align-items:center;gap:5px;font-size:13px;font-weight:700;color:#555b65;margin-bottom:9px}
.market-value{font-size:22px;font-weight:820;letter-spacing:-.025em;color:#242832;line-height:1.1}
.market-delta{font-size:12px;margin-top:7px;color:#6b7280;white-space:nowrap}
@media(max-width:768px){
  .block-container{padding-top:calc(env(safe-area-inset-top,0px) + 2.65rem)!important;padding-left:14px!important;padding-right:14px!important;padding-bottom:3rem}
  h1{font-size:1.72rem!important;line-height:1.18!important;letter-spacing:-.045em!important;margin-top:0!important;margin-bottom:.55rem!important;font-weight:800!important}
  .dev-credit{font-size:11px;margin-top:-.2rem;margin-bottom:.45rem}
  p,li,div{letter-spacing:-.015em}
  .hero{border-radius:22px;padding:22px 20px;margin:8px 0 18px}
  .hero-score{font-size:50px}.score-unit{font-size:16px}.risk-guide{font-size:11px;padding:6px 9px}.risk-label{font-size:16px}
  .section{margin-top:24px;margin-bottom:8px}.section h3{font-size:1.15rem!important}
  div[data-testid="stAlert"]{padding:14px 15px!important;border-radius:16px!important}
  div[data-testid="stAlert"] p{font-size:.93rem!important;line-height:1.58!important}
  .risk-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .risk-card{min-height:104px;padding:13px 12px}
  .risk-title{font-size:13px;margin-bottom:10px;gap:4px}.risk-score{font-size:23px}.risk-state{font-size:12px;gap:5px}.risk-dot{width:7px;height:7px;flex-basis:7px}
  .info-icon{width:14px;height:14px;font-size:9px;border-width:1px;cursor:pointer}
  .info-tip{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%) scale(.98);width:min(330px,86vw);font-size:13px;padding:14px 15px;border-radius:15px;box-shadow:0 18px 55px rgba(0,0,0,.20)}
  .info-icon:hover .info-tip,.info-icon:focus .info-tip,.info-icon:focus-visible .info-tip{transform:translate(-50%,-50%) scale(1)}
  .market-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .market-card{min-height:108px;padding:12px 12px}.spark-wrap{height:28px;margin-top:8px}.spark-wrap svg{height:28px}.market-name{font-size:12px;margin-bottom:7px}.market-value{font-size:19px}.market-delta{font-size:11px;white-space:normal}
  div[data-testid="stMetric"]{padding:12px}
  .recession-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.recession-card{min-height:64px;padding:9px 8px;border-radius:14px}.recession-name{font-size:10.5px;margin-bottom:5px}.recession-value{font-size:16px}
  .signal-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px}.signal-card{min-height:92px;padding:13px 11px;border-radius:15px}.signal-name{font-size:10.5px;margin-bottom:8px}.signal-status{gap:6px;min-height:22px}.signal-status-dot{width:9px;height:9px;flex-basis:9px}.signal-value{font-size:18px}.signal-count{font-size:9.5px;min-height:18px;padding:1px 6px}.signal-detail{font-size:10.5px;margin-top:7px;line-height:1.4}
  .app-title-row{padding:6px 0 3px}.app-title-text{font-size:1.82rem;line-height:1.24}.overview-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:10px 0 7px}.overview-card{min-height:130px;padding:12px 9px;border-radius:15px}.overview-head{gap:5px;font-size:10.5px;margin-bottom:10px;line-height:1.25}.overview-head-icon{width:20px;height:20px;border-radius:7px;flex-basis:20px}.overview-head-icon svg{width:12px;height:12px}.overview-main{min-height:38px}.overview-score{font-size:30px;line-height:1.04}.overview-unit{font-size:10.5px}.overview-status{gap:5px;font-size:29px;font-weight:820;min-height:38px;line-height:1.04}.overview-status .signal-status-dot{width:8px;height:8px;flex-basis:8px}.overview-sub{font-size:9.5px;margin-top:6px;line-height:1.35;min-height:25px}.overview-delta{font-size:9.5px;margin-top:7px;padding-top:6px}.overview-count{font-size:8px;padding:1px 5px;margin-left:1px}
}

.r38-dark .stApp{background:#0f141c!important;color:#eef2f7!important}
.r38-dark .r38-panel,.r38-dark .r38-hero-card,.r38-dark .r38-action,.r38-dark .r38-market-table{background:#171e28!important;border-color:#2a3442!important;color:#edf2f7!important}
.r38-dark .r38-section-title,.r38-dark .r38-card-title,.r38-dark .r38-signal-main,.r38-dark .r38-risk-score,.r38-dark .r38-metric-value,.r38-dark .r38-recession-value{color:#f3f6fa!important}
.r38-dark .r38-subtitle,.r38-dark .r38-credit,.r38-dark .r38-horizon,.r38-dark .r38-risk-name,.r38-dark .r38-metric-name,.r38-dark .r38-note,.r38-dark .r38-risk-foot,.r38-dark .r38-side-copy{color:#aeb8c5!important}
.r38-dark .r38-col-head,.r38-dark .r38-recession-card{background:#121923!important;border-color:#2a3442!important;color:#dce4ee!important}
.r38-dark .r38-metric,.r38-dark .r38-market-col{border-color:#27313e!important}
.r38-dark .r38-interpret{background:#10263a!important;border-color:#204566!important;color:#cde7fb!important}
.r38-dark .r38-interpret-label{color:#79c1ff!important}
.r38-dark .r38-callout{background:#2a171a!important;border-color:#553036!important;color:#f2cdd1!important}
.r38-dark .r38-callout.warn{background:#2a2114!important;border-color:#554523!important;color:#f1dfb3!important}
.r38-dark [data-testid="stExpander"]{background:#171e28!important;border-color:#2a3442!important}


.hm-summary{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:0 0 9px;padding:14px 16px;border:1px solid #dde3eb;border-radius:12px;background:#fff}
.hm-summary>div:first-child{display:flex;align-items:baseline;gap:10px;min-width:0}
.hm-summary strong{font-size:15px;color:#1b2330;white-space:nowrap}
.hm-summary span{font-size:11px;color:#84909e}
.hm-breadth{font-size:12px!important;font-weight:750!important;color:#5d6876!important;white-space:nowrap}
.tm-help{margin:0 0 10px;padding:0 2px;font-size:10.5px;color:#7b8694}
.tm-viewport{width:100%;overflow:auto;border:1px solid #dde3eb;border-radius:12px;background:#eef1f4;-webkit-overflow-scrolling:touch;touch-action:pan-x pan-y pinch-zoom}
.tm-wrap{position:relative;width:100%;height:min(72vw,760px);min-height:600px;overflow:visible;background:#eef1f4}
.tm-tile{position:absolute;box-sizing:border-box;border:1px solid rgba(255,255,255,.72);padding:5px 6px;overflow:visible;display:flex;flex-direction:column;justify-content:center;outline:none;cursor:pointer}
.tm-tile:focus{z-index:9;box-shadow:inset 0 0 0 2px rgba(255,255,255,.95)}
.tm-symbol{font-size:10px;font-weight:900;line-height:1.02;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.tm-change{margin-top:2px;font-size:8px;font-weight:850;line-height:1.02;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.tm-name{margin-top:2px;font-size:7px;font-weight:650;opacity:.8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tm-tile.md .tm-symbol{font-size:12px}.tm-tile.md .tm-change{font-size:9px}.tm-tile.md .tm-name{font-size:7.5px}
.tm-tile.lg .tm-symbol{font-size:17px}.tm-tile.lg .tm-change{font-size:12px}.tm-tile.lg .tm-name{font-size:9px}
.tm-tile.sm .tm-name{display:none}
.tm-tile.xs .tm-symbol,.tm-tile.xs .tm-change,.tm-tile.xs .tm-name{display:none}
.tm-tile:focus::after{
  content:attr(data-symbol) " · " attr(data-name) "\\A" attr(data-change) "   현재가 " attr(data-price) "\\A" "S&P500 비중 " attr(data-weight);
  white-space:pre;position:absolute;z-index:9999;left:0;top:calc(100% + 6px);transform:none;
  min-width:220px;max-width:min(290px,calc(100vw - 36px));box-sizing:border-box;padding:10px 12px;border-radius:9px;
  background:rgba(15,23,34,.95);color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.26);
  font:750 11.5px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;text-align:left;pointer-events:none
}
.tm-sector-label{position:absolute;z-index:6;pointer-events:none;padding:5px 8px;border-radius:5px;background:rgba(10,18,28,.82);color:#fff;font-size:13px;font-weight:900;line-height:1.05;letter-spacing:-.15px;box-shadow:0 1px 4px rgba(0,0,0,.18)}
.tm-sector-label span{font-weight:800;opacity:.9;font-size:10px;margin-left:2px}
.tm-sector-outline{position:absolute;z-index:5;pointer-events:none;box-sizing:border-box;border:3px solid rgba(255,255,255,.96);box-shadow:inset 0 0 0 1px rgba(17,26,38,.18)}
.r38-dark .tm-sector-outline{border-color:rgba(245,248,252,.9);box-shadow:inset 0 0 0 1px rgba(0,0,0,.5)}

.r38-dark .hm-summary{background:#171e28;border-color:#2a3442}
.r38-dark .hm-summary strong{color:#f2f5f9}.r38-dark .hm-summary span,.r38-dark .tm-help{color:#9aa7b6}
.r38-dark .tm-viewport,.r38-dark .tm-wrap{background:#111823;border-color:#2a3442}
@media(max-width:780px){
  .hm-summary{align-items:flex-start;flex-direction:column;gap:6px}
  .hm-summary>div:first-child{display:block}
  .hm-summary>div:first-child span{display:block;margin-top:3px}
  .tm-help{font-size:9.5px;line-height:1.45}
  /* v3.46: mobile heatmap is fit-to-screen. No horizontal map canvas by default. */
  .tm-viewport{height:auto;min-height:0;overflow:visible;border-radius:10px}
  .tm-wrap{width:100%;height:auto;min-height:0;max-height:none;aspect-ratio:1.52/1}
  .tm-tile{padding:1px 2px;border-width:.6px}
  .tm-symbol{font-size:5.5px}.tm-change{font-size:4.8px;margin-top:1px}.tm-name{display:none}
  .tm-tile.md .tm-symbol{font-size:7px}.tm-tile.md .tm-change{font-size:5.5px}
  .tm-tile.lg .tm-symbol{font-size:9px}.tm-tile.lg .tm-change{font-size:6.5px}.tm-tile.lg .tm-name{display:none}
  .tm-sector-label{font-size:6.5px;padding:2px 3px;border-radius:3px}
  .tm-sector-label span{font-size:5.5px;margin-left:1px}
  .tm-sector-outline{border-width:1.5px}
  .tm-tile:focus{z-index:20}
  .tm-tile:focus::after{left:0;top:calc(100% + 3px);min-width:185px;max-width:230px;font-size:10px;padding:8px 9px}
}

.news-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 12px}
.news-toolbar-note{font-size:11px;color:#7d8998}
.news-filter-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:8px 0 16px}
.news-filter-card,.news-filter-card:link,.news-filter-card:visited,.news-filter-card:hover,.news-filter-card:active{color:#26313e!important;text-decoration:none!important}
.news-filter-card{display:flex;align-items:center;gap:10px;min-width:0;min-height:68px;padding:11px 12px;border:1px solid #dde3eb;border-radius:13px;background:#fff;box-sizing:border-box;transition:border-color .14s ease,background .14s ease,box-shadow .14s ease,transform .14s ease}
.news-filter-card:hover{border-color:#b6c3d8;box-shadow:0 5px 16px rgba(36,52,78,.08);transform:translateY(-1px)}
.news-filter-card.active{border-color:#4f70dc;background:#eef3ff;box-shadow:0 0 0 1px rgba(79,112,220,.16)}
.news-filter-icon{display:flex;align-items:center;justify-content:center;width:31px;height:31px;flex:0 0 31px;border-radius:10px;background:#f1f4f8;color:#647389;font-size:15px;font-weight:850}
.news-filter-card.active .news-filter-icon{background:#4f70dc;color:#fff}
.news-filter-copy{min-width:0;display:flex;flex-direction:column;gap:3px}
.news-filter-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11.5px;font-weight:820;letter-spacing:-.02em}
.news-filter-count{font-size:9.5px;color:#8a95a3;font-weight:700}
.news-filter-card.active .news-filter-name{color:#3154c3}.news-filter-card.active .news-filter-count{color:#657dc4}
.news-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
.news-card{min-height:112px;padding:14px 15px 13px;border:1px solid #dde3eb;border-radius:12px;background:#fff;box-sizing:border-box}
.news-meta{display:flex;align-items:center;gap:6px;margin-bottom:8px;color:#8a95a3;font-size:10px;white-space:nowrap;overflow:hidden}
.news-category{display:inline-flex;align-items:center;height:20px;padding:0 7px;border-radius:999px;background:#eef3ff;color:#4565c5;font-weight:800}
.news-title{display:block;color:#19222d!important;text-decoration:none!important;font-size:13.5px;font-weight:780;line-height:1.42}
.news-go{margin-top:10px;color:#758190;font-size:9.5px;font-weight:700}
.r38-dark .news-card{background:#171e28;border-color:#2a3442}
.r38-dark .news-title{color:#f0f3f7!important}
.r38-dark .news-meta,.r38-dark .news-go,.r38-dark .news-toolbar-note{color:#9ba7b5}
.r38-dark .news-category{background:#22345f;color:#b8c8ff}
.r38-dark .news-filter-card{background:#171e28;border-color:#2a3442;color:#e8edf4!important}
.r38-dark .news-filter-card:hover{border-color:#46566d;box-shadow:0 5px 18px rgba(0,0,0,.2)}
.r38-dark .news-filter-card.active{background:#20315c;border-color:#6987e8}.r38-dark .news-filter-card.active .news-filter-name{color:#dce5ff}.r38-dark .news-filter-card.active .news-filter-count{color:#aebff2}
.r38-dark .news-filter-icon{background:#242e3c;color:#aeb9c8}.r38-dark .news-filter-card.active .news-filter-icon{background:#5a78da;color:#fff}
@media(max-width:780px){.news-filter-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.news-filter-card{min-height:61px;padding:9px 10px}.news-filter-icon{width:29px;height:29px;flex-basis:29px}.news-filter-name{font-size:11px}.news-list{grid-template-columns:1fr}.news-card{min-height:104px;padding:13px}.news-title{font-size:13px}}


.r38-nav-item,
.r38-nav-item:link,
.r38-nav-item:visited,
.r38-nav-item:hover,
.r38-nav-item:active{
  color:#fff!important;
  text-decoration:none!important;
  white-space:nowrap!important;
}
.r38-nav-item{opacity:.86}
.r38-nav-item.active{opacity:1}
.r38-nav-item:hover{opacity:1}
.r38-nav-item .r38-nav-icon{color:#fff!important}


.risk-detail-hero{display:grid;grid-template-columns:1.15fr .85fr;gap:12px;margin-bottom:12px}
.risk-score-card,.risk-explain-card,.risk-flow-card,.risk-reasons-card,.risk-band-card,.risk-signal-card,.risk-component-card{border:1px solid #dde3eb;border-radius:14px;background:#fff;box-sizing:border-box}
.risk-score-card{padding:20px 22px;display:flex;align-items:center;justify-content:space-between;gap:18px}
.risk-score-main{display:flex;align-items:flex-end;gap:8px}.risk-score-num{font-size:72px;line-height:.9;font-weight:900;letter-spacing:-2px;color:#2459d5}.risk-score-den{font-size:21px;color:#6f7a88;margin-bottom:5px}
.risk-score-side{display:flex;flex-direction:column;gap:7px;align-items:flex-start}.risk-badge{display:inline-flex;align-items:center;height:32px;padding:0 10px;border-radius:8px;border:1px solid #9cb7f6;background:#f5f8ff;color:#2459d5;font-size:13px;font-weight:800}.risk-delta{font-size:12.5px;color:#7d8998}
.risk-explain-card{padding:20px 22px;display:flex;align-items:center;font-size:15px;line-height:1.55;color:#334050}.risk-section-title{font-size:17px;font-weight:850;color:#1b2430;margin-bottom:12px}
.risk-detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}.risk-flow-card,.risk-reasons-card,.risk-band-card,.risk-signal-card{padding:16px}
.risk-flow{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.risk-flow-step{padding:12px 8px;border:1px solid #dde3eb;border-radius:10px;background:#fbfcfe;text-align:center}.risk-flow-label{font-size:11px;color:#7f8a98;min-height:28px}.risk-flow-value{font-size:29px;font-weight:900;color:#2459d5;margin-top:3px}.risk-flow-sub{font-size:10px;color:#98a1ad;margin-top:3px}
.risk-signal-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.risk-signal-box{padding:14px;border:1px solid #dde3eb;border-radius:10px;background:#fbfcfe}.risk-signal-count{font-size:32px;font-weight:900;color:#2459d5}.risk-signal-label{font-size:12.5px;color:#7d8998}
.risk-components{display:grid;grid-template-columns:1fr 1fr;gap:8px}.risk-component-card{padding:12px 14px}.risk-component-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.risk-component-name{font-size:13.5px;font-weight:800;color:#26313e}.risk-component-score{font-size:17px;font-weight:900;color:#1f2a37}
.risk-bar{height:7px;border-radius:999px;background:#e9edf3;overflow:hidden;margin-top:8px}.risk-bar>span{display:block;height:100%;background:#2b5fd7;border-radius:999px}.risk-component-note{font-size:11px;color:#8b96a3;margin-top:6px}
.risk-reasons{display:flex;flex-direction:column;gap:9px}.risk-reason{display:flex;gap:10px;align-items:flex-start;font-size:13px;line-height:1.45;color:#34404e}.risk-reason-dot{width:21px;height:21px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;flex:none;background:#2b5fd7;color:white;font-size:11px;font-weight:900}
.risk-band-track{position:relative;display:grid;grid-template-columns:repeat(5,1fr);height:10px;border-radius:999px;overflow:visible;margin:20px 0 8px}.risk-band-track>span{height:10px}.risk-band-track span:nth-child(1){background:#376fd4}.risk-band-track span:nth-child(2){background:#46ad65}.risk-band-track span:nth-child(3){background:#e3bd3f}.risk-band-track span:nth-child(4){background:#e47a2f}.risk-band-track span:nth-child(5){background:#df4545}
.risk-band-marker{position:absolute;top:-6px;width:28px;height:22px;border-radius:11px;background:#2459d5;color:#fff;font-size:10px;font-weight:900;display:flex;align-items:center;justify-content:center;transform:translateX(-50%)}.risk-band-labels{display:grid;grid-template-columns:repeat(5,1fr);font-size:10.5px;color:#808b98;text-align:center}
.r38-dark .risk-score-card,.r38-dark .risk-explain-card,.r38-dark .risk-flow-card,.r38-dark .risk-reasons-card,.r38-dark .risk-band-card,.r38-dark .risk-signal-card,.r38-dark .risk-component-card{background:#171e28;border-color:#2a3442}
.r38-dark .risk-section-title,.r38-dark .risk-component-name,.r38-dark .risk-component-score,.r38-dark .risk-explain-card,.r38-dark .risk-reason{color:#f0f3f7}.r38-dark .risk-flow-step,.r38-dark .risk-signal-box{background:#121923;border-color:#2a3442}
@media(max-width:900px){.risk-detail-hero,.risk-detail-grid{grid-template-columns:1fr}.risk-components{grid-template-columns:1fr}}
@media(max-width:620px){.risk-score-num{font-size:60px}.risk-flow{grid-template-columns:1fr 1fr}.risk-signal-row{grid-template-columns:1fr}}


</style>""", unsafe_allow_html=True)

components.html(f"""<script>
(() => {{
  const dark = {str(_theme=="dark").lower()};
  const doc = window.parent.document;
  [doc.body, doc.querySelector('.stApp')].forEach(el => {{
    if (el) el.classList.toggle('r38-dark', dark);
  }});
}})();
</script>""", height=0)


FRED_CSV="https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FRED_RECENT="https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd={}"
SERIES={
    "기준금리":"EFFR","3개월물":"DGS3MO","2년물":"DGS2","10년물":"DGS10","30년물":"DGS30",
    "10년물기간프리미엄":"THREEFYTP10","10년물실질금리":"DFII10",
    "하이일드스프레드":"BAMLH0A0HYM2","BBB스프레드":"BAMLC0A4CBBB",
    "CPI":"CPIAUCSL","근원CPI":"CPILFESL","근원PCE":"PCEPILFE",
    "실업률":"UNRATE","신규실업수당":"ICSA","S&P500":"SP500","VIX":"VIXCLS"
}
WEIGHTS={"시장·밸류에이션":.25,"변동성":.10,"금리":.25,"신용":.15,"경기":.17,"물가":.08}

# v3.38 데이터 공급자 추상화: 산식/UI는 공급자 심볼 대신 내부 표준 키를 사용한다.
# 완성본에서 실시간 API로 교체할 때 이 매핑/어댑터만 바꾸면 된다.
CANONICAL_DATA={
    "EFFR":{"internal":"기준금리","provider":"FRED","symbol":"EFFR"},
    "US3M":{"internal":"3개월물","provider":"FRED+TREASURY","symbol":"DGS3MO"},
    "US2Y":{"internal":"2년물","provider":"FRED+TREASURY","symbol":"DGS2"},
    "US10Y":{"internal":"10년물","provider":"FRED+TREASURY","symbol":"DGS10"},
    "US30Y":{"internal":"30년물","provider":"FRED+TREASURY","symbol":"DGS30"},
    "SP500":{"internal":"S&P500","provider":"FRED","symbol":"SP500"},
    "VIX":{"internal":"VIX","provider":"FRED","symbol":"VIXCLS"},
    "HY_OAS":{"internal":"하이일드스프레드","provider":"FRED","symbol":"BAMLH0A0HYM2"},
    "UNEMP":{"internal":"실업률","provider":"FRED","symbol":"UNRATE"},
    "CPI":{"internal":"CPI","provider":"FRED","symbol":"CPIAUCSL"},
}

def canonical_series(data,key):
    meta=CANONICAL_DATA.get(key,{})
    return data.get(meta.get("internal",""),pd.Series(dtype=float))

ROOT_CACHE=_Path(os.environ.get("LOCALAPPDATA", str(_Path.home()))) / "RiskMonitor"
CACHE_DIR=ROOT_CACHE / "data"
CACHE_DIR.mkdir(parents=True,exist_ok=True)
RECENT_DAYS=1000
REFRESH_STATUS=ROOT_CACHE / "refresh_status.json"
FX_CACHE=ROOT_CACHE / "fx_snapshot.json"
CAPE_CACHE=ROOT_CACHE / "cape.csv"



HEATMAP_CACHE=ROOT_CACHE / "sp500_market_map_200.json"
HEATMAP_SECTOR_CACHE=ROOT_CACHE / "sp500_sector_map.json"
HEATMAP_TTL_SECONDS=600
HEATMAP_SECTOR_TTL_SECONDS=86400
HEATMAP_TARGET_COUNT=200
SLICKCHARTS_SP500_URL="https://www.slickcharts.com/sp500"
WIKI_SP500_URL="https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

SECTOR_KO={
    "Information Technology":"정보기술",
    "Communication Services":"커뮤니케이션",
    "Consumer Discretionary":"경기소비재",
    "Financials":"금융",
    "Health Care":"헬스케어",
    "Industrials":"산업재",
    "Consumer Staples":"필수소비재",
    "Energy":"에너지",
    "Utilities":"유틸리티",
    "Real Estate":"부동산",
    "Materials":"소재",
}

FALLBACK_SECTOR={
    "NVDA":"정보기술","AAPL":"정보기술","MSFT":"정보기술","AVGO":"정보기술","ORCL":"정보기술","AMD":"정보기술",
    "CSCO":"정보기술","IBM":"정보기술","CRM":"정보기술","QCOM":"정보기술","AMAT":"정보기술","TXN":"정보기술",
    "ADI":"정보기술","MU":"정보기술","NOW":"정보기술","PLTR":"정보기술","LRCX":"정보기술","KLAC":"정보기술",
    "GOOGL":"커뮤니케이션","GOOG":"커뮤니케이션","META":"커뮤니케이션","NFLX":"커뮤니케이션","TMUS":"커뮤니케이션",
    "DIS":"커뮤니케이션","T":"커뮤니케이션","VZ":"커뮤니케이션","CMCSA":"커뮤니케이션",
    "AMZN":"경기소비재","TSLA":"경기소비재","HD":"경기소비재","MCD":"경기소비재","BKNG":"경기소비재",
    "TJX":"경기소비재","LOW":"경기소비재","SBUX":"경기소비재","NKE":"경기소비재","MAR":"경기소비재","UBER":"경기소비재",
    "JPM":"금융","V":"금융","MA":"금융","BAC":"금융","WFC":"금융","GS":"금융","MS":"금융","AXP":"금융",
    "C":"금융","BLK":"금융","SCHW":"금융","SPGI":"금융","CB":"금융","BRK.B":"금융","COF":"금융","PGR":"금융",
    "LLY":"헬스케어","JNJ":"헬스케어","ABBV":"헬스케어","UNH":"헬스케어","MRK":"헬스케어","TMO":"헬스케어",
    "ABT":"헬스케어","ISRG":"헬스케어","DHR":"헬스케어","PFE":"헬스케어","AMGN":"헬스케어","GILD":"헬스케어",
    "VRTX":"헬스케어","BMY":"헬스케어","SYK":"헬스케어","CVS":"헬스케어",
    "GE":"산업재","CAT":"산업재","RTX":"산업재","UNP":"산업재","HON":"산업재","ETN":"산업재","DE":"산업재",
    "LMT":"산업재","UPS":"산업재","BA":"산업재","PH":"산업재","GEV":"산업재",
    "WMT":"필수소비재","COST":"필수소비재","PG":"필수소비재","KO":"필수소비재","PEP":"필수소비재",
    "PM":"필수소비재","MO":"필수소비재","MDLZ":"필수소비재",
    "XOM":"에너지","CVX":"에너지","COP":"에너지","EOG":"에너지","SLB":"에너지","MPC":"에너지",
    "NEE":"유틸리티","CEG":"유틸리티","SO":"유틸리티","DUK":"유틸리티",
    "WELL":"부동산","PLD":"부동산","AMT":"부동산",
    "LIN":"소재","SHW":"소재","FCX":"소재","NEM":"소재",
}

def _table_rows(html):
    from html.parser import HTMLParser
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.in_cell=False
            self.cell=[]
            self.row=[]
            self.rows=[]
        def handle_starttag(self,tag,attrs):
            if tag=="tr":
                self.row=[]
            elif tag in ("td","th"):
                self.in_cell=True
                self.cell=[]
        def handle_data(self,data):
            if self.in_cell:
                self.cell.append(data)
        def handle_endtag(self,tag):
            if tag in ("td","th") and self.in_cell:
                self.row.append(" ".join("".join(self.cell).split()))
                self.in_cell=False
            elif tag=="tr" and self.row:
                self.rows.append(self.row)
    p=Parser()
    p.feed(html)
    return p.rows

def _http_text(url,timeout=(3,8)):
    headers={
        "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/152.0 Safari/537.36",
        "Accept-Language":"en-US,en;q=0.9",
    }
    r=requests.get(url,headers=headers,timeout=timeout)
    r.raise_for_status()
    return r.text

def _read_heatmap_cache():
    try:
        return json.loads(HEATMAP_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {"updated":0,"items":[]}

def _read_sector_cache():
    try:
        return json.loads(HEATMAP_SECTOR_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {"updated":0,"map":{}}

def _write_json_atomic(path,obj):
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(json.dumps(obj,ensure_ascii=False),encoding="utf-8")
        tmp.replace(path)
        return True
    except Exception:
        return False

def _heatmap_cache_fresh():
    return _file_fresh(HEATMAP_CACHE,HEATMAP_TTL_SECONDS)

def _sector_cache_fresh():
    return _file_fresh(HEATMAP_SECTOR_CACHE,HEATMAP_SECTOR_TTL_SECONDS)

def _fetch_sector_map(force=False):
    cached=_read_sector_cache()
    if not force and _sector_cache_fresh() and cached.get("map"):
        return cached.get("map",{})

    mapping=dict(cached.get("map",{}))
    try:
        rows=_table_rows(_http_text(WIKI_SP500_URL,timeout=(3,8)))
        found={}
        for row in rows:
            if len(row)<3:
                continue
            sym=row[0].strip()
            sec=row[2].strip()
            if sec in SECTOR_KO and 1<=len(sym)<=8:
                found[sym]=SECTOR_KO[sec]
                found[sym.replace("-",".")]=SECTOR_KO[sec]
        if found:
            mapping.update(found)
            _write_json_atomic(HEATMAP_SECTOR_CACHE,{"updated":time.time(),"map":mapping})
    except Exception:
        pass

    for k,v in FALLBACK_SECTOR.items():
        mapping.setdefault(k,v)
    return mapping

def _pct(s):
    try:
        return float(str(s).replace("%","").replace(",","").strip())
    except Exception:
        return np.nan

def _num(s):
    import re
    s=str(s).replace(",","").replace("$","").strip()
    try:
        return float(s)
    except Exception:
        m=re.search(r"(-?\d+(?:\.\d+)?)",s)
        return float(m.group(1)) if m else np.nan

def _fetch_slickcharts_top200(force=False):
    cached=_read_heatmap_cache()
    if not force and _heatmap_cache_fresh() and cached.get("items"):
        return cached

    sector_map=_fetch_sector_map(force=False)
    try:
        rows=_table_rows(_http_text(SLICKCHARTS_SP500_URL,timeout=(3,9)))
        parsed=[]
        for row in rows:
            if len(row)<7:
                continue
            rank_txt=row[0].replace("#","").strip()
            if not rank_txt.isdigit():
                continue
            rank=int(rank_txt)
            company=row[1].strip()
            symbol=row[2].strip()
            weight=_pct(row[3])
            price=_num(row[4])
            change_pct=_pct(row[6])
            if rank<1 or not symbol or not np.isfinite(weight):
                continue
            sector=sector_map.get(symbol) or sector_map.get(symbol.replace("-",".")) or FALLBACK_SECTOR.get(symbol) or "기타"
            parsed.append({
                "rank":rank,"symbol":symbol,"name":company,"weight":weight,
                "price":price,"change":change_pct,"sector":sector,"stale":False
            })
        parsed=sorted(parsed,key=lambda x:x["rank"])[:HEATMAP_TARGET_COUNT]
        if len(parsed)>=150:
            snap={"updated":time.time(),"source":"Slickcharts (SPY holdings-based weight)","items":parsed}
            _write_json_atomic(HEATMAP_CACHE,snap)
            return snap
        raise ValueError(f"parsed only {len(parsed)} rows")
    except Exception:
        if cached.get("items"):
            cached=dict(cached)
            cached["stale"]=True
            for q in cached.get("items",[]):
                q["stale"]=True
            return cached
        return {"updated":0,"source":"unavailable","items":[],"stale":True}

def _heat_color(change,dark=False):
    if not np.isfinite(change):
        return "#313844" if dark else "#e7ebf0"
    mag=min(abs(float(change)),5.0)/5.0
    if change>0:
        lo=(86,35,40) if dark else (255,238,239)
        hi=(210,47,58) if dark else (229,59,70)
    elif change<0:
        lo=(27,48,77) if dark else (235,243,255)
        hi=(43,104,190) if dark else (47,112,201)
    else:
        return "#313844" if dark else "#eef1f4"
    rgb=tuple(round(lo[i]+(hi[i]-lo[i])*mag) for i in range(3))
    return "#%02x%02x%02x"%rgb

def _heat_text_color(change,dark=False):
    if dark:
        return "#f7f9fc"
    if np.isfinite(change) and abs(float(change))>=2.2:
        return "#ffffff"
    return "#17202b"

def _split_rect(items,x,y,w,h):
    if not items:
        return []
    if len(items)==1:
        return [(items[0],x,y,w,h)]
    total=sum(max(float(i[2]),0.0001) for i in items)
    target=total/2.0
    acc=0.0
    cut=1
    for idx,it in enumerate(items[:-1],1):
        acc+=max(float(it[2]),0.0001)
        if acc>=target:
            cut=idx
            break
    a,b=items[:cut],items[cut:]
    wa=sum(max(float(i[2]),0.0001) for i in a)
    ratio=wa/total if total else 0.5
    out=[]
    if w>=h:
        w1=w*ratio
        out.extend(_split_rect(a,x,y,w1,h))
        out.extend(_split_rect(b,x+w1,y,w-w1,h))
    else:
        h1=h*ratio
        out.extend(_split_rect(a,x,y,w,h1))
        out.extend(_split_rect(b,x,y+h1,w,h-h1))
    return out

def _heatmap_html(snapshot,dark=False):
    items=[q for q in snapshot.get("items",[])[:HEATMAP_TARGET_COUNT] if float(q.get("weight",0) or 0)>0]
    if not items:
        return ""

    sector_totals={}
    for q in items:
        sec=q.get("sector") or "기타"
        sector_totals[sec]=sector_totals.get(sec,0.0)+float(q.get("weight",0) or 0)

    sector_items=[(sec,sec,w) for sec,w in sorted(sector_totals.items(),key=lambda kv:kv[1],reverse=True)]
    sector_rects=_split_rect(sector_items,0,0,100,100)
    rect_map={sec:(x,y,w,h) for (sec,_,_),x,y,w,h in sector_rects}

    blocks=[]
    valid_changes=[]
    for sector,_ in sorted(sector_totals.items(),key=lambda kv:kv[1],reverse=True):
        sx,sy,sw,sh=rect_map[sector]
        rows=[q for q in items if (q.get("sector") or "기타")==sector]
        row_by_symbol={q["symbol"]:q for q in rows}
        inner=[(q["symbol"],q["name"],float(q["weight"])) for q in sorted(rows,key=lambda q:float(q.get("weight",0) or 0),reverse=True)]
        rects=_split_rect(inner,sx,sy,sw,sh)
        sec_changes=[]
        for (sym,name,weight),x,y,w,h in rects:
            q=row_by_symbol.get(sym,{})
            ch=float(q.get("change",np.nan))
            if np.isfinite(ch):
                valid_changes.append(ch)
                sec_changes.append(ch)
            price=float(q.get("price",np.nan))
            bg=_heat_color(ch,dark)
            fg=_heat_text_color(ch,dark)
            change_txt=f"{ch:+.2f}%" if np.isfinite(ch) else "N/A"
            weight_txt=f"{weight:.3f}%"
            price_txt=f"${price:,.2f}" if np.isfinite(price) else "N/A"
            area=w*h
            cls=" lg" if area>=190 else (" md" if area>=70 else (" sm" if area>=24 else " xs"))
            stale_txt=" · 지연" if q.get("stale") or snapshot.get("stale") else ""
            blocks.append(
                f'<div class="tm-tile{cls}" tabindex="0" role="button" '
                f'data-symbol="{_esc(sym)}" data-name="{_esc(name)}" data-change="{_esc(change_txt)}" '
                f'data-weight="{_esc(weight_txt)}" data-price="{_esc(price_txt)}" '
                f'style="left:{x:.4f}%;top:{y:.4f}%;width:{w:.4f}%;height:{h:.4f}%;background:{bg};color:{fg}" '
                f'title="{_esc(sym)} · {_esc(name)} · {change_txt} · 비중 {weight_txt}">'
                f'<div class="tm-symbol">{_esc(sym)}</div>'
                f'<div class="tm-change">{_esc(change_txt)}</div>'
                f'<div class="tm-name">{_esc(name)}{stale_txt}</div>'
                f'</div>'
            )

        blocks.append(
            f'<div class="tm-sector-outline" '
            f'style="left:{sx:.4f}%;top:{sy:.4f}%;width:{sw:.4f}%;height:{sh:.4f}%"></div>'
        )
        if sw*sh>=120:
            avg=float(np.mean(sec_changes)) if sec_changes else np.nan
            avg_txt=f"{avg:+.2f}%" if np.isfinite(avg) else ""
            blocks.append(
                f'<div class="tm-sector-label" style="left:{sx:.4f}%;top:{sy:.4f}%">'
                f'{_esc(sector)} <span>{_esc(avg_txt)}</span></div>'
            )

    up=sum(1 for x in valid_changes if x>0)
    down=sum(1 for x in valid_changes if x<0)
    flat=len(valid_changes)-up-down
    source_note="SPY 보유비중 기반" if "Slickcharts" in snapshot.get("source","") else "캐시 기반"
    return (
        '<div class="hm-summary">'
        '<div><strong>S&amp;P500 대표 200종목 시장 맵</strong>'
        f'<span>타일 면적 = {source_note} · 색상 = 일간 등락률</span></div>'
        f'<div class="hm-breadth">상승 {up} · 하락 {down} · 보합 {flat}</div>'
        '</div>'
        '<div class="tm-help">작은 타일은 텍스트를 생략합니다. 타일을 누르면 종목 상세가 표시됩니다. '
        '모바일에서는 전체 맵을 화면 폭에 맞춰 한눈에 보이도록 축소합니다. 작은 종목은 텍스트를 생략하고 큰 타일 위주로 표시합니다.</div>'
        f'<div class="tm-viewport"><div class="tm-wrap">{"".join(blocks)}</div></div>'
    )


NEWS_CACHE=ROOT_CACHE / "korean_econ_news.json"
NEWS_TTL_SECONDS=600
NEWS_QUERIES=QUERIES

def _read_news_cache():
    try: return json.loads(NEWS_CACHE.read_text(encoding="utf-8"))
    except Exception: return {"updated":0,"items":[]}

def _news_cache_fresh():
    return _file_fresh(NEWS_CACHE,NEWS_TTL_SECONDS)

def _clean_news_title(title,source=""):
    title=" ".join(str(title or "").split())
    if source:
        suffix=" - "+source.strip()
        if title.endswith(suffix): title=title[:-len(suffix)].rstrip()
    return title

def _fetch_google_news_rss(label,query):
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    q=quote(query,safe="")
    url=f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=(3,8)); r.raise_for_status()
    root=ET.fromstring(r.content); out=[]
    for item in root.findall(".//item")[:18]:
        title=item.findtext("title") or ""; link=item.findtext("link") or ""; pub=item.findtext("pubDate") or ""
        sn=item.find("source"); source=(sn.text or "").strip() if sn is not None else ""
        title=_clean_news_title(title,source)
        if not title or not link: continue
        try:
            dt=parsedate_to_datetime(pub)
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            published=dt.timestamp()
        except Exception: published=0
        out.append({"category":label,"title":title,"source":source or "Google News","link":link,"published":published})
    return out

def _fetch_news_snapshot(force=False):
    cached=_read_news_cache()
    if not force and _news_cache_fresh() and cached.get("items"): return cached
    items=[]; errors=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(_fetch_google_news_rss,l,q):l for l,q in NEWS_QUERIES}
        for fut in as_completed(futs):
            try: items.extend(fut.result())
            except Exception as e: errors.append(str(e))
    seen=set(); clean=[]
    for q in sorted(items,key=lambda z:float(z.get("published",0)),reverse=True):
        k=" ".join(q.get("title","").lower().split())
        if not k or k in seen: continue
        seen.add(k); clean.append(q)
    if clean:
        snap={"updated":time.time(),"items":clean[:144],"errors":errors,"source":"Google News RSS"}
        _write_json_atomic(NEWS_CACHE,snap); return snap
    if cached.get("items"):
        cached=dict(cached); cached["stale"]=True; return cached
    return {"updated":0,"items":[],"stale":True}

def _news_when(ts):
    if not ts: return ""
    try:
        dt=datetime.fromtimestamp(float(ts),tz=ZoneInfo("Asia/Seoul")); now=datetime.now(ZoneInfo("Asia/Seoul"))
        sec=max(0,(now-dt).total_seconds())
        if sec<3600: return f"{max(1,int(sec//60))}분 전"
        if sec<86400: return f"{int(sec//3600)}시간 전"
        if sec<172800: return "어제"
        return dt.strftime("%m.%d %H:%M")
    except Exception: return ""

def _news_html(items):
    cards=[]
    for q in items:
        cards.append(
            '<article class="news-card">'
            f'<div class="news-meta"><span class="news-category">{_esc(q.get("category",""))}</span>'
            f'<span>{_esc(" · ".join(q.get("tags",[])))}</span><span>{_esc(q.get("source",""))}</span><span>·</span><span>{_esc(_news_when(q.get("published",0)))}</span></div>'
            f'<a class="news-title" href="{_esc(q.get("link",""))}" target="_blank" rel="noopener noreferrer">{_esc(q.get("title",""))}</a>'
            '<div class="news-go">기사 보기 ↗</div></article>'
        )
    return '<div class="news-list">'+"".join(cards)+'</div>'

_NEWS_CATEGORY_ICONS={
    '전체':'▦','주요 뉴스':'★','연준·금리':'%','경기·고용':'↗','물가':'₩',
    '기업·실적':'▤','기술·AI·반도체':'AI','정책·무역':'⚖','지정학·에너지':'◆','한국 관련':'KR',
}
def _news_category_cards(items,active,theme):
    cards=[]
    for name in ['전체']+CATEGORIES:
        count=len(items) if name=='전체' else len(select_news(items,name))
        selected=name==active
        href=f'?view=news&theme={theme}&news_category={quote(name)}'
        cards.append(
            f'<a class="news-filter-card{" active" if selected else ""}" href="{href}" target="_self"'
            +(' aria-current="page"' if selected else '')+'>'
            f'<span class="news-filter-icon">{_esc(_NEWS_CATEGORY_ICONS.get(name,"•"))}</span>'
            f'<span class="news-filter-copy"><span class="news-filter-name">{_esc(name)}</span>'
            f'<span class="news-filter-count">기사 {count}개</span></span></a>'
        )
    return '<nav class="news-filter-grid" aria-label="뉴스 카테고리">'+''.join(cards)+'</nav>'


def _risk_level_label(score):
    s=float(score)
    if s<=20:return "매우 낮음"
    if s<=40:return "낮음"
    if s<=60:return "보통"
    if s<=80:return "높음"
    return "매우 높음"


def _risk_band(score):
    s=float(score)
    if s>=80: return "very_high"
    if s>=65: return "high"
    if s>=50: return "elevated"
    if s>=35: return "normal"
    return "low"

def _risk_phrase_bank():
    return {
        "시장·밸류에이션":{
            "very_high":["주가가 많이 오른 상태라 가격 부담이 매우 큽니다.","시장 과열 부담이 상당히 큰 편입니다."],
            "high":["주가 수준이 높아 조정 위험을 계속 지켜볼 필요가 있습니다.","시장 과열 부담이 꽤 큰 편입니다."],
            "elevated":["주가 수준이 다소 높은 편이라 추가 상승 여력보다 조정 위험을 함께 볼 필요가 있습니다.","시장 가격 부담이 평소보다 조금 높습니다."],
            "normal":["시장 가격 부담은 특별히 높지도 낮지도 않은 수준입니다.","시장 과열 정도는 보통 수준입니다."],
            "low":["시장 과열 부담은 크지 않습니다.","현재 주가 수준만 놓고 보면 과열 신호는 강하지 않습니다."],
        },
        "변동성":{
            "very_high":["주가 변동이 매우 커져 단기 불안이 강하게 나타나고 있습니다.","시장 흔들림이 매우 커진 상태입니다."],
            "high":["주가 변동이 커져 단기 불안이 높아진 상태입니다.","시장 흔들림이 평소보다 큰 편입니다."],
            "elevated":["주가 변동이 조금 커지고 있어 단기 흐름을 주의해서 볼 필요가 있습니다.","단기 시장 불안이 평소보다 조금 높습니다."],
            "normal":["주가 변동은 보통 수준입니다.","시장 흔들림은 평소 수준에 가깝습니다."],
            "low":["주가 변동은 비교적 안정적입니다.","현재 시장 흔들림은 크지 않습니다."],
        },
        "금리":{
            "very_high":["금리 부담이 매우 커 주식시장에 강한 압박 요인으로 작용하고 있습니다.","높은 금리와 금리 움직임이 시장 부담을 크게 키우고 있습니다."],
            "high":["금리 부담이 현재 시장의 주요 위험 요인 중 하나입니다.","장기금리 부담이 꽤 높은 편입니다."],
            "elevated":["금리 부담이 평소보다 조금 높은 편입니다.","금리 수준과 최근 흐름이 시장에 약간의 부담을 주고 있습니다."],
            "normal":["금리 위험은 보통 수준입니다.","금리 쪽 부담은 중간 정도입니다."],
            "low":["금리 부담은 비교적 낮은 편입니다.","현재 금리 여건은 시장에 큰 부담을 주는 수준은 아닙니다."],
        },
        "신용":{
            "very_high":["신용시장이 크게 불안해지고 있어 기업 자금조달 여건까지 주의해서 볼 필요가 있습니다.","회사채 시장의 불안이 매우 큰 상태입니다."],
            "high":["신용시장 불안이 커지고 있어 주식시장에도 부담이 될 수 있습니다.","회사채 시장이 평소보다 불안한 편입니다."],
            "elevated":["신용시장에 약간의 긴장감이 나타나고 있습니다.","회사채 시장의 부담이 조금 높아졌습니다."],
            "normal":["신용시장은 대체로 평소 수준입니다.","회사채 시장에서 특별한 이상 신호는 크지 않습니다."],
            "low":["신용시장은 비교적 안정적입니다.","기업 자금조달 여건에서 큰 불안 신호는 보이지 않습니다."],
        },
        "경기":{
            "very_high":["경기 둔화 신호가 매우 강해지고 있습니다.","고용과 경기 흐름에서 뚜렷한 악화 신호가 나타나고 있습니다."],
            "high":["경기 둔화 위험이 꽤 높아진 상태입니다.","고용과 경기 흐름이 약해지고 있어 주의가 필요합니다."],
            "elevated":["경기 둔화 가능성이 평소보다 조금 높아졌습니다.","고용과 경기 흐름이 다소 약해지고 있습니다."],
            "normal":["경기 위험은 보통 수준입니다.","경기 흐름은 아직 뚜렷한 악화 구간은 아닙니다."],
            "low":["경기 쪽 위험은 비교적 낮습니다.","고용과 경기 흐름은 대체로 안정적입니다."],
        },
        "물가":{
            "very_high":["물가 압력이 매우 높아 금리 인하 기대를 제약할 수 있습니다.","인플레이션 부담이 시장에 큰 압박으로 작용하고 있습니다."],
            "high":["물가 부담이 꽤 높아 금리 경로에 부담을 줄 수 있습니다.","인플레이션 압력이 여전히 높은 편입니다."],
            "elevated":["물가 압력이 조금 높은 편이라 금리 흐름과 함께 지켜볼 필요가 있습니다.","인플레이션 부담이 평소보다 약간 높습니다."],
            "normal":["물가 위험은 보통 수준입니다.","물가 흐름은 특별히 과열된 수준은 아닙니다."],
            "low":["물가 부담은 비교적 낮은 편입니다.","현재 인플레이션 압력은 크지 않습니다."],
        },
    }

def _choose_phrase(category, score, variant=0):
    bank=_risk_phrase_bank()
    band=_risk_band(score)
    arr=bank.get(category,{}).get(band,[])
    if not arr:
        return f"{category} 위험은 {score:.0f}점입니다."
    return arr[variant % len(arr)]

def _signal_text(names, kind):
    names=[str(x) for x in (names or []) if str(x).strip()]
    if not names:
        return ""
    joined=", ".join(names[:3])
    if kind=="structural":
        return f"중기적으로는 {joined} 신호가 잡혀 있어 조정 위험을 계속 지켜볼 필요가 있습니다."
    return f"단기적으로는 {joined} 신호가 나타나 시장이 빠르게 흔들릴 가능성을 주의해야 합니다."

def _risk_sentence_engine(category_scores, structural_count, rapid_count, structural_names=None, rapid_names=None, max_items=5):
    scores={k:float(v) for k,v in category_scores.items()}
    ordered=sorted(scores.items(), key=lambda kv:kv[1], reverse=True)
    low_ordered=sorted(scores.items(), key=lambda kv:kv[1])

    primary=ordered[0]
    secondary=ordered[1]
    stabilizer=low_ordered[0]

    reasons=[]
    reasons.append(_choose_phrase(primary[0], primary[1], 0))

    # Add a second risk driver only when it is meaningfully elevated.
    if secondary[1] >= 50:
        reasons.append(_choose_phrase(secondary[0], secondary[1], 1))

    # Add one stabilizer when it is truly helping.
    if stabilizer[1] <= 35 and stabilizer[0] not in (primary[0], secondary[0]):
        reasons.append(_choose_phrase(stabilizer[0], stabilizer[1], 0))

    structural_text=_signal_text(structural_names,"structural") if structural_count else ""
    rapid_text=_signal_text(rapid_names,"rapid") if rapid_count else ""
    if structural_text:
        reasons.append(structural_text)
    elif structural_count:
        reasons.append(f"구조적 위험신호가 {structural_count}개 있어 중기적인 조정 가능성은 계속 확인할 필요가 있습니다.")

    if rapid_text:
        reasons.append(rapid_text)
    elif rapid_count:
        reasons.append(f"급변 신호가 {rapid_count}개 있어 단기적으로 시장이 빠르게 흔들릴 가능성을 주의해야 합니다.")
    else:
        # Plain-language replacement for the old "즉각적인 시장 스트레스는 제한적입니다."
        reasons.append("지금 당장 시장이 크게 흔들릴 조짐은 많지 않습니다.")

    # De-duplicate and cap.
    out=[]
    for r in reasons:
        if r and r not in out:
            out.append(r)
        if len(out)>=max_items:
            break

    # Summary sentence: risk driver + stabilizer + near-term conclusion.
    high_name,high_score=primary
    low_name,low_score=stabilizer
    high_map={
        "시장·밸류에이션":"시장 과열",
        "변동성":"시장 변동성",
        "금리":"금리",
        "신용":"신용시장",
        "경기":"경기 둔화",
        "물가":"물가",
    }
    low_map={
        "시장·밸류에이션":"시장 과열",
        "변동성":"변동성",
        "금리":"금리",
        "신용":"신용시장",
        "경기":"경기",
        "물가":"물가",
    }

    if high_score>=65:
        lead=f"현재는 {high_map.get(high_name,high_name)} 부담이 가장 큽니다."
    elif high_score>=50:
        lead=f"현재는 {high_map.get(high_name,high_name)} 부담이 다른 요인보다 조금 큰 편입니다."
    else:
        lead="현재는 한 가지 위험 요인이 크게 튀는 상황은 아닙니다."

    if low_score<=35:
        balance=f"반면 {low_map.get(low_name,low_name)}는 비교적 안정적입니다."
    else:
        balance="다른 위험 요인들도 대체로 보통 수준에 가깝습니다."

    if rapid_count:
        ending="다만 단기 급변 신호가 있어 시장 움직임이 갑자기 커질 가능성은 주의해야 합니다."
    elif structural_count:
        ending="당장 큰 충격 신호는 강하지 않지만, 중기적인 위험 신호는 남아 있습니다."
    else:
        ending="지금 당장 시장이 크게 흔들릴 조짐은 많지 않습니다."

    summary=f"{lead} {balance} {ending}"
    return summary,out


# -----------------------------------------------------------------------------
# Market Status sentence engine v0.2
# Shared diagnostic layer for dashboard / future Market Status page.
# Composite-risk formulas are unchanged.
# -----------------------------------------------------------------------------
def _pct_ret_v02(s,n):
    z=s.dropna()
    if len(z)<=n:return np.nan
    return (float(z.iloc[-1])/float(z.iloc[-1-n])-1.0)*100.0

def _point_change_v02(s,n):
    z=s.dropna()
    if len(z)<=n:return np.nan
    return float(z.iloc[-1]-z.iloc[-1-n])

def _market_axis_flags_v02(sp,vix,y10,hy,bbb):
    sp5=_pct_ret_v02(sp,5); sp20=_pct_ret_v02(sp,20)
    vix5=_pct_ret_v02(vix,5); vix20=_pct_ret_v02(vix,20); vix_now=latest(vix)
    _y5=_point_change_v02(y10,5); _y20=_point_change_v02(y10,20)
    _hy5=_point_change_v02(hy,5); _hy20=_point_change_v02(hy,20)
    _b5=_point_change_v02(bbb,5); _b20=_point_change_v02(bbb,20)
    y5=_y5*100 if pd.notna(_y5) else np.nan; y20=_y20*100 if pd.notna(_y20) else np.nan
    hy5=_hy5*100 if pd.notna(_hy5) else np.nan; hy20=_hy20*100 if pd.notna(_hy20) else np.nan
    b5=_b5*100 if pd.notna(_b5) else np.nan; b20=_b20*100 if pd.notna(_b20) else np.nan
    equity=bool((pd.notna(sp5) and sp5<=-4.0) or (pd.notna(sp20) and sp20<=-7.0))
    vol=bool((pd.notna(vix_now) and vix_now>=22 and pd.notna(vix5) and vix5>=20) or (pd.notna(vix_now) and vix_now>=27) or (pd.notna(vix20) and vix20>=35 and pd.notna(vix_now) and vix_now>=20))
    rates=bool((pd.notna(y5) and y5>=15) or (pd.notna(y20) and y20>=40))
    credit=bool((pd.notna(hy5) and hy5>=15) or (pd.notna(hy20) and hy20>=30) or (pd.notna(b5) and b5>=8) or (pd.notna(b20) and b20>=18))
    axes={"주식":equity,"변동성":vol,"금리":rates,"신용":credit}
    metrics={"sp5":sp5,"sp20":sp20,"vix":vix_now,"vix5":vix5,"vix20":vix20,"y10_5bp":y5,"y10_20bp":y20,"hy_5bp":hy5,"hy_20bp":hy20,"bbb_5bp":b5,"bbb_20bp":b20}
    return axes,metrics

def _axis_recent_hits_v02(sp,vix,y10,hy,bbb,axis_name,lookback=5):
    idx=sp.dropna().index[-lookback:]
    hits=0
    for dt in idx:
        try:
            a,_=_market_axis_flags_v02(sp.loc[:dt],vix.loc[:dt],y10.loc[:dt],hy.loc[:dt],bbb.loc[:dt])
            hits+=int(bool(a.get(axis_name,False)))
        except Exception:
            pass
    return hits

def market_status_sentence_v02(sp,vix,y10,hy,bbb):
    axes,metrics=_market_axis_flags_v02(sp,vix,y10,hy,bbb)
    persistent={}
    for name,active in axes.items():
        persistent[name]=bool(active or _axis_recent_hits_v02(sp,vix,y10,hy,bbb,name,5)>=2)
    active=[k for k,v in persistent.items() if v]
    count=len(active)
    vix_now=metrics.get("vix",np.nan)
    credit_calm=not persistent["신용"]
    vol_calm=(not persistent["변동성"]) and (pd.isna(vix_now) or vix_now<20)
    if count>=3: confidence,strength="높음","strong"
    elif count==2: confidence,strength="보통 이상","medium"
    elif count==1: confidence,strength="보통","weak"
    else: confidence,strength="낮음","calm"
    aset=set(active)
    if count>=3:
        sentence="주가·변동성·금리·신용 가운데 여러 시장 축에서 부담이 동시에 나타나고 있습니다. 단기 시장 스트레스가 넓게 퍼지는지 주의해서 볼 필요가 있습니다."
    elif aset=={"주식","변동성"} and credit_calm:
        sentence="주가가 약해지면서 변동성이 높아지고 있습니다. 다만 신용시장은 아직 안정적이어서 불안이 금융시장 전반으로 확산됐다고 보기는 이릅니다."
    elif "금리" in aset and count==1 and credit_calm and vol_calm:
        sentence="장기금리가 빠르게 오르고 있지만 변동성과 신용시장은 안정적이어서 금융시장 전반의 불안으로 번지는 모습은 아직 뚜렷하지 않습니다."
    elif "금리" in aset and ("변동성" in aset or "신용" in aset):
        sentence="장기금리 부담이 커지는 가운데 변동성이나 신용시장에서도 스트레스가 함께 나타나고 있습니다. 금리 상승이 다른 시장으로 확산되는지 확인이 필요합니다."
    elif count==2:
        sentence=f"{active[0]}과 {active[1]}에서 부담이 함께 나타나고 있습니다. 아직 모든 시장으로 확산된 상황은 아니어서 추가 확인이 필요합니다."
    elif count==1:
        one={"주식":"주가가 약해지고 있지만 다른 시장의 확인 신호는 아직 충분하지 않습니다.","변동성":"변동성이 높아졌지만 다른 시장까지 불안이 확산됐다는 확인은 아직 부족합니다.","금리":"장기금리 상승 부담이 나타나고 있지만 다른 시장의 동반 불안은 아직 뚜렷하지 않습니다.","신용":"신용스프레드가 넓어지고 있지만 다른 시장의 동반 악화는 아직 뚜렷하지 않습니다."}
        sentence=one.get(active[0],"일부 시장 지표에서 부담이 나타나고 있지만 추가 확인이 필요합니다.")
    else:
        sentence="시장 전반에서 뚜렷한 단기 스트레스 확산 신호는 많지 않습니다."
    return {"sentence":sentence,"axes":persistent,"raw_axes":axes,"active_axes":active,"axis_count":count,"confidence":confidence,"strength":strength,"metrics":metrics}


def _market_aux_v345():
    path=ROOT_CACHE / 'market_aux_v348.json'
    out,state,_=load_market_aux(path,force=bool(globals().get('_manual_refresh',False)))
    if state.get('running'):
        @st.fragment(run_every='2s')
        def aux_progress():
            # Each completed symbol is persisted atomically. Rerun uses new data.
            st.caption('보조 시장 데이터 확인 중… 준비된 지표부터 표시합니다.')
            stamp=path.stat().st_mtime_ns if path.exists() else 0
            old=st.session_state.get('_aux_stamp348',-1)
            if stamp!=old or not job_status(path).get('running'):
                st.session_state['_aux_stamp348']=stamp
                st.rerun()
        aux_progress()
    elif state.get('error'):
        st.caption('일부 보조 데이터 갱신 실패 · 관측일과 자료 부족 표시를 확인하세요.')
    return out


def _ret_txt_v345(s,n):
    v=_pct_ret_v02(s,n); return "N/A" if pd.isna(v) else f"{v:+.1f}%"

def _bp_txt_v345(s,n):
    v=_point_change_v02(s,n); return "N/A" if pd.isna(v) else f"{v*100:+.0f}bp"

def _pctile_v345(s,window=252):
    z=s.dropna().tail(window)
    if len(z)<10:return np.nan
    cur=float(z.iloc[-1]); return float((z<=cur).mean()*100)

def _mcard_v345(title,value,state,detail=""):
    cls={"안정":"good","정상":"good","관찰":"warn","주의":"warn","경계":"warn","위험":"bad","참고":"info","확인 부족":"na"}.get(state,"na")
    return f'<div class="ms-card"><div class="ms-kicker">{_esc(title)}</div><div class="ms-value">{_esc(value)}</div><div class="ms-state {cls}">{_esc(state)}</div><div class="ms-detail">{_esc(detail)}</div></div>'

def _section_v345(title,body,note=""):
    n=('<div class="ms-note">'+_esc(note)+'</div>') if note else ''
    return f'<section class="ms-section"><div class="ms-title">{_esc(title)}</div>{body}{n}</section>'

def _market_status_cards_v345(scores):
    pairs=[("주식",scores.get("시장·밸류에이션",np.nan)),("금리",scores.get("금리",np.nan)),("신용",scores.get("신용",np.nan)),("변동성",scores.get("변동성",np.nan)),("경기",scores.get("경기",np.nan)),("물가",scores.get("물가",np.nan))]
    out=[]
    for n,v in pairs:
        state="확인 부족" if pd.isna(v) else ("안정" if v<40 else ("정상" if v<60 else ("주의" if v<80 else "위험")))
        out.append(_mcard_v345(n,("N/A" if pd.isna(v) else f"{v:.0f}/100"),state,"현재 위험도 기준"))
    return ''.join(out)


# -----------------------------------------------------------------------------
# Market Status indicator-specific criteria v0.3 (v3.46)
# Common architecture is shared, but thresholds/methods differ by indicator.
# This layer is intentionally separate from the composite 0-100 Risk Index.
# -----------------------------------------------------------------------------
_MS_RANK={"안정":0,"정상":0,"참고":0,"관찰":1,"주의":2,"위험":3,"확인 부족":-1}
_MS_STATE={0:"정상",1:"관찰",2:"주의",3:"위험"}

def _ms_rank_v346(state):
    return _MS_RANK.get(state,-1)

def _ms_state_v346(rank):
    return _MS_STATE.get(max(0,min(3,int(rank))),"정상")

def _ms_result_v346(state,reason="",level="—",change="—",meta=None):
    return {"state":state,"rank":_ms_rank_v346(state),"reason":reason,"level":level,"change":change,"meta":meta or {}}

def _ms_missing_v346(reason="데이터 부족"):
    return _ms_result_v346("확인 부족",reason,"확인 부족","확인 부족")

def _ms_worse_v346(*states):
    good=[x for x in states if x in _MS_RANK and _MS_RANK[x]>=0]
    if not good:return "확인 부족"
    return max(good,key=lambda x:_MS_RANK[x])

def _ms_raise_v346(state,minimum):
    if state=="확인 부족": return minimum
    return _ms_state_v346(max(_ms_rank_v346(state),_ms_rank_v346(minimum)))

def _move_percentile_v346(s,n,kind="pct",mode="abs",window=504):
    z=s.dropna().astype(float)
    if len(z)<=max(n+30,40): return np.nan
    mv=(z.pct_change(n)*100.0) if kind=="pct" else (z.diff(n)*100.0)
    cur=float(mv.iloc[-1]) if pd.notna(mv.iloc[-1]) else np.nan
    hist=mv.iloc[:-1].dropna().tail(window)
    if pd.isna(cur) or len(hist)<30:return np.nan
    if mode=="abs":
        cur_cmp=abs(cur); comp=hist.abs()
    elif mode=="up":
        cur_cmp=cur; comp=hist
    elif mode=="down":
        cur_cmp=-cur; comp=-hist
    else:
        cur_cmp=cur; comp=hist
    return float((((comp<cur_cmp).mean()) + 0.5*((comp==cur_cmp).mean()))*100.0)

def _move_pct_text_v346(p):
    if pd.isna(p): return "역사 비교 부족"
    tail=max(0.1,100.0-float(p))
    return f"최근 분포 상위 {tail:.1f}% 변동" if p>=50 else f"최근 분포 {p:.0f}백분위"

def _rank_fixed_v346(v,observe,caution,danger):
    if pd.isna(v): return -1
    a=abs(float(v))
    if a>=danger:return 3
    if a>=caution:return 2
    if a>=observe:return 1
    return 0

def _eval_equity_v346(s):
    z=s.dropna().astype(float)
    if len(z)<25:return _ms_missing_v346()
    r5=_pct_ret_v02(z,5); r20=_pct_ret_v02(z,20)
    dd=(float(z.iloc[-1]/z.tail(min(252,len(z))).max()-1.0)*100.0) if len(z) else np.nan
    level_rank=3 if dd<=-20 else (2 if dd<=-10 else (1 if dd<=-5 else 0))
    change_rank=0
    if pd.notna(r5): change_rank=max(change_rank,3 if r5<=-7 else (2 if r5<=-4 else (1 if r5<=-2.5 else 0)))
    if pd.notna(r20): change_rank=max(change_rank,3 if r20<=-12 else (2 if r20<=-8 else (1 if r20<=-5 else 0)))
    p5=_move_percentile_v346(z,5,"pct","abs")
    if pd.notna(r5) and r5<0 and pd.notna(p5):
        if p5>=97.5: change_rank=max(change_rank,2)
        elif p5>=90: change_rank=max(change_rank,1)
    rank=max(level_rank,change_rank)
    if level_rank>=1 and change_rank>=1 and rank<3: rank+=1
    reason=f"5일 {r5:+.1f}% · 20일 {r20:+.1f}% · 고점 대비 {dd:.1f}%" if pd.notna(r5) and pd.notna(r20) and pd.notna(dd) else "주가 하락속도와 고점 대비 낙폭을 함께 확인"
    return _ms_result_v346(_ms_state_v346(rank),reason,_ms_state_v346(level_rank),_ms_state_v346(change_rank),{"r5":r5,"r20":r20,"dd":dd,"p5":p5})

def _eval_ma200_v346(s):
    z=s.dropna().astype(float)
    if len(z)<200:return _ms_missing_v346("200거래일 데이터 부족")
    ma=z.rolling(200).mean(); dev=float((z.iloc[-1]/ma.iloc[-1]-1.0)*100.0)
    if dev<=-12:rank=3
    elif dev<=-7:rank=2
    elif dev<=-3:rank=1
    elif dev>=18:rank=2
    elif dev>=12:rank=1
    else:rank=0
    side="하방 이탈" if dev<0 else ("상방 과열" if dev>=12 else "정상 범위")
    return _ms_result_v346(_ms_state_v346(rank),f"200DMA 대비 {dev:+.1f}% · {side}",_ms_state_v346(rank),"참고",{"dev":dev})

def _eval_relative_v346(v):
    if pd.isna(v):return _ms_missing_v346()
    rank=3 if v<=-7 else (2 if v<=-4 else (1 if v<=-2 else 0))
    return _ms_result_v346(_ms_state_v346(rank),f"RSP가 SPY 대비 20일 {v:+.1f}%p",_ms_state_v346(rank),"참고",{"relative":v})

def _eval_rate_move_v346(s,label="금리"):
    z=s.dropna().astype(float)
    if len(z)<25:return _ms_missing_v346()
    c5=_point_change_v02(z,5); c20=_point_change_v02(z,20)
    bp5=c5*100 if pd.notna(c5) else np.nan; bp20=c20*100 if pd.notna(c20) else np.nan
    rank=max(_rank_fixed_v346(bp5,15,25,40),_rank_fixed_v346(bp20,35,55,80),0)
    p5=_move_percentile_v346(z,5,"bp","abs"); p20=_move_percentile_v346(z,20,"bp","abs")
    p=max([x for x in (p5,p20) if pd.notna(x)],default=np.nan)
    if pd.notna(p):
        if p>=97.5:rank=max(rank,2)
        elif p>=90:rank=max(rank,1)
    direction="급등" if (pd.notna(bp5) and bp5>0) else ("급락" if pd.notna(bp5) and bp5<0 else "변화")
    reason=f"5일 {bp5:+.0f}bp · 20일 {bp20:+.0f}bp · {direction}" if pd.notna(bp5) and pd.notna(bp20) else f"{label} 변화속도 확인"
    return _ms_result_v346(_ms_state_v346(rank),reason,"참고",_ms_state_v346(rank),{"bp5":bp5,"bp20":bp20,"pctl":p})

def _eval_curve_v346(s,label="수익률곡선"):
    z=s.dropna().astype(float)
    if len(z)<22:return _ms_missing_v346()
    cur=float(z.iloc[-1]); ch20=float((z.iloc[-1]-z.iloc[-21])*100.0)
    level_rank=2 if cur<=-1.0 else (1 if cur<0 else 0)
    change_rank=2 if abs(ch20)>=80 else (1 if abs(ch20)>=50 else 0)
    if cur>=0 and float(z.iloc[-21])<0 and ch20>=25: change_rank=max(change_rank,1)
    rank=min(2,max(level_rank,change_rank))
    phase="역전" if cur<0 else ("정상 기울기" if cur>=0 else "")
    reason=f"현재 {cur:+.2f}%p · 20일 {ch20:+.0f}bp · {phase}"
    return _ms_result_v346(_ms_state_v346(rank),reason,_ms_state_v346(level_rank),_ms_state_v346(change_rank),{"spread":cur,"bp20":ch20})

def _eval_vix_v346(s):
    z=s.dropna().astype(float)
    if len(z)<22:return _ms_missing_v346()
    cur=latest(z); r5=_pct_ret_v02(z,5); r20=_pct_ret_v02(z,20)
    level_rank=0 if cur<20 else (1 if cur<25 else (2 if cur<30 else 3))
    stable=cur<15
    change_rank=0
    if pd.notna(r5): change_rank=max(change_rank,3 if r5>=60 else (2 if r5>=35 else (1 if r5>=20 else 0)))
    if pd.notna(r20): change_rank=max(change_rank,3 if r20>=100 else (2 if r20>=60 else (1 if r20>=35 else 0)))
    p5=_move_percentile_v346(z,5,"pct","up")
    if pd.notna(p5):
        if p5>=97.5 and pd.notna(r5) and r5>0:change_rank=max(change_rank,2)
        elif p5>=90 and pd.notna(r5) and r5>0:change_rank=max(change_rank,1)
    rank=max(level_rank,change_rank)
    if level_rank>=1 and change_rank>=1 and rank<3:rank+=1
    state="안정" if rank==0 and stable else _ms_state_v346(rank)
    reason=f"VIX {cur:.1f} · 5일 {r5:+.1f}% · 20일 {r20:+.1f}%" if pd.notna(r5) and pd.notna(r20) else f"VIX {cur:.1f}"
    return _ms_result_v346(state,reason,("안정" if stable else _ms_state_v346(level_rank)),_ms_state_v346(change_rank),{"value":cur,"r5":r5,"r20":r20,"p5":p5})

def _eval_credit_v346(s,kind="HY"):
    z=s.dropna().astype(float)
    if len(z)<22:return _ms_missing_v346()
    cur=latest(z); c5=_point_change_v02(z,5); c20=_point_change_v02(z,20)
    bp5=c5*100 if pd.notna(c5) else np.nan; bp20=c20*100 if pd.notna(c20) else np.nan
    if kind=="HY":
        if cur<3.5: level_rank=0; stable=True
        elif cur<4.5: level_rank=0; stable=False
        elif cur<6.0: level_rank=1; stable=False
        elif cur<8.0: level_rank=2; stable=False
        else: level_rank=3; stable=False
        cr5=(15,30,60); cr20=(30,60,120)
    else:
        if cur<1.3: level_rank=0; stable=True
        elif cur<1.8: level_rank=0; stable=False
        elif cur<2.5: level_rank=1; stable=False
        elif cur<3.5: level_rank=2; stable=False
        else: level_rank=3; stable=False
        cr5=(8,15,30); cr20=(18,35,70)
    change_rank=0
    if pd.notna(bp5) and bp5>0: change_rank=max(change_rank,3 if bp5>=cr5[2] else (2 if bp5>=cr5[1] else (1 if bp5>=cr5[0] else 0)))
    if pd.notna(bp20) and bp20>0: change_rank=max(change_rank,3 if bp20>=cr20[2] else (2 if bp20>=cr20[1] else (1 if bp20>=cr20[0] else 0)))
    p5=_move_percentile_v346(z,5,"bp","up")
    if pd.notna(p5) and pd.notna(bp5) and bp5>0:
        if p5>=97.5:change_rank=max(change_rank,2)
        elif p5>=90:change_rank=max(change_rank,1)
    rank=max(level_rank,change_rank)
    if level_rank>=1 and change_rank>=1 and rank<3:rank+=1
    state="안정" if rank==0 and stable else _ms_state_v346(rank)
    reason=f"{kind} {cur:.2f}%p · 5일 {bp5:+.0f}bp · 20일 {bp20:+.0f}bp" if pd.notna(bp5) and pd.notna(bp20) else f"{kind} {cur:.2f}%p"
    return _ms_result_v346(state,reason,("안정" if stable else _ms_state_v346(level_rank)),_ms_state_v346(change_rank),{"value":cur,"bp5":bp5,"bp20":bp20,"p5":p5})

def _eval_claims_v346(s):
    z=s.dropna().astype(float)
    if len(z)<20:return _ms_missing_v346()
    avg4=z.rolling(4).mean().dropna()
    if len(avg4)<10:return _ms_missing_v346()
    cur=latest(avg4); ch8=_pct_ret_v02(avg4,8); p=_pctile_v345(avg4,52)
    low52=float(avg4.tail(52).min()) if len(avg4.tail(52)) else np.nan
    rise52=((cur/low52)-1.0)*100.0 if pd.notna(low52) and low52>0 else np.nan
    # Claims are not abnormal merely because they make a small new 1-year high.
    # Level alert requires a meaningful rise from the 52-week low; percentile is supporting context.
    level_rank=3 if pd.notna(rise52) and rise52>=25 else (2 if pd.notna(rise52) and rise52>=15 else (1 if pd.notna(rise52) and rise52>=8 else 0))
    if pd.notna(p) and p<80: level_rank=min(level_rank,1)
    change_rank=3 if pd.notna(ch8) and ch8>=20 else (2 if pd.notna(ch8) and ch8>=10 else (1 if pd.notna(ch8) and ch8>=5 else 0))
    rank=max(level_rank,change_rank)
    if level_rank>=1 and change_rank>=1 and rank<3:rank+=1
    reason=f"4주평균 {cur/1000:.0f}K · 52주 저점 대비 {rise52:+.1f}% · 약 8주 {ch8:+.1f}% · 1년 {p:.0f}백분위" if pd.notna(ch8) and pd.notna(p) and pd.notna(rise52) else f"4주평균 {cur/1000:.0f}K"
    return _ms_result_v346(_ms_state_v346(rank),reason,_ms_state_v346(level_rank),_ms_state_v346(change_rank),{"avg4":cur,"ch8":ch8,"pctl":p,"rise52":rise52})

def _eval_sahm_v346(v):
    if pd.isna(v):return _ms_missing_v346()
    rank=3 if v>=0.75 else (2 if v>=0.50 else (1 if v>=0.30 else 0))
    reason=f"3개월 평균이 이전 12개월 저점 대비 {v:.2f}%p 상승"
    return _ms_result_v346(_ms_state_v346(rank),reason,_ms_state_v346(rank),"월간",{"value":v})

def _eval_inflation_v346(s,kind="CPI"):
    z=s.dropna().astype(float)
    if len(z)<16:return _ms_missing_v346()
    yoy=z.pct_change(12)*100.0; ann=((z/z.shift(3))**4-1.0)*100.0
    y=latest(yoy); a=latest(ann)
    if pd.isna(y) or pd.isna(a):return _ms_missing_v346()
    if kind=="Core PCE":
        l=(2.5,3.0,4.0); m=(2.5,3.0,4.0)
    elif kind=="Core CPI":
        l=(3.0,3.5,4.5); m=(3.0,3.5,4.5)
    else:
        l=(3.0,3.5,5.0); m=(3.0,4.0,6.0)
    level_rank=3 if y>=l[2] else (2 if y>=l[1] else (1 if y>=l[0] else 0))
    change_rank=3 if a>=m[2] else (2 if a>=m[1] else (1 if a>=m[0] else 0))
    if a>=y+0.5 and a>=m[0]:change_rank=max(change_rank,2)
    rank=max(level_rank,change_rank)
    if level_rank>=1 and change_rank>=1 and rank<3:rank+=1
    reason=f"YoY {y:.1f}% · 3개월 연율 {a:.1f}%" + (" · 최근 재가속" if a>=y+0.5 and a>=m[0] else "")
    return _ms_result_v346(_ms_state_v346(rank),reason,_ms_state_v346(level_rank),_ms_state_v346(change_rank),{"yoy":y,"ann3":a})

def _eval_move_only_v346(s,n5=5,n20=20,kind="pct",cap="주의"):
    z=s.dropna().astype(float)
    if len(z)<40:return _ms_missing_v346()
    v5=_pct_ret_v02(z,n5) if kind=="pct" else (_point_change_v02(z,n5)*100)
    v20=_pct_ret_v02(z,n20) if kind=="pct" else (_point_change_v02(z,n20)*100)
    p5=_move_percentile_v346(z,n5,kind,"abs"); p20=_move_percentile_v346(z,n20,kind,"abs")
    p=max([x for x in (p5,p20) if pd.notna(x)],default=np.nan)
    rank=0
    if pd.notna(p):
        if p>=97.5:rank=2
        elif p>=90:rank=1
    rank=min(rank,_ms_rank_v346(cap))
    reason=(f"5일 {v5:+.1f}% · 20일 {v20:+.1f}% · {_move_pct_text_v346(p)}" if kind=="pct" and pd.notna(v5) and pd.notna(v20)
            else f"최근 변화 · {_move_pct_text_v346(p)}")
    return _ms_result_v346(_ms_state_v346(rank),reason,"참고",_ms_state_v346(rank),{"v5":v5,"v20":v20,"pctl":p})

def _group_state_v346(results):
    valid=[r for r in results if isinstance(r,dict) and r.get("rank",-1)>=0]
    if not valid:return {"state":"확인 부족","count":0,"total":0}
    rank=max(r.get("rank",0) for r in valid)
    count=sum(1 for r in valid if r.get("rank",0)>=1)
    return {"state":_ms_state_v346(rank),"count":count,"total":len(valid)}

def _market_status_cards_v346(groups):
    out=[]
    for name in ("주식","금리","신용","변동성","경기","물가"):
        g=groups.get(name,{"state":"확인 부족","count":0,"total":0})
        detail=(f"비정상 신호 {g['count']}/{g['total']}" if g.get('total') else "판정 데이터 부족")
        out.append(_mcard_v345(name,detail,g.get("state","확인 부족"),"지표별 기준으로 판정"))
    return ''.join(out)


CAPE_URL="https://www.multpl.com/shiller-pe/table/by-month"


# v3.44.0 source refresh TTLs.
# UI reruns never need to hit the network merely because the user changed a view/theme.
SERIES_TTL_SECONDS={
    "EFFR":1800,
    "DGS3MO":1800,"DGS2":1800,"DGS10":1800,"DGS30":1800,
    "SP500":1800,"VIXCLS":1800,
    "BAMLH0A0HYM2":3600,"BAMLC0A4CBBB":3600,
    "THREEFYTP10":21600,"ICSA":21600,
    "CPIAUCSL":43200,"CPILFESL":43200,"PCEPILFE":43200,"UNRATE":43200,
}
FX_TTL_SECONDS=600
CAPE_TTL_SECONDS=86400
TREASURY_TTL_SECONDS=1800
AUTO_REFRESH_CHECK_SECONDS=600

def _file_fresh(path,ttl):
    try:
        return (time.time()-path.stat().st_mtime) < ttl
    except Exception:
        return False

def _series_fresh(sid):
    return _file_fresh(_cache_file(sid),SERIES_TTL_SECONDS.get(sid,3600))

def _auto_refresh_due():
    # Missing auxiliary caches should be filled even when the last general refresh was recent.
    if not FX_CACHE.exists() or not CAPE_CACHE.exists():
        return True
    if not REFRESH_STATUS.exists():
        return True
    try:
        return (time.time()-REFRESH_STATUS.stat().st_mtime) >= AUTO_REFRESH_CHECK_SECONDS
    except Exception:
        return True


def _migrate_legacy_cache():
    if any(CACHE_DIR.glob("*.csv")): return
    base=_Path(os.environ.get("LOCALAPPDATA", str(_Path.home())))
    for old_name in ("RiskMonitor_3_25_0","RiskMonitor_3_24_0","RiskMonitor_3_23_0"):
        old=base / old_name / "data"
        if old.exists():
            for f in old.glob("*.csv"):
                try: shutil.copy2(f, CACHE_DIR / f.name)
                except Exception: pass
            break
_migrate_legacy_cache()


def _parse_fred(text,series):
    from io import StringIO
    lines=text.lstrip('\ufeff').splitlines()
    header=next((i for i,line in enumerate(lines[:30]) if 'observation_date' in next(csv.reader([line])) and series in next(csv.reader([line]))),None)
    if header is None: raise ValueError(f'{series}: FRED CSV 헤더 없음')
    df=pd.read_csv(StringIO('\n'.join(lines[header:])),usecols=['observation_date',series],dtype=str)
    df['date']=pd.to_datetime(df['observation_date'],errors='coerce')
    df[series]=pd.to_numeric(df[series],errors='coerce')
    df=df.dropna(subset=['date',series]).drop_duplicates('date',keep='first').sort_values('date')
    if df.empty:raise ValueError(f'{series}: 유효 데이터 없음')
    return df.set_index('date')[series].astype(float)


def _fetch(series,recent=False):
    if recent:
        since=(pd.Timestamp.now().normalize()-pd.Timedelta(days=RECENT_DAYS)).strftime("%Y-%m-%d")
        url=FRED_RECENT.format(series,since)
    else: url=FRED_CSV.format(series)
    r=requests.get(url,timeout=(3,10)); r.raise_for_status(); return _parse_fred(r.text,series)


def _cache_file(series): return CACHE_DIR / f"{series}.csv"

def _read_cache(series):
    f=_cache_file(series)
    if not f.exists(): return pd.Series(dtype=float)
    try:
        df=pd.read_csv(f,parse_dates=["date"])
        if "value" not in df: return pd.Series(dtype=float)
        return pd.Series(df["value"].astype(float).values,index=pd.DatetimeIndex(df["date"])).dropna().sort_index()
    except Exception: return pd.Series(dtype=float)


def _write_cache(series,s):
    if s is None or not len(s): return
    tmp=_cache_file(series).with_suffix(".tmp")
    pd.DataFrame({"date":s.index,"value":s.values}).to_csv(tmp,index=False); tmp.replace(_cache_file(series))


def _merge_and_write(series,new):
    old=_read_cache(series)
    merged=pd.concat([old,new]).groupby(level=0).last().sort_index() if len(old) else new.sort_index()
    _write_cache(series,merged); return merged


def _treasury_latest():
    year=pd.Timestamp.now().year
    url=("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
         f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv")
    headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
    r=requests.get(url,headers=headers,timeout=(3,6)); r.raise_for_status()
    rows=list(csv.DictReader(r.text.lstrip("\ufeff").splitlines())); parsed=[]
    for row in rows:
        d=pd.to_datetime(row.get("Date"),errors="coerce")
        if pd.isna(d): continue
        vals={}
        for col,key in (("3 Mo","DGS3MO"),("2 Yr","DGS2"),("10 Yr","DGS10"),("30 Yr","DGS30")):
            v=pd.to_numeric(row.get(col),errors="coerce")
            if pd.notna(v): vals[key]=float(v)
        if vals: parsed.append((d,vals))
    if not parsed: raise ValueError("Treasury 최신 금리 데이터 없음")
    return max(parsed,key=lambda x:x[0])


def _read_all_cache():
    out={}
    for name,sid in SERIES.items():
        s=_read_cache(sid)
        if name=="기준금리" and not len(s):
            legacy=_read_cache("FEDFUNDS")
            if len(legacy): s=legacy
        out[name]=s
    return out


def _initial_fetch():
    out={}; errors=[]
    def one(item):
        name,sid=item
        try:
            s=_fetch(sid,recent=True); _write_cache(sid,s); return name,s,None
        except Exception as e: return name,pd.Series(dtype=float),f"{name} ({sid}): {e}"
    with ThreadPoolExecutor(max_workers=10) as ex:
        required={'기준금리','2년물','10년물','하이일드스프레드','CPI','실업률','S&P500','VIX'}
        ordered=sorted(SERIES.items(),key=lambda item:item[0] not in required)
        futures=[ex.submit(one,x) for x in ordered]
        for f in as_completed(futures):
            name,s,err=f.result(); out[name]=s
            if err: errors.append(err)
    return out,errors


def _refresh_series(name,sid,force=False):
    try:
        cached=_read_cache(sid)
        if len(cached) and not force and _series_fresh(sid):
            return name,cached,None
        new=_fetch(sid,recent=bool(len(cached)))
        return name,_merge_and_write(sid,new),None
    except Exception as e:
        return name,_read_cache(sid),f"{name}: {e}"


def _fetch_yahoo_symbol(ticker):
    enc=quote(ticker,safe="")
    headers={"User-Agent":"Mozilla/5.0"}
    attempts=[
        ("query1.finance.yahoo.com","5d","1m"),
        ("query2.finance.yahoo.com","5d","5m"),
        ("query1.finance.yahoo.com","1mo","15m"),
        ("query2.finance.yahoo.com","1mo","1d"),
    ]
    last_error=None
    for host,rng,interval in attempts:
        try:
            url=f"https://{host}/v8/finance/chart/{enc}?range={rng}&interval={interval}&includePrePost=false"
            r=requests.get(url,headers=headers,timeout=(3,6)); r.raise_for_status()
            result=r.json().get("chart",{}).get("result") or []
            if not result: raise ValueError(f"{ticker}: Yahoo 데이터 없음")
            row=result[0]; meta=row.get("meta",{})
            closes=[float(x) for x in (row.get("indicators",{}).get("quote",[{}])[0].get("close") or []) if x is not None]
            cur=meta.get("regularMarketPrice")
            if cur is None and closes: cur=closes[-1]
            prev=meta.get("chartPreviousClose",meta.get("previousClose"))
            if prev is None and len(closes)>=2: prev=closes[-2]
            if cur is None: raise ValueError(f"{ticker}: 현재값 없음")
            return {"value":float(cur),"prev":float(prev) if prev is not None else np.nan,"time":time.time(),"spark":closes[-60:],"stale":False,"interval":interval}
        except Exception as e:
            last_error=e
    raise ValueError(f"{ticker}: Yahoo 요청 실패 ({last_error})")


def _refresh_fx(force=False):
    if not force and _file_fresh(FX_CACHE,FX_TTL_SECONDS): return []
    tickers={"원/달러":"USDKRW=X","엔/달러":"USDJPY=X","달러인덱스":"DX-Y.NYB","WTI 유가":"CL=F"}
    previous=_read_fx().get("items",{})
    snap={"updated":time.time(),"source":"Yahoo Finance","items":dict(previous)}
    errors=[]; successes=0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(_fetch_yahoo_symbol,t):name for name,t in tickers.items()}
        for f,name in [(f,n) for f,n in futs.items()]:
            try:
                snap["items"][name]=f.result(); successes+=1
            except Exception as e:
                errors.append(f"{name}: {e}")
                if name in snap["items"]:
                    snap["items"][name]=dict(snap["items"][name]); snap["items"][name]["stale"]=True
    if snap["items"]:
        ROOT_CACHE.mkdir(parents=True,exist_ok=True)
        tmp=FX_CACHE.with_suffix(".tmp"); tmp.write_text(json.dumps(snap,ensure_ascii=False),encoding="utf-8"); tmp.replace(FX_CACHE)
    return errors


def _read_fx():
    try: return json.loads(FX_CACHE.read_text(encoding="utf-8"))
    except Exception: return {"items":{}}


def _read_cape():
    if not CAPE_CACHE.exists(): return pd.Series(dtype=float)
    try:
        df=pd.read_csv(CAPE_CACHE,parse_dates=["date"])
        if "cape" not in df: return pd.Series(dtype=float)
        out=pd.Series(pd.to_numeric(df["cape"],errors="coerce").values,index=pd.DatetimeIndex(df["date"])).dropna()
        return out[~out.index.duplicated(keep="last")].sort_index()
    except Exception: return pd.Series(dtype=float)


def _refresh_cape(force=False):
    if not force and _file_fresh(CAPE_CACHE,CAPE_TTL_SECONDS): return True
    headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
    r=requests.get(CAPE_URL,headers=headers,timeout=(3,7)); r.raise_for_status()
    # Multpl의 월별 표를 외부 HTML 파서 의존성 없이 읽는다.
    rows=re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>",r.text,re.I|re.S)
    rec=[]
    for d_raw,v_raw in rows:
        d_txt=re.sub(r"<[^>]+>","",html.unescape(d_raw)).strip()
        v_txt=re.sub(r"<[^>]+>","",html.unescape(v_raw)).replace("\xa0","").strip()
        d=pd.to_datetime(d_txt,errors="coerce"); v=pd.to_numeric(v_txt.replace(",",""),errors="coerce")
        if pd.notna(d) and pd.notna(v): rec.append((d,float(v)))
    if len(rec)<100: raise ValueError("CAPE 월별 표 파싱 실패")
    df=pd.DataFrame(rec,columns=["date","cape"]).drop_duplicates("date",keep="last").sort_values("date")
    tmp=CAPE_CACHE.with_suffix(".tmp"); df.to_csv(tmp,index=False); tmp.replace(CAPE_CACHE)
    return True


def _write_refresh_status(ok,errors):
    ROOT_CACHE.mkdir(parents=True,exist_ok=True)
    payload={"finished":time.time(),"ok":bool(ok),"errors":errors[:10]}
    tmp=REFRESH_STATUS.with_suffix(".tmp"); tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8"); tmp.replace(REFRESH_STATUS)


def _refresh_all_background(force=False):
    errors=[]
    priority=[("기준금리","EFFR"),("3개월물","DGS3MO"),("2년물","DGS2"),("10년물","DGS10"),("30년물","DGS30")]
    need_treasury=force or not _file_fresh(_cache_file("DGS10"),TREASURY_TTL_SECONDS)
    with ThreadPoolExecutor(max_workers=6) as ex:
        fs=[ex.submit(_refresh_series,*x,force) for x in priority]
        fx_future=ex.submit(_refresh_fx,force)
        cape_future=ex.submit(_refresh_cape,force)
        treasury_future=ex.submit(_treasury_latest) if need_treasury else None
        for f in fs:
            _,_,err=f.result()
            if err: errors.append(err)
        try: errors.extend(fx_future.result())
        except Exception as e: errors.append(f"환율: {e}")
        try: cape_future.result()
        except Exception as e: errors.append(f"CAPE: {e}")
        if treasury_future is not None:
            try:
                d,vals=treasury_future.result()
                for sid,v in vals.items():
                    _merge_and_write(sid,pd.Series([v],index=pd.DatetimeIndex([d]),dtype=float))
            except Exception as e:
                errors.append(f"미 재무부 최신 금리: {e}")
    rest=[x for x in SERIES.items() if x not in priority]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures=[ex.submit(_refresh_series,*x,force) for x in rest]
        for f in as_completed(futures):
            _,_,err=f.result()
            if err: errors.append(err)
    _write_refresh_status(not errors,errors)


def _status_mtime():
    try: return REFRESH_STATUS.stat().st_mtime
    except Exception: return 0.0


def _cache_ready(data):
    required=("기준금리","2년물","10년물","하이일드스프레드","CPI","실업률","S&P500","VIX")
    return all(len(data.get(k,pd.Series(dtype=float)).dropna()) for k in required)


def _get_session_data():
    stamp=_status_mtime()
    if st.session_state.get("_market_data_stamp")==stamp and "_market_data_mem" in st.session_state:
        return st.session_state["_market_data_mem"]
    d=_read_all_cache()
    st.session_state["_market_data_mem"]=d
    st.session_state["_market_data_stamp"]=stamp
    return d

def _set_session_data(d):
    st.session_state["_market_data_mem"]=d
    st.session_state["_market_data_stamp"]=_status_mtime()

def _get_session_cape():
    stamp=_status_mtime()
    if st.session_state.get("_cape_stamp")==stamp and "_cape_mem" in st.session_state:
        return st.session_state["_cape_mem"]
    c=_read_cape()
    st.session_state["_cape_mem"]=c
    st.session_state["_cape_stamp"]=stamp
    return c

def _get_session_fx_items():
    stamp=_status_mtime()
    if st.session_state.get("_fx_stamp")==stamp and "_fx_mem" in st.session_state:
        return st.session_state["_fx_mem"]
    items=_read_fx().get("items",{})
    st.session_state["_fx_mem"]=items
    st.session_state["_fx_stamp"]=stamp
    return items

def _invalidate_session_market_cache():
    for k in ("_market_data_mem","_market_data_stamp","_cape_mem","_cape_stamp","_fx_mem","_fx_stamp",
              "_dashboard_calc","_dashboard_calc_stamp"):
        st.session_state.pop(k,None)


# v3.43.1 adaptive dashboard refinement — Streamlit engine + custom HTML/CSS skin.
st.markdown("""<style>
html,body,.stApp{background:#f5f7fb!important;color:#171b23}
header[data-testid="stHeader"]{background:transparent!important}
.block-container{max-width:none!important;padding:26px 28px 54px 188px!important}
[data-testid="stSidebar"]{display:none!important}[data-testid="stToolbar"]{right:10px!important}#MainMenu{visibility:hidden}
[data-testid="stSidebar"]{width:286px!important;min-width:286px!important}
[data-testid="stSidebar"]>div:first-child{width:286px!important}
.r38-sidebar{position:fixed;z-index:50;left:0;top:0;bottom:0;width:158px;background:linear-gradient(180deg,#101b2d,#0d1726);color:#fff;padding:22px 13px 18px;box-sizing:border-box}.r38-brand{display:flex;align-items:center;gap:9px;padding:0 9px 20px;font-size:14px;font-weight:800;line-height:1.25}.r38-brand-mark{width:27px;height:32px}.r38-brand-mark svg{width:27px;height:32px}.r38-nav{display:flex;flex-direction:column;gap:6px}.r38-nav-item{display:flex;align-items:center;gap:11px;height:42px;border-radius:7px;padding:0 11px;color:#aeb9c9;font-size:13.5px;font-weight:650;text-decoration:none!important}.r38-nav-item.active{background:linear-gradient(90deg,#365dce,#506be6);color:#fff;box-shadow:0 5px 16px rgba(45,78,190,.28)}.r38-nav-icon{width:17px;text-align:center;font-size:15px}.r38-side-bottom{position:absolute;left:20px;right:20px;bottom:20px;border-top:1px solid rgba(255,255,255,.08);padding-top:16px;color:#9eabba;font-size:11px;line-height:1.55}.r38-side-title{color:#dbe3ef;font-weight:700}.r38-toggle{display:flex;align-items:center;justify-content:space-between;margin-top:16px;color:#9eabba!important;text-decoration:none!important}.r38-toggle-pill{width:34px;height:18px;border-radius:999px;background:#566274;position:relative}.r38-toggle-pill:after{content:'';position:absolute;width:14px;height:14px;border-radius:50%;background:#d9dee6;left:2px;top:2px;transition:.15s}.r38-toggle-pill.on{background:#4469d8}.r38-toggle-pill.on:after{left:18px;background:#fff}
.r38-mobilebar{display:none}.r38-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:16px}.r38-title{font-size:30px;font-weight:850;letter-spacing:-.045em;line-height:1.18}.r38-subtitle{font-size:15px;color:#69717d;margin-top:6px}.r38-credit{font-size:12px;color:#939aa5;margin-top:3px}.r38-head-actions{display:flex;gap:10px}.r38-action{cursor:pointer;height:44px;border:1px solid #dfe4eb;border-radius:8px;background:#fff;padding:0 15px;display:flex;align-items:center;font-size:14px;font-weight:650;color:#3c4654;text-decoration:none!important}
.r38-panel{background:#fff;border:1px solid #dde3eb;border-radius:12px;padding:19px;margin-bottom:15px;box-shadow:0 1px 2px rgba(25,38,58,.025)}.r38-section-title{display:flex;align-items:center;gap:7px;font-size:18px;font-weight:820;color:#202631;margin-bottom:15px}
.r38-info{position:relative;display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border:1px solid #9da5af;border-radius:50%;font-size:9px;color:#7d8590;font-weight:800;cursor:help;outline:none;flex:0 0 15px}.r38-info:hover,.r38-info:focus{background:#eef2f7;color:#37404b;border-color:#66717e}.r38-info-tip{visibility:hidden;opacity:0;pointer-events:none;position:absolute;z-index:9999;left:50%;top:23px;transform:translateX(-50%) translateY(-3px);width:min(330px,78vw);padding:12px 13px;border:1px solid #dfe4ea;border-radius:11px;background:#fff;box-shadow:0 12px 32px rgba(13,24,40,.15);font-size:12.5px;font-weight:550;line-height:1.55;color:#414955;text-align:left;white-space:normal;transition:opacity .12s ease,transform .12s ease}.r38-info:hover .r38-info-tip,.r38-info:focus .r38-info-tip{visibility:visible;opacity:1;transform:translateX(-50%) translateY(0)}
.r38-hero-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;align-items:stretch}.r38-hero-card{position:relative;min-height:306px;height:100%;border:1px solid #e3e7ed;border-radius:11px;padding:19px 19px 17px;box-sizing:border-box;background:#fff;overflow:visible;display:flex;flex-direction:column}.r38-hero-card.danger{border-color:#f0dddd}.r38-hero-card.warn{border-color:#f0e4cf}.r38-card-title{font-size:16.5px;font-weight:800;color:#3a4049;display:flex;align-items:center;gap:6px}.r38-horizon{font-size:12.5px;color:#8b929d;margin-top:4px}.r38-hero-main{display:grid;grid-template-columns:minmax(0,1fr) minmax(145px,38%);align-items:center;gap:18px;margin-top:18px;min-height:126px;flex:1}.r38-hero-left{min-width:0}.r38-hero-side{min-width:0;display:flex;align-items:center;justify-content:flex-start;text-align:left}.r38-big{font-size:45px;font-weight:850;line-height:1;white-space:nowrap;letter-spacing:-.05em}.r38-big.red{color:#d92f3b}.r38-big.orange{color:#d77b00}.r38-unit{font-size:14px;font-weight:650;white-space:nowrap;color:#555d68;margin-left:4px}.r38-badge{display:inline-flex;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:800;margin-top:9px}.r38-badge.red{color:#fff;background:#e83d49}.r38-badge.orange{color:#fff;background:#f09a18}.r38-badge.green{color:#fff;background:#2ca675}.r38-badge.gray{color:#5e6672;background:#eef1f5}.r38-delta-label{font-size:12px;color:#737b87}.r38-delta{font-size:14px;margin-top:4px;font-weight:800}.r38-up{color:#e03b45}.r38-down{color:#2f70c9}.r38-flat{color:#7b8490}.r38-side-copy{font-size:13.5px;line-height:1.5;color:#616a76;font-weight:700;max-width:185px}.r38-side-copy strong{display:block;font-size:14.5px;color:#343b45;margin-bottom:4px}.r38-signal-main{font-size:38px;font-weight:850;white-space:nowrap;line-height:1.05;letter-spacing:-.035em;color:#252b34}.r38-signal-meta{font-size:13px;color:#707985;margin-top:8px;font-weight:700}.r38-callout{position:static;margin-top:12px;height:72px;min-height:72px;box-sizing:border-box;border-radius:8px;padding:12px 13px;font-size:12.5px;line-height:1.5;background:#fff6f6;border:1px solid #f5dede;color:#5c3b3e;display:flex;flex-direction:column;justify-content:center}.r38-callout.warn{background:#fff9ef;border-color:#f3e4c9;color:#69523a}.r38-summary-lines{display:flex;flex-direction:column;gap:3px}.r38-summary-lines b{font-weight:820}.r38-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}.r38-chip{display:inline-flex;align-items:center;min-height:25px;box-sizing:border-box;padding:4px 8px;border-radius:999px;background:#fff0f0;border:1px solid #f3d3d3;color:#c33b42;font-size:11.5px;font-weight:750;line-height:1.2;white-space:nowrap}.r38-chip.warn{background:#fff5e7;border-color:#f0ddbd;color:#a76600}.r38-interpret{margin-top:12px;padding:14px 16px;border-radius:9px;background:#eef7ff;border:1px solid #d6e9f9;font-size:13.5px;line-height:1.6;color:#294862;font-weight:620}.r38-interpret-label{font-weight:850;color:#1f6598;margin-right:9px;white-space:nowrap}
.r38-risk-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px}.r38-risk-card{border:1px solid #e2e7ed;border-radius:9px;padding:15px 12px 13px;min-height:158px}.r38-risk-top{display:flex;align-items:center;gap:8px}.r38-risk-icon{width:28px;height:28px;border-radius:7px;background:#f2f6ff;border:1px solid #dfe7fa;display:flex;align-items:center;justify-content:center;color:#345ec8;font-size:14px;font-weight:800}.r38-risk-icon svg{width:17px;height:17px}.r38-risk-name{font-size:clamp(10.5px,.78vw,13px);font-weight:760;color:#3d4550;display:flex;align-items:center;gap:5px;white-space:nowrap;min-width:0}.r38-risk-numrow{display:flex;align-items:center;justify-content:space-between;margin-top:15px}.r38-risk-score{font-size:clamp(23px,1.7vw,28px);font-weight:850;white-space:nowrap}.r38-mini-state{font-size:clamp(8.5px,.66vw,11px);font-weight:800;border-radius:999px;padding:4px 7px;background:#fff1f1;color:#d63e46;white-space:nowrap}.r38-mini-state.mid{background:#fff7df;color:#c98300}.r38-mini-state.low{background:#edf8f3;color:#24855e}.r38-segments{display:flex;gap:3px;margin-top:13px}.r38-seg{height:4px;flex:1;border-radius:99px;background:#e8ebef}.r38-seg.on-red{background:#ea3944}.r38-seg.on-orange{background:#f0a018}.r38-seg.on-green{background:#3da77a}.r38-risk-foot,.r38-note{font-size:clamp(9.5px,.7vw,11.5px);color:#8c949f;margin-top:10px}.r38-risk-foot{white-space:nowrap}
.r38-market-table{border:1px solid #e1e6ed;border-radius:9px;overflow:hidden;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));background:#fff}.r38-market-col{min-width:0;border-right:1px solid #e7ebf0}.r38-market-col:last-child{border-right:0}.r38-col-head{height:42px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;background:#fafbfc;border-bottom:1px solid #e7ebf0}.r38-metric{min-height:90px;padding:11px 12px 9px;border-bottom:1px solid #edf0f3}.r38-metric:last-child{border-bottom:0}.r38-metric-name{font-size:11.5px;color:#555e69;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.r38-metric-row{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;margin-top:4px}.r38-metric-value{font-size:18px;font-weight:820;white-space:nowrap}.r38-metric-delta{font-size:11px;margin-top:3px;font-weight:700;white-space:nowrap}.r38-spark{width:74px;height:30px;flex:0 0 74px}.r38-spark svg{width:100%;height:30px}.r38-recession{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}.r38-recession-card{background:#f8fafc;border:1px solid #e7ebf0;border-radius:8px;padding:10px 11px}.r38-recession-name{font-size:11.5px;color:#808895}.r38-recession-value{font-size:19px;font-weight:820;margin-top:3px}
div[data-testid="stButton"] button{border:1px solid #dfe4eb!important;background:#fff!important;color:#3e4651!important;border-radius:7px!important;font-size:12px!important;font-weight:700!important;min-height:36px!important;box-shadow:none!important}[data-testid="stExpander"]{border:1px solid #dde3eb!important;border-radius:10px!important;background:#fff!important}.r38-footer{font-size:10.5px;color:#9299a3;text-align:right;margin-top:12px}
@media(max-width:1180px) and (min-width:781px){.r38-hero-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.r38-hero-card:first-child{grid-column:1/-1}.r38-hero-card{min-height:300px}.r38-hero-main{grid-template-columns:minmax(0,1fr) minmax(150px,36%)}.r38-big{white-space:nowrap}.r38-unit{white-space:nowrap}.r38-signal-main{white-space:nowrap}}
@media(max-width:1050px){.block-container{padding-left:176px!important;padding-right:18px!important}.r38-risk-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.r38-market-table{grid-template-columns:repeat(3,minmax(0,1fr))}.r38-market-col:nth-child(3){border-right:0}.r38-market-col:nth-child(n+4){border-top:1px solid #e7ebf0}}

@media (orientation:portrait) and (min-width:781px){
  .r38-hero-grid{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:8px}
  .r38-hero-card:first-child{grid-column:auto!important}
  .r38-hero-card{min-height:300px;padding:16px 13px 14px}
  .r38-card-title{font-size:clamp(13px,1.25vw,16px);white-space:nowrap}
  .r38-horizon{font-size:clamp(10px,1vw,12px);white-space:nowrap}
  .r38-hero-main{grid-template-columns:minmax(0,1fr) minmax(95px,34%);gap:10px;min-height:120px}
  .r38-big{font-size:clamp(34px,3.6vw,43px)}
  .r38-unit{font-size:clamp(11px,1.15vw,13px)}
  .r38-signal-main{font-size:clamp(31px,3.7vw,38px)}
  .r38-badge{font-size:clamp(9.5px,1vw,11.5px);padding:5px 8px}
  .r38-side-copy{font-size:clamp(10px,1.05vw,12.5px);line-height:1.42;max-width:150px}
  .r38-side-copy strong{font-size:clamp(10.5px,1.1vw,13px)}
  .r38-callout{min-height:68px;padding:10px 11px;font-size:clamp(10px,1vw,12px)}
  .r38-chip{font-size:clamp(9px,.95vw,11px);padding:4px 7px}
  .r38-risk-grid{grid-template-columns:repeat(6,minmax(0,1fr))!important;gap:7px}
  .r38-risk-card{padding:12px 8px 11px;min-height:148px;min-width:0}
  .r38-risk-top{gap:5px}
  .r38-risk-icon{width:25px;height:25px;flex:0 0 25px;font-size:12px}
  .r38-risk-name{font-size:clamp(9px,1.15vw,11.5px)}
  .r38-mini-state{font-size:clamp(7.8px,.9vw,9.8px);padding:3px 5px}
  .r38-risk-score{font-size:clamp(20px,2.45vw,25px)}
  .r38-risk-foot{font-size:clamp(8px,.9vw,10px)}
  .r38-segments{gap:2px}
}
@media(max-width:780px){.r38-sidebar{display:none}.block-container{padding:calc(env(safe-area-inset-top,0px) + 44px) 12px 40px!important}.r38-mobilebar{display:flex;align-items:center;justify-content:space-between;background:#101b2d;color:#fff;margin:-18px -12px 15px;padding:0 14px;min-height:46px;position:relative;z-index:90}.r38-mobile-brand{font-size:13px;font-weight:800}.r38-mobile-nav{margin-left:auto;position:relative}.r38-mobile-nav summary{list-style:none;cursor:pointer;font-size:21px;line-height:46px;padding:0 2px;user-select:none;-webkit-tap-highlight-color:transparent}.r38-mobile-nav summary::-webkit-details-marker{display:none}.r38-mobile-drawer{position:absolute;right:-8px;top:43px;width:min(280px,82vw);background:#101b2d;border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:8px;box-shadow:0 16px 36px rgba(0,0,0,.28)}.r38-mobile-link{display:flex;align-items:center;min-height:42px;padding:0 12px;border-radius:8px;color:#dbe3ef!important;text-decoration:none!important;font-size:13px;font-weight:700}.r38-mobile-link.active{background:#3f61d0;color:#fff!important}.r38-mobile-link.disabled{opacity:.45;pointer-events:none}.r38-mobile-divider{height:1px;background:rgba(255,255,255,.08);margin:6px 4px}.r38-title{font-size:23px}.r38-subtitle{font-size:11.5px}.r38-head-actions{display:none}.r38-panel{padding:12px 11px}.r38-section-title{font-size:15px}.r38-hero-grid{grid-template-columns:1fr}.r38-hero-card{min-height:255px}.r38-hero-main{grid-template-columns:1fr;gap:10px;min-height:auto}.r38-hero-side{justify-content:flex-start;text-align:left}.r38-side-copy{max-width:none}.r38-callout{margin-top:14px;height:auto;min-height:auto}.r38-card-title{font-size:14px}.r38-big{font-size:37px;white-space:nowrap}.r38-signal-main{font-size:31px;white-space:nowrap}.r38-risk-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.r38-market-table{grid-template-columns:repeat(2,minmax(0,1fr))}.r38-market-col,.r38-market-col:nth-child(3){border-right:1px solid #e7ebf0}.r38-market-col:nth-child(even){border-right:0}.r38-market-col:nth-child(n+3){border-top:1px solid #e7ebf0}.r38-recession{gap:5px}.r38-metric{min-height:80px;padding:9px}.r38-spark{width:58px;flex-basis:58px}.r38-info-tip{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%) scale(.98);width:min(340px,86vw);font-size:13px;padding:14px 15px;border-radius:14px;box-shadow:0 18px 55px rgba(0,0,0,.20)}.r38-info:hover .r38-info-tip,.r38-info:focus .r38-info-tip{transform:translate(-50%,-50%) scale(1)}.r38-footer{text-align:left}}
</style>""", unsafe_allow_html=True)

now_kst=datetime.now(ZoneInfo('Asia/Seoul'))
_theme_q='dark' if _theme=='dark' else 'light'
_dashboard_active=' active' if _view=='dashboard' else ''
_risk_active=' active' if _view=='risk' else ''
_heatmap_active=' active' if _view=='heatmap' else ''
_news_active=' active' if _view=='news' else ''
_market_active=' active' if _view=='market' else ''
_theme_next='light' if _theme=='dark' else 'dark'
sidebar='''<aside class="r38-sidebar"><div class="r38-brand"><span class="r38-brand-mark"><svg viewBox="0 0 32 38" fill="none"><path d="M16 2.5 27 7v8.4c0 8.1-4.4 14.4-11 18.1C9.4 29.8 5 23.5 5 15.4V7L16 2.5Z" stroke="#E7EDF7" stroke-width="1.5"/><path d="m11 18 3 3 7-8" stroke="#E7EDF7" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span>Market Risk<br>Monitor</span></div><nav class="r38-nav"><a class="r38-nav-item'''+_dashboard_active+'''" href="?view=dashboard&theme='''+_theme_q+'''" target="_self"><span class="r38-nav-icon">⌂</span>대시보드</a><a class="r38-nav-item'''+_heatmap_active+'''" href="?view=heatmap&theme='''+_theme_q+'''" target="_self"><span class="r38-nav-icon">▦</span>S&P500 시장 맵</a><a class="r38-nav-item'''+_risk_active+'''" href="?view=risk&theme='''+_theme_q+'''" target="_self"><span class="r38-nav-icon">◉</span>위험지수</a><a class="r38-nav-item'''+_market_active+'''" href="?view=market&theme='''+_theme_q+'''" target="_self"><span class="r38-nav-icon">≋</span>시장 상태</a><div class="r38-nav-item"><span class="r38-nav-icon">▣</span>데이터</div><a class="r38-nav-item'''+_news_active+'''" href="?view=news&theme='''+_theme_q+'''" target="_self"><span class="r38-nav-icon">▧</span>뉴스</a><div class="r38-nav-item"><span class="r38-nav-icon">▤</span>리포트</div><div class="r38-nav-item"><span class="r38-nav-icon">⚙</span>설정</div><div class="r38-nav-item"><span class="r38-nav-icon">?</span>도움말</div></nav><div class="r38-side-bottom"><div class="r38-side-title">최종 업데이트</div><div>'''+now_kst.strftime('%Y.%m.%d %H:%M')+'''</div><div>(한국시간 기준)</div><a class="r38-toggle" href="?view='''+_view+'''&theme='''+_theme_next+'''" target="_self">다크 모드 <span class="r38-toggle-pill'''+(' on' if _theme=='dark' else '')+'''"></span></a></div></aside><div class="r38-mobilebar"><div class="r38-mobile-brand">Market Risk Monitor</div><details class="r38-mobile-nav"><summary aria-label="메뉴 열기">☰</summary><div class="r38-mobile-drawer"><a class="r38-mobile-link'''+_dashboard_active+'''" href="?view=dashboard&theme='''+_theme_q+'''" target="_self">대시보드</a><a class="r38-mobile-link'''+_heatmap_active+'''" href="?view=heatmap&theme='''+_theme_q+'''" target="_self">S&amp;P500 시장 맵</a><a class="r38-mobile-link'''+_risk_active+'''" href="?view=risk&theme='''+_theme_q+'''" target="_self">위험지수</a><a class="r38-mobile-link'''+_market_active+'''" href="?view=market&theme='''+_theme_q+'''" target="_self">시장 상태</a><span class="r38-mobile-link disabled">데이터 · 준비 중</span><a class="r38-mobile-link'''+_news_active+'''" href="?view=news&theme='''+_theme_q+'''" target="_self">뉴스</a><div class="r38-mobile-divider"></div><a class="r38-mobile-link" href="?view='''+_view+'''&theme='''+_theme_next+'''" target="_self">다크 모드 전환</a></div></details></div>'''
st.markdown(sidebar,unsafe_allow_html=True)
st.markdown(f'''<div class="r38-head"><div><div class="r38-title">미국 증시 위험 모니터</div><div class="r38-subtitle">현재 시장 상황과 주요 위험 신호를 한눈에 확인하세요.</div><div class="r38-credit">Developed by 유유상 · v3.48.1</div></div><div class="r38-head-actions"><div class="r38-action">{now_kst.strftime('%Y.%m.%d')}　▣</div><a class="r38-action" href="?view={_view}&theme={_theme_q}&refresh=1" target="_self">↻　데이터 업데이트</a></div></div>''',unsafe_allow_html=True)

# News and heatmap are independent routes: no FRED bootstrap or risk engine.
if _view in ('news','heatmap'):
    st.markdown('### '+('경제 뉴스' if _view=='news' else 'S&P500 시장맵'))
    manual=str(_qp.get('refresh','0'))=='1'
    if manual:st.query_params.pop('refresh',None)
    if _view=='news':
        cache_path=NEWS_CACHE
        reader=_read_news_cache
        fresh=_news_cache_fresh
        def loader():
            value=_fetch_news_snapshot(force=True)
            if value.get('stale') or not value.get('items'):raise ValueError('뉴스 갱신 실패')
        st.caption('정보 제공용 뉴스 · 제목 기준 카테고리/태그 · 점수 및 시장 판정에 반영하지 않습니다.')
        category=str(_qp.get('news_category','전체'))
        if category not in ['전체']+CATEGORIES:category='전체'
    else:
        cache_path=HEATMAP_CACHE
        reader=_read_heatmap_cache
        fresh=_heatmap_cache_fresh
        def loader():
            value=_fetch_slickcharts_top200(force=True)
            if value.get('stale') or not value.get('items'):raise ValueError('시장맵 갱신 실패')
    if st.button('새로고침',key='light_refresh348'):manual=True
    if manual or not fresh():start_job(cache_path,loader,cooldown=0 if manual else 30)
    polling=job_status(cache_path).get('running',False)
    @st.fragment(run_every='2s' if polling else None)
    def light_content():
        snap=reader();items=snap.get('items',[]);state=job_status(cache_path)
        if items:
            if _view=='news':
                st.markdown(_news_category_cards(items,category,_theme_q),unsafe_allow_html=True)
                chosen=select_news(items,category)
                if chosen:st.markdown(_news_html(chosen),unsafe_allow_html=True)
                else:st.info('해당 카테고리에 저장된 기사가 없습니다.')
            else:st.markdown(_heatmap_html(snap,dark=_theme=='dark'),unsafe_allow_html=True)
            updated=snap.get('updated',0)
            label=datetime.fromtimestamp(updated,tz=ZoneInfo('Asia/Seoul')).strftime('%m.%d %H:%M KST')
            st.caption('마지막 수집 '+label+(' · 갱신 확인 중' if state.get('running') else ''))
        elif state.get('running'):st.info('데이터를 처음 준비하고 있어요. 완료되면 자동으로 표시됩니다.')
        else:st.warning('데이터를 가져오지 못했습니다. 새로고침으로 다시 시도해 주세요.')
        if state.get('error'):st.caption('새 데이터 수집에 실패했습니다. 저장된 자료가 있으면 유지합니다.')
        if polling and not state.get('running'):st.rerun()
    light_content()
    st.stop()

# Handle one-shot manual refresh after refresh helpers are defined.
_manual_refresh = str(_qp.get("refresh", "0")) == "1"
if _manual_refresh:
    st.session_state.refresh_started = True
    st.session_state.refresh_applied = False
    st.session_state.refresh_baseline = _status_mtime()
    start_job(ROOT_CACHE / 'core_refresh',lambda:_refresh_all_background(force=True),cooldown=5)
    st.session_state.refresh_applied=not job_status(ROOT_CACHE / 'core_refresh').get('running',False)
    # Remove refresh=1 so browser reloads don't retrigger endlessly.
    st.query_params.clear()
    if _view != "dashboard":
        st.query_params["view"] = _view
    if _theme != "light":
        st.query_params["theme"] = _theme

bootstrap_key=ROOT_CACHE / 'core_refresh'
if job_status(bootstrap_key).get("running"):
    # See individual CSVs before the complete background batch finishes.
    data=_read_all_cache();_set_session_data(data)
else:data=_get_session_data()
if not _cache_ready(data):
    def bootstrap():
        _,errors=_initial_fetch()
        _write_refresh_status(not errors,errors)
    state=job_status(bootstrap_key)
    if not state or st.button('데이터 다시 받기',key='bootstrap_retry348'):
        start_job(bootstrap_key,bootstrap,cooldown=5)
    running=job_status(bootstrap_key).get('running',False)
    st.markdown('### 미국 증시 위험 모니터')
    st.markdown('[뉴스 먼저 보기](?view=news) · [시장맵 먼저 보기](?view=heatmap)')
    @st.fragment(run_every='2s' if running else None)
    def bootstrap_progress():
        current=_read_all_cache()
        ready=sum(bool(len(x)) for x in current.values())
        st.info(f'처음 실행할 데이터를 준비하고 있어요. {ready}/{len(SERIES)}개 준비')
        if _cache_ready(current):
            _set_session_data(current);st.rerun()
        if running and not job_status(bootstrap_key).get('running'):st.rerun()
    bootstrap_progress()
    if not running:st.warning('필수 지표가 부족합니다. 데이터 다시 받기를 눌러 주세요.')
    st.stop()

if "refresh_started" not in st.session_state:
    st.session_state.refresh_started=True
    st.session_state.refresh_baseline=_status_mtime()
    if _auto_refresh_due() and not job_status(bootstrap_key).get("running"):
        st.session_state.refresh_applied=False
        start_job(ROOT_CACHE / 'core_refresh',lambda:_refresh_all_background(force=False),cooldown=30)
        st.session_state.refresh_applied=not job_status(ROOT_CACHE / 'core_refresh').get('running',False)
    else:
        st.session_state.refresh_applied=not job_status(bootstrap_key).get("running",False)

def _render_refresh_done():
    try:
        info=json.loads(REFRESH_STATUS.read_text(encoding="utf-8"))
        ts=datetime.fromtimestamp(info.get("finished",time.time()),tz=ZoneInfo("Asia/Seoul")).strftime("%H:%M KST")
        st.markdown(f"<div class='data-status done'><span></span>최신 데이터 · {ts}</div>",unsafe_allow_html=True)
    except Exception:
        st.markdown("<div class='data-status done'><span></span>최신 데이터</div>",unsafe_allow_html=True)

if st.session_state.get("refresh_started") and not st.session_state.get("refresh_applied"):
    @st.fragment(run_every="2s")
    def refresh_indicator():
        baseline=st.session_state.get("refresh_baseline",0.0)
        now=_status_mtime()
        if now>baseline:
            st.session_state.refresh_applied=True
            _invalidate_session_market_cache()
            st.rerun()
        if not job_status(ROOT_CACHE / 'core_refresh').get('running',False):
            st.session_state.refresh_applied=True
            st.caption('갱신 작업이 종료됐습니다. 일부 자료는 기존 값을 유지할 수 있습니다.')
            return
        st.markdown("<div class='data-status'><span></span>최신 데이터 확인 중…</div>",unsafe_allow_html=True)
else:
    def refresh_indicator():
        _render_refresh_done()


def latest(s):
    s=s.dropna(); return float(s.iloc[-1]) if len(s) else np.nan

def second(s):
    z=s.dropna(); return float(z.iloc[-2]) if len(z)>=2 else np.nan

def clamp(x): return float(np.clip(x,0,100)) if pd.notna(x) else np.nan

def interp_score(x,xp,fp):
    if pd.isna(x): return np.nan
    return clamp(float(np.interp(float(x),xp,fp)))


def percentile_score(series,value,high_is_risk=True,lookback_years=20):
    s=series.dropna().copy()
    if len(s)<30 or pd.isna(value): return np.nan
    idx=pd.to_datetime(s.index,errors="coerce"); s=s[~idx.isna()].copy(); s.index=idx[~idx.isna()]
    if not len(s): return np.nan
    cutoff=s.index.max()-pd.DateOffset(years=lookback_years); s=s.loc[s.index>=cutoff]
    if len(s)<30:return np.nan
    p=float((s<=float(value)).mean()*100); return clamp(p if high_is_risk else 100-p)


def weighted(scores):
    n=d=0
    for k,w in WEIGHTS.items():
        v=scores.get(k,np.nan)
        if pd.notna(v): n+=float(v)*w; d+=w
    return clamp(n/d) if d else np.nan


def weighted_custom(scores,weights):
    n=d=0
    for k,w in weights.items():
        v=scores.get(k,np.nan)
        if pd.notna(v): n+=float(v)*w; d+=w
    return clamp(n/d) if d else np.nan


def market_overheat_from_dev(dev):
    # 가격이 붕괴한 뒤의 스트레스가 아니라, 폭락 전 가격 과열 취약성을 측정한다.
    return interp_score(dev,[-15,-5,0,5,10,15,20],[0,5,15,40,70,90,100])


def cape_score(cape_value):
    return interp_score(cape_value,[10,15,20,25,30,35,40,45],[5,10,25,45,65,80,92,100])


def market_momentum_score(sp,dev):
    z=sp.dropna()
    if len(z)<21 or z.iloc[-21]<=0:return np.nan
    ret20=(z.iloc[-1]/z.iloc[-21]-1)*100
    raw=interp_score(ret20,[-12,-6,0,3,6,10,15],[0,5,10,30,55,80,100])
    # 폭락 뒤의 기술적 반등을 과열로 오인하지 않도록 200일선 위치에 따라 모멘텀 영향 제한.
    if pd.isna(dev): gate=.5
    elif dev<=0: gate=.25
    elif dev<5: gate=.25+.35*(dev/5)
    elif dev<10: gate=.60+.30*((dev-5)/5)
    else: gate=1.0
    return clamp(raw*gate),ret20


def market_risk_score(sp,cape):
    if len(sp.dropna())<220:return np.nan,{"dev":np.nan,"cape":np.nan,"mom20":np.nan}
    z=sp.dropna(); ma=z.rolling(200).mean(); dev=(latest(z)/latest(ma)-1)*100
    over=market_overheat_from_dev(dev)
    cv=latest(cape) if len(cape.dropna()) else np.nan
    val=cape_score(cv) if pd.notna(cv) else np.nan
    mom,mom20=market_momentum_score(z,dev)
    score=weighted_custom({"over":over,"value":val,"momentum":mom},{"over":.45,"value":.35,"momentum":.20})
    return score,{"dev":dev,"cape":cv,"over":over,"valuation":val,"momentum":mom,"mom20":mom20}


def vix_surge_detail(vix):
    z=vix.dropna()
    if len(z)<6 or z.iloc[-6]<=0:return {"score":np.nan,"pct":np.nan,"points":np.nan}
    pct=(z.iloc[-1]/z.iloc[-6]-1)*100; pts=float(z.iloc[-1]-z.iloc[-6])
    pct_s=interp_score(pct,[-25,0,10,25,50,80,150],[0,5,20,45,70,90,100])
    pts_s=interp_score(pts,[-8,0,2,5,10,20,40],[0,5,20,45,70,90,100])
    return {"score":weighted_custom({"pct":pct_s,"pts":pts_s},{"pct":.60,"pts":.40}),"pct":pct,"points":pts}


def volatility_score(vix):
    level=interp_score(latest(vix),[10,12,15,20,25,30,40,60],[5,10,20,40,60,75,90,100])
    surge=vix_surge_detail(vix)
    return weighted_custom({"level":level,"surge":surge["score"]},{"level":.55,"surge":.45}),{"level":level,**surge}


def sahm_series(u):
    m=u.resample("MS").mean(); ma3=m.rolling(3).mean(); low=ma3.rolling(12,min_periods=12).min(); return (ma3-low).dropna()


def sahm_score(u):
    s=sahm_series(u); v=latest(s) if len(s) else np.nan
    return interp_score(v,[0,.1,.2,.35,.5,.75,1.5],[5,15,30,50,70,90,100]),v


def rate_rise_score(y10,obs=20):
    z=y10.dropna()
    if len(z)<=obs:return np.nan,np.nan
    delta=float(z.iloc[-1]-z.iloc[-1-obs])
    return interp_score(delta,[-1,-.5,0,.15,.35,.60,1.0,1.5],[0,5,10,25,50,75,90,100]),delta


def rate_score(y2,y10,fed,term_premium):
    curve=(y10-y2).dropna(); policy=(y10-fed).dropna()
    curve_v=latest(curve); policy_v=latest(policy); tp=latest(term_premium) if len(term_premium.dropna()) else np.nan
    level=interp_score(latest(y10),[0,1.5,2.5,3.5,4.25,5,6,8],[5,10,20,35,55,75,90,100])
    rise,rise_delta=rate_rise_score(y10,20)
    # 음의 스프레드는 단기금리가 장기금리보다 높은 긴축/역전 상태로 평가.
    curve_s=interp_score(curve_v,[-2,-1,-.5,0,.5,1,2],[100,90,75,60,35,20,5])
    policy_s=interp_score(policy_v,[-3,-2,-1,0,1,2],[100,90,70,45,20,5])
    tp_s=interp_score(tp,[-1,-.5,0,.5,1,1.5,2.5],[5,10,20,45,65,80,100]) if pd.notna(tp) else np.nan
    score=weighted_custom({"level":level,"rise":rise,"curve":curve_s,"policy":policy_s,"tp":tp_s},
                          {"level":.35,"rise":.25,"curve":.15,"policy":.15,"tp":.10})
    return score,{"level":level,"rise":rise,"rise_delta":rise_delta,"curve":curve_s,"curve_value":curve_v,
                  "policy":policy_s,"policy_value":policy_v,"tp":tp_s,"tp_value":tp}


def spread_change_score(s,obs=20):
    z=s.dropna()
    if len(z)<=obs:return np.nan
    delta=float(z.iloc[-1]-z.iloc[-1-obs])
    if obs<=5:
        return interp_score(delta,[-.5,0,.15,.30,.60,1.20,2.0],[0,5,25,45,70,90,100])
    return interp_score(delta,[-1,0,.25,.50,1.0,2.0,4.0],[0,5,25,45,70,90,100])


def credit_score(hy,bbb):
    hy_abs=interp_score(latest(hy),[1.5,2.5,3.5,5,7,10,15],[5,12,25,50,70,90,100])
    bbb_abs=interp_score(latest(bbb),[.4,.8,1.0,1.5,2.5,4,6],[5,12,20,40,65,85,100]) if len(bbb.dropna()) else np.nan
    hy5,bbb5=spread_change_score(hy,5),spread_change_score(bbb,5)
    hy20,bbb20=spread_change_score(hy,20),spread_change_score(bbb,20)
    fast5=weighted_custom({"hy":hy5,"bbb":bbb5},{"hy":.70,"bbb":.30})
    trend20=weighted_custom({"hy":hy20,"bbb":bbb20},{"hy":.70,"bbb":.30})
    score=weighted_custom({"hy":hy_abs,"bbb":bbb_abs,"fast5":fast5,"trend20":trend20},
                          {"hy":.45,"bbb":.20,"fast5":.15,"trend20":.20})
    return score,{"hy_abs":hy_abs,"bbb_abs":bbb_abs,"fast5":fast5,"trend20":trend20}


def claims_score(icsa):
    z=icsa.dropna()
    if len(z)<20:return np.nan,{"level":np.nan,"trend":np.nan,"trend_pct":np.nan}
    ma4=z.rolling(4).mean().dropna()
    if len(ma4)<12:return np.nan,{"level":np.nan,"trend":np.nan,"trend_pct":np.nan}
    # 인구/노동시장 규모 변화 때문에 절대 건수 대신 과거 10년 내 상대 수준을 보되, 미래 데이터는 사용하지 않는다.
    level=percentile_score(ma4,latest(ma4),True,lookback_years=10)
    if len(ma4)>=9 and ma4.iloc[-9]>0:
        pct=(ma4.iloc[-1]/ma4.iloc[-9]-1)*100
        trend=interp_score(pct,[-20,-5,0,5,10,20,40],[0,5,15,30,50,75,100])
    else: pct=trend=np.nan
    return weighted_custom({"level":level,"trend":trend},{"level":.60,"trend":.40}),{"level":level,"trend":trend,"trend_pct":pct}


def economy_score(unemp,icsa):
    unemp_level=interp_score(latest(unemp),[3,3.5,4,4.5,5,6,8,10],[10,15,25,40,55,70,90,100])
    sahm_s,sahm_v=sahm_score(unemp); claims,cd=claims_score(icsa)
    # Sahm 단독 신호의 오경보를 줄이기 위해 신규 실업수당의 최근 8주 상승 추세가 확인될 때만 강한 신호로 인정한다.
    claims_confirm=pd.notna(cd.get("trend",np.nan)) and cd.get("trend",0)>=50
    sahm_adj=sahm_s
    if pd.notna(sahm_v) and sahm_v>=.5 and not claims_confirm: sahm_adj=min(sahm_s,55)
    score=weighted_custom({"unemp":unemp_level,"sahm":sahm_adj,"claims":claims},{"unemp":.30,"sahm":.35,"claims":.35})
    return score,{"unemp":unemp_level,"sahm":sahm_adj,"sahm_raw":sahm_s,"sahm_value":sahm_v,"claims":claims,"claims_confirm":claims_confirm,**{f"claims_{k}":v for k,v in cd.items()}}


def _annualized_3m(s):
    m=s.dropna().resample("MS").last().dropna()
    if len(m)<4 or m.iloc[-4]<=0:return np.nan
    return ((m.iloc[-1]/m.iloc[-4])**4-1)*100


def inflation_level_score(v):
    return interp_score(v,[0,1,2,2.5,3,4,6,8,10],[5,10,20,35,50,70,90,98,100])


def inflation_momentum_score(v):
    return interp_score(v,[-2,0,1,2,2.5,3,4,6,8,10],[0,5,10,20,35,50,70,90,98,100])


def _inflation_metric(s,yoy_weight,m3_weight):
    yoy=latest(s.pct_change(12)*100); m3=_annualized_3m(s)
    ys=inflation_level_score(yoy); ms=inflation_momentum_score(m3)
    return weighted_custom({"yoy":ys,"m3":ms},{"yoy":yoy_weight,"m3":m3_weight}),{"yoy":yoy,"m3":m3,"yoy_score":ys,"m3_score":ms}


def inflation_score(cpi,core_cpi,core_pce):
    h,hd=_inflation_metric(cpi,.55,.45)
    c,cd=_inflation_metric(core_cpi,.45,.55) if len(core_cpi.dropna()) else (np.nan,{})
    p,pd_=_inflation_metric(core_pce,.45,.55) if len(core_pce.dropna()) else (np.nan,{})
    score=weighted_custom({"headline":h,"core_cpi":c,"core_pce":p},{"headline":.25,"core_cpi":.35,"core_pce":.40})
    recent=weighted_custom({"headline":hd.get("m3_score",np.nan),"core_cpi":cd.get("m3_score",np.nan),"core_pce":pd_.get("m3_score",np.nan)},
                           {"headline":.25,"core_cpi":.35,"core_pce":.40})
    yoy_comp=weighted_custom({"headline":hd.get("yoy_score",np.nan),"core_cpi":cd.get("yoy_score",np.nan),"core_pce":pd_.get("yoy_score",np.nan)},
                             {"headline":.25,"core_cpi":.35,"core_pce":.40})
    return score,{"headline":hd,"core_cpi":cd,"core_pce":pd_,"recent":recent,"yoy":yoy_comp}


def inversion_memory(spread210,months=18,full_months=6):
    z=spread210.dropna().sort_index()
    if not len(z):return 0.0,None
    inv=z[z<0]
    if not len(inv):return 0.0,None
    last_inv=inv.index[-1]; end=z.index[-1]
    age=max(0.0,(end-last_inv).days/30.44)
    if age<=full_months:sev=100.0
    elif age>=months:sev=0.0
    else:sev=100*(months-age)/(months-full_months)
    return clamp(sev),last_inv


def structural_signals(details,spread210):
    items=[]; mem,last_inv=inversion_memory(spread210)
    if mem>=25:
        items.append(("장단기 금리 역전 이력",mem))
    val=details.get("market",{}).get("valuation",np.nan)
    if pd.notna(val) and val>=85: items.append(("시장 고평가",val))
    recent=details.get("inflation",{}).get("recent",np.nan); yoy=details.get("inflation",{}).get("yoy",np.nan)
    if pd.notna(recent) and recent>=70 and (pd.isna(yoy) or recent>=yoy): items.append(("물가 재가속",recent))
    ed=details.get("economy",{})
    if pd.notna(ed.get("sahm_value",np.nan)) and ed.get("sahm_value",0)>=.5 and ed.get("claims_confirm",False):
        items.append(("고용 악화 확인",max(ed.get("sahm",0),ed.get("claims_trend",0))))
    if len(items)>=3:level="경계"
    elif len(items)>=2:level="주의"
    elif len(items)==1:level="관찰"
    else:level="정상"
    return {"level":level,"count":len(items),"items":items,"inversion_memory":mem,"last_inversion":last_inv}


def fast_signal_scores(details):
    credit_vals=[details.get("credit",{}).get("fast5",np.nan),details.get("credit",{}).get("trend20",np.nan)]
    credit_vals=[float(v) for v in credit_vals if pd.notna(v)]
    return {
        "VIX":details.get("volatility",{}).get("score",np.nan),
        "신용":max(credit_vals) if credit_vals else np.nan,
        "10년물":details.get("rates",{}).get("rise",np.nan),
        "고용":details.get("economy",{}).get("claims_trend",np.nan),
    }


def rapid_alert(current_fast,previous_fast=None):
    previous_fast=previous_fast or {}
    flags={k:(pd.notna(v) and v>=70) for k,v in current_fast.items()}
    prev_flags={k:(pd.notna(previous_fast.get(k,np.nan)) and previous_fast.get(k,np.nan)>=70) for k in current_fast}
    count=sum(flags.values()); prev_count=sum(prev_flags.values())
    extreme_vix=pd.notna(current_fast.get("VIX",np.nan)) and current_fast.get("VIX",0)>=85
    extreme_credit=pd.notna(current_fast.get("신용",np.nan)) and current_fast.get("신용",0)>=80
    if count>=3 and (prev_count>=2 or sum(pd.notna(v) and v>=85 for v in current_fast.values())>=2):
        level="강한 스트레스"
    elif count>=2 and (prev_count>=2 or (extreme_vix and extreme_credit)):
        level="급변 경보"
    elif count>=1:
        level="관찰"
    else:
        level="정상"
    active=[k for k,v in flags.items() if v]
    return {"level":level,"count":count,"active":active,"scores":current_fast}


def signal_floor(structure,rapid):
    sc=int((structure or {}).get("count",0) or 0); rc=int((rapid or {}).get("count",0) or 0)
    floor=0; reason=""
    if sc==1: floor,reason=40,"구조적 위험 신호 1개"
    elif sc>=2: floor,reason=50,"구조적 위험 신호 2개 이상"
    if rc==2 and 55>floor: floor,reason=55,"시장 급변 신호 2개"
    elif rc>=3 and 65>floor: floor,reason=65,"시장 급변 신호 3개 이상"
    if sc>=2 and rc>=3: floor,reason=70,"구조적 위험과 강한 급변 신호 동시 확인"
    elif sc>=2 and rc>=2 and 65>floor: floor,reason=65,"구조적 위험과 급변 신호 동시 확인"
    return floor,reason

def active_market_stress(sp,vix,credit_fast):
    z=sp.dropna(); vz=vix.dropna()
    if len(z)<21:return {"floor":0,"reason":"","drawdown":np.nan,"ret5":np.nan,"ret20":np.nan}
    peak=z.tail(252).max(); dd=(z.iloc[-1]/peak-1)*100 if peak>0 else np.nan
    r5=(z.iloc[-1]/z.iloc[-6]-1)*100 if len(z)>=6 and z.iloc[-6]>0 else np.nan
    r20=(z.iloc[-1]/z.iloc[-21]-1)*100 if z.iloc[-21]>0 else np.nan
    vv=latest(vz); cf=float(credit_fast) if pd.notna(credit_fast) else np.nan
    confirm55=(pd.notna(vv) and vv>=25) or (pd.notna(cf) and cf>=60)
    confirm65=(pd.notna(vv) and vv>=30) or (pd.notna(cf) and cf>=70)
    confirm75=(pd.notna(vv) and vv>=40) or (pd.notna(cf) and cf>=85)
    fast55=(pd.notna(r5) and r5<=-5) or (pd.notna(r20) and r20<=-8)
    fast65=(pd.notna(r5) and r5<=-7) or (pd.notna(r20) and r20<=-12)
    fast75=(pd.notna(r5) and r5<=-10) or (pd.notna(r20) and r20<=-15)
    floor=0; reason=""
    if pd.notna(dd) and dd<=-20 and fast75 and confirm75: floor,reason=75,"위기 수준의 진행 중 시장 스트레스"
    elif pd.notna(dd) and dd<=-15 and fast65 and confirm65: floor,reason=65,"강한 진행 중 시장 스트레스"
    elif pd.notna(dd) and dd<=-10 and fast55 and confirm55: floor,reason=55,"진행 중 시장 조정 스트레스"
    return {"floor":floor,"reason":reason,"drawdown":dd,"ret5":r5,"ret20":r20,"vix":vv,"credit_fast":cf}

def apply_risk_floors(base,structure,rapid,sp,vix,credit_fast):
    sf,sreason=signal_floor(structure,rapid); stress=active_market_stress(sp,vix,credit_fast)
    candidates=[(float(base) if pd.notna(base) else 0,"기본 종합위험"),(sf,sreason),(stress["floor"],stress["reason"])]
    final,reason=max(candidates,key=lambda x:x[0])
    return clamp(final),{"base":base,"signal_floor":sf,"stress_floor":stress["floor"],"reason":reason,"stress":stress}

def _truncate_one(s):
    z=s.dropna(); return z.iloc[:-1] if len(z)>1 else z


def compute_snapshot(data,cape,with_alerts=True):
    fed,y2,y10=data["기준금리"],data["2년물"],data["10년물"]
    tp=data.get("10년물기간프리미엄",pd.Series(dtype=float))
    hy,bbb=data["하이일드스프레드"],data["BBB스프레드"]
    cpi,core_cpi,core_pce=data["CPI"],data["근원CPI"],data["근원PCE"]
    unemp,icsa,sp,vix=data["실업률"],data["신규실업수당"],data["S&P500"],data["VIX"]
    market,md=market_risk_score(sp,cape); vol,vd=volatility_score(vix); rates,rd=rate_score(y2,y10,fed,tp)
    credit,cd=credit_score(hy,bbb); econ,ed=economy_score(unemp,icsa); infl,id_=inflation_score(cpi,core_cpi,core_pce)
    scores={"시장·밸류에이션":market,"변동성":vol,"금리":rates,"신용":credit,"경기":econ,"물가":infl}
    details={"market":md,"volatility":vd,"rates":rd,"credit":cd,"economy":ed,"inflation":id_}
    overall=weighted(scores)
    structure=structural_signals(details,(y10-y2).dropna()) if with_alerts else None
    return {"scores":scores,"details":details,"overall":overall,"structure":structure}

def label(x):
    if pd.isna(x):return "데이터 부족"
    if x<=20:return "매우 낮음"
    if x<=40:return "낮음"
    if x<=60:return "보통"
    if x<=80:return "높음"
    return "매우 높음"

def risk_class(x):
    if pd.isna(x): return "na"
    if x<=20: return "vlow"
    if x<=40: return "low"
    if x<=60: return "mid"
    if x<=80: return "high"
    return "vhigh"



def delta_value(a,b):
    if pd.isna(a) or pd.isna(b): return None,"비교 불가","flat"
    d=float(a-b)
    if d>0:return d,f"▲ {abs(d):.1f}","up"
    if d<0:return d,f"▼ {abs(d):.1f}","down"
    return d,"— 0.0","flat"


# ---------- v3.43.1 redesigned frontend ----------
import math

def _esc(x): return html.escape(str(x))

def _info38(text):
    return f'<span class="r38-info" tabindex="0">i<span class="r38-info-tip">{_esc(text)}</span></span>'

def _gauge_svg(score, tone="#e53b46"):
    sc=0.0 if pd.isna(score) else float(np.clip(score,0,100))
    angle=180-(sc*1.8); rad=math.radians(angle); cx,cy=50,53
    nx=cx+26*math.cos(rad); ny=cy-26*math.sin(rad)
    return f'''<div class="r38-gauge"><svg viewBox="0 0 100 66" aria-hidden="true"><path d="M12 53 A38 38 0 0 1 88 53" pathLength="100" fill="none" stroke="#edf0f4" stroke-width="8" stroke-linecap="round"/><path d="M12 53 A38 38 0 0 1 88 53" pathLength="100" fill="none" stroke="{tone}" stroke-width="8" stroke-linecap="round" stroke-dasharray="{sc:.1f} 100"/><line x1="50" y1="53" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#aab1bb" stroke-width="1.2"/><circle cx="50" cy="53" r="2.2" fill="#fff" stroke="#aab1bb" stroke-width="1"/><text x="10" y="64" class="r38-gauge-label">0</text><text x="84" y="64" class="r38-gauge-label">100</text></svg></div>'''

def _status_tone(score):
    if pd.isna(score): return ('gray','#89919b')
    if score>=61: return ('red','#e53b46')
    if score>=41: return ('orange','#efa019')
    return ('green','#2fa374')

def _risk_badge(score):
    c,_=_status_tone(score); return f'<span class="r38-badge {c}">{_esc(label(score))}</span>'

def _seg_html(score):
    n=0 if pd.isna(score) else int(np.clip(math.ceil(float(score)/20),0,5))
    c,_=_status_tone(score); on={'red':'on-red','orange':'on-orange','green':'on-green','gray':''}[c]
    return '<div class="r38-segments">'+''.join(f'<span class="r38-seg {on if i<n else ""}"></span>' for i in range(5))+'</div>'

def _spark_svg_38(values, cls='flat'):
    vals=[float(x) for x in values if pd.notna(x)]
    if len(vals)<2:return '<div class="r38-spark"></div>'
    vals=vals[-60:]
    if len(vals)>36:
        idx=np.linspace(0,len(vals)-1,36,dtype=int)
        vals=[vals[i] for i in idx]
    lo=min(vals); hi=max(vals); span=(hi-lo) or 1.0; pts=[]
    for i,v in enumerate(vals):
        x=2+62*i/(len(vals)-1); y=25-22*(v-lo)/span; pts.append(f'{x:.1f},{y:.1f}')
    color='#e53b46' if cls=='up' else ('#2f70c9' if cls=='down' else '#8b93a1')
    pts_str=' '.join(pts)
    return f'<div class="r38-spark"><svg viewBox="0 0 66 28" preserveAspectRatio="none"><polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'

def _fmt_series_metric(s, unit='%', decimals=2):
    cur=latest(s); prv=second(s)
    if pd.isna(cur): return 'N/A','', 'flat'
    val=f'{cur:,.{decimals}f}{unit}'
    if pd.isna(prv): return val,'직전값 없음','flat'
    ch=float(cur-prv)
    if ch>0:return val,f'▲ {abs(ch):.{decimals}f}{unit}','up'
    if ch<0:return val,f'▼ {abs(ch):.{decimals}f}{unit}','down'
    return val,f'— {0:.{decimals}f}{unit}','flat'

def _fmt_fx_metric(name,decimals=2):
    item=fx.get(name,{})
    v=item.get('value',np.nan); p=item.get('prev',np.nan); stale=bool(item.get('stale',False))
    if pd.isna(v): return 'N/A','', 'flat'
    val=f'{v:,.{decimals}f}'
    if pd.isna(p) or p==0:return val,('직전값 없음 · 지연' if stale else '직전값 없음'),'flat'
    ch=float(v-p); pct=ch/p*100
    suffix=' · 지연' if stale else ''
    if ch>0:return val,f'▲ {abs(ch):,.{decimals}f} (+{abs(pct):.2f}%){suffix}','up'
    if ch<0:return val,f'▼ {abs(ch):,.{decimals}f} (-{abs(pct):.2f}%){suffix}','down'
    return val,f'— 0.{"0"*decimals} (0.00%){suffix}','flat'

def _cpi_metric(s):
    yoy=s.pct_change(12)*100; cur=latest(yoy); prv=second(yoy)
    if pd.isna(cur):return 'N/A','', 'flat'
    val=f'{cur:.2f}%'
    if pd.isna(prv):return val,'직전 발표 없음','flat'
    ch=float(cur-prv)
    if ch>0:return val,f'▲ {abs(ch):.2f}%p','up'
    if ch<0:return val,f'▼ {abs(ch):.2f}%p','down'
    return val,'— 0.00%p','flat'

def _metric_html(name,value,delta,cls,spark):
    return f'''<div class="r38-metric"><div class="r38-metric-name">{_esc(name)}</div><div class="r38-metric-row"><div><div class="r38-metric-value">{_esc(value)}</div><div class="r38-metric-delta r38-{cls}">{_esc(delta)}</div></div>{_spark_svg_38(spark,cls)}</div></div>'''

fed,y3m,y2,y10,y30=data['기준금리'],data.get('3개월물',pd.Series(dtype=float)),data['2년물'],data['10년물'],data['30년물']
term_premium=data.get('10년물기간프리미엄',pd.Series(dtype=float)); hy,bbb=data['하이일드스프레드'],data['BBB스프레드']
cpi,core_cpi,core_pce=data['CPI'],data['근원CPI'],data['근원PCE']; unemp,icsa,sp,vix=data['실업률'],data['신규실업수당'],data['S&P500'],data['VIX']
cape=_get_session_cape(); spread210=(y10-y2).dropna(); spread103m=(y10-y3m).dropna() if len(y3m) else pd.Series(dtype=float); spread10fed=(y10-fed).dropna()
if _view in ('dashboard','risk'):
    snapshot=compute_snapshot(data,cape); scores=snapshot['scores']; details=snapshot['details']; structure=snapshot['structure']
    base_overall=snapshot['overall']; dev=details['market'].get('dev',np.nan); sahm_now=details['economy'].get('sahm_value',np.nan)
    zsp=sp.dropna(); prev_date=zsp.index[-2] if len(zsp)>=2 else None
    if prev_date is not None:
        prev_data={k:v.loc[:prev_date].dropna() for k,v in data.items()}; prev_cape=cape.loc[:prev_date].dropna() if len(cape) else cape
        prev_snapshot=compute_snapshot(prev_data,prev_cape,with_alerts=False); prev_fast=fast_signal_scores(prev_snapshot['details'])
    else:
        prev_data={}; prev_snapshot=None; prev_fast={}
    current_fast=fast_signal_scores(details); rapid=rapid_alert(current_fast,prev_fast)
    overall,floor_diag=apply_risk_floors(base_overall,structure,rapid,sp,vix,current_fast.get('신용',np.nan))
    if prev_snapshot is not None:
        prev_structure=structural_signals(prev_snapshot['details'],(prev_data['10년물']-prev_data['2년물']).dropna()); prev_rapid=rapid_alert(prev_fast,{})
        prev_overall,_=apply_risk_floors(prev_snapshot['overall'],prev_structure,prev_rapid,prev_data['S&P500'],prev_data['VIX'],prev_fast.get('신용',np.nan))
    else: prev_overall=np.nan
    _,delta_text,delta_class=delta_value(overall,prev_overall)


refresh_indicator()


if _view=="market":
    st.markdown('''<style>
    .ms-hero{border:1px solid #e5e7eb;border-radius:24px;padding:22px 24px;background:rgba(255,255,255,.82);margin:8px 0 14px}.ms-hero h2{font-size:23px;margin:0 0 7px;letter-spacing:-.035em}.ms-hero p{margin:0;color:#737983;font-size:13px;line-height:1.55}
    .ms-principle{border:1px solid #dfe5ef;border-radius:16px;padding:12px 14px;background:#f7f9fc;color:#5d6672;font-size:11px;line-height:1.55;margin:-4px 0 12px}.ms-principle b{color:#28313d}
    .ms-grid6{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px;margin:12px 0}.ms-grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.ms-grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.ms-card{border:1px solid #e5e7eb;border-radius:16px;padding:13px;background:rgba(255,255,255,.80);min-height:112px}.ms-kicker{font-size:11.5px;color:#777f8b;font-weight:750}.ms-value{font-size:20px;font-weight:850;margin-top:6px;letter-spacing:-.03em;color:#292d35}.ms-state{display:inline-block;margin-top:7px;padding:3px 7px;border-radius:999px;font-size:10px;font-weight:800}.ms-state.good{background:#eaf7ef;color:#16845a}.ms-state.warn{background:#fff4dd;color:#b66a00}.ms-state.bad{background:#fff0f0;color:#d33c45}.ms-state.info{background:#edf3ff;color:#4569c7}.ms-state.na{background:#f1f3f5;color:#7c838c}.ms-detail{font-size:10.3px;color:#858c96;margin-top:7px;line-height:1.45}.ms-section{border:1px solid #e5e7eb;border-radius:20px;padding:17px 18px;background:rgba(255,255,255,.76);margin:10px 0}.ms-title{font-size:15px;font-weight:850;margin-bottom:11px;color:#292d35}.ms-note{font-size:11px;color:#7c838c;margin-top:10px;line-height:1.5}.ms-list{display:grid;gap:7px}.ms-row{display:grid;grid-template-columns:1.15fr .75fr .95fr 2fr;gap:10px;align-items:center;border-top:1px solid #edf0f2;padding:9px 2px;font-size:12px}.ms-row:first-child{border-top:0}.ms-row b{font-size:12.5px}.ms-summary{font-size:14px;line-height:1.7;color:#343942;background:#f7f9fb;border-radius:14px;padding:14px 16px}.ms-badge{display:inline-block;font-size:10px;font-weight:800;background:#eef2ff;color:#4661c9;padding:3px 7px;border-radius:999px;margin:5px 6px 0 0}
    .r38-dark .ms-hero,.r38-dark .ms-card,.r38-dark .ms-section{background:#171e28;border-color:#2a3442}.r38-dark .ms-hero h2,.r38-dark .ms-title,.r38-dark .ms-value{color:#f1f4f8}.r38-dark .ms-hero p,.r38-dark .ms-detail,.r38-dark .ms-note{color:#9ba7b5}.r38-dark .ms-principle,.r38-dark .ms-summary{background:#121923;border-color:#2a3442;color:#c5ced8}.r38-dark .ms-principle b{color:#eef2f7}
    @media(max-width:900px){.ms-grid6{grid-template-columns:repeat(2,minmax(0,1fr))}.ms-grid4{grid-template-columns:repeat(2,minmax(0,1fr))}.ms-grid3{grid-template-columns:1fr}.ms-row{grid-template-columns:1.1fr .8fr 1fr}.ms-row span:last-child{grid-column:1/-1;color:#7c838c}.ms-card{min-height:102px}.ms-hero{padding:17px}.ms-principle{font-size:10.5px}}
    </style>''',unsafe_allow_html=True)

    from market_view import render as render_market_v347
    aux=_market_aux_v345()
    market_data=dict(aux)
    market_data.update({
        'SP500':sp,'US3M':data.get('3개월물',pd.Series(dtype=float)),
        'US2Y':y2,'US10Y':y10,'US30Y':y30,'EFFR':fed,
        'REAL10':data.get('10년물실질금리',pd.Series(dtype=float)),
        'TERM':data.get('10년물기간프리미엄',pd.Series(dtype=float)),
        'HY':hy,'BBB':bbb,'VIX':vix,'UNEMP':unemp,'CLAIMS':icsa,
        'CPI':cpi,'CORECPI':core_cpi,'COREPCE':core_pce,'CAPE':cape,
    })
    render_market_v347(st,market_data)
    st.stop()


if _view=="risk":
    # Reuse the snapshot already calculated above for the dashboard header.
    # This avoids an extra compute_snapshot() call and keeps this view fast.
    _risk_final=float(overall)
    _risk_base=float(base_overall)
    _risk_prev=float(prev_overall) if pd.notna(prev_overall) else np.nan
    _risk_delta=_risk_final-_risk_prev if np.isfinite(_risk_prev) else np.nan

    _risk_categories={
        "시장·밸류에이션":float(scores.get("시장·밸류에이션",0) or 0),
        "변동성":float(scores.get("변동성",0) or 0),
        "금리":float(scores.get("금리",0) or 0),
        "신용":float(scores.get("신용",0) or 0),
        "경기":float(scores.get("경기",0) or 0),
        "물가":float(scores.get("물가",0) or 0),
    }
    _risk_categories={k:(0.0 if not np.isfinite(v) else v) for k,v in _risk_categories.items()}
    _struct_count=int(structure.get("count",0) or 0) if isinstance(structure,dict) else (len(structure) if isinstance(structure,(list,tuple,set)) else int(bool(structure)))
    _rapid_count=int(rapid.get("count",0) or 0) if isinstance(rapid,dict) else (len(rapid) if isinstance(rapid,(list,tuple,set)) else int(bool(rapid)))
    _structure_floor=float(floor_diag.get("signal_floor",0) or 0)
    _stress_floor=float(floor_diag.get("stress_floor",0) or 0)
    def _signal_names(obj):
        if isinstance(obj,dict):
            for key in ("items","signals","active","names"):
                val=obj.get(key)
                if isinstance(val,(list,tuple,set)):
                    return [str(x) for x in val]
            return []
        if isinstance(obj,(list,tuple,set)):
            return [str(x) for x in obj]
        return []

    _struct_names=_signal_names(structure)
    _rapid_names=_signal_names(rapid)
    _level=_risk_level_label(_risk_final)
    _summary,_reasons=_risk_sentence_engine(
        _risk_categories,
        _struct_count,
        _rapid_count,
        _struct_names,
        _rapid_names,
        max_items=5
    )

    st.markdown('<section class="r38-panel"><div class="r38-section-title">위험지수 상세</div><div class="r38-note">오늘의 위험지수가 어떤 요인으로 형성됐는지 자세히 확인하세요.</div></section>',unsafe_allow_html=True)
    _delta_txt=f"{_risk_delta:+.1f}" if np.isfinite(_risk_delta) else "—"
    st.markdown(
        f'<div class="risk-detail-hero"><div class="risk-score-card"><div class="risk-score-main"><div class="risk-score-num">{_risk_final:.0f}</div><div class="risk-score-den">/ 100</div></div><div class="risk-score-side"><span class="risk-badge">현재 위험도 · {_esc(_level)}</span><div class="risk-delta">전일 대비 {_esc(_delta_txt)}</div></div></div><div class="risk-explain-card">{_esc(_summary)}</div></div>',
        unsafe_allow_html=True)

    st.markdown(
        '<div class="risk-detail-grid"><section class="risk-flow-card"><div class="risk-section-title">점수 형성 요약</div><div class="risk-flow">'
        f'<div class="risk-flow-step"><div class="risk-flow-label">기본 종합위험</div><div class="risk-flow-value">{_risk_base:.0f}</div><div class="risk-flow-sub">6대 요소 기본 점수</div></div>'
        f'<div class="risk-flow-step"><div class="risk-flow-label">구조적 신호 하한</div><div class="risk-flow-value">{_structure_floor:.0f}</div><div class="risk-flow-sub">중기 위험 하한</div></div>'
        f'<div class="risk-flow-step"><div class="risk-flow-label">시장 스트레스 하한</div><div class="risk-flow-value">{_stress_floor:.0f}</div><div class="risk-flow-sub">진행 중 스트레스</div></div>'
        f'<div class="risk-flow-step"><div class="risk-flow-label">최종 위험지수</div><div class="risk-flow-value">{_risk_final:.0f}</div><div class="risk-flow-sub">0 ~ 100</div></div></div></section>'
        '<section class="risk-signal-card"><div class="risk-section-title">위험 신호</div><div class="risk-signal-row">'
        f'<div class="risk-signal-box"><div class="risk-signal-count">{_struct_count}</div><div class="risk-signal-label">구조적 위험신호</div></div>'
        f'<div class="risk-signal-box"><div class="risk-signal-count">{_rapid_count}</div><div class="risk-signal-label">시장 급변신호</div></div>'
        '</div></section></div>',unsafe_allow_html=True)

    _notes={"시장·밸류에이션":"200일선·CAPE·20일 모멘텀","변동성":"VIX 수준·단기 급등","금리":"10년물 수준·상승속도·스프레드","신용":"HY/BBB 스프레드와 단기 악화","경기":"실업률·Sahm·실업수당","물가":"CPI·Core CPI·Core PCE"}
    _names={"시장·밸류에이션":"시장 과열도","변동성":"변동성","금리":"금리","신용":"신용 시장","경기":"경기","물가":"물가"}
    _components=[]
    for k,v in _risk_categories.items():
        _components.append(f'<div class="risk-component-card"><div class="risk-component-head"><div class="risk-component-name">{_esc(_names[k])}</div><div class="risk-component-score">{v:.0f}</div></div><div class="risk-bar"><span style="width:{max(0,min(100,v)):.1f}%"></span></div><div class="risk-component-note">{_esc(_notes[k])}</div></div>')
    _reason_html="".join(f'<div class="risk-reason"><span class="risk-reason-dot">✓</span><span>{_esc(r)}</span></div>' for r in _reasons)
    st.markdown(f'<div class="risk-detail-grid"><section class="risk-flow-card"><div class="risk-section-title">6대 구성요소</div><div class="risk-components">{"".join(_components)}</div></section><section class="risk-reasons-card"><div class="risk-section-title">오늘 점수가 나온 이유</div><div class="risk-reasons">{_reason_html}</div></section></div>',unsafe_allow_html=True)

    _marker=max(0,min(100,_risk_final))
    st.markdown(
        '<section class="risk-band-card"><div class="risk-section-title">위험구간 해석</div><div class="risk-band-track"><span></span><span></span><span></span><span></span><span></span>'
        f'<div class="risk-band-marker" style="left:{_marker:.1f}%">{_risk_final:.0f}</div></div>'
        '<div class="risk-band-labels"><div>매우 낮음<br>0~20</div><div>낮음<br>21~40</div><div>보통<br>41~60</div><div>높음<br>61~80</div><div>매우 높음<br>81~100</div></div>'
        f'<div class="risk-component-note" style="margin-top:10px">현재 위험지수 {_risk_final:.0f}은(는) {_esc(_level)} 구간입니다.</div></section>',unsafe_allow_html=True)
    st.stop()

_structure_count=int(structure.get('count',0) or 0); _structure_raw=structure.get('level','정상')
_rapid_count=int(rapid.get('count',0) or 0); _rapid_raw=rapid.get('level','정상')
struct_score=50 if _structure_count>=2 else (40 if _structure_count==1 else 0); rapid_score=65 if _rapid_count>=3 else (55 if _rapid_count==2 else 0)
struct_tone='#e53b46' if _structure_count>=3 else ('#ef9d17' if _structure_count else '#2fa374'); rapid_tone='#e53b46' if _rapid_count>=2 else ('#ef9d17' if _rapid_count else '#2fa374')
struct_label={'정상':'정상','관찰':'관찰','주의':'주의','경계':'경고'}.get(_structure_raw,_structure_raw); rapid_label={'정상':'정상','관찰':'관찰','급변 경보':'경고','강한 스트레스':'경고'}.get(_rapid_raw,_rapid_raw)
struct_chips=''.join(f'<span class="r38-chip warn">{_esc(x[0])}</span>' for x in structure.get('items',[])) or '<span class="r38-chip warn">활성 신호 없음</span>'
rapid_chips=''.join(f'<span class="r38-chip">{_esc(x)}</span>' for x in rapid.get('active',[])) or '<span class="r38-chip">급변 없음</span>'
_struct_names=[x[0] for x in structure.get('items',[]) if x]
try:
    _market_v02=market_status_sentence_v02(sp,vix,y10,hy,bbb)
    market_summary=_market_v02['sentence']
except Exception:
    if rapid.get('level') in ('급변 경보','강한 스트레스'):
        market_summary='단기 시장 스트레스가 빠르게 높아지고 있어 변동성 확대에 주의가 필요합니다.'
    elif _structure_count>=2:
        market_summary='시장 급변은 제한적이지만 여러 구조적 부담이 겹쳐 중기 위험을 주의해서 볼 구간입니다.'
    elif _structure_count==1:
        _reason=_struct_names[0] if _struct_names else '구조적 위험 요인'
        market_summary=f'시장 전반은 비교적 안정적이지만, {_reason}로 구조적 부담은 남아 있습니다.'
    elif overall>=61:
        market_summary='여러 위험 요인이 높아져 시장 취약성이 높은 상태입니다.'
    elif overall>=41:
        market_summary='시장 위험은 보통 수준이며 일부 지표의 변화는 계속 확인할 필요가 있습니다.'
    else:
        market_summary='시장 전반은 안정적이며 뚜렷한 급변 신호는 없습니다.'
hero_tone='#e53b46' if overall>=61 else ('#ef9d17' if overall>=41 else '#2fa374')
level1=f'''<section class="r38-panel"><div class="r38-section-title">한눈에 보는 시장 위험 {_info38("종합 위험지수는 중기적인 시장 취약성을 0~100으로 요약합니다. 구조적 위험은 수개월~1년 지속될 수 있는 취약성을, 시장 급변 신호는 수일~수주 단위의 빠른 스트레스를 별도로 보여줍니다.")}</div><div class="r38-hero-grid">
<div class="r38-hero-card danger"><div class="r38-card-title">위험지수 {_info38("시장·밸류에이션, 변동성, 금리, 신용, 경기, 물가를 가중 합산한 기본 위험도에 구조·급변·진행 중 시장 스트레스 하한을 적용한 최종 위험지수입니다.")}</div><div class="r38-horizon">중기 · 누적 시장 취약성</div><div class="r38-hero-main"><div class="r38-hero-left"><div><span class="r38-big {'red' if overall>=61 else ('orange' if overall>=41 else '')}">{overall:.1f}</span><span class="r38-unit">/ 100</span></div>{_risk_badge(overall)}</div><div class="r38-hero-side"><div class="r38-side-copy"><strong>전일 대비</strong><div class="r38-delta r38-{delta_class}">{_esc(delta_text)}</div></div></div></div><div class="r38-callout"><div class="r38-summary-lines"><div>현재 위험도 <b>{_esc(label(overall))}</b></div><div class="r38-chips"><span class="r38-chip warn">구조적 신호 {_structure_count}개</span><span class="r38-chip">급변 신호 {_rapid_count}개</span></div></div></div></div>
<div class="r38-hero-card warn"><div class="r38-card-title">구조적 위험 {_info38("장단기금리 역전 기억, 높은 CAPE, 물가 재가속, 고용 악화처럼 수개월 이상 지속될 수 있는 구조적 취약성을 감지합니다.")}</div><div class="r38-horizon">수개월~1년 · 지속 취약성</div><div class="r38-hero-main"><div class="r38-hero-left"><div class="r38-signal-main">{_esc(struct_label)}</div><span class="r38-badge {'orange' if _structure_count else 'green'}">신호 {_structure_count}개</span></div><div class="r38-hero-side"><div class="r38-side-copy"><strong>{'활성 신호 확인' if _structure_count else '구조 신호 없음'}</strong>{'현재 구조적 취약성이 감지되었습니다.' if _structure_count else '현재 뚜렷한 구조적 취약성은 없습니다.'}</div></div></div><div class="r38-callout warn"><b>감지된 신호 ({_structure_count}개)</b><div class="r38-chips">{struct_chips}</div></div></div>
<div class="r38-hero-card danger"><div class="r38-card-title">시장 급변 신호 {_info38("VIX, 신용 스프레드, 10년물 금리 상승, 신규 실업수당 추세 등 서로 다른 빠른 지표가 동시에 악화되는지를 봅니다. 1개 축은 관찰만 하며, 2개 이상 동시 확인되면 단기 시장 스트레스가 강화된 것으로 해석합니다.")}</div><div class="r38-horizon">수일~수주 · 단기 시장 스트레스</div><div class="r38-hero-main"><div class="r38-hero-left"><div class="r38-signal-main">{_esc(rapid_label)}</div><span class="r38-badge {'red' if _rapid_count>=2 else ('orange' if _rapid_count else 'green')}">급변 {_rapid_count}개</span></div><div class="r38-hero-side"><div class="r38-side-copy"><strong>{'단기 스트레스 확인' if _rapid_count>=2 else ('단일 축 관찰' if _rapid_count else '급변 없음')}</strong>{'여러 시장 축의 급격한 악화가 동시에 확인됩니다.' if _rapid_count>=2 else ('일부 급변 축을 관찰 중입니다.' if _rapid_count else '현재 뚜렷한 단기 급변 신호는 없습니다.')}</div></div></div><div class="r38-callout"><b>감지된 신호 ({_rapid_count}개)</b><div class="r38-chips">{rapid_chips}</div></div></div>
</div><div class="r38-interpret"><span class="r38-interpret-label">현재 시장 해석</span>{_esc(market_summary)}</div></section>'''
st.markdown(level1,unsafe_allow_html=True)


def _risk_icon_svg(kind):
    icons={
        '시장·밸류에이션':'<svg viewBox="0 0 24 24" fill="none"><path d="M4 17 9 12l4 3 7-8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 7h3v3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
        '변동성':'<svg viewBox="0 0 24 24" fill="none"><path d="M3 13c3-7 5 7 8 0s5-7 10 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
        '금리':'<span style="font-size:15px;font-weight:850">%</span>',
        '신용':'<svg viewBox="0 0 24 24" fill="none"><rect x="4" y="6" width="16" height="12" rx="2" stroke="currentColor" stroke-width="1.7"/><path d="M7 10h10M7 14h6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
        '경기':'<svg viewBox="0 0 24 24" fill="none"><path d="M5 18V11M10 18V7M15 18v-4M20 18V9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
        '물가':'<span style="font-size:16px;font-weight:850">$</span>'
    }
    return icons.get(kind,'')

label_map={'시장·밸류에이션':'시장 과열도','변동성':'변동성','금리':'금리','신용':'신용 시장','경기':'경기','물가':'물가'}
risk_info_map={
'시장·밸류에이션':'S&P500의 200일선 대비 과열, CAPE 고평가, 최근 상승 모멘텀을 종합한 시장 과열도입니다.',
'변동성':'현재 VIX 절대수준과 최근 5거래일 급등 속도를 종합합니다.',
'금리':'미국 10년물 수준과 상승 속도, 10Y-2Y, 10Y-EFFR, 기간프리미엄을 종합합니다.',
'신용':'하이일드·BBB 스프레드 수준과 최근 5일·20일 악화 속도를 종합합니다.',
'경기':'실업률, Sahm Rule, 신규 실업수당의 상대 수준과 추세를 종합합니다.',
'물가':'CPI, 근원 CPI, 근원 PCE의 전년비와 최근 3개월 연율화 흐름을 종합합니다.'
}
risk_cards=[]
for k in ['시장·밸류에이션','변동성','금리','신용','경기','물가']:
    sc=scores.get(k,np.nan); state_class='low' if pd.notna(sc) and sc<41 else ('mid' if pd.notna(sc) and sc<61 else '')
    score_txt=f'{sc:.1f}' if pd.notna(sc) else 'N/A'
    risk_cards.append(f'''<div class="r38-risk-card"><div class="r38-risk-top"><div class="r38-risk-icon">{_risk_icon_svg(k)}</div><div class="r38-risk-name">{label_map[k]} {_info38(risk_info_map[k])}</div></div><div class="r38-risk-numrow"><div class="r38-risk-score">{score_txt}</div><span class="r38-mini-state {state_class}">{_esc(label(sc))}</span></div>{_seg_html(sc)}<div class="r38-risk-foot">0~100 · 높을수록 위험</div></div>''')
st.markdown(f'''<section class="r38-panel"><div class="r38-section-title">6대 위험 카테고리 현황 {_info38("종합 위험지수를 구성하는 여섯 영역의 현재 점수입니다. 각 점수는 0~100이며 높을수록 해당 영역의 위험이 큽니다.")}</div><div class="r38-risk-grid">{''.join(risk_cards)}</div><div class="r38-note">* 각 카테고리는 0~100 점수로 평가되며, 높을수록 위험이 큽니다.</div></section>''',unsafe_allow_html=True)

fx=_get_session_fx_items()
spv,spd,spc=_fmt_series_metric(sp,'',2); effv,effd,effc=_fmt_series_metric(fed,'%',2); y2v,y2d,y2c=_fmt_series_metric(y2,'%',2); y10v,y10d,y10c=_fmt_series_metric(y10,'%',2); y30v,y30d,y30c=_fmt_series_metric(y30,'%',2)
hyv,hyd,hyc=_fmt_series_metric(hy,'%p',2); cpiv,cpid,cpic=_cpi_metric(cpi); unv,und,unc=_fmt_series_metric(unemp,'%',1)
dxyv,dxyd,dxyc=_fmt_fx_metric('달러인덱스',2); krwv,krwd,krwc=_fmt_fx_metric('원/달러',2); jpyv,jpyd,jpyc=_fmt_fx_metric('엔/달러',2); wtiv,wtid,wtic=_fmt_fx_metric('WTI 유가',2); wtiv='$'+wtiv if wtiv!='N/A' else wtiv
cols=[('주식 / 정책',[('S&P 500',spv,spd,spc,list(sp.dropna().tail(60).values)),('미국 기준금리',effv,effd,effc,list(fed.dropna().tail(36).values))]),('국채 금리',[('미국 2Y',y2v,y2d,y2c,list(y2.dropna().tail(60).values)),('미국 10Y',y10v,y10d,y10c,list(y10.dropna().tail(60).values)),('미국 30Y',y30v,y30d,y30c,list(y30.dropna().tail(60).values))]),('신용 / 물가',[('하이일드 스프레드',hyv,hyd,hyc,list(hy.dropna().tail(60).values)),('CPI',cpiv,cpid,cpic,list((cpi.pct_change(12)*100).dropna().tail(18).values))]),('경기 / 달러',[('실업률',unv,und,unc,list(unemp.dropna().tail(18).values)),('달러 인덱스',dxyv,dxyd,dxyc,fx.get('달러인덱스',{}).get('spark',[]))]),('환율 / 원자재',[('원/달러',krwv,krwd,krwc,fx.get('원/달러',{}).get('spark',[])),('엔/달러',jpyv,jpyd,jpyc,fx.get('엔/달러',{}).get('spark',[])),('WTI 유가',wtiv,wtid,wtic,fx.get('WTI 유가',{}).get('spark',[]))])]
market_html=[]
for head,items in cols: market_html.append('<div class="r38-market-col"><div class="r38-col-head">'+_esc(head)+'</div>'+''.join(_metric_html(*x) for x in items)+'</div>')
_claims_confirm=bool(details.get('economy',{}).get('claims_confirm',False))
if pd.notna(sahm_now) and sahm_now>=.5 and _claims_confirm: rec_status='확인'
elif pd.notna(sahm_now) and sahm_now>=.5: rec_status='관찰'
else: rec_status='정상'
sahm_text=f'{sahm_now:.2f}%p' if pd.notna(sahm_now) else 'N/A'; unemp_text=f'{latest(unemp):.1f}%' if pd.notna(latest(unemp)) else 'N/A'
rec_html=f'''<div class="r38-recession"><div class="r38-recession-card"><div class="r38-recession-name">실업률</div><div class="r38-recession-value">{unemp_text}</div></div><div class="r38-recession-card"><div class="r38-recession-name">Sahm Rule</div><div class="r38-recession-value">{sahm_text}</div></div><div class="r38-recession-card"><div class="r38-recession-name">경기침체 신호</div><div class="r38-recession-value">{rec_status}</div></div></div>'''
st.markdown(f'''<section class="r38-panel"><div class="r38-section-title">핵심 시장 상태 {_info38("위험지수 계산과 시장 해석에 쓰는 주요 지표의 현재값, 직전 변화, 최근 추세를 함께 보여줍니다. 환율·DXY·WTI 일부 항목은 참고용이며 산식에는 포함되지 않습니다.")}</div><div class="r38-market-table">{''.join(market_html)}</div>{rec_html}<div class="r38-note">환율·달러인덱스·WTI 유가는 참고자료이며 종합위험지수 산식에는 포함하지 않습니다.</div></section>''',unsafe_allow_html=True)

@st.cache_data(ttl=3600,show_spinner=False)
def historical_risk_fast_338(data,cape):
    months=pd.date_range(pd.Timestamp.now().normalize()-pd.DateOffset(months=12),pd.Timestamp.now().normalize(),freq='MS'); rows=[]; prior_fast={}
    for dt in months:
        sub={k:v.loc[:dt].dropna() for k,v in data.items()}
        if len(sub.get('S&P500',pd.Series(dtype=float)))<220 or len(sub.get('VIX',pd.Series(dtype=float)))<30 or len(sub.get('10년물',pd.Series(dtype=float)))<30: continue
        sub_cape=cape.loc[:dt].dropna() if len(cape) else cape; snap=compute_snapshot(sub,sub_cape,with_alerts=False); fast=fast_signal_scores(snap['details']); rap=rapid_alert(fast,prior_fast)
        struct=structural_signals(snap['details'],(sub['10년물']-sub['2년물']).dropna()); final,_=apply_risk_floors(snap['overall'],struct,rap,sub['S&P500'],sub['VIX'],fast.get('신용',np.nan)); rows.append((dt,snap['overall'],final)); prior_fast=fast
    return pd.DataFrame(rows,columns=['date','base','risk']).set_index('date') if rows else pd.DataFrame(columns=['base','risk'])

def render_history_chart_338(hist):
    rows=[]
    for dt,row in hist.dropna(how='all').iterrows():
        dt=pd.Timestamp(dt); rows.append({'date':f'{dt.year}년 {dt.month}월 {dt.day}일','year':int(dt.year),'month':int(dt.month),'risk':round(float(row['risk']),1),'base':round(float(row['base']),1)})
    payload=json.dumps(rows,ensure_ascii=False)
    chart_html='''<div id="r38ChartWrap" style="width:100%;height:300px;position:relative;font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR','Segoe UI',sans-serif;touch-action:pan-y;background:#fff"><svg id="r38Chart" width="100%" height="300"></svg><div id="r38Tip" style="display:none;position:absolute;pointer-events:none;background:#101827;color:#fff;border-radius:7px;padding:8px 10px;font-size:11px;line-height:1.55;white-space:nowrap;z-index:5"></div></div><script>(()=>{const data=__PAYLOAD__,svg=document.getElementById('r38Chart'),wrap=document.getElementById('r38ChartWrap'),tip=document.getElementById('r38Tip');if(!data.length)return;const NS='http://www.w3.org/2000/svg',W=Math.max(320,wrap.clientWidth),H=300,L=38,R=12,T=24,B=35,PW=W-L-R,PH=H-T-B;svg.setAttribute('viewBox',`0 0 ${W} ${H}`);const x=i=>L+(data.length===1?PW/2:i*PW/(data.length-1)),y=v=>T+(100-v)*PH/100,el=(n,a={})=>{const q=document.createElementNS(NS,n);Object.entries(a).forEach(([k,v])=>q.setAttribute(k,v));return q};[[70,100,'#fff1f1'],[40,70,'#fff8e8'],[0,40,'#f1f8f4']].forEach(([a,b,c])=>svg.appendChild(el('rect',{x:L,y:y(b),width:PW,height:y(a)-y(b),fill:c})));[0,25,50,75,100].forEach(v=>{const yy=y(v);svg.appendChild(el('line',{x1:L,y1:yy,x2:W-R,y2:yy,stroke:'#e7ebef','stroke-width':'1'}));const t=el('text',{x:L-7,y:yy+4,'text-anchor':'end',fill:'#818995','font-size':'10'});t.textContent=v;svg.appendChild(t)});data.forEach((d,i)=>{if(i===0||i===data.length-1||i%2===0){const t=el('text',{x:x(i),y:H-11,'text-anchor':'middle',fill:'#818995','font-size':'10'});t.textContent=i===0?`${String(d.year).slice(-2)}년 ${d.month}월`:(d.month===1?`${String(d.year).slice(-2)}년`:`${d.month}월`);svg.appendChild(t)}});svg.appendChild(el('polyline',{points:data.map((d,i)=>`${x(i)},${y(d.base)}`).join(' '),fill:'none',stroke:'#4169c7','stroke-width':'1.6','stroke-dasharray':'5 4'}));svg.appendChild(el('polyline',{points:data.map((d,i)=>`${x(i)},${y(d.risk)}`).join(' '),fill:'none',stroke:'#e23a43','stroke-width':'2.1','stroke-linejoin':'round','stroke-linecap':'round'}));const leg1=el('text',{x:L,y:12,fill:'#e23a43','font-size':'10'});leg1.textContent='━ 최종 위험지수';svg.appendChild(leg1);const leg2=el('text',{x:L+92,y:12,fill:'#4169c7','font-size':'10'});leg2.textContent='┄ 기본 위험지수';svg.appendChild(leg2);const show=clientX=>{const rect=wrap.getBoundingClientRect(),px=Math.max(0,Math.min(rect.width,clientX-rect.left)),idx=Math.max(0,Math.min(data.length-1,Math.round(px/rect.width*(data.length-1)))),d=data[idx];tip.innerHTML=`<b>${d.date}</b><br><span style="color:#ff5961">●</span> 최종 위험지수　<b>${d.risk.toFixed(1)}</b><br><span style="color:#6790e8">●</span> 기본 위험지수　${d.base.toFixed(1)}`;tip.style.display='block';tip.style.left=Math.max(4,Math.min(px+10,rect.width-175))+'px';tip.style.top='45px'},hide=()=>tip.style.display='none';wrap.addEventListener('mousemove',e=>show(e.clientX));wrap.addEventListener('mouseleave',hide);wrap.addEventListener('touchstart',e=>{if(e.touches[0])show(e.touches[0].clientX)},{passive:true});wrap.addEventListener('touchend',hide,{passive:true});})();</script>'''.replace('__PAYLOAD__',payload)
    components.html(chart_html,height=305,scrolling=False)

st.markdown(f'''<section class="r38-panel"><div class="r38-section-title">위험지수 추이 {_info38("빨간선은 신호 하한을 반영한 최종 위험지수, 파란 점선은 하한 적용 전 기본 위험지수입니다. 과거 계산은 초기 로딩 속도를 위해 필요할 때만 실행합니다.")}</div>''',unsafe_allow_html=True)
if 'show_history_338' not in st.session_state: st.session_state.show_history_338=False
if st.button('최근 1년 추이 불러오기',type='secondary',key='history338'): st.session_state.show_history_338=True
if st.session_state.show_history_338:
    with st.spinner('추이 계산 중…'): hist=historical_risk_fast_338(data,cape)
    if len(hist): render_history_chart_338(hist); st.caption('최근 1년 월별 스냅샷 · 빨강=최종 위험지수, 파랑 점선=신호 하한 적용 전 기본 위험지수')
    else: st.warning('과거 위험지수를 계산할 데이터가 부족합니다.')
else: st.caption('초기 로딩 속도를 위해 과거 추이 계산은 필요할 때만 실행합니다.')
st.markdown('</section>',unsafe_allow_html=True)
with st.expander('세부 데이터 및 계산 기준'):
    st.write('종합위험지수: 시장·밸류에이션 25% + 금리 25% + 신용 15% + 경기 17% + 변동성 10% + 물가 8%.')
    st.write('최종 위험지수는 기본 위험도, 구조·급변 신호 하한, 진행 중 시장 스트레스 하한 중 가장 높은 값을 사용합니다.')
    st.write('시장·밸류에이션: 200일선 과열 45% + CAPE 35% + 최근 20거래일 상승 모멘텀 20%. 폭락 자체는 추가 위험으로 가산하지 않습니다.')
    st.write('변동성: 현재 VIX 절대수준 55% + 최근 5거래일 급등 45%.')
    st.write('금리: 10년물 수준 35% + 최근 20거래일 상승속도 25% + 10Y-2Y 15% + 10Y-EFFR 15% + 10년물 기간프리미엄 10%.')
    st.write('신용: HY OAS 45% + BBB OAS 20% + 최근 5거래일 확대 15% + 최근 20거래일 확대 20%.')
    st.write('경기: 실업률 30% + Sahm Rule 35% + 신규 실업수당 35%.')
    st.write('물가: CPI 25% + 근원 CPI 35% + 근원 PCE 40%.')
    st.write('데이터 공급자는 내부 표준 키와 분리되어 향후 실시간 API로 교체하기 쉽도록 유지합니다.')
st.markdown(f'<div class="r38-footer">Risk Monitor 3.48.1 · 화면 갱신 {datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")} · 캐시 즉시 표시 · 백그라운드 최신화</div>',unsafe_allow_html=True)
