# Weapon Action DB — Claude CLI 가이드

이 프로젝트는 액션 게임 무기 레퍼런스를 수집·검색·조합하는 DB 시스템입니다.
**Claude Code CLI**를 사용해 `data/weapons.json`을 지속적으로 확장할 수 있습니다.

---

## 프로젝트 구조

```
weapon-action-db/
├── data/
│   └── weapons.json     ← 메인 DB (여기에 엔트리 추가)
├── css/style.css
├── js/app.js
└── index.html           ← 브라우저에서 직접 열기 (로컬 서버 필요)
```

---

## JSON 엔트리 스키마

새 엔트리는 반드시 아래 구조를 따라야 합니다.

```json
{
  "id": "카테고리약어-번호",
  "weaponCategory": "대검|카타나|쌍검|창|도끼|낫|해머|채찍|권투|활|1H검|마법",
  "weaponSubtype": "구체적인 무기 이름",
  "game": "게임 타이틀",
  "developer": "개발사",
  "actionName": "액션 이름 (한글/원어 병기 권장)",
  "actionType": "기본 공격|무기술|차지 공격|카운터|패리|...",
  "description": "이 액션이 무엇인지 2~3문장으로 설명",
  "motionType": ["slash", "thrust", "overhead", "sweep", "spin", "charge", "dodge-cancel", "parry", "counter", "throw", "combo", "leap"],
  "mechanics": {
    "startupSpeed": "very-fast|fast|medium|slow|very-slow",
    "range": "short|short-medium|medium|medium-long|long|very-long",
    "staggerPower": "very-low|low|medium|high|very-high|continuous",
    "comboRole": ["opener", "extender", "finisher", "launcher", "ender", "punish"],
    "specialProperties": ["knockdown", "poise-breaking", "gap-closer", "..."],
    "resourceCost": "스태미나|FP|없음|쿨다운|...",
    "frameApprox": {
      "startup": "~Xf",
      "active": "~Xf",
      "recovery": "~Xf"
    }
  },
  "designNotes": "왜 이 액션이 잘 설계되었는지, 어떤 원칙을 담고 있는지. 게임 디자이너 관점에서 서술.",
  "tags": ["tag1", "tag2", "..."],
  "applicableWeapons": ["적용 가능한 무기 종류"],
  "addedDate": "YYYY-MM-DD"
}
```

**ID 규칙:**
- `gs-` → 대검 (Greatsword)
- `kt-` → 카타나
- `db-` → 쌍검 (Dual Blades)
- `sp-` → 창 (Spear)
- `ax-` → 도끼 (Axe)
- `sc-` → 낫 (Scythe)
- `hm-` → 해머 (Hammer)
- `wh-` → 채찍 (Whip)
- `ft-` → 권투 (Fist)
- `bw-` → 활 (Bow)
- `sw-` → 1H검 (Sword)
- `mg-` → 마법 (Magic)

---

## Claude CLI 사용법

### 기본 실행
```bash
cd D:/Project/weapon-action-db
claude
```

### 추천 프롬프트 예시

**1. 특정 무기 유형 레퍼런스 추가**
```
카타나 무기 레퍼런스 5개를 추가해줘.
Nioh 2, Ghost of Tsushima, Wo Long: Fallen Dynasty를 포함해서.
data/weapons.json의 weapons 배열에 추가하고 ID는 kt-006부터 시작해.
```

**2. 특정 게임의 모든 무기 유형 수집**
```
Monster Hunter: World의 무기 액션 레퍼런스를 장도, 태도, 랜스, 건랜스, 수렵피리 각 1개씩 추가해줘.
각각의 핵심 액션(콤보, 특수기 등)을 게임 디자이너 관점에서 설계 노트와 함께 작성해줘.
```

**3. 특정 메카닉 패턴 수집**
```
패리/카운터 메카닉이 뛰어난 게임들의 레퍼런스를 무기 종류 무관하게 6개 추가해줘.
Sekiro, Dark Souls, Sifu, Ghost of Tsushima 등을 참고해서.
```

**4. 새 무기 카테고리 추가**
```
"방패" 카테고리 레퍼런스 4개를 추가해줘.
Dark Souls의 방패 패리, Monster Hunter의 차지 블레이드 가드 포인트,
God of War Ragnarok의 Dauntless Shield 등을 포함해서.
```

**5. 조합 아이디어에서 새 무기 설계**
```
다음 두 레퍼런스를 조합한 새 무기 "파동검" 액션을 설계하고 JSON 엔트리로 추가해줘:
- 세키로의 모탈 드로우 (카타나 고속 발도)
- God of War의 레비아탄 도끼 리콜 (투척-귀환)
무기 카테고리는 카타나로 설정.
```

**6. 레퍼런스 품질 검토**
```
data/weapons.json을 읽고 designNotes가 너무 짧거나 태그가 부족한 엔트리를 찾아서
내용을 보강해줘. 특히 설계 원칙 설명이 구체적이지 않은 항목들 위주로.
```

---

## 로컬 서버 실행

### 방법 1: start.bat 더블클릭 (가장 간단)
`start.bat` 파일을 더블클릭하면 서버 시작 + 브라우저 자동 오픈

### 방법 2: 터미널에서 직접 실행
```bash
cd D:/Project/weapon-action-db
python server.py
```

접속: http://127.0.0.1:4200
(127.0.0.1 전용 바인드 — 외부 네트워크 접근 불가)

---

## 현재 DB 통계

현재 포함된 레퍼런스 예시:
- **대검**: Elden Ring, Dark Souls 3, Monster Hunter, God of War
- **카타나**: Sekiro, Nioh 2, Ghost of Tsushima, Elden Ring
- **쌍검**: Monster Hunter, Nioh 2, Bayonetta, Hades
- **창**: Monster Hunter, Hades, Nioh 2, Bloodborne
- **도끼**: God of War, Elden Ring, Dark Souls 3
- **낫**: Nioh 2, Hollow Knight, Bloodborne
- **해머**: Monster Hunter, Dark Souls 3, Elden Ring
- **활**: Horizon Zero Dawn, Elden Ring, Monster Hunter Rise
- **권투**: Sifu, Hades, Street Fighter 6
- **1H검**: Hollow Knight, Hades, Elden Ring, The Witcher 3
- **채찍**: Elden Ring, Castlevania
- **마법**: Elden Ring, Devil May Cry 5

총 **41개** 초기 레퍼런스 (Claude CLI로 무제한 확장 가능)
