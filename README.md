# Ryan Chung — AI/ML Portfolio

A dark-themed, mobile-friendly, multi-page GitHub Pages portfolio with two real interactive Micrograd demos, a notebook-based learning series, and space for future AI infrastructure projects. The design intentionally omits a footer, and school references use only “Columbia University.”

**Target site:** https://ryan30402.github.io/

## What's included

| Public page | URL | Contents |
| --- | --- | --- |
| Home | `/` | Intro, featured Micrograd, future projects |
| Projects | `/projects/` | Filterable project cards |
| Micrograd | `/projects/micrograd/` | Derivative plot, neuron graph, notebook loss trace |
| Learning | `/learning/` | Andrej Karpathy learning roadmap |
| About | `/about/` | Academic background, interests and GitHub |

The site uses plain HTML, CSS, and JavaScript. No Node.js, npm, framework, backend, or paid hosting is required.

The bundled `assets/micrograd.ipynb` is the user's original uploaded notebook, including saved outputs. The on-page JavaScript visualizations demonstrate the associated mathematics rather than running Python in the browser.

**Credit:** Micrograd is a learning exercise following Andrej Karpathy's [Neural Networks: Zero to Hero](https://karpathy.ai/zero-to-hero.html) materials.

## 上線方式（macOS）

### 1. 下載檔案

下載對話中的 `ryan-portfolio-site.zip`，放在 `~/Downloads/`。

### 2. 解壓縮、Clone GitHub Repository

在 Terminal 輸入：

```bash
cd ~/Downloads
unzip ryan-portfolio-site.zip
git clone https://github.com/ryan30402/ryan30402.github.io.git
```

若 Repository 仍為空，Git 顯示 `You appear to have cloned an empty repository` 是正常的。

### 3. 將網站檔案複製到 Repository

```bash
cp -R ryan-portfolio-site/. ryan30402.github.io/
cd ryan30402.github.io
```

注意：`/.` 很重要，它會一起複製隱藏的 `.nojekyll` 檔案。

### 4. 本機預覽

```bash
python3 -m http.server 8000
```

在瀏覽器打開 http://localhost:8000/。

你可以點擊不同頁面、調整 Micrograd 滑桿、切換主題。關閉伺服器請按 **Control + C**。

**不要直接在 Finder 裡雙擊 `index.html` 預覽。** 此網站使用從根目錄開始的 URL；使用 HTTP 伺服器預覽才符合 GitHub Pages 的路徑行為。

### 5. 檢查專案

在專案資料夾執行：

```bash
python3 scripts/check_site.py
```

這會檢查內部頁面、靜態資源與 Notebook 是否存在；不是完整的瀏覽器測試。

### 6. 發布到 GitHub

確認已退出本機伺服器後，在專案資料夾執行：

```bash
git add .
git commit -m "Launch personal portfolio with Micrograd demos"
git branch -M main
git push -u origin main
```

第一次執行 `git commit` 時，Git 可能要求設定姓名與電子郵件。請使用自己的 GitHub 帳號設定。推送到 GitHub 可能需要 GitHub CLI、SSH Key，或 Git Credential Manager 完成身分驗證；不能直接用 GitHub 帳號密碼當作 HTTPS Git 密碼。

### 7. 開啟 GitHub Pages

1. 前往 https://github.com/ryan30402/ryan30402.github.io/settings/pages
2. `Build and deployment → Source`：**Deploy from a branch**。
3. `Branch`：**main**；目錄：**/(root)**。
4. 按 **Save**。
5. 等待 GitHub Pages 發布，再開啟 https://ryan30402.github.io/。

如果網站尚未出現，到 Repository 的 **Actions** 頁面檢查 Pages 部署是否完成。

> GitHub Pages 的預設發佈機制與設定請參照 [官方文件](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)。

## 以後如何編輯

| 想改什麼 | 修改哪個檔案 |
| --- | --- |
| 首頁自我介紹與作品卡片 | `index.html` |
| Projects 頁面內容 | `projects/index.html` |
| Karpathy 進度與學習路線 | `learning/index.html` |
| Micrograd 文字、圖表外觀 | `projects/micrograd/index.html` |
| 微分、Neuron 和 Loss 互動程式 | `assets/js/micrograd.js` |
| 全站配色、字型、卡片與 RWD | `assets/css/styles.css` |
| 導航、手機選單、主題切換、篩選 | `assets/js/main.js` |
| About、學歷與未來聯絡方式 | `about/index.html` |
| 原始 Jupyter Notebook | `assets/micrograd.ipynb` |

### 後續加入 LinkedIn、Email、Resume

這份初版只放已確認的 GitHub 帳號。請先確認要公開的 LinkedIn、電子郵件和履歷 PDF，再把連結加入 `about/index.html` 或全站導覽。不要在網頁中留下假地址。

### 新增下一個 Karpathy Lesson

等 Makemore 有實際筆記之後，新增對應的 HTML 頁面（例如 `learning/makemore/index.html`），再把 `learning/index.html` 的 Makemore 卡片連到該路由。不要把還沒做的課程標成 Completed。

### 類似 InferScale / TraceGuard 的未來專案

目前兩者僅是規劃卡片、沒有假的 Demo 或 Source 按鈕。實際有實作時，新增專案詳細頁、更新 `projects/index.html` 卡片，並貼上真實 GitHub Repository 連結。

## Release notes

- Default dark theme and optional light theme (stored in `localStorage`).
- Responsive mobile menu and real HTML page routes.
- Project category filter.
- Live derivative plot with gradient-descent step and reset controls.
- Live single-neuron tanh graph with backward gradients.
- SVG chart of a *single saved* 20-iteration training log; this is not a reproducibility or model performance claim.
- No third-party CDN or tracker.
- `.nojekyll` allows direct GitHub Pages publishing.

## Limitations

- There is no online notebook execution or Python backend.
- This first release uses manually authored HTML; if content grows substantially, it can be migrated to Astro/Markdown in a later iteration.
- Browser routes need to be served from `/`, matching a user site (`ryan30402.github.io`).
- GitHub remote publishing must be carried out by the repository owner.
