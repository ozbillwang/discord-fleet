# Discord Bot Setup Guide

## Overview
We need to create **2 separate Discord bot applications**:
1. **Guild Manager Bot** (admin bot) - manages the Discord server, creates channels, manages roles
2. **Bot User Bot** (member-facing bot) - answers members in bound channels

---

## Step 1: Create Guild Manager Bot Application

### 1.1 Go to Discord Developer Portal
1. Open https://discord.com/developers/applications
2. Click **"New Application"** (top right)
3. Name it: `BuilderXAI Guild Manager` (or your preferred name)
4. Accept Terms of Service
5. Click **"Create"**

### 1.2 Configure Guild Manager Bot Settings

**In the left sidebar, click "Bot"**

1. Click **"Add Bot"**
2. Under **"TOKEN"** section:
   - Click **"Reset Token"** if needed
   - Click **"Copy"** to copy the token
   - ⚠️ **SAVE THIS TOKEN** - you'll need it for GitHub Secrets
   - Keep it private! Never share or commit to git

3. Scroll down to **"Intents"** and enable:
   - ✅ **PRESENCE INTENT** (to track member status)
   - ✅ **SERVER MEMBERS INTENT** (to manage roles)
   - ✅ **MESSAGE CONTENT INTENT** (to read message content)

4. Scroll down to **"Privileged Gateway Intents"** section:
   - Toggle on all three:
     - ✅ Presence Intent
     - ✅ Server Members Intent
     - ✅ Message Content Intent

**TOKEN FOR GUILD MANAGER:**
```
<SAVE YOUR TOKEN HERE - you'll add to GitHub Secrets as DISCORD_GUILD_MANAGER_TOKEN>
```

---

### 1.3 Get Guild Manager Bot Invite URL

**In the left sidebar, click "OAuth2" → "URL Generator"**

1. Under **"SCOPES"** select:
   - ✅ `bot` (enables bot user)

2. Under **"PERMISSIONS"** select:
   - ✅ `Administrator` (for guild management)
   
   OR be more specific:
   - ✅ Manage Channels
   - ✅ Manage Roles
   - ✅ Manage Guild
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Attach Files
   - ✅ Read Message History
   - ✅ Manage Messages

3. Copy the **Generated URL** at the bottom
4. Open it in a browser to invite the bot to your Discord server

**GUILD MANAGER INVITE URL:**
```
<SAVE THIS URL - use to invite bot to your server>
```

---

## Step 2: Create Bot User Application

### 2.1 Create Another Application
1. Go back to https://discord.com/developers/applications
2. Click **"New Application"** again
3. Name it: `BuilderXAI` (or your preferred name for member-facing bot)
4. Click **"Create"**

### 2.2 Configure Bot User Settings

**In the left sidebar, click "Bot"**

1. Click **"Add Bot"**
2. Under **"TOKEN"** section:
   - Click **"Copy"** to copy the token
   - ⚠️ **SAVE THIS TOKEN** - you'll need it for GitHub Secrets
   - Keep it private!

3. Scroll down to **"Intents"** and enable:
   - ✅ **MESSAGE CONTENT INTENT** (to read messages)
   - ✅ **GUILD MESSAGES INTENT** (to receive messages in channels)
   - ✅ **DIRECT MESSAGES INTENT** (for DMs)

**TOKEN FOR BOT USER:**
```
<SAVE YOUR TOKEN HERE - you'll add to GitHub Secrets as DISCORD_BOT_USER_TOKEN>
```

---

### 2.3 Get Bot User Invite URL

**In the left sidebar, click "OAuth2" → "URL Generator"**

1. Under **"SCOPES"** select:
   - ✅ `bot`

2. Under **"PERMISSIONS"** select:
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Attach Files
   - ✅ Read Message History
   - ✅ Create Public Threads
   - ✅ Send Messages in Threads

3. Copy the **Generated URL**
4. Open it in a browser to invite the bot to your Discord server

**BOT USER INVITE URL:**
```
<SAVE THIS URL - use to invite bot to your server>
```

---

## Step 3: Configure Application IDs

For both bots, go to **"General Information"** tab to find the **Application ID**:

**GUILD MANAGER APPLICATION ID:**
```
<SAVE THIS - needed for Discord API calls>
```

**BOT USER APPLICATION ID:**
```
<SAVE THIS - needed for Discord API calls>
```

---

## Step 4: Get Your Discord Server Info

### 4.1 Find Your Server ID
1. In Discord, enable **Developer Mode**:
   - User Settings → App Settings → Advanced → Toggle "Developer Mode"
2. Right-click your server name in the sidebar
3. Click "Copy Server ID"

**YOUR DISCORD SERVER ID:**
```
<SAVE THIS>
```

### 4.2 Create Test Channels
Create a few test channels in your Discord server:
- `#guild-manager-test` (for Guild Manager bot testing)
- `#bot-user-test` (for Bot User testing)
- `#general` (for general use)

---

## Summary: Tokens to Save

After completing all steps above, you should have:

| Item | Value | Used For |
|------|-------|----------|
| Guild Manager Bot Token | `discord_XXX_...` | `DISCORD_GUILD_MANAGER_TOKEN` Secret |
| Bot User Bot Token | `discord_XXX_...` | `DISCORD_BOT_USER_TOKEN` Secret |
| Guild Manager App ID | `123456789...` | Lambda function config |
| Bot User App ID | `123456789...` | Lambda function config |
| Discord Server ID | `123456789...` | Lambda function config |

---

## Next: Add Tokens to GitHub Secrets

Once you have both bot tokens:

1. Go to your GitHub repo: https://github.com/ozbillwang/discord-fleet
2. Settings → Secrets and variables → Actions
3. Click **"New repository secret"**
4. Add these secrets:

**Secret 1: DISCORD_GUILD_MANAGER_TOKEN**
- Name: `DISCORD_GUILD_MANAGER_TOKEN`
- Value: (paste the Guild Manager bot token)
- Click "Add secret"

**Secret 2: DISCORD_BOT_USER_TOKEN**
- Name: `DISCORD_BOT_USER_TOKEN`
- Value: (paste the Bot User bot token)
- Click "Add secret"

---

## Verification

After adding secrets, verify both bots appear in your Discord server:
- ✅ `BuilderXAI Guild Manager` should be online and in your member list
- ✅ `BuilderXAI` (or Bot User) should be online and in your member list

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot doesn't appear in server | Make sure you used the correct invite URL for that bot |
| "Unauthorized" error | Check bot token is correctly copied (no extra spaces) |
| Bot can't read messages | Enable "Message Content Intent" in Developer Portal |
| Bot can't manage channels | Grant "Manage Channels" permission in OAuth2 URL Generator |

---

## Next Steps

Once both bots are in your Discord server and tokens are in GitHub Secrets:
1. Configure API Gateway for Discord interactions
2. Set up Discord webhook endpoints
3. Deploy Lambda functions
4. Test message routing

Ready to proceed? Run the verification steps above and let me know when the bots are in your server! ✅
