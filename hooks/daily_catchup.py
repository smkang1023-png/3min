# -*- coding: utf-8 -*-
"""SessionStart 훅: 오늘자 콘텐츠가 없으면 이 세션에 캐치업 실행 지시를 주입.

07:03 예약 실행(daily-content-engine)을 PC 절전 등으로 놓친 날의 보완 장치.
오늘자 content/YYYYMMDD_econ.json이 이미 있으면 아무것도 출력하지 않는다.
테스트: python daily_catchup.py 20991231  (강제로 미생성 분기 실행)
"""
import datetime
import json
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent  # content-engine

now = datetime.datetime.now()
override = sys.argv[1] if len(sys.argv) > 1 else None
today = override or now.strftime("%Y%m%d")
marker = ENGINE / "content" / f"{today}_econ.json"

# 오늘자가 이미 있거나 아직 이른 시각(07시 전)이면 조용히 종료
if marker.exists() or (override is None and now.hour < 7):
    sys.exit(0)

ctx = (
    f"오늘 아침 예약 작업(daily-content-engine)이 실행되지 못해 오늘자({today}) 콘텐츠가 아직 없다. 캐치업 규칙: "
    f"(1) {ENGINE}\\data\\catchup_{today}.lock 파일이 이미 있으면 다른 세션이 진행 중이니 아무것도 하지 마라. "
    f"(2) 없으면 그 lock 파일을 먼저 만들고, 사용자에게 한 줄로 알린 뒤 "
    "C:\\Users\\user\\.claude\\scheduled-tasks\\daily-content-engine\\SKILL.md 의 절차를 이 세션에서 그대로 실행하라. "
    "(3) 사용자의 첫 메시지가 별도 요청이면 그 요청을 먼저 처리하고, 마친 직후 파이프라인을 실행하라."
)

print(json.dumps({
    "systemMessage": "daily-content-engine catch-up: 오늘자 콘텐츠 미생성 — 이 세션에서 생성을 진행합니다.",
    "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx},
}))
