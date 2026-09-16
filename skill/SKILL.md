---
name: kahoot-pilot
description: >-
  Kahoot 即時 AI 答題助理。當使用者說「幫我玩 Kahoot」、「開始 Kahoot 答題」、「接管 Kahoot」、「Kahoot 代打」時觸發。
  支援 CDP 瀏覽器接管（localhost:9222）與多模態螢幕視覺識別，透過 Google Gemini 毫秒級極速解答並自動點擊。
---

# Kahoot AI 答題助理 (kahoot-pilot)

此技能讓 Antigravity 能夠化身為使用者的 Kahoot 代打與即時競賽助理。

## 🎯 觸發條件
當使用者提及以下意圖時自動激活：
- 「幫我玩 Kahoot」
- 「接管 Kahoot」
- 「開始 Kahoot 答題」
- 「啟動 Kahoot agent」

---

## 📋 代理人執行流程 (Workflow)

### 步驟 1：確認執行環境
1. 確保使用者已以遠端除錯模式開啟 Chrome：
   ```powershell
   & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\tmp\kahoot_profile"
   ```
2. 使用者已在該 Chrome 中開啟 `https://kahoot.it` 並進入遊戲房間/等待大廳。

### 步驟 2：在背景啟動 kahoo-agent
使用 `run_command` 工具在專案目錄下啟動 CDP 或 Vision 模式（作為後台任務）：

```powershell
python main.py cdp --delay 0.3
```

*(如果使用者表示題目只出現在主辦人的 Zoom/Teams 投影片上，則改啟動 `python main.py vision`)*

### 步驟 3：監控與回報
1. 利用後台任務的日誌輸出，掌握當前遊戲狀態。
2. 當題目出現並完成作答時，向使用者簡要回報：
   - 當前題目
   - 預測選擇的選項與顏色
   - AI 推論耗時（毫秒）與信心度。

### 步驟 4：結束接管
當使用者說「停止答題」或遊戲結束時，使用 `manage_task` 的 `kill` 動作安全關閉背景任務。
