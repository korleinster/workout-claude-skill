# 🏋️ Workout Log — Claude Code Skill

A **Claude Code skill** that automates workout logging in Notion from a single Apple Fitness screenshot.

After your workout, take a screenshot of the Fitness app summary screen and send it to Claude. It automatically parses the data, logs it to your monthly Notion page, and adds AI trainer feedback comparing it to your previous sessions.

---

## ✨ Features

| Feature | Description |
|------|------|
| 📸 Auto image parsing | Extracts date, workout type, duration, BPM, calories, and intensity from Apple Fitness summary |
| 🏃 Workout type recognition | Auto-maps Indoor Cycling→Cycle, Running→Run, Strength→Weights, etc. |
| ➕ Combined workout merging | Multiple workouts on the same day → merged into one row (Cycle+Run, total calories, etc.) |
| 📝 Auto memo capture | Any text you type alongside the image is saved to the memo column |
| 🗂️ Monthly Notion auto-organization | Creates a new page automatically when the month changes, keeps previous data |
| 🔄 Auto column expansion | Automatically adds missing columns to existing tables |
| 📊 Progress comparison feedback | Analyzes trends and changes compared to the last 3–5 sessions |
| 🔀 Month-boundary linking | Auto-references the previous month's page on the first entry of a new month |
| 💬 Trainer feedback saved to Notion | Feedback is also automatically saved to a Notion table column |

---

## 📋 Notion Table Structure

| Date | Workout | Duration | Intensity | Avg BPM | Max BPM | Calories | Weight | Memo | Trainer Feedback |
|------|----------|------|------|---------|---------|--------|------|------|----------------|
| 6/1 (Mon) | Cycle | 30 min | 6 (Moderate) | 145 | 167 | 348 kcal | 88.2 kg | | Avg BPM 145, solid cardio zone session... |
| 6/4 (Thu) | Cycle+Run | 50 min | 7 (Hard) | 152 | 171 | 490 kcal | - | Slight lower back soreness | Calories up 41% vs last session... |

---

## 🗂️ Notion Page Auto-Structure

```
Workout (root page)
  └ 2026
       └ 2026_05  ← previous month (used for comparison)
       └ 2026_06  ← current month, auto-logged
       └ 2026_07  ← auto-created as empty table when July starts
```

A new page is created as an empty table when the month changes. On the first entry of a new month, the previous month's page is automatically referenced so trainer feedback comparisons continue without interruption.

| Situation | Behavior |
|------|------|
| Mid-month (3+ entries) | References current month page only |
| Early month (fewer than 3 entries) | Auto-fetches current + previous month → fills from last entry backwards |
| Very first entry | Writes feedback from today's data only, no comparison |

---

## 💡 Trainer Feedback Example

```
You trained in the cardio zone (140–160 BPM) with an average of 145 BPM,
reaching a peak of 167 BPM — a high-intensity session.
Average BPM rose by 5 compared to your last workout (5/29), showing steady cardio load increase.
Your recent 3-session average calorie burn is a stable 327 kcal.
At 88.2 kg with a goal of 80 kg, you have 8.2 kg to go — at this pace, achievable in 6–8 weeks.
For your next session, try extending the 130 rpm interval from 30s to 45s to step up intensity!
```

**BPM Zone Reference:**

| Range | Zone | Description |
|------|-----|------|
| ~120 BPM | Fat Burn Zone | Low intensity |
| 120–140 BPM | Aerobic Zone | Comfortable |
| 140–160 BPM | Cardio Zone | Effective for fat loss ✅ |
| 160+ BPM | Peak Zone | Very high intensity |

---

## 🚀 Installation

### 1. Install Claude Code

Follow the [Claude Code official docs](https://docs.anthropic.com/claude-code) to install.

### 2. Download the skill

```bash
git clone https://github.com/korleinster/workout-claude-skill.git
```

### 3. Connect Notion MCP

Connect the Notion MCP in Claude Code:

1. Claude Code Settings → MCP Servers
2. Add Notion MCP and link your Notion account

### 4. Prepare your Notion page

Create the following structure in Notion:

```
Workout           ← root page
  └ 2026          ← year page
```

Monthly pages (e.g. `2026_06`) are created automatically by the skill.

### 5. Configure SKILL.md

In the **Notion Structure** section of `SKILL.md`, replace the two IDs with your own page IDs:

```
ROOT_PAGE_ID  → your Workout root page ID
YEAR_PAGE_ID  → your year page ID (e.g. 2026 page)
```

How to find the ID from a Notion URL:
```
https://www.notion.so/workspace/page-title-[ID is here]
```

### 6. Update your profile

Fill in your info in the "User Info" section (step 6) of `SKILL.md`:

```markdown
- Height: 187 cm / Current weight: 88 kg / Goal: 80 kg
- Workout: Indoor cycling 3× per week
- Intervals: 90 rpm 1 min → 110 rpm 2 min → 130 rpm 30 sec
- Diet: Korean food with less flour + portion control
```

### 7. Register the skill

```bash
# Copy to Claude Code skills directory
cp -r workout-claude-skill ~/.claude/skills/workout-log
```

---

## 📱 Usage

### Basic usage

After your workout, take a screenshot of the **Apple Fitness app** summary screen and run:

```
/workout-log [attach screenshot]
```

### Add weight

```
/workout-log today's weight 87.5 kg [attach screenshot]
```

### Add a memo

```
/workout-log slight lower back soreness today [attach screenshot]
```

Any text you type alongside the image is automatically saved to the **memo column**.

### Combined workouts (multiple on the same day)

```
/workout-log [cycling screenshot] [running screenshot]
```

Multiple workouts on the same day are **merged into a single row** (`Cycle+Run`, total calories, etc.).

---

## 📸 Supported Screenshot Format

Supports the workout summary screen from the Apple Fitness app:

```
┌─────────────────────────┐
│     June 1 (Mon)        │
│  Indoor Cycling         │
│  11:18–11:49            │
├─────────────────────────┤
│ Duration    Active Cal  │
│ 0:30:36    290 KCAL     │
│ Total Cal   Avg BPM     │
│ 348 KCAL   145 BPM      │
├─────────────────────────┤
│ Effort: 6 Moderate      │
└─────────────────────────┘
```

---

## ☕ Sponsor

If this skill has helped your workout logging, consider sponsoring!

[![GitHub Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-❤️-ea4aaa?style=for-the-badge&logo=github-sponsors)](https://github.com/sponsors/korleinster)

---

## 📄 License

[CC BY 4.0](LICENSE) — When using, modifying, or distributing, **you must credit the original author (korleinster)**.

---

## 🤝 Contributing

Issues and PRs are welcome! Contributions of any kind are appreciated — new workout app support, improved feedback logic, and more.
