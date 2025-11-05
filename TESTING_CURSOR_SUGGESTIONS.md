# Testing Cursor-Style Inline Suggestions

## 🐛 Honest Status: NOT FULLY TESTED

I apologize - I initially built this theoretically without actually running it. I've now fixed several issues, but you'll need to test it to find any remaining bugs.

## 🔧 Fixes Applied

1. **Simplified the extension** - removed over-complex decoration logic
2. **Fixed backend JSON format** - removed incompatible `response_format` parameter
3. **Added debug logging** - you'll see console output at each step
4. **Inline widget rendering** - ghost text should appear as inline decorations

---

## 🚀 Step-by-Step Testing

### 1. Start Backend

```bash
cd server
# Make sure you have OPENAI_API_KEY set
export OPENAI_API_KEY="your-key-here"
python -m app
```

**Expected output:**
```
🤖 InlineSuggestionsService initialized with model: gpt-4.1
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Start Frontend

```bash
cd client
npm install  # if not done yet
npm run dev
```

**Expected output:**
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### 3. Open Browser

1. Navigate to `http://localhost:5173`
2. **Open DevTools** (F12) and go to **Console** tab
3. Watch for logs as you type

### 4. Test Inline Suggestions

#### Test A: Basic Trigger

1. Click in the editor
2. Type: `The Provider shall be liable for `
3. **Stop typing and wait 2 seconds**

**Expected Console Logs:**
```
💡 Requesting inline AI suggestion...
📨 Raw WebSocket message received: {...}
🔍 Parsed message: { status: 'inline_suggestion', alternatives: [...] }
📥 Editor received pendingSuggestion: { ... }
✅ Converting to CursorStyleSuggestion format: { alternatives_count: 3, ... }
🎯 Pushing suggestion to editor plugin...
✅ Suggestion pushed successfully
```

**Expected UI:**
- You should see **gray italic text** appear after "for "
- You should see a **black tooltip** above it with "Tab accept → next (1/3) Esc dismiss"

**If nothing appears:**
- Check console for errors
- Check if WebSocket is connected (green dot in UI)
- Check backend logs for API errors

#### Test B: Cycling Alternatives

1. With suggestion showing, press **→** (right arrow)
2. Text should change to alternative 2
3. Press **→** again for alternative 3
4. Press **→** again to cycle back to 1

**Expected Console Logs:**
```
🔄 Cycled to alternative 2/3
```

**Expected UI:**
- Ghost text changes each time
- Counter updates: "2/3", then "3/3", then "1/3"

#### Test C: Accepting Suggestion

1. With suggestion showing, press **Tab**
2. Ghost text should become real text (black, not gray)
3. Tooltip should disappear

**Expected Console Logs:**
```
✅ Accepting inline suggestion: [accepted text]
✅ Suggestion accepted: [accepted text]
```

#### Test D: Rejecting Suggestion

1. Type to trigger a new suggestion
2. Press **Esc**
3. Ghost text should disappear

**Expected Console Logs:**
```
❌ Rejecting inline suggestion: suggestion_12345
❌ Suggestion rejected
```

---

## 🐛 Common Issues & Fixes

### Issue 1: No ghost text appears

**Check 1: Is the WebSocket sending suggestions?**
```
Look for in console: "📨 Raw WebSocket message received"
```
If missing → Backend isn't responding

**Check 2: Is the editor receiving it?**
```
Look for: "📥 Editor received pendingSuggestion"
```
If missing → useSocket hook isn't working

**Check 3: Is it being pushed to plugin?**
```
Look for: "🎯 Pushing suggestion to editor plugin..."
```
If missing → The useEffect isn't triggering

**Check 4: Are there TypeScript errors?**
```bash
cd client
npm run build
```
Look for errors related to CursorStyleSuggestions

### Issue 2: Backend error "API key not configured"

**Fix:**
```bash
export OPENAI_API_KEY="sk-..."
cd server
python -m app
```

### Issue 3: Backend returns empty alternatives

**Check backend logs for:**
```
❌ OpenAI API error in inline suggestions: [error details]
```

