# Mission Control Dashboard

Live status dashboard for Ibe's autonomous AI projects — accessible from anywhere, anytime.

## Quick Access

📱 **Mobile**: Open this dashboard on your phone using the QR code below or by copying the URL to your mobile browser.

🖥️ **Desktop**: Same URL works on any browser.

## 🎯 What You're Looking At

- **Vision**: Building a 24/7 autonomous organization that brings value and financial rewards
- **Systems Running**: Emy AI, Trade-Alerts, Scalp-Engine (3 active systems)
- **Agents Active**: 6 autonomous agents driving 24/7 operations
- **Projects**: 8 active projects with status, phases, and next milestones
- **Priorities**: Current work items with completion tracking
- **System Health**: Real-time status of all components

## 📱 Scan for Mobile Access

Open this QR code with your phone's camera to instantly access the dashboard:

![QR Code - Scan to open Mission Control on your phone](https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=https://github.com/ibenwandu/projects-personal)

## 🔄 How Updates Work

This dashboard updates automatically when development sessions close:
- Captures all project decisions and status updates
- Regenerates the dashboard HTML
- Commits to git and publishes via GitHub Pages (within 1 minute)

**Last updated**: Check timestamp in dashboard header

**Update frequency**: Typically 1-2x per day (when development sessions close)

## 🎨 Features

- ✅ Live clock (updates every second)
- ✅ Expandable project cards (click to see full details)
- ✅ Filterable projects (All / Live / Ready / Pending / Disabled)
- ✅ System status indicators (green = running, amber = warning, red = offline)
- ✅ Priority tracking with completion percentages
- ✅ Responsive design (desktop, tablet, mobile)
- ✅ Can be embedded in iframes

## 📖 Documentation

For full project documentation:
- [Main README](https://github.com/ibenwandu/projects-personal/blob/main/README.md) — Project overview
- [GitHub Pages Setup](./GITHUB_PAGES_SETUP.md) — Technical setup details
- [Implementation Summary](./IMPLEMENTATION_SUMMARY.md) — Architecture and design

## 🔗 Embed This Dashboard

You can embed the dashboard in documentation, wikis, or other platforms:

```html
<iframe src="https://github.com/ibenwandu/projects-personal"
        width="100%"
        height="800"
        frameborder="0"
        title="Mission Control Dashboard">
</iframe>
```

---

**Dashboard**: [index.html](./index.html) — Self-contained interactive HTML, no external dependencies

**Built with**: HTML5, CSS3, JavaScript (vanilla, no frameworks)

**Security**: No credentials, no external API calls — 100% static content
