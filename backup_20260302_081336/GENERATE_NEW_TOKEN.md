# Generate New Google Drive Refresh Token

## Step-by-Step Instructions

### Step 1: Run the Script
```bash
cd personal/Trade-Alerts
python get_new_refresh_token.py
```

### Step 2: Visit the Authorization URL
The script will display a URL like:
```
https://accounts.google.com/o/oauth2/auth?client_id=...&redirect_uri=urn:ietf:wg:oauth:2.0:oob&scope=https://www.googleapis.com/auth/drive&access_type=offline&response_type=code&approval_prompt=force
```

**Copy and paste this URL into your browser.**

### Step 3: Authorize the Application
1. Sign in to your Google account (if not already signed in)
2. Review the permissions requested
3. **IMPORTANT**: Make sure you see "offline access" or "Keep me signed in" option
4. Click "Allow" or "Continue"

### Step 4: Copy the Authorization Code
After authorization, Google will show you a code like:
```
4/0ATX87IPTPw_af8YbLh9xHYRduxb4LoT06OXY6ttpfsBG6mAXzuSahR-H4YMWLLcbXhcWRw
```

**Copy this entire code.**

### Step 5: Paste the Code
Go back to the terminal where the script is running and paste the code when prompted:
```
Enter verification code: [paste your code here]
```

Press Enter.

### Step 6: Get Your Refresh Token
The script will display your new refresh token. It will look like:
```
1//05xNNn6c7gR0KCgYIARAAGAUSNwF-L9IrQ...
```

### Step 7: Update Your .env File
1. Open `personal/Trade-Alerts/.env`
2. Find the line: `GOOGLE_DRIVE_REFRESH_TOKEN=...`
3. Replace the value with your new refresh token
4. Save the file

### Step 8: Test
Run the test script:
```bash
python test_drive_auth.py
```

You should see:
- [OK] Authenticated with Google Drive
- Successfully listed X files

---

## Alternative: Use the Complete OAuth Script

If you already have an authorization code from a previous attempt:

```bash
python complete_oauth.py
```

Then paste either:
- The full redirect URL from your browser
- Or just the authorization code

---

## Troubleshooting

**Problem**: "EOF when reading a line"
- **Solution**: The script needs interactive input. Make sure you're running it in a terminal (not through an IDE that doesn't support input)

**Problem**: "No refresh token found"
- **Solution**: Make sure you granted "offline access" during authorization. You may need to revoke previous access and try again.

**Problem**: "invalid_grant" error
- **Solution**: The authorization code may have expired (they expire quickly). Generate a new one.

