# 把這次改動和中文 Canvas 拿到公司電腦

公司電腦要 clone 的是你這個 fork 的 `agent-auto-draft` 分支，不是上游 YuE 的 `main`。遠端是 `git@github.com:luyou00001/YuE2.git`。

這次進 git 的內容是三份報告，沒有改模型源碼：

- `agent_instructions.md`、`agent_answer.md`：文字結論，clone 之後用任何編輯器就能看。
- `docs/yue2-research-map.canvas.tsx`：中文 Canvas 源碼。Cursor 不會渲染倉庫裡的這份，要複製到該工作區的 canvases 目錄。

公司電腦需要能用 SSH 訪問這個 GitHub 倉庫。

```bash
git clone git@github.com:luyou00001/YuE2.git
cd YuE2
git checkout agent-auto-draft
```

先用編輯器打開 `agent_instructions.md` 就能看文字版。Canvas 要這樣開：

1. 用 Cursor 打開剛 clone 的 `YuE2` 文件夾，讓它生成工作區目錄。
2. 在 `~/.cursor/projects/` 裡找名字對應該路徑的文件夾。路徑裡的 `/` 會變成 `-`。例如 clone 在 `/Users/你的用戶名/YuE2`，目錄多半是 `~/.cursor/projects/Users-你的用戶名-YuE2/`。
3. 把報告複製進去：

```bash
mkdir -p ~/.cursor/projects/這裡換成上一步看到的目錄名/canvases
cp docs/yue2-research-map.canvas.tsx ~/.cursor/projects/這裡換成上一步看到的目錄名/canvases/
```

4. 在 Cursor 裡打開那個 `yue2-research-map.canvas.tsx`。它會在聊天旁邊編譯成可交互的報告。之後這台開發機若有新版本，在公司電腦執行 `git pull`，再把 `docs/` 裡的文件覆蓋回 canvases 目錄。

本次更新的文件：`docs/yue2-research-map.canvas.tsx`