**Common causes:**
- Invalid API key
- Rate limit exceeded
- Model not available (try GPT-3.5 instead)

**Fix: Use GPT-3.5 (cheaper, faster):**
```bash
export INLINE_SUGGESTIONS_MODEL="gpt-3.5-turbo"
python -m app
```

### Issue 4: Ghost text appears but in wrong position

**This means decorations are working but position is off.**

**Debug:**
1. Check `pendingSuggestion.position` in console
2. It should be the cursor position when you stopped typing
3. If it's wrong, the WebSocket is sending the wrong position

### Issue 5: TypeScript compilation errors

**If you see errors like "Property 'setSuggestion' does not exist":**

```bash
cd client
rm -rf node_modules
npm install
npm run dev
```

---

## 📊 What to Look For

### ✅ Working Correctly:

1. Console shows all debug logs in order
2. Gray italic text appears after you stop typing
3. Tooltip shows keyboard shortcuts
4. Arrow keys cycle through 3 alternatives
5. Tab accepts, Esc rejects
6. Text becomes black after accepting

### ❌ Not Working:

1. No console logs → Extension not loaded
2. Logs stop at "Requesting inline suggestion" → Backend issue
3. Logs show "alternatives: []" → OpenAI API issue
4. Ghost text doesn't appear → Decoration rendering issue
5. Tab doesn't work → Keyboard handler issue

---

## 🔬 Manual Backend Test (Bypass Frontend)

If frontend isn't working, test backend directly:

```bash
# In a new terminal, with backend running:
curl -X POST http://localhost:8000/ws \
  -H "Content-Type: application/json" \
  -d '{
    "type": "inline_suggestion",
    "content": "The Provider shall be liable for",
    "cursor_position": 35,
    "context_before": "The Provider shall be liable for",
    "context_after": "",
    "suggestion_type": "completion"
  }'
```

**Expected response should include:**
```json
{
  "status": "inline_suggestion",
  "alternatives": [
    {"text": "...", "confidence": 0.85, "reasoning": "Formal legal style"},
    {"text": "...", "confidence": 0.80, "reasoning": "Clear and concise"},
    {"text": "...", "confidence": 0.75, "reasoning": "Detailed and protective"}
  ]
}
```

---

## 🐞 Debug Checklist

Run through this if nothing works:

- [ ] Backend is running (`http://localhost:8000/docs` loads)
- [ ] Frontend is running (`http://localhost:5173` loads)
- [ ] WebSocket connected (green dot in UI)
- [ ] OpenAI API key is set (`echo $OPENAI_API_KEY`)
- [ ] Console shows no TypeScript errors
- [ ] Browser DevTools console is open
- [ ] Typed at least 10 characters
- [ ] Waited 2 seconds after typing
- [ ] Typed with a space at the end ("for " not "for")

---

## 📝 Report Issues

If it's still not working, provide:

1. **Frontend console logs** (copy all logs)
2. **Backend terminal output** (copy any errors)
3. **What you typed** (exact text)
4. **Screenshot** of the editor
5. **Browser** (Chrome, Firefox, etc.)

---

## 🎯 Known Limitations

1. **Debounce delay**: 1.5 seconds - might feel slow
2. **No mobile support**: Arrow keys don't work on mobile
3. **Position tracking**: May drift if document changes rapidly
4. **OpenAI latency**: 1-3 seconds for API response
5. **No persistence**: Suggestions don't persist across page refresh

---

## ✅ Success Criteria

You'll know it's working when you can:

1. Type "The Provider shall " and see gray text appear
2. Press → to see 3 different alternatives
3. Press Tab and see text become real
4. All console logs show up in correct order
5. Backend logs show "✅ Sent 3 alternative(s)"

---

## 🚨 If All Else Fails

If you can't get it working, try reverting to the simpler tooltip version:

```bash
git checkout client/src/internal/Editor.tsx
# This will restore the old tooltip overlay approach
```

The old version showed suggestions as overlays (not inline), but it definitely worked.

---

**Good luck! Let me know what errors you see in the console.** 🙏
