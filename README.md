# לוח משחקים — קדימה-צורן ופרו סוקר

אפליקציה מקומית שמושכת את כל המשחקים של קדימה-צורן ופרו סוקר, בכל הגילאים,
מאתר ההתאחדות לכדורגל בישראל (football.org.il), ומציגה אותם עם סינון לפי
עונה/שנה וגיל, בשתי לשוניות: **משחקים קרובים** ו-**ארכיון**.

## חשוב לדעת לפני שמתחילים

- `scraper.py` נכתב לפי מבנה ה-URL הידוע של האתר (`club_id`, `team_id`,
  `season_id`), שאותר דרך חיפוש, אך **לא נבדק מול האתר החי** — לסביבה שבה
  נכתב הקוד אין גישת רשת לאתר. סביר להניח שיידרש כיוונון קטן של הפרסור
  (parsing) בהרצה הראשונה אצלכם.
- מזהה המועדון של "פרו סוקר" הוגדר לפי "פרו סוקר השרון" (`club_id=8555`),
  מכיוון שזה היה המועדון היחיד בשם הזה שנמצא. אם התכוונתם למועדון אחר,
  עדכנו את `club_id` בקובץ `config.py`.
- קדימה-צורן: `club_id=4015`.

## התקנה (חד-פעמי)

```bash
cd football-tracker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## שלב 1: משיכת הנתונים

```bash
python scraper.py --debug
```

- `--debug` שומר עותק גולמי (HTML/JSON/טקסט) של כל עמוד שנסרק לתוך
  `data/debug/`. **בהרצה הראשונה תמיד הריצו עם `--debug`.**
- אם בסיום הריצה `data/games.json` ריק או שהמספר של המשחקים הוא 0:
  1. פתחו את `data/debug/team_<id>_<season>.txt` וראו איך נראה הטקסט
     המוצג בפועל של לוח המשחקים.
  2. פתחו את `data/debug/team_<id>_<season>.json` — אם יש שם payload
     שמכיל את רשימת המשחקים (למשל מפתחות כמו `games`, `matches`,
     `fixtures`), אפשר לפרסר אותו ישירות ולדלג על הניחוש הטקסטואלי.
  3. עדכנו את `parse_team_page_from_text()` או `parse_json_for_games()`
     ב-`scraper.py` בהתאם למבנה שראיתם, והריצו שוב.
- אפשר להגביל טווח עונות ומועדונים:

```bash
python scraper.py --years 2024 2026 --clubs kadima_zoran
```

## שלב 2: הרצת האתר

```bash
python app.py
```

פתחו בדפדפן: http://127.0.0.1:5000

מהאתר עצמו אפשר גם ללחוץ על "עדכון נתונים מהתאחדות הכדורגל" כדי להריץ
מחדש את הסקרייפר (ייקח כמה דקות, תלוי בכמות הקבוצות/עונות).

## פרסום לאינטרנט (Vercel + GitHub Actions)

הרעיון: **Vercel** לא יכול להריץ דפדפן headless (Playwright) בפונקציות
שרת שלו, אז את הסריקה בפועל מריצים ב-**GitHub Actions** (בחינם, על
שרתי אובונטו שיש בהם כל מה שצריך להריץ כרום headless), בלוח זמנים קבוע
(כברירת מחדל — כל יום ב-04:00 UTC). כל הרצה כותבת את `public/games.json`
ומבצעת עליו commit. Vercel מחובר לריפו וב-build סטטי פשוט — כל commit
חדש (כולל זה שה-Action עצמו יוצר) מפעיל דיפלוי אוטומטי מחדש.

### שלב 1: להעלות את הפרויקט ל-GitHub

```bash
cd football-tracker
git init
git add .
git commit -m "Initial commit"
```

בדפדפן: היכנסו ל-github.com, לחצו "New repository", תנו לו שם
(לדוגמה `football-tracker`), השאירו אותו **Public** (כדי ש-GitHub
Actions וה-Pages/Vercel יעבדו בלי הגבלות של תוכנית בתשלום), ואל תסמנו
"Add a README" (כבר יש לנו אחד). אחרי היצירה GitHub יראה לכם פקודות —
הריצו:

```bash
git remote add origin https://github.com/<your-username>/football-tracker.git
git branch -M main
git push -u origin main
```

### שלב 2: לוודא שה-Action יכול לבצע commit

ב-GitHub: Settings של הריפו → Actions → General → גללו ל-"Workflow
permissions" → סמנו **"Read and write permissions"** → Save. (בלי זה
ה-workflow ייכשל ב-`git push` בסוף הריצה.)

### שלב 3: להריץ את הסקרייפר בפעם הראשונה

ב-GitHub: לשונית **Actions** → workflow בשם "Scrape fixtures" → כפתור
**"Run workflow"**. עקבו אחרי הריצה — היא מתקינה Playwright, סורקת,
ועושה commit ל-`public/games.json`. זה עלול לקחת כמה דקות.

אם היא נכשלת, פתחו את הלוג — זה בדיוק כמו להריץ `python scraper.py`
אצלכם, אז אותם דברים שציינו למעלה (0 קבוצות/0 משחקים → צריך לכוון את
parse_team_page_from_text/parse_json_for_games) רלוונטיים גם כאן.

### שלב 4: לחבר את הריפו ל-Vercel

1. היכנסו ל-vercel.com עם חשבון ה-GitHub שלכם.
2. "Add New..." → "Project" → בחרו את הריפו `football-tracker`.
3. Vercel יזהה שאין framework (Other) — זה בסדר, `vercel.json` בפרויקט
   כבר אומר לו לשרת את התיקייה `public/` כאתר סטטי.
4. "Deploy". תוך דקה תקבלו כתובת ציבורית בסגנון
   `https://football-tracker-<random>.vercel.app`.

מאותה נקודה — בכל פעם שה-GitHub Action ירוץ (מדי יום, או ידנית) ויעדכן
את `public/games.json`, Vercel יריץ דיפלוי חדש אוטומטית תוך שניות,
והאתר הציבורי יציג את הנתונים העדכניים.

## מבנה הפרויקט

```
football-tracker/
  config.py        # רשימת המועדונים למעקב + מיפוי שנת עונה -> season_id
  scraper.py        # סקרייפר Playwright + כתיבה ל-data/games.json
  app.py             # שרת Flask מקומי (סינון + כפתור רענון) — לשימוש אצלכם במחשב
  templates/index.html, static/style.css, static/app.js   # ה-UI של app.py
  public/index.html  # האתר הסטטי שמתפרסם ל-Vercel (מושך public/games.json)
  public/games.json  # מה שמוצג באתר הציבורי — מתעדכן ע"י ה-GitHub Action
  vercel.json         # אומר ל-Vercel לשרת את public/ כאתר סטטי
  .github/workflows/scrape.yml  # מריץ scraper.py מדי יום ומעדכן public/games.json
  data/games.json    # נוצר אחרי הרצת scraper.py (מקומי)
  data/debug/         # דמפים גולמיים (--debug)
```
