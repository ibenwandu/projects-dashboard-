# GitHub Pages Configuration for Mission Control Dashboard

## Prerequisites

Before configuring GitHub Pages, ensure you have:

- **Repository**: `ibenwandu/projects-personal` (or your appropriate repository)
- **Code pushed to GitHub**: The `docs/` folder with `index.html` must be committed and pushed to the `main` branch
- **Repository permissions**: You must have "Settings" access to the repository (Owner or Collaborator with Admin role)
- **Branch protection**: If your repository has branch protection rules on `main`, ensure they allow GitHub Pages deployment

## Step-by-Step Configuration

### 1. Navigate to Repository Settings

1. Go to your GitHub repository: https://github.com/ibenwandu/projects-personal
2. Click the **Settings** tab (top right of the repository header)

### 2. Access GitHub Pages Settings

1. In the left sidebar, scroll down to **Code and automation** section
2. Click **Pages**

### 3. Configure Deployment Source

Under the **Source** section, you will see deployment options:

1. From the dropdown, select **Deploy from a branch**
2. In the **Branch** dropdown, select: `main`
3. In the **Folder** dropdown, select: `/docs`
4. Click **Save**

GitHub will process your configuration and begin deploying.

### 4. Wait for Deployment

- GitHub typically processes the configuration within **30 seconds to 1 minute**
- You will see a notification box appear when the deployment is complete
- The notification will display your GitHub Pages URL in the format: `https://<username>.github.io/projects-personal/`

### 5. Access Your Dashboard

Once deployment is complete, visit your GitHub Pages URL:

```
https://ibenwandu.github.io/projects-personal/
```

The Mission Control Dashboard should load automatically.

---

## Verification Checklist

After your site is live, verify functionality:

- [ ] GitHub Pages shows "Your site is live at: https://ibenwandu.github.io/projects-personal/"
- [ ] Dashboard loads and displays without errors
- [ ] Dark theme renders correctly (background, text, cards)
- [ ] "Last Updated" timestamp is visible in the header
- [ ] Live clock in top-right corner ticks every second
- [ ] Project cards are displayed and clickable
- [ ] Filter buttons (All, In Progress, Complete, Blocked) work correctly
- [ ] Page is responsive and readable on mobile devices
- [ ] Any QR codes or links in the dashboard are functional
- [ ] No console errors appear in browser Developer Tools (F12)

---

## Troubleshooting

### Dashboard Does Not Appear After 1 Minute

**Check the following:**

1. **GitHub Pages is enabled** in Settings → Pages
   - Verify that the "Your site is live at..." message appears
   - If you see "No deployment" or "Not published yet", GitHub is still processing

2. **Source configuration is correct**
   - Go to Settings → Pages
   - Confirm: Branch = `main`, Folder = `/docs`
   - If settings are incorrect, update and save again

3. **Files exist on GitHub**
   - Navigate to your repository on GitHub.com
   - Click "docs" folder to verify `index.html` is present
   - If files are missing, you may need to commit and push again

4. **Clear browser cache**
   - Press **Ctrl+Shift+Del** (Windows) or **Cmd+Shift+Del** (Mac)
   - Clear "Cached images and files" for "All time"
   - Reload the GitHub Pages URL

5. **Check GitHub Actions**
   - Go to the **Actions** tab in your repository
   - Look for a workflow named "pages build and deployment"
   - If it shows a red ✗, click it to see error details
   - Common errors: file not found, invalid paths, or permissions issues

### Styling or Layout Appears Broken

**If the dashboard loads but looks incorrect:**

1. **Check character encoding** in `docs/index.html`
   - The file should start with: `<meta charset="utf-8">`
   - If missing or incorrect, add/fix this line

2. **Open browser Developer Console** (F12)
   - Look for red error messages in the Console tab
   - Screenshot and address any JavaScript errors

3. **Verify CSS paths**
   - In the Network tab (F12), check if CSS files are loading (HTTP 200 status)
   - If any show 404 errors, the file paths need updating

4. **Test in a different browser**
   - Open the GitHub Pages URL in Chrome, Firefox, Edge, Safari
   - If it works in one browser, the issue may be local cache

### GitHub Pages URL Is Different Than Expected

GitHub Pages URLs follow this format:

- **User repositories** (personal): `https://<username>.github.io/<repo-name>/`
- **Organization repositories**: `https://<org-name>.github.io/`

To find your actual GitHub Pages URL:

1. Go to your repository Settings → Pages
2. Look for the blue banner that says "Your site is live at: <URL>"
3. That URL is your GitHub Pages address

**Update any references** (in documentation, README.md, links, etc.) if your URL differs from the expected format.

### Deployment Stuck or Failed

**If GitHub Pages shows an error or won't deploy:**

1. **Check GitHub Status**
   - Visit https://www.githubstatus.com/ to confirm GitHub is operational

2. **Verify branch protection rules**
   - Go to Settings → Branches → Branch protection rules
   - Ensure GitHub Apps/Actions aren't blocking deployment
   - Temporarily disable branch protection if necessary (then re-enable after)

3. **Commit and push a simple test**
   - Make a small change to `docs/index.html` (e.g., add a comment)
   - Commit and push to trigger a fresh deployment
   - Wait 1 minute and refresh

4. **Check file permissions**
   - Ensure `docs/index.html` is readable (not marked as private)
   - On GitHub web UI, you should be able to view the file in the browser

---

## Next Steps After Configuration

Once GitHub Pages is successfully deployed and verified:

1. **Automated updates** — The Mission Control Dashboard will automatically update every time you run `/close-session`
   - The `docs/index.html` file commits to GitHub automatically
   - GitHub Pages publishes within 1 minute of push

2. **No further manual configuration** is required
   - The dashboard will continuously reflect your latest project status
   - Simply run your standard session close procedure

3. **Share your dashboard** — Your GitHub Pages URL is now public
   - You can share the link with stakeholders, portfolio reviewers, or team members
   - The dashboard will display your current project portfolio and status

4. **Optional customization** — You can customize the dashboard further by:
   - Editing the HTML/CSS in `docs/index.html`
   - Adding new sections or data fields
   - Changing colors, fonts, or layout
   - All changes will auto-deploy on next push

---

## Quick Reference

| Item | Value |
|------|-------|
| **Repository** | https://github.com/ibenwandu/projects-personal |
| **Settings URL** | https://github.com/ibenwandu/projects-personal/settings/pages |
| **Dashboard URL** | https://ibenwandu.github.io/projects-personal/ |
| **Source Branch** | main |
| **Source Folder** | /docs |
| **Deployment Time** | 30 seconds to 1 minute |
| **Update Frequency** | Automatic on each push |

---

**Document Version**: 1.0
**Last Updated**: March 15, 2026
**Status**: Ready for user configuration
