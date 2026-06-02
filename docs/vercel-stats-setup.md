# GitHub Stats 自托管部署备忘

> 目的：`README.md` 里的 Stats 卡 / 语言卡用的是**自己部署的** `github-readme-stats`，
> 避免公共实例 `github-readme-stats.vercel.app` 频繁 503 导致坏图。

## 关键信息

| 项目 | 值 |
|------|----|
| 部署平台 | Vercel（用 GitHub 账号登录，免费） |
| 项目源码 | https://github.com/anuraghazra/github-readme-stats |
| **我的实例地址** | `https://github-readme-stats-umber-three-90.vercel.app` |
| 环境变量 | `PAT_1` = 一个 GitHub Personal Access Token |

## 首次部署步骤

1. **建 GitHub Token**：https://github.com/settings/tokens → *Generate new token (classic)*
   - scope 不用勾（只读公开数据足够；要统计私有贡献则勾 `repo`）
   - 建议过期设为 **No expiration**，否则到期后卡会失效
   - 复制 token（`ghp_...`，只显示一次）
2. **部署到 Vercel**：打开源码仓库 → 点 README 里的 **Deploy** 按钮 → 用 GitHub 登录 → import → Deploy
3. **配环境变量**：Vercel 项目 → *Settings → Environment Variables* → 加 `PAT_1` = 刚才的 token → 保存
4. **Redeploy** 一次让变量生效
5. 拿到实例地址，替换 `README.md` 里两张卡的域名

## README 里的引用方式

把卡片 URL 的域名指向自己的实例即可（带素雅透明主题）：

```
https://github-readme-stats-umber-three-90.vercel.app/api?username=emmett2020&show_icons=true&hide_border=true&bg_color=00000000&title_color=808080&text_color=808080&icon_color=76B900
https://github-readme-stats-umber-three-90.vercel.app/api/top-langs/?username=emmett2020&layout=compact&hide_border=true&bg_color=00000000&title_color=808080&text_color=808080
```

## 卡片又变坏图了？排查顺序

1. **token 过期** → 重新生成，更新 Vercel 的 `PAT_1`，Redeploy（最常见原因）
2. **实例被删/暂停** → 进 Vercel 看项目是否还在、是否超额度
3. 直接 `curl` 实例地址看返回：200 + `image/svg+xml` 即正常；503 / 报错则按上面处理

## 验证命令

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  "https://github-readme-stats-umber-three-90.vercel.app/api?username=emmett2020"
```

---

## 附：贪吃蛇贡献图（无需 Vercel）

蛇形动画**不依赖 Vercel**，由本仓库的 `.github/workflows/animation.yml` 定时生成，
SVG 推到 `output` 分支，`README.md` 直接引用。无第三方依赖，稳定。

- 手动触发重新生成：`gh workflow run animation.yml`
- 生成两个文件：亮色 `github-contribution-grid-snake.svg` + 暗色 `...-snake-dark.svg`
